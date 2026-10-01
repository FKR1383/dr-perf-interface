# vllm-040 full-feedback result

Status: `success`; iterations: 1; fixed workload: `b4dc7a44446129a390f3562813f437f232c27e68c2333430dd1919c735e0629a`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `request_blocks = len(self.req_to_blocks[running_request_id])`; `first_block_shared = int(bool(self.req_to_blocks[running_request_id]) and self.req_to_blocks[running_request_id][0].ref_cnt == len(self.req_to_blocks))`; `fully_shared_length = len(self.req_to_blocks[running_request_id]) if self.req_to_blocks[running_request_id] and self.req_to_blocks[running_request_id][-1].ref_cnt == len(self.req_to_blocks) else 0`; `active_requests = len(self.req_to_blocks)` | 0% | success |
