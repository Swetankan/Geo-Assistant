"""Explicit canonical evaluation schema. Inspect and adapt supplied files first.

These contracts are project-owned; missing assessor files have not been inspected.
No loader silently guesses field meanings or query partitions.
"""
import json
from pathlib import Path
from typing import Literal
from pydantic import Field
from app.schemas import StrictModel


class RetrievalQuestion(StrictModel):
    id: str
    query: str
    split: Literal['tune','holdout']
    judgments: dict[str,int]
    category: Literal['exact_identifier','paraphrase','multi_hop','list','table'] | None = None
    synthetic: bool = False


class CalibrationQuestion(StrictModel):
    id: str
    query: str
    split: Literal['fit','test']
    judgments: dict[str,int]
    synthetic: bool = False


def inspect_jsonl(path):
    rows=[json.loads(line) for line in Path(path).read_text(encoding='utf-8-sig').splitlines() if line.strip()]
    return {'rows':len(rows),'keys':sorted({k for row in rows for k in row}),
            'value_types':{k:sorted({type(row[k]).__name__ for row in rows if k in row}) for k in sorted({k for row in rows for k in row})}}


def load_questions(path,kind='retrieval',require_assessment_counts=True):
    model=RetrievalQuestion if kind=='retrieval' else CalibrationQuestion
    rows=[model.model_validate(json.loads(line)) for line in Path(path).read_text(encoding='utf-8-sig').splitlines() if line.strip()]
    if not rows or len({r.id for r in rows})!=len(rows):
        raise ValueError('Questions must be nonempty with unique IDs')
    if any(v not in (0,1,2) for row in rows for v in row.judgments.values()):
        raise ValueError('Only grades 0,1,2 are valid')
    if len({r.synthetic for r in rows})!=1:
        raise ValueError('Do not mix synthetic and assessment questions')
    if require_assessment_counts:
        expected={'tune':20,'holdout':10} if kind=='retrieval' else {'fit':25,'test':15}
        for split,count in expected.items():
            if sum(r.split==split for r in rows)!=count:
                raise ValueError(f'Expected {count} questions in {split}')
    return rows
