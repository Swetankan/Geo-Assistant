"""Deterministic original vector search, RRF, and synthetic-only BM25 backend."""
import math
import re
from collections import Counter
import numpy as np
from app.schemas import RankedResult


def tokens(text):
    return re.findall(r'\w+',text.casefold())


def exact_search(query, vectors, ids, k=10):
    matrix, query = np.asarray(vectors,dtype=float), np.asarray(query,dtype=float)
    if k <= 0 or matrix.ndim != 2 or query.shape != (matrix.shape[1],) or len(ids) != len(matrix):
        raise ValueError('Invalid vector dimensions or k')
    if len(set(ids)) != len(ids) or not np.isfinite(matrix).all() or not np.isfinite(query).all():
        raise ValueError('IDs must be unique and vectors finite')
    norms = np.linalg.norm(matrix,axis=1)*np.linalg.norm(query)
    scores = np.divide(matrix@query,norms,out=np.zeros(len(matrix)),where=norms>0)
    return [RankedResult(chunk_id=ids[i],score=float(scores[i]),sources=['exact_vector'])
            for i in sorted(range(len(ids)),key=lambda i:(-scores[i],ids[i]))[:k]]


def rrf(rankings, constant=60, limit=50):
    if constant < 0 or limit <= 0:
        raise ValueError('Invalid RRF parameters')
    totals, sources = {}, {}
    for ranking in rankings:
        seen = set()
        for hit in ranking:
            if hit.chunk_id in seen:
                continue
            seen.add(hit.chunk_id)
            totals[hit.chunk_id] = totals.get(hit.chunk_id,0)+1/(constant+len(seen))
            sources.setdefault(hit.chunk_id,set()).update(hit.sources)
    return [RankedResult(chunk_id=i,score=s,sources=sorted(sources[i]))
            for i,s in sorted(totals.items(),key=lambda x:(-x[1],x[0]))[:limit]]


class LocalBM25:
    """Smoke-test backend only. Production keyword queries use Elasticsearch."""
    def __init__(self,chunks):
        self.chunks = {c.id:c for c in chunks}
        self.counts = {c.id:Counter(tokens(c.text)) for c in chunks}
        self.df = Counter(t for c in self.counts.values() for t in c)
        self.average = sum(sum(c.values()) for c in self.counts.values())/max(1,len(chunks))

    def search(self,query,k=50,predicate=lambda c:True):
        hits = []
        for id_,count in self.counts.items():
            if not predicate(self.chunks[id_]):
                continue
            length = sum(count.values())
            score = 0.0
            for term in set(tokens(query)):
                frequency = count[term]
                idf = math.log(1+(len(self.chunks)-self.df[term]+.5)/(self.df[term]+.5))
                score += idf*frequency*2.2/(frequency+1.2*(.25+.75*length/max(self.average,1)))
            if score > 0:
                hits.append(RankedResult(chunk_id=id_,score=score,sources=['synthetic_bm25']))
        return sorted(hits,key=lambda h:(-h.score,h.chunk_id))[:k]
