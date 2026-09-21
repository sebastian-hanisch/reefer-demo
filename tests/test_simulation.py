import statistics

import pytest

import rfr_constants as C
import rfr_rules as R
import rfr_scenario as SC
import rfr_simulation as SIM
from helpers import random_setup, reference_run


def go(inst, est, reefer, plugs, buffer, record=False):
    return SIM.run(inst, est, reefer, plugs, buffer, record=record)


def test_counters_and_cumulative_match_the_independent_reference_on_random_scenarios():
    for seed in range(60):
        inst, est, reefer, plugs = random_setup(seed)
        slots = plugs * inst.max_height
        for rule, buffer in (("egal", 0), ("reserviert", slots), ("puffer", 2), ("puffer", 5)):
            ref = reference_run(inst, est, reefer, plugs, rule, buffer)
            r = go(inst, est, reefer, plugs, R.buffer_for(C.RULE_PUFFER, buffer, plugs, inst.max_height) if rule == "puffer" else buffer)
            assert (r.moves, r.retrievals, r.retrievals_with_move, r.reefer_arrivals, r.unpowered, r.blocked, r.capacity_short, r.unpowered_relocations, r.max_stack_height) == \
                   (ref["moves"], ref["ret"], ref["with_move"], ref["reefer"], ref["unpowered"], ref["blocked"], ref["capacity"], ref["reloc_unpowered"], ref["maxh"]), (seed, rule)
            assert list(r.cumulative) == ref["cum"], (seed, rule)


def test_the_family_limits_are_exactly_the_two_special_rules():
    """Puffer 0 = egal, Puffer >= alle Steckdosen-Plätze = reserviert: der Regler ist eine Familie, keine dritte Regel."""
    for seed in range(40):
        inst, est, reefer, plugs = random_setup(seed)
        slots = plugs * inst.max_height
        assert go(inst, est, reefer, plugs, 0) == go(inst, est, reefer, plugs, 0)
        assert go(inst, est, reefer, plugs, slots) == go(inst, est, reefer, plugs, slots + 7)
        egal = reference_run(inst, est, reefer, plugs, "egal")
        assert go(inst, est, reefer, plugs, 0).moves == egal["moves"]
        res = reference_run(inst, est, reefer, plugs, "reserviert")
        assert go(inst, est, reefer, plugs, slots).moves == res["moves"] and go(inst, est, reefer, plugs, slots).unpowered == res["unpowered"]


def test_recorded_steps_keep_every_invariant():
    for seed in range(25):
        inst, est, reefer, plugs = random_setup(seed)
        r = go(inst, est, reefer, plugs, 3, record=True)
        assert len(r.steps) == inst.n_events
        plugged = set(range(plugs))
        present = set()
        prev_moves = 0
        for step, (kind, c) in zip(r.steps, inst.events):
            assert (step.kind, step.container) == (kind, c)
            (present.add if kind == "A" else present.remove)(c)
            flat = [x for s in step.stacks for x in s]
            assert sorted(flat) == sorted(present) and all(len(s) <= inst.max_height for s in step.stacks)
            assert step.unpowered_now == tuple(sorted(x for k, s in enumerate(step.stacks) if k not in plugged for x in s if reefer[x]))
            assert step.moves_so_far - prev_moves == len(step.moved) and (kind == "D" or not step.moved)
            assert not step.arrival_unpowered or (kind == "A" and reefer[c] and c in step.unpowered_now)
            prev_moves = step.moves_so_far
        assert not present and r.steps[-1].moves_so_far == r.moves


def test_a_reefer_stands_on_a_plug_stack_whenever_one_had_room_at_arrival():
    for seed in range(25):
        inst, est, reefer, plugs = random_setup(seed)
        r = go(inst, est, reefer, plugs, 4, record=True)
        for k, step in enumerate(r.steps):
            if step.kind == "A" and reefer[step.container]:
                before = r.steps[k - 1].stacks if k else tuple(() for _ in range(inst.n_stacks))
                had_room = any(len(before[i]) < inst.max_height for i in range(plugs))
                assert (step.stack < plugs) == had_room and step.arrival_unpowered == (not had_room)


def test_result_without_retrievals_has_zero_rates():
    r = SIM.Result(0, 0, 0, 0, (), (), 0, 0, 0, 0, 0, None)
    assert r.moves_per_retrieval == 0.0 and r.share_retrievals_with_move == 0.0


def test_counters_add_up():
    for seed in range(40):
        inst, est, reefer, plugs = random_setup(seed)
        r = go(inst, est, reefer, plugs, 3)
        assert r.unpowered == r.blocked + r.capacity_short and r.reefer_arrivals == sum(reefer.values()) and r.retrievals == inst.n_containers
        assert r.unpowered <= r.reefer_arrivals and r.retrievals_with_move <= r.retrievals and r.moves >= r.retrievals_with_move
        assert 0 <= r.moves_per_retrieval and 0 <= r.share_retrievals_with_move <= 1
        assert (r.plug_utilisation is None) == (plugs == 0)
        if plugs:
            assert 0 <= r.plug_utilisation <= 1


def test_no_reefers_means_nothing_to_count_and_reserving_only_costs_moves():
    inst = SC.generate_instance(8, 5, 0.8, 300, 3)
    est = SC.estimate_departures(inst, 0.5)
    none = SC.reefer_flags(inst, 0)
    a, b = go(inst, est, none, 3, 0), go(inst, est, none, 3, 15)
    assert (a.reefer_arrivals, a.unpowered, a.blocked, a.capacity_short, a.unpowered_relocations, a.plug_utilisation) == (0, 0, 0, 0, 0, 0.0)
    assert b.moves > a.moves


def test_zero_plug_stacks_leave_every_reefer_without_power_and_count_it_as_capacity():
    inst = SC.generate_instance(6, 5, 0.8, 120, 4)
    est = SC.estimate_departures(inst, 0.5)
    fl = SC.reefer_flags(inst, 30)
    r = go(inst, est, fl, 0, 0)
    assert r.unpowered == r.reefer_arrivals == r.capacity_short > 0 and r.blocked == 0 and r.plug_utilisation is None
    assert go(inst, est, fl, 0, 5) == go(inst, est, fl, 0, 0)                 # der Puffer bewirkt ohne Steckdosen nichts


def test_all_reefers_make_the_normal_rule_irrelevant():
    inst = SC.generate_instance(8, 5, 0.8, 200, 2)
    est = SC.estimate_departures(inst, 0.5)
    fl = SC.reefer_flags(inst, 100)
    base = go(inst, est, fl, 3, 0)
    assert go(inst, est, fl, 3, 6) == base and go(inst, est, fl, 3, 15) == base


def test_smallest_block_two_stacks_of_height_two():
    inst = SC.generate_instance(2, 2, 1.0, 12, 1)
    est = SC.estimate_departures(inst, 0.0)
    fl = SC.reefer_flags(inst, 50)
    r = go(inst, est, fl, 1, 1, record=True)
    ref = reference_run(inst, est, fl, 1, "puffer", 1)
    assert r.moves == ref["moves"] and r.unpowered == ref["unpowered"] and len(r.steps) == 24


def test_plug_utilisation_is_the_mean_share_of_plug_slots_with_reefers():
    inst, est, reefer, plugs = random_setup(11)
    plugs = max(plugs, 1)
    r = go(inst, est, reefer, plugs, 2, record=True)
    slots = plugs * inst.max_height
    expected = statistics.fmean(sum(1 for k in range(plugs) for x in step.stacks[k] if reefer[x]) / slots for step in r.steps)
    assert r.plug_utilisation == pytest.approx(expected)


def test_measured_facts_reproduce_the_messreihe():
    """Zahlen aus hafen-planung/messreihe_reefer/sweep4.json (8 x 5, 300 Container, 20 % Reefer, 3 Steckdosen-Stapel, sigma 50 %, Seeds 0-199)."""
    rows = {0: [], 6: [], 15: []}
    for seed in range(200):
        inst = SC.generate_instance(8, 5, 0.8, 300, seed)
        est = SC.estimate_departures(inst, 0.5)
        fl = SC.reefer_flags(inst, 20)
        for b in rows:
            r = go(inst, est, fl, 3, b)
            rows[b].append((r.moves_per_retrieval, r.unpowered))
    mean = {b: (statistics.fmean(x[0] for x in v), statistics.fmean(x[1] for x in v)) for b, v in rows.items()}
    assert mean[0] == pytest.approx((0.778, 1.065), abs=6e-4)
    assert mean[6] == pytest.approx((0.798, 0.015), abs=6e-4)
    assert mean[15] == pytest.approx((0.933, 0.0), abs=6e-4)
