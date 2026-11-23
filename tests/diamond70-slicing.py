import argparse
import json
import pathlib
import random
import runpy
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'native'))
from sliced_bond import Boundary, execute

def main():
    parser = argparse.ArgumentParser(description='Exact all-zero amplitude for prefixes of the Diamond #70 forward circuit.')
    parser.add_argument('--depth', type=int, default=5, choices=range(1,101), metavar='1..100')
    parser.add_argument('--seed', type=int, default=873, help='Contraction seed; the circuit seed is fixed.')
    parser.add_argument('--representation', choices=['affine','compact'], default='compact')
    parser.add_argument('--reverse', action='store_true', help='Use the adjoint of the forward prefix and relabel its wires.')
    parser.add_argument('--plan-only', action='store_true')
    args=parser.parse_args()
    fixture=runpy.run_path(str(ROOT/'tests/mps-random-uncompute.py'))
    gates=fixture['make'](100,8377)[:150*args.depth]
    if args.reverse:
        order=list(range(100))
        random.Random(args.seed).shuffle(order)
        gates=[dict(g,q=order[g['q']],controls=[order[q] for q in g['controls']])
               for g in fixture['inverse'](gates)]
    try:
        result=execute(100,gates,'0'*100,max_bytes=256*2**20,
                       max_slices=512 if args.reverse else 256,max_products=2**41,
                       trials=12 if args.reverse else 16,seed=args.seed,
                       representation=args.representation,plan_only=args.plan_only)
    except Boundary as exc:
        print(json.dumps(dict(depth=args.depth,status='resource-boundary',reason=str(exc))))
        return 1
    print(json.dumps(dict(depth=args.depth,reverse=args.reverse,seed=args.seed,
                          planOnly=args.plan_only,result=result),allow_nan=False))
    return 0

if __name__=='__main__':
    sys.exit(main())
