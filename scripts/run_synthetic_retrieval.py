"""Run local synthetic retrieval and cross-encoder comparisons only."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.cli import import_corpus
from app.models import LocalEmbeddings, LocalReranker
from app.pipeline import Assistant
from app.schemas import Chunk, Entity, Relation, RankedResult
from app.settings import ROOT, load_settings
from evalsuite.datasets import load_questions
from evalsuite.retrieval import evaluate
from ingest.extract import RuleExtractor
from ingest.relations import build_relations
from retrieve.graph import EvidenceGraph
from retrieve.ranking import LocalBM25


def read(path, model):
    return [model.model_validate_json(line) for line in path.read_text(encoding='utf-8').splitlines() if line]


def main():
    corpus = ROOT / 'evalsuite/fixtures/corpus'
    data = ROOT / 'data/private/corpus'
    import_corpus(corpus, data)
    chunks, entities, relations = (read(data / (name + '.jsonl'), model) for name, model in
                                   [('chunks', Chunk), ('entities', Entity), ('relations', Relation)])
    settings = load_settings()
    embedding = LocalEmbeddings(settings['embedding_models'][0])
    vectors = {c.id: v for c, v in zip(chunks, embedding.encode([c.text for c in chunks]))}
    reranker = LocalReranker(settings['reranker'])
    class Store:
        def __init__(self): self.lexical = LocalBM25(chunks)
        def search(self, query, vector=None, k=20, filters=None, num_candidates=50):
            if vector is None:
                return self.lexical.search(query, k, filters.accepts if filters else None)
            import numpy as np
            scored = [(float(np.dot(vector, vectors[c.id])), c.id) for c in chunks if not filters or filters.accepts(c)]
            return [RankedResult(chunk_id=i, score=s, sources=['exact_vector_synthetic']) for s, i in sorted(scored, key=lambda x: (-x[0], x[1]))[:k]]
    class Embed:
        def encode(self, texts, query=False): return embedding.encode(texts, query=query)
    class Rerank:
        def rerank(self, query, hits, chunk_map, batch_size=16): return reranker.rerank(query, hits, chunk_map, batch_size)
    graph = EvidenceGraph(entities, relations)
    class InertLLM: pass
    assistant = Assistant(chunks, entities, graph, settings, Store(), Embed(), Rerank(), InertLLM())
    questions = load_questions(ROOT / 'evalsuite/retrieval_judgments.jsonl')
    output = ROOT / 'evidence/synthetic_assessment'
    output.mkdir(exist_ok=True)
    scored = []
    for constant in (20, 60, 100):
        tune = [q for q in questions if q.split == 'tune']
        rows = evaluate(assistant, tune, constant)
        scores = [r['ndcg'] for r in rows if r['mode'] == 'graph_hybrid' and r['k'] == 5]
        scored.append((sum(scores) / len(scores), constant, rows))
    best = sorted(scored, key=lambda x: (-x[0], x[1]))[0]
    holdout = evaluate(assistant, [q for q in questions if q.split == 'holdout'], best[1])
    (output / 'retrieval_results.json').write_text(json.dumps({'synthetic': True, 'tune': best[2], 'holdout': holdout}, indent=2), encoding='utf-8')
    summary = {'synthetic': True, 'tuned_rrf_constant': best[1], 'tune_graph_hybrid_ndcg5': best[0], 'holdout_at_5': {}}
    for mode in ('keyword', 'vector', 'hybrid', 'graph_hybrid'):
        rows = [r for r in holdout if r['mode'] == mode and r['k'] == 5]
        summary['holdout_at_5'][mode] = {metric: sum(r[metric] for r in rows) / len(rows) for metric in ('precision', 'recall', 'mrr', 'ndcg')}
    (output / 'retrieval_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    # Cache each cross-encoder call once per query/N; one selected batch setting.
    rr = []
    for q in [q for q in questions if q.split == 'holdout'][:2]:
        candidates, *_ = assistant.retrieve(q.query, assistant.query_entities(q.query), __import__('retrieve.filters', fromlist=['QueryFilter']).QueryFilter())
        for n in (10, 20, 50):
            before = candidates[:n]
            import time
            started = time.perf_counter()
            after = reranker.rerank(q.query, before, assistant.chunks, batch_size=16)
            elapsed = time.perf_counter() - started
            from evalsuite.metrics import ndcg_at_k, reciprocal_rank
            bi, ai = [h.chunk_id for h in before], [h.chunk_id for h in after]
            rr.append({'id': q.id, 'split': q.split, 'n': n, 'batch_size': 16,
                       'before_ndcg5': ndcg_at_k(bi, q.judgments, 5), 'after_ndcg5': ndcg_at_k(ai, q.judgments, 5),
                       'before_mrr': reciprocal_rank(bi, q.judgments), 'after_mrr': reciprocal_rank(ai, q.judgments),
                       'extra_seconds': elapsed, 'synthetic': True, 'repeat_order_equal': None})
    (output / 'reranker_results.json').write_text(json.dumps({'synthetic': True, 'results': rr}, indent=2), encoding='utf-8')
    (output / 'ann_results.json').write_text(json.dumps({'synthetic': True, 'approximate': 'not run: Elasticsearch is not available', 'exact': 'local embeddings produced; ANN recall not claimed'}, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__': main()
