"""Second round of perfmark regions for the Wan 2.1 host path, on top of mark_wan.py.

    python mark_more.py /home/ubuntu/drperf-cases/videogen/wan-more/diffusers [--undo]

`wan-more` is a copy of `wan-src` (already carrying the 20 regions of
mark_wan.py and the four fixes of the first round).  This script adds regions on
the paths that round did not look at:

  * the attention processor split into qkv / rope-apply / sdpa / out
  * the per-step host work in the denoising loop (input cast, CFG combine,
    callback_on_step_end)
  * the scheduler's timestep lookup
  * the VAE ENCODE path, the DiagonalGaussianDistribution constructor, and the
    TILED encode/decode with their blend_v / blend_h row loops
  * postprocess_video split into denormalise / to-numpy / to-PIL / stack
  * the prompt path: prompt_clean, the text-encoder call, the re-padding

Every new region declares `tag=<unique 9xx>` as its FIRST state.  drperf's
per-thread key cache compares region and state-name strings by POINTER
(client/drperf.c get_key) and the Python binding re-allocates those bytes at
every region, so two regions under the same root with the same state COUNT and
the same state VALUES are recorded as one key.  A distinct constant in position
0 makes that impossible; it costs one of the four state slots and shows up in
the derived formula as `0*tag`.

Marks are applied by exact-text replacement so the splits inside a method body
can be placed precisely.  `--undo` restores the .orig2 copies.
"""

import os
import re
import shutil
import sys

T = "models/transformers/transformer_wan.py"
P = "pipelines/wan/pipeline_wan.py"
V = "models/autoencoders/autoencoder_kl_wan.py"
VAE = "models/autoencoders/vae.py"
S = "schedulers/scheduling_flow_match_euler_discrete.py"
VP = "video_processor.py"
IP = "image_processor.py"

# ------------------------------------------------------------------ attention
# The body of WanAttnProcessor.__call__ (already inside the `attn` region added
# by mark_wan.py) split into its four host phases.
ATTN_OLD = '''            query, key, value = _get_qkv_projections(attn, hidden_states, encoder_hidden_states)

            query = attn.norm_q(query)
            key = attn.norm_k(key)

            query = query.unflatten(2, (attn.heads, -1))
            key = key.unflatten(2, (attn.heads, -1))
            value = value.unflatten(2, (attn.heads, -1))

            if rotary_emb is not None:

                def apply_rotary_emb(
                    hidden_states: torch.Tensor,
                    freqs_cos: torch.Tensor,
                    freqs_sin: torch.Tensor,
                ):
                    x1, x2 = hidden_states.unflatten(-1, (-1, 2)).unbind(-1)
                    cos = freqs_cos[..., 0::2]
                    sin = freqs_sin[..., 1::2]
                    out = torch.empty_like(hidden_states)
                    out[..., 0::2] = x1 * cos - x2 * sin
                    out[..., 1::2] = x1 * sin + x2 * cos
                    return out.type_as(hidden_states)

                query = apply_rotary_emb(query, *rotary_emb)
                key = apply_rotary_emb(key, *rotary_emb)
'''

ATTN_NEW = '''            with perfmark.region("attn_qkv", tag=901, seq_len=hidden_states.shape[1], kv_len=(hidden_states.shape[1] if encoder_hidden_states is None else encoder_hidden_states.shape[1]), heads=attn.heads):
                query, key, value = _get_qkv_projections(attn, hidden_states, encoder_hidden_states)

                query = attn.norm_q(query)
                key = attn.norm_k(key)

                query = query.unflatten(2, (attn.heads, -1))
                key = key.unflatten(2, (attn.heads, -1))
                value = value.unflatten(2, (attn.heads, -1))

            if rotary_emb is not None:
                with perfmark.region("attn_rope", tag=902, seq_len=hidden_states.shape[1], heads=attn.heads, batch=hidden_states.shape[0]):

                    def apply_rotary_emb(
                        hidden_states: torch.Tensor,
                        freqs_cos: torch.Tensor,
                        freqs_sin: torch.Tensor,
                    ):
                        x1, x2 = hidden_states.unflatten(-1, (-1, 2)).unbind(-1)
                        cos = freqs_cos[..., 0::2]
                        sin = freqs_sin[..., 1::2]
                        out = torch.empty_like(hidden_states)
                        out[..., 0::2] = x1 * cos - x2 * sin
                        out[..., 1::2] = x1 * sin + x2 * cos
                        return out.type_as(hidden_states)

                    query = apply_rotary_emb(query, *rotary_emb)
                    key = apply_rotary_emb(key, *rotary_emb)
'''

SDPA_OLD = '''            hidden_states = dispatch_attention_fn(
                query,
                key,
                value,
                attn_mask=attention_mask,
                dropout_p=0.0,
                is_causal=False,
                backend=self._attention_backend,
                # Reference: https://github.com/huggingface/diffusers/pull/12909
                parallel_config=(self._parallel_config if encoder_hidden_states is None else None),
            )
            hidden_states = hidden_states.flatten(2, 3)
            hidden_states = hidden_states.type_as(query)

            if hidden_states_img is not None:
                hidden_states = hidden_states + hidden_states_img

            hidden_states = attn.to_out[0](hidden_states)
            hidden_states = attn.to_out[1](hidden_states)
            return hidden_states
'''

SDPA_NEW = '''            with perfmark.region("attn_sdpa", tag=903, seq_len=hidden_states.shape[1], kv_len=key.shape[1], heads=attn.heads):
                hidden_states = dispatch_attention_fn(
                    query,
                    key,
                    value,
                    attn_mask=attention_mask,
                    dropout_p=0.0,
                    is_causal=False,
                    backend=self._attention_backend,
                    # Reference: https://github.com/huggingface/diffusers/pull/12909
                    parallel_config=(self._parallel_config if encoder_hidden_states is None else None),
                )
            with perfmark.region("attn_out", tag=904, seq_len=hidden_states.shape[1], heads=attn.heads, batch=hidden_states.shape[0]):
                hidden_states = hidden_states.flatten(2, 3)
                hidden_states = hidden_states.type_as(query)

                if hidden_states_img is not None:
                    hidden_states = hidden_states + hidden_states_img

                hidden_states = attn.to_out[0](hidden_states)
                hidden_states = attn.to_out[1](hidden_states)
            return hidden_states
'''

# --------------------------------------------------------------- denoise loop
STEP_PREP_OLD = '''                        latent_model_input = latents.to(transformer_dtype)
                        if self.config.expand_timesteps:
                            # seq_len: num_latent_frames * latent_height//2 * latent_width//2
                            temp_ts = (mask[0][0][:, ::2, ::2] * t).flatten()
                            # batch_size, seq_len
                            timestep = temp_ts.unsqueeze(0).expand(latents.shape[0], -1)
                        else:
                            timestep = t.expand(latents.shape[0])
'''

STEP_PREP_NEW = '''                        with perfmark.region("step_prep", tag=905, frames=latents.shape[2], numel=latents.numel(), batch=latents.shape[0]):
                            latent_model_input = latents.to(transformer_dtype)
                            if self.config.expand_timesteps:
                                # seq_len: num_latent_frames * latent_height//2 * latent_width//2
                                temp_ts = (mask[0][0][:, ::2, ::2] * t).flatten()
                                # batch_size, seq_len
                                timestep = temp_ts.unsqueeze(0).expand(latents.shape[0], -1)
                            else:
                                timestep = t.expand(latents.shape[0])
'''

CFG_COMB_OLD = '''                                noise_pred = noise_uncond + current_guidance_scale * (noise_pred - noise_uncond)
'''

CFG_COMB_NEW = '''                                with perfmark.region("cfg_combine", tag=906, frames=latents.shape[2], height=latents.shape[3], numel=latents.numel()):
                                    noise_pred = noise_uncond + current_guidance_scale * (noise_pred - noise_uncond)
'''

CALLBACK_OLD = '''                        if callback_on_step_end is not None:
                            callback_kwargs = {}
                            for k in callback_on_step_end_tensor_inputs:
                                callback_kwargs[k] = locals()[k]
                            callback_outputs = callback_on_step_end(self, i, t, callback_kwargs)

                            latents = callback_outputs.pop("latents", latents)
                            prompt_embeds = callback_outputs.pop("prompt_embeds", prompt_embeds)
                            negative_prompt_embeds = callback_outputs.pop("negative_prompt_embeds", negative_prompt_embeds)
'''

CALLBACK_NEW = '''                        if callback_on_step_end is not None:
                            with perfmark.region("callback_step", tag=907, ninputs=len(callback_on_step_end_tensor_inputs), frames=latents.shape[2], numel=latents.numel()):
                                callback_kwargs = {}
                                for k in callback_on_step_end_tensor_inputs:
                                    callback_kwargs[k] = locals()[k]
                                callback_outputs = callback_on_step_end(self, i, t, callback_kwargs)

                                latents = callback_outputs.pop("latents", latents)
                                prompt_embeds = callback_outputs.pop("prompt_embeds", prompt_embeds)
                                negative_prompt_embeds = callback_outputs.pop("negative_prompt_embeds", negative_prompt_embeds)
'''

# ------------------------------------------------------------------ scheduler
SCHED_IDX_OLD = """        if schedule_timesteps is None:
            schedule_timesteps = self.timesteps

        indices = (schedule_timesteps == timestep).nonzero()

        # The sigma index that is taken for the **very** first `step`
        # is always the second index (or the last index if there is only 1)
        # This way we can ensure we don't accidentally skip a sigma in
        # case we start in the middle of the denoising schedule (e.g. for image-to-image)
        pos = 1 if len(indices) > 1 else 0

        return indices[pos].item()
"""

SCHED_IDX_NEW = """        with perfmark.region("sched_index", tag=908, nts=self.timesteps.numel()):
            if schedule_timesteps is None:
                schedule_timesteps = self.timesteps

            indices = (schedule_timesteps == timestep).nonzero()

            # The sigma index that is taken for the **very** first `step`
            # is always the second index (or the last index if there is only 1)
            # This way we can ensure we don't accidentally skip a sigma in
            # case we start in the middle of the denoising schedule (e.g. for image-to-image)
            pos = 1 if len(indices) > 1 else 0

            return indices[pos].item()
"""

# ------------------------------------------------------------- postprocessing
PP_OLD = '''            image = self._denormalize_conditionally(image, do_denormalize)

            if output_type == "pt":
                return image

            image = self.pt_to_numpy(image)

            if output_type == "np":
                return image

            if output_type == "pil":
                return self.numpy_to_pil(image)
'''

PP_NEW = '''            with perfmark.region("pp_denorm", tag=909, frames=image.shape[0], height=image.shape[2], width=image.shape[3]):
                image = self._denormalize_conditionally(image, do_denormalize)

            if output_type == "pt":
                return image

            with perfmark.region("pp_tonumpy", tag=910, frames=image.shape[0], height=image.shape[2], width=image.shape[3]):
                image = self.pt_to_numpy(image)

            if output_type == "np":
                return image

            if output_type == "pil":
                with perfmark.region("pp_topil", tag=911, frames=image.shape[0], height=image.shape[1], width=image.shape[2]):
                    return self.numpy_to_pil(image)
'''

PP_STACK_OLD = '''            if output_type == "np":
                outputs = np.stack(outputs)
            elif output_type == "pt":
                outputs = torch.stack(outputs)
            elif not output_type == "pil":
'''

PP_STACK_NEW = '''            if output_type == "np":
                with perfmark.region("pp_stack", tag=912, batch=batch_size, frames=video.shape[2], height=video.shape[3]):
                    outputs = np.stack(outputs)
            elif output_type == "pt":
                outputs = torch.stack(outputs)
            elif not output_type == "pil":
'''

# --------------------------------------------------------------- VAE (encode)
VAE_ENCODE_OLD = '''        if self.use_slicing and x.shape[0] > 1:
            encoded_slices = [self._encode(x_slice) for x_slice in x.split(1)]
            h = torch.cat(encoded_slices)
        else:
            h = self._encode(x)
        posterior = DiagonalGaussianDistribution(h)

        if not return_dict:
            return (posterior,)
        return AutoencoderKLOutput(latent_dist=posterior)
'''

VAE_ENCODE_NEW = '''        with perfmark.region("vae_encode", tag=913, batch=x.shape[0], frames=x.shape[2], height=x.shape[3]):
            if self.use_slicing and x.shape[0] > 1:
                encoded_slices = [self._encode(x_slice) for x_slice in x.split(1)]
                h = torch.cat(encoded_slices)
            else:
                h = self._encode(x)
            posterior = DiagonalGaussianDistribution(h)

            if not return_dict:
                return (posterior,)
            return AutoencoderKLOutput(latent_dist=posterior)
'''

VAE_ENC_FRAMES_OLD = '''    def _encode(self, x: torch.Tensor):
        _, _, num_frame, height, width = x.shape

        self.clear_cache()'''

VAE_ENC_FRAMES_NEW = '''    def _encode(self, x: torch.Tensor):
        with perfmark.region("vae_encode_frames", tag=914, frames=x.shape[2], height=x.shape[3], width=x.shape[4]):
            return self._encode_inner(x)

    def _encode_inner(self, x: torch.Tensor):
        _, _, num_frame, height, width = x.shape

        self.clear_cache()'''

VAE_ENC_CHUNK_OLD = '''    def forward(self, x, feat_cache=None, feat_idx=[0]):
        if feat_cache is not None:
            idx = feat_idx[0]
            cache_x = x[:, :, -CACHE_T:, :, :].clone()
            if cache_x.shape[2] < 2 and feat_cache[idx] is not None:
                # cache last frame of last two chunk
                cache_x = torch.cat([feat_cache[idx][:, :, -1, :, :].unsqueeze(2).to(cache_x.device), cache_x], dim=2)
            x = self.conv_in(x, feat_cache[idx])
            feat_cache[idx] = cache_x
            feat_idx[0] += 1
        else:
            x = self.conv_in(x)

        ## downsamples'''

VAE_ENC_CHUNK_NEW = '''    def forward(self, x, feat_cache=None, feat_idx=[0]):
      with perfmark.region("vae_encode_chunk", tag=915, height=x.shape[3], width=x.shape[4]):
        if feat_cache is not None:
            idx = feat_idx[0]
            cache_x = x[:, :, -CACHE_T:, :, :].clone()
            if cache_x.shape[2] < 2 and feat_cache[idx] is not None:
                # cache last frame of last two chunk
                cache_x = torch.cat([feat_cache[idx][:, :, -1, :, :].unsqueeze(2).to(cache_x.device), cache_x], dim=2)
            x = self.conv_in(x, feat_cache[idx])
            feat_cache[idx] = cache_x
            feat_idx[0] += 1
        else:
            x = self.conv_in(x)

        ## downsamples'''

DGD_OLD = '''    def __init__(self, parameters: torch.Tensor, deterministic: bool = False):
        self.parameters = parameters
        self.mean, self.logvar = torch.chunk(parameters, 2, dim=1)
        self.logvar = torch.clamp(self.logvar, -30.0, 20.0)
        self.deterministic = deterministic
        self.std = torch.exp(0.5 * self.logvar)
        self.var = torch.exp(self.logvar)'''

DGD_NEW = '''    def __init__(self, parameters: torch.Tensor, deterministic: bool = False):
      import perfmark
      with perfmark.region("dgd_init", tag=916, chans=parameters.shape[1], numel=parameters.numel()):
        self.parameters = parameters
        self.mean, self.logvar = torch.chunk(parameters, 2, dim=1)
        self.logvar = torch.clamp(self.logvar, -30.0, 20.0)
        self.deterministic = deterministic
        self.std = torch.exp(0.5 * self.logvar)
        self.var = torch.exp(self.logvar)'''

# ------------------------------------------------------------------ VAE tiling
TDEC_OLD = '''        _, _, num_frames, height, width = z.shape
        sample_height = height * self.spatial_compression_ratio
        sample_width = width * self.spatial_compression_ratio
'''

TDEC_NEW = '''        _, _, num_frames, height, width = z.shape
        with perfmark.region("tiled_decode_r", tag=917, frames=num_frames, height=height, width=width):
            return self._tiled_decode_inner(z, return_dict)

    def _tiled_decode_inner(self, z, return_dict: bool = True):
        _, _, num_frames, height, width = z.shape
        sample_height = height * self.spatial_compression_ratio
        sample_width = width * self.spatial_compression_ratio
'''

TENC_OLD = '''        _, _, num_frames, height, width = x.shape
        encode_spatial_compression_ratio = self.spatial_compression_ratio
'''

TENC_NEW = '''        _, _, num_frames, height, width = x.shape
        with perfmark.region("tiled_encode_r", tag=918, frames=num_frames, height=height, width=width):
            return self._tiled_encode_inner(x)

    def _tiled_encode_inner(self, x: torch.Tensor):
        _, _, num_frames, height, width = x.shape
        encode_spatial_compression_ratio = self.spatial_compression_ratio
'''

BLEND_OLD = '''    def blend_v(self, a: torch.Tensor, b: torch.Tensor, blend_extent: int) -> torch.Tensor:
        blend_extent = min(a.shape[-2], b.shape[-2], blend_extent)
        for y in range(blend_extent):
            b[:, :, :, y, :] = a[:, :, :, -blend_extent + y, :] * (1 - y / blend_extent) + b[:, :, :, y, :] * (
                y / blend_extent
            )
        return b

    def blend_h(self, a: torch.Tensor, b: torch.Tensor, blend_extent: int) -> torch.Tensor:
        blend_extent = min(a.shape[-1], b.shape[-1], blend_extent)
        for x in range(blend_extent):
            b[:, :, :, :, x] = a[:, :, :, :, -blend_extent + x] * (1 - x / blend_extent) + b[:, :, :, :, x] * (
                x / blend_extent
            )
        return b
'''

BLEND_NEW = '''    def blend_v(self, a: torch.Tensor, b: torch.Tensor, blend_extent: int) -> torch.Tensor:
        with perfmark.region("blend_v_r", tag=919, extent=min(a.shape[-2], b.shape[-2], blend_extent), frames=a.shape[2], width=a.shape[-1]):
            blend_extent = min(a.shape[-2], b.shape[-2], blend_extent)
            for y in range(blend_extent):
                b[:, :, :, y, :] = a[:, :, :, -blend_extent + y, :] * (1 - y / blend_extent) + b[:, :, :, y, :] * (
                    y / blend_extent
                )
            return b

    def blend_h(self, a: torch.Tensor, b: torch.Tensor, blend_extent: int) -> torch.Tensor:
        with perfmark.region("blend_h_r", tag=920, extent=min(a.shape[-1], b.shape[-1], blend_extent), frames=a.shape[2], height=a.shape[-2]):
            blend_extent = min(a.shape[-1], b.shape[-1], blend_extent)
            for x in range(blend_extent):
                b[:, :, :, :, x] = a[:, :, :, :, -blend_extent + x] * (1 - x / blend_extent) + b[:, :, :, :, x] * (
                    x / blend_extent
                )
            return b
'''

# --------------------------------------------------------------- prompt path
T5_OLD = '''        device = device or self._execution_device
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
'''

T5_NEW = '''        with perfmark.region("t5_embeds", tag=921, batch=(1 if isinstance(prompt, str) else len(prompt)), maxlen=max_sequence_length):
            device = device or self._execution_device
            dtype = dtype or self.text_encoder.dtype

            prompt = [prompt] if isinstance(prompt, str) else prompt
            with perfmark.region("prompt_clean_r", tag=922, batch=len(prompt), chars=sum(len(u) for u in prompt)):
                prompt = [prompt_clean(u) for u in prompt]
            batch_size = len(prompt)

            with perfmark.region("t5_forward", tag=923, batch=batch_size, maxlen=max_sequence_length):
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

            with perfmark.region("t5_repad", tag=924, batch=batch_size, maxlen=max_sequence_length, dim=prompt_embeds.shape[2]):
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
'''


# (file, old, new)
EDITS = [
    (T, ATTN_OLD, ATTN_NEW),
    (T, SDPA_OLD, SDPA_NEW),
    (P, STEP_PREP_OLD, STEP_PREP_NEW),
    (P, CFG_COMB_OLD, CFG_COMB_NEW),
    (P, CALLBACK_OLD, CALLBACK_NEW),
    (P, T5_OLD, T5_NEW),
    (S, SCHED_IDX_OLD, SCHED_IDX_NEW),
    (IP, PP_OLD, PP_NEW),
    (VP, PP_STACK_OLD, PP_STACK_NEW),
    (V, VAE_ENCODE_OLD, VAE_ENCODE_NEW),
    (V, VAE_ENC_FRAMES_OLD, VAE_ENC_FRAMES_NEW),
    (V, VAE_ENC_CHUNK_OLD, VAE_ENC_CHUNK_NEW),
    (V, TDEC_OLD, TDEC_NEW),
    (V, TENC_OLD, TENC_NEW),
    (V, BLEND_OLD, BLEND_NEW),
    (VAE, DGD_OLD, DGD_NEW),
]


def _ensure_import(src):
    if re.search(r"^import perfmark$", src, re.M):
        return src
    m = re.search(r"^(?:from|import) .*\n", src, re.M)
    pos = m.start() if m else 0
    return src[:pos] + "import perfmark\n" + src[pos:]


def main():
    root = os.path.abspath(sys.argv[1])
    undo = "--undo" in sys.argv
    files = sorted({e[0] for e in EDITS})

    if undo:
        for rel in files:
            full = os.path.join(root, rel)
            if os.path.exists(full + ".orig2"):
                shutil.move(full + ".orig2", full)
                print("restored", rel)
        return

    for rel in files:
        full = os.path.join(root, rel)
        if not os.path.exists(full + ".orig2"):
            shutil.copy(full, full + ".orig2")

    for rel, old, new in EDITS:
        full = os.path.join(root, rel)
        src = open(full).read()
        tag = re.search(r'perfmark\.region\("(\w+)"', new).group(1)
        if 'perfmark.region("%s"' % tag in src:
            print("already   %-40s %s" % (rel, tag))
            continue
        n = src.count(old)
        if n != 1:
            raise SystemExit("mark_more.py: anchor for %s in %s matched %d times" % (tag, rel, n))
        src = _ensure_import(src.replace(old, new))
        open(full, "w").write(src)
        print("marked    %-40s %s" % (rel, tag))


if __name__ == "__main__":
    main()
