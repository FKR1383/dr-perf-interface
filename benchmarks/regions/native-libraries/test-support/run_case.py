#!/usr/bin/env python3
"""Build pinned RapidJSON headers plus one marked file and run semantic assertions."""
import argparse, json, os, shutil, subprocess, tarfile, tempfile
from pathlib import Path
p=argparse.ArgumentParser(); p.add_argument('--source-root',type=Path,required=True); a=p.parse_args()
here=Path(__file__).resolve().parent
manifest=json.loads((here.parent/'case.json').read_text())
source=a.source_root.resolve()/manifest['source']['path']
assert source.is_file(),source
assert manifest['id'] in source.read_text()
with tempfile.TemporaryDirectory(prefix='drperf-rapidjson-') as tmp:
    stage=Path(tmp)
    with tarfile.open(here/'headers.tar.gz') as archive:
        for member in archive.getmembers():
            assert not member.issym() and not member.islnk()
            assert (stage/member.name).resolve().is_relative_to(stage)
        archive.extractall(stage,filter='data')
    shutil.copy2(source,stage/manifest['source']['path'])
    compiler=os.environ.get('CXX','c++')
    command=[compiler,'-std=c++11','-O2','-Wall','-Wextra','-I'+str(stage/'include'),'-I'+str(here.parent),'-I'+str(here),str(here/'case.cpp'),'-o',str(stage/'case')]
    library=os.environ.get('PERFMARK_LIB')
    if os.environ.get('DRPERF'):
        assert library and Path(library).is_file(), 'DRPERF requires PERFMARK_LIB pointing to libperfmark.so'
    if library:
        path=Path(library).resolve()
        command.extend(['-DDRPERF_BENCH_REAL',str(path),'-Wl,-rpath,'+str(path.parent),'-Wl,--wrap=perfmark_begin_v','-Wl,--wrap=perfmark_end'])
    subprocess.run(command,check=True,timeout=60)
    subprocess.run([str(stage/'case')],check=True,timeout=30)
