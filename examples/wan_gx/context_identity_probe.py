"""Check the two private driver queries used by this cuBLASLt build.

Native profiling established that TLS table slot 2 is equivalent to
cuCtxGetCurrent, and context table slot 4 is equivalent to cuCtxGetId.
This probe uses initialized contexts; it does not test GPU arithmetic.
"""
import ctypes as C
import json
import torch

P = C.c_void_p
cu = C.CDLL('libcuda.so.1')

def api(name, args):
    fn = getattr(cu, name)
    fn.argtypes, fn.restype = args, C.c_int
    return fn

export = api('cuGetExportTable', [C.POINTER(P), P])
current = api('cuCtxGetCurrent', [C.POINTER(P)])
identity = api('cuCtxGetId', [P, C.POINTER(C.c_ulonglong)])
create = api('cuCtxCreate_v2', [C.POINTER(P), C.c_uint, C.c_int])
destroy = api('cuCtxDestroy_v2', [P])
set_current = api('cuCtxSetCurrent', [P])
push = api('cuCtxPushCurrent_v2', [P])
pop = api('cuCtxPopCurrent_v2', [C.POINTER(P)])

def slot(hex_uuid, index):
    result = P()
    raw = C.create_string_buffer(bytes.fromhex(hex_uuid))
    assert export(C.byref(result), raw) == 0
    table = C.cast(result, C.POINTER(P))
    assert table[0] >= (index+1)*C.sizeof(P)
    assert table[index]
    return table[index]

# Establish the same initialized-primary-context boundary as Wan.
torch.empty(1, device='cuda')
tls_current = C.CFUNCTYPE(C.c_int, C.POINTER(P))(
    slot('42d85a8123f6cb478298f6e78a3aecdc', 2))
private_id = C.CFUNCTYPE(C.c_int, P, C.POINTER(C.c_ulonglong))(
    slot('21318c60971432488ca641ff7324c8f2', 4))

def check(expected):
    actual, private = P(), P()
    assert current(C.byref(actual)) == tls_current(C.byref(private)) == 0
    assert actual.value == private.value == expected.value
    a, b = C.c_ulonglong(), C.c_ulonglong()
    assert identity(actual, C.byref(a)) == private_id(private, C.byref(b)) == 0
    assert a.value == b.value and a.value != 0
    return a.value

primary = P()
assert current(C.byref(primary)) == 0
primary_id = check(primary)
seen = {primary_id}
# Exercise destruction and allocator reuse, plus stack restoration.
for _ in range(8):
    context, popped = P(), P()
    assert create(C.byref(context), 0, 0) == 0
    value = check(context)
    assert value not in seen
    seen.add(value)
    assert push(primary) == 0
    assert check(primary) == primary_id
    assert pop(C.byref(popped)) == 0 and popped.value == primary.value
    assert check(context) == value
    assert set_current(primary) == destroy(context) == 0
assert check(primary) == primary_id
print('CONTEXT_IDENTITY_OK', json.dumps({'distinct_contexts': len(seen), 'stack_round_trips': 8}), flush=True)
