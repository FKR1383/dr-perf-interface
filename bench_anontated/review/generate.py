#!/usr/bin/env python3
"""Generate a complete, evidence-linked annotated-region document without running cases."""
import ast
import collections
import difflib
import hashlib
import html
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SECTIONS = [
    'Annotation worked and optimization was accepted',
    'Annotation worked; optimization was not accepted or not attempted',
    'Annotation did not qualify',
    'Blocked or unmeasured; no successful annotation claim',
]

def read(path):
    return json.loads(path.read_text()) if path and path.is_file() else {}

def rel(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()

def link(path):
    return os.path.relpath(path, OUT)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def snippet(path, case, manifest, pristine):
    text = path.read_text()
    lines = text.splitlines()
    if manifest['language'] == 'python':
        tree = ast.parse(text)
        marks = [n for n in ast.walk(tree) if isinstance(n, (ast.With, ast.AsyncWith))
                 and any(isinstance(i.context_expr, ast.Call)
                         and ast.unparse(i.context_expr.func) == 'perfmark.region'
                         and i.context_expr.args and isinstance(i.context_expr.args[0], ast.Constant)
                         and i.context_expr.args[0].value == case for i in n.items)]
        assert len(marks) == 1, (path, len(marks))
        mark = marks[0]
        parents = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and n.lineno <= mark.lineno <= mark.end_lineno <= n.end_lineno]
        owner = min(parents, key=lambda n:n.end_lineno-n.lineno) if parents else mark
        start = min([owner.lineno] + [n.lineno for n in getattr(owner, 'decorator_list', [])])
        end = owner.end_lineno
        call = next(i.context_expr for i in mark.items if isinstance(i.context_expr, ast.Call)
                    and ast.unparse(i.context_expr.func) == 'perfmark.region')
        pcvs = [{'name': k.arg or '**', 'expression': ast.get_source_segment(text, k.value)} for k in call.keywords]
        scope = 'Enclosing function, including the complete marked region and local PCV definitions'
        marker_line = mark.lineno
    else:
        markers = [i for i,l in enumerate(lines) if 'DRPERF_BENCH_REGION' in l and f'"{case}"' in l]
        assert len(markers) == 1, path
        original = pristine.read_text().splitlines()
        mapping = difflib.SequenceMatcher(a=original, b=lines, autojunk=False).get_matching_blocks()
        def mapped(n):
            for block in mapping:
                if block.a <= n < block.a + block.size:
                    return block.b + n - block.a
            raise ValueError(f'Cannot map original line {n+1}: {path}')
        start = min(mapped(manifest['region']['start_line']-1), markers[0]) + 1
        end = max(mapped(manifest['region']['end_line']-1), markers[0]) + 1
        marker_line = markers[0]+1
        pcvs = []
        scope = 'Exact collected C++ region with its empty marker; runtime blocked'
    return {'path': rel(path), 'sha256': digest(path), 'start_line': start, 'end_line': end,
            'marker_line': marker_line, 'scope': scope, 'pcvs': pcvs,
            'code': '\n'.join(lines[start-1:end])}

def measured(path, workspace, source):
    data = read(path)
    if not data:
        return None
    inv_path = path.parent/'invocation.json'
    invocation = read(inv_path)
    hashes = invocation.get('source_hashes', {})
    mismatch = []
    for name, sha in hashes.items():
        if name == source or name.startswith('tests/'):
            p = workspace/name
            if not p.is_file() or digest(p) != sha:
                mismatch.append(name)
    source_bound = source in hashes and not mismatch
    return {'path': rel(path), 'invocation': rel(inv_path) if invocation else None,
            'sha256': digest(path), 'source_and_tests_match': source_bound,
            'mismatches': mismatch, 'gate_pass': bool(data.get('gate_pass')),
            'returncode': data.get('returncode'), 'max_unexplained_share': data.get('max_unexplained_share'),
            'distinct_states': data.get('distinct_states'), 'required_states': data.get('required_states'),
            'formula': data.get('formula'), 'gate_reasons': data.get('gate_reasons', []),
            'validity_warnings': data.get('validity_warnings', []), 'states': data.get('states', [])}

def total(m):
    return sum(s['calls']*s['instructions_per_call'] for s in m['states'])

def flatten(value):
    if isinstance(value, str): return [value]
    if isinstance(value, list): return [s for v in value for s in flatten(v)]
    return []

def build():
    manifests = {read(p)['id']: p for p in (ROOT/'benchmarks/regions').glob('*/cases/*/case.json')}
    # Some expanded workloads reuse a parent identity without copying case.json.
    workspaces = sorted(p for p in (ROOT/'bench_anontated').glob('*/*')
                        if p.is_dir() and p.name in manifests
                        and (p/read(manifests[p.name])['source']['path']).is_file())
    rows = []
    for workspace in workspaces:
        case, group = workspace.name, workspace.parent.name
        if case not in manifests: continue
        mp = manifests[case]; manifest = read(mp)
        pristine = (mp.parent/manifest['source']['snapshot']).resolve()
        source = manifest['source']['path']
        result_path = workspace/'result.json'; result = read(result_path)
        opt_dir = ROOT/'bench_optimized'/group/case
        opt_result_path = opt_dir/'result.json'; opt_result = read(opt_result_path)
        final = result.get('final_measurement')
        if group == 'growth-multifold' and case == 'aq-003':
            final_path = (opt_dir/opt_result['baseline_measurement']).resolve()
        else:
            final_path = workspace/final if final else None
        measurement = measured(final_path, workspace, source) if final_path else None
        region = snippet(workspace/source, case, manifest, pristine)
        worked = bool(measurement and measurement['gate_pass'] and measurement['returncode'] == 0
                      and measurement['source_and_tests_match'] and not measurement['validity_warnings'])
        optimization = {'status': opt_result.get('status', 'not-attempted'), 'accepted': False}
        if opt_result:
            optimization['result'] = rel(opt_result_path)
            optimization['reason'] = opt_result.get('reason', '')
            if opt_result.get('baseline_measurement') and opt_result.get('optimized_measurement'):
                before = measured((opt_dir/opt_result['baseline_measurement']).resolve(), workspace, source)
                after = measured((opt_dir/opt_result['optimized_measurement']).resolve(), opt_dir, source)
                optimization.update(baseline=before, measurement=after)
                if before and after and before['states'] and after['states']:
                    key = lambda s:json.dumps(s['state'], sort_keys=True)
                    b = {key(s):s['calls'] for s in before['states']}; a = {key(s):s['calls'] for s in after['states']}
                    optimization['same_states_and_calls'] = b == a
                    if b == a and total(after): optimization['instruction_ratio'] = total(before)/total(after)
                optimization['accepted'] = bool((opt_result.get('accepted') or opt_result.get('status') == 'accepted')
                    and before and after and before['source_and_tests_match'] and after['source_and_tests_match']
                    and after['returncode'] == 0 and not after['validity_warnings']
                    and optimization.get('same_states_and_calls'))
            if (opt_dir/source).is_file():
                optimization['region'] = snippet(opt_dir/source, case, manifest, pristine)
        section = 0 if worked and optimization['accepted'] else 1 if worked else 2 if measurement else 3
        notes = flatten(result.get('notes')) + flatten(result.get('reason')) + flatten(result.get('optimization_review'))
        if isinstance(result.get('evidence'), str): notes.append(result['evidence'])
        notes += flatten(opt_result.get('limitations')) + flatten(opt_result.get('scope'))
        if result.get('surrogate_warning'): notes.append(result['surrogate_warning'])
        rows.append({'key': f'{group}/{case}', 'anchor': f'{group}-{case}', 'case': case, 'group': group,
                     'symbol': manifest['region']['symbol'], 'language': manifest['language'],
                     'source': manifest['source'], 'status': result.get('status', 'annotation-qualified' if worked else 'unmeasured'),
                     'worked': worked, 'section': section, 'region': region, 'measurement': measurement,
                     'optimization': optimization, 'notes': list(dict.fromkeys(notes)),
                     'result': rel(result_path) if result_path.is_file() else rel(workspace/'README.md'),
                     'workload': manifest.get('workload',{}).get('description',''),
                     'experiment_readme': rel(workspace/'README.md') if (workspace/'README.md').exists() else None})
    rows.sort(key=lambda r:(r['section'], -(r['optimization'].get('instruction_ratio') or 0) if r['section']==0 else 0, r['group'], r['case']))
    covered = {r['case'] for r in rows}
    pending = collections.Counter(p.parents[2].name for cid,p in manifests.items() if cid not in covered)
    return rows, dict(pending)

def percent(value):
    return 'not measured' if value is None else f'{value*100:.2f}%'

def formula(m):
    f = m.get('formula') if m else None
    if not f: return 'No accepted affine formula recorded.'
    terms = [f'{v:.6g} * {k}' for k,v in f.get('coefficients',{}).items()]
    terms.append(f"{f.get('constant',0):.6g}")
    return 'estimated cost = ' + ' + '.join(terms) + ' + unexplained'

def ann_label(row):
    return 'PASS' if row['worked'] else 'DID NOT QUALIFY' if row['measurement'] else 'BLOCKED / UNMEASURED'

def opt_label(row):
    opt=row['optimization']
    if opt['accepted']:
        return f"accepted; {opt.get('instruction_ratio',0):.2f}x fewer target instructions; optimized gate {'PASS' if opt['measurement']['gate_pass'] else 'FAIL'}"
    return opt['status']

def candidate_notes(opt):
    m = opt.get('measurement')
    if not m: return 'No final candidate measurement recorded.'
    match = m['source_and_tests_match']
    return ('Displayed candidate source and tests match the recorded invocation: '
            + ('yes.' if match else 'NO. Mismatches: '+', '.join(m['mismatches'])
               + '. The recorded metrics do not validate this exact displayed candidate/test combination.'))

def prose(row):
    m=row['measurement']; lines=[f"Annotation: {ann_label(row)}. Recorded status: {row['status']}.", f"Optimization: {opt_label(row)}."]
    if m:
        lines.append(f"Maximum unexplained share: {percent(m['max_unexplained_share'])}; states: {m['distinct_states']} (required {m['required_states']}); exit code: {m['returncode']}.")
        lines.append('Displayed source and tests match the final invocation: '+('yes.' if m['source_and_tests_match'] else 'NO — missing or mismatched hashes.'))
        lines += m['gate_reasons'] + m['validity_warnings']
    return lines + row['notes']

def fence(code, language):
    import re
    ticks='`'*max(3,1+max([len(s) for s in re.findall(r'`+',code)] or [0]))
    return f'{ticks}{language}\n{code}\n{ticks}'

INTRO = ('“Worked” means the final annotation passed the recorded 5% unexplained-cost gate, '
         'with a successful workload and matching source/test hashes. Accepted optimizations are listed first within that group. '
         'Annotation success and optimization success are separate: an accepted optimization can still have a failing optimized model, which is shown explicitly. '
         'Results concern observed workloads, not universal cost proofs or application speedups. Low unexplained share does not bound numerical prediction error; '
         'the expanded cookie experiment documents large reconstruction errors on cheap controls. '
         'Expanded workloads remain separate entries from their earlier trials, so a later success does not erase an earlier failure. Coefficients are rounded for display; linked metrics retain their full precision.')

def markdown(rows,pending):
    lines=['# Annotated code regions: successful cases first','',INTRO,'',
           f'{len(rows)} experiment entries / {len({r["case"] for r in rows})} distinct case IDs. '
           f'{sum(r["worked"] for r in rows)} annotations pass; '
           f'{sum(r["section"]==2 for r in rows)} measured annotations did not qualify; '
           f'{sum(r["section"]==3 for r in rows)} entries are blocked or unmeasured.','',
           f'The {sum(pending.values())} newer collection cases have empty markers and no annotation experiment yet: '+', '.join(f'{g}: {n}' for g,n in sorted(pending.items()))+'.','',
           'Code below is copied verbatim from the experiment sources, without truncation. Python entries include the enclosing function so local PCV definitions are visible. C++ blocked entries retain their empty markers. Earlier rounds and helper definitions are available through the linked files.','',
           '[Searchable HTML version](annotated-regions.html) · [Machine-readable index](index.json)','',
           '## Contents','', '| Case / experiment | Annotation | Max unexplained | Optimization |','| --- | --- | ---: | --- |']
    for r in rows:
        m=r['measurement']
        lines.append(f"| [{r['key']}](#{r['anchor']}) | {ann_label(r)} | {percent(m['max_unexplained_share']) if m else '—'} | {opt_label(r)} |")
    for section,title in enumerate(SECTIONS):
        lines += ['',f'## {title}','']
        for r in rows:
            if r['section']!=section: continue
            s=r['region'];m=r['measurement']
            lines += [f'<a id="{r["anchor"]}"></a>',f'### {r["key"]}: `{r["symbol"]}`','']
            lines += [p+'\n' for p in prose(r)]
            lines += [f"Source: [{s['path']}:{s['start_line']}–{s['end_line']}]({link(ROOT/s['path'])}); marker line {s['marker_line']}. Upstream revision `{r['source']['revision']}`.", '',
                      f"[Outcome]({link(ROOT/r['result'])})" + (f" · [Final metrics]({link(ROOT/m['path'])}) · [Invocation]({link(ROOT/m['invocation'])})" if m and m['invocation'] else '') + (f" · [Experiment notes]({link(ROOT/r['experiment_readme'])})" if r['experiment_readme'] else ''), '',
                      '**PCVs in the source:**','']
            lines += [f"- `{p['name']} = {p['expression']}`" for p in s['pcvs']] or ['None declared.']
            lines += ['',fence(formula(m),'text'),'',s['scope']+':','',fence(s['code'],'python' if r['language']=='python' else 'cpp'),'']
            opt=r['optimization']
            if opt.get('region'):
                osrc=opt['region']
                lines += ['**Optimized candidate** ('+('accepted' if opt['accepted'] else 'not accepted')+'). '+opt.get('reason',''),'',candidate_notes(opt),'',
                          f"[Candidate source]({link(ROOT/osrc['path'])}) · [Optimization outcome]({link(ROOT/opt['result'])})",'',
                          fence(formula(opt.get('measurement')),'text'),'',fence(osrc['code'],'python' if r['language']=='python' else 'cpp'),'']
    return '\n'.join(lines)+'\n'

def html_doc(rows,pending):
    esc=html.escape
    def a(path,label):return f'<a href="{esc(link(ROOT/path),quote=True)}">{esc(label)}</a>'
    counts=collections.Counter(r['section'] for r in rows)
    parts=['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
           '<title>Annotated code regions</title><style>body{font:16px/1.55 system-ui,sans-serif;margin:0;background:#f6f7fa;color:#182433}header,main{max-width:1180px;margin:auto;padding:24px}header{padding-bottom:8px}h1{line-height:1.2}nav{position:sticky;top:0;background:#fff;border-block:1px solid #d6dce4;padding:12px 24px;z-index:2;display:flex;gap:10px;flex-wrap:wrap;align-items:center}input{flex:1;min-width:240px}input,select,button{font:inherit;padding:7px;border:1px solid #b7c1cc;border-radius:5px}article{background:#fff;border:1px solid #d6dce4;border-radius:8px;padding:20px;margin:18px 0}h3{margin:0 0 8px;overflow-wrap:anywhere}pre{background:#15202e;color:#e0e9f1;padding:16px;overflow:auto;font:13px/1.6 ui-monospace,monospace;tab-size:4}code{overflow-wrap:anywhere}a{color:#175d98}summary{cursor:pointer;font-weight:600;padding:10px 0}.pass{color:#176342}.fail{color:#a53628}.muted{color:#536273}.pill{display:inline-block;border-radius:12px;background:#e8eef5;padding:2px 10px;margin:0 6px 6px 0}details[open]>summary{border-bottom:1px solid #dde4ed}section[hidden],article[hidden]{display:none}@media print{nav{display:none}body{background:white}pre{white-space:pre-wrap;color:black;background:#f4f4f4}article{break-inside:auto}}</style>',
           '<header><h1>Annotated code regions</h1><p>Successful annotations first, with accepted optimizations at the top.</p>',
           f'<p>{esc(INTRO)}</p><p><b>{len(rows)}</b> experiment entries · <b>{sum(r["worked"] for r in rows)}</b> passing annotations · <b>{counts[2]}</b> measured cases that did not qualify · <b>{counts[3]}</b> blocked or unmeasured.</p>',
           f'<p class="muted">The {sum(pending.values())} newer collection cases still have empty markers and no annotation experiment. This document includes all existing experiment exports and both expanded workloads. Code is included in full.</p>',
           '<p><a href="annotated-regions.md">Markdown document</a> · <a href="index.json">Evidence index</a></p></header>',
           '<nav><input id="search" type="search" aria-label="Search cases and code" placeholder="Search case, function, PCV, or code…"><select id="status" aria-label="Filter outcome"><option value="all">All outcomes</option>'+''.join(f'<option value="{i}">{esc(t)}</option>' for i,t in enumerate(SECTIONS))+'</select><button id="expand">Expand visible code</button><button id="collapse">Collapse code</button><span id="count" aria-live="polite"></span></nav><main>']
    for i,title in enumerate(SECTIONS):
        parts.append(f'<section data-section="{i}"><h2>{esc(title)} ({counts[i]})</h2>')
        for r in rows:
            if r['section']!=i:continue
            s=r['region'];m=r['measurement'];opt=r['optimization']
            parts += [f'<article id="{r["anchor"]}" data-outcome="{i}"><h3>{esc(r["key"])} · {esc(r["symbol"])}</h3>',
                      f'<span class="pill {"pass" if r["worked"] else "fail"}">{esc(ann_label(r))}</span><span class="pill">{esc(opt_label(r))}</span>']
            parts += [f'<p>{esc(p)}</p>' for p in prose(r)[2:]]
            parts += [f'<p>{a(s["path"],s["path"])} · lines {s["start_line"]}–{s["end_line"]}, marker {s["marker_line"]}<br>Upstream: <code>{esc(r["source"]["revision"])}</code></p>',
                      f'<p>{a(r["result"],"Outcome")}' + (f' · {a(m["path"],"Final metrics")} · {a(m["invocation"],"Invocation")}' if m and m['invocation'] else '') + (f' · {a(r["experiment_readme"],"Experiment notes")}' if r['experiment_readme'] else '') + '</p>',
                      '<p><b>PCVs:</b> '+ ('; '.join('<code>'+esc(p['name']+' = '+p['expression'])+'</code>' for p in s['pcvs']) or 'none declared')+'</p>',
                      '<pre>'+esc(formula(m))+'</pre>',
                      f'<details {"open" if r["worked"] else ""}><summary>Annotated source · {esc(s["scope"])}</summary><pre><code>{esc(s["code"])}</code></pre></details>']
            if opt.get('region'):
                osrc=opt['region'];label='accepted' if opt['accepted'] else 'not accepted'
                parts += [f'<details><summary>Optimized candidate · {label}</summary><p>{esc(opt.get("reason",""))}</p><p>{esc(candidate_notes(opt))}</p><p>{a(osrc["path"],"Candidate source")} · {a(opt["result"],"Optimization outcome")}</p><pre>{esc(formula(opt.get("measurement")))}</pre><pre><code>{esc(osrc["code"])}</code></pre></details>']
            parts.append('</article>')
        parts.append('</section>')
    parts += ['</main><script>const cards=[...document.querySelectorAll("article")];const search=document.querySelector("#search"),status=document.querySelector("#status");const texts=cards.map(c=>c.textContent.toLowerCase());function filter(){const q=search.value.toLowerCase();cards.forEach((c,i)=>{c.hidden=!(status.value==="all"||c.dataset.outcome===status.value)||!texts[i].includes(q)});document.querySelectorAll("section").forEach(s=>s.hidden=![...s.querySelectorAll("article")].some(c=>!c.hidden));document.querySelector("#count").textContent=cards.filter(c=>!c.hidden).length+" / "+cards.length+" entries"}search.addEventListener("input",filter);status.addEventListener("change",filter);document.querySelector("#expand").onclick=()=>cards.filter(c=>!c.hidden).forEach(c=>c.querySelectorAll("details").forEach(d=>d.open=true));document.querySelector("#collapse").onclick=()=>document.querySelectorAll("details").forEach(d=>d.open=false);window.addEventListener("beforeprint",()=>document.querySelectorAll("details").forEach(d=>d.open=true));filter();</script></html>']
    return '\n'.join(parts)+'\n'

def main():
    rows,pending=build()
    assert rows and len({r['key'] for r in rows}) == len(rows)
    for r in rows:
        assert r['region']['code'] and r['region']['start_line'] <= r['region']['marker_line'] <= r['region']['end_line']
        if r['worked']: assert r['measurement']['source_and_tests_match']
    (OUT/'annotated-regions.md').write_text(markdown(rows,pending))
    (OUT/'annotated-regions.html').write_text(html_doc(rows,pending))
    index={'experiment_entries':len(rows),'unique_cases':len({r['case'] for r in rows}),
           'section_counts':{t:sum(r['section']==i for r in rows) for i,t in enumerate(SECTIONS)},
           'not_yet_annotated_groups':pending,'entries':rows}
    (OUT/'index.json').write_text(json.dumps(index,indent=2)+'\n')
    print(json.dumps({k:v for k,v in index.items() if k!='entries'}))

if __name__=='__main__':main()
