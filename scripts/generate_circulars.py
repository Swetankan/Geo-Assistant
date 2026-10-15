"""Create openly disclosed fictional policies attached to supplied school names."""
import json
import sys
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.settings import ROOT
from app.cli import import_gpkg


def main(gpkg):
    source = ROOT / 'data/private/schools/schools.geojson'
    if not source.exists():
        if gpkg is None:
            raise FileNotFoundError('Import schools.gpkg first or pass its path with --gpkg')
        import_gpkg(gpkg, ROOT / 'data/private/schools')
    features = json.loads(source.read_text(encoding='utf-8'))['features']
    schools = []
    seen = set()
    for feature in features:
        props = feature['properties']
        name = props.get('name')
        if name and name.casefold() not in seen:
            seen.add(name.casefold())
            schools.append((name, str(props['osm_id'])))
        if len(schools) == 12: break
    boards = ['CBSE', 'ICSE', 'WBBSE', 'CBSE', 'ICSE', 'WBBSE', 'CBSE', 'ICSE', 'WBBSE', 'CBSE', 'ICSE', 'WBBSE']
    folder = ROOT / 'evalsuite/fixtures/corpus'
    for i, ((school, osm_id), board) in enumerate(zip(schools, boards), 1):
        circular = f'CIRC-2026-{i:02d}'
        month = (i % 12) + 1
        content = f'''# Synthetic Circular {circular}: Fictional admission scenario

DISCLOSURE: This circular is fictional. Its policy facts do not describe the real school named below.

Issued 2026-{month:02d}-15 by the fictional East India District Education Office. Synthetic scenario reference school: {school} (OSM ID {osm_id}).

Circular {circular} applies to {board} schools and mentions {school}. In this fictional scenario, {school} is affiliated with {board}.

## Fictional eligibility and seats
{school} hypothetically offers {60 + 10*i} seats for Class 11. Applicants must be at least 14 years. The invented academic cut-off is {70 + i}% marks. Applications hypothetically close on 2026-{month:02d}-30.

## Fictional documents and policy
Rule {i} requires proof of age and prior examination marks. The fictional locality is Sector {i}. Circular {circular} supersedes Circular 2025-{i:02d} in this invented scenario.
'''
        (folder / f'{circular}.md').write_text(content, encoding='utf-8')
    print(json.dumps({'synthetic_documents': len(schools), 'source_school_names': [x[0] for x in schools], 'disclosure': 'All policy facts are fictional'}, indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description='Generate disclosed fictional admissions circulars.')
    parser.add_argument('--gpkg',type=Path,help='path to the supplied schools.gpkg if it has not been imported')
    main(parser.parse_args().gpkg)
