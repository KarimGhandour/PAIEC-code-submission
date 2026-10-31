"""Six-budget Brier ALC, separately labeled from two-budget research metrics."""
import math
BUDGETS=(0,1,3,7,15,31)
WEIGHTS=(.1,.2,.2,.2,.2,.1)
def brier_alc(scores):
    if set(scores)!=set(BUDGETS):raise ValueError('All six budgets required')
    if any(not math.isfinite(scores[b]) or not 0<=scores[b]<=1 for b in BUDGETS):raise ValueError('Invalid Brier')
    return sum(w*scores[b] for b,w in zip(BUDGETS,WEIGHTS))
