"""Score reviewed submissions and compare complete timing/drperf pairs.

Judgments are evaluator-only. Semantic review is explicit: this does not pretend
that matching PCV names establishes correct discovery.
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def score_session(session, answers):
    case = session['case']
    required = {f['id'] for f in answers[case]['factors']}
    if not required:
        raise ValueError(f'{case}: no reviewed reference factors')
    rounds = session['rounds']
    if not rounds or [r['round'] for r in rounds] != list(range(len(rounds))):
        raise ValueError('rounds must contain consecutive submissions starting at round 0 (code inspection)')
    if len(rounds) > session['budget'] + 1:
        raise ValueError('submission exceeds measurement budget')
    scores = []
    for r in rounds:
        covered, accepted = set(), 0
        claims, judgments = r['claims'], r['judgments']
        ids = [c['id'] for c in claims]
        if len(ids) != len(set(ids)) or set(ids) != set(judgments):
            raise ValueError('each claim needs exactly one evaluator judgment')
        for claim in claims:
            if not all(isinstance(claim.get(k),str) and claim[k].strip() for k in ('region','expression','evidence')):
                raise ValueError('claims need a region, executable-expression description and evidence')
            j = judgments[claim['id']]
            if not isinstance(j.get('accepted'),bool) or not j.get('reason'):
                raise ValueError('judgments need a boolean accepted and a reason')
            supports = set(j['supports'])
            if not supports <= required:
                raise ValueError('judgment refers to an unknown reference factor')
            if j['accepted']:
                if not supports:
                    raise ValueError('accepted claims must map to reviewed reference factors; extend the answer key for valid new discoveries')
                accepted += 1
                covered |= supports
        false = len(claims) - accepted
        precision = accepted/len(claims) if claims else 0.0
        recall = len(covered)/len(required)
        scores.append({'round':r['round'], 'precision':precision, 'recall':recall,
                       'f1':2*precision*recall/(precision+recall) if precision+recall else 0.0,
                       'exact':covered==required and false==0,
                       'unsupported_claims':false, 'covered':sorted(covered)})
    first = next((s['round'] for s in scores if s['exact']),None)
    return {'case':case,'seed':session['seed'],'condition':session['condition'],
            'track':session.get('track','discovery'),
            'model':session['model'], 'family':session.get('family',case),
            'budget':session['budget'], 'first_exact_round':first,
            'accuracy_at_budget':scores[-1]['exact'],
            'success_by_budget':first is not None,
            'final':scores[-1], 'rounds':scores}


def compare(sessions, answers):
    if not sessions:
        raise ValueError('no sessions supplied; empty data is not an accuracy result')
    tracks = {s.get('track','discovery') for s in sessions}
    if len(tracks) != 1:
        raise ValueError('score each track separately; different input-access conditions cannot be pooled')
    pairs = defaultdict(dict)
    for session in sessions:
        if session['condition'] not in ('timing','drperf'):
            raise ValueError('unknown condition')
        if not isinstance(session['budget'],int) or session['budget'] < 1:
            raise ValueError('positive integer measurement budget required')
        result = score_session(session,answers)
        key = (result['case'],result['seed'],result['model'],result['budget'])
        if result['condition'] in pairs[key]:
            raise ValueError(f'duplicate session: {key}, {result["condition"]}')
        pairs[key][result['condition']] = result
    if any(set(p) != {'timing','drperf'} for p in pairs.values()):
        raise ValueError('incomplete pairs: provide both conditions for every case, seed, model and budget')
    if any(p['timing']['family'] != p['drperf']['family'] for p in pairs.values()):
        raise ValueError('paired conditions disagree on source family')
    summary = {}
    for condition in ('timing','drperf'):
        rows = [p[condition] for p in pairs.values()]
        summary[condition] = {
            'sessions':len(rows),
            'accuracy_at_budget':sum(r['accuracy_at_budget'] for r in rows)/len(rows),
            'success_by_budget':sum(r['success_by_budget'] for r in rows)/len(rows),
            'mean_precision':sum(r['final']['precision'] for r in rows)/len(rows),
            'mean_recall':sum(r['final']['recall'] for r in rows)/len(rows),
            'mean_f1':sum(r['final']['f1'] for r in rows)/len(rows),
            'accuracy_after_round':{
                str(i):sum(r['rounds'][min(i,len(r['rounds'])-1)]['exact'] for r in rows if r['budget']>=i)
                /sum(r['budget']>=i for r in rows)
                for i in range(max(r['budget'] for r in rows)+1)
            },
        }
    family_deltas = defaultdict(list)
    wins = losses = ties = 0
    for p in pairs.values():
        delta = int(p['drperf']['accuracy_at_budget'])-int(p['timing']['accuracy_at_budget'])
        family_deltas[p['timing']['family']].append(delta)
        wins += delta > 0; losses += delta < 0; ties += delta == 0
    return {'track':next(iter(tracks)), 'pairs':len(pairs),'distinct_cases':len({k[0] for k in pairs}),
            'source_families':len(family_deltas),'conditions':summary,
            'paired_accuracy_delta':summary['drperf']['accuracy_at_budget']-summary['timing']['accuracy_at_budget'],
            'family_macro_delta':sum(sum(v)/len(v) for v in family_deltas.values())/len(family_deltas),
            'drperf_wins':wins,'timing_wins':losses,'ties':ties,
            'sessions':[p[c] for p in pairs.values() for c in ('timing','drperf')],
            'scope':'Accuracy of reviewed PCV claims on the supplied cases. Historical discovery reports are not agent evaluation results.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('judgments',type=Path)
    parser.add_argument('--output',type=Path)
    args = parser.parse_args()
    answers = {p.parent.parent.name:json.loads(p.read_text()) for p in (ROOT/'cases').glob('*/reference/answer.json')}
    try:
        report = compare(json.loads(args.judgments.read_text())['sessions'],answers)
    except (ValueError,KeyError,TypeError) as exc:
        parser.exit(2,f'score: {exc}\n')
    text = json.dumps(report,indent=2)+'\n'
    if args.output:
        args.output.write_text(text)
    else:
        print(text,end='')


if __name__ == '__main__':
    main()
