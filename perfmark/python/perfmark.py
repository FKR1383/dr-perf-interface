"""perfmark -- mark regions of a Python program for drperf.

    import perfmark

    with perfmark.region("bind_batch", n_entries=len(entries)):
        ...                                   # counted, state n_entries=<value>

    with perfmark.region("consume", q=len(queue), batch=b, mode="fast"):
        ...   # integer keywords = declared states (all part of the key);
              # other keywords are extra states recorded per trigger in the trace

    @perfmark.region("encode")                # decorator form, no state
    def encode(...): ...

    st = perfmark.states(n=256)               # K=V args passed by `drperf run --state`

Without libperfmark.so, or outside DynamoRIO, the markers are no-ops (a ctypes
call into an empty C function).  Declared state values must fit in a signed
64-bit integer; extra states are recorded as strings.
"""
import ctypes
import functools
import numbers
import os
import sys

__all__ = ["region", "begin", "end", "state", "states", "available", "calibrate", "capture", "capture_exit", "summarize"]


def _find_lib():
    here = os.path.dirname(os.path.abspath(__file__))
    cands = []
    if os.environ.get("PERFMARK_LIB"):
        cands.append(os.environ["PERFMARK_LIB"])
    cands += [
        os.path.join(here, "libperfmark.so"),
        os.path.join(here, "..", "libperfmark.so"),
        os.path.join(here, "..", "..", "build", "libperfmark.so"),
        "libperfmark.so",
    ]
    for c in cands:
        try:
            # PyDLL: do not release the GIL around the (empty) marker call.
            # With CDLL every marker would release and re-acquire the GIL,
            # which costs thousands of instructions once other threads exist.
            return ctypes.PyDLL(c)
        except OSError:
            continue
    return None


def _load_ext():
    """The C extension (build/_perfmark.so): markers cost a few hundred
    instructions instead of ~10K through ctypes and a Python `with`."""
    import importlib.util
    here = os.path.dirname(os.path.abspath(__file__))
    cands = [os.environ.get("PERFMARK_EXT"), os.path.join(here, "..", "..", "build", "_perfmark.so"),
             os.path.join(here, "_perfmark.so")]
    for c in cands:
        if not c or not os.path.exists(c):
            continue
        try:
            spec = importlib.util.spec_from_file_location("_perfmark", c)
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            sys.modules["_perfmark"] = m
            return m
        except Exception:
            continue
    return None


_ext = None if os.environ.get("PERFMARK_NO_EXT") else _load_ext()
_lib = None if _ext is not None else _find_lib()
available = _ext is not None or _lib is not None
fast = _ext is not None

if _ext is not None:
    _begin, _end, _state = _ext.begin, _ext.end, _ext.state
elif available:
    _begin = _lib.perfmark_begin
    _begin.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int64]
    _begin.restype = None
    _begin_v_raw = _lib.perfmark_begin_v
    _begin_v_raw.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.POINTER(ctypes.c_char_p), ctypes.POINTER(ctypes.c_int64)]
    _begin_v_raw.restype = None

    def _begin_v(region, key):
        n = len(key)
        names = (ctypes.c_char_p * n)(*[k for k, _ in key])
        vals = (ctypes.c_int64 * n)(*[v for _, v in key])
        _begin_v_raw(region, n, names, vals)
    _end = _lib.perfmark_end
    _end.argtypes = [ctypes.c_char_p]
    _end.restype = None
    _state = _lib.perfmark_state
    _state.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    _state.restype = None
else:
    if os.environ.get("DRPERF"):
        raise ImportError("perfmark: libperfmark.so not found (set PERFMARK_LIB); "
                          "refusing to run under drperf with no-op markers")

    def _begin(region, state_name, state_value):
        pass

    def _begin_v(region, key):
        pass

    def _end(region):
        pass

    def _state(name, value):
        pass


def _encode(s):
    return s if isinstance(s, bytes) else str(s).encode()


def _split_state(state):
    """Keyword states -> (declared states [(bytes, int)], extra states [(bytes, bytes)]).

    Integer values (not bool) are declared states: they form the aggregation
    key and the cost formula is derived in all of them.
    Any other value is an extra state, recorded per trigger in the trace."""
    key, extra = [], []
    for k, v in state.items():
        if isinstance(v, numbers.Integral) and not isinstance(v, bool):
            value = int(v)
            if not -(1 << 63) <= value < (1 << 63):
                raise OverflowError("declared state %r must fit a signed 64-bit integer" % k)
            key.append((_encode(k), value))
        else:
            extra.append((_encode(k), _encode(v)))
    return key, extra


def _open(name, key, extra):
    if len(key) == 1:
        _begin(name, key[0][0], key[0][1])
    elif not key:
        _begin(name, b"", 0)
    else:
        _begin_v(name, key)
    for k, v in extra:
        _state(k, v)


if _ext is not None:
    class region(_ext.Region):
        """Context manager and decorator delimiting a counted region (C fast path).

        Integer keywords are the declared states (all part of the aggregation
        key, the formula is derived in them); other keywords are extra states
        attached to each trigger.
        """
        __slots__ = ()

        def __init__(self, name, **state):
            if _calibrate_pending:
                _calibrate_once()
            key, extra = _split_state(state)
            _ext.Region.__init__(self, _encode(name), key or None, extra or None)

        def state(self, name, value):
            """Attach an extra state to the open region (call inside the block)."""
            _ext.Region.state(self, _encode(name), _encode(value))

        def __call__(self, fn):
            @functools.wraps(fn)
            def wrapper(*args, **kwargs):
                self.__enter__()
                try:
                    return fn(*args, **kwargs)
                finally:
                    self.__exit__(None, None, None)
            return wrapper


class _region_ctypes(object):
    """Context manager and decorator delimiting a counted region (ctypes path)."""
    __slots__ = ("_name", "_key", "_extra")

    def __init__(self, name, **state):
        self._name = _encode(name)
        self._key, self._extra = _split_state(state)

    def state(self, name, value):
        """Attach an extra state to the open region (call inside the block)."""
        _state(_encode(name), _encode(value))

    def __enter__(self):
        if _calibrate_pending:
            _calibrate_once()
        _open(self._name, self._key, self._extra)
        return self

    def __exit__(self, *exc):
        _end(self._name)
        return False

    def __call__(self, fn):
        name, key, extra = self._name, self._key, self._extra

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            _open(name, key, extra)
            try:
                return fn(*args, **kwargs)
            finally:
                _end(name)
        return wrapper


if _ext is None:
    region = _region_ctypes


def begin(name, state_name="", state_value=0):
    _begin(_encode(name), _encode(state_name), int(state_value))


def end(name):
    _end(_encode(name))


def state(name, value):
    """Attach an extra named value to the innermost open region."""
    _state(_encode(name), _encode(value))


def _coerce(v):
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        return v


def states(argv=None, **defaults):
    """Return {key: value} from K=V arguments (defaults overridden by argv).

    `drperf run --state n=256` appends `n=256` to the command line.  Consumed
    arguments are removed from sys.argv when argv is None.
    """
    src = sys.argv if argv is None else argv
    out = dict(defaults)
    keep = [src[0]] if src else []
    for a in src[1:]:
        if "=" in a and not a.startswith("-"):
            k, v = a.split("=", 1)
            out[k] = _coerce(v)
        else:
            keep.append(a)
    if argv is None:
        sys.argv[:] = keep
    return out


_MISSING = object()


def summarize(v):
    """(label suffix, value) for a captured variable, or None if it is not data."""
    if v is None or isinstance(v, (type, type(summarize), type(os))):
        return None
    if isinstance(v, bool):
        return "", int(v)
    if isinstance(v, int):
        return "", v
    if isinstance(v, float):
        return "", v
    shape = getattr(v, "shape", None)
    if shape is not None and not isinstance(shape, (str, bytes)):
        try:
            n = 1
            for d in shape:
                n *= int(d)
            return "numel", n
        except (TypeError, ValueError):
            pass
    try:
        return "len", len(v)
    except TypeError:
        return None


def capture(loc, glob, names):
    """Summaries of the named free variables of a region, for auto-captured states."""
    out = {}
    for n in names:
        parts = n.split(".")
        v = loc.get(parts[0], _MISSING)
        if v is _MISSING:
            v = glob.get(parts[0], _MISSING)
            if v is _MISSING:
                continue
        try:
            for attr in parts[1:]:
                v = getattr(v, attr)
        except Exception:
            continue
        try:
            sv = summarize(v)
        except Exception:
            sv = None
        if sv is None:
            continue
        kind, val = sv
        out["%s(%s)" % (kind, n) if kind else n] = val
    return out


CAPTURE_REGION = b"_perfmark_capture"


def capture_exit(loc, glob, names, declared):
    """Record the captured names and the declared states again at region exit
    (as name@exit).  The work runs inside a nested `_perfmark_capture` region
    so the analyzers can subtract it from the enclosing region."""
    _begin(CAPTURE_REGION, b"", 0)
    try:
        vals = capture(loc, glob, names)
        for k, fn in declared.items():
            try:
                sv = summarize(fn())
            except Exception:
                continue
            if sv is not None:
                vals[k] = sv[1]
    finally:
        _end(CAPTURE_REGION)
    for k, v in vals.items():
        _state(_encode(k + "@exit"), _encode(v))


def calibrate(n=20):
    """Measure the marker cost so drperf can subtract it.

    _perfmark_calibration        : n empty regions -> cost inside the brackets
    _perfmark_calibration_outer  : the loop of n empty regions -> its self is
                                   n x the cost outside the brackets + loop
    _perfmark_calibration_loop   : the same loop with a bare `pass` body
    """
    inner = region("_perfmark_calibration")
    outer = region("_perfmark_calibration_outer")
    loop = region("_perfmark_calibration_loop")
    with loop:
        for _ in range(n):
            pass
    with outer:
        for _ in range(n):
            with inner:
                pass


_calibrate_pending = bool(os.environ.get("PERFMARK_CALIBRATE")) and available


def _calibrate_once():
    """Calibration runs at the first real region, not at import.

    With late attach, DynamoRIO starts at the first marker; calibrating at
    import would attach before the program has done any of its own work, which
    is exactly what late attach exists to avoid."""
    global _calibrate_pending
    if _calibrate_pending:
        _calibrate_pending = False
        calibrate()
