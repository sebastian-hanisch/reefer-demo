import statistics

import pytest

import rfr_constants as C
import rfr_evaluation as E
import rfr_scenario as SC
import rfr_simulation as SIM
from rfr_evaluation import BlockResult

EG, PU, RS = C.RULE_EGAL, C.RULE_PUFFER, C.RULE_RESERVIERT
P = E.Params(8, 5, 80, 300, 20, 3, 50, 6)


def br(seed, un=(5, 2, 0), mv=(100, 104, 130), blocked=None, cap=None, ret=100, util=(0.3, 0.3, 0.3)):
    """Künstlicher Block: je Regel (egal, Puffer, reserviert) Reefer ohne Strom und Umstapelungen."""
    keys = (EG, PU, RS)
    blocked = blocked or un
    cap = cap or tuple(u - b for u, b in zip(un, blocked))
    return BlockResult(seed, ret, 20, dict(zip(keys, mv)), dict(zip(keys, un)), dict(zip(keys, blocked)), dict(zip(keys, cap)), dict(zip(keys, util)))


# ---------------------------------------------------------------------------------------------------
# Ein Block
# ---------------------------------------------------------------------------------------------------
def test_params_derive_capacity_slots_and_the_rule_of_thumb():
    assert E.capacity_of(P) == 28 and E.slots_of(P) == 15 and E.thumb_of(P) == 6
    assert E.slots_of(P._replace(plug_stacks=0)) == 0 and E.thumb_of(P._replace(plug_stacks=0)) == 0
    assert E.thumb_of(P._replace(plug_stacks=1, reefer_pct=50)) == 5            # auf die Steckdosen-Plätze begrenzt


def test_run_rules_returns_the_three_rules_with_their_buffers():
    inst, est, reefer = E.make_block(P, 3)
    outs = E.run_rules(P, inst, est, reefer)
    assert [o.key for o in outs] == list(C.RULE_KEYS) and [o.buffer for o in outs] == [0, 6, 15]
    assert [o.label for o in outs] == [C.RULE_LABELS[k] for k in C.RULE_KEYS]
    for o in outs:
        assert o.result == SIM.run(inst, est, reefer, 3, o.buffer)
    assert E.outcome_of(outs, PU) is outs[1]
    assert all(o.result.steps for o in E.run_rules(P, inst, est, reefer, record=True))


def test_make_block_is_the_scenario_of_the_scenario_module():
    inst, est, reefer = E.make_block(P, 5)
    ref = SC.generate_instance(8, 5, 0.8, 300, 5)
    assert inst.events == ref.events and est == SC.estimate_departures(ref, 0.5) and reefer == SC.reefer_flags(ref, 20)


def test_the_buffer_is_capped_at_the_plug_slots_for_the_puffer_rule():
    inst, est, reefer = E.make_block(P._replace(buffer=99), 1)
    assert E.outcome_of(E.run_rules(P._replace(buffer=99), inst, est, reefer), PU).buffer == 15


# ---------------------------------------------------------------------------------------------------
# Stichprobe
# ---------------------------------------------------------------------------------------------------
def test_sample_has_one_result_per_seed_and_ignores_the_chosen_seed():
    res = E.sample(P, 6)
    assert [r.seed for r in res] == list(range(6)) and all(r.retrievals == 300 for r in res)
    inst, est, reefer = E.make_block(P, 4)
    direct = {o.key: o.result for o in E.run_rules(P, inst, est, reefer)}
    assert res[4].moves == {k: r.moves for k, r in direct.items()} and res[4].unpowered == {k: r.unpowered for k, r in direct.items()}
    assert res[4].reefer_arrivals == direct[EG].reefer_arrivals and res[4].utilisation[PU] == direct[PU].plug_utilisation


def test_means_and_utilisation():
    res = (br(0, un=(4, 1, 0), mv=(100, 110, 150)), br(1, un=(6, 3, 0), mv=(120, 120, 180)))
    assert E.mean_of(res, EG) == 5 and E.mean_of(res, PU, "moves") == 115 and E.mean_of(res, RS, "moves_pr") == pytest.approx(1.65)
    assert E.mean_of(res, PU, "blocked") == 2 and E.mean_of(res, PU, "capacity_short") == 0
    assert E.mean_utilisation(res, PU) == pytest.approx(0.3)
    assert E.mean_utilisation((br(0, util=(None, None, None)),), PU) is None


def test_paired_differences_are_rule_minus_reference():
    res = (br(0, un=(4, 1, 0), mv=(100, 110, 150)), br(1, un=(6, 3, 0), mv=(120, 120, 180)))
    assert E.paired(res, PU, EG) == [-3, -3] and E.paired(res, RS, EG, "moves") == [50, 60]
    assert E.paired(res, PU, EG, "moves_pr") == pytest.approx([0.1, 0.0])


# ---------------------------------------------------------------------------------------------------
# Verteilung und Urteil
# ---------------------------------------------------------------------------------------------------
def test_distribution_counts_better_equal_worse_and_gains():
    res = (br(0, un=(5, 2, 0)), br(1, un=(3, 3, 0)), br(2, un=(2, 4, 0)), br(3, un=(6, 1, 0)))
    d = E.distribution(res, PU, EG)
    assert (d.n, d.better, d.equal, d.worse) == (4, 0.5, 0.25, 0.25)
    assert d.mean_gain == pytest.approx((3 + 0 - 2 + 5) / 4) and d.median_gain == pytest.approx(1.5)
    assert d.better + d.equal + d.worse == pytest.approx(1)


def test_distribution_of_moves_uses_integer_equality():
    res = (br(0, mv=(100, 100, 130)), br(1, mv=(100, 101, 130)), br(2, mv=(100, 99, 130)))
    d = E.distribution(res, PU, EG, "moves_pr")
    assert (d.better, d.equal, d.worse) == pytest.approx((1 / 3, 1 / 3, 1 / 3)) and d.field == "moves_pr"


def test_verdict_three_states_and_the_threshold_of_two_standard_errors():
    clear = tuple(br(i, un=(5 + i % 2, 2, 0)) for i in range(20))
    v = E.verdict(clear, PU, EG)
    assert v.kind == "better" and v.diff < 0 and v.n == 20 and v.pct < 0 and v.field == "unpowered"
    worse = tuple(br(i, un=(2, 5 + i % 2, 0)) for i in range(20))
    assert E.verdict(worse, PU, EG).kind == "worse"
    noisy = tuple(br(i, un=(3, 3 + (1 if i % 2 else -1), 0)) for i in range(20))
    assert E.verdict(noisy, PU, EG).kind == "unclear"
    # genau an der Schwelle: Differenz = 2 Standardfehler ist noch unklar, knapp darüber klar
    diffs = [-1, -1, -1, -1, 0, 0, 0, 0, 0, 0]
    n = len(diffs)
    se = statistics.stdev(diffs) / n ** 0.5
    mean = statistics.fmean(diffs)
    z = abs(mean) / se
    res = tuple(br(i, un=(5, 5 + d, 0)) for i, d in enumerate(diffs))
    assert E.verdict(res, PU, EG).kind == "better" and z == pytest.approx(2.449, abs=1e-3) and C.VERDICT_Z == 2.0            # z = 2,45: klar bei Schwelle 2 (bei 3 wäre es unklar)
    boundary = tuple(br(i, un=(5, 5 + d, 0)) for i, d in enumerate([-1, -1, 0, 0, 0, 0, 0, 0, 0, 0]))
    assert E.verdict(boundary, PU, EG).kind == "unclear"                              # z = 1,5


def test_verdict_with_identical_differences_and_no_variance():
    same = tuple(br(i, un=(5, 2, 0)) for i in range(5))
    v = E.verdict(same, PU, EG)
    assert v.kind == "better" and v.se == 0 and v.diff == -3
    zero = tuple(br(i, un=(5, 5, 0)) for i in range(5))
    assert E.verdict(zero, PU, EG).kind == "unclear"
    worse = tuple(br(i, un=(5, 6, 0)) for i in range(5))
    assert E.verdict(worse, PU, EG).kind == "worse"
    assert E.verdict((br(0),), PU, EG).se == 0


def test_verdict_percentage_is_none_when_the_reference_needs_nothing():
    res = tuple(br(i, un=(0, 1, 0)) for i in range(5))
    v = E.verdict(res, PU, EG)
    assert v.pct is None and v.kind == "worse"
    v = E.verdict(tuple(br(i, mv=(100, 110, 130)) for i in range(5)), PU, EG, "moves_pr")
    assert v.kind == "worse" and v.pct == pytest.approx(10.0)


# ---------------------------------------------------------------------------------------------------
# Kurven
# ---------------------------------------------------------------------------------------------------
def test_buffer_points_cover_the_range_and_always_include_current_and_thumb():
    assert E.buffer_points(5, 2, 3) == (0, 1, 2, 3, 4, 5)
    assert E.buffer_points(0, 0, 0) == (0,)
    big = E.buffer_points(30, 7, 9)
    assert big[0] == 0 and big[-1] == 30 and 7 in big and 9 in big and len(big) <= C.CURVE_MAX_POINTS + 2 and list(big) == sorted(set(big))
    assert E.buffer_points(5, 99, -3) == (0, 1, 2, 3, 4, 5)                                # Werte außerhalb werden begrenzt


def test_buffer_curve_equals_direct_means_and_ends_at_the_two_special_rules():
    cv = E.buffer_curve(P, 4)
    s = cv.series["Puffer"]
    assert cv.n_blocks == 4 and 0 in cv.xs and 15 in cv.xs and 6 in cv.xs
    for j, b in enumerate(cv.xs):
        rows = []
        for seed in range(4):
            inst, est, reefer = E.make_block(P, seed)
            rows.append(SIM.run(inst, est, reefer, 3, b))
        assert s["unpowered"][j] == pytest.approx(statistics.fmean(r.unpowered for r in rows))
        assert s["moves_pr"][j] == pytest.approx(statistics.fmean(r.moves_per_retrieval for r in rows))
        assert s["blocked"][j] + s["capacity_short"][j] == pytest.approx(s["unpowered"][j])
    res = E.sample(P, 4)
    assert s["unpowered"][0] == pytest.approx(E.mean_of(res, EG)) and s["unpowered"][-1] == pytest.approx(E.mean_of(res, RS))


def test_buffer_curve_without_plug_stacks_is_a_single_point():
    cv = E.buffer_curve(P._replace(plug_stacks=0), 3)
    assert cv.xs == (0,) and len(cv.series["Puffer"]["unpowered"]) == 1


def test_plug_curve_has_a_point_per_plug_stack_count_and_three_rules():
    cv = E.plug_curve(P._replace(n_stacks=5, n_containers=100), 3)
    assert cv.xs == (0, 1, 2, 3, 4) and list(cv.series) == ["egal", "Puffer (Faustregel)", "reserviert"]
    p = P._replace(n_stacks=5, n_containers=100)
    for j, s in enumerate(cv.xs):
        for name, key in (("egal", EG), ("Puffer (Faustregel)", PU), ("reserviert", RS)):
            slots = s * 5
            b = {EG: 0, RS: slots, PU: SC.rule_of_thumb_buffer(E.capacity_of(p), 5, 20, s)}[key]
            vals = []
            for seed in range(3):
                inst, est, reefer = E.make_block(p, seed)
                vals.append(SIM.run(inst, est, reefer, s, b).unpowered)
            assert cv.series[name]["unpowered"][j] == pytest.approx(statistics.fmean(vals)), (s, name)
    assert cv.series["egal"]["unpowered"][0] == cv.series["reserviert"]["unpowered"][0]                  # ohne Steckdosen sind alle Regeln gleich


# ---------------------------------------------------------------------------------------------------
# Diagnose
# ---------------------------------------------------------------------------------------------------
def diag_outcomes(un, blocked, cap, arrivals=20, mv=(100, 104, 130)):
    def res(m, u, b, c):
        return SIM.Result(m, 100, 50, 5, (m,), (), arrivals, u, b, c, 0, 0.3)
    return [E.Outcome(EG, "e", 0, res(mv[0], 5, 5, 0)), E.Outcome(PU, "p", 6, res(mv[1], un, blocked, cap)), E.Outcome(RS, "r", 15, res(mv[2], 0, 0, 0))]


def test_diagnose_kinds():
    assert E.diagnose(diag_outcomes(0, 0, 0, arrivals=0)).kind == "no_reefers"
    assert E.diagnose(diag_outcomes(0, 0, 0)).kind == "ok"
    assert E.diagnose(diag_outcomes(3, 3, 0)).kind == "blocked"
    assert E.diagnose(diag_outcomes(3, 0, 3)).kind == "capacity"
    assert E.diagnose(diag_outcomes(4, 2, 2)).kind == "blocked"                                    # Gleichstand: blockiert zuerst nennen
    assert E.diagnose(diag_outcomes(4, 1, 3)).kind == "capacity"
    d = E.diagnose(diag_outcomes(3, 3, 0, mv=(100, 104, 130)))
    assert (d.unpowered, d.blocked, d.capacity_short) == (3, 3, 0) and d.reserve_extra_moves_pct == pytest.approx(30.0)
    assert E.diagnose(diag_outcomes(0, 0, 0, mv=(0, 0, 4))).reserve_extra_moves_pct is None


def test_suggested_event_prefers_the_first_reefer_without_power_then_a_move_at_high_load():
    inst, est, reefer = E.make_block(P._replace(plug_stacks=1, reefer_pct=40), 2)
    r = SIM.run(inst, est, reefer, 1, 0, record=True)
    k = E.suggested_event(r)
    assert r.steps[k - 1].arrival_unpowered
    assert k == next(i for i, s in enumerate(r.steps, 1) if s.arrival_unpowered)
    quiet = SIM.run(*E.make_block(P._replace(reefer_pct=0), 2)[:2], E.make_block(P._replace(reefer_pct=0), 2)[2], 3, 15, record=True)
    k = E.suggested_event(quiet)
    assert quiet.steps[k - 1].kind == "D" and quiet.steps[k - 1].moved
    filled = sum(len(x) for x in quiet.steps[k - 1].stacks)
    assert all(sum(len(x) for x in s.stacks) <= filled for s in quiet.steps if s.kind == "D" and s.moved)
    step = SIM.Step("A", 0, 0, (), ((0,),), 0, (), False)
    empty = SIM.Result(0, 0, 0, 1, (0, 0), (step, step), 0, 0, 0, 0, 0, None)
    assert E.suggested_event(empty) == 2                                                            # weder Reefer ohne Strom noch Umstapelung: das Ende
    assert E.suggested_event(SIM.Result(0, 0, 0, 0, (), (), 0, 0, 0, 0, 0, None)) == 0
