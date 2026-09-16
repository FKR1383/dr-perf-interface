"""Summarize real drperf regions, including incomplete runs and GX residue."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'lib'))
import derive,runner
path=Path(sys.argv[1]);rs=runner.load_runs(str(path/'raw'))
if not rs['runs']: raise SystemExit('No completed drperf records; wait for the run to finish.')
keys,slots=runner.blocks_of_set(rs)
report={'validity':runner.validity(rs),'regions':{},'counters':[r['data']['drperf'] for r in rs['runs']]}
for name in sorted({k['region'] for k in keys.values()}):
    if name.startswith('_perfmark'):continue
    states,names,dropped=derive.per_state(keys,name)
    vecs,calls=derive.per_trigger(states)
    total=sum(sum(v.values())*calls[x] for x,v in vecs.items())
    gx=sum(c*calls[x] for x,v in vecs.items() for b,c in v.items() if slots[b][0]=='gx_cuda.so')
    regimes=derive.derive(vecs,slots,split=False)
    entry=dict(calls=sum(calls.values()),own_instructions=total,mean=total/sum(calls.values()),
               gx_module_instructions=gx,pcvs=names,states=len(vecs),dropped=dropped)
    if regimes:
        model,=regimes
        entry.update(coefficients=model.a,constant=model.c,
                     max_unexplained=max(model.irr.get(v,0)/sum(vecs[v].values()) for v in model.values),
                     max_reconstruction_error=max(abs(model.total(v)-sum(vecs[v].values()))/sum(vecs[v].values()) for v in model.values))
    report['regions'][name]=entry
report['total_marked_own_instructions']=sum(r['own_instructions'] for r in report['regions'].values())
(path.parent/(path.name+'-summary.json')).write_text(json.dumps(report,indent=2)+'\n')
print('validity:',report['validity'])
for name,r in sorted(report['regions'].items(),key=lambda kv:-kv[1]['own_instructions']):
    print(name,r['calls'],round(r['mean']),round(r['own_instructions']),r.get('max_unexplained','insufficient states'))
