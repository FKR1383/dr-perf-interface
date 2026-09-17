"""Check the reverse-order writer reproduces demo_gradio.py's video exactly.

The anti-drifting sampler prepends each section, so this replays that: build the
history by prepending, and compare FramePack's save-everything-each-section against
encoding each frame once and joining the chunks by copying packets.
"""
import os, sys, time

import numpy as np
import torch

sys.path.insert(0, "/home/ubuntu/drperf-cases/videogen/causal/FramePack-fix")
from diffusers_helper.utils import soft_append_bcthw, ReverseChunkMp4Writer, save_bcthw_as_mp4

OUT = "/home/ubuntu/drperf-cases/.tmp/framepack_rev"
os.makedirs(OUT, exist_ok=True)
FPS, CRF = 30, 16


def read_frames(path):
    import av
    fr = []
    with av.open(path) as c:
        for f in c.decode(video=0):
            fr.append(f.to_ndarray(format="rgb24"))
    return np.stack(fr) if fr else np.zeros((0,))


def section_pixels(i, n, h, w):
    g = torch.Generator().manual_seed(500 + i)
    base = torch.randn(1, 3, 1, h, w, generator=g) * 0.6
    ramp = torch.linspace(-1, 1, n).view(1, 1, n, 1, 1)
    return torch.clamp(base + ramp * 0.4, -1, 1).expand(1, 3, n, h, w).contiguous()


def run(mode, sections, lws, h, w):
    overlap = lws * 4 - 3
    first_n = lws * 4 + 1
    later_n = (lws * 2 - 1) * 4 + 1
    history, writer, t_video, files = None, None, 0.0, 0
    for i in range(sections):
        is_last = i == sections - 1
        cur = section_pixels(i, first_n if i == 0 else later_n, h, w)
        # the base demo prepends: soft_append_bcthw(current, history, overlap)
        history = cur if history is None else soft_append_bcthw(cur, history, overlap)
        t = time.perf_counter()
        if mode == "stock":
            path = os.path.join(OUT, f"stock_{history.shape[2]}.mp4")
            save_bcthw_as_mp4(history, path, fps=FPS, crf=CRF)
            files += 1
            last = path
        else:
            path = os.path.join(OUT, "fixed.mp4")
            if writer is None:
                writer = ReverseChunkMp4Writer(path, fps=FPS, crf=CRF)
            writer.add_settled(history, overlap, is_last)
            writer.assemble()
            if is_last:
                writer.cleanup()
            files = 1
            last = path
        t_video += time.perf_counter() - t
    encoded = writer.encoded if writer else None
    return t_video, last, history.shape[2], files, encoded


def main():
    sections = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    h = w = int(sys.argv[2]) if len(sys.argv) > 2 else 256
    lws = 9
    for f in os.listdir(OUT):
        p = os.path.join(OUT, f)
        os.remove(p) if os.path.isfile(p) else None
    print(f"Reverse (anti-drifting) loop: {sections} sections, {h}x{w}\n")
    ts, ps, ns, fs, _ = run("stock", sections, lws, h, w)
    tf, pf, nf, ff, enc = run("fixed", sections, lws, h, w)
    print(f"{'':10s} {'video time':>11s} {'frames':>8s} {'encoded':>9s} {'files':>6s}")
    print(f"{'stock':10s} {ts:10.2f}s {ns:8d} {'n/a':>9s} {fs:6d}")
    print(f"{'fixed':10s} {tf:10.2f}s {nf:8d} {enc:9d} {ff:6d}")
    print(f"{'':10s} {ts/tf:9.1f}x faster\n")
    A, B = read_frames(ps), read_frames(pf)
    print(f"decoded: stock {A.shape}, fixed {B.shape}")
    if A.shape != B.shape:
        print("SHAPES DIFFER")
        return
    d = np.abs(A.astype(np.int16) - B.astype(np.int16))
    print(f"max per-pixel difference: {d.max()}  mean {d.mean():.4f}")
    print("FRAMES IDENTICAL" if d.max() == 0 else "frames differ")


if __name__ == "__main__":
    main()
