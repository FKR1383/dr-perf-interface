"""TEMPORARY nested probe markers for the Wan 2.1 host-tax decomposition.

    python mark_tax_probe.py                # insert into wan-tax
    python mark_tax_probe.py --undo         # restore the .probe_orig copies

Splits the four regions that carry a big shape-independent constant
(`denoise_step`, `transformer_forward`, `block`, `attn`) into their sub-steps.

Every probe region declares exactly ONE state, `n = MULT * <shape quantity>`,
because drperf's per-thread fast key cache compares the region and state-name
strings by POINTER (client/drperf.c:339-351), so two regions under the same root
with the same state COUNT and the same state VALUES are recorded as one key.
A distinct MULT per region makes the (count, value) signature unique:

    transformer_forward sub-steps   2..15  x seq_len
    block sub-steps                16..25  x seq_len
    self-attention sub-steps       26..34  x seq_len
    cross-attention sub-steps      66..74  x seq_len   (own region names too)
    denoise_step sub-steps        128..768 x seq_len   (= 2..12 x latents.numel())

`latents.numel() == 64 * seq_len` at batch 1, so the pipeline band starts at 128
and cannot meet the 2..74 band.  Multiplying the state by a constant leaves the
derived INTERCEPT exact (cost = a*(M*s) + b) and only rescales the slope.

Each of the four regions also gets a `*_null` probe wrapping `pass`, so the cost
of opening one probe marker can be subtracted from the others.
"""
import os
import shutil
import sys

ROOT = "/home/ubuntu/drperf-cases/videogen/wan-tax/diffusers"
P = os.path.join(ROOT, "pipelines/wan/pipeline_wan.py")
T = os.path.join(ROOT, "models/transformers/transformer_wan.py")

EDITS = []          # (path, old, new)


def edit(path, old, new):
    EDITS.append((path, old, new))


# --------------------------------------------------------------- pipeline
edit(P, '''                    with perfmark.region("denoise_step", batch=latents.shape[0], frames=latents.shape[2], height=latents.shape[3], width=latents.shape[4]):
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
                            with perfmark.region("cfg", frames=latents.shape[2], height=latents.shape[3], width=latents.shape[4], numel=latents.numel()):
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
''', '''                    with perfmark.region("denoise_step", batch=latents.shape[0], frames=latents.shape[2], height=latents.shape[3], width=latents.shape[4]):
                        _nn = latents.numel()
                        with perfmark.region("ds_null", n=12 * _nn):
                            pass
                        with perfmark.region("ds_setup", n=2 * _nn):
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

                        with perfmark.region("ds_input", n=3 * _nn):
                            latent_model_input = latents.to(transformer_dtype)
                        with perfmark.region("ds_timestep", n=4 * _nn):
                            if self.config.expand_timesteps:
                                # seq_len: num_latent_frames * latent_height//2 * latent_width//2
                                temp_ts = (mask[0][0][:, ::2, ::2] * t).flatten()
                                # batch_size, seq_len
                                timestep = temp_ts.unsqueeze(0).expand(latents.shape[0], -1)
                            else:
                                timestep = t.expand(latents.shape[0])

                        with perfmark.region("ds_cond", n=5 * _nn):
                            with current_model.cache_context("cond"):
                                noise_pred = current_model(
                                    hidden_states=latent_model_input,
                                    timestep=timestep,
                                    encoder_hidden_states=prompt_embeds,
                                    attention_kwargs=attention_kwargs,
                                    return_dict=False,
                                )[0]

                        if self.do_classifier_free_guidance:
                            with perfmark.region("cfg", frames=latents.shape[2], height=latents.shape[3], width=latents.shape[4], numel=latents.numel()):
                                with perfmark.region("ds_uncond", n=6 * _nn):
                                    with current_model.cache_context("uncond"):
                                        noise_uncond = current_model(
                                            hidden_states=latent_model_input,
                                            timestep=timestep,
                                            encoder_hidden_states=negative_prompt_embeds,
                                            attention_kwargs=attention_kwargs,
                                            return_dict=False,
                                        )[0]
                                with perfmark.region("ds_combine", n=7 * _nn):
                                    noise_pred = noise_uncond + current_guidance_scale * (noise_pred - noise_uncond)

                        # compute the previous noisy sample x_t -> x_t-1
                        with perfmark.region("ds_sched", n=8 * _nn):
                            latents = self.scheduler.step(noise_pred, t, latents, return_dict=False)[0]

                        with perfmark.region("ds_callback", n=9 * _nn):
                            if callback_on_step_end is not None:
                                callback_kwargs = {}
                                for k in callback_on_step_end_tensor_inputs:
                                    callback_kwargs[k] = locals()[k]
                                callback_outputs = callback_on_step_end(self, i, t, callback_kwargs)

                                latents = callback_outputs.pop("latents", latents)
                                prompt_embeds = callback_outputs.pop("prompt_embeds", prompt_embeds)
                                negative_prompt_embeds = callback_outputs.pop("negative_prompt_embeds", negative_prompt_embeds)

                        # call the callback, if provided
                        with perfmark.region("ds_progress", n=10 * _nn):
                            if i == len(timesteps) - 1 or ((i + 1) > num_warmup_steps and (i + 1) % self.scheduler.order == 0):
                                progress_bar.update()

                        with perfmark.region("ds_xla", n=11 * _nn):
                            if XLA_AVAILABLE:
                                xm.mark_step()
''')

# --------------------------------------------------------------- attention processor
edit(T, '''class WanAttnProcessor:
    _attention_backend = None''', '''# probe-only: one name set per attention kind, so the self- and cross-attention
# sub-steps do not land in one region (they have different work).
_AT_NAMES = (
    ("at_null", "at_img", "at_qkv", "at_qknorm", "at_unflat", "at_rope", "at_sdpa", "at_flat", "at_out"),
    ("ax_null", "ax_img", "ax_qkv", "ax_qknorm", "ax_unflat", "ax_rope", "ax_sdpa", "ax_flat", "ax_out"),
)


class WanAttnProcessor:
    _attention_backend = None''')

edit(T, '''        with perfmark.region("attn", batch=hidden_states.shape[0], seq_len=hidden_states.shape[1], heads=attn.heads, kv_len=(hidden_states.shape[1] if encoder_hidden_states is None else encoder_hidden_states.shape[1])):
            encoder_hidden_states_img = None
            if attn.add_k_proj is not None:
                # 512 is the context length of the text encoder, hardcoded for now
                image_context_length = encoder_hidden_states.shape[1] - 512
                encoder_hidden_states_img = encoder_hidden_states[:, :image_context_length]
                encoder_hidden_states = encoder_hidden_states[:, image_context_length:]

            query, key, value = _get_qkv_projections(attn, hidden_states, encoder_hidden_states)

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

            # I2V task
            hidden_states_img = None
            if encoder_hidden_states_img is not None:
                key_img, value_img = _get_added_kv_projections(attn, encoder_hidden_states_img)
                key_img = attn.norm_added_k(key_img)

                key_img = key_img.unflatten(2, (attn.heads, -1))
                value_img = value_img.unflatten(2, (attn.heads, -1))

                hidden_states_img = dispatch_attention_fn(
                    query,
                    key_img,
                    value_img,
                    attn_mask=None,
                    dropout_p=0.0,
                    is_causal=False,
                    backend=self._attention_backend,
                    # Reference: https://github.com/huggingface/diffusers/pull/12909
                    parallel_config=None,
                )
                hidden_states_img = hidden_states_img.flatten(2, 3)
                hidden_states_img = hidden_states_img.type_as(query)

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
            hidden_states = hidden_states.flatten(2, 3)
            hidden_states = hidden_states.type_as(query)

            if hidden_states_img is not None:
                hidden_states = hidden_states + hidden_states_img

            hidden_states = attn.to_out[0](hidden_states)
            hidden_states = attn.to_out[1](hidden_states)
            return hidden_states
''', '''        with perfmark.region("attn", batch=hidden_states.shape[0], seq_len=hidden_states.shape[1], heads=attn.heads, kv_len=(hidden_states.shape[1] if encoder_hidden_states is None else encoder_hidden_states.shape[1])):
            _x = 0 if encoder_hidden_states is None else 1
            _nm = _AT_NAMES[_x]
            _s = hidden_states.shape[1] * (1 + 39 * _x)
            with perfmark.region(_nm[0], n=34 * _s):
                pass
            with perfmark.region(_nm[1], n=26 * _s):
                encoder_hidden_states_img = None
                if attn.add_k_proj is not None:
                    # 512 is the context length of the text encoder, hardcoded for now
                    image_context_length = encoder_hidden_states.shape[1] - 512
                    encoder_hidden_states_img = encoder_hidden_states[:, :image_context_length]
                    encoder_hidden_states = encoder_hidden_states[:, image_context_length:]

            with perfmark.region(_nm[2], n=27 * _s):
                query, key, value = _get_qkv_projections(attn, hidden_states, encoder_hidden_states)

            with perfmark.region(_nm[3], n=28 * _s):
                query = attn.norm_q(query)
                key = attn.norm_k(key)

            with perfmark.region(_nm[4], n=29 * _s):
                query = query.unflatten(2, (attn.heads, -1))
                key = key.unflatten(2, (attn.heads, -1))
                value = value.unflatten(2, (attn.heads, -1))

            with perfmark.region(_nm[5], n=30 * _s):
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

            # I2V task
            with perfmark.region(_nm[6], n=31 * _s):
                hidden_states_img = None
                if encoder_hidden_states_img is not None:
                    key_img, value_img = _get_added_kv_projections(attn, encoder_hidden_states_img)
                    key_img = attn.norm_added_k(key_img)

                    key_img = key_img.unflatten(2, (attn.heads, -1))
                    value_img = value_img.unflatten(2, (attn.heads, -1))

                    hidden_states_img = dispatch_attention_fn(
                        query,
                        key_img,
                        value_img,
                        attn_mask=None,
                        dropout_p=0.0,
                        is_causal=False,
                        backend=self._attention_backend,
                        # Reference: https://github.com/huggingface/diffusers/pull/12909
                        parallel_config=None,
                    )
                    hidden_states_img = hidden_states_img.flatten(2, 3)
                    hidden_states_img = hidden_states_img.type_as(query)

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
            with perfmark.region(_nm[7], n=32 * _s):
                hidden_states = hidden_states.flatten(2, 3)
                hidden_states = hidden_states.type_as(query)

                if hidden_states_img is not None:
                    hidden_states = hidden_states + hidden_states_img

            with perfmark.region(_nm[8], n=33 * _s):
                hidden_states = attn.to_out[0](hidden_states)
                hidden_states = attn.to_out[1](hidden_states)
            return hidden_states
''')

# --------------------------------------------------------------- transformer block
edit(T, '''        with perfmark.region("block", batch=hidden_states.shape[0], seq_len=hidden_states.shape[1], text_len=encoder_hidden_states.shape[1]):
            if temb.ndim == 4:
                # temb: batch_size, seq_len, 6, inner_dim (wan2.2 ti2v)
                shift_msa, scale_msa, gate_msa, c_shift_msa, c_scale_msa, c_gate_msa = (
                    self.scale_shift_table.unsqueeze(0) + temb.float()
                ).chunk(6, dim=2)
                # batch_size, seq_len, 1, inner_dim
                shift_msa = shift_msa.squeeze(2)
                scale_msa = scale_msa.squeeze(2)
                gate_msa = gate_msa.squeeze(2)
                c_shift_msa = c_shift_msa.squeeze(2)
                c_scale_msa = c_scale_msa.squeeze(2)
                c_gate_msa = c_gate_msa.squeeze(2)
            else:
                # temb: batch_size, 6, inner_dim (wan2.1/wan2.2 14B)
                shift_msa, scale_msa, gate_msa, c_shift_msa, c_scale_msa, c_gate_msa = (
                    self.scale_shift_table + temb.float()
                ).chunk(6, dim=1)

            # 1. Self-attention
            norm_hidden_states = (self.norm1(hidden_states.float()) * (1 + scale_msa) + shift_msa).type_as(hidden_states)
            attn_output = self.attn1(norm_hidden_states, None, None, rotary_emb)
            hidden_states = (hidden_states.float() + attn_output * gate_msa).type_as(hidden_states)

            # 2. Cross-attention
            norm_hidden_states = self.norm2(hidden_states.float()).type_as(hidden_states)
            attn_output = self.attn2(norm_hidden_states, encoder_hidden_states, None, None)
            hidden_states = hidden_states + attn_output

            # 3. Feed-forward
            norm_hidden_states = (self.norm3(hidden_states.float()) * (1 + c_scale_msa) + c_shift_msa).type_as(
                hidden_states
            )
            ff_output = self.ffn(norm_hidden_states)
            hidden_states = (hidden_states.float() + ff_output.float() * c_gate_msa).type_as(hidden_states)

            return hidden_states
''', '''        with perfmark.region("block", batch=hidden_states.shape[0], seq_len=hidden_states.shape[1], text_len=encoder_hidden_states.shape[1]):
            _s = hidden_states.shape[1]
            with perfmark.region("bl_null", n=35 * _s):
                pass
            with perfmark.region("bl_mod", n=16 * _s):
                if temb.ndim == 4:
                    # temb: batch_size, seq_len, 6, inner_dim (wan2.2 ti2v)
                    shift_msa, scale_msa, gate_msa, c_shift_msa, c_scale_msa, c_gate_msa = (
                        self.scale_shift_table.unsqueeze(0) + temb.float()
                    ).chunk(6, dim=2)
                    # batch_size, seq_len, 1, inner_dim
                    shift_msa = shift_msa.squeeze(2)
                    scale_msa = scale_msa.squeeze(2)
                    gate_msa = gate_msa.squeeze(2)
                    c_shift_msa = c_shift_msa.squeeze(2)
                    c_scale_msa = c_scale_msa.squeeze(2)
                    c_gate_msa = c_gate_msa.squeeze(2)
                else:
                    # temb: batch_size, 6, inner_dim (wan2.1/wan2.2 14B)
                    shift_msa, scale_msa, gate_msa, c_shift_msa, c_scale_msa, c_gate_msa = (
                        self.scale_shift_table + temb.float()
                    ).chunk(6, dim=1)

            # 1. Self-attention
            with perfmark.region("bl_norm1", n=17 * _s):
                norm_hidden_states = (self.norm1(hidden_states.float()) * (1 + scale_msa) + shift_msa).type_as(hidden_states)
            with perfmark.region("bl_attn1", n=18 * _s):
                attn_output = self.attn1(norm_hidden_states, None, None, rotary_emb)
            with perfmark.region("bl_res1", n=19 * _s):
                hidden_states = (hidden_states.float() + attn_output * gate_msa).type_as(hidden_states)

            # 2. Cross-attention
            with perfmark.region("bl_norm2", n=20 * _s):
                norm_hidden_states = self.norm2(hidden_states.float()).type_as(hidden_states)
            with perfmark.region("bl_attn2", n=21 * _s):
                attn_output = self.attn2(norm_hidden_states, encoder_hidden_states, None, None)
            with perfmark.region("bl_res2", n=22 * _s):
                hidden_states = hidden_states + attn_output

            # 3. Feed-forward
            with perfmark.region("bl_norm3", n=23 * _s):
                norm_hidden_states = (self.norm3(hidden_states.float()) * (1 + c_scale_msa) + c_shift_msa).type_as(
                    hidden_states
                )
            with perfmark.region("bl_ffn", n=24 * _s):
                ff_output = self.ffn(norm_hidden_states)
            with perfmark.region("bl_res3", n=25 * _s):
                hidden_states = (hidden_states.float() + ff_output.float() * c_gate_msa).type_as(hidden_states)

            return hidden_states
''')

# --------------------------------------------------------------- transformer forward
edit(T, '''            batch_size, num_channels, num_frames, height, width = hidden_states.shape
            p_t, p_h, p_w = self.config.patch_size
            post_patch_num_frames = num_frames // p_t
            post_patch_height = height // p_h
            post_patch_width = width // p_w

            rotary_emb = self.rope(hidden_states)

            hidden_states = self.patch_embedding(hidden_states)
            hidden_states = hidden_states.flatten(2).transpose(1, 2)

            # flatten+transpose produces a non-contiguous tensor; make it contiguous before the block loop.
            hidden_states = hidden_states.contiguous()

            # timestep shape: batch_size, or batch_size, seq_len (wan 2.2 ti2v)
            if timestep.ndim == 2:
                ts_seq_len = timestep.shape[1]
                timestep = timestep.flatten()  # batch_size * seq_len
            else:
                ts_seq_len = None

            temb, timestep_proj, encoder_hidden_states, encoder_hidden_states_image = self.condition_embedder(
                timestep, encoder_hidden_states, encoder_hidden_states_image, timestep_seq_len=ts_seq_len
            )
            if ts_seq_len is not None:
                # batch_size, seq_len, 6, inner_dim
                timestep_proj = timestep_proj.unflatten(2, (6, -1))
            else:
                # batch_size, 6, inner_dim
                timestep_proj = timestep_proj.unflatten(1, (6, -1))

            if encoder_hidden_states_image is not None:
                encoder_hidden_states = torch.concat([encoder_hidden_states_image, encoder_hidden_states], dim=1)

            # 4. Transformer blocks
            if torch.is_grad_enabled() and self.gradient_checkpointing:
                for block in self.blocks:
                    hidden_states = self._gradient_checkpointing_func(
                        block, hidden_states, encoder_hidden_states, timestep_proj, rotary_emb
                    )
            else:
                for block in self.blocks:
                    hidden_states = block(hidden_states, encoder_hidden_states, timestep_proj, rotary_emb)

            # 5. Output norm, projection & unpatchify
            if temb.ndim == 3:
                # batch_size, seq_len, inner_dim (wan 2.2 ti2v)
                shift, scale = (self.scale_shift_table.unsqueeze(0).to(temb.device) + temb.unsqueeze(2)).chunk(2, dim=2)
                shift = shift.squeeze(2)
                scale = scale.squeeze(2)
            else:
                # batch_size, inner_dim
                shift, scale = (self.scale_shift_table.to(temb.device) + temb.unsqueeze(1)).chunk(2, dim=1)

            # Move the shift and scale tensors to the same device as hidden_states.
            # When using multi-GPU inference via accelerate these will be on the
            # first device rather than the last device, which hidden_states ends up
            # on.
            shift = shift.to(hidden_states.device)
            scale = scale.to(hidden_states.device)

            hidden_states = (self.norm_out(hidden_states.float()) * (1 + scale) + shift).type_as(hidden_states)
            hidden_states = self.proj_out(hidden_states)

            hidden_states = hidden_states.reshape(
                batch_size, post_patch_num_frames, post_patch_height, post_patch_width, p_t, p_h, p_w, -1
            )
            hidden_states = hidden_states.permute(0, 7, 1, 4, 2, 5, 3, 6)
            output = hidden_states.flatten(6, 7).flatten(4, 5).flatten(2, 3)

            if not return_dict:
                return (output,)

            return Transformer2DModelOutput(sample=output)
''', '''            _sq = ((hidden_states.shape[2] // self.config.patch_size[0])
                   * (hidden_states.shape[3] // self.config.patch_size[1])
                   * (hidden_states.shape[4] // self.config.patch_size[2]))
            with perfmark.region("tf_null", n=36 * _sq):
                pass
            with perfmark.region("tf_shape", n=2 * _sq):
                batch_size, num_channels, num_frames, height, width = hidden_states.shape
                p_t, p_h, p_w = self.config.patch_size
                post_patch_num_frames = num_frames // p_t
                post_patch_height = height // p_h
                post_patch_width = width // p_w

            with perfmark.region("tf_rope", n=3 * _sq):
                rotary_emb = self.rope(hidden_states)

            with perfmark.region("tf_patch", n=4 * _sq):
                hidden_states = self.patch_embedding(hidden_states)
            with perfmark.region("tf_flatten", n=5 * _sq):
                hidden_states = hidden_states.flatten(2).transpose(1, 2)

            # flatten+transpose produces a non-contiguous tensor; make it contiguous before the block loop.
            with perfmark.region("tf_contig", n=6 * _sq):
                hidden_states = hidden_states.contiguous()

            # timestep shape: batch_size, or batch_size, seq_len (wan 2.2 ti2v)
            with perfmark.region("tf_tsdim", n=7 * _sq):
                if timestep.ndim == 2:
                    ts_seq_len = timestep.shape[1]
                    timestep = timestep.flatten()  # batch_size * seq_len
                else:
                    ts_seq_len = None

            with perfmark.region("tf_cond", n=8 * _sq):
                temb, timestep_proj, encoder_hidden_states, encoder_hidden_states_image = self.condition_embedder(
                    timestep, encoder_hidden_states, encoder_hidden_states_image, timestep_seq_len=ts_seq_len
                )
            with perfmark.region("tf_unflat", n=9 * _sq):
                if ts_seq_len is not None:
                    # batch_size, seq_len, 6, inner_dim
                    timestep_proj = timestep_proj.unflatten(2, (6, -1))
                else:
                    # batch_size, 6, inner_dim
                    timestep_proj = timestep_proj.unflatten(1, (6, -1))

                if encoder_hidden_states_image is not None:
                    encoder_hidden_states = torch.concat([encoder_hidden_states_image, encoder_hidden_states], dim=1)

            # 4. Transformer blocks
            with perfmark.region("tf_blocks", n=10 * _sq):
                if torch.is_grad_enabled() and self.gradient_checkpointing:
                    for block in self.blocks:
                        hidden_states = self._gradient_checkpointing_func(
                            block, hidden_states, encoder_hidden_states, timestep_proj, rotary_emb
                        )
                else:
                    for block in self.blocks:
                        hidden_states = block(hidden_states, encoder_hidden_states, timestep_proj, rotary_emb)

            # 5. Output norm, projection & unpatchify
            with perfmark.region("tf_shift", n=11 * _sq):
                if temb.ndim == 3:
                    # batch_size, seq_len, inner_dim (wan 2.2 ti2v)
                    shift, scale = (self.scale_shift_table.unsqueeze(0).to(temb.device) + temb.unsqueeze(2)).chunk(2, dim=2)
                    shift = shift.squeeze(2)
                    scale = scale.squeeze(2)
                else:
                    # batch_size, inner_dim
                    shift, scale = (self.scale_shift_table.to(temb.device) + temb.unsqueeze(1)).chunk(2, dim=1)

                # Move the shift and scale tensors to the same device as hidden_states.
                # When using multi-GPU inference via accelerate these will be on the
                # first device rather than the last device, which hidden_states ends up
                # on.
                shift = shift.to(hidden_states.device)
                scale = scale.to(hidden_states.device)

            with perfmark.region("tf_normout", n=12 * _sq):
                hidden_states = (self.norm_out(hidden_states.float()) * (1 + scale) + shift).type_as(hidden_states)
            with perfmark.region("tf_projout", n=13 * _sq):
                hidden_states = self.proj_out(hidden_states)

            with perfmark.region("tf_unpatch", n=14 * _sq):
                hidden_states = hidden_states.reshape(
                    batch_size, post_patch_num_frames, post_patch_height, post_patch_width, p_t, p_h, p_w, -1
                )
                hidden_states = hidden_states.permute(0, 7, 1, 4, 2, 5, 3, 6)
                output = hidden_states.flatten(6, 7).flatten(4, 5).flatten(2, 3)

            with perfmark.region("tf_ret", n=15 * _sq):
                if not return_dict:
                    _ret = (output,)
                else:
                    _ret = Transformer2DModelOutput(sample=output)
            return _ret
''')


def main():
    undo = "--undo" in sys.argv
    paths = sorted({p for p, _, _ in EDITS})
    if undo:
        for p in paths:
            if os.path.exists(p + ".probe_orig"):
                shutil.move(p + ".probe_orig", p)
                print("restored", p)
        return
    for p in paths:
        if not os.path.exists(p + ".probe_orig"):
            shutil.copy(p, p + ".probe_orig")
    for p, old, new in EDITS:
        src = open(p).read()
        if new in src:
            print("already", p, old.splitlines()[0][:60])
            continue
        if src.count(old) != 1:
            raise SystemExit("mark_tax_probe.py: anchor matched %d times in %s:\n%s"
                             % (src.count(old), p, old[:200]))
        open(p, "w").write(src.replace(old, new))
        print("probed  ", os.path.basename(p), "<-", old.splitlines()[0].strip()[:70])


if __name__ == "__main__":
    main()
