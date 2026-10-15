"""Compute transparent, synthetic-only calibration metrics over deterministic local signals."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.settings import ROOT
from evalsuite.datasets import load_questions
from evalsuite.metrics import reliability, ece, brier_score, coverage_accuracy
from retrieve.confidence import fit_temperature, sigmoid


def main():
    questions = load_questions(ROOT / 'evalsuite/calibration_questions.jsonl', 'calibration')
    # Synthetic benchmark-only fixed score signal; no live reranker logits or calibrated claims.
    scores = [((int(q.id[-2:]) * 17) % 31 - 15) / 10 for q in questions]
    labels = [int(max(q.judgments.values(), default=0) >= 1) for q in questions]
    fit = [i for i, q in enumerate(questions) if q.split == 'fit']
    test = [i for i, q in enumerate(questions) if q.split == 'test']
    temperature = fit_temperature([scores[i] for i in fit], [labels[i] for i in fit], split='fit')
    raw = sigmoid([scores[i] for i in test])
    scaled = sigmoid([scores[i] for i in test], temperature)
    thresholds = [0.3, 0.5, 0.7, 0.8, 0.9]
    result = {'synthetic': True, 'status': 'illustrative only; deterministic surrogate scores, not reranker observations',
              'fit_count': len(fit), 'test_count': len(test), 'temperature_fit_only': temperature,
              'raw': {'ece': ece(raw, [labels[i] for i in test]), 'brier': brier_score(raw, [labels[i] for i in test]),
                      'reliability': reliability(raw, [labels[i] for i in test])},
              'scaled': {'ece': ece(scaled, [labels[i] for i in test]), 'brier': brier_score(scaled, [labels[i] for i in test]),
                         'reliability': reliability(scaled, [labels[i] for i in test])},
              'coverage': [coverage_accuracy(scaled, [labels[i] for i in test], t) for t in thresholds]}
    path = ROOT / 'evidence/synthetic_assessment/calibration_results.json'
    path.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
