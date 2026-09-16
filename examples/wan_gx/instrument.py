"""Matched region boundaries for real Wan calls; no GPU values become PCVs."""
import functools
import inspect
import perfmark


def install(pipe):
    import wan.text2video as pipeline
    import wan.modules.model as model
    import wan.modules.vae as vae
    import wan.modules.t5 as t5
    import wan.modules.tokenizers as tokens
    import wan.utils.fm_solvers_unipc as scheduler
    regions=[]
    module_counts={id(pipe.model):len(tuple(pipe.model.modules())),
                   id(pipe.vae.model):len(tuple(pipe.vae.model.modules()))}
    def wrap(owner, method, name, features):
        original=getattr(owner,method)
        signature=inspect.signature(original)
        @functools.wraps(original)
        def measured(*args,**kwargs):
            arguments=signature.bind(*args,**kwargs).arguments
            pcvs=features(arguments)
            with perfmark.region(name,**pcvs): return original(*args,**kwargs)
        setattr(owner,method,measured)
        regions.append(name)
    def tensor(a):
        x=a.get('x',a.get('ids',a.get('z')))
        return {'elements':x.numel()}
    wrap(pipeline.WanT2V,'generate','wan_generate',lambda a:{'frames':a.get('frame_num',81),'steps':a.get('sampling_steps',50)})
    wrap(model.WanModel,'forward','wan_transformer',lambda a:{'tokens':a['seq_len']})
    wrap(model.WanModel,'to','wan_model_to',lambda a:{'modules':module_counts[id(a['self'])]})
    for cls,name in [(model.WanAttentionBlock,'wan_block'),(model.WanSelfAttention,'wan_self_attention'),
                     (model.WanT2VCrossAttention,'wan_cross_attention'),(model.Head,'wan_head'),
                     (model.WanRMSNorm,'wan_rms_norm'),(model.WanLayerNorm,'wan_layer_norm')]:
        wrap(cls,'forward',name,tensor)
    wrap(model,'rope_apply','wan_rope_apply',tensor)
    wrap(model,'sinusoidal_embedding_1d','wan_time_embedding',lambda a:{'batch':a['position'].numel()})
    wrap(model,'flash_attention','wan_flash_attention',lambda a:{'q_tokens':a['q'].shape[1],'k_tokens':a['k'].shape[1]})
    wrap(t5.T5EncoderModel,'__call__','wan_encode_text',lambda a:{'chars':sum(map(len,a['texts']))})
    wrap(tokens.HuggingfaceTokenizer,'__call__','wan_tokenize',lambda a:{'chars':sum(map(len,a['sequence'])) if not isinstance(a['sequence'],str) else len(a['sequence'])})
    for cls,name in [(t5.T5Encoder,'wan_t5_encoder'),(t5.T5Attention,'wan_t5_attention'),(t5.T5FeedForward,'wan_t5_ffn')]:
        wrap(cls,'forward',name,tensor)
    wrap(scheduler.FlowUniPCMultistepScheduler,'step','wan_scheduler',lambda a:{'step':a['self'].step_index or 0})
    wrap(vae.WanVAE_,'decode','wan_vae_decode',tensor)
    wrap(vae.WanVAE_,'clear_cache','wan_vae_clear_cache',lambda a:{'modules':module_counts[id(a['self'])]})
    for cls,name in [(vae.Decoder3d,'wan_vae_decoder'),(vae.ResidualBlock,'wan_vae_residual'),
                     (vae.Resample,'wan_vae_resample'),(vae.CausalConv3d,'wan_vae_conv'),(vae.AttentionBlock,'wan_vae_attention')]:
        wrap(cls,'forward',name,tensor)
    return regions
