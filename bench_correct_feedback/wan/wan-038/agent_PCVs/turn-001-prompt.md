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

CASE: wan-038
SANITIZED BENCHMARK:
--- FILE: src/diffusers/schedulers/scheduling_flow_match_euler_discrete.py ---
# Copyright 2025 Stability AI, Katherine Crowson and The HuggingFace Team. All rights reserved.
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
import math
from dataclasses import dataclass
from typing import Literal, Optional, Union

import numpy as np
import torch

from ..configuration_utils import ConfigMixin, register_to_config
from ..utils import BaseOutput, is_scipy_available, logging
from ..utils.torch_utils import randn_tensor
from .scheduling_utils import SchedulerMixin


if is_scipy_available():
    import scipy.stats

logger = logging.get_logger(__name__)  # pylint: disable=invalid-name


@dataclass
class FlowMatchEulerDiscreteSchedulerOutput(BaseOutput):
    """
    Output class for the scheduler's `step` function output.

    Args:
        prev_sample (`torch.FloatTensor` of shape `(batch_size, num_channels, height, width)` for images):
            Computed sample `(x_{t-1})` of previous timestep. `prev_sample` should be used as next model input in the
            denoising loop.
    """

    prev_sample: torch.FloatTensor


class FlowMatchEulerDiscreteScheduler(SchedulerMixin, ConfigMixin):
    """
    Euler scheduler.

    This model inherits from [`SchedulerMixin`] and [`ConfigMixin`]. Check the superclass documentation for the generic
    methods the library implements for all schedulers such as loading and saving.

    Args:
        num_train_timesteps (`int`, defaults to 1000):
            The number of diffusion steps to train the model.
        shift (`float`, defaults to 1.0):
            The shift value for the timestep schedule.
        use_dynamic_shifting (`bool`, defaults to False):
            Whether to apply timestep shifting on-the-fly based on the image resolution.
        base_shift (`float`, defaults to 0.5):
            Value to stabilize image generation. Increasing `base_shift` reduces variation and image is more consistent
            with desired output.
        max_shift (`float`, defaults to 1.15):
            Value change allowed to latent vectors. Increasing `max_shift` encourages more variation and image may be
            more exaggerated or stylized.
        base_image_seq_len (`int`, defaults to 256):
            The base image sequence length.
        max_image_seq_len (`int`, defaults to 4096):
            The maximum image sequence length.
        invert_sigmas (`bool`, defaults to False):
            Whether to invert the sigmas.
        shift_terminal (`float`, defaults to None):
            The end value of the shifted timestep schedule.
        use_karras_sigmas (`bool`, defaults to False):
            Whether to use Karras sigmas for step sizes in the noise schedule during sampling.
        use_exponential_sigmas (`bool`, defaults to False):
            Whether to use exponential sigmas for step sizes in the noise schedule during sampling.
        use_beta_sigmas (`bool`, defaults to False):
            Whether to use beta sigmas for step sizes in the noise schedule during sampling.
        time_shift_type (`str`, defaults to "exponential"):
            The type of dynamic resolution-dependent timestep shifting to apply. Either "exponential" or "linear".
        stochastic_sampling (`bool`, defaults to False):
            Whether to use stochastic sampling.
    """

    _compatibles = []
    order = 1

    @register_to_config
    def __init__(
        self,
        num_train_timesteps: int = 1000,
        shift: float = 1.0,
        use_dynamic_shifting: bool = False,
        base_shift: float | None = 0.5,
        max_shift: float | None = 1.15,
        base_image_seq_len: int = 256,
        max_image_seq_len: int = 4096,
        invert_sigmas: bool = False,
        shift_terminal: float = None,
        use_karras_sigmas: bool = False,
        use_exponential_sigmas: bool = False,
        use_beta_sigmas: bool = False,
        time_shift_type: Literal["exponential", "linear"] = "exponential",
        stochastic_sampling: bool = False,
    ):
        if self.config.use_beta_sigmas and not is_scipy_available():
            raise ImportError("Make sure to install scipy if you want to use beta sigmas.")
        if (
            sum(
                [
                    self.config.use_beta_sigmas,
                    self.config.use_exponential_sigmas,
                    self.config.use_karras_sigmas,
                ]
            )
            > 1
        ):
            raise ValueError(
                "Only one of `config.use_beta_sigmas`, `config.use_exponential_sigmas`, `config.use_karras_sigmas` can be used."
            )
        if time_shift_type not in {"exponential", "linear"}:
            raise ValueError("`time_shift_type` must either be 'exponential' or 'linear'.")

        timesteps = np.linspace(1, num_train_timesteps, num_train_timesteps, dtype=np.float32)[::-1].copy()
        timesteps = torch.from_numpy(timesteps).to(dtype=torch.float32)

        sigmas = timesteps / num_train_timesteps
        if not use_dynamic_shifting:
            # when use_dynamic_shifting is True, we apply the timestep shifting on the fly based on the image resolution
            sigmas = shift * sigmas / (1 + (shift - 1) * sigmas)

        self.timesteps = sigmas * num_train_timesteps

        self._step_index = None
        self._begin_index = None

        self._shift = shift

        self.sigmas = sigmas.to("cpu")  # to avoid too much CPU/GPU communication
        self.sigma_min = self.sigmas[-1].item()
        self.sigma_max = self.sigmas[0].item()

    @property
    def shift(self):
        """
        The value used for shifting.
        """
        return self._shift

    @property
    def step_index(self):
        """
        The index counter for current timestep. It will increase 1 after each scheduler step.
        """
        return self._step_index

    @property
    def begin_index(self):
        """
        The index for the first timestep. It should be set from pipeline with `set_begin_index` method.
        """
        return self._begin_index

    # Copied from diffusers.schedulers.scheduling_dpmsolver_multistep.DPMSolverMultistepScheduler.set_begin_index
    def set_begin_index(self, begin_index: int = 0):
        """
        Sets the begin index for the scheduler. This function should be run from pipeline before the inference.

        Args:
            begin_index (`int`, defaults to `0`):
                The begin index for the scheduler.
        """
        self._begin_index = begin_index

    def set_shift(self, shift: float):
        """
        Sets the shift value for the scheduler.

        Args:
            shift (`float`):
                The shift value to be set.
        """
        self._shift = shift

    def scale_noise(
        self,
        sample: torch.FloatTensor,
        timestep: float | torch.FloatTensor,
        noise: torch.FloatTensor | None = None,
    ) -> torch.FloatTensor:
        """
        Forward process in flow-matching

        Args:
            sample (`torch.FloatTensor`):
                The input sample.
            timestep (`torch.FloatTensor`):
                The current timestep in the diffusion chain.
            noise (`torch.FloatTensor`):
                The noise tensor.

        Returns:
            `torch.FloatTensor`:
                A scaled input sample.
        """
        # Make sure sigmas and timesteps have the same device and dtype as original_samples
        sigmas = self.sigmas.to(device=sample.device, dtype=sample.dtype)

        if sample.device.type == "mps" and torch.is_floating_point(timestep):
            # mps does not support float64
            schedule_timesteps = self.timesteps.to(sample.device, dtype=torch.float32)
            timestep = timestep.to(sample.device, dtype=torch.float32)
        else:
            schedule_timesteps = self.timesteps.to(sample.device)
            timestep = timestep.to(sample.device)

        # self.begin_index is None when scheduler is used for training, or pipeline does not implement set_begin_index
        if self.begin_index is None:
            step_indices = [self.index_for_timestep(t, schedule_timesteps) for t in timestep]
        elif self.step_index is not None:
            # add_noise is called after first denoising step (for inpainting)
            step_indices = [self.step_index] * timestep.shape[0]
        else:
            # add noise is called before first denoising step to create initial latent(img2img)
            step_indices = [self.begin_index] * timestep.shape[0]

        sigma = sigmas[step_indices].flatten()
        while len(sigma.shape) < len(sample.shape):
            sigma = sigma.unsqueeze(-1)

        sample = sigma * noise + (1.0 - sigma) * sample

        return sample

    def _sigma_to_t(self, sigma) -> float:
        return sigma * self.config.num_train_timesteps

    def time_shift(self, mu: float, sigma: float, t: torch.Tensor) -> torch.Tensor:
        """
        Apply time shifting to the sigmas.

        Args:
            mu (`float`):
                The mu parameter for the time shift.
            sigma (`float`):
                The sigma parameter for the time shift.
            t (`torch.Tensor`):
                The input timesteps.

        Returns:
            `torch.Tensor`:
                The time-shifted timesteps.
        """
        if self.config.time_shift_type == "exponential":
            return self._time_shift_exponential(mu, sigma, t)
        elif self.config.time_shift_type == "linear":
            return self._time_shift_linear(mu, sigma, t)

    def stretch_shift_to_terminal(self, t: torch.Tensor) -> torch.Tensor:
        r"""
        Stretches and shifts the timestep schedule to ensure it terminates at the configured `shift_terminal` config
        value.

        Reference:
        https://github.com/Lightricks/LTX-Video/blob/a01a171f8fe3d99dce2728d60a73fecf4d4238ae/ltx_video/schedulers/rf.py#L51

        Args:
            t (`torch.Tensor`):
                A tensor of timesteps to be stretched and shifted.

        Returns:
            `torch.Tensor`:
                A tensor of adjusted timesteps such that the final value equals `self.config.shift_terminal`.
        """
        one_minus_z = 1 - t
        scale_factor = one_minus_z[-1] / (1 - self.config.shift_terminal)
        stretched_t = 1 - (one_minus_z / scale_factor)
        return stretched_t

    def set_timesteps(
        self,
        num_inference_steps: int | None = None,
        device: str | torch.device = None,
        sigmas: list[float] | None = None,
        mu: float | None = None,
        timesteps: list[float] | None = None,
    ):
        """
        Sets the discrete timesteps used for the diffusion chain (to be run before inference).

        Args:
            num_inference_steps (`int`, *optional*):
                The number of diffusion steps used when generating samples with a pre-trained model.
            device (`str` or `torch.device`, *optional*):
                The device to which the timesteps should be moved to. If `None`, the timesteps are not moved.
            sigmas (`list[float]`, *optional*):
                Custom values for sigmas to be used for each diffusion step. If `None`, the sigmas are computed
                automatically.
            mu (`float`, *optional*):
                Determines the amount of shifting applied to sigmas when performing resolution-dependent timestep
                shifting.
            timesteps (`list[float]`, *optional*):
                Custom values for timesteps to be used for each diffusion step. If `None`, the timesteps are computed
                automatically.
        """
        with perfmark.region("wan-038"):
            if self.config.use_dynamic_shifting and mu is None:
                raise ValueError("`mu` must be passed when `use_dynamic_shifting` is set to be `True`")

            if sigmas is not None and timesteps is not None:
                if len(sigmas) != len(timesteps):
                    raise ValueError("`sigmas` and `timesteps` should have the same length")

            if num_inference_steps is not None:
                if (sigmas is not None and len(sigmas) != num_inference_steps) or (
                    timesteps is not None and len(timesteps) != num_inference_steps
                ):
                    raise ValueError(
                        "`sigmas` and `timesteps` should have the same length as num_inference_steps, if `num_inference_steps` is provided"
                    )
            else:
                num_inference_steps = len(sigmas) if sigmas is not None else len(timesteps)

            self.num_inference_steps = num_inference_steps

            # 1. Prepare default sigmas
            is_timesteps_provided = timesteps is not None

            if is_timesteps_provided:
                timesteps = np.array(timesteps).astype(np.float32)

            if sigmas is None:
                if timesteps is None:
                    timesteps = np.linspace(
                        self._sigma_to_t(self.sigma_max),
                        self._sigma_to_t(self.sigma_min),
                        num_inference_steps,
                    )
                sigmas = timesteps / self.config.num_train_timesteps
            else:
                sigmas = np.array(sigmas).astype(np.float32)
                num_inference_steps = len(sigmas)

            # 2. Perform timestep shifting. Either no shifting is applied, or resolution-dependent shifting of
            #    "exponential" or "linear" type is applied
            if self.config.use_dynamic_shifting:
                sigmas = self.time_shift(mu, 1.0, sigmas)
            else:
                sigmas = self.shift * sigmas / (1 + (self.shift - 1) * sigmas)

            # 3. If required, stretch the sigmas schedule to terminate at the configured `shift_terminal` value
            if self.config.shift_terminal:
                sigmas = self.stretch_shift_to_terminal(sigmas)

            # 4. If required, convert sigmas to one of karras, exponential, or beta sigma schedules
            if self.config.use_karras_sigmas:
                sigmas = self._convert_to_karras(in_sigmas=sigmas, num_inference_steps=num_inference_steps)
            elif self.config.use_exponential_sigmas:
                sigmas = self._convert_to_exponential(in_sigmas=sigmas, num_inference_steps=num_inference_steps)
            elif self.config.use_beta_sigmas:
                sigmas = self._convert_to_beta(in_sigmas=sigmas, num_inference_steps=num_inference_steps)

            # 5. Convert sigmas and timesteps to tensors and move to specified device
            sigmas = torch.from_numpy(sigmas).to(dtype=torch.float32, device=device)
            timesteps = sigmas * self.config.num_train_timesteps

            # 6. Append the terminal sigma value.
            #    If a model requires inverted sigma schedule for denoising but timesteps without inversion, the
            #    `invert_sigmas` flag can be set to `True`. This case is only required in Mochi
            if self.config.invert_sigmas:
                sigmas = 1.0 - sigmas
                timesteps = sigmas * self.config.num_train_timesteps
                sigmas = torch.cat([sigmas, torch.ones(1, device=sigmas.device)])
            else:
                sigmas = torch.cat([sigmas, torch.zeros(1, device=sigmas.device)])

            self.timesteps = timesteps
            self.sigmas = sigmas
            self._step_index = None
            self._begin_index = None

    def index_for_timestep(
        self,
        timestep: Union[float, torch.FloatTensor],
        schedule_timesteps: Optional[torch.FloatTensor] = None,
    ) -> int:
        """
        Get the index for the given timestep.

        Args:
            timestep (`float` or `torch.FloatTensor`):
                The timestep to find the index for.
            schedule_timesteps (`torch.FloatTensor`, *optional*):
                The schedule timesteps to validate against. If `None`, the scheduler's timesteps are used.

        Returns:
            `int`:
                The index of the timestep.
        """
        if schedule_timesteps is None:
            schedule_timesteps = self.timesteps

        indices = (schedule_timesteps == timestep).nonzero()

        # The sigma index that is taken for the **very** first `step`
        # is always the second index (or the last index if there is only 1)
        # This way we can ensure we don't accidentally skip a sigma in
        # case we start in the middle of the denoising schedule (e.g. for image-to-image)
        pos = 1 if len(indices) > 1 else 0

        return indices[pos].item()

    def _init_step_index(self, timestep: Union[float, torch.FloatTensor]) -> None:
        if self.begin_index is None:
            if isinstance(timestep, torch.Tensor):
                timestep = timestep.to(self.timesteps.device)
            self._step_index = self.index_for_timestep(timestep)
        else:
            self._step_index = self._begin_index

    def step(
        self,
        model_output: torch.FloatTensor,
        timestep: float | torch.FloatTensor,
        sample: torch.FloatTensor,
        s_churn: float = 0.0,
        s_tmin: float = 0.0,
        s_tmax: float = float("inf"),
        s_noise: float = 1.0,
        generator: torch.Generator | None = None,
        per_token_timesteps: torch.Tensor | None = None,
        return_dict: bool = True,
    ) -> FlowMatchEulerDiscreteSchedulerOutput | tuple:
        """
        Predict the sample from the previous timestep by reversing the SDE. This function propagates the diffusion
        process from the learned model outputs (most often the predicted noise).

        Args:
            model_output (`torch.FloatTensor`):
                The direct output from learned diffusion model.
            timestep (`float`):
                The current discrete timestep in the diffusion chain.
            sample (`torch.FloatTensor`):
                A current instance of a sample created by the diffusion process.
            s_churn (`float`):
            s_tmin  (`float`):
            s_tmax  (`float`):
            s_noise (`float`, defaults to 1.0):
                Scaling factor for noise added to the sample.
            generator (`torch.Generator`, *optional*):
                A random number generator.
            per_token_timesteps (`torch.Tensor`, *optional*):
                The timesteps for each token in the sample.
            return_dict (`bool`, defaults to `True`):
                Whether or not to return a
                [`~schedulers.scheduling_flow_match_euler_discrete.FlowMatchEulerDiscreteSchedulerOutput`] or tuple.

        Returns:
            [`~schedulers.scheduling_flow_match_euler_discrete.FlowMatchEulerDiscreteSchedulerOutput`] or `tuple`:
                If return_dict is `True`,
                [`~schedulers.scheduling_flow_match_euler_discrete.FlowMatchEulerDiscreteSchedulerOutput`] is returned,
                otherwise a tuple is returned where the first element is the sample tensor.
        """

        if (
            isinstance(timestep, int)
            or isinstance(timestep, torch.IntTensor)
            or isinstance(timestep, torch.LongTensor)
        ):
            raise ValueError(
                (
                    "Passing integer indices (e.g. from `enumerate(timesteps)`) as timesteps to"
                    " `FlowMatchEulerDiscreteScheduler.step()` is not supported. Make sure to pass"
                    " one of the `scheduler.timesteps` as a timestep."
                ),
            )

        if self.step_index is None:
            self._init_step_index(timestep)

        # Upcast to avoid precision issues when computing prev_sample
        sample = sample.to(torch.float32)

        if per_token_timesteps is not None:
            per_token_sigmas = per_token_timesteps / self.config.num_train_timesteps

            sigmas = self.sigmas[:, None, None]
            lower_mask = sigmas < per_token_sigmas[None] - 1e-6
            lower_sigmas = lower_mask * sigmas
            lower_sigmas, _ = lower_sigmas.max(dim=0)

            current_sigma = per_token_sigmas[..., None]
            next_sigma = lower_sigmas[..., None]
            dt = current_sigma - next_sigma
        else:
            sigma_idx = self.step_index
            sigma = self.sigmas[sigma_idx]
            sigma_next = self.sigmas[sigma_idx + 1]

            current_sigma = sigma
            next_sigma = sigma_next
            dt = sigma_next - sigma

        if self.config.stochastic_sampling:
            x0 = sample - current_sigma * model_output
            noise = randn_tensor(sample.shape, generator=generator, device=sample.device, dtype=sample.dtype)
            prev_sample = (1.0 - next_sigma) * x0 + next_sigma * noise
        else:
            prev_sample = sample + dt * model_output

        # upon completion increase step index by one
        self._step_index += 1
        if per_token_timesteps is None:
            # Cast sample back to model compatible dtype
            prev_sample = prev_sample.to(model_output.dtype)

        if not return_dict:
            return (prev_sample,)

        return FlowMatchEulerDiscreteSchedulerOutput(prev_sample=prev_sample)

    # Copied from diffusers.schedulers.scheduling_euler_discrete.EulerDiscreteScheduler._convert_to_karras
    def _convert_to_karras(self, in_sigmas: torch.Tensor, num_inference_steps: int) -> torch.Tensor:
        """
        Construct the noise schedule as proposed in [Elucidating the Design Space of Diffusion-Based Generative
        Models](https://huggingface.co/papers/2206.00364).

        Args:
            in_sigmas (`torch.Tensor`):
                The input sigma values to be converted.
            num_inference_steps (`int`):
                The number of inference steps to generate the noise schedule for.

        Returns:
            `torch.Tensor`:
                The converted sigma values following the Karras noise schedule.
        """

        # Hack to make sure that other schedulers which copy this function don't break
        # TODO: Add this logic to the other schedulers
        if hasattr(self.config, "sigma_min"):
            sigma_min = self.config.sigma_min
        else:
            sigma_min = None

        if hasattr(self.config, "sigma_max"):
            sigma_max = self.config.sigma_max
        else:
            sigma_max = None

        sigma_min = sigma_min if sigma_min is not None else in_sigmas[-1].item()
        sigma_max = sigma_max if sigma_max is not None else in_sigmas[0].item()

        rho = 7.0  # 7.0 is the value used in the paper
        ramp = np.linspace(0, 1, num_inference_steps)
        min_inv_rho = sigma_min ** (1 / rho)
        max_inv_rho = sigma_max ** (1 / rho)
        sigmas = (max_inv_rho + ramp * (min_inv_rho - max_inv_rho)) ** rho
        return sigmas

    # Copied from diffusers.schedulers.scheduling_euler_discrete.EulerDiscreteScheduler._convert_to_exponential
    def _convert_to_exponential(self, in_sigmas: torch.Tensor, num_inference_steps: int) -> torch.Tensor:
        """
        Construct an exponential noise schedule.

        Args:
            in_sigmas (`torch.Tensor`):
                The input sigma values to be converted.
            num_inference_steps (`int`):
                The number of inference steps to generate the noise schedule for.

        Returns:
            `torch.Tensor`:
                The converted sigma values following an exponential schedule.
        """

        # Hack to make sure that other schedulers which copy this function don't break
        # TODO: Add this logic to the other schedulers
        if hasattr(self.config, "sigma_min"):
            sigma_min = self.config.sigma_min
        else:
            sigma_min = None

        if hasattr(self.config, "sigma_max"):
            sigma_max = self.config.sigma_max
        else:
            sigma_max = None

        sigma_min = sigma_min if sigma_min is not None else in_sigmas[-1].item()
        sigma_max = sigma_max if sigma_max is not None else in_sigmas[0].item()

        sigmas = np.exp(np.linspace(math.log(sigma_max), math.log(sigma_min), num_inference_steps))
        return sigmas

    # Copied from diffusers.schedulers.scheduling_euler_discrete.EulerDiscreteScheduler._convert_to_beta
    def _convert_to_beta(
        self, in_sigmas: torch.Tensor, num_inference_steps: int, alpha: float = 0.6, beta: float = 0.6
    ) -> torch.Tensor:
        """
        Construct a beta noise schedule as proposed in [Beta Sampling is All You
        Need](https://huggingface.co/papers/2407.12173).

        Args:
            in_sigmas (`torch.Tensor`):
                The input sigma values to be converted.
            num_inference_steps (`int`):
                The number of inference steps to generate the noise schedule for.
            alpha (`float`, *optional*, defaults to `0.6`):
                The alpha parameter for the beta distribution.
            beta (`float`, *optional*, defaults to `0.6`):
                The beta parameter for the beta distribution.

        Returns:
            `torch.Tensor`:
                The converted sigma values following a beta distribution schedule.
        """

        # Hack to make sure that other schedulers which copy this function don't break
        # TODO: Add this logic to the other schedulers
        if hasattr(self.config, "sigma_min"):
            sigma_min = self.config.sigma_min
        else:
            sigma_min = None

        if hasattr(self.config, "sigma_max"):
            sigma_max = self.config.sigma_max
        else:
            sigma_max = None

        sigma_min = sigma_min if sigma_min is not None else in_sigmas[-1].item()
        sigma_max = sigma_max if sigma_max is not None else in_sigmas[0].item()

        sigmas = np.array(
            [
                sigma_min + (ppf * (sigma_max - sigma_min))
                for ppf in [
                    scipy.stats.beta.ppf(timestep, alpha, beta)
                    for timestep in 1 - np.linspace(0, 1, num_inference_steps)
                ]
            ]
        )
        return sigmas

    def _time_shift_exponential(self, mu: float, sigma: float, t: torch.Tensor) -> torch.Tensor:
        return math.exp(mu) / (math.exp(mu) + (1 / t - 1) ** sigma)

    def _time_shift_linear(self, mu: float, sigma: float, t: torch.Tensor) -> torch.Tensor:
        return mu / (mu + (1 / t - 1) ** sigma)

    def __len__(self) -> int:
        return self.config.num_train_timesteps

--- FILE: tests/test_case.py ---
"""Correctness and marker-reachability test for wan-038."""
import argparse
from marker_probe import Probe

parser = argparse.ArgumentParser()
parser.add_argument("--source-root", required=True)
args = parser.parse_args()
probe = Probe()
from helper import run
run("wan-038", args.source_root)
probe.finish("wan-038")

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
    elif number <= 39:
        for _ in range(3):
            _run_scheduler(torch, diffusers, number)
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
# wan-038

Find cheap state expressions available at entry to the existing `perfmark.region` that explain its instruction count. Derived features, products, powers, comparisons, conditional expressions, and relevant runtime or library state are allowed. Preserve the marked region, program behavior, and workload.

--- FILE: case.json ---
{
  "schema_version": 1,
  "id": "wan-038",
  "title": "FlowMatchEulerDiscreteScheduler.set_timesteps body",
  "language": "python",
  "region": {
    "symbol": "FlowMatchEulerDiscreteScheduler.set_timesteps",
    "start_line": 309,
    "end_line": 382,
    "kind": "function"
  },
  "marker": {
    "kind": "python-context",
    "name": "wan-038",
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
    "path": "src/diffusers/schedulers/scheduling_flow_match_euler_discrete.py",
    "sha256": "1af27be5b2f92b7d139d3c50239be5ce3eafc4a7eddf59c2d30689f8ec31e93d"
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
