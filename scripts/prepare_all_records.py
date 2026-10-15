"""Merge GeoPackage facts and explicitly synthetic circular records for local indexing."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.cli import import_corpus
from app.schemas import Chunk, Entity, Relation
from app.settings import ROOT
from ingest.extract import merge_entities


def read(path, model):
    return [model.model_validate_json(line) for line in path.read_text(encoding='utf-8').splitlines() if line]


def main():
    schools = ROOT / 'data/private/schools'
    fiction = ROOT / 'data/private/corpus'
    import_corpus(ROOT / 'evalsuite/fixtures/corpus', fiction)
    chunks = read(schools / 'chunks.jsonl', Chunk) + read(fiction / 'chunks.jsonl', Chunk)
    entities = merge_entities(read(schools / 'entities.jsonl', Entity) + read(fiction / 'entities.jsonl', Entity))
    relations = read(fiction / 'relations.jsonl', Relation)
    if len({c.id for c in chunks}) != len(chunks): raise ValueError('Duplicate chunk ID')
    if len({e.id for e in entities}) != len(entities): raise ValueError('Duplicate entity ID')
    out = ROOT / 'data/private/index_input'
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in [('chunks', chunks), ('entities', entities), ('relations', relations)]:
        (out / f'{name}.jsonl').write_text(''.join(r.model_dump_json() + '\n' for r in rows), encoding='utf-8')
    report = {'chunks': len(chunks), 'entities': len(entities), 'relations': len(relations),
              'synthetic_chunks': sum(c.synthetic for c in chunks), 'real_geopackage_features': len(chunks)-sum(c.synthetic for c in chunks),
              'synthetic_policy_facts': 'fictional; do not present as real admissions policies'}
    (out / 'manifest.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
