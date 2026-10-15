"""Read GeoPackage geometry without GDAL. Keep source polygons and derived points."""
import json
import sqlite3
from pathlib import Path
from shapely import from_wkb
from shapely.geometry import mapping, shape
from shapely.ops import transform
from pyproj import Transformer
from app.schemas import Entity, Attributes, GeoPoint, stable_id


def decode_gpkg_geometry(blob):
    if not blob or blob[:2] != b'GP':
        raise ValueError('Invalid GeoPackage geometry header')
    envelope_code = (blob[3] >> 1) & 7
    sizes = {0:0,1:32,2:48,3:48,4:64}
    if envelope_code not in sizes:
        raise ValueError('Invalid geometry envelope')
    return from_wkb(blob[8+sizes[envelope_code]:])


def read_gpkg(path: Path):
    with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory = sqlite3.Row
        for spec in db.execute('SELECT table_name,column_name,srs_id FROM gpkg_geometry_columns'):
            table, column, srs = tuple(spec)
            quote = lambda x: '"'+x.replace('"','""')+'"'
            for row in db.execute(f'SELECT * FROM {quote(table)}'):
                if row[column] is None:
                    continue
                geom = decode_gpkg_geometry(row[column])
                if srs != 4326:
                    geom = transform(Transformer.from_crs(srs,4326,always_xy=True).transform,geom)
                if geom.is_empty or not geom.is_valid:
                    raise ValueError(f'Empty/invalid geometry for feature {row["fid"]}')
                props = {k:row[k] for k in row.keys() if k != column}
                yield dict(type='Feature',id=str(props.get('osm_id',props['fid'])),
                           properties=props,geometry=mapping(geom))


def school_entity(feature):
    p = feature['properties']
    # Representative point is guaranteed inside the polygon; it is not an entrance.
    point = shape(feature['geometry']).representative_point()
    osm_id = str(p['osm_id'])
    return Entity(id=stable_id('entity','School',osm_id),type='School',
                  canonical_name=p.get('name') or f'Unnamed school (OSM {osm_id})',
                  attributes=Attributes(osm_id=osm_id,location=GeoPoint(lat=point.y,lon=point.x)))


def distance_metres(left, right):
    project = Transformer.from_crs(4326,32646,always_xy=True).transform
    return transform(project,shape(left)).distance(transform(project,shape(right)))
