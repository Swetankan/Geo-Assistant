import json
from pathlib import Path
import numpy as np
from evalsuite.metrics import reliability,ece,brier_score,log_loss,coverage_accuracy,choose_threshold
from retrieve.confidence import LogisticCalibrator,fit_temperature,sigmoid


def calibrate(fit_features,fit_scores,fit_labels,test_features,test_scores,test_labels,output):
    """Caller supplies features from fixed retrieval and top-passage grade>=1 labels.

    Write fit parameters before looking at test metrics. No holdout tuning.
    """
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    lock=output/'calibrator.json'
    if lock.exists():
        raise FileExistsError('Calibration already fitted in this run directory')
    temperature=fit_temperature(fit_scores,fit_labels)
    fit_x=np.asarray(fit_features,dtype=float).copy()
    fit_x[:,0]=sigmoid(fit_scores,temperature)
    model=LogisticCalibrator().fit(fit_x,fit_labels)
    model.temperature=temperature
    lock.write_text(json.dumps(dict(mean=model.mean.tolist(),scale=model.scale.tolist(),weights=model.weights.tolist(),
                                   temperature=temperature,threshold=model.threshold,label='top passage grade >= 1'),indent=2))
    test_x=np.asarray(test_features,dtype=float).copy()
    test_x[:,0]=sigmoid(test_scores,temperature)
    probabilities=model.predict(test_x)
    report={'count':len(test_labels),'reliability':reliability(probabilities,test_labels),
            'ece':ece(probabilities,test_labels),'brier':brier_score(probabilities,test_labels),'log_loss':log_loss(probabilities,test_labels),
            'reranker_ece_before':ece(sigmoid(test_scores),test_labels),'reranker_ece_after':ece(sigmoid(test_scores,temperature),test_labels),
            'threshold_sweep':[coverage_accuracy(probabilities,test_labels,t) for t in (.5,.6,.7,.8,.9)],
            'chosen_threshold_result':coverage_accuracy(probabilities,test_labels,model.threshold) if model.threshold is not None else None}
    (output/'calibration_results.json').write_text(json.dumps(report,indent=2))
    return model,report
