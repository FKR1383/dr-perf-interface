"""derive -- cost formulas from per-basic-block instruction counts
(`drperf run --blocks`), in every state a region declares.

For a region declaring states (s1..sk), DynamoRIO counted every basic block
exactly, per combination of state values.  Each block gets a least-squares
hyperplane a1*s1 + .. + ak*sk + d over the observed points; the block is
affine if that plane holds within tolerance at every point, scaling in the variables whose slope matters
over the observed range, constant otherwise; a block that obeys no such
relation is reported separately as the irregular part and never enters the
formula.  Coefficients are attributed to the functions the blocks live in.
With one variable the points may be split into two regimes.

Counts include every thread that ran inside the region (OpenMP workers too),
exclude OpenMP runtime modules (spin-waiting), and add nested marked regions
back through the trace (inclusive formulas).  SPEC.md states the rules.
"""
import json
import os
import re

REL_TOL = 0.05      # a block follows the plane if every point is within 5% of its own count (plus ABS_TOL)
ABS_TOL = 64.0      # instructions per call: tiling/rounding slack for small blocks
MIN_VALUES = 3      # state points needed before a relation is claimed (k variables need k + 2)
MIN_SPLIT = 3       # points needed in each regime of a split; a 3-point regime is reported as weak
RUNTIME_MODULES = ("libgomp", "libiomp", "libomp", "libtbb")   # spin/barrier waiting, not work


def is_runtime(sym):
    return sym[0].startswith(RUNTIME_MODULES)


# ------------------------------------------------------------------ input

_TOK = re.compile(r'"(?:[^"\\]|\\.)*"|\S+')


def _tokens(line):
    out = []
    for t in _TOK.findall(line):
        if t.startswith('"'):
            out.append(json.loads(t))
        else:
            try:
                out.append(int(t))
            except ValueError:
                out.append(float(t))
    return out


def load_blocks(prefix):
    """prefix.blocks -> {key_index: dict}; prefix.slots -> {slot: (module, symbol, offset)}.
    Key records: "K idx region nk name1 value1 .. root count" (older files:
    "K idx region name value root count")."""
    keys, slots = {}, {}
    cur = None
    with open(prefix + ".blocks") as f:
        for line in f:
            if line.startswith("K "):
                parts = _tokens(line[2:])
                idx, region = parts[0], parts[1]
                over = False
                if isinstance(parts[2], int):
                    nk = parts[2]
                    if nk < 0:          # state combinations beyond the per-region budget
                        over, nk = True, 0
                    states = [(parts[3 + 2 * i], parts[4 + 2 * i]) for i in range(nk)]
                    root, count = parts[3 + 2 * nk], parts[4 + 2 * nk]
                else:
                    states = [(parts[2], parts[3])] if parts[2] != "" else []
                    root, count = parts[4], parts[5]
                cur = {"region": region, "states": states, "overflow": over,
                       "state_name": states[0][0] if states else "",
                       "state_value": states[0][1] if states else 0,
                       "root": root, "count": count, "vec": {}}
                keys[idx] = cur
            else:
                a, b = line.split()
                cur["vec"][int(a)] = int(b)
    if os.path.exists(prefix + ".slots"):
        with open(prefix + ".slots") as f:
            for line in f:
                slot, rest = line.split(" ", 1)
                parts = _tokens(rest)
                if len(parts) == 3:
                    mod, offs, sym = parts
                else:
                    mod, sym = parts[0], parts[1]
                    offs = None
                slots[int(slot)] = (mod, sym, offs)
    return keys, slots


def _val(x):
    """State values stay integers when they are integral: converting to float
    merges combinations that differ only above 2**53."""
    if isinstance(x, int):
        return x
    try:
        f = float(x)
    except (TypeError, ValueError):
        return 0
    return int(f) if f.is_integer() else f


def per_state(keys, region):
    """({state tuple: (summed vec, triggers)}, state names, calls left out).

    A region can also carry a bucket for the state combinations beyond the
    client's per-region budget, and older runs recorded a key with no states at
    all.  Those calls cannot be placed at a state point, so they are counted and
    dropped rather than merged into a point they do not belong to."""
    mine = [k for k in keys.values() if k["region"] == region and k["count"] > 0]
    names = ()
    for k in mine:
        if k["states"] and not k.get("overflow"):
            names = tuple(n for n, _ in k["states"])
            break
    out, dropped = {}, 0
    for k in mine:
        if k.get("overflow") or len(k["states"]) != len(names):
            dropped += k["count"]
            continue
        v = tuple(_val(val) for _, val in k["states"])
        vec, n = out.get(v, ({}, 0))
        for slot, c in k["vec"].items():
            vec[slot] = vec.get(slot, 0) + c
        out[v] = (vec, n + k["count"])
    return out, names, dropped


def per_trigger(states):
    vecs, trig = {}, {}
    for v, (vec, n) in states.items():
        vecs[v] = {slot: c / n for slot, c in vec.items()}
        trig[v] = n
    return vecs, trig


# ------------------------------------------------------------- derivation


class Regime(object):
    def __init__(self, values, k):
        self.values = values    # sorted state tuples covered by this regime
        self.k = k
        self.a = [0.0] * k      # coefficient per declared state
        self.c = 0.0
        self.irr = {}           # state -> irregular instrs per trigger
        self.wait = {}          # state -> OpenMP runtime (spin/barrier) instrs per trigger
        self.n_affine = self.n_const = self.n_irr = 0
        self.by_sym_a = [{} for _ in range(k)]
        self.by_sym_c = {}
        self.by_sym_irr = {}
        self.dependent = set()  # variables that are linear functions of earlier ones over these points
        self.marker = 0.0       # marker cost subtracted from c (calibrated), 0 if none

    def formula(self, v):
        return sum(a * x for a, x in zip(self.a, v)) + self.c

    def total(self, v):
        return self.formula(v) + self.irr.get(v, 0.0)

    def irr_share(self):
        tot = sum(self.total(v) for v in self.values)
        return (sum(self.irr.values()) / tot) if tot else 0.0

    def irr_fracs(self):
        """Irregular fraction of the cost at each point (each point counts once,
        so one very expensive point cannot dominate a split decision)."""
        return [(self.irr.get(v, 0.0) / self.total(v)) if self.total(v) else 0.0 for v in self.values]


def _solve(A, b):
    """Gauss-Jordan with partial pivoting.  Returns (x, dependent): columns
    without a usable pivot (linearly dependent) get x = 0 and are listed."""
    n = len(b)
    M = [A[i][:] + [b[i]] for i in range(n)]
    scale = max([abs(M[i][j]) for i in range(n) for j in range(n)] + [1.0])
    pivot_row, used, dep = {}, set(), set()
    for c in range(n):
        cand = [r for r in range(n) if r not in used]
        piv = max(cand, key=lambda r: abs(M[r][c]))
        if abs(M[piv][c]) <= 1e-9 * scale:
            dep.add(c)
            continue
        used.add(piv)
        pivot_row[c] = piv
        for r in range(n):
            if r != piv and M[r][c] != 0.0:
                f = M[r][c] / M[piv][c]
                M[r] = [M[r][j] - f * M[piv][j] for j in range(n + 1)]
    x = [0.0] * n
    for c, r in pivot_row.items():
        x[c] = M[r][n] / M[r][c]
    return x, dep


def affine_fit(vs, ys):
    """Least-squares plane through (state tuple, count) points, on centred and
    scaled variables: (coefficients, intercept, worst deviation, dependent
    variables).

    Scaling matters: a declared state that is a product can be 1e12 while
    another is 10, and solving the normal equations on the raw columns loses
    the small one to rounding."""
    k, n = len(vs[0]), len(vs)
    mx = [sum(v[j] for v in vs) / n for j in range(k)]
    my = sum(ys) / n
    sc = [max(abs(v[j] - mx[j]) for v in vs) or 1.0 for j in range(k)]
    X = [[(v[j] - mx[j]) / sc[j] for j in range(k)] for v in vs]
    A = [[sum(X[i][p] * X[i][q] for i in range(n)) for q in range(k)] for p in range(k)]
    b = [sum(X[i][p] * (ys[i] - my) for i in range(n)) for p in range(k)]
    a, dep = _solve(A, b)
    a = [a[j] / sc[j] for j in range(k)]        # back to instructions per unit
    c = my - sum(a[j] * mx[j] for j in range(k))
    dev = max(abs(y - (sum(a[j] * v[j] for j in range(k)) + c)) for v, y in zip(vs, ys))
    return a, c, dev, dep


def derive_regime(vecs, values, slots):
    """Per-block relation test over the given state points (sorted tuples)."""
    k = len(values[0]) if values else 0
    if len(values) < max(MIN_VALUES, k + 2):
        return None
    r = Regime(values, k)
    n = len(values)
    mx = [sum(v[j] for v in values) / n for j in range(k)]
    ranges = [max(v[j] for v in values) - min(v[j] for v in values) for j in range(k)]
    blocks = set()
    for v in values:
        blocks.update(vecs[v].keys())
    for b in sorted(blocks, key=repr):
        sym = slots.get(b, ("?", "?", None))[:2]
        ys = [vecs[v].get(b, 0.0) for v in values]
        if is_runtime(sym):
            for v, y in zip(values, ys):
                r.wait[v] = r.wait.get(v, 0.0) + y
            continue
        a, c, dev, dep = affine_fit(values, ys)
        r.dependent |= dep
        # the plane must hold at every point relative to the count at that point
        ok = all(abs(y - (sum(a[j] * v[j] for j in range(k)) + c)) <= max(ABS_TOL, REL_TOL * y)
                 for v, y in zip(values, ys))
        thr = max(ABS_TOL, REL_TOL * max(ys))
        # The origin need not be a valid input. For example, a traversal has
        # depth-1 descents: a negative intercept is valid and must not change
        # acceptance when the annotator translates a PCV by a constant.
        if ok:
            exact = dev <= 1e-9 * max(1.0, max(ys))
            scal = [j for j in range(k) if abs(a[j]) * ranges[j] > thr or (exact and abs(a[j]) > 1e-9)]
            if scal:
                # slopes too small to matter over the observed range are folded
                # into the constant at the mean of their variable
                cc = c + sum(a[j] * mx[j] for j in range(k) if j not in scal)
                r.c += cc
                r.n_affine += 1
                r.by_sym_c[sym] = r.by_sym_c.get(sym, 0.0) + cc
                for j in scal:
                    r.a[j] += a[j]
                    r.by_sym_a[j][sym] = r.by_sym_a[j].get(sym, 0.0) + a[j]
            else:
                cm = sum(ys) / len(ys)
                r.c += cm
                r.n_const += 1
                r.by_sym_c[sym] = r.by_sym_c.get(sym, 0.0) + cm
        else:
            r.n_irr += 1
            for v, y in zip(values, ys):
                r.irr[v] = r.irr.get(v, 0.0) + y
            r.by_sym_irr[sym] = r.by_sym_irr.get(sym, 0.0) + sum(ys) / len(ys)
    return r


def derive(vecs, slots, split=True, max_irr=0.05):
    """Regimes covering the observed points: one, or two along a single variable."""
    values = sorted(vecs)
    if not values:
        return []
    k = len(values[0])
    whole = derive_regime(vecs, values, slots)
    if whole is None:
        return []
    if not split or k != 1 or whole.irr_share() <= max_irr or len(values) < 2 * MIN_SPLIT:
        return [whole]
    # a split is judged by the mean irregular fraction over the points (one vote
    # per point): judged by cost, one 128-token prefill step would outweigh
    # every decode step and no split could ever pay off
    best, best_irr = [whole], sum(whole.irr_fracs()) / len(values)
    for i in range(MIN_SPLIT, len(values) - MIN_SPLIT + 1):
        lo, hi = derive_regime(vecs, values[:i], slots), derive_regime(vecs, values[i:], slots)
        if lo is None or hi is None:
            continue
        irr = (sum(lo.irr_fracs()) + sum(hi.irr_fracs())) / len(values)
        if irr < best_irr - 0.1:
            best, best_irr = [lo, hi], irr
    return best


# --------------------------------------------------------- inclusive vectors


def key_state(r):
    """Declared (key) state values of a trace record as a tuple of floats."""
    vals = list(r.get("state", {}).values())
    nk = r.get("nk")
    if nk is None:                 # older trace: the first entry is the key state
        nk = 1 if vals else 0
    return tuple(_val(x) for x in vals[:nk])


def nested_map(recs, target):
    """From trace records: for each trigger of `target`, the nested marked
    regions (any depth) as (region, state tuple) with multiplicity."""
    by_tid = {}
    for r in recs:
        by_tid.setdefault((r.get("run", 0), r.get("pid", 0), r["tid"]), []).append(r)
    out = []   # (parent state tuple, {(region, state): count})
    for tid, lst in by_tid.items():
        lst.sort(key=lambda r: r["seq"])
        trigs = [r for r in lst if r["region"] == target]
        for t in trigs:
            pv = key_state(t)
            inner = {}
            for r in lst:
                if r is t or r["region"] == target or ":" in r["region"] or r["region"] == "_perfmark_capture":
                    continue
                if t["seq"] < r["seq"] and r["seq_end"] <= t["seq_end"]:
                    key = (r["region"], key_state(r))
                    inner[key] = inner.get(key, 0) + 1
            out.append((pv, inner))
    return out


def _same(a, b):
    return len(a) == len(b) and all(abs(x - y) < 1e-9 for x, y in zip(a, b))


def nested_calls(recs, region):
    """{nested region: calls per trigger of `region`}, from the trace nesting.
    What a region's own cost leaves out, so the reader can compose it."""
    counts, parents = {}, 0
    for pv, inner in nested_map(recs, region):
        parents += 1
        for (reg, _sv), m in inner.items():
            counts[reg] = counts.get(reg, 0) + m
    if not parents:
        return {}
    return {r: n / parents for r, n in counts.items()}


def inclusive_vectors(keys, region, recs):
    """(per-trigger vectors per state point, triggers per point, state names,
    nested marked triggers per call, calls left out).

    The vectors are the region's OWN cost: instructions counted while it was the
    innermost open region.  Regions nested inside it are not folded in, because
    the client aggregates a nested region over every parent that called it, so
    folding its mean into each parent erases the parent's own dependence on its
    state.  `nested_calls` says what was left out."""
    own, names, dropped = per_state(keys, region)
    vecs, trig = per_trigger(own)
    vecs, trig = per_trigger(own)
    inner_total = parents = 0
    for pv, inner in nested_map(recs, region):
        parents += 1
        inner_total += sum(inner.values())
    return vecs, trig, names, (inner_total / parents if parents else 0.0), dropped


# ---------------------------------------------------------------- report


def fmt(x):
    if x != 0 and abs(x) < 1:        # a small per-unit coefficient is not zero
        return "%.3g" % x
    if abs(x - round(x)) < 0.05:
        return "{:,}".format(int(round(x)))
    return "{:,.1f}".format(x)


def fmt_state(names, v):
    if not names:
        return "-"
    return ",".join("%s=%s" % (n, fmt(x)) for n, x in zip(names, v))


def regime_range(regimes, r, names):
    """Label of a regime: 'n <= 6' / 'n >= 16' along one variable, else 'all'."""
    if len(regimes) > 1 and names:
        return ("%s <= %s" % (names[0], fmt(r.values[-1][0]))) if r is regimes[0] else ("%s >= %s" % (names[0], fmt(r.values[0][0])))
    return "all %s" % ", ".join(names) if names else "all"


def formula_text(r, names):
    terms = ["%s*%s" % (fmt(a), n) for a, n in zip(r.a, names)]
    return " + ".join(terms + [fmt(r.c)]) if terms else fmt(r.c)


def describe(region, names, regimes, trig, slots, top=6):
    out = []
    values = sorted(trig)
    k = len(names)
    out.append("derive %s   (instructions per call on all threads, nested marked regions included, OpenMP runtime waiting excluded; derived per basic block)" % region)
    out.append("  states: %s" % ", ".join("%s x%d" % (fmt_state(names, v), trig[v]) for v in values))
    if not regimes:
        out.append("  fewer than %d state points: no relation claimed" % max(MIN_VALUES, k + 2))
        return "\n".join(out)
    for r in regimes:
        rng = regime_range(regimes, r, names)
        share = r.irr_share()
        weak = "   (3 points: weak)" if len(r.values) == 3 and len(regimes) > 1 else ""
        out.append("  cost(%s) = %s        [%s]   blocks: %d affine, %d constant, %d irregular (%.1f%% of cost)%s" % (
            ", ".join(names), formula_text(r, names), rng, r.n_affine, r.n_const, r.n_irr, 100 * share, weak))
        for j in sorted(r.dependent):
            if j < k:
                out.append("    note: %s is a linear function of the earlier states over the observed points; its coefficient cannot be separated (attributed to them)" % names[j])
        if r.marker:
            out.append("    marker cost subtracted from the constant: %s per call (calibrated)" % fmt(r.marker))
        if r.irr:
            out.append("    irregular blocks, per call: %s .. %s" % (fmt(min(r.irr.values())), fmt(max(r.irr.values()))))
        if r.wait:
            out.append("    OpenMP runtime waiting, per call (excluded): %s .. %s" % (fmt(min(r.wait.values())), fmt(max(r.wait.values()))))
        for j in range(k):
            top_a = sorted(r.by_sym_a[j].items(), key=lambda kv: -abs(kv[1]))[:top]
            if top_a:
                out.append("    per-%s coefficient by function:" % names[j])
                for (m, s_), a in top_a:
                    out.append("      %14s  %s  [%s]" % (fmt(a), s_[:70], m))
        top_c = sorted(r.by_sym_c.items(), key=lambda kv: -abs(kv[1]))[:top]
        if top_c:
            out.append("    constant by function:")
            for (m, s_), c in top_c:
                out.append("      %14s  %s  [%s]" % (fmt(c), s_[:70], m))
        top_i = sorted(r.by_sym_irr.items(), key=lambda kv: -abs(kv[1]))[:3]
        if top_i and share > 0.02:
            out.append("    irregular by function:")
            for (m, s_), c in top_i:
                out.append("      %14s  %s  [%s]" % (fmt(c), s_[:70], m))
    return "\n".join(out)


def regime_for(regimes, v):
    """Index of the regime that covers v: below the first regime's top value or
    above the second's bottom value; a value between two regimes belongs to
    neither (the boundary was not observed) and is not predicted."""
    if not regimes:
        return None
    if len(regimes) == 1:
        return 0
    if v <= regimes[0].values[-1]:
        return 0
    if v >= regimes[1].values[0]:
        return 1
    return None


def evaluate(regimes, v):
    i = regime_for(regimes, v)
    return None if i is None else regimes[i].formula(v)


def predict(regimes, trig_other, vecs_other, slots_other):
    """Per regime: (regime, formula total, measured total, triggers) over the
    other run's triggers that the regime covers (OpenMP runtime waiting
    excluded on both sides), plus the number of triggers between regimes."""
    out = []
    for i, r in enumerate(regimes):
        pred = meas = 0.0
        nt = 0
        for v, n in trig_other.items():
            if len(v) != r.k or regime_for(regimes, v) != i:
                continue
            pred += n * r.formula(v)
            nt += n
            meas += n * sum(c for b, c in vecs_other[v].items() if not is_runtime(slots_other.get(b, ("?", "?", None))))
        out.append((r, pred, meas, nt))
    gap = sum(n for v, n in trig_other.items() if len(v) == regimes[0].k and regime_for(regimes, v) is None) if regimes else 0
    return out, gap
