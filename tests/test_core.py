import math
import pytest
from pydantic import ValidationError
from app.schemas import Entity, GeoPoint, Span, stable_id
from ingest.documents import chunk_text
from evalsuite.metrics import *


def test_schema_and_ids():
    assert stable_id('doc', {'b': 2, 'a': 1}) == stable_id('doc', {'a': 1, 'b': 2})
    for value in [dict(start=1,end=1),dict(start=-1,end=2),dict(start=0,end=1.5)]:
        with pytest.raises(ValidationError):
            Span(**value)
    with pytest.raises(ValidationError):
        GeoPoint(lat=91,lon=0)
    with pytest.raises(ValidationError):
        Entity(id='x',type='School',canonical_name='X',attributes={'count':'10'})


def test_chunks_keep_unicode_and_newlines():
    text = 'বিদ্যালয়\r\nSchool ABC ' * 20
    chunks = list(chunk_text('d','s',None,text,40,8))
    assert all(c.text == text[c.start:c.end] for c in chunks)
    assert chunks[-1].end == len(text)
    assert chunks == list(chunk_text('d','s',None,text,40,8))
    with pytest.raises(ValueError):
        list(chunk_text('d','s',None,text,10,10))


def test_ranking_metrics():
    j = {'a': 2, 'b': 1, 'c': 0}
    r = ['c','b','a']
    assert precision_at_k(r,j,2) == .5
    assert recall_at_k(r,j,2) == .5
    assert reciprocal_rank(r,j) == .5
    assert mrr([r,[]],[j,j]) == .25
    assert ndcg_at_k(r,j,3) == pytest.approx((1/math.log2(3)+3/2)/(3+1/math.log2(3)))
    assert recall_at_k(['a'],{},5) == 0
    assert ndcg_at_k([],{},5) == 0
    assert precision_at_k(['a','a'],j,2) == .5


def test_one_to_one_matching():
    g = [dict(type='School',document_id='d',start=0,end=3)]
    assert entity_scores(g+g,g)['School']['precision'] == .5
    p = [dict(type='School',document_id='d',start=2,end=5)]
    assert entity_scores(p,g,True)['School']['tp'] == 1
    assert entity_scores(p,g,False)['School']['tp'] == 0
    # A greedy matcher fails here: first prediction can match both gold spans.
    g = [dict(type='School',document_id='d',start=0,end=2), dict(type='School',document_id='d',start=3,end=5)]
    p = [dict(type='School',document_id='d',start=0,end=5), dict(type='School',document_id='d',start=0,end=2)]
    assert entity_scores(p,g,True)['School']['tp'] == 2


def test_calibration_boundaries():
    assert [r['count'] for r in reliability([0,.2,.4,.6,.8,1],[0,0,0,1,1,1])] == [1,1,1,1,2]
    assert brier_score([0,1],[0,1]) == 0
    assert ece([0,1],[0,1]) == 0
    assert log_loss([.5,.5],[0,1]) == pytest.approx(math.log(2))
    assert coverage_accuracy([.2],[0],.9)['accuracy'] is None
    assert choose_threshold([.2,.9],[0,1]) == .9
    assert choose_threshold([.2,.9],[0,0]) is None
    with pytest.raises(ValueError):
        brier_score([float('nan')],[1])
