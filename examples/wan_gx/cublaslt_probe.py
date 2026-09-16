"""Isolate cuDNN engine 58's real cuBLASLt host-side heuristic query."""
import ctypes as C
import os
from pathlib import Path
import torch

os.chdir(Path(os.environ['CUDNN_LOGDEST_DBG']).parent)
torch.empty(1, device='cuda')
lib = C.CDLL('libcublasLt.so.12')
P = C.c_void_p

def api(name, args):
    fn = getattr(lib, name)
    fn.argtypes, fn.restype = args, C.c_int
    return fn

create = api('cublasLtCreate', [C.POINTER(P)])
make_desc = api('cublasLtMatmulDescCreate', [C.POINTER(P), C.c_int, C.c_int])
make_layout = api('cublasLtMatrixLayoutCreate', [C.POINTER(P), C.c_int, C.c_uint64, C.c_uint64, C.c_int64])
make_pref = api('cublasLtMatmulPreferenceCreate', [C.POINTER(P)])
set_pref = api('cublasLtMatmulPreferenceSetAttribute', [P, C.c_int, P, C.c_size_t])
query = api('cublasLtMatmulAlgoGetHeuristic', [P,P,P,P,P,P,P,C.c_int,P,C.POINTER(C.c_int)])
handle = P()
print('LT_CREATE', create(C.byref(handle)), handle.value, flush=True)
for dtype in [14, 0]:
    desc, pref = P(), P()
    assert make_desc(C.byref(desc), 77, 0) == 0
    layouts=[]
    for rows, cols in [(131040,16),(16,16),(131040,16)]:
        layout=P()
        assert make_layout(C.byref(layout), dtype, rows, cols, rows) == 0
        layouts.append(layout)
    assert make_pref(C.byref(pref)) == 0
    workspace=C.c_uint64(134217728)
    assert set_pref(pref,1,C.byref(workspace),8) == 0
    alignment=C.c_uint32(16)
    for attr in [5,6,7,8]:
        assert set_pref(pref,attr,C.byref(alignment),4) == 0
    result=C.create_string_buffer(1024)
    count=C.c_int(-1)
    status=query(handle,desc,*layouts,layouts[-1],pref,1,result,C.byref(count))
    print('LT_HEURISTIC',dtype,'status',status,'count',count.value, flush=True)
