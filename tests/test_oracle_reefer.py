"""Orakel-Test (zweite, anders gebaute Nachrechnung, klein und schnell): der Ablauf mit Positionslisten und Bestfit als Schadenstupel statt der Schleife in
`rfr_rules`, über bewusst extreme Räume (Höhe 1, 2 Stapel, Füllgrad 100 %, nur Reefer) - dazu Stichproben-Mittel, gepaartes Urteil, Verteilung und Diagnose
aus der Nachrechnung. Ohne Steckdosen-Stapel und ohne Reefer ist "egal" genau Bestfit der Stapelplanung (dort per Test gegen deren Referenzwerte)."""

import math
import random
import statistics

import pytest

import rfr_constants as C
import rfr_evaluation as EV
import rfr_scenario as SC
import rfr_simulation as SIM

INF = float("inf")


def _reference(inst, est, reefer, plugs, buffer):
    H, n = inst.max_height, inst.n_stacks
    content = {i: [] for i in range(n)}
    out = dict(moves=0, ret=0, with_move=0, reefer=0, unpowered=0, blocked=0, capacity=0, reloc=0, maxh=0, cum=[])

    def choose(c, excl):
        cand = [i for i in range(n) if i != excl and len(content[i]) < H]
        assert cand
        if reefer[c]:
            pool = [i for i in cand if i < plugs]
            powered = bool(pool)
            pool = pool or cand
        else:
            powered = True
            free = sum(H - len(content[k]) for k in range(plugs))
            pool = cand if free - 1 >= buffer else ([i for i in cand if i >= plugs] or cand)

        def key(i):
            top = est[content[i][-1]] if content[i] else INF
            return (0, top, i) if top >= est[c] else (1, -top, i)
        return min(pool, key=key), powered

    for kind, c in inst.events:
        if kind == "A":
            i, powered = choose(c, None)
            if reefer[c]:
                out["reefer"] += 1
                if not powered:
                    out["unpowered"] += 1
                    normals = sum(1 for k in range(plugs) for x in content[k] if not reefer[x])
                    out["blocked" if normals else "capacity"] += 1
            content[i].append(c)
        else:
            x = next(k for k in range(n) if c in content[k])
            above = content[x][content[x].index(c) + 1:]
            for b in reversed(above):
                content[x].remove(b)
                j, powered = choose(b, x)
                content[j].append(b)
                if reefer[b] and not powered:
                    out["reloc"] += 1
            content[x].remove(c)
            out["ret"] += 1
            out["moves"] += len(above)
            out["with_move"] += 1 if above else 0
        out["maxh"] = max(out["maxh"], max(len(s) for s in content.values()))
        out["cum"].append(out["moves"])
    return out


def test_simulation_matches_a_position_based_reference_on_extreme_blocks():
    rng = random.Random(5)
    for it in range(40):
        n, h = rng.randint(2, 10), rng.randint(1, 6)
        inst = SC.generate_instance(n, h, rng.choice([0.4, 0.8, 1.0]), rng.randint(1, 100), rng.randint(0, 999))
        est = SC.estimate_departures(inst, rng.choice([0.0, 0.5, 2.0]))
        reefer = SC.reefer_flags(inst, rng.choice([0, 20, 100]))
        plugs = rng.randint(0, n - 1)
        slots = plugs * h
        for buffer in (0, rng.randint(0, max(slots, 1)), slots):
            r = SIM.run(inst, est, reefer, plugs, buffer)
            ref = _reference(inst, est, reefer, plugs, buffer)
            assert (r.moves, r.retrievals, r.retrievals_with_move, r.reefer_arrivals, r.unpowered, r.blocked, r.capacity_short, r.unpowered_relocations, r.max_stack_height) == \
                   (ref["moves"], ref["ret"], ref["with_move"], ref["reefer"], ref["unpowered"], ref["blocked"], ref["capacity"], ref["reloc"], ref["maxh"]), (it, buffer)
            assert list(r.cumulative) == ref["cum"]


@pytest.mark.parametrize("p", [EV.Params(8, 5, 80, 150, 20, 3, 50, 6), EV.Params(6, 4, 60, 100, 40, 0, 50, 0), EV.Params(5, 3, 100, 80, 50, 4, 100, 12)])
def test_sample_verdict_distribution_and_diagnosis_match_the_reference(p):
    mine = []
    for seed in range(12):
        inst, est, reefer = EV.make_block(p, seed)
        slots = p.plug_stacks * p.max_height
        mine.append({k: _reference(inst, est, reefer, p.plug_stacks, b) for k, b in (("egal", 0), ("puffer", max(0, min(p.buffer, slots))), ("reserviert", slots))})
    sample = EV.sample(p, 12)
    for key in C.RULE_KEYS:
        assert abs(EV.mean_of(sample, key, "unpowered") - statistics.fmean(r[key]["unpowered"] for r in mine)) < 1e-12
        assert abs(EV.mean_of(sample, key, "moves_pr") - statistics.fmean(r[key]["moves"] / r[key]["ret"] for r in mine)) < 1e-12
        d = [r[key]["moves"] / r[key]["ret"] - r["egal"]["moves"] / r["egal"]["ret"] for r in mine]
        v = EV.verdict(sample, key, "egal", "moves_pr")
        assert abs(v.diff - statistics.fmean(d)) < 1e-12 and abs(v.se - statistics.stdev(d) / math.sqrt(len(d))) < 1e-12
        dist = EV.distribution(sample, key, "egal", "unpowered")
        dm = [r[key]["unpowered"] - r["egal"]["unpowered"] for r in mine]
        assert abs(dist.better - sum(x < 0 for x in dm) / len(dm)) < 1e-12 and abs(dist.worse - sum(x > 0 for x in dm) / len(dm)) < 1e-12
    inst, est, reefer = EV.make_block(p, 490)
    dg = EV.diagnose(EV.run_rules(p, inst, est, reefer))
    slots = p.plug_stacks * p.max_height
    puf = _reference(inst, est, reefer, p.plug_stacks, max(0, min(p.buffer, slots)))
    expected = "no_reefers" if puf["reefer"] == 0 else ("ok" if puf["unpowered"] == 0 else ("blocked" if puf["blocked"] >= puf["capacity"] else "capacity"))
    assert dg.kind == expected
