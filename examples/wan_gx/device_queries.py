"""Record primary-context limits used by real cuBLAS/cuDNN host dispatch."""
import argparse
import ctypes
import json
from pathlib import Path
import torch

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
assert 'gx_cuda.so' not in Path('/proc/self/maps').read_text()
assert 'A100' in torch.cuda.get_device_name(0)
torch.empty(1, device='cuda')
driver = ctypes.CDLL('libcuda.so.1')
driver.cuCtxGetLimit.argtypes = [ctypes.POINTER(ctypes.c_size_t), ctypes.c_int]
driver.cuCtxGetLimit.restype = ctypes.c_int
limits = []
for limit in range(10):
    value = ctypes.c_size_t(0)
    status = driver.cuCtxGetLimit(ctypes.byref(value), limit)
    limits.append(dict(limit=limit, status=status, value=value.value if status == 0 else 0))
report = dict(device=str(torch.cuda.get_device_properties(0)), limits=limits)
driver.cuDeviceGetAttribute.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_int, ctypes.c_int]
attributes = []
for attribute in range(1, 201):
    value = ctypes.c_int(0)
    status = driver.cuDeviceGetAttribute(ctypes.byref(value), attribute, 0)
    attributes.append(dict(attribute=attribute, status=status, value=value.value if status == 0 else 0))
report['attributes'] = attributes
a.output.write_text(json.dumps(report, indent=2) + '\n')
a.output.with_suffix('.tsv').write_text(''.join(
    f"{r['limit']} {r['status']} {r['value']}\n" for r in limits))
a.output.with_suffix('.attributes.tsv').write_text(''.join(
    f"{r['attribute']} {r['status']} {r['value']}\n" for r in attributes))
print(json.dumps(report))
