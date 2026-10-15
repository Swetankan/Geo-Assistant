"""Administrator-only GeoServer provisioning. Never available as an LLM tool."""
import io
import json
import os
from pathlib import Path
import tempfile
import zipfile
import httpx
import shapefile
from pyproj import CRS
from app.settings import ROOT,load_settings
from ingest.geodata import read_gpkg
from geoserver.client import GeoServer


def shapefile_archive(features,layer,kind):
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory)
        with shapefile.Writer(str(root/layer),shapeType=kind,encoding='utf-8') as writer:
            writer.field('osm_id','C',size=48)
            writer.field('name','C',size=254)
            writer.field('type','C',size=30)
            for feature in features:
                writer.shape(feature['geometry'])
                p=feature['properties']
                writer.record(str(p.get('osm_id','')),p.get('name') or '',p.get('type') or '')
        (root/(layer+'.prj')).write_text(CRS.from_epsg(4326).to_wkt(version='WKT1_ESRI'))
        (root/(layer+'.cpg')).write_text('UTF-8')
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as archive:
            for path in root.iterdir():
                archive.write(path,path.name)
        return buffer.getvalue()


def provision(gpkg):
    settings=load_settings()
    url=settings['geoserver_url']
    # A fresh official GeoServer distribution has this bootstrap credential.
    # It is replaced immediately after scoped-user/data setup and never logged.
    configured=os.environ['GEO_ADMIN_PASSWORD']
    with httpx.Client(base_url=url,timeout=90,trust_env=False) as client:
        probe=client.get('/rest/about/version.json',auth=('admin',configured))
        password=configured if probe.status_code==200 else 'geoserver'
        client.auth=('admin',password)
        def call(method,path,**kwargs):
            response=client.request(method,path,**kwargs)
            if response.is_error:
                raise RuntimeError(f'GeoServer provisioning failed at {path}, HTTP {response.status_code}')
            return response
        version=call('GET','/rest/about/version.json').json()
        from xml.sax.saxutils import escape
        user='<user><userName>rag_geo</userName><password>'+escape(os.environ['GEO_PASSWORD'])+'</password><enabled>true</enabled></user>'
        existing_users=call('GET','/rest/security/usergroup/users',headers={'Accept':'application/json'}).json()
        exists='rag_geo' in str(existing_users)
        call('POST','/rest/security/usergroup/user/rag_geo' if exists else '/rest/security/usergroup/users',content=user,headers={'Content-Type':'application/xml'})
        roles=call('GET','/rest/security/roles',headers={'Accept':'application/json'}).json()
        if 'RAG_GEO' not in str(roles):
            call('POST','/rest/security/roles/role/RAG_GEO')
        call('POST','/rest/security/roles/role/RAG_GEO/user/rag_geo')
        workspace=settings['workspace']
        if client.get('/rest/workspaces/'+workspace+'.json').status_code==404:
            call('POST','/rest/workspaces',json={'workspace':{'name':workspace}})
        features=list(read_gpkg(gpkg))
        for layer,items,kind in [('schools',features,shapefile.POLYGON),('roads',[],shapefile.POLYLINE),('landuse',[],shapefile.POLYGON)]:
            if client.get(f'/rest/workspaces/{workspace}/datastores/{layer}.json').status_code==200:
                continue
            zipped=shapefile_archive(items,layer,kind)
            call('PUT',f'/rest/workspaces/{workspace}/datastores/{layer}/file.shp',params={'configure':'all'},
                 content=zipped,headers={'Content-Type':'application/zip'})
            title=layer if items else layer+' (NO DATA SUPPLIED - empty schema only)'
            call('PUT',f'/rest/workspaces/{workspace}/datastores/{layer}/featuretypes/{layer}',
                 json={'featureType':{'title':title,'srs':'EPSG:4326','enabled':True}})
        if password!=configured:
            admin_xml='<user><userName>admin</userName><password>'+escape(configured)+'</password><enabled>true</enabled></user>'
            call('POST','/rest/security/usergroup/user/admin',content=admin_xml,headers={'Content-Type':'application/xml'})
        client.auth=('admin',configured)
        call('POST','/rest/reload')
    geo=GeoServer(settings)
    access=geo.access_check()
    counts={layer:len(geo.features(layer)) for layer in ('schools','roads','landuse')}
    report={'version_response':version,'access':access,'feature_counts':counts,
            'roads_landuse_status':'empty schema only; no real or synthetic geometries supplied',
            'schools_source':'supplied schools.gpkg converted losslessly to shapefile geometry; names UTF-8'}
    (ROOT/'evidence/geoserver_integration.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    import argparse
    from scripts.start_elastic import load_private_environment
    parser=argparse.ArgumentParser()
    parser.add_argument('gpkg',type=Path)
    args=parser.parse_args()
    load_private_environment()
    print(json.dumps(provision(args.gpkg),indent=2))
