import numpy as np
from .model import sigmoid
PRECISION=1.0

def calibrate(logits,acquired_indices,acquired_y,prior_log_odds,precision=PRECISION):
    """Fit only intercepts, sharing the SOURCE ability prior between candidates.

    z = raw candidate logits; d_i = z_i - mean(z_acquired).
    alpha minimizes acquired NLL + precision/2*(alpha-source_log_odds)^2.
    p_i = sigmoid(alpha+d_i). Constant shifts in candidate logits cancel exactly.
    Only acquired labels are accepted. No held-out target outcomes are an input.
    """
    logits=np.asarray(logits);acquired_y=np.asarray(acquired_y);prior=np.asarray(prior_log_odds)
    if len(acquired_indices)!=7 or acquired_y.shape!=(7,logits.shape[1]):raise ValueError('Exactly seven observations per configuration required')
    if not set(np.unique(acquired_y))<={0,1} or precision<=0:raise ValueError('Binary labels and positive precision required')
    center=logits[acquired_indices].mean(axis=0);offsets=logits-center[None,:]
    lo=prior-20;hi=prior+20
    for _ in range(70):
        mid=(lo+hi)/2
        grad=(sigmoid(mid[None,:]+offsets[acquired_indices])-acquired_y).sum(axis=0)+precision*(mid-prior)
        hi=np.where(grad>0,mid,hi);lo=np.where(grad<=0,mid,lo)
    alpha=(lo+hi)/2
    gradient=(sigmoid(alpha[None,:]+offsets[acquired_indices])-acquired_y).sum(axis=0)+precision*(alpha-prior)
    assert np.max(np.abs(gradient))<1e-10
    return sigmoid(alpha[None,:]+offsets),{'alpha':alpha.tolist(),'prior_log_odds':prior.tolist(),
        'raw_logit_center':center.tolist(),'raw_candidate_intercept_shift':(alpha-center).tolist(),
        'n_labels_per_configuration':7,'successes':acquired_y.sum(axis=0).astype(int).tolist(),
        'failures':(7-acquired_y.sum(axis=0)).astype(int).tolist(),'prior_precision':precision,
        'maximum_gradient':float(np.max(np.abs(gradient)))}
