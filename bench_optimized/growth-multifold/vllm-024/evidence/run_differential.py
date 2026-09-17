"""Exact identity-order differential for the accepted vllm-024 candidate."""
import contextlib, hashlib, importlib.util, json, pathlib, sys, types
from unittest.mock import patch

HERE=pathlib.Path(__file__).resolve().parents[1]
ROOT=HERE.parents[2]
BASE=ROOT/"bench_anontated/growth-multifold/vllm-024"
OPT=ROOT/"bench_optimized/growth-multifold/vllm-024"

class Request:
    """Exact pinned Request.__lt__ ordering fields and statements."""
    def __init__(self,label,priority,arrival,request_id=None):
        self.label=label;self.priority=priority;self.arrival_time=float(arrival);self.request_id=request_id if request_id is not None else label
    def __lt__(self,other):
        if self.priority != other.priority:return self.priority < other.priority
        if self.arrival_time != other.arrival_time:return self.arrival_time < other.arrival_time
        if self.request_id != other.request_id:return self.request_id < other.request_id
        return id(self) < id(other)

perfmark=types.ModuleType("perfmark")
@contextlib.contextmanager
def region(name,**pcvs):yield
perfmark.region=region;request_module=types.ModuleType("vllm.v1.request");request_module.Request=Request
sys.modules["perfmark"]=perfmark;sys.modules["vllm.v1.request"]=request_module

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

baseline=load("queue_baseline",BASE/"vllm/v1/core/sched/request_queue.py")
optimized=load("queue_optimized",OPT/"vllm/v1/core/sched/request_queue.py")

def run(module,items,existing=(),incoming_kind="fcfs",self_alias=False):
    q=module.PriorityRequestQueue()
    for x in existing:q.add_request(x)
    if self_alias:
        for x in items:q.add_request(x)
        q.prepend_requests(q)
    else:
        incoming=module.FCFSRequestQueue() if incoming_kind=="fcfs" else module.PriorityRequestQueue()
        for x in items:incoming.add_request(x)
        q.prepend_requests(incoming)
    return [id(q.pop_request()) for _ in range(len(q))]

scenarios=[]
def check(name,items,existing=(),incoming_kind="fcfs",self_alias=False):
    before=[id(x) for x in items];a=run(baseline,items,existing,incoming_kind,self_alias);b=run(optimized,items,existing,incoming_kind,self_alias)
    assert a==b,(name,a,b);assert before==[id(x) for x in items]
    scenarios.append({"name":name,"length":len(items),"existing":len(existing),"incoming_kind":incoming_kind,"self_alias":self_alias,"popped_identity_sha256":hashlib.sha256(json.dumps(a).encode()).hexdigest()})

for n in range(11):
    for order in ("ascending","descending","mixed"):
        priorities=list(range(n))
        if order=="descending":priorities.reverse()
        elif order=="mixed":priorities=priorities[::2]+priorities[1::2]
        items=[Request(f"{n}-{order}-{i}",p,i) for i,p in enumerate(priorities)]
        check(f"length-{n}-{order}-fcfs",items,incoming_kind="fcfs")
        check(f"length-{n}-{order}-priority",items,incoming_kind="priority")

ties=[Request(f"tie-{i}",7,3.0,"same-id") for i in range(12)]
check("distinct-identity-final-tiebreak",ties)
same=Request("repeated",4,2.0,"same");check("repeated-identical-object",[same]*9)
for n in (16,33,64):
    prefix=list(range(n,n-8,-1));tail=list(range(8,n))
    check(f"descending-prefix-ascending-tail-{n}",[Request(f"pa-{n}-{i}",p,i) for i,p in enumerate(prefix+tail)])
    mixed=tail[::2]+tail[1::2]
    check(f"descending-prefix-mixed-tail-{n}",[Request(f"pm-{n}-{i}",p,i) for i,p in enumerate(prefix+mixed)])
existing=[Request(f"existing-{i}",20+i,i) for i in range(7)]
check("nonempty-existing",[Request(f"new-{i}",9-i,10+i) for i in range(10)],existing)
alias_items=[Request(f"alias-{i}",i%3,i) for i in range(10)]
check("priority-self-alias",alias_items,self_alias=True)

# A tiny incoming batch must not turn insertion into an O(existing) heapify.
# Patch the exact heapq module used by the loaded queue and assert the native
# bulk primitive is never reached for a 10,000-item existing heap.
for n in range(1, 9):
    q=optimized.PriorityRequestQueue()
    existing=[Request(f"large-existing-{n}-{i}",10000+i,i) for i in range(10000)]
    for x in existing:q.add_request(x)
    incoming=optimized.FCFSRequestQueue()
    items=[Request(f"tiny-incoming-{n}-{i}",n-i,20000+i) for i in range(n)]
    for x in items:incoming.add_request(x)
    with patch.object(optimized.heapq,"heapify",wraps=optimized.heapq.heapify) as heapify:
        q.prepend_requests(incoming)
        assert heapify.call_count == 0, (n, heapify.call_count)
    popped=[q.pop_request() for _ in range(len(q))]
    assert popped == sorted(existing+items)
    scenarios.append({"name":f"large-existing-10000-tiny-incoming-{n}",
                      "length":n,"existing":10000,"incoming_kind":"fcfs",
                      "self_alias":False,"heapify_calls":0,
                      "popped_identity_sha256":hashlib.sha256(
                          json.dumps([id(x) for x in popped]).encode()).hexdigest()})

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
receipt={"schema_version":1,"status":"passed","scenario_count":len(scenarios),"comparator_snapshot":{"path":"benchmarks/regions/vllm/upstream/vllm/v1/request.py","sha256":sha(ROOT/"benchmarks/regions/vllm/upstream/vllm/v1/request.py")},"baseline_source_sha256":sha(BASE/"vllm/v1/core/sched/request_queue.py"),"optimized_source_sha256":sha(OPT/"vllm/v1/core/sched/request_queue.py"),"optimization_patch_sha256":sha(OPT/"optimization.patch"),"scenarios":scenarios}
(HERE/"evidence/differential.json").write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps(receipt,indent=2))
