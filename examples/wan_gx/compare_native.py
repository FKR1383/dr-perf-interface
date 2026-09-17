"""Compare saved native CUDA results without adding work to timed regions."""
import argparse
import json
from pathlib import Path
import torch

p = argparse.ArgumentParser()
p.add_argument('baseline', type=Path)
p.add_argument('optimized', type=Path)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()

def metrics(x, y):
    assert x.shape == y.shape and x.dtype == y.dtype
    shape = list(x.shape)
    x, y = x.reshape(-1), y.reshape(-1)
    n = x.numel()
    squared_error = squared_reference = dot = squared_candidate = 0.0
    max_abs = 0.0
    different = 0
    for lo in range(0, n, 1_000_000):
        xx, yy = x[lo:lo+1_000_000].double(), y[lo:lo+1_000_000].double()
        assert torch.isfinite(xx).all() and torch.isfinite(yy).all()
        d = xx-yy
        squared_error += (d*d).sum().item()
        squared_reference += (xx*xx).sum().item()
        squared_candidate += (yy*yy).sum().item()
        dot += (xx*yy).sum().item()
        max_abs = max(max_abs, d.abs().max().item())
        different += (xx != yy).sum().item()
    return dict(shape=shape, elements=n, different_elements=different,
                max_abs=max_abs, rmse=(squared_error/n)**0.5,
                relative_l2=(squared_error/squared_reference)**0.5 if squared_reference else None,
                cosine=dot/(squared_reference*squared_candidate)**0.5 if squared_reference*squared_candidate else None)

baseline = json.loads((a.baseline/'report.json').read_text())
optimized = json.loads((a.optimized/'report.json').read_text())
for key in ('frames','steps','prompt','config','torch','cuda','cudnn','cudnn_enabled',
            'cudnn_benchmark','gpu','gpu_state','packages','warmup','shape','finite','library_path'):
    assert baseline[key] == optimized[key], key
assert baseline['finite']
result = dict(baseline_seconds=baseline['generation_seconds'],
              optimized_seconds=optimized['generation_seconds'],
              latency_reduction_percent=100*(1-optimized['generation_seconds']/baseline['generation_seconds']),
              speedup=baseline['generation_seconds']/optimized['generation_seconds'],
              samples_per_variant=1)
for filename in ('latents.pt','video.pt'):
    x = torch.load(a.baseline/filename, map_location='cpu', weights_only=True)
    y = torch.load(a.optimized/filename, map_location='cpu', weights_only=True)
    if isinstance(x, list):
        assert len(x) == len(y)
        result[filename] = [metrics(xx, yy) for xx, yy in zip(x, y)]
    else:
        result[filename] = metrics(x, y)
    del x, y
a.output.write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
