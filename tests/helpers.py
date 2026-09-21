"""Testhilfen: zufällige Szenarien und eine unabhängige, bewusst einfache Nachrechnung des Ablaufs (teilt keinen Code mit rfr_rules und rfr_simulation)."""

import random
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import rfr_scenario as SC  # noqa: E402

INF = float("inf")


def random_setup(seed, max_n=8, max_h=5):
    """(instance, estimates, reefer, plug_stacks) aus zufälligen, aber gültigen Einstellungen."""
    rng = random.Random(seed)
    n = rng.randint(3, max_n)
    h = rng.randint(2, max_h)
    fill = rng.choice([0.5, 0.6, 0.8, 1.0])
    n_cont = rng.randint(20, 90)
    inst = SC.generate_instance(n, h, fill, n_cont, seed)
    est = SC.estimate_departures(inst, rng.choice([0.0, 0.5, 1.5]))
    reefer = SC.reefer_flags(inst, rng.choice([0, 10, 20, 40, 60]))
    plugs = rng.randint(0, n - 1)
    return inst, est, reefer, plugs


def _best(stacks, cand, e, est):
    tops = [(est[stacks[i][-1]] if stacks[i] else INF, i) for i in cand]
    good = sorted(t for t in tops if t[0] >= e)
    if good:
        return good[0][1]
    bad = [t for t in tops if t[0] < e]
    return min(bad, key=lambda t: (-t[0], t[1]))[1]


def reference_run(inst, est, reefer, plugs, rule, buffer=0):
    """Unabhängige Nachrechnung. rule: "egal", "reserviert" oder "puffer" (mit buffer). Liefert ein dict mit den Zählern."""
    h = inst.max_height
    stacks = [[] for _ in range(inst.n_stacks)]
    plug_idx = list(range(plugs))

    def choose(c, exclude):
        cand = [i for i, s in enumerate(stacks) if i != exclude and len(s) < h]
        plain = [i for i in cand if i >= plugs]
        if reefer[c]:
            on_plug = [i for i in cand if i < plugs]
            return (_best(stacks, on_plug, est[c], est), True) if on_plug else (_best(stacks, cand, est[c], est), False)
        if rule == "egal":
            allowed = cand
        elif rule == "reserviert":
            allowed = plain or cand
        else:
            free = sum(h - len(stacks[k]) for k in plug_idx)
            allowed = (cand if free - 1 >= buffer else plain) or cand
        return _best(stacks, allowed, est[c], est), True

    out = dict(moves=0, ret=0, with_move=0, reefer=0, unpowered=0, blocked=0, capacity=0, reloc_unpowered=0, maxh=0, cum=[])
    for kind, c in inst.events:
        if kind == "A":
            i, powered = choose(c, None)
            if reefer[c]:
                out["reefer"] += 1
                if not powered:
                    out["unpowered"] += 1
                    normals_on_plug = sum(1 for k in plug_idx for x in stacks[k] if not reefer[x])
                    out["blocked" if normals_on_plug > 0 else "capacity"] += 1
            stacks[i].append(c)
        else:
            x = next(k for k, s in enumerate(stacks) if c in s)
            n_moved = 0
            while stacks[x][-1] != c:
                b = stacks[x].pop()
                j, powered = choose(b, x)
                stacks[j].append(b)
                n_moved += 1
                if reefer[b] and not powered:
                    out["reloc_unpowered"] += 1
            stacks[x].pop()
            out["ret"] += 1
            out["moves"] += n_moved
            out["with_move"] += n_moved > 0
        out["maxh"] = max(out["maxh"], max(len(s) for s in stacks))
        out["cum"].append(out["moves"])
    return out
