"""Ingest persisted provenance records through scoped runtime credentials."""
import argparse
import json
from pathlib import Path
from app.schemas import Chunk,Entity,Relation
from app.settings import load_settings
from app.models import LocalEmbeddings
from es.client import ElasticStore


def read_records(path,model):
    return [model.model_validate_json(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def ingest(directory,settings):
    store=ElasticStore(settings)
    identity=store.authenticate()
    chunks=read_records(directory/'chunks.jsonl',Chunk)
    entities=read_records(directory/'entities.jsonl',Entity)
    relations=read_records(directory/'relations.jsonl',Relation) if (directory/'relations.jsonl').exists() else []
    model=LocalEmbeddings(settings['embedding_models'][0])
    vectors=model.encode([c.text for c in chunks])
    records={'chunks':[{**c.model_dump(mode='json'),'embedding':v.tolist()} for c,v in zip(chunks,vectors)],
             'entities':[e.model_dump(mode='json') for e in entities],'relations':[r.model_dump(mode='json') for r in relations]}
    counts=[]
    for run in range(2):
        for logical,rows in records.items():
            store.bulk(settings['indices'][logical],rows)
        counts.append({logical:store.count(index) for logical,index in settings['indices'].items()})
    if counts[0]!=counts[1]:
        raise RuntimeError('Ingestion count changed on identical second run')
    return {'identity':identity,'counts':counts,'idempotent':True,'input_counts':{k:len(v) for k,v in records.items()}}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('directory',type=Path)
    parser.add_argument('--evidence',type=Path,default=Path('evidence/ingestion.json'))
    args=parser.parse_args()
    report=ingest(args.directory,load_settings())
    args.evidence.write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
