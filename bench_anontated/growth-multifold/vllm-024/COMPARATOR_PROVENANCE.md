# Request comparison provenance

The bounded workload's `Request.__lt__` body is copied statement-for-statement
from `vllm/v1/request.py` at pinned revision
`2cf0a6915ce544dc493a0990f2ea38d81601128a`. The pinned source snapshot has
SHA-256 `0287844f70eeaeb077d714e833a4b449a15e045a6516f8530182e357a5bec82f`.
It compares priority, arrival time, request ID, and finally object identity in
that order. The stand-in only omits unrelated Request state so heap scheduling
can be measured without loading the model runtime.
