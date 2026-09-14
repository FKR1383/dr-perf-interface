## FramePack: a constant-cost generator with a quadratic save

FramePack is the most widely used causal video generator, designed so that ordinary
hardware can make long video: it produces a section at a time, and its headline property
is that a section costs the same whether it is the first or the fiftieth. The sampling
loop delivers that. The save in the same loop does not.

Both entry points, `demo_gradio.py` and `demo_gradio_f1.py`, end each section with

    save_bcthw_as_mp4(history_pixels, output_filename, fps=30, crf=mp4_crf)

on the whole accumulated video. Section k re-encodes every frame produced so far, so an
S-section run encodes S(S+1)/2 sections' worth of frames instead of S, and leaves one
MP4 per section on disk.

This is the class of problem where the cost contradicts the code rather than the class
a screening harness finds. Nothing at the call site says the preview costs the whole
video; the loop reads as "generate a section, save a preview". It is invisible on a
short run, where it is 2.5x and looks like ordinary overhead, and the demo defaults
produce exactly that. And it is CPU work, so anyone watching GPU utilisation sees
nothing at all.

### The claim, measured

Encoding is flat at 15.9 ms per frame at FramePack's default 640x640, crf 16, 30 fps,
so all growth is re-encoding:

| video length | sections | frames encoded | as written | written once | waste |
|---|---|---|---|---|---|
| 5 s | 4 | 360 | 5.7 s | 2.3 s | 2.5x |
| 30 s | 25 | 11,700 | 186 s | 14 s | 13x |
| 60 s | 50 | 45,900 | 731 s | 29 s | 25x |
| 120 s | 100 | 181,800 | 2,897 s | 57 s | 50x |

`soft_append_bcthw` grows too, since it copies the whole history each section: 139 ms at
37 frames to 534 ms at 901, with 4.4 GB of float32 pixels resident by the end.

### Two fixes, because the two entry points run in opposite directions

`demo_gradio_f1.py` generates forward. Frames go to one open encoder as soon as blending
can no longer reach them, and are then dropped from `history_pixels`, since what is on
disk cannot change. Output is frame-for-frame identical and peak pixel memory becomes
constant. The file is fragmented per frame and flushed so the preview stays playable
while it is written; it trails by the encoder's lookahead, about one section.

`demo_gradio.py` prepends each section, so frames cannot be appended to one stream.
Each section's settled frames are encoded to their own chunk and the chunks are joined
by copying compressed packets, which never re-encodes. That leaves codec noise at chunk
boundaries, so fidelity was checked against the true pixels instead of against stock.

### Results, CPU

| variant | 4 sections | 8 | 16 | output |
|---|---|---|---|---|
| forward | 2.6x | 4.5x | 8.8x | byte-identical, 0 max per-pixel difference |
| reverse | 2.6x | 4.4x | 7.2x | 14.73 dB against stock's 14.74 dB |

Stock video-writing time grows 3.4x per doubling of length; fixed grows 1.9x. Peak
pixels held drops from the whole video to 33 frames: 154 MB rather than 2.7 GB for a
30-second video, and about 17 GB avoided at two minutes.

### Results, end to end on an A100

The right metric for a video generator is the rate it produces frames, and in those
terms this is not a speedup. It is the removal of a decay.

A 30-second video, 25 steps, 640x608, xformers active, high-VRAM confirmed on both
phases, GPU verified free before each. Stock's rate falls steadily as the video it is
appending to grows; fixed holds flat:

| section | 2 | 7 | 12 | 17 | 22 | 25 |
|---|---|---|---|---|---|---|
| stock | 0.8867 fps | 0.7895 | 0.7171 | 0.6534 | 0.6071 | 0.5816 |
| fixed | 0.9160 fps | 0.9045 | 0.9023 | 0.9023 | 0.9045 | 0.8845 |

**Stock loses 34% of its generation rate inside a single 30-second video.** Fixed holds
0.90 fps, within 3% end to end. Nothing was made faster: the machine stops being asked
to redo work, so the rate FramePack was designed to hold is the rate it holds.

| | stock | fixed |
|---|---|---|
| time | 1,276.9 s | 994.8 s |
| generation rate | 0.7056 fps | 0.9057 fps |
| output files | 25 | 1 |
| disk written | 424.9 MB | 28.9 MB |
| peak host memory | 14,089 MB | 11,883 MB |

**1.28x end to end, 282 seconds saved**, 2.2 GB less host memory, 396 MB never written.

Fitting the measured slope, stock at 38.75 + 0.926 per section against a flat 39.8, the
gain grows with length because the waste is quadratic:

| video | 15 s | 30 s | 60 s | 120 s | 300 s |
|---|---|---|---|---|---|
| gain | 1.12x | 1.28x (measured) | 1.57x | 2.15x | 3.89x |

### What drperf found once the whole host path was covered

The first probe marked one region and confirmed the issue already found by reading. Marking
the whole per-section host path, with the bodies copied line for line from the repository
and only markers added, shows it is not one stage but four. Each one is handed the entire
accumulated video every section, and each carries a coefficient per frame of history:

| region | instructions per frame of history | share | what it is |
|---|---|---|---|
| `save_encode` | 6,121,778 | 96.9% | libx264 re-encoding frames it already encoded |
| `save_to_uint8` | 138,240 | 2.2% | `float32 -> uint8` over the whole history |
| `save_clamp_float` | 46,656 | 0.7% | `clamp` and scale, allocating a float copy of the whole history |
| `blend_concat` | 12,096 | 0.2% | `torch.cat` copying the history to grow it by one section |
| `save_rearrange` | 0 | - | einops returns a view, correctly free |
| `blend_weights` | 0 | - | touches only the overlap, correct |
| `blend_to` | 0 | - | dtype already matches, correct |

Encoding dominates at 97%, but the three tensor passes above it are real and were invisible
in wall-clock next to the codec. Two of the seven regions are correct by construction, and
the derivation says so with a coefficient of exactly zero rather than a small number, which
is what makes the four that are not correct stand out.

The fixed version's report is the cleaner statement. drperf declines to fit `blend_concat`,
`blend_weights` and `blend_to` at all, saying "only 1 state point observed", because the
history handed to them is 33 frames in every section of every run: the state stopped
varying, so there is nothing left to be a function of. And the enclosing region goes from

    stock:  cost = 256,321,014.6*section + 274,238,807.8
    fixed:  cost =          -8.7*section + 288,262,771.5

### A measurement that had to be thrown away

An earlier run of this comparison gave 1.10x, and it was wrong. FramePack's worker leaves
its process alive after finishing, holding 68 GB of GPU memory, so the stock phase was
still resident when the fixed phase started and flipped it into low-VRAM mode with model
offloading. The two phases were not run under the same conditions.

It surfaced only because the generation rate looked too low to be believable, at 0.3 fps
on an A100. That turned out to be a second problem: FramePack looks for sage-attn,
flash-attn or xformers and silently falls back to PyTorch SDPA when none is installed.
Fixing the attention backend raised the baseline to 0.7 fps and, because the wasted
encoding is fixed CPU cost, made the fix worth more rather than less: 1.10x became 1.28x.

Two lessons, both cheap to apply and both nearly missed. A number that looks implausible
for the hardware is usually the measurement rather than the subject. And a comparison
between two phases of the same script needs the machine returned to the same state
between them, which here meant waiting for the GPU to actually be free and recording
which mode each phase chose.

### What the end-to-end run cannot show, and why

The two end-to-end videos differ at 9.41 dB, far more than codec noise. That is not the
fix. Running the unmodified code twice with the same seed gives 19.51 dB between its own
two outputs, while stock against fixed gives 21.41 dB: two runs of stock differ from each
other more than stock differs from fixed. FramePack's generation is not reproducible run
to run on this GPU, so no end-to-end pair could ever have matched. Frame identity is
therefore established on CPU, where the pixels going into the loop are controlled, and
there it is exact.

This is worth stating plainly because it is the trap in this kind of measurement: an
end-to-end diff on a generative pipeline looks like a correctness check and is not one.
The control that distinguishes them costs three short runs.

