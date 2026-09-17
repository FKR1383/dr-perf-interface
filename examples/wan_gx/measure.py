"""Run drperf inside GX's emu wrapper, keeping evidence instead of temporary output."""
import json
import subprocess
import time
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'lib'))
import runner
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False)
# Preserve complete diagnostic logs; the ordinary CLI keeps only a short tail.
def run_process(cmd, env, timeout):
    start=time.monotonic()
    with (out/'stdout.txt').open('wb') as stdout, (out/'stderr.txt').open('wb') as stderr:
        try:
            rc=subprocess.run(cmd,env=env,stdout=stdout,stderr=stderr,timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            rc=124
            stderr.write(b'\n[drperf: timeout]\n')
    return (rc,time.monotonic()-start,
            (out/'stdout.txt').read_text(errors='replace')[-2000:],
            (out/'stderr.txt').read_text(errors='replace')[-2000:])
runner.run_process=run_process
rc,log,files=runner.run(sys.argv[2:],str(out/'raw'),timeout=540)
(out/'output.txt').write_text(log)
print(log,flush=True)
if files:
    rs=runner.load_runs(str(out/'raw'))
    print(json.dumps({'validity':runner.validity(rs),'counters':[r['data']['drperf'] for r in rs['runs']]},indent=2))
for path in out.rglob('*'):
    if path.is_file(): path.chmod(0o644)
raise SystemExit(rc)
