#!/usr/bin/env python3
"""Verify the original 207 case bundles stayed unchanged during expansion."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
snapshot=json.loads((Path(__file__).parent/'original-cases.json').read_text())
failures=[]
for name,expected in snapshot['files'].items():
    path=ROOT/name
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:failures.append(name)
result={'original_commit':snapshot['commit'],'original_cases':snapshot['count'],'files_checked':len(snapshot['files']),'changed_or_missing':failures,'preserved':not failures}
print(json.dumps(result,indent=2))
raise SystemExit(bool(failures))
