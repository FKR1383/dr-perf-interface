import argparse, pathlib, sys
from marker_probe import Probe
from workloads import run
p=argparse.ArgumentParser(); p.add_argument("--source-root",required=True); a=p.parse_args()
root=pathlib.Path(a.source_root); target=(root/'sqlglot/parser.py').resolve(); assert target.is_file(), target
sys.path.insert(0,str(root/"src")); sys.path.insert(0,str(root)); probe=Probe(); run('sqlglot')
loaded={pathlib.Path(m.__file__).resolve() for m in sys.modules.values() if getattr(m,"__file__",None)}
assert target in loaded, f"marked source was not loaded from supplied checkout: {target}"
probe.finish('lt-045')
