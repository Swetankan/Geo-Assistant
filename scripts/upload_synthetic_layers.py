"""Replace only previously empty local GeoServer layers with marked demo geometries."""
import json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx,shapefile
from app.settings import ROOT,load_settings
from geoserver.bootstrap import shapefile_archive
from geoserver.client import GeoServer
from scripts.start_elastic import load_private_environment

def main():
    load_private_environment(); settings=load_settings(); geo=GeoServer(settings)
    initial={name:len(geo.features(name)) for name in ('schools','roads','landuse')}
    if initial['roads'] or initial['landuse']:
        for layer in ('roads','landuse'):
            if any(not str(f.get('properties',{}).get('name','')).startswith('SYNTHETIC ') for f in geo.features(layer)):
                raise RuntimeError('Refusing to replace non-synthetic GeoServer road/landuse features')
    data=ROOT/'data/private/synthetic_geodata'
    client=httpx.Client(base_url=settings['geoserver_url']+'/rest',auth=('admin',os.environ['GEO_ADMIN_PASSWORD']),timeout=60,trust_env=False)
    updated={}
    for layer,kind in [('roads',shapefile.POLYLINE),('landuse',shapefile.POLYGON)]:
        features=json.loads((data/f'{layer}.geojson').read_text(encoding='utf-8'))['features']
        archive=shapefile_archive(features,layer,kind)
        response=client.put(f'/workspaces/{settings["workspace"]}/datastores/{layer}/file.shp',
                            params={'configure':'all','update':'overwrite'},content=archive,
                            headers={'Content-Type':'application/zip'})
        if response.is_error: raise RuntimeError(f'GeoServer synthetic {layer} upload failed HTTP {response.status_code}')
        updated[layer]=len(features)
    counts={name:len(geo.features(name)) for name in ('schools','roads','landuse')}
    if counts['schools']!=initial['schools'] or counts['roads']!=12 or counts['landuse']!=12:
        raise RuntimeError(f'Unexpected WFS counts after update: {counts}')
    report={'synthetic_layers':updated,'counts':counts,'access':geo.access_check(),
            'disclosure':'Road and landuse geometries are synthetic demos, not OSM or surveyed features.'}
    (ROOT/'evidence/synthetic_geoserver_layers.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    prior=json.loads((ROOT/'evidence/geoserver_integration.json').read_text(encoding='utf-8'))
    prior['feature_counts']=counts
    prior['roads_landuse_status']='12 synthetic roads and 12 synthetic landuse polygons; not real observed geography'
    prior['synthetic_layer_disclosure']=report['disclosure']
    (ROOT/'evidence/geoserver_integration.json').write_text(json.dumps(prior,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
