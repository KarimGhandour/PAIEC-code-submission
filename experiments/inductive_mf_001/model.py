"""Extracted frozen MF-001 numerical functions; encoder is never trained."""
import time,sys,resource
import numpy as np
DIM=16
SEED=20261027
EPOCHS=200
LR=.02
VECTOR_PRECISION=16.
def sigmoid(x):return np.exp(-np.logaddexp(0.,-np.asarray(x)))

def logit(x):x=np.clip(np.asarray(x),1e-9,1-1e-9);return np.log(x)-np.log1p(-x)

def metrics(y,p):
    y=np.asarray(y);p=np.clip(np.asarray(p),1e-9,1-1e-9)
    return {'brier':float(np.mean((p-y)**2)),'nll':float(np.mean(-y*np.log(p)-(1-y)*np.log1p(-p)))}

def ranks(x):
    x=np.asarray(x);out=np.zeros(len(x));order=np.argsort(x);start=0
    while start<len(x):
        end=start+1
        while end<len(x) and x[order[end]]==x[order[start]]:end+=1
        out[order[start:end]]=(start+end-1)/2;start=end
    return out

def spearman(x,y):
    a,b=ranks(x),ranks(y)
    return None if np.std(a)<1e-10 or np.std(b)<1e-10 else float(np.corrcoef(a,b)[0,1])

def rss_gb():
    scale = 1 if sys.platform == "darwin" else 1024
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * scale / 1e9

def metadata_tokens(subject, foundation):
    return ["model=" + foundation,
            "provider=" + str(subject.get("provider") or "missing").lower(),
            "harness=" + str(subject.get("harness") or "missing").lower(),
            "effort=" + str(subject.get("reasoning_effort") or "missing").lower()]

def metadata_matrix(subjects, foundations, vocabulary=None):
    rows = [metadata_tokens(s, f) for s, f in zip(subjects, foundations)]
    if vocabulary is None:
        vocabulary = sorted({token for row in rows for token in row})
    lookup = {token: j for j, token in enumerate(vocabulary)}
    x = np.zeros((len(rows), len(vocabulary)), dtype=np.float32)
    for i, row in enumerate(rows):
        for token in row:
            if token in lookup:
                x[i, lookup[token]] = 0.5
    return x, vocabulary

def train_factor(x, metadata, families, device):
    """families contains (item row indices, subject row indices, observed y).

    Only passed source/training labels are seen; missing cells never become zero.
    """
    import torch
    from torch import nn
    import torch.nn.functional as F
    start = time.monotonic()
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    torch.set_num_threads(4)
    xt = torch.as_tensor(x, device=device)
    mt = torch.as_tensor(metadata, device=device)
    # Subject capability estimates and metadata initialization use training edges only.
    successes = np.zeros(len(metadata))
    totals = np.zeros(len(metadata))
    tensors = []
    for ii, ss, y in families:
        mask = np.isfinite(y)
        successes[ss] += np.nansum(y, axis=0)
        totals[ss] += mask.sum(axis=0)
        tensors.append((torch.as_tensor(ii, device=device), torch.as_tensor(ss, device=device),
                        torch.as_tensor(np.nan_to_num(y), dtype=torch.float32, device=device),
                        torch.as_tensor(mask, device=device)))
    assert (totals > 0).all()
    subject_prior = logit((successes + 1) / (totals + 2))
    initial_global = float(np.mean(subject_prior))
    initial_bias = np.linalg.solve(metadata.T @ metadata + np.eye(metadata.shape[1]),
                                   metadata.T @ (subject_prior - initial_global))

    class Factor(nn.Module):
        def __init__(self):
            super().__init__()
            self.projection = nn.Linear(768, DIM, bias=False)
            self.system_mapping = nn.Linear(metadata.shape[1], DIM, bias=False)
            self.bias_mapping = nn.Linear(metadata.shape[1], 1, bias=False)
            self.global_bias = nn.Parameter(torch.tensor(initial_global, dtype=torch.float32))
            nn.init.normal_(self.projection.weight, std=0.10)
            nn.init.normal_(self.system_mapping.weight, std=0.05)
            self.bias_mapping.weight.data.copy_(torch.as_tensor(initial_bias[None, :], dtype=torch.float32))

        def components(self, q, m):
            z = F.normalize(self.projection(q), dim=-1, eps=1e-8)
            v = self.system_mapping(m)
            b = self.global_bias + self.bias_mapping(m).squeeze(-1)
            return z, v, b

    model = Factor().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    losses = []
    for epoch in range(EPOCHS):
        optimizer.zero_grad(set_to_none=True)
        z, v, b = model.components(xt, mt)
        family_losses = []
        for ii, ss, yy, mask in tensors:
            logits = z[ii] @ v[ss].T + b[ss]
            family_losses.append(F.binary_cross_entropy_with_logits(logits[mask], yy[mask]))
        bce = torch.stack(family_losses).mean()
        regularization = 0.01 * (v.square().mean() + b.square().mean())
        regularization += 0.001 * (model.projection.weight.square().mean() +
                                  model.system_mapping.weight.square().mean() +
                                  model.bias_mapping.weight.square().mean())
        loss = bce + regularization
        if not torch.isfinite(loss):
            raise RuntimeError("Nonfinite training loss")
        loss.backward()
        optimizer.step()
        if epoch in (0, 49, 99, 199):
            losses.append({"epoch": epoch + 1, "bce": float(bce.detach().cpu()),
                           "regularized_loss": float(loss.detach().cpu())})
    model.eval()
    with torch.inference_mode():
        z, v, b = model.components(xt, mt)
    components = tuple(t.cpu().numpy().astype(np.float64) for t in (z, v, b))
    state = {key: value.detach().cpu() for key, value in model.state_dict().items()}
    info = {"seconds": time.monotonic() - start, "losses": losses,
            "trainable_parameters": sum(p.numel() for p in model.parameters()),
            "training_observations": int(totals.sum()), "peak_rss_gb": rss_gb()}
    return model, state, components, info

def new_subject_components(state, metadata):
    v = metadata @ state["system_mapping.weight"].numpy().T
    b = float(state["global_bias"]) + (metadata @ state["bias_mapping.weight"].numpy().T).ravel()
    return v.astype(float), b.astype(float)

def adapt(z, source_vectors, acquired, acquired_y, prior, vector_precision=VECTOR_PRECISION):
    """17-parameter MAP per subject, only seven labels and frozen item vectors.

    Acquired-vector centering removes candidate constant shifts; all candidates
    share the same SOURCE-only scalar ability prior (ORACLE-GAP-004).
    """
    assert len(acquired) == 7 and acquired_y.shape == (7, len(source_vectors))
    centered = z - z[acquired].mean(axis=0)
    design = np.column_stack([np.ones(len(z)), centered])
    xa = design[acquired]
    preds, records = [], []
    for j, v in enumerate(source_vectors):
        center = np.r_[prior[j], v]
        precision = np.r_[1.0, np.repeat(vector_precision, DIM)]
        beta = center.copy()
        y = acquired_y[:, j]
        def objective(w):
            logits = xa @ w
            return np.sum(np.logaddexp(0, logits) - y * logits) + 0.5 * np.sum(precision * (w - center) ** 2)
        for _ in range(50):
            p = sigmoid(xa @ beta)
            gradient = xa.T @ (p - y) + precision * (beta - center)
            hessian = xa.T @ ((p * (1-p))[:, None] * xa) + np.diag(precision)
            step = np.linalg.solve(hessian, gradient)
            if np.max(np.abs(step)) < 1e-10:
                break
            rate = 1.0
            while objective(beta - rate * step) > objective(beta) + 1e-12 and rate > 1e-8:
                rate *= 0.5
            beta -= rate * step
        assert np.max(np.abs(xa.T @ (sigmoid(xa @ beta)-y) + precision * (beta-center))) < 1e-7
        preds.append(sigmoid(design @ beta))
        records.append({"alpha": float(beta[0]), "prior": float(prior[j]),
                        "vector_delta_norm": float(np.linalg.norm(beta[1:] - v)),
                        "source_vector_norm": float(np.linalg.norm(v)),
                        "successes": int(y.sum())})
    return np.asarray(preds).T, records
