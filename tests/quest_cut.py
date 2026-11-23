"""Exact two-part circuit cut for the QuEST reference; q0 is least significant."""
import os
import subprocess
import numpy as np


def cut_reader(n, gates):
    cut = n // 2
    widths = (cut, n-cut)
    terms = [([], [])]

    def append(name, target, control=-1, angle=0.0):
        side = int(target >= cut)
        offset = cut if side else 0
        row = (name, target-offset, control-offset if control>=0 else -1, angle)
        for term in terms:
            term[side].append(row)

    def controlled(name, control, target):
        nonlocal terms
        if (control >= cut) == (target >= cut):
            append(name, target, control)
            return
        if len(terms) >= 64:
            raise ValueError('QuEST reference cut exceeds 64 terms')
        previous = terms
        branches = []
        for outcome in (0, 1):
            terms = [(lo.copy(), hi.copy()) for lo,hi in previous]
            append('project'+str(outcome), control)
            if outcome:
                append({'cx':'x','cz':'z'}[name], target)
            branches.extend(terms)
        terms = branches

    for g in gates:
        name, q, controls = g['name'], g['q'], g['controls']
        if not controls:
            append(name,q,angle=g['theta'])
        elif len(controls)==1:
            c = controls[0]
            if name=='swap':
                controlled('cx', c, q)
                controlled('cx', q, c)
                controlled('cx', c, q)
            elif name in ('cx','cz'):
                controlled(name,c,q)
            else:
                raise ValueError(name)
        else:
            raise ValueError(name)
    vectors = []
    for side,width in enumerate(widths):
        cache = {}
        states = []
        for term in terms:
            sequence = tuple(term[side])
            if sequence not in cache:
                lines = [f'{width} {len(sequence)}', *('%s %d %d %.17g'%g for g in sequence)]
                raw = subprocess.check_output([os.environ['DSIQ_QUEST_VECTOR']],
                    input=('\n'.join(lines)+'\n').encode('ascii'),timeout=120)
                vector = np.frombuffer(raw,dtype=np.complex128)
                if len(vector)!=1<<width or not np.isfinite(vector).all():
                    raise ValueError('Invalid QuEST reference vector')
                cache[sequence] = vector
            states.append(cache[sequence])
        vectors.append(np.stack(states))
    lo,hi = vectors
    size = 1<<cut
    def read(start,count):
        first, offset = divmod(start,size)
        stop = (start+count+size-1)//size
        chunk = hi[:,first:stop].T @ lo
        return chunk.reshape(-1)[offset:offset+count]
    return read,len(terms)
