"""Exact-in-form selected-amplitude contraction for two layers of ZZ and RX.

Variables 0..n-1 are the spins before the first mixer and n..2n-1 are
the spins before the second mixer. Conditioning a spin fixes a path variable.
All assignments of the conditioned spins contribute to the final amplitude.
"""
from itertools import product
import math
import random

import numpy as np


def factors(n, edges, cost_angles, mixer_angles, bits):
    if len(bits) != n or set(bits) - {'0', '1'}:
        raise ValueError('Supply a binary output string with one bit per wire')
    if len(cost_angles) != 2 or len(mixer_angles) != 2:
        raise ValueError('Expected two cost angles and two mixer angles')
    terms = []
    for layer, angle in enumerate(cost_angles):
        diag = np.exp(-0.5j * angle)
        zz = np.array([[diag, diag.conjugate()], [diag.conjugate(), diag]])
        for i, j in edges:
            if not 0 <= i < j < n:
                raise ValueError('Expected an ordered pair of distinct wires')
            terms.append(((layer*n+i, layer*n+j), zz))
    mixers = []
    for angle in mixer_angles:
        c, s = math.cos(angle/2), -1j*math.sin(angle/2)
        mixers.append(np.array([[c, s], [s, c]]))
    for q in range(n):
        terms.append(((q, n+q), mixers[0] / math.sqrt(2)))
        terms.append(((n+q,), mixers[1][int(bits[-1-q])]))
    return terms


def adjacency(terms, fixed):
    graph = {}
    for scope, _ in terms:
        live = set(scope) - fixed
        for i in live:
            graph.setdefault(i, set()).update(live - {i})
    return graph


def order_for(graph, rng, min_fill):
    graph = {i: s.copy() for i,s in graph.items()}
    order, largest, work = [], (), 0
    while graph:
        def score(i):
            ns = graph[i]
            fill = sum(len(ns - graph[j]) - 1 for j in ns) if min_fill else 0
            return fill, len(ns), rng.random()
        i = min(graph, key=score)
        neighbors = graph.pop(i)
        group = (i, *sorted(neighbors))
        if len(group) > len(largest):
            largest = group
        work += 1 << len(group)
        for j in neighbors:
            graph[j].update(neighbors - {j})
            graph[j].remove(i)
        order.append(i)
    return order, largest, work


def choose_order(graph, rng, trials):
    return min((order_for(graph, rng, k%2==0) for k in range(trials)),
               key=lambda p:(len(p[1]), p[2]))


def plan(terms, max_axes=18, trials=4):
    if not 2 <= max_axes <= 24 or trials < 1:
        raise ValueError('Invalid contraction budget')
    rng = random.Random(20261123)
    fixed = []
    while True:
        graph = adjacency(terms, set(fixed))
        order, peak, work = choose_order(graph, rng, trials)
        if not fixed:
            unconditioned = len(peak)
        if len(peak) <= max_axes:
            return dict(fixed=fixed, order=order, peak_axes=len(peak),
                        unsliced_peak_axes=unconditioned, slices=1 << len(fixed),
                        entries_processed_per_slice=work)
        fixed.append(max(peak, key=lambda i:(len(graph[i]), -i)))


def contract_slice(terms, order, assignment):
    live = []
    scalar = 1+0j
    for scope, value in terms:
        key = tuple(assignment.get(i, slice(None)) for i in scope)
        axes = tuple(i for i in scope if i not in assignment)
        if axes:
            live.append((axes, value[key]))
        else:
            scalar *= value[key]
    for wire in order:
        bucket = [(axes, v) for axes,v in live if wire in axes]
        live = [(axes, v) for axes,v in live if wire not in axes]
        axes = sorted({i for scope,_ in bucket for i in scope})
        acc = np.ones((2,)*len(axes), np.complex128)
        for scope, value in bucket:
            acc *= value.reshape(tuple(2 if i in scope else 1 for i in axes))
        result = acc.sum(axis=axes.index(wire))
        axes.remove(wire)
        if axes:
            live.append((tuple(axes), result))
        else:
            scalar *= result
    if live:
        raise ValueError('Incomplete elimination order')
    return complex(scalar)


def amplitude(terms, schedule, max_slices):
    if schedule['slices'] > max_slices:
        raise ValueError(f"Exact amplitude requires {schedule['slices']} slices with this schedule")
    # Compensated accumulation across every slice.
    total = correction = 0j
    for bits in product((0, 1), repeat=len(schedule['fixed'])):
        value = contract_slice(terms, schedule['order'], dict(zip(schedule['fixed'], bits)))
        increment = value - correction
        updated = total + increment
        correction = (updated - total) - increment
        total = updated
    return total
