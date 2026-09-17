"""Prove the incremental writer produces the same video, and measure what it saves.

The section loop of demo_gradio_f1.py is replayed exactly (same blending, same
overlap, same frame counts) on synthetic pixels, once with FramePack's
save-the-whole-video-each-section and once with the incremental writer. The two
outputs are then decoded and compared frame by frame.

No GPU or model weights: the loop's video handling is pure CPU, which is the point.
"""
import os, sys, time

import numpy as np
import torch

sys.path.insert(0, "/home/ubuntu/drperf-cases/videogen/causal/FramePack-fix")
from diffusers_helper.utils import soft_append_bcthw, IncrementalMp4Writer

OUT = "/home/ubuntu/drperf-cases/.tmp/framepack_test"
os.makedirs(OUT, exist_ok=True)

FPS = 30
CRF = 16


def save_whole(x, path, fps=FPS, crf=CRF):
    """FramePack's save_bcthw_as_mp4, with PyAV standing in for the dropped torchvision call."""
    import av, einops

    b, c, t, h, w = x.shape
    per_row = b
    for p in [6, 5, 4, 3, 2]:
        if b % p == 0:
            per_row = p
            break
    x = torch.clamp(x.float(), -1., 1.) * 127.5 + 127.5
    x = x.detach().cpu().to(torch.uint8)
    x = einops.rearrange(x, '(m n) c t h w -> t (m h) (n w) c', n=per_row)
    with av.open(path, mode="w") as container:
        stream = container.add_stream("libx264", rate=fps)
        stream.height, stream.width = x.shape[1], x.shape[2]
        stream.pix_fmt = "yuv420p"
        stream.options = {"crf": str(int(crf))}
        for frame in x.numpy():
            container.mux(stream.encode(av.VideoFrame.from_ndarray(frame, format="rgb24")))
        container.mux(stream.encode())


def read_frames(path):
    import av

    frames = []
    with av.open(path) as container:
        for frame in container.decode(video=0):
            frames.append(frame.to_ndarray(format="rgb24"))
    return np.stack(frames) if frames else np.zeros((0,))


def section_pixels(index, frames, h, w):
    """Deterministic, smoothly varying content so the encoder does realistic work."""
    g = torch.Generator().manual_seed(1000 + index)
    base = torch.randn(1, 3, 1, h, w, generator=g) * 0.6
    ramp = torch.linspace(-1, 1, frames).view(1, 1, frames, 1, 1)
    return torch.clamp(base + ramp * 0.4, -1, 1).expand(1, 3, frames, h, w).contiguous()


def run(mode, sections, latent_window_size, h, w):
    # Exactly the F1 loop's arithmetic: the first section decodes
    # latent_window_size + 1 latents, later sections decode latent_window_size * 2
    # and blend back over `overlap`, so each later section adds 36 frames.
    overlap = latent_window_size * 4 - 3
    first_frames = latent_window_size * 4 + 1
    later_frames = (latent_window_size * 2 - 1) * 4 + 1
    history = None
    writer = None
    written = 0
    encode_time = 0.0
    files = 0
    peak = 0

    for index in range(sections):
        current = section_pixels(index, first_frames if index == 0 else later_frames, h, w)
        if history is None:
            history = current
        else:
            history = soft_append_bcthw(history, current, overlap)

        final = index == sections - 1
        t = time.perf_counter()
        if mode == "stock":
            path = os.path.join(OUT, f"stock_{history.shape[2]}.mp4")
            save_whole(history, path)
            files += 1
            last_path = path
        else:
            path = os.path.join(OUT, "incremental.mp4")
            if writer is None:
                writer = IncrementalMp4Writer(path, fps=FPS, crf=CRF)
                files = 1
            settled = history.shape[2] - (0 if final else overlap)
            if settled > 0:
                writer.append_bcthw(history[:, :, :settled])
                # mirror the patch: written frames are dropped, so memory stays flat
                history = history[:, :, settled:]
                written += settled
            peak = max(peak, history.shape[2])
            if final:
                writer.close()
            else:
                writer.flush()
            last_path = path
        encode_time += time.perf_counter() - t

    return encode_time, last_path, (written if mode != 'stock' else history.shape[2]), files, max(peak, history.shape[2])


def main():
    sections = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    h = w = int(sys.argv[2]) if len(sys.argv) > 2 else 320
    lws = 9  # FramePack's default latent_window_size

    print(f"Replaying the F1 section loop: {sections} sections, "
          f"latent_window_size {lws}, {h}x{w}\n")

    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))

    t_stock, stock_path, n_stock, files_stock, peak_stock = run("stock", sections, lws, h, w)
    t_inc, inc_path, n_inc, files_inc, peak_inc = run("incremental", sections, lws, h, w)

    print(f"{'':14s} {'video-writing time':>19s} {'frames':>8s} {'files left':>11s} {'peak frames held':>17s}")
    print(f"{'stock':14s} {t_stock:18.2f}s {n_stock:8d} {files_stock:11d} {peak_stock:17d}")
    print(f"{'incremental':14s} {t_inc:18.2f}s {n_inc:8d} {files_inc:11d} {peak_inc:17d}")
    print(f"{'':14s} {t_stock/t_inc:17.1f}x faster\n")

    a = read_frames(stock_path)
    b = read_frames(inc_path)
    print(f"decoded frames: stock {a.shape}, incremental {b.shape}")
    if a.shape != b.shape:
        print("SHAPES DIFFER")
        return
    diff = np.abs(a.astype(np.int16) - b.astype(np.int16))
    print(f"max per-pixel difference: {diff.max()}   mean: {diff.mean():.4f}")
    print("FRAMES IDENTICAL" if diff.max() == 0 else "frames differ (see above)")


if __name__ == "__main__":
    main()
