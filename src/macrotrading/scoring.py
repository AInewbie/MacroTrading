"""WATCH is a research ranking, never a probability or position size."""
from .validation import number
DEFAULT_WEIGHTS={'P':25.,'F':25.,'M':20.,'C':20.,'X':10.,'R':-10.}
COMPONENT_VALUES={k:{0.,.5,1.} for k in 'PFMCX'}
def validate_components(components):
    if set(components)!=set('PFMCXR'): raise ValueError('WATCH requires exactly P,F,M,C,X,R')
    for k,v in components.items():
        number(v,k)
        if v not in ({0.,1.,2.} if k=='R' else {0.,.5,1.}): raise ValueError(f'invalid {k}={v}')
def validate_weights(weights):
    if set(weights)!=set(DEFAULT_WEIGHTS): raise ValueError('weights require P,F,M,C,X,R')
    for k,v in weights.items(): number(v,k,-50 if k=='R' else 0,0 if k=='R' else 100)
    if abs(sum(weights[k] for k in 'PFMCX')-100)>1e-9: raise ValueError('positive WATCH weights must sum to 100')
def watch_v1_score(components,weights=None):
    validate_components(components);weights=weights or DEFAULT_WEIGHTS;validate_weights(weights)
    return max(0.,min(100.,sum(weights[k]*components[k] for k in weights)))
def score_band(score):
    return 'Exploratory watch' if score<45 else 'Research review' if score<70 else 'Priority research'
