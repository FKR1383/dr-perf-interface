# vllm-062 full-feedback result

Status: `success`; iterations: 3; fixed workload: `5d5c42c050835a2697879e5bc95684ef555e184babedd62402ed5c5b8e00bc58`.

| iteration | exact PCVs | irregularity | outcome |
| ---: | --- | ---: | --- |
| 1 | `moved_requests = sum((i < self.num_reqs for i in self.batch_update_builder.removed))`; `removed_requests = len(self.batch_update_builder.removed)`; `nonempty_condensation = int(bool(self.batch_update_builder.removed) and self.num_reqs > 0)`; `moved_tokens = sum((int(self.num_tokens_no_spec[i]) + len(self.spec_token_ids[i]) for i in range(self.num_reqs, len(self._req_ids)) if self._req_ids[i] is not None))` | 29.0745% | retry |
| 2 | `moved_requests = sum((i < self.num_reqs for i in self.batch_update_builder.removed))`; `removed_requests = len(self.batch_update_builder.removed)`; `nonempty_condensation = int(bool(self.batch_update_builder.removed) and self.num_reqs > 0)`; `moved_generators = sum((i in self.generators for i in range(self.num_reqs, len(self._req_ids)) if self._req_ids[i] is not None))` | 12.62% | retry |
| 3 | `moved_requests = sum((i < self.num_reqs for i in self.batch_update_builder.removed))`; `removed_requests = len(self.batch_update_builder.removed)`; `nonempty_condensation = int(bool(self.batch_update_builder.removed) and self.num_reqs > 0)` | 3.49879% | success |
