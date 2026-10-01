# agent_PCVs: full-feedback PCV selector

You are the only PCV-selection agent for exactly one benchmark case. Your
conversation persists across that case's iterations and is never reused for
another case. You have no tools and cannot execute Dr. Perf directly. Treat
Dr. Perf as a black box: you propose a candidate, a trusted deterministic
script validates it and runs Dr. Perf, and on the next turn you receive the
complete Dr. Perf metrics report produced for that candidate.

Select between 1 and 4 cheap state expressions available when the marked
region is entered that explain its instruction count. Any cheap mathematical
derivation of entry state is allowed, including products, powers, comparisons,
conditional expressions, and cardinalities; runtime/library entry state is
also allowed. Avoid side effects, expensive computation, filesystem access,
counters, timers, and values outside signed 64-bit range.

The workload, target implementation, marker boundary, and correctness checks
are fixed for the entire case. Never propose changes to them. Return only the
candidate JSON required by the schema. Success requires valid irregularity
strictly below 10 percent. Coefficients are fitted by Dr. Perf; do not provide
coefficients as separate output.

This is iteration 1. The complete sanitized benchmark context follows. No previous annotations or measurements are included.

CASE: wan-041
SANITIZED BENCHMARK:
--- FILE: src/diffusers/video_processor.py ---
# Copyright 2026 The HuggingFace Team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import perfmark
import warnings

import numpy as np
import PIL
import torch
import torch.nn.functional as F

from .image_processor import VaeImageProcessor, is_valid_image, is_valid_image_imagelist


class VideoProcessor(VaeImageProcessor):
    r"""Simple video processor."""

    def preprocess_video(self, video, height: int | None = None, width: int | None = None, **kwargs) -> torch.Tensor:
        r"""
        Preprocesses input video(s). Keyword arguments will be forwarded to `VaeImageProcessor.preprocess`.

        Args:
            video (`list[PIL.Image]`, `list[list[PIL.Image]]`, `torch.Tensor`, `np.array`, `list[torch.Tensor]`, `list[np.array]`):
                The input video. It can be one of the following:
                * list of the PIL images.
                * list of list of PIL images.
                * 4D Torch tensors (expected shape for each tensor `(num_frames, num_channels, height, width)`).
                * 4D NumPy arrays (expected shape for each array `(num_frames, height, width, num_channels)`).
                * list of 4D Torch tensors (expected shape for each tensor `(num_frames, num_channels, height,
                  width)`).
                * list of 4D NumPy arrays (expected shape for each array `(num_frames, height, width, num_channels)`).
                * 5D NumPy arrays: expected shape for each array `(batch_size, num_frames, height, width,
                  num_channels)`.
                * 5D Torch tensors: expected shape for each array `(batch_size, num_frames, num_channels, height,
                  width)`.
            height (`int`, *optional*, defaults to `None`):
                The height in preprocessed frames of the video. If `None`, will use the `get_default_height_width()` to
                get default height.
            width (`int`, *optional*`, defaults to `None`):
                The width in preprocessed frames of the video. If `None`, will use get_default_height_width()` to get
                the default width.

        Returns:
            `torch.Tensor` of shape `(batch_size, num_channels, num_frames, height, width)`:
                A 5D tensor holding the batched channels-first video(s).
        """
        if isinstance(video, list) and isinstance(video[0], np.ndarray) and video[0].ndim == 5:
            warnings.warn(
                "Passing `video` as a list of 5d np.ndarray is deprecated."
                "Please concatenate the list along the batch dimension and pass it as a single 5d np.ndarray",
                FutureWarning,
            )
            video = np.concatenate(video, axis=0)
        if isinstance(video, list) and isinstance(video[0], torch.Tensor) and video[0].ndim == 5:
            warnings.warn(
                "Passing `video` as a list of 5d torch.Tensor is deprecated."
                "Please concatenate the list along the batch dimension and pass it as a single 5d torch.Tensor",
                FutureWarning,
            )
            video = torch.cat(video, axis=0)

        # ensure the input is a list of videos:
        # - if it is a batch of videos (5d torch.Tensor or np.ndarray), it is converted to a list of videos (a list of 4d torch.Tensor or np.ndarray)
        # - if it is a single video, it is converted to a list of one video.
        if isinstance(video, (np.ndarray, torch.Tensor)) and video.ndim == 5:
            video = list(video)
        elif isinstance(video, list) and is_valid_image(video[0]) or is_valid_image_imagelist(video):
            video = [video]
        elif isinstance(video, list) and is_valid_image_imagelist(video[0]):
            video = video
        else:
            raise ValueError(
                "Input is in incorrect format. Currently, we only support numpy.ndarray, torch.Tensor, PIL.Image.Image"
            )

        video = torch.stack([self.preprocess(img, height=height, width=width, **kwargs) for img in video], dim=0)

        # move the number of channels before the number of frames.
        video = video.permute(0, 2, 1, 3, 4)

        return video

    def postprocess_video(
        self, video: torch.Tensor, output_type: str = "np", **kwargs
    ) -> np.ndarray | torch.Tensor | list[PIL.Image.Image]:
        r"""
        Converts a video tensor to a list of frames for export. Keyword arguments will be forwarded to
        `VaeImageProcessor.postprocess`.

        Args:
            video (`torch.Tensor`): The video as a tensor.
            output_type (`str`, defaults to `"np"`): Output type of the postprocessed `video` tensor.
        """
        batch_size = video.shape[0]
        outputs = []
        for batch_idx in range(batch_size):
            batch_vid = video[batch_idx].permute(1, 0, 2, 3)
            batch_output = self.postprocess(batch_vid, output_type, **kwargs)
            outputs.append(batch_output)

        if output_type == "np":
            with perfmark.region("wan-041"):
                outputs = np.stack(outputs)
        elif output_type == "pt":
            outputs = torch.stack(outputs)
        elif not output_type == "pil":
            raise ValueError(f"{output_type} does not exist. Please choose one of ['np', 'pt', 'pil']")

        return outputs

    @staticmethod
    def classify_height_width_bin(height: int, width: int, ratios: dict) -> tuple[int, int]:
        r"""
        Returns the binned height and width based on the aspect ratio.

        Args:
            height (`int`): The height of the image.
            width (`int`): The width of the image.
            ratios (`dict`): A dictionary where keys are aspect ratios and values are tuples of (height, width).

        Returns:
            `tuple[int, int]`: The closest binned height and width.
        """
        ar = float(height / width)
        closest_ratio = min(ratios.keys(), key=lambda ratio: abs(float(ratio) - ar))
        default_hw = ratios[closest_ratio]
        return int(default_hw[0]), int(default_hw[1])

    @staticmethod
    def resize_and_crop_tensor(samples: torch.Tensor, new_width: int, new_height: int) -> torch.Tensor:
        r"""
        Resizes and crops a tensor of videos to the specified dimensions.

        Args:
            samples (`torch.Tensor`):
                A tensor of shape (N, C, T, H, W) where N is the batch size, C is the number of channels, T is the
                number of frames, H is the height, and W is the width.
            new_width (`int`): The desired width of the output videos.
            new_height (`int`): The desired height of the output videos.

        Returns:
            `torch.Tensor`: A tensor containing the resized and cropped videos.
        """
        orig_height, orig_width = samples.shape[3], samples.shape[4]

        # Check if resizing is needed
        if orig_height != new_height or orig_width != new_width:
            ratio = max(new_height / orig_height, new_width / orig_width)
            resized_width = int(orig_width * ratio)
            resized_height = int(orig_height * ratio)

            # Reshape to (N*T, C, H, W) for interpolation
            n, c, t, h, w = samples.shape
            samples = samples.permute(0, 2, 1, 3, 4).reshape(n * t, c, h, w)

            # Resize
            samples = F.interpolate(
                samples, size=(resized_height, resized_width), mode="bilinear", align_corners=False
            )

            # Center Crop
            start_x = (resized_width - new_width) // 2
            end_x = start_x + new_width
            start_y = (resized_height - new_height) // 2
            end_y = start_y + new_height
            samples = samples[:, :, start_y:end_y, start_x:end_x]

            # Reshape back to (N, C, T, H, W)
            samples = samples.reshape(n, t, c, new_height, new_width).permute(0, 2, 1, 3, 4)

        return samples

--- FILE: tests/test_case.py ---
"""Correctness and marker-reachability test for wan-041."""
import argparse
from marker_probe import Probe

parser = argparse.ArgumentParser()
parser.add_argument("--source-root", required=True)
args = parser.parse_args()
probe = Probe()
from helper import run
run("wan-041", args.source_root)
probe.finish("wan-041")

--- FILE: tests/helper.py ---
"""Small offline CPU correctness fixtures for the collected Wan regions."""
import argparse
import math
import os
import pathlib
import sys


def _load(source_root):
    source_root = pathlib.Path(source_root).resolve()
    package_root = source_root / "src"
    if not (package_root / "diffusers").is_dir():
        raise AssertionError(f"missing source package under {package_root}")
    sys.path.insert(0, str(package_root))
    import diffusers
    loaded = pathlib.Path(diffusers.__file__).resolve()
    if package_root not in loaded.parents:
        raise AssertionError(f"loaded diffusers from {loaded}, expected {package_root}")
    return diffusers


class DuckTokenizer:
    class Out(dict):
        input_ids = property(lambda self: self["input_ids"])
        attention_mask = property(lambda self: self["attention_mask"])

    def __init__(self, torch, vocab_size=128):
        self.torch = torch
        self.vocab_size = vocab_size

    def __call__(self, prompt, max_length=None, **kwargs):
        prompts = [prompt] if isinstance(prompt, str) else list(prompt)
        ids = self.torch.zeros(len(prompts), max_length, dtype=self.torch.long)
        mask = self.torch.zeros_like(ids)
        for row, text in enumerate(prompts):
            length = min(len(text.split()) + 1, max_length)
            ids[row, :length] = self.torch.arange(1, length + 1) % self.vocab_size
            mask[row, :length] = 1
        return self.Out(input_ids=ids, attention_mask=mask)


def _finite(torch, value):
    assert torch.isfinite(value).all().item()


def _vae(torch, diffusers):
    torch.manual_seed(7)
    return diffusers.AutoencoderKLWan(
        base_dim=8, z_dim=16, dim_mult=[1, 2, 4, 4], num_res_blocks=1,
        attn_scales=[], temperal_downsample=[False, True, True],
        scale_factor_temporal=4, scale_factor_spatial=8,
    ).eval()


def _transformer(torch, diffusers):
    torch.manual_seed(11)
    return diffusers.WanTransformer3DModel(
        patch_size=(1, 2, 2), num_attention_heads=4, attention_head_dim=8,
        in_channels=16, out_channels=16, text_dim=32, freq_dim=32,
        ffn_dim=64, num_layers=1, cross_attn_norm=True,
        qk_norm="rms_norm_across_heads", eps=1e-6, rope_max_seq_len=64,
    ).eval()


def _text(torch):
    from transformers import UMT5Config, UMT5EncoderModel
    cfg = UMT5Config(vocab_size=128, d_model=32, d_kv=8, d_ff=48,
                     num_layers=1, num_heads=4, relative_attention_num_buckets=8,
                     dropout_rate=0.0)
    torch.manual_seed(13)
    return UMT5EncoderModel(cfg).eval(), DuckTokenizer(torch, cfg.vocab_size)


def _pipeline(torch, diffusers, with_text=False):
    text_encoder, tokenizer = _text(torch) if with_text else (None, None)
    pipe = diffusers.WanPipeline(
        tokenizer=tokenizer, text_encoder=text_encoder, vae=_vae(torch, diffusers),
        transformer=_transformer(torch, diffusers),
        scheduler=diffusers.FlowMatchEulerDiscreteScheduler(shift=3.0),
    )
    pipe.set_progress_bar_config(disable=True)
    return pipe


def _run_image(torch, diffusers, number):
    processor = diffusers.VaeImageProcessor(do_resize=False)
    output_type = {1: "np", 2: "pt", 3: "np", 4: "pil"}[number]
    for batch, height, width in ((1, 6, 8), (2, 6, 8), (1, 8, 8), (1, 6, 12), (2, 10, 8), (1, 10, 12)):
        image = torch.linspace(-1, 1, batch * 3 * height * width).reshape(batch, 3, height, width)
        result = processor.postprocess(image, output_type=output_type)
        if output_type == "pt":
            assert tuple(result.shape) == (batch, 3, height, width); _finite(torch, result)
        elif output_type == "np":
            assert result.shape == (batch, height, width, 3)
            assert bool((result >= 0).all() and (result <= 1).all())
        else:
            assert len(result) == batch and result[0].size == (width, height)


def _run_vae(torch, diffusers, number):
    if number == 16:
        from diffusers.models.autoencoders.vae import DiagonalGaussianDistribution
        for batch, frames, side in ((1, 1, 2), (2, 1, 2), (1, 2, 2), (1, 1, 3), (2, 2, 3), (1, 3, 4)):
            params = torch.randn(batch, 8, frames, side, side)
            dist = DiagonalGaussianDistribution(params)
            assert tuple(dist.mode().shape) == (batch, 4, frames, side, side); _finite(torch, dist.std)
        return
    vae = _vae(torch, diffusers)
    if number in (7, 8):
        a = torch.zeros(1, 2, 2, 9, 9); b = torch.ones_like(a)
        for extent in (1, 2, 3, 4, 5, 6):
            out = vae.blend_h(a, b.clone(), extent) if number == 7 else vae.blend_v(a, b.clone(), extent)
            assert tuple(out.shape) == tuple(a.shape); _finite(torch, out)
            assert out.min().item() == 0.0 and out.max().item() == 1.0
        return
    if number == 9:
        for offset in (0, 1, 2, 3, 5, 8):
            vae._conv_idx = [offset]; vae._enc_conv_idx = [offset]
            vae.clear_cache(); assert vae._conv_idx == [0] and vae._enc_conv_idx == [0]
        return
    for frames, side in ((1, 16), (5, 16), (1, 32), (9, 16), (5, 32), (9, 48)):
        video = torch.randn(1, 3, frames, side, side)
        latent_frames = (frames - 1) // 4 + 1
        latent = torch.randn(1, 16, latent_frames, side // 8, side // 8)
        if number in (6, 11, 13, 15):
            if number == 13:
                vae.enable_tiling(tile_sample_min_height=24, tile_sample_min_width=24,
                                  tile_sample_stride_height=16, tile_sample_stride_width=16)
                value = vae.tiled_encode(video)
            else:
                value = vae.encode(video, return_dict=False)[0]
                value = value.parameters if hasattr(value, "parameters") else value
            assert value.ndim == 5 and value.shape[0] == 1; _finite(torch, value)
        else:
            if number == 12:
                vae.enable_tiling(tile_sample_min_height=24, tile_sample_min_width=24,
                                  tile_sample_stride_height=16, tile_sample_stride_width=16)
                value = vae.tiled_decode(latent, return_dict=False)[0]
            else:
                value = vae.decode(latent, return_dict=False)[0]
            assert value.ndim == 5 and value.shape[:2] == (1, 3); _finite(torch, value)


def _run_transformer(torch, diffusers, number):
    model = _transformer(torch, diffusers)
    for frames, side, text_length in ((1, 6, 4), (2, 6, 9), (1, 8, 6), (3, 6, 6), (2, 8, 4), (3, 8, 9)):
        hidden = torch.randn(1, 16, frames, side, side)
        if number == 21:
            cos, sin = model.rope(hidden)
            assert cos.shape == sin.shape and cos.shape[1] == frames * (side // 2) ** 2; _finite(torch, cos)
        else:
            text = torch.randn(1, text_length, 32)
            out = model(hidden_states=hidden, timestep=torch.tensor([1.0]),
                        encoder_hidden_states=text, return_dict=False)[0]
            assert tuple(out.shape) == tuple(hidden.shape); _finite(torch, out)


def _run_pipeline(torch, diffusers, number):
    if number in (31, 32, 33, 34, 35):
        pipe = _pipeline(torch, diffusers, with_text=True)
        for prompts, max_length in ((["red kite"], 8), (["small red kite"], 8), (["blue boat", "red kite"], 8), (["one calm lake"], 12), (["bright red kite", "blue boat"], 16), (["one calm lake at dawn"], 16)):
            negatives = ["blur" for _ in prompts]
            pe, ne = pipe.encode_prompt(prompt=prompts, negative_prompt=negatives,
                                        do_classifier_free_guidance=True,
                                        num_videos_per_prompt=1, max_sequence_length=max_length)
            assert tuple(pe.shape) == (len(prompts), max_length, 32)
            assert tuple(ne.shape) == (len(prompts), max_length, 32)
            _finite(torch, pe); _finite(torch, ne)
        return
    pipe = _pipeline(torch, diffusers)
    if number == 36:
        for batch, frames, side in ((1, 1, 16), (2, 1, 16), (1, 5, 16), (1, 1, 32), (2, 5, 32), (1, 9, 48)):
            latents = pipe.prepare_latents(batch, 16, side, side, frames, torch.float32,
                                           torch.device("cpu"), torch.Generator().manual_seed(3))
            expected = (batch, 16, (frames - 1) // pipe.vae_scale_factor_temporal + 1,
                        side // pipe.vae_scale_factor_spatial, side // pipe.vae_scale_factor_spatial)
            assert tuple(latents.shape) == expected; _finite(torch, latents)
        return
    for text_length, steps, seed in ((4, 1, 3), (8, 1, 5), (4, 2, 7), (12, 2, 11), (8, 3, 13), (12, 4, 17)):
        pe = torch.randn(1, text_length, 32); ne = torch.randn(1, text_length, 32)
        output_type = "pt" if number == 28 else "latent"
        out = pipe(prompt_embeds=pe, negative_prompt_embeds=ne, height=32, width=32,
                   num_frames=5, num_inference_steps=steps, guidance_scale=4.0,
                   generator=torch.Generator().manual_seed(seed), output_type=output_type)
        result = out.frames
        assert getattr(result, "shape", None) is not None; _finite(torch, result)


def _run_scheduler(torch, diffusers, number):
    sched = diffusers.FlowMatchEulerDiscreteScheduler(shift=3.0)
    for steps in (1, 2, 3, 4, 6, 8):
        sched.set_timesteps(steps, device="cpu")
        assert len(sched.timesteps) == steps and torch.all(sched.timesteps[:-1] >= sched.timesteps[1:])
        if number == 37:
            idx = sched.index_for_timestep(sched.timesteps[min(1, steps - 1)]); assert 0 <= idx < len(sched.timesteps)
        elif number == 39:
            sample = torch.randn(steps, 4, 3, 3); model = torch.full_like(sample, 0.25)
            out = sched.step(model, sched.timesteps[0], sample, return_dict=False)[0]
            assert tuple(out.shape) == tuple(sample.shape); _finite(torch, out)


def _run_video(torch, diffusers, number):
    processor = diffusers.VideoProcessor(do_resize=False)
    output_type = "np" if number == 41 else "pt"
    for batch, frames, side in ((1, 1, 6), (2, 1, 6), (1, 3, 6), (1, 1, 8), (2, 3, 8), (1, 5, 10)):
        video = torch.linspace(-1, 1, batch * 3 * frames * side * side).reshape(batch, 3, frames, side, side)
        out = processor.postprocess_video(video, output_type=output_type)
        expected = ((batch, frames, side, side, 3) if output_type == "np" else (batch, frames, 3, side, side))
        assert tuple(out.shape) == expected


def run(target, source_root):
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    diffusers = _load(source_root)
    import torch
    torch.set_grad_enabled(False); torch.set_num_threads(1)
    number = int(target.split("-")[-1])
    if number <= 4: _run_image(torch, diffusers, number)
    elif number <= 16: _run_vae(torch, diffusers, number)
    elif number <= 24: _run_transformer(torch, diffusers, number)
    elif number <= 36: _run_pipeline(torch, diffusers, number)
    elif number <= 39: _run_scheduler(torch, diffusers, number)
    else:
        for _ in range(3):
            _run_video(torch, diffusers, number)

--- FILE: tests/marker_probe.py ---
"""Native correctness-test marker observer; does not count instructions."""
import contextlib
import json
import os
import sys
import types
from collections import Counter


class Probe:
    def __init__(self):
        self.hits=Counter()
        self.instrumented=bool(os.environ.get('DRPERF'))
        original=None
        if self.instrumented:
            import perfmark
            original=perfmark.region
        module=types.ModuleType('perfmark')
        @contextlib.contextmanager
        def region(name, **pcvs):
            self.hits[name]+=1
            if original is None:
                yield
            else:
                with original(name, **pcvs):
                    yield
        module.region=region
        # Only instrumentation is replaced. Target functions and their
        # dependencies run normally; this is a reachability/correctness test.
        sys.modules['perfmark']=module

    def finish(self, target):
        print(json.dumps({'marker_hits':dict(self.hits),'target':target,
                          'measurement':'drperf' if self.instrumented else 'native correctness and reachability only'},sort_keys=True))
        assert self.hits[target]>0, f'test passed its value assertions but did not reach marker {target}'

--- FILE: TASK.md ---
# wan-041

Find cheap state expressions available at entry to the existing `perfmark.region` that explain its instruction count. Derived features, products, powers, comparisons, conditional expressions, and relevant runtime or library state are allowed. Preserve the marked region, program behavior, and workload.

--- FILE: case.json ---
{
  "schema_version": 1,
  "id": "wan-041",
  "title": "VideoProcessor.postprocess_video region",
  "language": "python",
  "region": {
    "symbol": "VideoProcessor.postprocess_video",
    "start_line": 112,
    "end_line": 112,
    "kind": "block"
  },
  "marker": {
    "kind": "python-context",
    "name": "wan-041",
    "pcvs": []
  },
  "status": "collected",
  "build_status": "not-built",
  "workload": {
    "description": "Exercise the named diffusers Wan method with a tiny random model on CPU. Use a bounded video or prompt-encoding call appropriate to this method; full model downloads are unnecessary.",
    "command": [
      "{python}",
      "tests/test_case.py",
      "--source-root",
      "{source_root}"
    ]
  },
  "source": {
    "repository": "https://github.com/huggingface/diffusers",
    "revision": "c5469b7ceb606edd7ba6570dcd17d38590a18db6",
    "path": "src/diffusers/video_processor.py",
    "sha256": "897d3b017dbaefdc0d85b2ceb022f261e919111f38313fa3c8691a6fa6e541bc"
  },
  "tests": {
    "files": [
      "tests/test_case.py",
      "tests/helper.py",
      "tests/marker_probe.py"
    ],
    "command": [
      "{python}",
      "tests/test_case.py",
      "--source-root",
      "{source_root}"
    ],
    "validation": {
      "status": "region-verified",
      "details": "Passed with the pinned patch applied to an isolated source copy under Python 3.11, PyTorch 2.14.0+cpu, and Diffusers runtime dependencies from the provided environment. Correctness assertions passed across three distinct bounded configurations and the native probe observed the named marker at least three times; this was not an instruction-count measurement."
    },
    "coverage_note": "The test imports diffusers from the supplied source root, checks finite outputs and shape or value semantics, and requires the named marker to be observed."
  }
}
