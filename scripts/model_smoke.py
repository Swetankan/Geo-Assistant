"""Actual local inference measurements on explicitly synthetic passages."""
import json
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import psutil
from app.models import LocalEmbeddings,LocalReranker
from app.settings import load_settings
from app.cli import demo_assistant
from retrieve.ranking import exact_search

settings=load_settings()
assistant=demo_assistant()
chunks=list(assistant.chunks.values())
report={'synthetic':True,'assessment_quality_evaluation':False,'embeddings':[]}
query='How many seats at Lotus Demo School?'
for config in settings['embedding_models']:
    started=time.perf_counter()
    model=LocalEmbeddings(config)
    load_seconds=time.perf_counter()-started
    started=time.perf_counter()
    vectors=model.encode([c.text for c in chunks])
    elapsed=time.perf_counter()-started
    q=model.encode([query],query=True)[0]
    hits=exact_search(q,vectors,[c.id for c in chunks])
    report['embeddings'].append(dict(source=config['source'],dimensions=int(vectors.shape[1]),load_seconds=load_seconds,
         encode_seconds=elapsed,chunks_per_second=len(chunks)/elapsed,process_rss_bytes=psutil.Process().memory_info().rss,
         top_ids=[h.chunk_id for h in hits],unit_norms=bool(np.allclose(np.linalg.norm(vectors,axis=1),1,atol=1e-5))))
    del model
reranker=LocalReranker(settings['reranker'])
rows=[]
for batch_size in (1,2,8):
    started=time.perf_counter()
    reranked=reranker.rerank(query,hits,assistant.chunks,batch_size)
    elapsed=time.perf_counter()-started
    repeated=reranker.rerank(query,hits,assistant.chunks,batch_size)
    rows.append(dict(batch_size=batch_size,seconds=elapsed,scores=[h.model_dump() for h in reranked],
                     repeated_order_equal=[h.chunk_id for h in reranked]==[h.chunk_id for h in repeated]))
report['reranker']=dict(source=settings['reranker']['source'],score_type='logit',runs=rows)
(ROOT/'evidence/model_smoke.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
