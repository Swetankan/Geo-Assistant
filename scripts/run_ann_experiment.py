"""Compare brute-force NumPy cosine top-10 with Elasticsearch HNSW on synthetic queries."""
import json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from app.models import LocalEmbeddings
from app.runtime import load_app_environment
from app.settings import ROOT,load_settings
from es.client import ElasticStore
from evalsuite.datasets import load_questions
from evalsuite.metrics import recall_at_k
from app.schemas import Chunk

def main():
    load_app_environment(); settings=load_settings(); store=ElasticStore(settings); identity=store.authenticate()
    model=LocalEmbeddings(settings['embedding_models'][0])
    chunks=[Chunk.model_validate_json(x) for x in (ROOT/'data/private/index_input/chunks.jsonl').read_text(encoding='utf-8').splitlines() if x]
    vectors=model.encode([c.text for c in chunks]); ids=[c.id for c in chunks]; matrix=np.asarray(vectors,dtype=np.float32)
    questions=load_questions(ROOT/'evalsuite/retrieval_judgments.jsonl')[:20]
    rows=[]
    for q in questions:
        query=model.encode([q.query],query=True)[0]
        started=time.perf_counter(); scores=matrix@query; exact_idx=np.argsort(-scores,kind='stable')[:10]; exact=[ids[i] for i in exact_idx]; exact_latency=time.perf_counter()-started
        for candidates in (20,50,100):
            started=time.perf_counter(); hits=store.search(q.query,query,k=10,num_candidates=candidates); elapsed=time.perf_counter()-started
            ann=[h.chunk_id for h in hits]
            overlap=len(set(exact)&set(ann))/10
            rows.append({'id':q.id,'num_candidates':candidates,'recall_at_10':overlap,'latency_seconds':elapsed,
                         'exact_numpy_seconds':exact_latency,'exact_ids':exact,'ann_ids':ann,'synthetic_queries':True})
    report={'synthetic_queries':True,'index_id_count':len(ids),'identity':identity,'results':rows,
            'summary':{str(n):{'mean_recall_at_10':float(np.mean([r['recall_at_10'] for r in rows if r['num_candidates']==n])),
                               'mean_latency_seconds':float(np.mean([r['latency_seconds'] for r in rows if r['num_candidates']==n]))} for n in (20,50,100)}}
    path=ROOT/'evidence/synthetic_assessment/ann_results.json'; path.write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps(report['summary'],indent=2))
if __name__=='__main__':main()
