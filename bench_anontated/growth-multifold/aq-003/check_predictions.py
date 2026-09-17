#!/usr/bin/env python3
"""Keep unexplained-cost coverage separate from numerical formula error."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
E=HERE/'evidence'
def read(name):return json.loads((E/name/'metrics.json').read_text())
def predictions(model,measured):
    f=model['formula'];rows=[]
    for s in measured['states']:
        pred=f['constant']+sum(f['coefficients'][k]*v for k,v in s['state'].items())
        actual=s['instructions_per_call'];unexplained=s.get('unexplained_instructions_per_call')
        rows.append({'state':s['state'],'predicted_explained_instructions':pred,'actual_total_instructions':actual,'measured_unexplained_instructions':unexplained,'relative_error_vs_total':(pred-actual)/actual if actual else None,'relative_reconstruction_error':(pred+unexplained-actual)/actual if actual and unexplained is not None else None})
    return rows
train=read('small-train');holdout=read('holdout')
result={'kind':'post-hoc small-to-larger split; annotation previously developed using other sizes up to1538characters','training':'small-train/metrics.json','holdout':'holdout/metrics.json','training_max_input_characters':290,'training_gate_pass':train['gate_pass'],'training_max_unexplained_share':train['max_unexplained_share'],'holdout_sizes_first_measured_after_training_fit':[482,962,1922],'holdout_formula_refit':False,'model_scope':'Only accepted affine component is predicted. Unexplained cost has no out-of-sample guarantee.','holdout_gate_note':'Standalone holdout fit correctly rejects insufficient state count; raw counts are valid, and prediction uses the prior training formula.','training_rows':predictions(train,train),'holdout_rows':predictions(train,holdout),'limitations':['Annotation design used earlier observations; this is not a blinded prospective extrapolation study.','Low unexplained share is not an aggregate formula error bound. Small block tolerances accumulate, and derive.py folds small slopes into constants.','The plain and None controls show large formula errors despite passing the unexplained-share gate; all controls are retained here.']}
(E/'small-to-larger.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'training_gate_pass':train['gate_pass'],'holdout_relative_errors':[r['relative_error_vs_total'] for r in result['holdout_rows']]}))
baseline=read('round2')
optimized=json.loads((HERE.parents[2]/'bench_optimized/growth-multifold/aq-003/evidence/round1/metrics.json').read_text())
reconstruction={'meaning':'Numerical reconstruction error is separate from unexplained-cost share; no data or tolerance settings changed.','baseline':predictions(baseline,baseline),'optimized':predictions(optimized,optimized)}
(E/'formula-reconstruction.json').write_text(json.dumps(reconstruction,indent=2)+'\n')
