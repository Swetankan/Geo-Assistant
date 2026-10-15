"""Prepare a document corpus using real GeoServer gazetteer or explicit GPKG input."""
import argparse
import json
from pathlib import Path
from app.schemas import Entity,Mention
from app.settings import load_settings
from app.models import local_llm
from app.runtime import load_app_environment
from ingest.documents import load_corpus
from ingest.extract import RuleExtractor,LLMExtractor,merge_entities,resolve_school
from ingest.relations import build_relations
from ingest.geodata import read_gpkg,school_entity
from geoserver.client import GeoServer


def prepare(corpus,output,settings,extractor_name='rules',gpkg=None,synthetic=False):
    features=list(read_gpkg(gpkg)) if gpkg else GeoServer(settings).features('schools')
    gazetteer=[school_entity(f) for f in features]
    extractor=RuleExtractor(gazetteer) if extractor_name=='rules' else LLMExtractor(local_llm(settings))
    chunks=list(load_corpus(corpus,synthetic=synthetic))
    extracted=[]
    unresolved=[]
    for chunk in chunks:
        for entity in extractor.extract(chunk):
            if entity.type=='School' and not entity.attributes.osm_id:
                match=resolve_school(entity.canonical_name,gazetteer,settings['resolution_threshold'])
                if match:
                    entity.id=match.id
                    entity.attributes=match.attributes.model_copy(deep=True)
                else:
                    unresolved.append({'id':entity.id,'name':entity.canonical_name,'reason':'below threshold or ambiguous'})
            extracted.append(entity)
    entities=merge_entities(gazetteer+extracted)
    for chunk in chunks:
        schools=[e for e in entities if e.type=='School' and any(m.chunk_id==chunk.id for m in e.mentions)]
        chunk.school_ids=sorted(e.id for e in schools)
        chunk.locations=[e.attributes.location for e in schools if e.attributes.location]
        boards={e.attributes.board for e in schools if e.attributes.board}
        if len(boards)==1:
            chunk.board=next(iter(boards))
    relations=build_relations(chunks,entities)
    output.mkdir(parents=True,exist_ok=True)
    for name,rows in [('chunks',chunks),('entities',entities),('relations',relations)]:
        (output/(name+'.jsonl')).write_text('\n'.join(row.model_dump_json() for row in rows)+'\n',encoding='utf-8')
    report={'chunks':len(chunks),'entities':len(entities),'relations':len(relations),'unresolved_schools':unresolved,
            'extractor':extractor_name,'synthetic_corpus':synthetic,'gazetteer_source':'gpkg' if gpkg else 'authenticated_geoserver',
            'validation_failures':getattr(extractor,'failures',[])}
    (output/'preparation_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('corpus',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--extractor',choices=['rules','llm'],default='rules')
    parser.add_argument('--gpkg',type=Path)
    parser.add_argument('--synthetic',action='store_true')
    args=parser.parse_args()
    load_app_environment()
    print(json.dumps(prepare(args.corpus,args.output,load_settings(),args.extractor,args.gpkg,args.synthetic),indent=2))
