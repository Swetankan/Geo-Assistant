import json
import numpy as np
import pytest
from evalsuite.datasets import load_questions,inspect_jsonl
from retrieve.confidence import LogisticCalibrator,fit_temperature,answer_agreement
from evalsuite.calibration import calibrate


def test_split_validation(tmp_path):
    path=tmp_path/'queries.jsonl'
    path.write_text(json.dumps({'id':'q','query':'school','split':'tune','judgments':{'c':2},'synthetic':True})+'\n')
    assert inspect_jsonl(path)['rows']==1
    with pytest.raises(ValueError,match='Expected 20'):
        load_questions(path)
    assert len(load_questions(path,require_assessment_counts=False))==1


def test_fit_only_calibration_and_persistence(tmp_path):
    x=np.array([[.1,0,0,0],[.2,.1,0,.2],[.8,1,1,.8],[.9,2,1,1]])
    y=[0,0,1,1]
    with pytest.raises(ValueError):
        LogisticCalibrator().fit(x,y,split='test')
    with pytest.raises(ValueError):
        fit_temperature([-2,-1,1,2],y,split='test')
    model,report=calibrate(x,[-2,-1,1,2],y,x,[-2,-1,1,2],y,tmp_path)
    loaded=LogisticCalibrator.load(tmp_path/'calibrator.json')
    assert np.allclose(model.predict(x),loaded.predict(x))
    assert report['count']==4 and report['chosen_threshold_result']['answered']>0
    with pytest.raises(FileExistsError):
        calibrate(x,[-2,-1,1,2],y,x,[-2,-1,1,2],y,tmp_path)


def test_agreement_proxy():
    a={'answer':'Forty seats','citations':[{'chunk_id':'a'}]}
    b={'answer':'40 seats','citations':[{'chunk_id':'a'}]}
    assert answer_agreement([a,a,a,b,b])==.6
    assert answer_agreement([])==0
