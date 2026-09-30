"""Portable reports must not scale with unrelated native synchronization traffic."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
import event_model
import execution
import explorer
import waits


def fixture(noise=0, violation=False):
    def event(kind, start, region, thread, seq):
        return dict(id=str(start), kind=kind, start=start, end=start+1,
                    group='0:1', tid=thread, regionSeq=seq, region=region,
                    object='1', aux='1', returned=True, result=0, api='perfmark_'+kind,
                    elapsedUs=0, potentialSyscalls=0, beginUs=start*100, endUs=(start+1)*100)
    pub = event('declared_publish', 10 if violation else 1, 'B', 2, 3)
    consumer = event('declared_waited', 3, 'A', 1, 1)
    records = [pub, consumer]
    for i in range(noise):
        records.append(event('lock', 20+2*i, '', 3, 0))
    model = dict(regions=[dict(id=name, name=name, states=[], calls=1,
                              regimes=[], points=[dict(state=[], calls=1, observed=1)])
                          for name in ('A','B')], validity={},
        provenance={'runs':[{'measurement':{'pid':1, 'wait_records':len(records), 'wait_dropped':0}}]},
        trace=dict(complete=True, events=[
            dict(group='0:1',thread='1',seq=1,end=2,region='A',values={}),
            dict(group='0:1',thread='2',seq=3,end=4,region='B',values={})]),
        waits=dict(status='observed', warnings=[], events=records,
                   operations=waits.analyze(records), regions=[], pendingCalls=[]))
    model['eventModel'] = event_model.check(model)
    model['executionGraph'] = execution.build(model)
    return model


class ReportStorage(unittest.TestCase):
    def test_native_edges_and_pending_records_remain_available_to_viewer(self):
        model=fixture(3)
        pub=dict(model['waits']['events'][0], id='100', kind='transfer', start=100,
                 end=101, object='10', api='cudaMemcpyAsync')
        sync=dict(model['waits']['events'][1], id='102', kind='stream_wait', start=102,
                  end=103, object='10', api='cudaStreamSynchronize')
        pending=dict(pub, id='104', kind='completion', start=104, end=0,
                     region='', regionSeq=0, object='20', returned=False)
        model['waits']['events'] += [pub,sync,pending]
        model['waits']['operations']=waits.analyze(model['waits']['events'])
        model['waits']['pendingCalls']=[{'id':'104'}]
        model['provenance']['runs'][0]['measurement']['wait_records']+=3
        model['eventModel']=event_model.check(model)
        model['executionGraph']=execution.build(model)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'report.json';explorer.write_model(model,path)
            report=explorer.load_model(path)
            self.assertEqual({e['id'] for e in report['waits']['events']}, {'1','3','100','102','104'})
            self.assertEqual(report['waits']['operations'][0]['producers'],['100'])
            full=explorer.load_model(path,True)
            self.assertEqual(full['waits'],model['waits'])
            self.assertEqual(execution.build(full),model['executionGraph'])

    def test_failed_report_replacement_preserves_old_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'report.json';explorer.write_model(fixture(3),path)
            before=path.read_bytes()
            replace=Path.replace
            def fail_report(source,target):
                if target==path:
                    raise OSError('simulated report publish failure')
                return replace(source,target)
            with patch.object(Path,'replace',fail_report):
                with self.assertRaisesRegex(OSError,'simulated'):
                    explorer.write_model(fixture(4,True),path)
            self.assertEqual(path.read_bytes(),before)
            self.assertEqual(event_model.check(explorer.load_model(path,True))['status'],'ordered')

    def test_background_volume_does_not_bloat_report_or_change_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            sizes=[]
            for noise in (0,10000):
                model=fixture(noise)
                original=copy.deepcopy(model)
                path=Path(tmp)/f'{noise}.json'
                explorer.write_model(model,path)
                self.assertEqual(model,original,'writing must not discard in-memory evidence')
                sizes.append(path.stat().st_size)
                compact=explorer.load_model(path)
                self.assertEqual(len(compact['waits']['events']),2)
                self.assertEqual(compact['executionGraph'],model['executionGraph'])
                self.assertEqual(compact['eventModel'],model['eventModel'])
                full=explorer.load_model(path,wait_evidence=True)
                self.assertEqual(full['waits'],model['waits'])
                self.assertEqual(event_model.check(full),model['eventModel'])
                with self.assertRaisesRegex(ValueError,'external'):
                    event_model.check(compact)
                with self.assertRaisesRegex(ValueError,'external'):
                    execution.build(compact)
            self.assertLess(sizes[1]-sizes[0],200)

    def test_missing_corrupt_and_relocated_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'report.json'
            explorer.write_model(fixture(3),path)
            compact=explorer.load_model(path)
            evidence=path.parent/compact['waits']['evidence']['path']
            moved=path.parent/'moved';moved.mkdir()
            shutil.copy(path,moved/path.name)
            self.assertEqual(explorer.load_model(moved/path.name)['eventModel']['status'],'ordered')
            with self.assertRaisesRegex(ValueError,'required for rechecking'):
                explorer.load_model(moved/path.name,wait_evidence=True)
            shutil.copy(evidence,moved/evidence.name)
            self.assertEqual(event_model.check(explorer.load_model(moved/path.name,True))['status'],'ordered')
            with (moved/evidence.name).open('ab') as stream:
                stream.write(b'corrupt')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):
                explorer.load_model(moved/path.name,True)

    def test_cli_rechecks_evidence_and_retains_violations(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'report.json'
            for violation in (False,True):
                explorer.write_model(fixture(3,violation),path)
                result=subprocess.run([str(ROOT/'bin/drperf-check-events'),str(path)],
                                      capture_output=True,text=True)
                self.assertEqual(result.returncode,1 if violation else 0,result.stderr)
                self.assertIn('violation' if violation else 'ordered',result.stdout)
            compact=explorer.load_model(path)
            (path.parent/compact['waits']['evidence']['path']).unlink()
            result=subprocess.run([str(ROOT/'bin/drperf-check-events'),str(path)],
                                  capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('required for rechecking',result.stderr)

    def test_legacy_inline_and_no_wait_reports_remain_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'legacy.json';model=fixture(3)
            path.write_text(json.dumps(model))
            self.assertEqual(explorer.load_model(path,True),model)
            del model['waits']
            explorer.write_model(model,path)
            self.assertNotIn('waits',explorer.load_model(path,True))

    def test_count_mismatch_is_not_treated_as_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'report.json';explorer.write_model(fixture(3),path)
            compact=explorer.load_model(path)
            compact['waits']['evidence']['eventCount']+=1
            path.write_text(json.dumps(compact))
            with self.assertRaisesRegex(ValueError,'count mismatch'):
                explorer.load_model(path,True)


if __name__=='__main__':
    unittest.main()
