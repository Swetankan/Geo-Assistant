"""Benchmark both local embedding models on first ten synthetic judged queries."""
import json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np,psutil
from app.models import LocalEmbeddings
from app.settings import ROOT,load_settings
from app.schemas import Chunk
from evalsuite.datasets import load_questions
from evalsuite.metrics import recall_at_k

def main():
    settings=load_settings(); chunks=[Chunk.model_validate_json(x) for x in (ROOT/'data/private/index_input/chunks.jsonl').read_text(encoding='utf-8').splitlines() if x]
    questions=load_questions(ROOT/'evalsuite/retrieval_judgments.jsonl')[:10]; reports=[]
    for cfg in settings['embedding_models']:
        started=time.perf_counter(); model=LocalEmbeddings(cfg); load_s=time.perf_counter()-started
        started=time.perf_counter(); vecs=model.encode([c.text for c in chunks],batch_size=64); encode_s=time.perf_counter()-started
        matrix=np.asarray(vecs,dtype=np.float32); ids=[c.id for c in chunks]; recalls=[]
        for q in questions:
            qv=model.encode([q.query],query=True)[0]; rank=np.argsort(-(matrix@qv),kind='stable')[:5]; recalls.append(recall_at_k([ids[i] for i in rank],q.judgments,5))
        reports.append({'model':cfg['source'],'dimensions':int(matrix.shape[1]),'load_seconds':load_s,'encoding_seconds':encode_s,
                        'chunks_per_second':len(chunks)/encode_s,'query_count':len(questions),'mean_recall_at_5':sum(recalls)/len(recalls),
                        'per_query_recall_at_5':recalls,'rss_bytes_after_encoding':psutil.Process().memory_info().rss,
                        'prefixes':{'query':cfg['query_prefix'],'document':cfg['document_prefix']}})
        del model,matrix,vecs
    report={'synthetic_judgments':True,'documents':len(chunks),'models':reports,'note':'Quality metrics are relative to generated synthetic labels.'}
    (ROOT/'evidence/live_synthetic_embedding_comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
