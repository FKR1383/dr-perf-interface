"""Turn archived vLLM/Wan marker locations into empty-marker source cases.

Archived PCV expressions are kept only as historical reference notes. Target
code comes from pinned pristine Git revisions, never from the marked copies.
"""
import argparse
import ast
import copy
import difflib
import hashlib
import json
import os
import subprocess
from pathlib import Path

DESTINATION=Path(__file__).resolve().parents[1]/'regions'
PROJECTS={
    'vllm': {'repository':'https://github.com/vllm-project/vllm',
             'revision':'2cf0a6915ce544dc493a0990f2ea38d81601128a',
             'repo':'@drperf/third_party/vllm-cpu/vllm', 'prefix':'',
             'marked':['vllm-cpu-src','vllm-cpu-req','vllm-cpu-batch','vllm-cpu-samp',
                       'vllm-cpu-out','vllm-cpu-kv','vllm-cpu-sched','vllm-cpu-spec'],
             'workload':'Exercise the named vLLM CPU execution path with a small cached model and bounded request batches. Adjust request options to reach this method; no particular dependency is supplied.'},
    'wan': {'repository':'https://github.com/huggingface/diffusers',
            'revision':'c5469b7ceb606edd7ba6570dcd17d38590a18db6',
            'repo':'videogen/diffusers','prefix':'src/',
            'marked':['videogen/wan-src','videogen/wan-more','videogen/wan-tax','videogen/wan-t5'],
            'workload':'Exercise the named diffusers Wan method with a tiny random model on CPU. Use a bounded video or prompt-encoding call appropriate to this method; full model downloads are unnecessary.'},
}


def functions(tree):
    result={}
    def walk(node,context=()):
        if isinstance(node,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)):
            context += (node.name,)
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
            result.setdefault('.'.join(context),[]).append(node)
        for child in ast.iter_child_nodes(node):
            walk(child,context)
    walk(tree)
    return result


def is_marker(node):
    return (isinstance(node,ast.With) and len(node.items)==1 and
            isinstance(node.items[0].context_expr,ast.Call) and
            ast.unparse(node.items[0].context_expr.func)=='perfmark.region')


class StripMarkers(ast.NodeTransformer):
    def visit_With(self,node):
        if is_marker(node):
            result=[]
            for child in node.body:
                transformed=self.visit(child)
                if isinstance(transformed,list):result.extend(transformed)
                elif transformed is not None:result.append(transformed)
            return result
        return self.generic_visit(node)


def cleaned_body(marker):
    module=ast.Module(body=copy.deepcopy(marker.body),type_ignores=[])
    return StripMarkers().visit(module).body


def matching_sequence(function,body):
    if not body or all(isinstance(n,ast.Pass) for n in body):
        return []
    wanted=[ast.dump(n) for n in body]
    matches=[]
    for node in ast.walk(function):
        for _,value in ast.iter_fields(node):
            if not isinstance(value,list) or not value or not all(isinstance(n,ast.stmt) for n in value):continue
            for i in range(len(value)-len(body)+1):
                if [ast.dump(n) for n in value[i:i+len(body)]]==wanted:
                    matches.append(value[i:i+len(body)])
    return matches


def add_marker(source,body,name):
    lines=source.splitlines(keepends=True)
    start,end=body[0].lineno-1,body[-1].end_lineno
    indent=lines[start][:len(lines[start])-len(lines[start].lstrip())]
    if '\t' in indent:raise ValueError('tab-indented region needs manual review')
    marked=lines[:start]+[indent+f'with perfmark.region("{name}"):\n']+[
        '    '+line if line.strip() else line for line in lines[start:end]]+lines[end:]
    tree=ast.parse(source)
    insert=tree.body[0].lineno-1
    for index,node in enumerate(tree.body):
        if (index==0 and isinstance(node,ast.Expr) and isinstance(node.value,ast.Constant) and isinstance(node.value.value,str)) or (
            isinstance(node,ast.ImportFrom) and node.module=='__future__'):
            insert=node.end_lineno
        else:break
    marked.insert(insert,'import perfmark\n')
    result=''.join(marked)
    ast.parse(result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path)
    parser.add_argument('--drperf',type=Path,default=Path(__file__).resolve().parents[2])
    args=parser.parse_args()
    for project,spec in PROJECTS.items():
        group=DESTINATION/project
        repo=args.drperf/spec['repo'][len('@drperf/'):] if spec['repo'].startswith('@drperf/') else args.archive/spec['repo']
        discovered={}
        for variant in spec['marked']:
            base=args.archive/variant
            for path in sorted(base.rglob('*.py')):
                raw=path.read_text(errors='replace')
                if 'with perfmark.region' not in raw:continue
                try:tree=ast.parse(raw)
                except SyntaxError:continue
                for symbol,nodes in functions(tree).items():
                    for function in nodes:
                        # Walk the named function only; nested definitions are
                        # separately addressed by their own qualified symbols.
                        def local_walk(node):
                            yield node
                            for child in ast.iter_child_nodes(node):
                                if isinstance(child,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):continue
                                yield from local_walk(child)
                        markers=[m for m in local_walk(function) if is_marker(m)]
                        if markers:
                            key=(spec['prefix']+path.relative_to(base).as_posix(),symbol)
                            bucket=discovered.setdefault(key,[])
                            for marker in markers:
                                call=marker.items[0].context_expr
                                if not call.args or not isinstance(call.args[0],ast.Constant):continue
                                bucket.append({'name':str(call.args[0].value),'body':cleaned_body(marker),
                                               'call':ast.unparse(call),'file':str(path.relative_to(args.archive))})
        count=0;skipped=[];seen=set();cache={}
        for (original,symbol),markers in sorted(discovered.items()):
            if original not in cache:
                proc=subprocess.run(['git','-C',str(repo),'show',spec['revision']+':'+original],capture_output=True)
                cache[original]=proc.stdout.decode() if proc.returncode==0 else None
            source=cache[original]
            if source is None:
                skipped.append({'path':original,'symbol':symbol,'reason':'no pristine source file'});continue
            tree=ast.parse(source)
            matches=functions(tree).get(symbol,[])
            if len(matches)!=1:
                skipped.append({'path':original,'symbol':symbol,'reason':'ambiguous or missing pristine function'});continue
            function=matches[0]
            if isinstance(function,ast.AsyncFunctionDef) or any(isinstance(n,(ast.Yield,ast.YieldFrom)) for n in ast.walk(function)):
                skipped.append({'path':original,'symbol':symbol,'reason':'suspending region requires separate marker lifetime review'});continue
            body=function.body
            if isinstance(body[0],ast.Expr) and isinstance(body[0].value,ast.Constant) and isinstance(body[0].value.value,str):body=body[1:]
            if not body:continue
            targets=[(body,'function',markers)]
            for marker in markers:
                candidates=matching_sequence(function,marker['body'])
                if len(candidates)==1:
                    targets.append((candidates[0],'block',[marker]))
            for selected,kind,evidence in targets:
                span=(original,selected[0].lineno,selected[-1].end_lineno)
                if span in seen:continue
                seen.add(span)
                count+=1;id=f'{project}-{count:03d}'
                case=group/'cases'/id;case.mkdir(parents=True,exist_ok=True)
                snapshot=group/'upstream'/original;snapshot.parent.mkdir(parents=True,exist_ok=True)
                snapshot.write_text(source)
                modified=add_marker(source,selected,id)
                patch=''.join(difflib.unified_diff(source.splitlines(True),modified.splitlines(True),
                                                fromfile='a/'+original,tofile='b/'+original))
                (case/'region.patch').write_text(patch)
                url=f'{spec["repository"]}/blob/{spec["revision"]}/{original}'
                data={'schema_version':1,'id':id,'title':symbol+(' body' if kind=='function' else ' region'),
                      'language':'python','source':{'repository':spec['repository'],'revision':spec['revision'],
                       'path':original,'snapshot':os.path.relpath(snapshot,case),
                       'sha256':hashlib.sha256(snapshot.read_bytes()).hexdigest()},
                      'region':{'symbol':symbol,'start_line':span[1],'end_line':span[2],'kind':kind},
                      'marker':{'kind':'python-context','name':id,'pcvs':[]},
                      'status':'collected','build_status':'not-built',
                      'workload':{'description':spec['workload'],'command':None},
                      'source_family':f'{project}:{original}:{symbol}',
                      'citations':[url]}
                previous=case/'case.json'
                if previous.exists():
                    old=json.loads(previous.read_text())
                    if old.get('source',{}).get('sha256')==data['source']['sha256'] and old.get('region')==data['region']:
                        if 'tests' in old:
                            data['tests']=old['tests']
                            data['workload']=old['workload']
                        if 'phase' in old:data['phase']=old['phase']
                (case/'case.json').write_text(json.dumps(data,indent=2)+'\n')
                (case/'task.md').write_text(f'# {symbol}\n\nInspect the marked {kind} in `{original}` at the pinned revision.\nThe marker has no PCVs; identify useful state expressions for its cost.\n\n{spec["workload"]}\n\nApply this case patch independently in an upstream checkout. The snapshot is\nsource context, not a standalone program. Install the matching project\ndependencies, make `perfmark/python` importable and build libperfmark before\nmeasuring. See `case.json` for the test command and recorded validation status.\nKeep the code behavior unchanged while adding observation state.\n\nThe `tests/` bundle supplies small inputs and correctness assertions. Keep these\nchecks passing while investigating the empty marker.\n')
                refs='\n'.join(sorted({f'- `{m["file"]}`: `{m["call"]}`' for m in evidence}))
                (case/'reference.md').write_text(f'# Collection provenance\n\nSource: [{symbol}]({url}).\n\nThis location was selected from earlier annotations in the local experiment\narchive. The following expressions are historical hypotheses, not a reviewed\nanswer key or a complexity guarantee:\n\n{refs}\n\nThe source snapshot is exported from pristine Git, and this case patch starts\nwith zero PCVs. Whole-function cases and child-block cases share a source family\nand must remain together when splitting or aggregating a future evaluation.\n')
        for license in ('LICENSE','LICENSE.md','NOTICE'):
            proc=subprocess.run(['git','-C',str(repo),'show',spec['revision']+':'+license],capture_output=True)
            if proc.returncode==0:
                (group/'upstream'/license).write_bytes(proc.stdout)
        (group/'collection.json').write_text(json.dumps({'project':project,'regions':count,'skipped':skipped,
            'note':'Whole-function and matched child-block targets are related, not statistically independent.'},indent=2)+'\n')
        print(f'{project}: {count} collected source regions; {len(skipped)} functions require manual review')


if __name__=='__main__':main()
