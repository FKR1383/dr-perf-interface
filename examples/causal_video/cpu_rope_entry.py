"""Run the frozen Inferix workload, then record opt-in RoPE cache metadata."""
import json
import os
from pathlib import Path
import sys


def _option(name):
    try:
        return sys.argv[sys.argv.index(name) + 1]
    except (ValueError, IndexError) as exc:
        raise SystemExit(f'missing {name}') from exc


def main():
    output = Path(_option('--output'))
    from inferix_runner import main as run_inferix
    run_inferix()

    # All workload timers and profiling gates are closed when main returns.
    report_path = output / 'report.json'
    report = json.loads(report_path.read_text())
    causal_model = sys.modules.get('inferix.models.self_forcing.causal_model')
    stats = (causal_model.rope_frequency_cache_stats()
             if causal_model is not None and hasattr(causal_model, 'rope_frequency_cache_stats')
             else None)
    requested = os.environ.get('INFERIX_ROPE_FREQ_CACHE') == '1'
    if requested and (stats is None or not stats['enabled']):
        raise RuntimeError('RoPE cache was requested but is absent from the selected Inferix tree')
    report.setdefault('optimizations', {})['rope_frequency_cache'] = dict(
        requested=requested,
        stats=stats,
    )
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    print('INFERIX_ROPE_CACHE', json.dumps(report['optimizations']['rope_frequency_cache']), flush=True)


if __name__ == '__main__':
    main()
