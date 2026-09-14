# FCFSRequestQueue.peek_request

Inspect the marked function in `vllm/v1/core/sched/request_queue.py` at the pinned revision.
The marker has no PCVs; identify useful state expressions for its cost.

Exercise the named vLLM CPU execution path with a small cached model and bounded request batches. Adjust request options to reach this method; no particular dependency is supplied.

Apply this case patch independently in an upstream checkout. The snapshot is
source context, not a standalone program. Install the matching project
dependencies, make `perfmark/python` importable and build libperfmark before
measuring. This collected region has not been built or executed as a new case.
Keep the code behavior unchanged while adding observation state.
