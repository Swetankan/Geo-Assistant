import struct
import pytest
from shapely.geometry import Polygon,mapping
from ingest.geodata import decode_gpkg_geometry,school_entity,distance_metres
from ingest.extract import RuleExtractor,resolve_school
from app.schemas import Chunk,Entity,stable_id


def test_gpkg_geometry_and_location():
    polygon=Polygon([(88,22),(88.001,22),(88.001,22.001),(88,22.001)])
    header=b'GP'+bytes([0,1])+struct.pack('<i',4326)
    assert decode_gpkg_geometry(header+polygon.wkb).equals(polygon)
    feature={'id':'1','properties':{'osm_id':'1','name':None},'geometry':mapping(polygon)}
    school=school_entity(feature)
    assert school.attributes.osm_id=='1'
    assert school.canonical_name=='Unnamed school (OSM 1)'
    assert distance_metres(mapping(polygon),mapping(polygon))==0


def test_rules_and_ambiguous_resolution():
    text='CBSE Rule 2 has 40 seats by 2026-11-01, not 2026-99-99.'
    chunk=Chunk(id='c',document_id='d',source='s',start=0,end=len(text),text=text)
    entities=RuleExtractor().extract(chunk)
    assert {e.type.value for e in entities}=={'Board','Rule','Quantity','Date'}
    assert len([e for e in entities if e.type=='Date'])==1
    for entity in entities:
        for m in entity.mentions:
            assert chunk.text[m.start:m.end]==entity.canonical_name
    schools=[Entity(id=str(i),type='School',canonical_name='Same School') for i in range(2)]
    assert resolve_school('Same School',schools) is None
