"""Index synthetic road entities and EPSG:32646 near edges from authenticated WFS geometries."""
import json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.runtime import load_app_environment
from app.settings import ROOT,load_settings
from app.schemas import Entity,Attributes,GeoPoint,stable_id
from es.client import ElasticStore
from geoserver.client import GeoServer
from ingest.geodata import distance_metres
from ingest.relations import relation
from shapely.geometry import shape

def main():
    load_app_environment(); settings=load_settings(); store=ElasticStore(settings); identity=store.authenticate(); geo=GeoServer(settings)
    schools=geo.features('schools'); roads=geo.features('roads')
    # Link the known local school entities by OSM ID (the synthetic road layer is explicitly disclosed).
    entities=[Entity.model_validate_json(x) for x in (ROOT/'data/private/schools/entities.jsonl').read_text(encoding='utf-8').splitlines() if x]
    school_by_osm={e.attributes.osm_id:e for e in entities}
    road_entities=[]
    for f in roads:
        osm=str(f['properties'].get('osm_id') or f['id']); point=shape(f['geometry']).representative_point()
        road_entities.append(Entity(id=stable_id('entity','Road',osm),type='Road',canonical_name=str(f['properties'].get('name') or osm),
                                    attributes=Attributes(osm_id=osm,location=GeoPoint(lat=point.y,lon=point.x),synthetic=True)))
    edges={}
    # Use actual authenticated WFS geometries for both sides; projected distance implementation is EPSG:32646.
    for sf in schools:
        osm=str(sf['properties'].get('osm_id') or sf['id']); school=school_by_osm.get(osm)
        if school is None: continue
        for rf,road in zip(roads,road_entities):
            distance=distance_metres(sf['geometry'],rf['geometry'])
            if distance<=300:
                edge=relation(school.id,road.id,'near',[f"geoserver:schools:{sf['id']}",f"geoserver:roads:{rf['id']}"],
                              f'projected_epsg32646_distance_m:{distance:.3f}; synthetic road',.75)
                edges[edge.id]=edge
    new_edges=list(edges.values())
    rows=[{'id':e.id,**e.model_dump(mode='json')} for e in new_edges]
    entity_rows=[{'id':e.id,**e.model_dump(mode='json')} for e in road_entities]
    store.bulk(settings['indices']['entities'],entity_rows); store.bulk(settings['indices']['relations'],rows)
    report={'identity':identity,'schools_wfs':len(schools),'roads_wfs':len(roads),'road_entities':len(road_entities),
            'near_edges_within_300m':len(new_edges),'crs':'EPSG:32646','synthetic_geometry':True,
            'warning':'Distances apply to synthetic demonstration roads only; not real road proximity.',
            'counts':{name:store.count(index) for name,index in settings['indices'].items()}}
    (ROOT/'evidence/synthetic_near_relations.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
