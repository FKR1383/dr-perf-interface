import contextlib
import importlib.util
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

BENCH=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('region_collection',BENCH/'regions/collect.py')
collection=importlib.util.module_from_spec(spec)
spec.loader.exec_module(collection)


class CollectionTests(unittest.TestCase):
    def test_catalog_matches_case_files_and_empty_markers(self):
        catalog=json.loads((BENCH/'regions/catalog.json').read_text())
        manifests=collection.cases()
        self.assertEqual(catalog['count'],len(manifests))
        self.assertEqual({c['id'] for c in catalog['cases']},{collection.load(p)['id'] for p in manifests})
        self.assertTrue(all(collection.load(p)['marker']['pcvs']==[] for p in manifests))

    def test_export_excludes_reference_and_includes_actual_empty_marker(self):
        case=BENCH/'regions/accidental-quadratic/cases/aq-001/case.json'
        data=collection.load(case)
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'case'
            with contextlib.redirect_stdout(io.StringIO()):collection.export(case,out)
            self.assertFalse((out/'reference.md').exists())
            self.assertFalse('citations' in json.loads((out/'case.json').read_text()))
            marked=(out/data['source']['path']).read_text()
            self.assertIn('perfmark.region(',marked)
            self.assertTrue((out/'TASK.md').is_file())
            self.assertTrue(any((out/'LICENSES').rglob('LICENSE*')))

    @unittest.skipUnless(shutil.which('c++'),'requires a C++ compiler')
    def test_cpp_marker_balances_early_return_with_zero_pcvs(self):
        code=r'''
#include <cassert>
#include "drperf_bench_region.h"
int begins=0, ends=0;
extern "C" void perfmark_begin_v(const char* region,int n,const char* const* names,const int64_t* values) {
  assert(region && n==0 && names==nullptr && values==nullptr); ++begins;
}
extern "C" void perfmark_end(const char*) { ++ends; }
int work(bool early) {
  DRPERF_BENCH_REGION("empty-region");
  if (early) return 7;
  return 8;
}
int main() {
  assert(work(true)==7 && begins==1 && ends==1);
  assert(work(false)==8 && begins==2 && ends==2);
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            source=root/'test.cc'; source.write_text(code)
            binary=root/'test'
            subprocess.run(['c++','-std=c++11','-Wall','-Wextra','-Werror',
                '-I'+str(BENCH/'regions/support'),'-I'+str(BENCH.parent/'perfmark'),
                str(source),'-o',str(binary)],check=True,capture_output=True)
            subprocess.run([str(binary)],check=True,capture_output=True)


if __name__=='__main__':unittest.main()
