"""Large bounded priority-queue workload with ordering controls."""
import argparse, random, sys, types
from pathlib import Path

class Request:
    """Comparator copied from pinned vLLM Request.__lt__ at revision 2cf0a691."""
    def __init__(self,i,priority,arrival):self.request_id=f"r{i}";self.priority=priority;self.arrival_time=float(arrival)
    def __lt__(self,other):
        if self.priority != other.priority:return self.priority < other.priority
        if self.arrival_time != other.arrival_time:return self.arrival_time < other.arrival_time
        if self.request_id != other.request_id:return self.request_id < other.request_id
        return id(self) < id(other)

def request(i,priority,arrival=None):return Request(i,priority,i if arrival is None else arrival)

def ordered_items(n, order):
    priorities=list(range(n))
    if order == "descending": priorities.reverse()
    elif order == "mixed": random.Random(1907+n).shuffle(priorities)
    return [request(i,p) for i,p in enumerate(priorities)]

def exercise(n, order, existing=0, simple=False):
    from vllm.v1.core.sched.request_queue import FCFSRequestQueue, PriorityRequestQueue
    q=PriorityRequestQueue()
    initial=[request(100000+i,2*n+i) for i in range(existing)]
    for item in initial:q.add_request(item)
    incoming=FCFSRequestQueue();items=ordered_items(n,order)
    for item in items:incoming.add_request(item)
    q.prepend_requests(incoming);assert len(q)==existing+n
    popped=[q.pop_request() for _ in range(len(q))]
    assert popped==sorted(initial+items) and {id(x) for x in popped}=={id(x) for x in initial+items}

def edge_cases():
    from vllm.v1.core.sched.request_queue import PriorityRequestQueue
    empty=PriorityRequestQueue();empty.prepend_requests(PriorityRequestQueue());assert len(empty)==0
    q=PriorityRequestQueue();tied=[request(i,7,3.0) for i in range(12)];incoming=PriorityRequestQueue()
    for x in tied:incoming.add_request(x)
    q.prepend_requests(incoming);assert [q.pop_request() for _ in range(12)]==sorted(tied)
    alias=PriorityRequestQueue();originals=[request(200+i,i%3) for i in range(9)]
    for x in originals:alias.add_request(x)
    alias.prepend_requests(alias);out=[alias.pop_request() for _ in range(18)]
    assert out==sorted(originals+originals) and all(out.count(x)==2 for x in originals)

def main():
    p=argparse.ArgumentParser();p.add_argument("--source-root",required=True);p.add_argument("--profile",choices=("descending","ascending","mixed","all"),default="descending");a=p.parse_args();sys.path.insert(0,a.source_root)
    from marker_probe import Probe
    probe=Probe();request_module=types.ModuleType("vllm.v1.request");request_module.Request=Request;sys.modules["vllm.v1.request"]=request_module
    sizes=(16,32,64,128,256,512,1024) if a.profile=="all" else (512,600,700,800,900,1000)
    for order in (("descending","ascending","mixed") if a.profile=="all" else (a.profile,)):
        for n in sizes:exercise(n,order,existing=0 if a.profile!="all" else n//8)
    if a.profile=="all":edge_cases()
    module=sys.modules["vllm.v1.core.sched.request_queue"]
    assert Path(module.__file__).resolve()==Path(a.source_root,"vllm/v1/core/sched/request_queue.py").resolve()
    probe.finish("vllm-024")

if __name__=="__main__":main()
