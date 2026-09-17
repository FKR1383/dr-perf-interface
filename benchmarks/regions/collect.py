#!/usr/bin/env python3
"""List, verify, and export collected source regions with empty PCV markers.

This tool does not run the target projects or an agent evaluation pipeline.
"""
import argparse
import ast
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def cases():
    return sorted(ROOT.glob('*/cases/*/case.json'))


def load(path):
    return json.loads(path.read_text())


def snapshot_path(path, manifest):
    snapshot = (path.parent / manifest['source']['snapshot']).resolve()
    if not snapshot.is_relative_to(ROOT):
        raise ValueError(f'{path}: source snapshot is outside the collection')
    return snapshot


def test_assets(path,data):
    tests=data.get('tests')
    if tests is None:
        return []
    command=tests.get('command')
    if not isinstance(command,list) or not command or not all(isinstance(x,str) for x in command):
        raise ValueError('tests.command must be a nonempty argument list')
    if tests.get('validation',{}).get('status') not in ('not-run','behavior-checked','region-verified'):
        raise ValueError('unknown test validation status')
    assets=[]
    for name in tests.get('files',[]):
        rel=Path(name)
        if rel.is_absolute() or '..' in rel.parts or not rel.parts or rel.parts[0]!='tests':
            raise ValueError('test files must be inside the case tests/ directory')
        source=path.parent/rel
        if not source.is_file():raise ValueError(f'missing test file {name}')
        assets.append((source,rel))
    for resource in tests.get('resources',[]):
        source=(path.parent/resource['source']).resolve()
        rel=Path(resource['destination'])
        if not source.is_relative_to(ROOT) or not source.is_file():
            raise ValueError('shared test resource must exist inside the collection')
        if rel.is_absolute() or '..' in rel.parts or not rel.parts or rel.parts[0]!='tests':
            raise ValueError('shared test destination must be inside tests/')
        if hashlib.sha256(source.read_bytes()).hexdigest()!=resource['sha256']:
            raise ValueError('shared test resource hash mismatch')
        assets.append((source,rel))
    destinations=[str(rel) for _,rel in assets]
    if not assets or len(destinations)!=len(set(destinations)):
        raise ValueError('tests need declared assets with unique destinations')
    if not any(arg in destinations for arg in command):
        raise ValueError('test command must invoke a declared test asset')
    for source,_ in assets:
        if source.suffix=='.py':ast.parse(source.read_bytes(),filename=str(source))
    return assets


def apply(path, manifest, destination):
    original = Path(manifest['source']['path'])
    if original.is_absolute() or '..' in original.parts:
        raise ValueError('source path must be relative to its upstream checkout')
    target = destination / original
    patch = (path.parent/'region.patch').resolve()
    # Git applies path-prefix filtering when cwd belongs to a surrounding
    # worktree. Stage independently so exports work inside this repository too.
    with tempfile.TemporaryDirectory(prefix='drperf-region-apply-') as tmp:
        staging=Path(tmp)
        staged=staging/original
        staged.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(snapshot_path(path,manifest),staged)
        stats=subprocess.check_output(['git','apply','--numstat',str(patch)],cwd=staging,text=True)
        touched=[line.split('\t',2)[-1] for line in stats.splitlines()]
        if touched != [original.as_posix()]:
            raise ValueError('a case patch must touch only its declared source file')
        subprocess.run(['git','apply','--check',str(patch)],cwd=staging,check=True,capture_output=True)
        subprocess.run(['git','apply',str(patch)],cwd=staging,check=True,capture_output=True)
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(staged,target)
    return target


class RemoveEmptyMarker(ast.NodeTransformer):
    def __init__(self, name):
        self.name = name
        self.markers = 0
        self.imports = 0
        self.spans = []

    def visit_Import(self,node):
        if len(node.names)==1 and node.names[0].name=='perfmark' and node.names[0].asname is None:
            self.imports += 1
            return None
        return node

    def visit_With(self,node):
        if len(node.items)==1:
            call=node.items[0].context_expr
            if isinstance(call,ast.Call) and ast.unparse(call.func)=='perfmark.region':
                if len(call.args)!=1 or call.keywords or not isinstance(call.args[0],ast.Constant) or call.args[0].value!=self.name:
                    raise ValueError('marker must contain only the region name, with no PCVs')
                self.markers += 1
                # Patches add one preceding import and one with-header line.
                self.spans.append((node.lineno-1,node.end_lineno-2))
                return [self.visit(n) for n in node.body]
        return self.generic_visit(node)


def check(path):
    data=load(path)
    test_assets(path,data)
    if data['schema_version']!=1 or data['marker']['pcvs']!=[]:
        raise ValueError('expected version 1 and an empty PCV list')
    if data['id']!=data['marker']['name']:
        raise ValueError('case and marker IDs differ')
    source=snapshot_path(path,data)
    raw=source.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=data['source']['sha256']:
        raise ValueError('source hash mismatch')
    revision=data['source']['revision']
    if len(revision)!=40 or any(c not in '0123456789abcdef' for c in revision):
        raise ValueError('source revision must be a full commit SHA')
    region=data['region']
    if not 1<=region['start_line']<=region['end_line']<=len(raw.splitlines()):
        raise ValueError('region source lines are out of bounds')
    for name in ('task.md','reference.md'):
        if not (path.parent/name).is_file():
            raise ValueError(f'missing {name}')
    with tempfile.TemporaryDirectory(prefix='drperf-region-check-') as tmp:
        marked=apply(path,data,Path(tmp))
        if data['language']=='python':
            original=ast.parse(raw)
            transformed=ast.parse(marked.read_bytes())
            remover=RemoveEmptyMarker(data['id'])
            transformed=remover.visit(transformed)
            if remover.markers!=1 or remover.imports!=1:
                raise ValueError('expected exactly one empty marker and one perfmark import')
            if ast.dump(original)!=ast.dump(transformed):
                raise ValueError('Python patch changes program structure beyond the empty marker')
            if not all(region['start_line']<=start<=end<=region['end_line'] for start,end in remover.spans):
                raise ValueError('Python marker is outside the declared source region')
        elif data['language']=='cpp':
            patch=(path.parent/'region.patch').read_text()
            changes=[line for line in patch.splitlines() if line[:1] in ('+','-') and not line.startswith(('+++','---'))]
            additions=[line[1:].strip() for line in changes if line.startswith('+') and line[1:].strip()]
            expected=['#include "drperf_bench_region.h"',f'DRPERF_BENCH_REGION("{data["id"]}");']
            if any(line.startswith('-') for line in changes) or sorted(additions)!=sorted(expected):
                raise ValueError('C++ patch must only add the helper include and one empty RAII marker')
            old_line=0
            for line in patch.splitlines():
                hunk=re.match(r'^@@ -(\d+)',line)
                if hunk:
                    old_line=int(hunk[1])
                elif line.startswith(('+++','---')):
                    continue
                elif line.startswith('+'):
                    if line[1:].strip()==expected[1] and not region['start_line']<=old_line<=region['end_line']:
                        raise ValueError('marker is outside the declared source region')
                elif line.startswith((' ','-')):
                    old_line+=1
        else:
            raise ValueError('unsupported marker language')
    return data


def export(path,destination):
    data=check(path)
    if destination.exists():
        raise ValueError('destination already exists')
    destination.mkdir(parents=True)
    apply(path,data,destination)
    shutil.copy2(path.parent/'task.md',destination/'TASK.md')
    # Only public identity and the empty target; reference notes stay in collection.
    public={k:data[k] for k in ('schema_version','id','title','language','region','marker','status','build_status','workload')}
    public['source']={k:v for k,v in data['source'].items() if k!='snapshot'}
    if 'tests' in data:
        # Shared-resource source paths are collection internals. All resources
        # are materialized at their declared destinations in the export.
        public['tests']={k:v for k,v in data['tests'].items() if k!='resources'}
        public['tests']['files']=[str(rel) for _,rel in test_assets(path,data)]
        for source,relative in test_assets(path,data):
            target=destination/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,target)
    (destination/'case.json').write_text(json.dumps(public,indent=2)+'\n')
    if data['language']=='cpp':
        shutil.copy2(ROOT/'support/drperf_bench_region.h',destination/'drperf_bench_region.h')
    group=path.parents[2]
    # License collection convention allows project-specific upstream subfolders.
    for license in (group/'upstream').rglob('*'):
        if license.is_file() and license.name.upper().startswith(('LICENSE','COPYING','NOTICE')):
            target=destination/'LICENSES'/license.relative_to(group/'upstream')
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(license,target)
    print(destination)


def test_case(path, python, d8, source_root, timeout):
    data=check(path)
    if not data.get('tests'):
        raise ValueError('case has no concrete test yet')
    with tempfile.TemporaryDirectory(prefix='drperf-case-test-') as tmp:
        destination=Path(tmp)/'case'
        export(path,destination)
        values={'{python}':python,'{d8}':d8,'{source_root}':str(source_root.resolve()) if source_root else str(destination)}
        command=[]
        for arg in data['tests']['command']:
            value=values.get(arg,arg)
            if value is None:
                raise ValueError(f'provide a binary for {arg}; host Node is not a pinned V8 substitute')
            if '{' in value or '}' in value:
                raise ValueError(f'unresolved test argument {value}')
            command.append(value)
        # A supplied full checkout must already contain this case's patch.
        # The driver is responsible for checking the imported file and marker.
        result=subprocess.run(command,cwd=destination,timeout=timeout)
        return result.returncode


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='cmd',required=True)
    sub.add_parser('list')
    p=sub.add_parser('check');p.add_argument('--require-tests',action='store_true')
    p=sub.add_parser('export');p.add_argument('id');p.add_argument('destination',type=Path)
    sub.add_parser('index')
    p=sub.add_parser('test');p.add_argument('id');p.add_argument('--python',default=sys.executable)
    p.add_argument('--d8');p.add_argument('--source-root',type=Path)
    p.add_argument('--timeout',type=float,default=120)
    args=parser.parse_args()
    paths=cases()
    if args.cmd=='index':
        index={'schema_version':1,'count':len(paths),'cases':[]}
        for path in paths:
            c=load(path)
            index['cases'].append({'id':c['id'],'manifest':path.relative_to(ROOT).as_posix(),
                                   'group':path.relative_to(ROOT).parts[0],
                                   'title':c['title'],'language':c['language'],
                                   'phase':c.get('phase','not-specified'),
                                   'test_status':c.get('tests',{}).get('validation',{}).get('status','missing'),
                                   'source_family':c.get('source_family',c['source']['path']+':'+c['region']['symbol'])})
        (ROOT/'catalog.json').write_text(json.dumps(index,indent=2)+'\n')
        print(f'Indexed {len(paths)} collected source regions.')
        return
    if args.cmd=='list':
        for path in paths:
            c=load(path)
            print(f'{c["id"]:24} {c["language"]:8} {c["source"]["path"]} :: {c["region"]["symbol"]}')
        print(f'{len(paths)} collected source regions')
        return
    if args.cmd in ('export','test'):
        matches=[p for p in paths if load(p)['id']==args.id]
        if len(matches)!=1:
            parser.error('case ID must identify exactly one collected region')
        if args.cmd=='export':
            export(matches[0],args.destination.resolve())
        else:
            try:
                rc=test_case(matches[0],args.python,args.d8,args.source_root,args.timeout)
            except (ValueError,OSError,subprocess.TimeoutExpired) as exc:
                parser.exit(1,f'test: {exc}\n')
            if rc:parser.exit(rc if rc>0 else 1)
        return
    failures=[]
    ids=set(); targets=set()
    for path in paths:
        try:
            c=check(path)
            if args.require_tests and not c.get('tests'):
                raise ValueError('missing concrete tests')
            target=(c['source']['repository'],c['source']['revision'],c['source']['path'],c['region']['start_line'],c['region']['end_line'])
            if c['id'] in ids or target in targets:
                raise ValueError('duplicate ID or exact source region')
            ids.add(c['id']);targets.add(target)
        except (ValueError,KeyError,OSError,SyntaxError,subprocess.CalledProcessError) as exc:
            failures.append(f'{path.relative_to(ROOT)}: {exc}')
    if failures:
        parser.exit(1,'\n'.join(failures)+'\n')
    tested=sum(bool(load(p).get('tests')) for p in paths)
    print(f'Checked {len(paths)} source regions and {tested} test bundles: hashes, independent patches, empty markers and unique targets.')


if __name__=='__main__':
    main()
