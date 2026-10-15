import argparse
import json
from pathlib import Path
from app.schemas import Entity, EntityType, Attributes, Chunk, Mention, stable_id
from app.settings import load_settings, ROOT
from ingest.documents import load_corpus
from ingest.extract import RuleExtractor, merge_entities
from ingest.relations import build_relations
from ingest.geodata import read_gpkg, school_entity
from retrieve.graph import EvidenceGraph
from app.pipeline import Assistant


def demo_assistant():
    synthetic_chunks = list(load_corpus(ROOT / 'evalsuite/fixtures/corpus', synthetic=True))
    chunks = list(synthetic_chunks)
    gazetteer = [Entity(id=stable_id('entity', 'School', name), type='School', canonical_name=name,
                        attributes=Attributes(synthetic=True)) for name in ('Lotus Demo School', 'River Demo School')]
    location_entities = []
    location_chunks = []
    schools_path = ROOT / 'data/private/schools/entities.jsonl'
    if schools_path.exists():
        for line in schools_path.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            school = Entity.model_validate_json(line)
            location = school.attributes.location
            if school.type != EntityType.School or location is None or school.canonical_name.startswith('Unnamed school'):
                continue
            text = (
                f'{school.canonical_name} is mapped at latitude {location.lat:.7f}, longitude {location.lon:.7f}. '
                'This representative point is inside the supplied school building polygon, not a verified entrance. '
                'The GeoPackage does not provide board, seat count, or admission cutoff.'
            )
            chunk_id = stable_id('chunk', 'gpkg-location', school.id, text)
            location_chunks.append(Chunk(
                id=chunk_id,
                document_id=stable_id('doc', 'gpkg', school.attributes.osm_id or school.id),
                source='schools.gpkg#' + (school.attributes.osm_id or school.id),
                start=0,
                end=len(text),
                text=text,
                synthetic=False,
                school_ids=[school.id],
                locations=[location],
            ))
            location_entities.append(school.model_copy(update={
                'mentions': [Mention(chunk_id=chunk_id, start=0, end=len(school.canonical_name))]
            }))

    extractor = RuleExtractor(gazetteer + location_entities)
    extracted = [e for c in chunks for e in extractor.extract(c)]
    entities = merge_entities(extracted + location_entities)
    chunks.extend(location_chunks)
    # The relation patterns apply to the synthetic circulars. GeoPackage
    # location rows contain only a school and its coordinates.
    relations = build_relations(synthetic_chunks, entities)
    return Assistant(chunks, entities, EvidenceGraph(entities, relations), load_settings(), demo=True)


def import_gpkg(path, output):
    features = list(read_gpkg(path))
    entities = [school_entity(f) for f in features]
    output.mkdir(parents=True, exist_ok=True)
    (output / 'schools.geojson').write_text(json.dumps({'type': 'FeatureCollection', 'features': features}, ensure_ascii=False), encoding='utf-8')
    (output / 'entities.jsonl').write_text(''.join(e.model_dump_json() + '\n' for e in entities), encoding='utf-8')
    chunks = []
    for entity in entities:
        loc = entity.attributes.location
        text = f'{entity.canonical_name}. OSM ID: {entity.attributes.osm_id}. Representative location: latitude {loc.lat:.7f}, longitude {loc.lon:.7f}. Location derived from the supplied school building polygon; not an entrance. Board, seats and admissions cutoff are not supplied.'
        doc = stable_id('doc', 'gpkg', entity.attributes.osm_id)
        chunks.append(Chunk(id=stable_id('chunk', doc, text), document_id=doc,
                            source='schools.gpkg#' + entity.attributes.osm_id,
                            start=0, end=len(text), text=text, school_ids=[entity.id], locations=[loc]))
    (output / 'chunks.jsonl').write_text(''.join(c.model_dump_json() + '\n' for c in chunks), encoding='utf-8')
    report = dict(features=len(features), entities=len(entities), chunks=len(chunks), synthetic=False,
                  named=sum(bool(f['properties'].get('name')) for f in features), source=Path(path).name,
                  extent=[min(e.attributes.location.lon for e in entities), min(e.attributes.location.lat for e in entities),
                          max(e.attributes.location.lon for e in entities), max(e.attributes.location.lat for e in entities)])
    (output / 'import_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def import_corpus(corpus, output):
    chunks = list(load_corpus(corpus, synthetic=True))
    gazetteer = []
    source_schools = ROOT / 'data/private/schools/entities.jsonl'
    if source_schools.exists():
        gazetteer = [Entity.model_validate_json(line) for line in source_schools.read_text(encoding='utf-8').splitlines() if line]
    extractor = RuleExtractor(gazetteer)
    entities = merge_entities([e for c in chunks for e in extractor.extract(c)])
    relations = build_relations(chunks, entities)
    output.mkdir(parents=True, exist_ok=True)
    for name, rows in [('chunks', chunks), ('entities', entities), ('relations', relations)]:
        (output / f'{name}.jsonl').write_text(''.join(r.model_dump_json() + '\n' for r in rows), encoding='utf-8')
    return dict(chunks=len(chunks), entities=len(entities), relations=len(relations), synthetic=True)


def main():
    parser = argparse.ArgumentParser(description='East India Geo-Assistant, local-only')
    sub = parser.add_subparsers(dest='command', required=True)
    demo = sub.add_parser('demo', help='Explicit synthetic smoke demo; no real-model claims')
    demo.add_argument('question')
    imp = sub.add_parser('import-gpkg')
    imp.add_argument('path', type=Path)
    imp.add_argument('--output', type=Path, default=ROOT / 'data/private/schools')
    corpus = sub.add_parser('prepare-corpus', help='Prepare explicitly synthetic assessment corpus')
    corpus.add_argument('directory', type=Path)
    corpus.add_argument('--output', type=Path, default=ROOT / 'data/private/corpus')
    args = parser.parse_args()
    if args.command == 'demo':
        answer, trace = demo_assistant().answer(args.question)
        print(json.dumps({'response': answer.model_dump(mode='json'), 'trace': trace}, indent=2, ensure_ascii=False))
    elif args.command == 'import-gpkg':
        print(json.dumps(import_gpkg(args.path, args.output), indent=2))
    else:
        print(json.dumps(import_corpus(args.directory, args.output), indent=2))


if __name__ == '__main__':
    main()
