"""Construct live assistant without administrator credentials."""
import os
from pathlib import Path
from app.schemas import Chunk,Entity,Relation
from app.settings import ROOT,load_settings
from app.models import LocalEmbeddings,LocalReranker,local_llm
from es.client import ElasticStore
from geoserver.client import GeoServer
from retrieve.graph import EvidenceGraph
from retrieve.confidence import LogisticCalibrator
from app.pipeline import Assistant


def load_app_environment():
    path=ROOT/'.env'
    allowed={'ES_APP_USER','ES_APP_PASSWORD','GEO_USER','GEO_PASSWORD'}
    if path.exists():
        for line in path.read_text().splitlines():
            if '=' in line and not line.startswith('#'):
                key,value=line.split('=',1)
                if key in allowed:
                    os.environ.setdefault(key,value)


def live_assistant(calibration_path=None):
    load_app_environment()
    settings=load_settings()
    store=ElasticStore(settings)
    store.authenticate()
    def records(logical,model):
        rows=[]
        for page in store.pages(settings['indices'][logical]):
            for hit in page:
                source=dict(hit['_source'])
                source.pop('embedding',None)
                rows.append(model.model_validate(source))
        return rows
    chunks=records('chunks',Chunk)
    entities=records('entities',Entity)
    relations=records('relations',Relation)
    graph=EvidenceGraph(entities,relations,settings['graph_fan_out'])
    calibrator=LogisticCalibrator.load(calibration_path) if calibration_path else None
    return Assistant(chunks,entities,graph,settings,store=store,embedder=LocalEmbeddings(settings['embedding_models'][0]),
                     reranker=LocalReranker(settings['reranker']),llm=local_llm(settings),calibrator=calibrator)
