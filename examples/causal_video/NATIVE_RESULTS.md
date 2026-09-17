# Inferix: native A100 results

On the pinned pretrained Self-Forcing model, two changes reduce median request
latency from **41.29 to 12.65 seconds (69.4% lower, 3.26× speedup)**. All three
variants saved byte-identical video tensors. These are native A100 results;
the completed [GX partial run](PARTIAL_RESULTS.md) agrees that the GPU is busy,
but omits the dominant PCIe transfer service and has 168 unmatched launches.
A separate baseline drperf run
measures marked host instructions under GX emulation.

| Variant | Three warmed native runs, seconds | Median | Peak allocated GPU memory |
| --- | --- | --- | --- |
| Host KV cache, original streaming decode | 41.230, 41.291, 41.305 | 41.291 | 24.86 GB |
| GPU KV cache, original streaming decode | 16.553, 16.662, 16.738 | 16.662 | 30.99 GB |
| GPU KV cache, skip discarded whole decode | 12.580, 12.652, 12.708 | 12.652 | 30.99 GB |

Hardware: one A100-PCIE-40GB, GPU1, on an AMD EPYC 9554 host.
GPU1 reports a PCIe Gen4 ×8 link; GPU0 was not used. Each variant loaded the
same trained weights, ran a full warmup, then generated three requests in the
same process. Variants ran sequentially, not in randomized order. These are
three observations per variant, not a confidence interval. Loading and video
file encoding are excluded; text encoding, denoising, VAE decode and output
transfer are included.

The request has 21 latent frames, four denoising steps per three-frame block,
480 × 832 pixels, batch one, fixed prompt and seed 42. The pinned Inferix
TRUE_STREAMING path returns seven nine-frame chunks, 63 pixel frames total.
That behavior is preserved; this is not an 81-frame throughput claim.

## What changed

**Cache residency:** `config.model_kwargs.enable_kv_offload=False` selects an
existing framework option. The default is true even for this A100 workload.
The persistent self/cross KV allocation is 5.71 GiB, and it fits on this GPU.
This is a configuration improvement, not a CPU source optimization.

Source inspection shows each layer fetching its full cache and writing the
active prefix back at every forward. For this request, the self-attention cache
alone implies 211.34 GB host-to-device plus 120.77 GB device-to-host payload.
Nsight measured 211.44 GB host-to-device and 121.16 GB device-to-host
(25.38 seconds of combined GPU copy durations), closely matching the
self-cache estimate plus other transfers. Kernels and copies occupy 98.7%
of its 41.30-second GPU event span. The long host CUDA synchronization calls
mostly wait on that scheduled work; they are not independent CPU dispatch cost.
The source estimate omits cross-attention and other transfers.

The active prefix grows with block index, so the writeback term sums
`1 + 2 + ... + B = B*(B+1)/2`, where B is the number of generated blocks. A
semantic variable for that term is the sum of active cache lengths. Moving the
cache to the GPU removes these PCIe transfers; GPU-local reads, writes and
stacking still occur. drperf's CPU instruction interface does not measure PCIe
service time, and current GX partial timing assigns memcpy zero service cost.

**Redundant decode:** TRUE_STREAMING decodes each latent block in its callback.
The original call also requests a complete sequence decode and discards its
pixel result. `inferix_decode.py` changes that call to NO_DECODE while retaining
the block callbacks, assembled video, final latents, fallback decode, and cache
clearing. The main measured request has eight VAE wrapper calls before and
seven after this change.

The saved `video.pt` SHA256 is identical for all three variants:
`5de8121ed9e0d6d9c9fb5f85dc5ff0c53aa4ca5d213079488261ba4481d719ad`.
A separate warmup plus two six-latent-frame segments also passed exact
callback, output-video and final-latent comparison, with empty VAE caches on
both sides. Validation-copy timings are excluded. The
host-metadata adaptation used in every row also produced the same native saved
video as the unadapted source.

These leads came from source inspection and native profiles. They must not be
presented as optimizations discovered by drperf feedback.

## Baseline drperf feedback

A separate host-KV baseline run counted **5.58 billion exclusive instructions
across marked regions**, with no collection validity errors, dropped states,
or instructions charged to `gx_cuda.so`. Self-attention accounted for 1.55
billion, the transformer block wrapper for 1.21 billion, cross-attention for
0.91 billion, causal RoPE for 0.75 billion, and VAE decoder for 0.64 billion.
These are disjoint marked-region counts, not an end-to-end CPU time or a GPU
critical path.

The self-attention marker declared query tokens and context tokens. Query
tokens stayed fixed at 4,680, while context took seven values from 4,680 to
32,760 (150 calls each). The full two-variable relation is rank deficient.
Conditioning on the observed fixed query length gives a fit of about
`1,457,699 - 0.00996 × context_tokens` exclusive instructions per call, with
1.19% maximum unexplained fraction. The tiny negative slope is not evidence
that longer context saves CPU work; mean counts are roughly 1.47 million per
call across these states. It does show that CPU instruction count here does
not track the large GPU/PCIe cost of growing cached context. The drperf run
does not measure PCIe transfer service, so it cannot independently quantify
the KV-residency speedup. [Checked-in drperf evidence](evidence/inferix-drperf.json)
links the raw counts and fitted relation.

[Machine-readable evidence](evidence/inferix-native.json) records inputs,
package versions, measured times, memory, report hashes and weight identities.
See [the study protocol and limitations](README.md) for the separate GX,
CPU-profile and drperf workflows.
