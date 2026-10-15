"""Administrator-only provisioning. Credentials must already be in environment."""
import os
from app.settings import load_settings
from es.client import ElasticStore
from es.mappings import mappings


def provision(settings):
    store=ElasticStore(settings,admin=True)
    observed=store.request('GET','/')['version']['number']
    if observed!=settings['elasticsearch_version']:
        raise ValueError('Server version differs from configured version')
    for logical,body in mappings(settings['embedding_models'][0]['dimensions']).items():
        index=settings['indices'][logical]
        response=store.http.head('/'+index)
        if response.status_code==404:
            store.request('PUT','/'+index,json=body)
        elif response.status_code!=200:
            raise RuntimeError('Index existence check failed')
        else:
            current=store.request('GET','/'+index+'/_mapping')[index]['mappings']
            actual=current['properties']
            expected=body['mappings']['properties']
            # Elasticsearch 8.19 defaults dense_vector.element_type to float;
            # older mapping creation omitted the default explicitly.
            actual=__import__('copy').deepcopy(actual)
            expected=__import__('copy').deepcopy(expected)
            if 'embedding' in actual and actual['embedding'].get('type')=='dense_vector':
                actual['embedding'].setdefault('element_type','float')
            if 'embedding' in expected and expected['embedding'].get('type')=='dense_vector':
                expected['embedding'].setdefault('element_type','float')
            if actual!=expected:
                raise ValueError('Existing index mapping mismatch; migration required')
    role={'cluster':[],'indices':[{'names':list(settings['indices'].values()),
                                 'privileges':['read','write','view_index_metadata']}],'applications':[],'run_as':[]}
    store.request('PUT','/_security/role/rag_app',json=role)
    password=os.environ['ES_APP_PASSWORD']
    store.request('PUT','/_security/user/rag_app',json={'password':password,'roles':['rag_app']})
    return {'version':observed,'indices':settings['indices'],'role':'rag_app','health':store.request('GET','/_cluster/health')}


if __name__=='__main__':
    import json
    print(json.dumps(provision(load_settings()),indent=2))
