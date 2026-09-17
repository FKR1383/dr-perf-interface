"""Reviewed neutral exports for the first three pilot workloads."""
import ast
import io
import json
import shutil
import subprocess
import tarfile
from pathlib import Path

SPECS = {
    'sqlglot': {'repo': 'oss/sqlglot-src', 'revision': '2e86ded7d0f6474e9041882058358616fb911464',
                'package': 'sqlglot', 'driver': 'oss/run_sqlglot.py',
                'python': 'oss-venv/bin/python', 'defaults': [{'n_joins': n} for n in (4, 8, 12, 16, 24, 32)]},
    'wan_a': {'repo': 'videogen/diffusers', 'revision': 'c5469b7ceb606edd7ba6570dcd17d38590a18db6',
              'package': 'src/diffusers', 'driver': 'videogen/run_tiny.py',
              'python': 'videogen/.venv/bin/python',
              'defaults': [{'hw': h, 'frames': f, 'steps': s, 'text': 16} for h,f,s in
                           [(32,5,2),(32,9,2),(64,5,2),(64,9,2),(32,5,4),(64,5,4)]]},
    'vllm_b': {'repo': '@drperf/third_party/vllm-cpu/vllm',
               'revision': '2cf0a6915ce544dc493a0990f2ea38d81601128a',
               'package': 'vllm', 'driver': 'examples/vllm_run_req.py',
               'python': '@drperf/third_party/vllm-cpu/.venv/bin/python',
               'defaults': [{'reqs': 4, 'passes': '4,4', 'max_tokens': 1}]},
}


class NeutralDriver(ast.NodeTransformer):
    # Applied only to the three audited drivers above. This is not a generic
    # leakage detector: archive drivers containing optimized variants need
    # separate review and adapters.
    def visit_Expr(self, node):
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return None  # old measurement commentary/docstrings
        return self.generic_visit(node)

    def visit_Import(self, node):
        for name in node.names:
            if name.name == 'perfmark':
                name.name, name.asname = 'bench_support', None
        return node

    def visit_Attribute(self, node):
        if ast.unparse(node) == 'perfmark.states':
            node.value = ast.Name(id='bench_support', ctx=ast.Load())
        return self.generic_visit(node)

    def visit_With(self, node):
        if len(node.items) == 1 and isinstance(node.items[0].context_expr, ast.Call):
            call = node.items[0].context_expr
            if ast.unparse(call.func) == 'perfmark.region':
                return [self.visit(n) for n in node.body]
        return self.generic_visit(node)

    def visit_Assign(self, node):
        names = [ast.unparse(t) for t in node.targets]
        if names == ['_SRC']:
            node.value = ast.parse("os.environ['BENCH_SOURCE']", mode='eval').body
        if names == ['_HF']:
            node.value = ast.parse("os.environ['HF_HOME']", mode='eval').body
        return self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute) and ast.unparse(node.func) == 'sys.path.insert':
            if any(isinstance(a, ast.Constant) and isinstance(a.value, str) and '/home/ubuntu/' in a.value for a in node.args):
                return ast.Constant(None)
        # An import assertion is retained but historical wording is neutralized.
        for arg in ast.walk(node):
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                arg.value = arg.value.replace('marked copy', 'prepared source')
        return self.generic_visit(node)


def prepare(case, destination, archive, drperf, condition, track='discovery'):
    spec = SPECS[case]
    if track == 'small-to-large' and case != 'sqlglot':
        raise ValueError('the small-to-large pilot currently has a reviewed input envelope only for sqlglot')
    if destination.exists():
        raise ValueError('destination already exists; use a fresh workspace for each condition')
    def resolve(path):
        return drperf / path[len('@drperf/'):] if path.startswith('@drperf/') else archive / path
    repo, python = resolve(spec['repo']), resolve(spec['python'])
    if not python.exists():
        raise ValueError(f'missing environment: {python}')
    data = subprocess.check_output(['git', '-C', str(repo), 'archive', spec['revision'], spec['package']])
    destination.mkdir(parents=True)
    source = destination/'source'
    source.mkdir()
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        tar.extractall(source, filter='data')
    for license_name in ('LICENSE', 'LICENSE.md', 'LICENSE.txt', 'NOTICE'):
        proc = subprocess.run(['git','-C',str(repo),'show',spec['revision']+':'+license_name], capture_output=True)
        if proc.returncode == 0:
            (source/license_name).write_bytes(proc.stdout)
    package = source/spec['package']
    if case == 'vllm_b':
        for binary in (repo/'vllm').glob('*.so'):
            shutil.copy2(binary, package/binary.name)
    # Use the checked-in evidence snapshot, not a mutable archived driver.
    benchmark = Path(__file__).resolve().parents[1]
    raw = (benchmark/'cases'/case/'reference'/'assets'/spec['driver']).read_text()
    tree = ast.fix_missing_locations(NeutralDriver().visit(ast.parse(raw)))
    driver = ast.unparse(tree)+'\n'
    if '/home/ubuntu/' in driver or 'perfmark.region' in driver:
        raise ValueError('driver still contains historical paths or solved markers')
    (destination/'workload.py').write_text(driver)
    shutil.copy2(benchmark/'cases'/case/'task.md', destination/'TASK.md')
    (destination/'bench_support.py').write_text('''import sys

def states(**defaults):
    for arg in sys.argv[1:]:
        key, sep, value = arg.partition('=')
        if not sep or key not in defaults:
            raise ValueError('unknown workload argument: ' + arg)
        defaults[key] = type(defaults[key])(value)
    return defaults
''')
    env = {'PYTHONPATH': str(package.parent), 'BENCH_SOURCE': str(package if case == 'vllm_b' else package.parent),
           'HF_HOME': str(drperf/'third_party/hf'), 'HF_HUB_OFFLINE': '1',
           'OMP_NUM_THREADS': '4', 'MKL_NUM_THREADS': '4', 'OPENBLAS_NUM_THREADS': '4',
           'PYTHONHASHSEED': '0', 'TOKENIZERS_PARALLELISM': 'false',
           'VLLM_CPU_OMP_THREADS_BIND': 'all'}
    session = {'schema_version':1, 'case':case, 'condition':condition, 'track':track,
               'python':str(python.absolute()), 'workload':'workload.py', 'env':env,
               'source_revision':spec['revision'], 'round_budget':3, 'points_per_round':6,
               'process_timeout_seconds':300,
               'note':'Supervisor configuration, not a filesystem security boundary.'}
    if track == 'small-to-large':
        session['input_envelope'] = {'n_joins': {'min':2, 'max':32}}
        with (destination/'TASK.md').open('a') as task:
            task.write('\nOnly small inputs are available: n_joins must be an explicit integer '
                       'between 2 and 32. Predict the cost dependencies at larger sizes and '
                       'state where you expect that prediction to stop applying. The evaluator '
                       'will check larger inputs after your final answer is frozen.\n')
    (destination/'session.json').write_text(json.dumps(session,indent=2)+'\n')
    versions = subprocess.check_output([str(python.absolute()), '-c',
        'import importlib.metadata as m, json; print(json.dumps(sorted((d.metadata["Name"],d.version) for d in m.distributions())))'],text=True)
    (destination/'dependencies.json').write_text(versions)
    (destination/'plan.json').write_text(json.dumps(spec['defaults'],indent=2)+'\n')
    (destination/'hypothesis.json').write_text(json.dumps({'claims':[], 'experiment':'Initial measurement'},indent=2)+'\n')
    return session
