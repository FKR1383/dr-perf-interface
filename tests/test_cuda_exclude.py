"""CUDA exclusion must suppress nested callees and resume host counting."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'lib'))
import derive
import runner

class CUDAExclusion(unittest.TestCase):
    def test_nested_scope_and_resume(self):
        with tempfile.TemporaryDirectory(prefix='cuda-exclude-',dir=ROOT/'out') as temp:
            out=Path(temp);lib=out/'fake_cuda.so';app=out/'app'
            subprocess.run(['gcc','-O2','-fPIC','-shared','-DEMULATOR',str(ROOT/'tests/cuda_exclude.c'),'-o',str(lib)],check=True)
            subprocess.run(['gcc','-O2','-rdynamic',str(ROOT/'tests/cuda_exclude.c'),str(lib),'-L'+str(ROOT/'build'),
                            '-lperfmark','-Wl,-rpath,'+str(ROOT/'build'),'-o',str(app)],check=True)
            datasets=[]
            for mode in ('','fake_cuda.so'):
                raw=out/('excluded' if mode else 'baseline')
                with patch.dict(os.environ,{'DRPERF_EXCLUDE_CUDA_MODULE':mode}):
                    rc,log,files=runner.run([str(app)],str(raw),timeout=30)
                self.assertEqual(rc,0,log);self.assertTrue(files)
                rs=runner.load_runs(str(raw));self.assertEqual(runner.validity(rs),[])
                keys,slots=runner.blocks_of_set(rs)
                regions={}
                for region in ('emulated','after'):
                    states,_,dropped=derive.per_state(keys,region)
                    self.assertEqual(dropped,0)
                    vecs,_=derive.per_trigger(states)
                    regions[region]={v:sum(cs.values()) for v,cs in vecs.items()}
                datasets.append(regions)
                if mode:
                    self.assertEqual(sum(n for k in keys.values() for b,n in k['vec'].items()
                                         if slots[b][0]=='fake_cuda.so'),0)
                    stats=rs['runs'][0]['data']['drperf']
                    self.assertEqual(stats['excluded_cuda_exports'],4)
                    self.assertEqual(stats['excluded_cuda_calls'],12)
                    self.assertGreater(stats['excluded_instructions'],10000)
            baseline,excluded=datasets
            self.assertEqual(baseline['after'],excluded['after'])
            self.assertEqual(len(set(excluded['emulated'].values())),1)
            self.assertGreater(baseline['emulated'][(3000,)],10*excluded['emulated'][(3000,)])
            self.assertGreater(excluded['after'][(3000,)],excluded['after'][(1000,)])

class ThreadScope(unittest.TestCase):
    def test_unmarked_workers_can_be_excluded(self):
        with tempfile.TemporaryDirectory(prefix='thread-scope-',dir=ROOT/'out') as temp:
            out=Path(temp);app=out/'app'
            subprocess.run(['gcc','-O2','-pthread',str(ROOT/'tests/cthreads.c'),'-L'+str(ROOT/'build'),
                            '-lperfmark','-Wl,-rpath,'+str(ROOT/'build'),'-o',str(app)],check=True)
            results=[]
            for follow in ('1','0'):
                raw=out/follow
                with patch.dict(os.environ,{'DRPERF_FOLLOW_THREADS':follow,'DRPERF_EXCLUDE_CUDA_MODULE':''}):
                    rc,log,files=runner.run([str(app),'n=1000000','threads=2'],str(raw),timeout=30)
                self.assertEqual(rc,0,log)
                rs=runner.load_runs(str(raw));self.assertEqual(runner.validity(rs),[])
                self.assertEqual(rs['runs'][0]['data']['drperf']['follow_unmarked_threads'],follow=='1')
                keys,_=runner.blocks_of_set(rs)
                results.append({name:sum(sum(vec.values()) for vec,n in derive.per_state(keys,name)[0].values())
                                for name in ('parallel','worker_loop','serial')})
            followed,caller=results
            self.assertGreater(followed['parallel']-caller['parallel'],5000000)
            self.assertEqual(followed['worker_loop'],caller['worker_loop'])
            self.assertEqual(followed['serial'],caller['serial'])

if __name__=='__main__': unittest.main()
