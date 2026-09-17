"""Bind accepted metrics and invocations to the current experiment sources."""
import hashlib,json,pathlib
HERE=pathlib.Path(__file__).resolve().parents[1];ROOT=HERE.parents[2]
rounds=[
 ROOT/"bench_anontated/growth-multifold/vllm-024/rounds/real-descending-sift",
 ROOT/"bench_anontated/growth-multifold/vllm-024/rounds/real-ascending-baseline",
 ROOT/"bench_anontated/growth-multifold/vllm-024/rounds/real-mixed-baseline",
 HERE/"rounds/guarded-final-descending",HERE/"rounds/guarded-final-ascending",HERE/"rounds/guarded-final-mixed"]
records=[]
for r in rounds:
 invocation=json.loads((r/"invocation.json").read_text());workspace=pathlib.Path(invocation["workspace"]);mismatches=[]
 for rel,expected in invocation["source_hashes"].items():
  path=workspace/rel;actual=hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
  if actual!=expected:mismatches.append({"path":rel,"recorded":expected,"actual":actual})
 metrics=json.loads((r/"metrics.json").read_text())
 records.append({"round":str(r.relative_to(ROOT)),"metrics_sha256":hashlib.sha256((r/"metrics.json").read_bytes()).hexdigest(),"invocation_sha256":hashlib.sha256((r/"invocation.json").read_bytes()).hexdigest(),"gate_pass":metrics["gate_pass"],"returncode":metrics["returncode"],"source_mismatches":mismatches})
snapshot=ROOT/"benchmarks/regions/vllm/upstream/vllm/v1/request.py"
report={"schema_version":1,"status":"passed" if all(x["gate_pass"] and x["returncode"]==0 and not x["source_mismatches"] for x in records) else "failed","comparator_snapshot_sha256":hashlib.sha256(snapshot.read_bytes()).hexdigest(),"rounds":records}
(HERE/"evidence/measurement-audit.json").write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report,indent=2))
if report["status"]!="passed":raise SystemExit(1)
