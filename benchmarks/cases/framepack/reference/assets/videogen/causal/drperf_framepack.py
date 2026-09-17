"""Price FramePack's per-section video handling with drperf.

The section loop is replayed on controlled pixels, so the only thing being counted is
what the loop does with the video: blend the new section in, then write. Declared
states are the section index and the number of frames already generated, so the cost
function says directly whether a section costs the same as the one before it.

  drperf-dev run --blocks --repeat 2 --state section=0,4,8,12,16,20 --state mode=0,1 \
      -o out/framepack -- python drperf_framepack.py
  drperf-dev derive out/framepack
"""
import os, sys

sys.path.insert(0, "/home/ubuntu/drperf/perfmark/python")
sys.path.insert(0, "/home/ubuntu/drperf-cases/videogen/causal/FramePack-fix")

import perfmark
import torch

from diffusers_helper.utils import soft_append_bcthw, save_bcthw_as_mp4, IncrementalMp4Writer

OUT = "/home/ubuntu/drperf-cases/.tmp/drperf_fp"
os.makedirs(OUT, exist_ok=True)

LWS = 9
OVERLAP = LWS * 4 - 3
FIRST_N = LWS * 4 + 1
LATER_N = (LWS * 2 - 1) * 4 + 1
H = W = 96          # small frames: the shape of the cost is what matters, not the pixels


def section_pixels(i, n):
    g = torch.Generator().manual_seed(500 + i)
    base = torch.randn(1, 3, 1, H, W, generator=g) * 0.6
    ramp = torch.linspace(-1, 1, n).view(1, 1, n, 1, 1)
    return torch.clamp(base + ramp * 0.4, -1, 1).expand(1, 3, n, H, W).contiguous()


def main():
    st = perfmark.states(section=8, mode=0)
    target = int(st["section"])     # how many sections to run before the measured one
    mode = int(st["mode"])          # 0 = stock, 1 = fixed

    history = None
    writer = None

    # Build up to the measured section without measuring, so the state under test is
    # "a section that follows `target` earlier ones".
    for i in range(target + 1):
        cur = section_pixels(i, FIRST_N if i == 0 else LATER_N)
        history = cur if history is None else soft_append_bcthw(history, cur, OVERLAP)
        measured = i == target
        frames_so_far = history.shape[2]

        if measured:
            with perfmark.region("section_save", section=i, frames=frames_so_far):
                if mode == 0:
                    save_bcthw_as_mp4(history, os.path.join(OUT, "stock.mp4"),
                                      fps=30, crf=16)
                else:
                    if writer is None:
                        writer = IncrementalMp4Writer(
                            os.path.join(OUT, "fixed.mp4"), fps=30, crf=16)
                    settled = history.shape[2] - OVERLAP
                    if settled > 0:
                        writer.append_bcthw(history[:, :, :settled])
                        history = history[:, :, settled:]
        else:
            if mode == 0:
                save_bcthw_as_mp4(history, os.path.join(OUT, "stock.mp4"), fps=30, crf=16)
            else:
                if writer is None:
                    writer = IncrementalMp4Writer(
                        os.path.join(OUT, "fixed.mp4"), fps=30, crf=16)
                settled = history.shape[2] - OVERLAP
                if settled > 0:
                    writer.append_bcthw(history[:, :, :settled])
                    history = history[:, :, settled:]

    if writer is not None:
        writer.close()
    print(f"section={target} mode={mode} frames={history.shape[2]}")


if __name__ == "__main__":
    main()
