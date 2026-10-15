import re
from app.schemas import Relation, stable_id
from ingest.geodata import distance_metres


def relation(source,target,kind,evidence,method,weight=1):
    return Relation(id=stable_id('relation',source,target,kind,sorted(evidence)),source_id=source,
                    target_id=target,type=kind,weight=weight,evidence=sorted(evidence),method=method)


def build_relations(chunks,entities):
    """Conservative sentence-local patterns. Mere document co-occurrence is insufficient."""
    edges = {}
    for chunk in chunks:
        local = [e for e in entities if any(m.chunk_id==chunk.id for m in e.mentions)]
        for sentence in re.finditer(r'[^.!?\n]+',chunk.text):
            present = [e for e in local if any(m.chunk_id==chunk.id and m.start>=sentence.start() and m.end<=sentence.end() for m in e.mentions)]
            for a in present:
                for b in present:
                    if a.id==b.id:
                        continue
                    kind = None
                    if a.type=='School' and b.type=='Board' and re.search(r'affiliated (?:with|to)',sentence.group(),re.I):
                        kind='affiliated_with'
                    elif a.type in ('Circular','Rule') and b.type=='Board' and re.search(r'applies to',sentence.group(),re.I):
                        kind='applies_to'
                    elif a.type=='Circular' and b.type=='School':
                        kind='mentions'
                    elif a.type=='School' and b.type=='Locality' and re.search(r'located in',sentence.group(),re.I):
                        kind='located_in'
                    elif a.type=='Circular' and b.type=='Circular':
                        if re.search(re.escape(a.canonical_name)+r'\s+supersedes\s+'+re.escape(b.canonical_name),sentence.group(),re.I):
                            kind='supersedes'
                    if kind:
                        edge=relation(a.id,b.id,kind,[chunk.id],'explicit_sentence_pattern',.9)
                        edges[edge.id]=edge
    return sorted(edges.values(),key=lambda r:r.id)


def near_relations(schools,roads):
    """Inputs (entity, GeoJSON feature) pairs. EPSG:32646 distances in metres."""
    for school,sf in schools:
        for road,rf in roads:
            distance=distance_metres(sf['geometry'],rf['geometry'])
            if distance<=300:
                yield relation(school.id,road.id,'near',[f'geoserver:schools:{sf["id"]}',f'geoserver:roads:{rf["id"]}'],
                               f'geometry_distance_epsg32646:{distance:.3f}m')
