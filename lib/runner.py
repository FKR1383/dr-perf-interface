"""runner -- run a program under the drperf client and read what it wrote.

Everything `drperf` needs: start the program with DynamoRIO attaching at the
first marked region, then read the per-basic-block counts and the trigger
trace back.  The analysis itself is in derive.py.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "lib"))
DRRUN = os.path.join(ROOT, "third_party", "dynamorio", "bin64", "drrun")
CLIENT = os.path.join(ROOT, "build", "libdrperf.so")
ATTACH = os.path.join(ROOT, "build", "libdrperf_attach.so")
PERFMARK = os.path.join(ROOT, "build", "libperfmark.so")
CALIB = "_perfmark_calibration"


def build_env():
    """A repeatable environment: fixed hash seed and thread counts, no ASLR
    (added by the caller), and the marker library and Python binding found."""
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = "0"
    for v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        env.setdefault(v, "4")
    env["PERFMARK_LIB"] = PERFMARK
    env["PERFMARK_CALIBRATE"] = "1"
    env["DRPERF"] = "1"
    py = os.path.join(ROOT, "perfmark", "python")
    env["PYTHONPATH"] = py + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    return env


def run(cmd, out, timeout=None):
    """Run `cmd` with the client, one output file per process.  DynamoRIO is
    started by the first marked region (see perfmark/attach.c), so everything
    before it runs natively."""
    if not os.path.exists(CLIENT) or not os.path.exists(ATTACH):
        sys.exit("drperf: build first (./build.sh)")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "run.%p.json")
    env = build_env()
    env["DRPERF_LATE"] = "1"
    env["DYNAMORIO_OPTIONS"] = "-code_api -client_lib '%s;0;%s'" % (
        CLIENT, " ".join(["-o", path, "-blocks"]))
    excluded = env.get("DRPERF_EXCLUDE_CUDA_MODULE", "")
    if excluded:
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,127}", excluded):
            raise ValueError("DRPERF_EXCLUDE_CUDA_MODULE must be a module basename")
        env["DYNAMORIO_OPTIONS"] = env["DYNAMORIO_OPTIONS"][:-1] + " -exclude_cuda_module " + excluded + "'"
    if env.get("DRPERF_FOLLOW_THREADS", "1") == "0":
        env["DYNAMORIO_OPTIONS"] = env["DYNAMORIO_OPTIONS"][:-1] + " -no_follow_threads'"
    pre = env.get("LD_PRELOAD", "")
    env["LD_PRELOAD"] = (ATTACH + " " + pre).strip()
    prefix = ["setarch", "-R"] if shutil.which("setarch") else []
    rc, wall, so, se = run_process(prefix + list(cmd), env, timeout)
    import glob
    files = sorted(os.path.basename(f) for f in glob.glob(os.path.join(out, "run.*.json")))
    return rc, so + se, files


def validity(rs):
    """What went wrong in the run itself, in words.  The counts stop being exact
    when the client runs out of room, and a caller that prints formulas without
    checking this is printing fiction."""
    out = []
    for run in rs["runs"]:
        d = run["data"].get("drperf", {})
        if d.get("excluded_cuda_module") and not d.get("excluded_cuda_exports"):
            out.append("requested CUDA exclusion matched no exports: " + d["excluded_cuda_module"])
        if d.get("slots_overflow"):
            out.append("%s basic blocks did not fit the counter table of %s slots: their counts "
                       "were merged into one slot" % (fmt_int(d["slots_overflow"]), fmt_int(d.get("max_slots", 0))))
        if d.get("counter_denied"):
            out.append("%s region keys got no counter array: the memory budget ran out"
                       % fmt_int(d["counter_denied"]))
        if d.get("state_overflows"):
            out.append("%s states were dropped at the marker: more than the client keeps"
                       % fmt_int(d["state_overflows"]))
        if d.get("unmatched_ends"):
            out.append("%s region ends had no matching begin" % fmt_int(d["unmatched_ends"]))
        if d.get("trace_dropped"):
            out.append("%s region triggers were left out of the trace: relations and nesting "
                       "are computed from a truncated trace" % fmt_int(d["trace_dropped"]))
    return sorted(set(out))


def fmt_int(n):
    return "{:,}".format(int(n))


def load_runs(out):
    """The run set as the readers below expect it."""
    runs = []
    for fn in sorted(os.listdir(out)):
        if not fn.endswith(".json") or fn.endswith(".struct.json"):
            continue
        with open(os.path.join(out, fn)) as f:
            runs.append({"data": json.load(f), "file": fn})
    return {"label": out, "runs": runs, "path": out}


def run_process(cmd, env, timeout):
    t0 = time.time()
    try:
        p = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=timeout)
        rc, out, err = p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as e:
        rc, out, err = -1, e.stdout or b"", (e.stderr or b"") + b"\n[drperf: timeout]"
    return rc, time.time() - t0, out.decode(errors="replace")[-2000:], err.decode(errors="replace")[-2000:]


_HASHES = [(re.compile(r"\[[0-9a-f]{8,16}\]"), ""),      # Rust v0 crate disambiguator
           (re.compile(r"::h[0-9a-f]{16}\b"), ""),        # Rust legacy hash
           (re.compile(r"\.(llvm|constprop|part|isra|cold|lto_priv)\.[0-9a-f]*"), "")]  # compiler clones


def demangle_all(names):
    """Demangle Rust/C++ names with c++filt (one process) and strip build hashes."""
    todo = sorted(n for n in names if n.startswith("_R") or n.startswith("_Z"))
    out = {}
    if todo and shutil.which("c++filt"):
        try:
            p = subprocess.run(["c++filt"], input="\n".join(todo) + "\n", stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, universal_newlines=True, timeout=60)
            lines = p.stdout.splitlines()
            if len(lines) == len(todo):
                out = dict(zip(todo, lines))
        except (OSError, subprocess.SubprocessError):
            pass
    res = {}
    for n in names:
        suffix = "+?" if n.endswith("+?") else ""
        base = n[:-2] if suffix else n
        d = out.get(base, base)
        for rx, sub in _HASHES:
            d = rx.sub(sub, d)
        res[n] = d + suffix
    return res


def _num(v):
    """Declared states are integers and the relations are claimed to be exact,
    so they stay integers: Python's are arbitrary precision, while float loses
    the low bits above 2**53 and would call a relation exact that is not."""
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return int(f) if f.is_integer() else f


def is_structural(name):
    return ":" in name or name == "_perfmark_capture"


def trace_regions(recs, structural=False):
    regions = sorted(set(r["region"] for r in recs if not r["region"].startswith(CALIB)
                         and (structural or not is_structural(r["region"]))))
    states = {}
    for R in regions:
        ks = set()
        for r in recs:
            if r["region"] == R:
                ks.update(k for k, v in r["state"].items() if _num(v) is not None)
        states[R] = sorted(ks)
    return regions, states


def feature_rows(recs, target_region, target_field, structural=False):
    """At every trigger of target_region: (features, y) with cum/cumend/last/count
    of every region's numeric states over earlier triggers."""
    regions, states = trace_regions(recs, structural)
    cum, cumend, last, count = {}, {}, {}, {}
    ended = sorted(recs, key=lambda r: r["seq_end"])
    ei = 0
    rows, names = [], []
    for R in regions:
        names.append("count(%s)" % R)
        for st in states[R]:
            names += ["cum(%s.%s)" % (R, st), "cumend(%s.%s)" % (R, st), "last(%s.%s)" % (R, st)]
    for r in recs:
        while ei < len(ended) and ended[ei]["seq_end"] < r["seq"]:
            e = ended[ei]
            for k, v in e["state"].items():
                x = _num(v)
                if x is not None:
                    cumend[(e["region"], k)] = cumend.get((e["region"], k), 0) + x
            ei += 1
        if r["region"] == target_region and target_field in r["state"] and _num(r["state"][target_field]) is not None:
            f = []
            for R in regions:
                f.append(count.get(R, 0))
                for st in states[R]:
                    f += [cum.get((R, st), 0), cumend.get((R, st), 0), last.get((R, st), 0)]
            rows.append((f, _num(r["state"][target_field])))
        count[r["region"]] = count.get(r["region"], 0) + 1
        for k, v in r["state"].items():
            x = _num(v)
            if x is not None:
                cum[(r["region"], k)] = cum.get((r["region"], k), 0) + x
                last[(r["region"], k)] = x
    return names, rows


def dedupe_columns(names, rows):
    """Drop constant columns and columns identical to an earlier one (keep alias names)."""
    keep, aliases = [], {}
    cols = {}
    for j, n in enumerate(names):
        col = tuple(f[j] for f, y in rows)
        if len(set(col)) <= 1:
            continue
        if col in cols:
            aliases.setdefault(cols[col], []).append(n)
            continue
        cols[col] = n
        keep.append(j)
    return keep, aliases


def exact_relations(names, rows, max_terms=3, coefs=(1, -1, 2, -2)):
    import itertools
    keep, aliases = dedupe_columns(names, rows)
    ys = [y for f, y in rows]
    found = []
    for k in range(1, max_terms + 1):
        for combo in itertools.combinations(keep, k):
            for cs in itertools.product(coefs, repeat=k):
                offset = None
                ok = True
                for (f, y) in rows:
                    pred = sum(c * f[j] for c, j in zip(cs, combo))
                    d = y - pred
                    if offset is None:
                        offset = d
                    elif d != offset if isinstance(d, int) and isinstance(offset, int) \
                            else abs(d - offset) > 1e-9:
                        ok = False
                        break
                if ok:
                    found.append((combo, cs, offset))
        if found:
            break
    out = []
    for combo, cs, offset in found:
        terms = []
        for c, j in zip(cs, combo):
            n = names[j]
            if aliases.get(n):
                n = "%s (= %s)" % (n, ", ".join(aliases[n]))
            terms.append(("%+d*%s" % (c, n)) if abs(c) != 1 else (("+ " if c > 0 else "- ") + n))
        expr = " ".join(terms).lstrip("+ ").replace(" +", " +").replace("+ -", "- ")
        if abs(offset) > 1e-9:
            expr += " %+g" % offset
        out.append(expr)
    return out


def blocks_of_set(rs):
    """Merged block keys and slot table over every file of the set (one
    process may hold the regions, others none; grid points are separate files)."""
    import derive
    keys, slots = {}, {}
    nxt = 0
    for run in rs["runs"]:
        fn = run.get("file")
        if not fn:
            continue
        prefix = os.path.join(rs["path"], fn)
        if not os.path.exists(prefix + ".blocks"):
            continue
        k, sl = derive.load_blocks(prefix)
        # block identity across processes: (module, offset) when the table has
        # offsets, else the per-process slot id
        ident = {}
        for slot, (mod, sym, offs) in sl.items():
            ident[slot] = (mod, offs) if offs is not None else (nxt, slot)
            slots[ident[slot]] = (mod, sym, offs)
        for idx, rec in k.items():
            rec["vec"] = {ident.get(slot, (nxt, slot)): c for slot, c in rec["vec"].items()}
            keys[(nxt, idx)] = rec
        nxt += 1
    return keys, slots


def load_traces_all(rs):
    """Trace records of every run of the set (all grid points, repeats and
    processes), each tagged with its run index and pid; sequence numbers are
    left as they are (derive only nests within one thread of one process)."""
    recs = []
    for ri, run in enumerate(rs["runs"]):
        tf = run["data"]["drperf"].get("trace_file", "")
        if not tf:
            continue
        if not os.path.exists(tf):
            cand = os.path.join(rs["path"], os.path.basename(tf))
            tf = cand if os.path.exists(cand) else tf
        if not os.path.exists(tf):
            continue
        with open(tf) as f:
            for line in f:
                line = line.strip()
                if line:
                    r = json.loads(line)
                    r["pid"] = run["data"]["drperf"].get("pid", 0)
                    r["run"] = ri
                    recs.append(r)
    return recs


def demangle_slots(slots):
    """Slot table with Rust/C++ symbol names demangled (as show/diff print them)."""
    names = demangle_all(set(sym for (mod, sym, off) in slots.values()))
    return {b: (mod, names.get(sym, sym), off) for b, (mod, sym, off) in slots.items()}


def calibration(run):
    """(inside, outside) instructions per marker pair, from the calibration
    regions perfmark.calibrate() runs at the first region: `inside` is what a
    pair costs the region it wraps, `outside` what it costs the region around
    it."""
    inner = outer = loop = None
    for reg in run["regions"]:
        if reg["region"] == CALIB and reg["count"]:
            inner = reg
        elif reg["region"] == CALIB + "_outer" and reg["count"]:
            outer = reg
        elif reg["region"] == CALIB + "_loop" and reg["count"]:
            loop = reg
    inside = inner["incl"]["sum"] / inner["count"] if inner else 0.0
    n = inner["count"] if inner else 20
    outside = 0.0
    if outer and loop and inner:
        outside = max(0.0, (outer["incl"]["sum"] / outer["count"] -
                            loop["incl"]["sum"] / loop["count"] - n * inside) / n)
    return inside, outside


def marker_cost(rs):
    """The calibrated marker cost of the run, or (0, 0) if it was not measured."""
    for run in rs["runs"]:
        try:
            inside, outside = calibration(run["data"])
        except (KeyError, TypeError, ZeroDivisionError):
            continue
        if inside:
            return inside, outside
    return 0.0, 0.0
