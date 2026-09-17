"""Native-only semantic capture; its host timings are not performance results.

Takes inferix_runner.py arguments and saves every segment's latents, output and
streamed callback frames, including warmup. Copies occur inside execution only
in this separate validation workload.
"""
import json
from pathlib import Path
import sys

args=sys.argv[1:]
def option(name): return args[args.index(name)+1]
assert option('--role')=='native'
sys.path.insert(0,option('--tree'))
from compat import install
install()
import torch
from inferix.pipeline.self_forcing.pipeline import SelfForcingPipeline
original=SelfForcingPipeline._generate_segment_with_streaming
captures=[]
def capture(self,*a,**kw):
    # The public loop passes these arguments by keyword in the pinned checkout.
    callbacks=[]
    callback=kw.get('stream_callback')
    if callback is not None:
        def wrapped(frames):
            callbacks.append(frames.detach().cpu().clone())
            return callback(frames)
        kw['stream_callback']=wrapped
    result=original(self,*a,**kw)
    model=self.pipeline.vae.model
    state={key: all(x is None for x in getattr(model,key))
           for key in ('_feat_map','_enc_feat_map')}
    captures.append(dict(callbacks=callbacks,
                         outputs=[x.detach().cpu().clone() for x in result],
                         cache_empty=state))
    return result
SelfForcingPipeline._generate_segment_with_streaming=capture
from inferix_runner import main
main()
out=Path(option('--output'))
torch.save(captures,out/'validation.pt')
(out/'validation.json').write_text(json.dumps(dict(
    timing_valid=False,reason='extra tensor copies for separate semantic validation',
    segments=[dict(callback_shapes=[list(x.shape) for x in c['callbacks']],
                   output_shapes=[list(x.shape) for x in c['outputs']],cache_empty=c['cache_empty'])
              for c in captures]),indent=2)+'\n')
print('SEMANTIC_CAPTURE_DONE',out,flush=True)
