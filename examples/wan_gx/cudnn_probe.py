"""Reproduce Wan VAE's first cuDNN convolution without loading the model."""
import os
from pathlib import Path
import torch

if os.environ.get('CUDNN_LOGDEST_DBG'):
    os.chdir(Path(os.environ['CUDNN_LOGDEST_DBG']).parent)

torch.set_num_threads(1)
print('DEVICE', torch.cuda.get_device_name(0), 'CUDNN', torch.backends.cudnn.version(), flush=True)
print('PROPERTIES', torch.cuda.get_device_properties(0), flush=True)
print('POLICY', torch.backends.cudnn.enabled, torch.backends.cudnn.allow_tf32,
      torch.backends.cudnn.benchmark, torch.backends.cudnn.deterministic, flush=True)
for dtype in (torch.bfloat16, torch.float32):
    x = torch.zeros((1,16,21,60,104), device='cuda', dtype=dtype)
    conv = torch.nn.Conv3d(16,16,1).to(device='cuda', dtype=dtype).eval()
    print('CONV_START', dtype, flush=True)
    print('BACKEND', torch._C._select_conv_backend(x, conv.weight, conv.bias,
          [1,1,1], [0,0,0], [1,1,1], False, [0,0,0], 1), flush=True)
    try:
        with torch.no_grad():
            y = conv(x)
        torch.cuda.synchronize()
        print('CONV_OK', dtype, tuple(y.shape), flush=True)
    except Exception as error:
        print('CONV_FAILED', dtype, repr(error), flush=True)
        raise
