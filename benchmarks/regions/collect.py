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


def apply(path, manifest, destination):
    original = Path(manifest['source']['path'])
    if original.is_absolute() or '..' in original.parts:
        raise ValueError('source path must be relative to its upstream checkout')
    target = destination / original
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(snapshot_path(path,manifest), target)
    patch = (path.parent/'region.patch').resolve()
    stats=subprocess.check_output(['git','apply','--numstat',str(patch)],cwd=destination,text=True)
    touched=[line.split('\t',2)[-1] for line in stats.splitlines()]
    if touched != [original.as_posix()]:
        raise ValueError('a case patch must touch only its declared source file')
    subprocess.run(['git','apply','--check',str(patch)],cwd=destination,check=True,capture_output=True)
    subprocess.run(['git','apply',str(patch)],cwd=destination,check=True,capture_output=True)
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


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='cmd',required=True)
    sub.add_parser('list')
    sub.add_parser('check')
    p=sub.add_parser('export');p.add_argument('id');p.add_argument('destination',type=Path)
    sub.add_parser('index')
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
    if args.cmd=='export':
        matches=[p for p in paths if load(p)['id']==args.id]
        if len(matches)!=1:
            parser.error('case ID must identify exactly one collected region')
        export(matches[0],args.destination.resolve())
        return
    failures=[]
    ids=set(); targets=set()
    for path in paths:
        try:
            c=check(path)
            target=(c['source']['repository'],c['source']['revision'],c['source']['path'],c['region']['start_line'],c['region']['end_line'])
            if c['id'] in ids or target in targets:
                raise ValueError('duplicate ID or exact source region')
            ids.add(c['id']);targets.add(target)
        except (ValueError,KeyError,OSError,SyntaxError,subprocess.CalledProcessError) as exc:
            failures.append(f'{path.relative_to(ROOT)}: {exc}')
    if failures:
        parser.exit(1,'\n'.join(failures)+'\n')
    print(f'Checked {len(paths)} source regions: hashes, independent patches, empty markers and unique targets.')


if __name__=='__main__':
    main()
