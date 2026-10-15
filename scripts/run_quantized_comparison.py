"""Create an isolated admin-only int8 HNSW benchmark index; app role stays scoped to 3 indices."""
import json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from app.models import LocalEmbeddings
from app.settings import ROOT,load_settings
from app.schemas import Chunk
from es.client import ElasticStore
from es.mappings import mappings
from scripts.start_elastic import load_private_environment
from evalsuite.datasets import load_questions

def main():
    load_private_environment(); settings=load_settings(); admin=ElasticStore(settings,admin=True)
    idx='east_india_chunks_int8'; spec=mappings(384,index_type='int8_hnsw')['chunks']
    if admin.http.head('/'+idx).status_code==404: admin.request('PUT','/'+idx,json=spec)
    else:
        actual=admin.request('GET','/'+idx+'/_mapping')[idx]['mappings']['properties']['embedding']
        if actual.get('index_options',{}).get('type')!='int8_hnsw': raise ValueError('Existing benchmark index mapping differs')
    chunks=[Chunk.model_validate_json(x) for x in (ROOT/'data/private/index_input/chunks.jsonl').read_text(encoding='utf-8').splitlines() if x]
    model=LocalEmbeddings(settings['embedding_models'][0]); vectors=model.encode([c.text for c in chunks])
    rows=[{**c.model_dump(mode='json'),'embedding':v.tolist()} for c,v in zip(chunks,vectors)]
    admin.allowed.add(idx); admin.bulk(idx,rows)
    questions=load_questions(ROOT/'evalsuite/retrieval_judgments.jsonl')[:20]
    idvec={c.id:v for c,v in zip(chunks,vectors)}; byid={c.id:c for c in chunks}; mat=np.asarray(vectors,dtype=np.float32); ids=[c.id for c in chunks]
    comparisons=[]
    for q in questions:
        qv=model.encode([q.query],query=True)[0]; exact=[ids[i] for i in np.argsort(-(mat@qv),kind='stable')[:10]]
        for candidates in (20,50,100):
            body={'size':10,'knn':{'field':'embedding','query_vector':qv.tolist(),'k':10,'num_candidates':candidates}}
            started=time.perf_counter(); result=admin.request('POST',f'/{idx}/_search',json=body); latency=time.perf_counter()-started
            found=[h['_id'] for h in result['hits']['hits']]
            comparisons.append({'id':q.id,'num_candidates':candidates,'recall_at_10':len(set(exact)&set(found))/10,'latency_seconds':latency})
    full=admin.request('GET','/east_india_chunks/_stats/store')['indices']['east_india_chunks']['total']['store']['size_in_bytes']
    quant=admin.request('GET',f'/{idx}/_stats/store')['indices'][idx]['total']['store']['size_in_bytes']
    report={'synthetic_queries':True,'quantized_index':idx,'mapping_type':'int8_hnsw','records':len(rows),'index_sizes_bytes':{'float_hnsw':full,'int8_hnsw':quant},
            'ann_summary':{str(n):{'mean_recall_at_10':float(np.mean([r['recall_at_10'] for r in comparisons if r['num_candidates']==n])),
                                   'mean_latency_seconds':float(np.mean([r['latency_seconds'] for r in comparisons if r['num_candidates']==n]))} for n in (20,50,100)},
            'application_role_scope':'unchanged; this experiment index is admin-only'}
    (ROOT/'evidence/live_quantized_comparison.json').write_text(json.dumps({'summary':report,'queries':comparisons},indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
