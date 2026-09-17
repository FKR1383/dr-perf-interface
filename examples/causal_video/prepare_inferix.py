"""Keep optional UI/network dependencies lazy for the local callback workload."""
import argparse
import difflib
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('tree', type=Path)
p.add_argument('--patch', type=Path, required=True)
a = p.parse_args()
path = a.tree/'inferix/core/media/__init__.py'
old = path.read_text()
imports = {
    'GradioStreamingBackend': 'gradio_streaming',
    'WebRTCStreamingBackend': 'webrtc_streaming',
    'RTMPStreamingBackend': 'rtmp_streaming',
    'InteractiveGradioBackend': 'interactive_gradio',
}
new = old
for name, module in imports.items():
    line = f'from inferix.core.media.{module} import {name}\n'
    assert new.count(line) == 1
    new = new.replace(line, '')
new += '\n\n_OPTIONAL_BACKENDS = ' + repr(imports) + '''

def __getattr__(name):
    if name not in _OPTIONAL_BACKENDS:
        raise AttributeError(name)
    import importlib
    value = getattr(importlib.import_module('.' + _OPTIONAL_BACKENDS[name], __name__), name)
    globals()[name] = value
    return value
'''
a.patch.write_text(''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                    fromfile='a/inferix/core/media/__init__.py', tofile='b/inferix/core/media/__init__.py')))
path.write_text(new)
