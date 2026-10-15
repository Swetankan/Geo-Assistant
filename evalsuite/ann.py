import time
import numpy as np
from retrieve.ranking import exact_search


def compare_ann(store,index,vectors,ids,queries,query_vectors):
    """ANN recall measures overlap with exact neighbors, not graded relevance."""
    store.assert_index(index)
    if len(queries)!=len(query_vectors) or len(queries)!=20:
        raise ValueError('Exactly 20 aligned query vectors required')
    rows=[]
    for query,vector in zip(queries,query_vectors):
        started=time.perf_counter()
        exact=exact_search(vector,vectors,ids,k=10)
        exact_seconds=time.perf_counter()-started
        expected={h.chunk_id for h in exact}
        for candidates in (20,50,100):
            started=time.perf_counter()
            data=store.request('POST',f'/{index}/_search',json={'size':10,'knn':{'field':'embedding','query_vector':np.asarray(vector).tolist(),'k':10,'num_candidates':candidates}})
            elapsed=time.perf_counter()-started
            actual={h['_id'] for h in data['hits']['hits']}
            rows.append(dict(query_id=query.id,num_candidates=candidates,ann_recall_at_10=len(expected&actual)/len(expected) if expected else 0,
                             ann_seconds=elapsed,exact_seconds=exact_seconds,exact_count=len(expected)))
    return rows
