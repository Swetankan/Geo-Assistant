import json
import httpx
import pytest
from es.client import ElasticStore
from es.mappings import mappings
from app.settings import load_settings,local_url
from app.models import LocalEmbeddings
from retrieve.filters import QueryFilter


def fake_store(monkeypatch,handler):
    monkeypatch.setenv('ES_APP_USER','rag_app')
    monkeypatch.setenv('ES_APP_PASSWORD','test-not-real')
    store=ElasticStore(load_settings())
    store.http.close()
    store.http=httpx.Client(base_url='http://127.0.0.1:9200',transport=httpx.MockTransport(handler))
    return store


def test_pit_advances_and_closes_latest_id(monkeypatch):
    calls=[]
    def handler(request):
        body=json.loads(request.content) if request.content else {}
        calls.append((request.method,request.url.path,body))
        if request.url.path.endswith('/_pit') and request.method=='POST':
            return httpx.Response(200,json={'id':'pit1'})
        if request.url.path=='/_search':
            if 'search_after' not in body:
                return httpx.Response(200,json={'pit_id':'pit2','hits':{'hits':[{'_id':'a','sort':['a',0]}]}})
            assert body['search_after']==['a',0] and body['pit']['id']=='pit2'
            return httpx.Response(200,json={'pit_id':'pit3','hits':{'hits':[]}})
        return httpx.Response(200,json={'succeeded':True})
    store=fake_store(monkeypatch,handler)
    assert len(list(store.pages('east_india_chunks')))==1
    assert calls[-1]==('DELETE','/_pit',{'id':'pit3'})


def test_bulk_reports_failures(monkeypatch):
    store=fake_store(monkeypatch,lambda request:httpx.Response(200,json={'errors':True,'items':[{'index':{'_id':'x','status':400,'error':{'type':'mapper_parsing_exception'}}}]}))
    with pytest.raises(RuntimeError,match='mapper_parsing_exception'):
        store.bulk('east_india_chunks',[{'id':'x'}])
    with pytest.raises(ValueError):
        store.bulk('unapproved',[])


def test_knn_filter_and_mapping(monkeypatch):
    def handler(request):
        body=json.loads(request.content)
        assert body['knn']['num_candidates']>=body['knn']['k']
        assert body['knn']['filter']['bool']['filter']==[{'term':{'board':'CBSE'}}]
        return httpx.Response(200,json={'hits':{'hits':[]}})
    store=fake_store(monkeypatch,handler)
    store.search('schools',[1,0],k=50,filters=QueryFilter(metadata={'board':'CBSE'}),num_candidates=20)
    mapping=mappings()['chunks']['mappings']
    assert mapping['dynamic']=='strict'
    assert mapping['properties']['embedding']['index_options']['type']=='hnsw'


def test_runtime_rejects_remote_and_superuser(monkeypatch):
    with pytest.raises(ValueError):
        local_url('https://example.com/api')
    monkeypatch.setenv('ES_APP_USER','elastic')
    monkeypatch.setenv('ES_APP_PASSWORD','test-not-real')
    with pytest.raises(ValueError):
        ElasticStore(load_settings())
