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

CASE: wan-016
SANITIZED BENCHMARK:
--- FILE: src/diffusers/models/autoencoders/vae.py ---
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
from dataclasses import dataclass

import numpy as np
import torch
import torch.nn as nn

from ...utils import BaseOutput
from ...utils.torch_utils import randn_tensor
from ..activations import get_activation
from ..attention_processor import SpatialNorm
from ..unets.unet_2d_blocks import (
    AutoencoderTinyBlock,
    UNetMidBlock2D,
    get_down_block,
    get_up_block,
)


@dataclass
class EncoderOutput(BaseOutput):
    r"""
    Output of encoding method.

    Args:
        latent (`torch.Tensor` of shape `(batch_size, num_channels, latent_height, latent_width)`):
            The encoded latent.
    """

    latent: torch.Tensor


@dataclass
class DecoderOutput(BaseOutput):
    r"""
    Output of decoding method.

    Args:
        sample (`torch.Tensor` of shape `(batch_size, num_channels, height, width)`):
            The decoded output sample from the last layer of the model.
    """

    sample: torch.Tensor
    commit_loss: torch.FloatTensor | None = None


class Encoder(nn.Module):
    r"""
    The `Encoder` layer of a variational autoencoder that encodes its input into a latent representation.

    Args:
        in_channels (`int`, *optional*, defaults to 3):
            The number of input channels.
        out_channels (`int`, *optional*, defaults to 3):
            The number of output channels.
        down_block_types (`tuple[str, ...]`, *optional*, defaults to `("DownEncoderBlock2D",)`):
            The types of down blocks to use. See `~diffusers.models.unet_2d_blocks.get_down_block` for available
            options.
        block_out_channels (`tuple[int, ...]`, *optional*, defaults to `(64,)`):
            The number of output channels for each block.
        layers_per_block (`int`, *optional*, defaults to 2):
            The number of layers per block.
        norm_num_groups (`int`, *optional*, defaults to 32):
            The number of groups for normalization.
        act_fn (`str`, *optional*, defaults to `"silu"`):
            The activation function to use. See `~diffusers.models.activations.get_activation` for available options.
        double_z (`bool`, *optional*, defaults to `True`):
            Whether to double the number of output channels for the last block.
    """

    def __init__(
        self,
        in_channels: int = 3,
        out_channels: int = 3,
        down_block_types: tuple[str, ...] = ("DownEncoderBlock2D",),
        block_out_channels: tuple[int, ...] = (64,),
        layers_per_block: int = 2,
        norm_num_groups: int = 32,
        act_fn: str = "silu",
        double_z: bool = True,
        mid_block_add_attention=True,
    ):
        super().__init__()
        self.layers_per_block = layers_per_block

        self.conv_in = nn.Conv2d(
            in_channels,
            block_out_channels[0],
            kernel_size=3,
            stride=1,
            padding=1,
        )

        self.down_blocks = nn.ModuleList([])

        # down
        output_channel = block_out_channels[0]
        for i, down_block_type in enumerate(down_block_types):
            input_channel = output_channel
            output_channel = block_out_channels[i]
            is_final_block = i == len(block_out_channels) - 1

            down_block = get_down_block(
                down_block_type,
                num_layers=self.layers_per_block,
                in_channels=input_channel,
                out_channels=output_channel,
                add_downsample=not is_final_block,
                resnet_eps=1e-6,
                downsample_padding=0,
                resnet_act_fn=act_fn,
                resnet_groups=norm_num_groups,
                attention_head_dim=output_channel,
                temb_channels=None,
            )
            self.down_blocks.append(down_block)

        # mid
        self.mid_block = UNetMidBlock2D(
            in_channels=block_out_channels[-1],
            resnet_eps=1e-6,
            resnet_act_fn=act_fn,
            output_scale_factor=1,
            resnet_time_scale_shift="default",
            attention_head_dim=block_out_channels[-1],
            resnet_groups=norm_num_groups,
            temb_channels=None,
            add_attention=mid_block_add_attention,
        )

        # out
        self.conv_norm_out = nn.GroupNorm(num_channels=block_out_channels[-1], num_groups=norm_num_groups, eps=1e-6)
        self.conv_act = nn.SiLU()

        conv_out_channels = 2 * out_channels if double_z else out_channels
        self.conv_out = nn.Conv2d(block_out_channels[-1], conv_out_channels, 3, padding=1)

        self.gradient_checkpointing = False

    def forward(self, sample: torch.Tensor) -> torch.Tensor:
        r"""The forward method of the `Encoder` class."""

        sample = self.conv_in(sample)

        if torch.is_grad_enabled() and self.gradient_checkpointing:
            # down
            for down_block in self.down_blocks:
                sample = self._gradient_checkpointing_func(down_block, sample)
            # middle
            sample = self._gradient_checkpointing_func(self.mid_block, sample)

        else:
            # down
            for down_block in self.down_blocks:
                sample = down_block(sample)

            # middle
            sample = self.mid_block(sample)

        # post-process
        sample = self.conv_norm_out(sample)
        sample = self.conv_act(sample)
        sample = self.conv_out(sample)

        return sample


class Decoder(nn.Module):
    r"""
    The `Decoder` layer of a variational autoencoder that decodes its latent representation into an output sample.

    Args:
        in_channels (`int`, *optional*, defaults to 3):
            The number of input channels.
        out_channels (`int`, *optional*, defaults to 3):
            The number of output channels.
        up_block_types (`tuple[str, ...]`, *optional*, defaults to `("UpDecoderBlock2D",)`):
            The types of up blocks to use. See `~diffusers.models.unet_2d_blocks.get_up_block` for available options.
        block_out_channels (`tuple[int, ...]`, *optional*, defaults to `(64,)`):
            The number of output channels for each block.
        layers_per_block (`int`, *optional*, defaults to 2):
            The number of layers per block.
        norm_num_groups (`int`, *optional*, defaults to 32):
            The number of groups for normalization.
        act_fn (`str`, *optional*, defaults to `"silu"`):
            The activation function to use. See `~diffusers.models.activations.get_activation` for available options.
        norm_type (`str`, *optional*, defaults to `"group"`):
            The normalization type to use. Can be either `"group"` or `"spatial"`.
    """

    def __init__(
        self,
        in_channels: int = 3,
        out_channels: int = 3,
        up_block_types: tuple[str, ...] = ("UpDecoderBlock2D",),
        block_out_channels: tuple[int, ...] = (64,),
        layers_per_block: int = 2,
        norm_num_groups: int = 32,
        act_fn: str = "silu",
        norm_type: str = "group",  # group, spatial
        mid_block_add_attention=True,
    ):
        super().__init__()
        self.layers_per_block = layers_per_block

        self.conv_in = nn.Conv2d(
            in_channels,
            block_out_channels[-1],
            kernel_size=3,
            stride=1,
            padding=1,
        )

        self.up_blocks = nn.ModuleList([])

        temb_channels = in_channels if norm_type == "spatial" else None

        # mid
        self.mid_block = UNetMidBlock2D(
            in_channels=block_out_channels[-1],
            resnet_eps=1e-6,
            resnet_act_fn=act_fn,
            output_scale_factor=1,
            resnet_time_scale_shift="default" if norm_type == "group" else norm_type,
            attention_head_dim=block_out_channels[-1],
            resnet_groups=norm_num_groups,
            temb_channels=temb_channels,
            add_attention=mid_block_add_attention,
        )

        # up
        reversed_block_out_channels = list(reversed(block_out_channels))
        output_channel = reversed_block_out_channels[0]
        for i, up_block_type in enumerate(up_block_types):
            prev_output_channel = output_channel
            output_channel = reversed_block_out_channels[i]

            is_final_block = i == len(block_out_channels) - 1

            up_block = get_up_block(
                up_block_type,
                num_layers=self.layers_per_block + 1,
                in_channels=prev_output_channel,
                out_channels=output_channel,
                prev_output_channel=prev_output_channel,
                add_upsample=not is_final_block,
                resnet_eps=1e-6,
                resnet_act_fn=act_fn,
                resnet_groups=norm_num_groups,
                attention_head_dim=output_channel,
                temb_channels=temb_channels,
                resnet_time_scale_shift=norm_type,
            )
            self.up_blocks.append(up_block)
            prev_output_channel = output_channel

        # out
        if norm_type == "spatial":
            self.conv_norm_out = SpatialNorm(block_out_channels[0], temb_channels)
        else:
            self.conv_norm_out = nn.GroupNorm(num_channels=block_out_channels[0], num_groups=norm_num_groups, eps=1e-6)
        self.conv_act = nn.SiLU()
        self.conv_out = nn.Conv2d(block_out_channels[0], out_channels, 3, padding=1)

        self.gradient_checkpointing = False

    def forward(
        self,
        sample: torch.Tensor,
        latent_embeds: torch.Tensor | None = None,
    ) -> torch.Tensor:
        r"""The forward method of the `Decoder` class."""

        sample = self.conv_in(sample)

        if torch.is_grad_enabled() and self.gradient_checkpointing:
            # middle
            sample = self._gradient_checkpointing_func(self.mid_block, sample, latent_embeds)

            # up
            for up_block in self.up_blocks:
                sample = self._gradient_checkpointing_func(up_block, sample, latent_embeds)
        else:
            # middle
            sample = self.mid_block(sample, latent_embeds)

            # up
            for up_block in self.up_blocks:
                sample = up_block(sample, latent_embeds)

        # post-process
        if latent_embeds is None:
            sample = self.conv_norm_out(sample)
        else:
            sample = self.conv_norm_out(sample, latent_embeds)
        sample = self.conv_act(sample)
        sample = self.conv_out(sample)

        return sample


class UpSample(nn.Module):
    r"""
    The `UpSample` layer of a variational autoencoder that upsamples its input.

    Args:
        in_channels (`int`, *optional*, defaults to 3):
            The number of input channels.
        out_channels (`int`, *optional*, defaults to 3):
            The number of output channels.
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
    ) -> None:
        super().__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.deconv = nn.ConvTranspose2d(in_channels, out_channels, kernel_size=4, stride=2, padding=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        r"""The forward method of the `UpSample` class."""
        x = torch.relu(x)
        x = self.deconv(x)
        return x


class MaskConditionEncoder(nn.Module):
    """
    used in AsymmetricAutoencoderKL
    """

    def __init__(
        self,
        in_ch: int,
        out_ch: int = 192,
        res_ch: int = 768,
        stride: int = 16,
    ) -> None:
        super().__init__()

        channels = []
        while stride > 1:
            stride = stride // 2
            in_ch_ = out_ch * 2
            if out_ch > res_ch:
                out_ch = res_ch
            if stride == 1:
                in_ch_ = res_ch
            channels.append((in_ch_, out_ch))
            out_ch *= 2

        out_channels = []
        for _in_ch, _out_ch in channels:
            out_channels.append(_out_ch)
        out_channels.append(channels[-1][0])

        layers = []
        in_ch_ = in_ch
        for l in range(len(out_channels)):
            out_ch_ = out_channels[l]
            if l == 0 or l == 1:
                layers.append(nn.Conv2d(in_ch_, out_ch_, kernel_size=3, stride=1, padding=1))
            else:
                layers.append(nn.Conv2d(in_ch_, out_ch_, kernel_size=4, stride=2, padding=1))
            in_ch_ = out_ch_

        self.layers = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor, mask=None) -> torch.Tensor:
        r"""The forward method of the `MaskConditionEncoder` class."""
        out = {}
        for l in range(len(self.layers)):
            layer = self.layers[l]
            x = layer(x)
            out[str(tuple(x.shape))] = x
            x = torch.relu(x)
        return out


class MaskConditionDecoder(nn.Module):
    r"""The `MaskConditionDecoder` should be used in combination with [`AsymmetricAutoencoderKL`] to enhance the model's
    decoder with a conditioner on the mask and masked image.

    Args:
        in_channels (`int`, *optional*, defaults to 3):
            The number of input channels.
        out_channels (`int`, *optional*, defaults to 3):
            The number of output channels.
        up_block_types (`tuple[str, ...]`, *optional*, defaults to `("UpDecoderBlock2D",)`):
            The types of up blocks to use. See `~diffusers.models.unet_2d_blocks.get_up_block` for available options.
        block_out_channels (`tuple[int, ...]`, *optional*, defaults to `(64,)`):
            The number of output channels for each block.
        layers_per_block (`int`, *optional*, defaults to 2):
            The number of layers per block.
        norm_num_groups (`int`, *optional*, defaults to 32):
            The number of groups for normalization.
        act_fn (`str`, *optional*, defaults to `"silu"`):
            The activation function to use. See `~diffusers.models.activations.get_activation` for available options.
        norm_type (`str`, *optional*, defaults to `"group"`):
            The normalization type to use. Can be either `"group"` or `"spatial"`.
    """

    def __init__(
        self,
        in_channels: int = 3,
        out_channels: int = 3,
        up_block_types: tuple[str, ...] = ("UpDecoderBlock2D",),
        block_out_channels: tuple[int, ...] = (64,),
        layers_per_block: int = 2,
        norm_num_groups: int = 32,
        act_fn: str = "silu",
        norm_type: str = "group",  # group, spatial
    ):
        super().__init__()
        self.layers_per_block = layers_per_block

        self.conv_in = nn.Conv2d(
            in_channels,
            block_out_channels[-1],
            kernel_size=3,
            stride=1,
            padding=1,
        )

        self.up_blocks = nn.ModuleList([])

        temb_channels = in_channels if norm_type == "spatial" else None

        # mid
        self.mid_block = UNetMidBlock2D(
            in_channels=block_out_channels[-1],
            resnet_eps=1e-6,
            resnet_act_fn=act_fn,
            output_scale_factor=1,
            resnet_time_scale_shift="default" if norm_type == "group" else norm_type,
            attention_head_dim=block_out_channels[-1],
            resnet_groups=norm_num_groups,
            temb_channels=temb_channels,
        )

        # up
        reversed_block_out_channels = list(reversed(block_out_channels))
        output_channel = reversed_block_out_channels[0]
        for i, up_block_type in enumerate(up_block_types):
            prev_output_channel = output_channel
            output_channel = reversed_block_out_channels[i]

            is_final_block = i == len(block_out_channels) - 1

            up_block = get_up_block(
                up_block_type,
                num_layers=self.layers_per_block + 1,
                in_channels=prev_output_channel,
                out_channels=output_channel,
                prev_output_channel=None,
                add_upsample=not is_final_block,
                resnet_eps=1e-6,
                resnet_act_fn=act_fn,
                resnet_groups=norm_num_groups,
                attention_head_dim=output_channel,
                temb_channels=temb_channels,
                resnet_time_scale_shift=norm_type,
            )
            self.up_blocks.append(up_block)
            prev_output_channel = output_channel

        # condition encoder
        self.condition_encoder = MaskConditionEncoder(
            in_ch=out_channels,
            out_ch=block_out_channels[0],
            res_ch=block_out_channels[-1],
        )

        # out
        if norm_type == "spatial":
            self.conv_norm_out = SpatialNorm(block_out_channels[0], temb_channels)
        else:
            self.conv_norm_out = nn.GroupNorm(num_channels=block_out_channels[0], num_groups=norm_num_groups, eps=1e-6)
        self.conv_act = nn.SiLU()
        self.conv_out = nn.Conv2d(block_out_channels[0], out_channels, 3, padding=1)

        self.gradient_checkpointing = False

    def forward(
        self,
        z: torch.Tensor,
        image: torch.Tensor | None = None,
        mask: torch.Tensor | None = None,
        latent_embeds: torch.Tensor | None = None,
    ) -> torch.Tensor:
        r"""The forward method of the `MaskConditionDecoder` class."""
        sample = z
        sample = self.conv_in(sample)

        upscale_dtype = next(iter(self.up_blocks.parameters())).dtype
        if torch.is_grad_enabled() and self.gradient_checkpointing:
            # middle
            sample = self._gradient_checkpointing_func(self.mid_block, sample, latent_embeds)
            sample = sample.to(upscale_dtype)

            # condition encoder
            if image is not None and mask is not None:
                masked_image = (1 - mask) * image
                im_x = self._gradient_checkpointing_func(
                    self.condition_encoder,
                    masked_image,
                    mask,
                )

            # up
            for up_block in self.up_blocks:
                if image is not None and mask is not None:
                    sample_ = im_x[str(tuple(sample.shape))]
                    mask_ = nn.functional.interpolate(mask, size=sample.shape[-2:], mode="nearest")
                    sample = sample * mask_ + sample_ * (1 - mask_)
                sample = self._gradient_checkpointing_func(up_block, sample, latent_embeds)
            if image is not None and mask is not None:
                sample = sample * mask + im_x[str(tuple(sample.shape))] * (1 - mask)
        else:
            # middle
            sample = self.mid_block(sample, latent_embeds)
            sample = sample.to(upscale_dtype)

            # condition encoder
            if image is not None and mask is not None:
                masked_image = (1 - mask) * image
                im_x = self.condition_encoder(masked_image, mask)

            # up
            for up_block in self.up_blocks:
                if image is not None and mask is not None:
                    sample_ = im_x[str(tuple(sample.shape))]
                    mask_ = nn.functional.interpolate(mask, size=sample.shape[-2:], mode="nearest")
                    sample = sample * mask_ + sample_ * (1 - mask_)
                sample = up_block(sample, latent_embeds)
            if image is not None and mask is not None:
                sample = sample * mask + im_x[str(tuple(sample.shape))] * (1 - mask)

        # post-process
        if latent_embeds is None:
            sample = self.conv_norm_out(sample)
        else:
            sample = self.conv_norm_out(sample, latent_embeds)
        sample = self.conv_act(sample)
        sample = self.conv_out(sample)

        return sample


class VectorQuantizer(nn.Module):
    """
    Improved version over VectorQuantizer, can be used as a drop-in replacement. Mostly avoids costly matrix
    multiplications and allows for post-hoc remapping of indices.
    """

    # NOTE: due to a bug the beta term was applied to the wrong term. for
    # backwards compatibility we use the buggy version by default, but you can
    # specify legacy=False to fix it.
    def __init__(
        self,
        n_e: int,
        vq_embed_dim: int,
        beta: float,
        remap=None,
        unknown_index: str = "random",
        sane_index_shape: bool = False,
        legacy: bool = True,
    ):
        super().__init__()
        self.n_e = n_e
        self.vq_embed_dim = vq_embed_dim
        self.beta = beta
        self.legacy = legacy

        self.embedding = nn.Embedding(self.n_e, self.vq_embed_dim)
        self.embedding.weight.data.uniform_(-1.0 / self.n_e, 1.0 / self.n_e)

        self.remap = remap
        if self.remap is not None:
            self.register_buffer("used", torch.tensor(np.load(self.remap)))
            self.used: torch.Tensor
            self.re_embed = self.used.shape[0]
            self.unknown_index = unknown_index  # "random" or "extra" or integer
            if self.unknown_index == "extra":
                self.unknown_index = self.re_embed
                self.re_embed = self.re_embed + 1
            print(
                f"Remapping {self.n_e} indices to {self.re_embed} indices. "
                f"Using {self.unknown_index} for unknown indices."
            )
        else:
            self.re_embed = n_e

        self.sane_index_shape = sane_index_shape

    def remap_to_used(self, inds: torch.LongTensor) -> torch.LongTensor:
        ishape = inds.shape
        assert len(ishape) > 1
        inds = inds.reshape(ishape[0], -1)
        used = self.used.to(inds)
        match = (inds[:, :, None] == used[None, None, ...]).long()
        new = match.argmax(-1)
        unknown = match.sum(2) < 1
        if self.unknown_index == "random":
            new[unknown] = torch.randint(0, self.re_embed, size=new[unknown].shape).to(device=new.device)
        else:
            new[unknown] = self.unknown_index
        return new.reshape(ishape)

    def unmap_to_all(self, inds: torch.LongTensor) -> torch.LongTensor:
        ishape = inds.shape
        assert len(ishape) > 1
        inds = inds.reshape(ishape[0], -1)
        used = self.used.to(inds)
        if self.re_embed > self.used.shape[0]:  # extra token
            inds[inds >= self.used.shape[0]] = 0  # simply set to zero
        back = torch.gather(used[None, :][inds.shape[0] * [0], :], 1, inds)
        return back.reshape(ishape)

    def forward(self, z: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, tuple]:
        # reshape z -> (batch, height, width, channel) and flatten
        z = z.permute(0, 2, 3, 1).contiguous()
        z_flattened = z.view(-1, self.vq_embed_dim)

        # distances from z to embeddings e_j (z - e)^2 = z^2 + e^2 - 2 e * z
        min_encoding_indices = torch.argmin(torch.cdist(z_flattened, self.embedding.weight), dim=1)

        z_q = self.embedding(min_encoding_indices).view(z.shape)
        perplexity = None
        min_encodings = None

        # compute loss for embedding
        if not self.legacy:
            loss = self.beta * torch.mean((z_q.detach() - z) ** 2) + torch.mean((z_q - z.detach()) ** 2)
        else:
            loss = torch.mean((z_q.detach() - z) ** 2) + self.beta * torch.mean((z_q - z.detach()) ** 2)

        # preserve gradients
        z_q: torch.Tensor = z + (z_q - z).detach()

        # reshape back to match original input shape
        z_q = z_q.permute(0, 3, 1, 2).contiguous()

        if self.remap is not None:
            min_encoding_indices = min_encoding_indices.reshape(z.shape[0], -1)  # add batch axis
            min_encoding_indices = self.remap_to_used(min_encoding_indices)
            min_encoding_indices = min_encoding_indices.reshape(-1, 1)  # flatten

        if self.sane_index_shape:
            min_encoding_indices = min_encoding_indices.reshape(z_q.shape[0], z_q.shape[2], z_q.shape[3])

        return z_q, loss, (perplexity, min_encodings, min_encoding_indices)

    def get_codebook_entry(self, indices: torch.LongTensor, shape: tuple[int, ...]) -> torch.Tensor:
        # shape specifying (batch, height, width, channel)
        if self.remap is not None:
            indices = indices.reshape(shape[0], -1)  # add batch axis
            indices = self.unmap_to_all(indices)
            indices = indices.reshape(-1)  # flatten again

        # get quantized latent vectors
        z_q: torch.Tensor = self.embedding(indices)

        if shape is not None:
            z_q = z_q.view(shape)
            # reshape back to match original input shape
            z_q = z_q.permute(0, 3, 1, 2).contiguous()

        return z_q


class DiagonalGaussianDistribution(object):
    def __init__(self, parameters: torch.Tensor, deterministic: bool = False):
        with perfmark.region("wan-016"):
            self.parameters = parameters
            self.mean, self.logvar = torch.chunk(parameters, 2, dim=1)
            self.logvar = torch.clamp(self.logvar, -30.0, 20.0)
            self.deterministic = deterministic
            self.std = torch.exp(0.5 * self.logvar)
            self.var = torch.exp(self.logvar)
            if self.deterministic:
                self.var = self.std = torch.zeros_like(
                    self.mean, device=self.parameters.device, dtype=self.parameters.dtype
                )

    def sample(self, generator: torch.Generator | None = None) -> torch.Tensor:
        # make sure sample is on the same device as the parameters and has same dtype
        sample = randn_tensor(
            self.mean.shape,
            generator=generator,
            device=self.parameters.device,
            dtype=self.parameters.dtype,
        )
        x = self.mean + self.std * sample
        return x

    def kl(self, other: "DiagonalGaussianDistribution" = None) -> torch.Tensor:
        if self.deterministic:
            return torch.Tensor([0.0])
        else:
            if other is None:
                return 0.5 * torch.sum(
                    torch.pow(self.mean, 2) + self.var - 1.0 - self.logvar,
                    dim=[1, 2, 3],
                )
            else:
                return 0.5 * torch.sum(
                    torch.pow(self.mean - other.mean, 2) / other.var
                    + self.var / other.var
                    - 1.0
                    - self.logvar
                    + other.logvar,
                    dim=[1, 2, 3],
                )

    def nll(self, sample: torch.Tensor, dims: tuple[int, ...] = [1, 2, 3]) -> torch.Tensor:
        if self.deterministic:
            return torch.Tensor([0.0])
        logtwopi = np.log(2.0 * np.pi)
        return 0.5 * torch.sum(
            logtwopi + self.logvar + torch.pow(sample - self.mean, 2) / self.var,
            dim=dims,
        )

    def mode(self) -> torch.Tensor:
        return self.mean


class IdentityDistribution(object):
    def __init__(self, parameters: torch.Tensor):
        self.parameters = parameters

    def sample(self, generator: torch.Generator | None = None) -> torch.Tensor:
        return self.parameters

    def mode(self) -> torch.Tensor:
        return self.parameters


class EncoderTiny(nn.Module):
    r"""
    The `EncoderTiny` layer is a simpler version of the `Encoder` layer.

    Args:
        in_channels (`int`):
            The number of input channels.
        out_channels (`int`):
            The number of output channels.
        num_blocks (`tuple[int, ...]`):
            Each value of the tuple represents a Conv2d layer followed by `value` number of `AutoencoderTinyBlock`'s to
            use.
        block_out_channels (`tuple[int, ...]`):
            The number of output channels for each block.
        act_fn (`str`):
            The activation function to use. See `~diffusers.models.activations.get_activation` for available options.
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        num_blocks: tuple[int, ...],
        block_out_channels: tuple[int, ...],
        act_fn: str,
    ):
        super().__init__()

        layers = []
        for i, num_block in enumerate(num_blocks):
            num_channels = block_out_channels[i]

            if i == 0:
                layers.append(nn.Conv2d(in_channels, num_channels, kernel_size=3, padding=1))
            else:
                layers.append(
                    nn.Conv2d(
                        num_channels,
                        num_channels,
                        kernel_size=3,
                        padding=1,
                        stride=2,
                        bias=False,
                    )
                )

            for _ in range(num_block):
                layers.append(AutoencoderTinyBlock(num_channels, num_channels, act_fn))

        layers.append(nn.Conv2d(block_out_channels[-1], out_channels, kernel_size=3, padding=1))

        self.layers = nn.Sequential(*layers)
        self.gradient_checkpointing = False

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        r"""The forward method of the `EncoderTiny` class."""
        if torch.is_grad_enabled() and self.gradient_checkpointing:
            x = self._gradient_checkpointing_func(self.layers, x)

        else:
            # scale image from [-1, 1] to [0, 1] to match TAESD convention
            x = self.layers(x.add(1).div(2))

        return x


class DecoderTiny(nn.Module):
    r"""
    The `DecoderTiny` layer is a simpler version of the `Decoder` layer.

    Args:
        in_channels (`int`):
            The number of input channels.
        out_channels (`int`):
            The number of output channels.
        num_blocks (`tuple[int, ...]`):
            Each value of the tuple represents a Conv2d layer followed by `value` number of `AutoencoderTinyBlock`'s to
            use.
        block_out_channels (`tuple[int, ...]`):
            The number of output channels for each block.
        upsampling_scaling_factor (`int`):
            The scaling factor to use for upsampling.
        act_fn (`str`):
            The activation function to use. See `~diffusers.models.activations.get_activation` for available options.
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        num_blocks: tuple[int, ...],
        block_out_channels: tuple[int, ...],
        upsampling_scaling_factor: int,
        act_fn: str,
        upsample_fn: str,
    ):
        super().__init__()

        layers = [
            nn.Conv2d(in_channels, block_out_channels[0], kernel_size=3, padding=1),
            get_activation(act_fn),
        ]

        for i, num_block in enumerate(num_blocks):
            is_final_block = i == (len(num_blocks) - 1)
            num_channels = block_out_channels[i]

            for _ in range(num_block):
                layers.append(AutoencoderTinyBlock(num_channels, num_channels, act_fn))

            if not is_final_block:
                layers.append(nn.Upsample(scale_factor=upsampling_scaling_factor, mode=upsample_fn))

            conv_out_channel = num_channels if not is_final_block else out_channels
            layers.append(
                nn.Conv2d(
                    num_channels,
                    conv_out_channel,
                    kernel_size=3,
                    padding=1,
                    bias=is_final_block,
                )
            )

        self.layers = nn.Sequential(*layers)
        self.gradient_checkpointing = False

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        r"""The forward method of the `DecoderTiny` class."""
        # Clamp.
        x = torch.tanh(x / 3) * 3

        if torch.is_grad_enabled() and self.gradient_checkpointing:
            x = self._gradient_checkpointing_func(self.layers, x)
        else:
            x = self.layers(x)

        # scale image from [0, 1] to [-1, 1] to match diffusers convention
        return x.mul(2).sub(1)


class AutoencoderMixin:
    def enable_tiling(self):
        r"""
        Enable tiled VAE decoding. When this option is enabled, the VAE will split the input tensor into tiles to
        compute decoding and encoding in several steps. This is useful for saving a large amount of memory and to allow
        processing larger images.
        """
        if not hasattr(self, "use_tiling"):
            raise NotImplementedError(f"Tiling doesn't seem to be implemented for {self.__class__.__name__}.")
        self.use_tiling = True

    def disable_tiling(self):
        r"""
        Disable tiled VAE decoding. If `enable_tiling` was previously enabled, this method will go back to computing
        decoding in one step.
        """
        self.use_tiling = False

    def enable_slicing(self):
        r"""
        Enable sliced VAE decoding. When this option is enabled, the VAE will split the input tensor in slices to
        compute decoding in several steps. This is useful to save some memory and allow larger batch sizes.
        """
        if not hasattr(self, "use_slicing"):
            raise NotImplementedError(f"Slicing doesn't seem to be implemented for {self.__class__.__name__}.")
        self.use_slicing = True

    def disable_slicing(self):
        r"""
        Disable sliced VAE decoding. If `enable_slicing` was previously enabled, this method will go back to computing
        decoding in one step.
        """
        self.use_slicing = False

--- FILE: tests/test_case.py ---
"""Correctness and marker-reachability test for wan-016."""
import argparse
from marker_probe import Probe

parser = argparse.ArgumentParser()
parser.add_argument("--source-root", required=True)
args = parser.parse_args()
probe = Probe()
from helper import run
run("wan-016", args.source_root)
probe.finish("wan-016")

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
    elif number <= 16:
        for _ in range(3):
            _run_vae(torch, diffusers, number)
    elif number <= 24: _run_transformer(torch, diffusers, number)
    elif number <= 36: _run_pipeline(torch, diffusers, number)
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
# wan-016

Find cheap state expressions available at entry to the existing `perfmark.region` that explain its instruction count. Derived features, products, powers, comparisons, conditional expressions, and relevant runtime or library state are allowed. Preserve the marked region, program behavior, and workload.

--- FILE: case.json ---
{
  "schema_version": 1,
  "id": "wan-016",
  "title": "DiagonalGaussianDistribution.__init__ body",
  "language": "python",
  "region": {
    "symbol": "DiagonalGaussianDistribution.__init__",
    "start_line": 689,
    "end_line": 698,
    "kind": "function"
  },
  "marker": {
    "kind": "python-context",
    "name": "wan-016",
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
    "path": "src/diffusers/models/autoencoders/vae.py",
    "sha256": "8e6abad3bd7b7806dd9c6c451b2438641ef728d7884e6bfed37b867f719b98fc"
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
