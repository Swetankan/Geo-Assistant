"""Generate explicitly fictional nearby roads/land-use to exercise GIS code paths."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pyproj import Transformer
from shapely.geometry import LineString,box,mapping,shape
from shapely.ops import transform
from app.settings import ROOT
from ingest.geodata import read_gpkg

def main(gpkg):
    schools=list(read_gpkg(gpkg))
    roads=[]; land=[]; tr=Transformer.from_crs(4326,32646,always_xy=True); inv=Transformer.from_crs(32646,4326,always_xy=True)
    for i,school in enumerate(schools[:12],1):
        p=shape(school['geometry']).representative_point(); x,y=tr.transform(p.x,p.y); osm=str(school['properties']['osm_id']); name=school['properties'].get('name') or ('OSM '+osm)
        # Artificial geometry centered near supplied school locations; never actual transport geography.
        road_m=LineString([(x+100,y-250),(x+100,y+250)])
        road=transform(inv.transform,road_m)
        roads.append({'type':'Feature','id':'synthetic-road-'+osm,'geometry':mapping(road),
                      'properties':{'osm_id':'synthetic-road-'+osm,'name':f'SYNTHETIC Road near {name}','type':'synthetic_local_road','synthetic':True,'school_osm_id':osm}})
        parcel=transform(inv.transform,box(x-250,y-250,x+250,y+250))
        land.append({'type':'Feature','id':'synthetic-landuse-'+osm,'geometry':mapping(parcel),
                     'properties':{'osm_id':'synthetic-landuse-'+osm,'name':f'SYNTHETIC land-use parcel near {name}','type':'synthetic_mixed_use','synthetic':True,'school_osm_id':osm}})
    out=ROOT/'data/private/synthetic_geodata';out.mkdir(parents=True,exist_ok=True)
    for name,features in [('roads',roads),('landuse',land)]:
        (out/f'{name}.geojson').write_text(json.dumps({'type':'FeatureCollection','features':features},ensure_ascii=False),encoding='utf-8')
    report={'synthetic':True,'source_schools':len(schools),'roads':len(roads),'landuse':len(land),
            'method':'500m projected line 100m from each of first 12 school representative points; square synthetic parcels',
            'warning':'Not real roads or land-use observations; never use for navigation or policy.'}
    (out/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Build clearly synthetic GIS demo layers from supplied school locations.')
    parser.add_argument('gpkg',type=Path,help='path to the supplied schools.gpkg')
    main(parser.parse_args().gpkg)
