"""Compatibility for torchvision's removed video writer; model math is unchanged."""
def install():
    import torchvision.io
    if not hasattr(torchvision.io, 'write_video'):
        def write_video(filename, video_array, fps, video_codec='libx264', options=None, **kwargs):
            if kwargs:
                raise NotImplementedError(f'Unsupported writer options: {kwargs}')
            import imageio.v2 as imageio
            imageio.mimwrite(filename, video_array.cpu().numpy(), fps=float(fps), codec=video_codec,
                            ffmpeg_params=[part for pair in (options or {}).items()
                                           for part in ('-' + pair[0], str(pair[1]))])
        torchvision.io.write_video = write_video


def install_inferix_loader():
    """Resolve Diffusers' newly reserved parallel_config argument for one GPU.

    Inferix uses its own ParallelConfig class. New Diffusers consumes the
    constructor keyword and calls enable_parallelism with that incompatible
    class. Restore it to the model and attention modules after loading; their
    single-device constructors already select the same attention implementation.
    """
    import functools
    import os
    import zipfile
    import torch
    original_load = torch.load
    @functools.wraps(original_load)
    def load_mapped(path, *args, **kwargs):
        # Avoid duplicate anonymous checkpoint buffers during setup. Copying
        # into the unchanged model/state_dict still follows upstream semantics.
        if isinstance(path, (str, os.PathLike)) and zipfile.is_zipfile(path):
            kwargs.setdefault('mmap', True)
        return original_load(path, *args, **kwargs)
    torch.load = load_mapped
    from inferix.models.self_forcing.causal_model import CausalWanModel
    from inferix.models.wan_base.utils.parallel_config import ParallelConfig
    original = CausalWanModel.enable_parallelism
    def enable_parallelism(self, config):
        if not isinstance(config, ParallelConfig):
            return original(self, config)
        assert config.world_size == config.ulysses_size == config.ring_size == 1
        for module in self.modules():
            if hasattr(module, 'parallel_config'):
                module.parallel_config = config
    CausalWanModel.enable_parallelism = enable_parallelism
