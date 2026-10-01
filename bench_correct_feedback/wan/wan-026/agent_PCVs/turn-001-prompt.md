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

CASE: wan-026
SANITIZED BENCHMARK:
--- FILE: src/diffusers/pipelines/wan/pipeline_wan.py ---
# Copyright 2025 The Wan Team and The HuggingFace Team. All rights reserved.
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
import html
from typing import Any, Callable

import regex as re
import torch
from transformers import AutoTokenizer, UMT5EncoderModel

from ...callbacks import MultiPipelineCallbacks, PipelineCallback
from ...loaders import WanLoraLoaderMixin
from ...models import AutoencoderKLWan, WanTransformer3DModel
from ...schedulers import FlowMatchEulerDiscreteScheduler
from ...utils import is_ftfy_available, is_torch_xla_available, logging, replace_example_docstring
from ...utils.torch_utils import randn_tensor
from ...video_processor import VideoProcessor
from ..pipeline_utils import DiffusionPipeline
from .pipeline_output import WanPipelineOutput


if is_torch_xla_available():
    import torch_xla.core.xla_model as xm

    XLA_AVAILABLE = True
else:
    XLA_AVAILABLE = False

logger = logging.get_logger(__name__)  # pylint: disable=invalid-name

if is_ftfy_available():
    import ftfy


EXAMPLE_DOC_STRING = """
    Examples:
        ```python
        >>> import torch
        >>> from diffusers.utils import export_to_video
        >>> from diffusers import AutoencoderKLWan, WanPipeline
        >>> from diffusers.schedulers.scheduling_unipc_multistep import UniPCMultistepScheduler

        >>> # Available models: Wan-AI/Wan2.1-T2V-14B-Diffusers, Wan-AI/Wan2.1-T2V-1.3B-Diffusers
        >>> model_id = "Wan-AI/Wan2.1-T2V-14B-Diffusers"
        >>> vae = AutoencoderKLWan.from_pretrained(model_id, subfolder="vae", torch_dtype=torch.float32)
        >>> pipe = WanPipeline.from_pretrained(model_id, vae=vae, torch_dtype=torch.bfloat16)
        >>> flow_shift = 5.0  # 5.0 for 720P, 3.0 for 480P
        >>> pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config, flow_shift=flow_shift)
        >>> pipe.to("cuda")

        >>> prompt = "A cat and a dog baking a cake together in a kitchen. The cat is carefully measuring flour, while the dog is stirring the batter with a wooden spoon. The kitchen is cozy, with sunlight streaming through the window."
        >>> negative_prompt = "Bright tones, overexposed, static, blurred details, subtitles, style, works, paintings, images, static, overall gray, worst quality, low quality, JPEG compression residue, ugly, incomplete, extra fingers, poorly drawn hands, poorly drawn faces, deformed, disfigured, misshapen limbs, fused fingers, still picture, messy background, three legs, many people in the background, walking backwards"

        >>> output = pipe(
        ...     prompt=prompt,
        ...     negative_prompt=negative_prompt,
        ...     height=720,
        ...     width=1280,
        ...     num_frames=81,
        ...     guidance_scale=5.0,
        ... ).frames[0]
        >>> export_to_video(output, "output.mp4", fps=16)
        ```
"""


def basic_clean(text):
    if is_ftfy_available():
        text = ftfy.fix_text(text)
    text = html.unescape(html.unescape(text))
    return text.strip()


def whitespace_clean(text):
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    return text


def prompt_clean(text):
    text = whitespace_clean(basic_clean(text))
    return text


class WanPipeline(DiffusionPipeline, WanLoraLoaderMixin):
    r"""
    Pipeline for text-to-video generation using Wan.

    This model inherits from [`DiffusionPipeline`]. Check the superclass documentation for the generic methods
    implemented for all pipelines (downloading, saving, running on a particular device, etc.).

    Args:
        tokenizer ([`T5Tokenizer`]):
            Tokenizer from [T5](https://huggingface.co/docs/transformers/en/model_doc/t5#transformers.T5Tokenizer),
            specifically the [google/umt5-xxl](https://huggingface.co/google/umt5-xxl) variant.
        text_encoder ([`T5EncoderModel`]):
            [T5](https://huggingface.co/docs/transformers/en/model_doc/t5#transformers.T5EncoderModel), specifically
            the [google/umt5-xxl](https://huggingface.co/google/umt5-xxl) variant.
        transformer ([`WanTransformer3DModel`]):
            Conditional Transformer to denoise the input latents.
        scheduler ([`UniPCMultistepScheduler`]):
            A scheduler to be used in combination with `transformer` to denoise the encoded image latents.
        vae ([`AutoencoderKLWan`]):
            Variational Auto-Encoder (VAE) Model to encode and decode videos to and from latent representations.
        transformer_2 ([`WanTransformer3DModel`], *optional*):
            Conditional Transformer to denoise the input latents during the low-noise stage. If provided, enables
            two-stage denoising where `transformer` handles high-noise stages and `transformer_2` handles low-noise
            stages. If not provided, only `transformer` is used.
        boundary_ratio (`float`, *optional*, defaults to `None`):
            Ratio of total timesteps to use as the boundary for switching between transformers in two-stage denoising.
            The actual boundary timestep is calculated as `boundary_ratio * num_train_timesteps`. When provided,
            `transformer` handles timesteps >= boundary_timestep and `transformer_2` handles timesteps <
            boundary_timestep. If `None`, only `transformer` is used for the entire denoising process.
    """

    model_cpu_offload_seq = "text_encoder->transformer->transformer_2->vae"
    _callback_tensor_inputs = ["latents", "prompt_embeds", "negative_prompt_embeds"]
    _optional_components = ["transformer", "transformer_2"]

    def __init__(
        self,
        tokenizer: AutoTokenizer,
        text_encoder: UMT5EncoderModel,
        vae: AutoencoderKLWan,
        scheduler: FlowMatchEulerDiscreteScheduler,
        transformer: WanTransformer3DModel | None = None,
        transformer_2: WanTransformer3DModel | None = None,
        boundary_ratio: float | None = None,
        expand_timesteps: bool = False,  # Wan2.2 ti2v
    ):
        super().__init__()

        self.register_modules(
            vae=vae,
            text_encoder=text_encoder,
            tokenizer=tokenizer,
            transformer=transformer,
            scheduler=scheduler,
            transformer_2=transformer_2,
        )
        self.register_to_config(boundary_ratio=boundary_ratio)
        self.register_to_config(expand_timesteps=expand_timesteps)
        self.vae_scale_factor_temporal = self.vae.config.scale_factor_temporal if getattr(self, "vae", None) else 4
        self.vae_scale_factor_spatial = self.vae.config.scale_factor_spatial if getattr(self, "vae", None) else 8
        self.video_processor = VideoProcessor(vae_scale_factor=self.vae_scale_factor_spatial)

    def _get_t5_prompt_embeds(
        self,
        prompt: str | list[str] = None,
        num_videos_per_prompt: int = 1,
        max_sequence_length: int = 226,
        device: torch.device | None = None,
        dtype: torch.dtype | None = None,
    ):
        device = device or self._execution_device
        dtype = dtype or self.text_encoder.dtype

        prompt = [prompt] if isinstance(prompt, str) else prompt
        prompt = [prompt_clean(u) for u in prompt]
        batch_size = len(prompt)

        text_inputs = self.tokenizer(
            prompt,
            padding="max_length",
            max_length=max_sequence_length,
            truncation=True,
            add_special_tokens=True,
            return_attention_mask=True,
            return_tensors="pt",
        )
        text_input_ids, mask = text_inputs.input_ids, text_inputs.attention_mask
        seq_lens = mask.gt(0).sum(dim=1).long()

        prompt_embeds = self.text_encoder(text_input_ids.to(device), mask.to(device)).last_hidden_state
        prompt_embeds = prompt_embeds.to(dtype=dtype, device=device)
        prompt_embeds = [u[:v] for u, v in zip(prompt_embeds, seq_lens)]
        prompt_embeds = torch.stack(
            [torch.cat([u, u.new_zeros(max_sequence_length - u.size(0), u.size(1))]) for u in prompt_embeds], dim=0
        )

        # duplicate text embeddings for each generation per prompt, using mps friendly method
        _, seq_len, _ = prompt_embeds.shape
        prompt_embeds = prompt_embeds.repeat(1, num_videos_per_prompt, 1)
        prompt_embeds = prompt_embeds.view(batch_size * num_videos_per_prompt, seq_len, -1)

        return prompt_embeds

    def encode_prompt(
        self,
        prompt: str | list[str],
        negative_prompt: str | list[str] | None = None,
        do_classifier_free_guidance: bool = True,
        num_videos_per_prompt: int = 1,
        prompt_embeds: torch.Tensor | None = None,
        negative_prompt_embeds: torch.Tensor | None = None,
        max_sequence_length: int = 226,
        device: torch.device | None = None,
        dtype: torch.dtype | None = None,
    ):
        r"""
        Encodes the prompt into text encoder hidden states.

        Args:
            prompt (`str` or `list[str]`, *optional*):
                prompt to be encoded
            negative_prompt (`str` or `list[str]`, *optional*):
                The prompt or prompts not to guide the image generation. If not defined, one has to pass
                `negative_prompt_embeds` instead. Ignored when not using guidance (i.e., ignored if `guidance_scale` is
                less than `1`).
            do_classifier_free_guidance (`bool`, *optional*, defaults to `True`):
                Whether to use classifier free guidance or not.
            num_videos_per_prompt (`int`, *optional*, defaults to 1):
                Number of videos that should be generated per prompt. torch device to place the resulting embeddings on
            prompt_embeds (`torch.Tensor`, *optional*):
                Pre-generated text embeddings. Can be used to easily tweak text inputs, *e.g.* prompt weighting. If not
                provided, text embeddings will be generated from `prompt` input argument.
            negative_prompt_embeds (`torch.Tensor`, *optional*):
                Pre-generated negative text embeddings. Can be used to easily tweak text inputs, *e.g.* prompt
                weighting. If not provided, negative_prompt_embeds will be generated from `negative_prompt` input
                argument.
            device: (`torch.device`, *optional*):
                torch device
            dtype: (`torch.dtype`, *optional*):
                torch dtype
        """
        device = device or self._execution_device

        prompt = [prompt] if isinstance(prompt, str) else prompt
        if prompt is not None:
            batch_size = len(prompt)
        else:
            batch_size = prompt_embeds.shape[0]

        if prompt_embeds is None:
            prompt_embeds = self._get_t5_prompt_embeds(
                prompt=prompt,
                num_videos_per_prompt=num_videos_per_prompt,
                max_sequence_length=max_sequence_length,
                device=device,
                dtype=dtype,
            )

        if do_classifier_free_guidance and negative_prompt_embeds is None:
            negative_prompt = negative_prompt or ""
            negative_prompt = batch_size * [negative_prompt] if isinstance(negative_prompt, str) else negative_prompt

            if prompt is not None and type(prompt) is not type(negative_prompt):
                raise TypeError(
                    f"`negative_prompt` should be the same type to `prompt`, but got {type(negative_prompt)} !="
                    f" {type(prompt)}."
                )
            elif batch_size != len(negative_prompt):
                raise ValueError(
                    f"`negative_prompt`: {negative_prompt} has batch size {len(negative_prompt)}, but `prompt`:"
                    f" {prompt} has batch size {batch_size}. Please make sure that passed `negative_prompt` matches"
                    " the batch size of `prompt`."
                )

            negative_prompt_embeds = self._get_t5_prompt_embeds(
                prompt=negative_prompt,
                num_videos_per_prompt=num_videos_per_prompt,
                max_sequence_length=max_sequence_length,
                device=device,
                dtype=dtype,
            )

        return prompt_embeds, negative_prompt_embeds

    def check_inputs(
        self,
        prompt,
        negative_prompt,
        height,
        width,
        prompt_embeds=None,
        negative_prompt_embeds=None,
        callback_on_step_end_tensor_inputs=None,
        guidance_scale_2=None,
    ):
        if height % 16 != 0 or width % 16 != 0:
            raise ValueError(f"`height` and `width` have to be divisible by 16 but are {height} and {width}.")

        if callback_on_step_end_tensor_inputs is not None and not all(
            k in self._callback_tensor_inputs for k in callback_on_step_end_tensor_inputs
        ):
            raise ValueError(
                f"`callback_on_step_end_tensor_inputs` has to be in {self._callback_tensor_inputs}, but found {[k for k in callback_on_step_end_tensor_inputs if k not in self._callback_tensor_inputs]}"
            )

        if prompt is not None and prompt_embeds is not None:
            raise ValueError(
                f"Cannot forward both `prompt`: {prompt} and `prompt_embeds`: {prompt_embeds}. Please make sure to"
                " only forward one of the two."
            )
        elif negative_prompt is not None and negative_prompt_embeds is not None:
            raise ValueError(
                f"Cannot forward both `negative_prompt`: {negative_prompt} and `negative_prompt_embeds`: {negative_prompt_embeds}. Please make sure to"
                " only forward one of the two."
            )
        elif prompt is None and prompt_embeds is None:
            raise ValueError(
                "Provide either `prompt` or `prompt_embeds`. Cannot leave both `prompt` and `prompt_embeds` undefined."
            )
        elif prompt is not None and (not isinstance(prompt, str) and not isinstance(prompt, list)):
            raise ValueError(f"`prompt` has to be of type `str` or `list` but is {type(prompt)}")
        elif negative_prompt is not None and (
            not isinstance(negative_prompt, str) and not isinstance(negative_prompt, list)
        ):
            raise ValueError(f"`negative_prompt` has to be of type `str` or `list` but is {type(negative_prompt)}")

        if self.config.boundary_ratio is None and guidance_scale_2 is not None:
            raise ValueError("`guidance_scale_2` is only supported when the pipeline's `boundary_ratio` is not None.")

    def prepare_latents(
        self,
        batch_size: int,
        num_channels_latents: int = 16,
        height: int = 480,
        width: int = 832,
        num_frames: int = 81,
        dtype: torch.dtype | None = None,
        device: torch.device | None = None,
        generator: torch.Generator | list[torch.Generator] | None = None,
        latents: torch.Tensor | None = None,
    ) -> torch.Tensor:
        if latents is not None:
            return latents.to(device=device, dtype=dtype)

        num_latent_frames = (num_frames - 1) // self.vae_scale_factor_temporal + 1
        shape = (
            batch_size,
            num_channels_latents,
            num_latent_frames,
            int(height) // self.vae_scale_factor_spatial,
            int(width) // self.vae_scale_factor_spatial,
        )
        if isinstance(generator, list) and len(generator) != batch_size:
            raise ValueError(
                f"You have passed a list of generators of length {len(generator)}, but requested an effective batch"
                f" size of {batch_size}. Make sure the batch size matches the length of the generators."
            )

        latents = randn_tensor(shape, generator=generator, device=device, dtype=dtype)
        return latents

    @property
    def guidance_scale(self):
        return self._guidance_scale

    @property
    def do_classifier_free_guidance(self):
        return self._guidance_scale > 1.0

    @property
    def num_timesteps(self):
        return self._num_timesteps

    @property
    def current_timestep(self):
        return self._current_timestep

    @property
    def interrupt(self):
        return self._interrupt

    @property
    def attention_kwargs(self):
        return self._attention_kwargs

    @torch.no_grad()
    @replace_example_docstring(EXAMPLE_DOC_STRING)
    def __call__(
        self,
        prompt: str | list[str] = None,
        negative_prompt: str | list[str] = None,
        height: int = 480,
        width: int = 832,
        num_frames: int = 81,
        num_inference_steps: int = 50,
        guidance_scale: float = 5.0,
        guidance_scale_2: float | None = None,
        num_videos_per_prompt: int | None = 1,
        generator: torch.Generator | list[torch.Generator] | None = None,
        latents: torch.Tensor | None = None,
        prompt_embeds: torch.Tensor | None = None,
        negative_prompt_embeds: torch.Tensor | None = None,
        output_type: str | None = "np",
        return_dict: bool = True,
        attention_kwargs: dict[str, Any] | None = None,
        callback_on_step_end: Callable[[int, int], None] | PipelineCallback | MultiPipelineCallbacks | None = None,
        callback_on_step_end_tensor_inputs: list[str] = ["latents"],
        max_sequence_length: int = 512,
    ):
        r"""
        The call function to the pipeline for generation.

        Args:
            prompt (`str` or `list[str]`, *optional*):
                The prompt or prompts to guide the image generation. If not defined, pass `prompt_embeds` instead.
            negative_prompt (`str` or `list[str]`, *optional*):
                The prompt or prompts to avoid during image generation. If not defined, pass `negative_prompt_embeds`
                instead. Ignored when not using guidance (`guidance_scale` < `1`).
            height (`int`, defaults to `480`):
                The height in pixels of the generated image.
            width (`int`, defaults to `832`):
                The width in pixels of the generated image.
            num_frames (`int`, defaults to `81`):
                The number of frames in the generated video.
            num_inference_steps (`int`, defaults to `50`):
                The number of denoising steps. More denoising steps usually lead to a higher quality image at the
                expense of slower inference.
            guidance_scale (`float`, defaults to `5.0`):
                Guidance scale as defined in [Classifier-Free Diffusion
                Guidance](https://huggingface.co/papers/2207.12598). `guidance_scale` is defined as `w` of equation 2.
                of [Imagen Paper](https://huggingface.co/papers/2205.11487). Guidance scale is enabled by setting
                `guidance_scale > 1`. Higher guidance scale encourages to generate images that are closely linked to
                the text `prompt`, usually at the expense of lower image quality.
            guidance_scale_2 (`float`, *optional*, defaults to `None`):
                Guidance scale for the low-noise stage transformer (`transformer_2`). If `None` and the pipeline's
                `boundary_ratio` is not None, uses the same value as `guidance_scale`. Only used when `transformer_2`
                and the pipeline's `boundary_ratio` are not None.
            num_videos_per_prompt (`int`, *optional*, defaults to 1):
                The number of images to generate per prompt.
            generator (`torch.Generator` or `list[torch.Generator]`, *optional*):
                A [`torch.Generator`](https://pytorch.org/docs/stable/generated/torch.Generator.html) to make
                generation deterministic.
            latents (`torch.Tensor`, *optional*):
                Pre-generated noisy latents sampled from a Gaussian distribution, to be used as inputs for image
                generation. Can be used to tweak the same generation with different prompts. If not provided, a latents
                tensor is generated by sampling using the supplied random `generator`.
            prompt_embeds (`torch.Tensor`, *optional*):
                Pre-generated text embeddings. Can be used to easily tweak text inputs (prompt weighting). If not
                provided, text embeddings are generated from the `prompt` input argument.
            negative_prompt_embeds (`torch.Tensor`, *optional*):
                Pre-generated negative text embeddings. Can be used to easily tweak text inputs (prompt weighting). If
                not provided, `negative_prompt_embeds` are generated from the `negative_prompt` input argument.
            output_type (`str`, *optional*, defaults to `"np"`):
                The output format of the generated image. Choose between `PIL.Image` or `np.array`.
            return_dict (`bool`, *optional*, defaults to `True`):
                Whether or not to return a [`WanPipelineOutput`] instead of a plain tuple.
            attention_kwargs (`dict`, *optional*):
                A kwargs dictionary that if specified is passed along to the `AttentionProcessor` as defined under
                `self.processor` in
                [diffusers.models.attention_processor](https://github.com/huggingface/diffusers/blob/main/src/diffusers/models/attention_processor.py).
            callback_on_step_end (`Callable`, `PipelineCallback`, `MultiPipelineCallbacks`, *optional*):
                A function or a subclass of `PipelineCallback` or `MultiPipelineCallbacks` that is called at the end of
                each denoising step during the inference. with the following arguments: `callback_on_step_end(self:
                DiffusionPipeline, step: int, timestep: int, callback_kwargs: Dict)`. `callback_kwargs` will include a
                list of all tensors as specified by `callback_on_step_end_tensor_inputs`.
            callback_on_step_end_tensor_inputs (`list`, *optional*):
                The list of tensor inputs for the `callback_on_step_end` function. The tensors specified in the list
                will be passed as `callback_kwargs` argument. You will only be able to include variables listed in the
                `._callback_tensor_inputs` attribute of your pipeline class.
            max_sequence_length (`int`, defaults to `512`):
                The maximum sequence length of the text encoder. If the prompt is longer than this, it will be
                truncated. If the prompt is shorter, it will be padded to this length.

        Examples:

        Returns:
            [`~WanPipelineOutput`] or `tuple`:
                If `return_dict` is `True`, [`WanPipelineOutput`] is returned, otherwise a `tuple` is returned where
                the first element is a list with the generated images and the second element is a list of `bool`s
                indicating whether the corresponding generated image contains "not-safe-for-work" (nsfw) content.
        """

        if isinstance(callback_on_step_end, (PipelineCallback, MultiPipelineCallbacks)):
            callback_on_step_end_tensor_inputs = callback_on_step_end.tensor_inputs

        # 1. Check inputs. Raise error if not correct
        self.check_inputs(
            prompt,
            negative_prompt,
            height,
            width,
            prompt_embeds,
            negative_prompt_embeds,
            callback_on_step_end_tensor_inputs,
            guidance_scale_2,
        )

        if num_frames % self.vae_scale_factor_temporal != 1:
            logger.warning(
                f"`num_frames - 1` has to be divisible by {self.vae_scale_factor_temporal}. Rounding to the nearest number."
            )
            num_frames = num_frames // self.vae_scale_factor_temporal * self.vae_scale_factor_temporal + 1
        num_frames = max(num_frames, 1)

        patch_size = (
            self.transformer.config.patch_size
            if self.transformer is not None
            else self.transformer_2.config.patch_size
        )
        h_multiple_of = self.vae_scale_factor_spatial * patch_size[1]
        w_multiple_of = self.vae_scale_factor_spatial * patch_size[2]
        calc_height = height // h_multiple_of * h_multiple_of
        calc_width = width // w_multiple_of * w_multiple_of
        if height != calc_height or width != calc_width:
            logger.warning(
                f"`height` and `width` must be multiples of ({h_multiple_of}, {w_multiple_of}) for proper patchification. "
                f"Adjusting ({height}, {width}) -> ({calc_height}, {calc_width})."
            )
            height, width = calc_height, calc_width

        if self.config.boundary_ratio is not None and guidance_scale_2 is None:
            guidance_scale_2 = guidance_scale

        self._guidance_scale = guidance_scale
        self._guidance_scale_2 = guidance_scale_2
        self._attention_kwargs = attention_kwargs
        self._current_timestep = None
        self._interrupt = False

        device = self._execution_device

        # 2. Define call parameters
        if prompt is not None and isinstance(prompt, str):
            batch_size = 1
        elif prompt is not None and isinstance(prompt, list):
            batch_size = len(prompt)
        else:
            batch_size = prompt_embeds.shape[0]

        # 3. Encode input prompt
        prompt_embeds, negative_prompt_embeds = self.encode_prompt(
            prompt=prompt,
            negative_prompt=negative_prompt,
            do_classifier_free_guidance=self.do_classifier_free_guidance,
            num_videos_per_prompt=num_videos_per_prompt,
            prompt_embeds=prompt_embeds,
            negative_prompt_embeds=negative_prompt_embeds,
            max_sequence_length=max_sequence_length,
            device=device,
        )

        transformer_dtype = self.transformer.dtype if self.transformer is not None else self.transformer_2.dtype
        prompt_embeds = prompt_embeds.to(transformer_dtype)
        if negative_prompt_embeds is not None:
            negative_prompt_embeds = negative_prompt_embeds.to(transformer_dtype)

        # 4. Prepare timesteps
        self.scheduler.set_timesteps(num_inference_steps, device=device)
        timesteps = self.scheduler.timesteps

        # 5. Prepare latent variables
        num_channels_latents = (
            self.transformer.config.in_channels
            if self.transformer is not None
            else self.transformer_2.config.in_channels
        )
        latents = self.prepare_latents(
            batch_size * num_videos_per_prompt,
            num_channels_latents,
            height,
            width,
            num_frames,
            torch.float32,
            device,
            generator,
            latents,
        )

        mask = torch.ones(latents.shape, dtype=torch.float32, device=device)

        # 6. Denoising loop
        num_warmup_steps = len(timesteps) - num_inference_steps * self.scheduler.order
        self._num_timesteps = len(timesteps)

        # We set the index here to remove DtoH sync, helpful especially during compilation.
        # Check out more details here: https://github.com/huggingface/diffusers/pull/11696
        self.scheduler.set_begin_index(0)

        if self.config.boundary_ratio is not None:
            boundary_timestep = self.config.boundary_ratio * self.scheduler.config.num_train_timesteps
        else:
            boundary_timestep = None

        with self.progress_bar(total=num_inference_steps) as progress_bar:
            for i, t in enumerate(timesteps):
                with perfmark.region("wan-026"):
                    if self.interrupt:
                        continue

                    self._current_timestep = t

                    if boundary_timestep is None or t >= boundary_timestep:
                        # wan2.1 or high-noise stage in wan2.2
                        current_model = self.transformer
                        current_guidance_scale = guidance_scale
                    else:
                        # low-noise stage in wan2.2
                        current_model = self.transformer_2
                        current_guidance_scale = guidance_scale_2

                    latent_model_input = latents.to(transformer_dtype)
                    if self.config.expand_timesteps:
                        # seq_len: num_latent_frames * latent_height//2 * latent_width//2
                        temp_ts = (mask[0][0][:, ::2, ::2] * t).flatten()
                        # batch_size, seq_len
                        timestep = temp_ts.unsqueeze(0).expand(latents.shape[0], -1)
                    else:
                        timestep = t.expand(latents.shape[0])

                    with current_model.cache_context("cond"):
                        noise_pred = current_model(
                            hidden_states=latent_model_input,
                            timestep=timestep,
                            encoder_hidden_states=prompt_embeds,
                            attention_kwargs=attention_kwargs,
                            return_dict=False,
                        )[0]

                    if self.do_classifier_free_guidance:
                        with current_model.cache_context("uncond"):
                            noise_uncond = current_model(
                                hidden_states=latent_model_input,
                                timestep=timestep,
                                encoder_hidden_states=negative_prompt_embeds,
                                attention_kwargs=attention_kwargs,
                                return_dict=False,
                            )[0]
                        noise_pred = noise_uncond + current_guidance_scale * (noise_pred - noise_uncond)

                    # compute the previous noisy sample x_t -> x_t-1
                    latents = self.scheduler.step(noise_pred, t, latents, return_dict=False)[0]

                    if callback_on_step_end is not None:
                        callback_kwargs = {}
                        for k in callback_on_step_end_tensor_inputs:
                            callback_kwargs[k] = locals()[k]
                        callback_outputs = callback_on_step_end(self, i, t, callback_kwargs)

                        latents = callback_outputs.pop("latents", latents)
                        prompt_embeds = callback_outputs.pop("prompt_embeds", prompt_embeds)
                        negative_prompt_embeds = callback_outputs.pop("negative_prompt_embeds", negative_prompt_embeds)

                    # call the callback, if provided
                    if i == len(timesteps) - 1 or ((i + 1) > num_warmup_steps and (i + 1) % self.scheduler.order == 0):
                        progress_bar.update()

                    if XLA_AVAILABLE:
                        xm.mark_step()

        self._current_timestep = None

        if not output_type == "latent":
            latents = latents.to(self.vae.dtype)
            latents_mean = (
                torch.tensor(self.vae.config.latents_mean)
                .view(1, self.vae.config.z_dim, 1, 1, 1)
                .to(latents.device, latents.dtype)
            )
            latents_std = 1.0 / torch.tensor(self.vae.config.latents_std).view(1, self.vae.config.z_dim, 1, 1, 1).to(
                latents.device, latents.dtype
            )
            latents = latents / latents_std + latents_mean
            video = self.vae.decode(latents, return_dict=False)[0]
            video = self.video_processor.postprocess_video(video, output_type=output_type)
        else:
            video = latents

        # Offload all models
        self.maybe_free_model_hooks()

        if not return_dict:
            return (video,)

        return WanPipelineOutput(frames=video)

--- FILE: tests/test_case.py ---
"""Correctness and marker-reachability test for wan-026."""
import argparse
from marker_probe import Probe

parser = argparse.ArgumentParser()
parser.add_argument("--source-root", required=True)
args = parser.parse_args()
probe = Probe()
from helper import run
run("wan-026", args.source_root)
probe.finish("wan-026")

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
    elif number <= 36:
        for _ in range(3):
            _run_pipeline(torch, diffusers, number)
    elif number <= 39: _run_scheduler(torch, diffusers, number)
    else: _run_video(torch, diffusers, number)

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
# wan-026

Find cheap state expressions available at entry to the existing `perfmark.region` that explain its instruction count. Derived features, products, powers, comparisons, conditional expressions, and relevant runtime or library state are allowed. Preserve the marked region, program behavior, and workload.

--- FILE: case.json ---
{
  "schema_version": 1,
  "id": "wan-026",
  "title": "WanPipeline.__call__ region",
  "language": "python",
  "region": {
    "symbol": "WanPipeline.__call__",
    "start_line": 591,
    "end_line": 652,
    "kind": "block"
  },
  "marker": {
    "kind": "python-context",
    "name": "wan-026",
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
    "path": "src/diffusers/pipelines/wan/pipeline_wan.py",
    "sha256": "2a5fcd905ad0fbcbd76240e02007e73ab3583f927da8b9fe0fbe5a4a54d792aa"
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
