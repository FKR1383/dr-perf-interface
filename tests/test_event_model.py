from pathlib import Path
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'lib'))
import event_model
import explorer
import runner


def checkpoint(kind, start, region='A', event=1, generation=1, thread=1):
    return dict(kind='declared_'+kind, id=str(start), api='perfmark_event_'+kind,
                start=start, end=start+1, beginUs=start*100, endUs=(start+1)*100,
                region=region, regionSeq=1 if region=='A' else 3,
                group='0:1', tid=thread, object=str(event), aux=str(generation), result=0, returned=True)


def model(events):
    return dict(validity={}, waits=dict(status='observed', events=events, operations=[]),
        trace=dict(complete=True, events=[dict(group='0:1',thread='1',seq=1,end=2,region='A',values={'need':1}),
                                         dict(group='0:1',thread='2',seq=3,end=4,region='B',values={})]),
        regions=[dict(id='A',states=['need'],calls=1,points=[dict(state=[1],calls=1)]),
                 dict(id='B',states=[],calls=1,points=[dict(state=[],calls=1)])])


class EventModel(unittest.TestCase):
    def valid(self):
        return model([checkpoint('publish',3,'B',thread=2),checkpoint('waited',5)])

    def test_waited_needs_no_begin(self):
        r=event_model.check(self.valid())
        self.assertEqual(r['status'],'ordered')
        self.assertNotIn('begin', r['edges'][0])

    def test_already_published_is_valid(self):
        m=self.valid();m['waits']['events'][0]=checkpoint('publish',-2,'B',thread=2)
        self.assertEqual(event_model.check(m)['status'],'ordered')

    def test_marker_does_not_enforce_order(self):
        m=self.valid();m['waits']['events'][0]=checkpoint('publish',7,'B',thread=2)
        r=event_model.check(m);self.assertEqual(r['status'],'violation')
        self.assertEqual(r['violations'][0]['consumer'],'A')

    def test_generation_cannot_reuse_old_publication(self):
        m=self.valid();m['waits']['events'][0]['aux']='0'
        self.assertEqual(event_model.check(m)['status'],'unverified')

    def test_duplicate_publication_is_invalid(self):
        m=self.valid();m['waits']['events'].append(checkpoint('publish',8,'B',thread=2))
        self.assertEqual(event_model.check(m)['status'],'violation')

    def test_cross_process_ids_are_not_merged(self):
        m=self.valid();m['waits']['events'][0]['group']='1:2'
        self.assertEqual(event_model.check(m)['status'],'unverified')

    def test_publish_without_consumer_makes_no_wait_claim(self):
        m=self.valid();m['waits']['events'].pop()
        r=event_model.check(m)
        self.assertEqual(r['edges'],[])
        self.assertEqual(r['interfaces'],[])

    def test_waited_without_publication_is_unverified(self):
        m=self.valid();m['waits']['events'].pop(0)
        self.assertEqual(event_model.check(m)['status'],'unverified')

    def test_legacy_end_is_readable_without_begin(self):
        m=self.valid();m['waits']['events'][-1]['kind']='declared_wait_end'
        self.assertEqual(event_model.check(m)['status'],'ordered')

    def test_unannotated_sync_remains_unknown(self):
        m=self.valid();m['waits']['operations']=[dict(checkpoint('wait_begin',20),api='sem_wait')]
        r=event_model.check(m);self.assertEqual(r['status'],'ordered')
        self.assertEqual(r['unexplained'][0]['term'],'unexplained(Wait[?])')

    def test_native_operation_is_not_assigned_by_proximity(self):
        m=self.valid();m['waits']['operations']=[dict(checkpoint('wait_begin',3),api='sem_wait')]
        r=event_model.check(m);self.assertEqual(r['status'],'ordered')
        self.assertEqual(r['unexplained'][0]['count'],1)

    def contextual(self):
        m = model([])
        m['regions'] = [dict(id=name, states=[], calls=2 if name=='sync' else 1,
                             points=[dict(state=[], calls=2 if name=='sync' else 1)])
                        for name in ('A', 'D', 'sync', 'C', 'E')]
        m['trace']['events'] = [dict(group='0:1', thread=str(tid), seq=start, end=end, region=name, values={})
                               for name,tid,start,end in [('A',1,1,10),('sync',1,2,3),
                                   ('D',1,11,20),('sync',1,12,13),('C',2,21,22),('E',2,23,24)]]
        m['waits']['events'] = [dict(checkpoint(kind,start,name,event=event,thread=tid),regionSeq=seq)
                               for kind,start,name,event,tid,seq in [('publish',10,'C',1,2,21),
                                   ('waited',40,'A',1,1,1),('publish',60,'E',2,2,23),('waited',80,'D',2,1,11)]]
        m['waits']['operations'] = [dict(checkpoint('wait_begin',start,'sync'),kind='completion',
                                        api='sem_wait',end=start+5,regionSeq=seq,producers=[])
                                   for start,seq in [(30,2),(70,12)]]
        return m

    def test_shared_primitive_keeps_each_callers_declared_dependency(self):
        r=event_model.check(self.contextual())
        self.assertEqual(r['status'],'ordered')
        self.assertEqual([(e['consumer'],e['producer']) for e in r['edges']],[('A','C'),('D','E')])
        self.assertEqual([e['nativeContext'] for e in r['edges']],
                         [[dict(region='sync',api='sem_wait',count=1)]]*2)
        # Enclosing annotations do not fabricate primitive-to-publisher matches.
        self.assertEqual(r['unexplained'][0]['count'],2)

    def test_unmarked_primitive_has_the_same_semantic_edges(self):
        m=self.contextual()
        m['regions']=[r for r in m['regions'] if r['id']!='sync']
        m['trace']['events']=[t for t in m['trace']['events'] if t['region']!='sync']
        for op,name,seq in zip(m['waits']['operations'],('A','D'),(1,11)):
            op.update(region=name,regionSeq=seq)
        r=event_model.check(m)
        self.assertEqual([(e['consumer'],e['producer']) for e in r['edges']],[('A','C'),('D','E')])
        self.assertEqual([e['nativeContext'][0]['region'] for e in r['edges']],['A','D'])

    def test_parent_marker_cannot_claim_context_after_its_checkpoint(self):
        m=self.contextual();m['waits']['events'][1].update(start=32,end=33)
        r=event_model.check(m)
        self.assertEqual(r['edges'][0]['nativeContext'],[])
        self.assertEqual(r['unexplained'][0]['count'],2)

    def test_existing_native_producer_mapping_is_not_reported_unexplained(self):
        m=self.contextual();m['waits']['operations'][0]['producers']=['native-publication']
        r=event_model.check(m)
        self.assertEqual(r['nativeResolved'],1)
        self.assertEqual(r['unexplained'][0]['count'],1)

    def test_partial_capture_is_not_verified(self):
        m=self.valid();m['waits']['status']='partial'
        self.assertEqual(event_model.check(m)['status'],'unverified')

    def test_checkpoint_must_reference_its_captured_invocation(self):
        for change in ('missing','forged','outside'):
            m=self.valid(); waited=m['waits']['events'][-1]
            if change=='missing': waited['regionSeq']=99
            elif change=='forged': waited['region']='B'
            else: waited.update(region='',regionSeq=0)
            r=event_model.check(m)
            if change=='forged':
                self.assertEqual(r['status'],'ordered')
                self.assertEqual(r['edges'][0]['consumer'],'A')
            else:
                self.assertEqual(r['status'],'unverified')
                self.assertEqual(r['edges'][0]['status'],'unverified')

    def test_recheck_detects_missing_wait_sidecar_records(self):
        m=self.valid()
        m['provenance']={'runs':[{'measurement':{'pid':1,'wait_records':3,'wait_dropped':0}}]}
        self.assertEqual(event_model.check(m)['status'],'unverified')

    def test_recheck_validates_persisted_probe_request(self):
        m=self.valid(); publication=m['waits']['events'][0]
        publication.update(injectedDelayMs=10)
        m['provenance']={'runs':[{'measurement':{'pid':1,'wait_records':2,'wait_dropped':0,
            'wait_delay_ms':10,'wait_delay_region':'wrong','wait_delay_kind':'event',
            'wait_delay_injections':1}}]}
        r=event_model.check(m)
        self.assertEqual(r['status'],'unverified')
        self.assertTrue(r['probe'])
        self.assertTrue(any('inconsistent' in x['reason'] for x in r['unverified']))

    def test_recheck_compares_probe_target_to_original_region_name(self):
        m=self.valid(); publication=m['waits']['events'][0]
        publication.update(injectedDelayMs=10)
        next(r for r in m['regions'] if r['id']=='B')['originalName']='raw.B'
        m['provenance']={'runs':[{'measurement':{'pid':1,'wait_records':2,'wait_dropped':0,
            'wait_delay_ms':10,'wait_delay_region':'raw.B','wait_delay_kind':'event',
            'wait_delay_injections':1}}]}
        self.assertEqual(event_model.check(m)['status'],'ordered')

    def test_incomplete_publication_cannot_create_a_violation(self):
        m=self.valid(); publication=m['waits']['events'][0]
        publication.update(start=7,end=8,returned=False)
        r=event_model.check(m)
        self.assertEqual(r['status'],'unverified')
        self.assertFalse(r['violations'])

    def test_probe_uses_distance_and_stays_bounded(self):
        r=event_model.check(self.valid());p=event_model.probe_plan(r,margin_ms=100,maximum_ms=100)
        self.assertEqual(p[0]['delayMs'],100);self.assertTrue(p[0]['capped'])
        r['probe']=True
        with self.assertRaises(ValueError):event_model.probe_plan(r)

    def test_large_serialized_timestamp_is_exact(self):
        m=self.valid()
        for e in m['waits']['events']:
            for k in ['beginUs','endUs']:e[k]=str(2**60+e[k])
        self.assertEqual(event_model.check(m)['edges'][0]['distanceUs'],100)

    def test_delay_kind_is_explicit(self):
        env={'DRPERF_WAITS':'1','DRPERF_WAIT_DELAY_MS':'100','DRPERF_WAIT_DELAY_REGION':'B','DRPERF_WAIT_DELAY_KIND':'event'}
        self.assertIn('-wait_delay_event',runner.wait_options(env))
        env['DRPERF_WAIT_DELAY_KIND']='bad'
        with self.assertRaises(ValueError):runner.wait_options(env)


class PythonEventProbe(unittest.TestCase):
    def test_python_publication_delay_releases_gil_and_exposes_missing_wait(self):
        with tempfile.TemporaryDirectory(prefix='python-events-',dir=ROOT/'out') as tmp:
            for mode in ['correct','missing-wait']:
                reports=[]
                for label,delay in [('baseline',0),('probe',500)]:
                    folder=Path(tmp)/(mode+'-'+label)
                    with patch.dict(os.environ,{'DRPERF_WAITS':'1','DRPERF_WAIT_DELAY_REGION':'B',
                           'DRPERF_WAIT_DELAY_MS':str(delay),'DRPERF_WAIT_DELAY_KIND':'event',
                           'DRPERF_FOLLOW_THREADS':'0'}):
                        rc,log,_=runner.run([sys.executable,str(ROOT/'examples/waits/events.py'),mode],str(folder),timeout=30)
                    self.assertEqual(rc,0,log)
                    profile=explorer.build_model(folder,discover=False)
                    self.assertFalse(profile['validity']['errors'])
                    reports.append(profile['eventModel'])
                self.assertFalse(reports[0]['violations'])
                self.assertEqual(bool(reports[1]['violations']),mode=='missing-wait')
                self.assertTrue(reports[1]['probe'])

    def test_requested_event_probe_with_no_matching_region_is_unverified(self):
        with tempfile.TemporaryDirectory(prefix='python-events-no-hit-',dir=ROOT/'out') as tmp:
            folder=Path(tmp)/'raw'
            with patch.dict(os.environ,{'DRPERF_WAITS':'1','DRPERF_WAIT_DELAY_REGION':'missing',
                   'DRPERF_WAIT_DELAY_MS':'10','DRPERF_WAIT_DELAY_KIND':'event',
                   'DRPERF_FOLLOW_THREADS':'0'}):
                rc,log,_=runner.run([sys.executable,str(ROOT/'examples/waits/events.py'),'correct'],
                                    str(folder),timeout=30)
            self.assertEqual(rc,0,log)
            profile=explorer.build_model(folder,discover=False)
            report=profile['eventModel']
            self.assertEqual(report['status'],'unverified')
            self.assertFalse(report['probe'])
            self.assertTrue(profile['waits']['probeRequested'])
            checked=Path(tmp)/'profile.json'; checked.write_text(json.dumps(profile))
            result=subprocess.run([str(ROOT/'bin/drperf-check-events'),str(checked)],capture_output=True,text=True)
            self.assertEqual(result.returncode,2,result.stdout+result.stderr)
            self.assertIn('requested delay probe did not execute',result.stdout)

    def test_marker_callees_are_excluded_and_counting_resumes(self):
        with tempfile.TemporaryDirectory(prefix='event-counts-',dir=ROOT/'out') as tmp:
            folder=Path(tmp)
            source=folder/'payload.c'
            source.write_text('''#include <stdint.h>
volatile uint64_t sink;
__attribute__((noinline)) void payload(void) {
    for (uint64_t i=0;i<1000;++i) sink += i;
}
int perfmark_event_publish(uint64_t event, uint64_t generation) {
    payload(); return 0;
}
''')
            library=folder/'libperfmark_fixture.so'
            subprocess.run(['gcc','-O2','-fPIC','-shared',str(source),'-o',str(library)],check=True)
            app=folder/'app.c'
            app.write_text('''#include "perfmark.h"
#include <dlfcn.h>
#include <assert.h>
int main(int argc, char **argv) {
    void *lib=dlopen(argv[1],RTLD_NOW); assert(lib);
    int (*publish)(uint64_t,uint64_t)=dlsym(lib,"perfmark_event_publish");
    void (*payload)(void)=dlsym(lib,"payload");
    perfmark_begin("capture","n",1); perfmark_end("capture");
    perfmark_begin("marker.only","n",1);
    publish(1,1);
    perfmark_event_waited(1,1);
    perfmark_end("marker.only");
    perfmark_begin("real.work","n",1);
    payload();
    perfmark_end("real.work");
}
''')
            exe=folder/'app'
            subprocess.run(['gcc','-O2',str(app),'-I'+str(ROOT/'perfmark'),
                '-L'+str(ROOT/'build'),'-lperfmark','-ldl','-Wl,-rpath,'+str(ROOT/'build'),
                '-o',str(exe)],check=True)
            for enabled in ['0','1']:
                raw=folder/enabled
                with patch.dict(os.environ,{'DRPERF_WAITS':enabled,'DRPERF_FOLLOW_THREADS':'0'}):
                    rc,log,_=runner.run([str(exe),str(library)],str(raw),timeout=30)
                self.assertEqual(rc,0,log)
                keys,slots=runner.blocks_of_set(explorer.load_raw_runs(raw))
                costs={name:sum(c for row in keys.values() if row['region']==name
                    for block,c in row['vec'].items() if slots[block][1]=='payload')
                    for name in ['marker.only','real.work']}
                self.assertEqual(costs['marker.only'],0,costs)
                self.assertGreater(costs['real.work'],1000,costs)


if __name__=='__main__':unittest.main()
