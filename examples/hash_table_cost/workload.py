"""Entry-time semantic summaries, read from real CPython table layouts."""
import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "bin"))
from _hash_study import snapshot, measure

MOD = sys.hash_info.modulus
SHIFT = sys.int_info.bits_per_digit
MASK = (1 << SHIFT)-1


def limbs(value):
    return max(1, (value.bit_length()+SHIFT-1)//SHIFT)


def clone(value):
    return int.from_bytes(value.to_bytes((value.bit_length()+7)//8, "little"), "little")


def lookup_summary(table, query):
    s = snapshot(table)
    assert all(e is None or type(e[1]) is int for e in s["entries"])
    h = hash(query)
    assert h >= 0 and type(query) is int and query > 0
    f = {name: 0 for name in ("probes", "dummy_probes", "hash_mismatches", "equal_hash", "eq_digits",
                             "eq_unequal", "hit", "identity", "hash_subtractions",
                             "eq_ge2", "eq_ge3", "eq_ge4", "eq_gt4")}
    f.update(used=s["used"], capacity=s["capacity"], dummy_slots=s["indices"].count(-2),
             key_digits=limbs(query), hash_digits=limbs(query), width=s["width"])
    assert f["key_digits"] > 1
    x = 0
    for j in reversed(range(limbs(query))):
        x = ((x << SHIFT) & MOD) | (x >> (MOD.bit_length()-SHIFT))
        x += (query >> (j*SHIFT)) & MASK
        if x >= MOD: f["hash_subtractions"] += 1; x -= MOD
    assert x == h
    perturb, index = h, h & (s["capacity"]-1)
    while True:
        f["probes"] += 1
        entry = s["indices"][index]
        if entry == -1: break
        if entry == -2:
            f["dummy_probes"] += 1
        else:
            stored_hash, key = s["entries"][entry]
            if key is query:
                f["identity"] = f["hit"] = 1
                break
            if stored_hash != h:
                f["hash_mismatches"] += 1
            else:
                f["equal_hash"] += 1
                compared = 0
                if limbs(key) == limbs(query):
                    for j in reversed(range(limbs(key))):
                        f["eq_digits"] += 1
                        compared += 1
                        if ((key >> (j*SHIFT)) & MASK) != ((query >> (j*SHIFT)) & MASK): break
                for threshold in (2, 3, 4):
                    f[f"eq_ge{threshold}"] += int(compared >= threshold)
                f["eq_gt4"] += int(compared > 4)
                if key == query:
                    f["hit"] = 1
                    break
                f["eq_unequal"] += 1
        perturb >>= 5
        index = (5*index + perturb + 1) & (s["capacity"]-1)
        assert f["probes"] < 2*s["capacity"]
    assert bool(query in table) == bool(f["hit"])
    for width in (1, 2, 4, 8):
        for name in ("probes", "dummy_probes", "hash_mismatches"):
            f[f"{name}_w{width}"] = f[name] if s["width"] == width else 0
    return f, s


LOOKUP_MODELS = {
    "metadata": ("used", "capacity", "dummy_slots", "key_digits", "hit"),
    "probes": ("hash_digits", "probes", "hit"),
    "semantic": ("hash_digits", "hash_subtractions", "probes_w1", "probes_w2",
                 "dummy_probes_w1", "dummy_probes_w2", "hash_mismatches", "equal_hash", "eq_digits", "hit"),
    "peeled": ("hash_digits", "hash_subtractions", "probes_w1", "probes_w2",
               "dummy_probes_w1", "dummy_probes_w2", "hash_mismatches", "equal_hash",
               "eq_digits", "eq_ge2", "eq_ge3", "eq_ge4", "eq_gt4", "hit"),
    "audit": ("case_id",),
}

INSERT_MODELS = {
    "metadata": ("used", "capacity", "resize"),
    "moved": ("probes", "equal_hash", "eq_digits", "moved", "resize"),
    "semantic": ("probes_w1", "probes_w2", "equal_hash", "eq_digits", "eq_ge3",
                 "dummy_probes_w1", "dummy_probes_w2", "resize", "moved", "deleted_entries",
                 "new_index_bytes", "rebuild_collisions", "insert_collisions"),
    "widths": ("probes_w1", "probes_w2", "equal_hash", "eq_digits", "eq_ge3",
               "dummy_probes_w1", "dummy_probes_w2", "resize", "moved", "deleted_entries",
               "new_index_bytes", "rebuild_collisions_w1", "rebuild_collisions_w2", "insert_collisions"),
    "peeled": ("probes_w1", "probes_w2", "equal_hash", "eq_digits", "eq_ge3",
               "dummy_probes_w1", "dummy_probes_w2", "resize", "moved", "deleted_entries",
               "new_index_bytes", "rebuild_collisions_w1", "rebuild_collisions_w2", "insert_collisions",
               "rebuild_ge1_w1", "rebuild_ge1_w2", "rebuild_ge2_w1", "rebuild_ge2_w2"),
    "audit": ("case_id",),
}


def insertion_summary(table, query):
    f, s = lookup_summary(table, query)
    assert not f["hit"]
    resize = int(s["usable"] == 0)
    capacity = max(8, 1 << (3*s["used"]-1).bit_length()) if resize else s["capacity"]
    indices = [-1]*capacity if resize else list(s["indices"])
    collisions, ge1, ge2 = 0, 0, 0
    if resize:
        for entry in s["entries"]:
            if entry is None: continue
            h, _ = entry
            perturb, index = h, h & (capacity-1)
            chain = 0
            while indices[index] >= 0:
                collisions += 1
                chain += 1
                perturb >>= 5
                index = (5*index + perturb + 1) & (capacity-1)
            indices[index] = 0
            ge1 += int(chain >= 1)
            ge2 += int(chain >= 2)
    perturb = hash(query)
    index, insert_collisions = perturb & (capacity-1), 0
    while indices[index] >= 0:
        insert_collisions += 1
        perturb >>= 5
        index = (5*index + perturb + 1) & (capacity-1)
    width = 1 if capacity <= 128 else 2 if capacity <= 32768 else 4
    f.update(resize=resize, moved=s["used"]*resize, deleted_entries=(s["nentries"]-s["used"])*resize,
             new_index_bytes=capacity*width*resize, rebuild_collisions=collisions,
             insert_collisions=insert_collisions, expected_capacity=capacity)
    for w in (1, 2):
        f[f"rebuild_collisions_w{w}"] = collisions if width == w else 0
        f[f"rebuild_ge1_w{w}"] = ge1 if width == w else 0
        f[f"rebuild_ge2_w{w}"] = ge2 if width == w else 0
    return f


def insertion_cases():
    pending, rows = [], []
    for capacity in (32, 64, 128, 256, 512, 1024, 2048):
        for layout in ("spread", "same_hash", "deleted_front"):
            for full in (False, True):
                count = capacity*2//3 - int(not full)
                prefix = 1 << (SHIFT*3)
                step = 1 if layout == "spread" else MOD
                keys = [prefix+(i+1)*step for i in range(count)]
                query = prefix+(count+1)*step
                copies = []
                for _ in range(2*len(INSERT_MODELS)):
                    table = dict.fromkeys(keys, 7)
                    if layout == "deleted_front":
                        for key in keys[:count//3]: del table[key]
                    copies.append(table)
                f = insertion_summary(copies[0], query)
                assert f["capacity"] == capacity and f["resize"] == int(full)
                row = dict(case_id=len(rows), layout=layout, **f)
                rows.append(row)
                pending.append((copies, query, row))
    return pending, rows


class WorkKey:
    """Legal dict key with data-dependent work in its equality callback."""
    def __init__(self, value, work): self.value, self.work = value, work
    def __hash__(self): return 42
    def __eq__(self, other):
        accumulator = 0
        for _ in range(self.work): accumulator ^= 1
        return self.value == other.value


CALLBACK_MODELS = {
    "container": ("used", "probes", "equal_hash", "hit"),
    "callback": ("probes", "equal_hash", "callback_iterations", "hit"),
    "audit": ("case_id",),
}


def callback_cases():
    pending, rows = [], []
    for n in (8, 16, 32, 64):
        for work in (0, 8, 64, 256):
            table = {WorkKey(i, work): 7 for i in range(n)}
            s = snapshot(table)
            for hit in (True, False):
                query = WorkKey(n-1 if hit else n, 0)
                perturb, index, probes, comparisons = 42, 42 & (s["capacity"]-1), 0, 0
                while True:
                    probes += 1
                    ix = s["indices"][index]
                    if ix == -1: break
                    comparisons += 1
                    if s["entries"][ix][1].value == query.value: break
                    perturb >>= 5
                    index = (5*index+perturb+1) & (s["capacity"]-1)
                assert (query in table) == hit
                row = dict(case_id=len(rows), used=n, work=work, probes=probes,
                           equal_hash=comparisons, callback_iterations=comparisons*work, hit=int(hit))
                rows.append(row)
                pending.append((table, query, row))
    # Exercise adaptive interpreter specialization before the first marker.
    for table, query, _ in pending:
        for _ in range(8): table.get(query)
    return pending, rows


def build(n, layout, digits):
    prefix = 1 << (SHIFT*(digits-1))
    if layout == "spread": keys = [prefix+i+1 for i in range(n)]
    else: keys = [prefix+(i+1)*MOD for i in range(n*(2 if layout.startswith("deleted") else 1))]
    table = {key: 7 for key in keys}
    if layout == "deleted_front":
        for key in keys[:n]: del table[key]
    if layout == "deleted_back":
        for key in keys[n-1:-1]: del table[key]
    assert len(table) == n
    return table, keys


def lookup_cases():
    pending, rows = [], []
    shapes = [(n, kind, digits) for n in (8, 32, 128, 512)
              for kind in ("spread", "same_hash", "deleted_front", "deleted_back") for digits in (4, 16)]
    shapes += [(n, "same_hash", digits) for n in (8, 32, 128, 512) for digits in (64, 256)]
    for n, kind, digits in shapes:
        table, keys = build(n, kind, digits)
        for hit in (True, False):
            query = clone(keys[-1] if hit else keys[-1]+(1 if kind == "spread" else MOD))
            f, _ = lookup_summary(table, query)
            row = dict(case_id=len(rows), layout=kind, requested_digits=digits, **f)
            rows.append(row)
            pending.append((table, query, row))
    return pending, rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--study", choices=("lookup", "insert", "callback"), default="lookup")
    args = parser.parse_args()
    pending, rows = {"lookup": lookup_cases, "insert": insertion_cases, "callback": callback_cases}[args.study]()
    models = {"lookup": LOOKUP_MODELS, "insert": INSERT_MODELS, "callback": CALLBACK_MODELS}[args.study]
    repeats = 1 if args.study == "insert" else 128 if args.study == "lookup" else 16
    for tables, query, row in pending:
        copy = 0
        for model, names in models.items():
            for _ in range(2):
                table = tables[copy] if args.study == "insert" else tables
                result = measure(args.study+"_"+model, table, query, names, tuple(row[n] for n in names), repeats, int(args.study == "insert"))
                if args.study == "insert":
                    assert result == 0 and len(table) == row["used"]+1 and table[query] == 7
                    assert snapshot(table)["capacity"] == row["expected_capacity"]
                    copy += 1
                else: assert result == row["hit"]*7*repeats
    Path(args.output).write_text(json.dumps(dict(study=args.study, repeats=repeats, cases=rows), indent=2)+"\n")
    print(f"PASS: {len(rows)} {args.study} cases; {len(rows)*len(models)*2*repeats:,} checked operations")


if __name__ == "__main__": main()
