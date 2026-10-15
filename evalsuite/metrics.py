"""Original metrics. Grade >=1 is relevant; unjudged=0; gain=2**grade-1.

Duplicate retrieved IDs count once at their first rank. Empty relevance returns
zero recall/nDCG. Precision uses k, including unfilled result slots.
"""
import math
import numpy as np


def unique(ranking):
    return list(dict.fromkeys(ranking))


def precision_at_k(ranking, judgments, k):
    if k <= 0:
        raise ValueError("k must be positive")
    return sum(judgments.get(x, 0) >= 1 for x in unique(ranking)[:k]) / k


def recall_at_k(ranking, judgments, k):
    if k <= 0:
        raise ValueError("k must be positive")
    total = sum(v >= 1 for v in judgments.values())
    return sum(judgments.get(x, 0) >= 1 for x in unique(ranking)[:k]) / total if total else 0.0


def reciprocal_rank(ranking, judgments):
    return next((1 / i for i, x in enumerate(unique(ranking), 1) if judgments.get(x, 0) >= 1), 0.0)


def mrr(rankings, judgments):
    if len(rankings) != len(judgments):
        raise ValueError("rankings and judgments must align")
    return sum(reciprocal_rank(r, j) for r, j in zip(rankings, judgments)) / len(rankings) if rankings else 0.0


def ndcg_at_k(ranking, judgments, k):
    if k <= 0 or any(v not in (0, 1, 2) for v in judgments.values()):
        raise ValueError("positive k and grades 0/1/2 required")
    def dcg(grades):
        return sum((2 ** g - 1) / math.log2(i + 2) for i, g in enumerate(grades))
    ideal = dcg(sorted(judgments.values(), reverse=True)[:k])
    return dcg([judgments.get(x, 0) for x in unique(ranking)[:k]]) / ideal if ideal else 0.0


def _validate_probabilities(probabilities, labels):
    p, y = np.asarray(probabilities, dtype=float), np.asarray(labels, dtype=float)
    if p.ndim != 1 or p.shape != y.shape or not len(p):
        raise ValueError("nonempty aligned one-dimensional arrays required")
    if not np.all(np.isfinite(p)) or np.any((p < 0) | (p > 1)) or not np.all(np.isin(y, [0, 1])):
        raise ValueError("probabilities must be finite in [0,1], labels binary")
    return p, y


def reliability(probabilities, labels, bins=5):
    p, y = _validate_probabilities(probabilities, labels)
    if bins <= 0:
        raise ValueError("bins must be positive")
    assignments = np.minimum((p * bins).astype(int), bins - 1)
    rows = []
    for i in range(bins):
        mask = assignments == i
        rows.append(dict(lower=i/bins, upper=(i+1)/bins, count=int(mask.sum()),
                         confidence=float(p[mask].mean()) if mask.any() else None,
                         accuracy=float(y[mask].mean()) if mask.any() else None))
    return rows


def ece(probabilities, labels):
    rows = reliability(probabilities, labels)
    return sum(r['count'] * abs(r['confidence']-r['accuracy']) for r in rows if r['count']) / len(labels)


def brier_score(probabilities, labels):
    p, y = _validate_probabilities(probabilities, labels)
    return float(np.mean((p-y)**2))


def log_loss(probabilities, labels):
    p, y = _validate_probabilities(probabilities, labels)
    p = np.clip(p, 1e-15, 1-1e-15)
    return float(-np.mean(y*np.log(p)+(1-y)*np.log1p(-p)))


def coverage_accuracy(probabilities, labels, threshold):
    p, y = _validate_probabilities(probabilities, labels)
    if not 0 <= threshold <= 1:
        raise ValueError("threshold outside [0,1]")
    mask = p >= threshold
    return dict(threshold=threshold, answered=int(mask.sum()), coverage=float(mask.mean()),
                accuracy=float(y[mask].mean()) if mask.any() else None)


def choose_threshold(probabilities, labels, target=0.9):
    """Call on fit data only. None means no nonzero coverage meets the target."""
    _validate_probabilities(probabilities, labels)
    candidates = [coverage_accuracy(probabilities, labels, float(t)) for t in sorted(set(probabilities))]
    eligible = [r for r in candidates if r['answered'] and r['accuracy'] >= target]
    return max(eligible, key=lambda r: (r['coverage'], -r['threshold']))['threshold'] if eligible else None


def entity_scores(predicted, gold, relaxed=False):
    """Maximum bipartite one-to-one matching, not greedy overlap matching.

    Input records: type, document_id, page, start, end. Both sides must use the
    same document/page coordinate system (convert chunk-local spans first).
    """
    results = {}
    for kind in sorted({x['type'] for x in predicted + gold}):
        pp = [x for x in predicted if x['type'] == kind]
        gg = [x for x in gold if x['type'] == kind]
        adjacency = []
        for p in pp:
            compatible = []
            for j, g in enumerate(gg):
                same = (p['document_id'], p.get('page')) == (g['document_id'], g.get('page'))
                span = max(p['start'], g['start']) < min(p['end'], g['end']) if relaxed else (p['start'],p['end']) == (g['start'],g['end'])
                if same and span:
                    compatible.append(j)
            adjacency.append(compatible)
        matches = {}
        def augment(i, visited):
            for j in adjacency[i]:
                if j in visited:
                    continue
                visited.add(j)
                if j not in matches or augment(matches[j], visited):
                    matches[j] = i
                    return True
            return False
        tp = sum(augment(i, set()) for i in range(len(pp)))
        precision, recall = tp/len(pp) if pp else 0.0, tp/len(gg) if gg else 0.0
        results[kind] = dict(tp=tp, fp=len(pp)-tp, fn=len(gg)-tp, precision=precision,
                             recall=recall, f1=2*precision*recall/(precision+recall) if precision+recall else 0.0)
    return results
