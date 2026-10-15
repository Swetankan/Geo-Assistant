"""Fit-only calibration; confidence estimates top-passage relevance."""
import numpy as np
from evalsuite.metrics import log_loss, choose_threshold


def sigmoid(logits,temperature=1):
    if temperature<=0:
        raise ValueError('Positive temperature required')
    return 1/(1+np.exp(-np.clip(np.asarray(logits,dtype=float)/temperature,-700,700)))


def fit_temperature(scores,labels,split='fit',grid=(.5,.75,1,1.5,2,2.5,3)):
    if split!='fit':
        raise ValueError('Calibration training requires fit split')
    return min(grid,key=lambda t:(log_loss(sigmoid(scores,t),labels),t))


def answer_agreement(answers):
    """Automated proxy: majority fraction of normalized answer + citation-ID sets."""
    from collections import Counter
    signatures=[(' '.join(a['answer'].casefold().split()),tuple(sorted(c['chunk_id'] for c in a['citations']))) for a in answers]
    return max(Counter(signatures).values())/len(signatures) if signatures else 0


class LogisticCalibrator:
    temperature=1.0
    def fit(self,features,labels,split='fit',iterations=2000,learning_rate=.1):
        if split!='fit':
            raise ValueError('Fit split only')
        x=np.asarray(features,dtype=float)
        y=np.asarray(labels,dtype=float)
        if x.ndim!=2 or len(x)!=len(y) or not len(y) or not np.isfinite(x).all() or not np.isin(y,[0,1]).all():
            raise ValueError('Invalid calibration data')
        self.mean=x.mean(axis=0)
        self.scale=np.maximum(x.std(axis=0),1e-8)
        z=np.column_stack([np.ones(len(x)),(x-self.mean)/self.scale])
        self.weights=np.zeros(z.shape[1])
        for _ in range(iterations):
            gradient=z.T@(sigmoid(z@self.weights)-y)/len(y)
            gradient[1:]+=.01*self.weights[1:]
            self.weights-=learning_rate*gradient
        self.threshold=choose_threshold(self.predict(x),y)
        return self

    def predict(self,features):
        x=np.asarray(features,dtype=float)
        z=np.column_stack([np.ones(len(x)),(x-self.mean)/self.scale])
        return sigmoid(z@self.weights)

    @classmethod
    def load(cls,path):
        import json
        from pathlib import Path
        data=json.loads(Path(path).read_text())
        model=cls()
        model.mean=np.asarray(data['mean'],dtype=float)
        model.scale=np.asarray(data['scale'],dtype=float)
        model.weights=np.asarray(data['weights'],dtype=float)
        model.temperature=float(data['temperature'])
        model.threshold=data['threshold']
        if model.temperature<=0 or np.any(model.scale<=0) or not np.isfinite(model.weights).all():
            raise ValueError('Invalid saved calibration parameters')
        return model
