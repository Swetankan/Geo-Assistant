"""Tuning and holdout evaluation using original metrics; no fabricated labels."""
import json
import time
from pathlib import Path
from evalsuite.metrics import precision_at_k,recall_at_k,reciprocal_rank,ndcg_at_k
from retrieve.filters import QueryFilter

MODES=('keyword','vector','hybrid','graph_hybrid')
KS=(1,3,5,10,20)


def evaluate(assistant,questions,rrf_constant):
    original=dict(assistant.settings)
    assistant.settings={**original,'rrf_constant':rrf_constant,'rerank_n':max(50,original['rerank_n'])}
    records=[]
    try:
        for question in questions:
            for mode in MODES:
                started=time.perf_counter()
                hits,*_=assistant.retrieve(question.query,assistant.query_entities(question.query),QueryFilter(),mode)
                elapsed=time.perf_counter()-started
                ranking=[h.chunk_id for h in hits]
                for k in KS:
                    records.append(dict(id=question.id,split=question.split,category=question.category,
                        mode=mode,k=k,precision=precision_at_k(ranking,question.judgments,k),
                        recall=recall_at_k(ranking,question.judgments,k),mrr=reciprocal_rank(ranking,question.judgments),
                        ndcg=ndcg_at_k(ranking,question.judgments,k),latency_seconds=elapsed,
                        chunk_ids=ranking[:k],synthetic=question.synthetic))
    finally:
        assistant.settings=original
    return records


def tune_then_holdout(assistant,questions,output,constants=(20,60,100)):
    """Tune ONE parameter on graph_hybrid nDCG@5; persist choice before holdout."""
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    lock=output/'frozen_choice.json'
    if lock.exists():
        raise FileExistsError('Existing frozen experiment; use a new run directory')
    tune=[q for q in questions if q.split=='tune']
    holdout=[q for q in questions if q.split=='holdout']
    if not tune or not holdout:
        raise ValueError('Both tune and holdout required')
    scored=[]
    for constant in constants:
        rows=evaluate(assistant,tune,constant)
        scores=[r['ndcg'] for r in rows if r['mode']=='graph_hybrid' and r['k']==5]
        scored.append((sum(scores)/len(scores),constant,rows))
    best=sorted(scored,key=lambda r:(-r[0],r[1]))[0]
    lock.write_text(json.dumps({'parameter':'rrf_constant','value':best[1],'objective':'tune graph_hybrid nDCG@5',
                               'tune_ids':[q.id for q in tune]},indent=2),encoding='utf-8')
    final=evaluate(assistant,holdout,best[1])
    (output/'retrieval_results.json').write_text(json.dumps({'synthetic':questions[0].synthetic,
         'tune':best[2],'holdout':final,'manual_categories':False},indent=2),encoding='utf-8')
    return best[1],final


def reranker_comparison(assistant,questions,operational_n=20,batch_sizes=(1,8,16)):
    """N comparisons on holdout are evaluation, not hyperparameter selection.

    The declared operational N remains fixed regardless of this report.
    """
    rows=[]
    original=assistant.settings
    try:
        assistant.settings={**original,'rerank_n':50}
        for q in questions:
            candidates,*_=assistant.retrieve(q.query,assistant.query_entities(q.query),QueryFilter())
            for n in (10,20,50):
                for batch in batch_sizes:
                    before=candidates[:n]
                    started=time.perf_counter()
                    after=assistant.reranker.rerank(q.query,before,assistant.chunks,batch)
                    elapsed=time.perf_counter()-started
                    repeated=assistant.reranker.rerank(q.query,before,assistant.chunks,batch)
                    bi,ai=[h.chunk_id for h in before],[h.chunk_id for h in after]
                    rows.append(dict(id=q.id,split=q.split,n=n,actual_candidates=len(before),batch_size=batch,
                       before_ndcg5=ndcg_at_k(bi,q.judgments,5),after_ndcg5=ndcg_at_k(ai,q.judgments,5),
                       before_mrr=reciprocal_rank(bi,q.judgments),after_mrr=reciprocal_rank(ai,q.judgments),
                       extra_seconds=elapsed,repeat_order_equal=ai==[h.chunk_id for h in repeated],
                       operational_n=operational_n,selection_policy='predeclared; report does not tune holdout'))
    finally:
        assistant.settings=original
    return rows
