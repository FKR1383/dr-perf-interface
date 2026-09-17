"""Cold-start wall time of the Kimi CLI: N fresh processes per tree, best and median."""
import json, os, statistics, subprocess, sys, tempfile, time, pathlib
PY = "/home/ubuntu/drperf-cases/kimi-venv/bin/python"
DRIVER = str(pathlib.Path(__file__).resolve().parent / "run_kimi.py")
N = int(os.environ.get("N", "9"))
out = []
for tree in sys.argv[1:]:
    ts = []
    for i in range(N):
        env = dict(os.environ, PYTHONPATH=f"/home/ubuntu/drperf-cases/{tree}:/home/ubuntu/drperf/perfmark/python")
        t = time.time()
        r = subprocess.run([PY, DRIVER, "n_tools=17"], capture_output=True, text=True, env=env)
        dt = time.time() - t
        assert r.returncode == 0, r.stderr[-400:]
        ts.append(dt)
    res = {"tree": tree, "n": N, "best_s": round(min(ts), 3), "median_s": round(statistics.median(ts), 3),
           "mean_s": round(statistics.mean(ts), 3)}
    print(json.dumps(res), flush=True)
    out.append(res)
if len(out) == 2:
    a, b = out
    print(f"\n{a['tree']} -> {b['tree']}: best {a['best_s']}s -> {b['best_s']}s "
          f"({(a['best_s']-b['best_s'])/a['best_s']*100:+.1f}%), "
          f"median {a['median_s']}s -> {b['median_s']}s ({(a['median_s']-b['median_s'])/a['median_s']*100:+.1f}%)")
