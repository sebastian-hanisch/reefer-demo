import pytest

import rfr_constants as C
import rfr_scenario as SC


def test_events_and_estimates_are_bit_identical_to_the_stapelplanung_demo():
    """Referenzwerte aus stk_scenario (Stapelplanung-Demo), damit die Zahlen der Messreihe reproduzierbar bleiben."""
    inst = SC.generate_instance(6, 5, 0.8, 120, 7)
    assert (inst.n_events, inst.capacity, inst.mean_dwell) == (240, 20, 28.75)
    assert inst.events[:12] == (("A", 0), ("A", 1), ("A", 2), ("D", 0), ("D", 1), ("A", 3), ("A", 4), ("A", 5), ("A", 6), ("A", 7), ("A", 8), ("A", 9))
    est = SC.estimate_departures(inst, 0.5)
    assert [round(est[c], 4) for c in range(4)] == [-18.563, 26.7911, 19.9353, 5.2455]


def test_every_container_arrives_once_before_it_departs_and_the_capacity_holds():
    for seed in range(15):
        inst = SC.generate_instance(6, 4, 0.8, 60, seed)
        assert sorted(inst.arrival) == sorted(inst.departure) == list(range(60))
        assert all(inst.arrival[c] < inst.departure[c] for c in range(60))
        present = 0
        for kind, _ in inst.events:
            present += 1 if kind == "A" else -1
            assert 0 <= present <= inst.capacity
        assert present == 0 and inst.n_events == 120


def test_capacity_for_matches_the_stapelplanung_formula():
    assert SC.capacity_for(8, 5, 0.8) == 28 and SC.capacity_for(10, 6, 0.8) == 43 and SC.capacity_for(2, 1, 0.1) == 1 and SC.capacity_for(4, 2, 1.0) == 6


@pytest.mark.parametrize("args", [(1, 5, 0.8, 10, 0), (4, 0, 0.8, 10, 0), (4, 5, 0.0, 10, 0), (4, 5, 1.1, 10, 0), (4, 5, 0.8, 0, 0)])
def test_invalid_instances_are_rejected(args):
    with pytest.raises(ValueError):
        SC.generate_instance(*args)


def test_estimates_scale_with_sigma_and_reject_negative_sigma():
    inst = SC.generate_instance(6, 5, 0.8, 60, 2)
    exact = SC.estimate_departures(inst, 0.0)
    assert exact == {c: float(d) for c, d in inst.departure.items()}
    a, b = SC.estimate_departures(inst, 0.5), SC.estimate_departures(inst, 1.0)
    assert all(abs((b[c] - inst.departure[c]) - 2 * (a[c] - inst.departure[c])) < 1e-9 for c in a)
    with pytest.raises(ValueError):
        SC.estimate_departures(inst, -0.1)


def test_reefer_flags_extremes_determinism_and_independence_of_the_events():
    inst = SC.generate_instance(6, 5, 0.8, 200, 4)
    assert not any(SC.reefer_flags(inst, 0).values()) and all(SC.reefer_flags(inst, 100).values())
    assert SC.reefer_flags(inst, 20) == SC.reefer_flags(inst, 20) and SC.reefer_flags(inst, 20) != SC.reefer_flags(inst, 20, seed=5)
    assert len(SC.reefer_flags(inst, 20)) == 200
    share = sum(SC.reefer_flags(inst, 20).values()) / 200
    assert 0.1 < share < 0.3
    more = SC.reefer_flags(inst, 40)
    assert all(more[c] for c, v in SC.reefer_flags(inst, 20).items() if v)          # dieselben Zufallszahlen: ein größerer Anteil enthält den kleineren
    with pytest.raises(ValueError):
        SC.reefer_flags(inst, 101)
    with pytest.raises(ValueError):
        SC.reefer_flags(inst, -1)


def test_rule_of_thumb_buffer_is_the_expected_number_of_reefers_capped_at_the_plug_slots():
    assert SC.rule_of_thumb_buffer(28, 5, 20, 3) == 6 and SC.rule_of_thumb_buffer(28, 5, 30, 2) == 8 and SC.rule_of_thumb_buffer(28, 5, 10, 4) == 3
    assert SC.rule_of_thumb_buffer(28, 5, 40, 3) == 11 and SC.rule_of_thumb_buffer(28, 5, 0, 3) == 0
    assert SC.rule_of_thumb_buffer(28, 5, 50, 1) == 5 and SC.rule_of_thumb_buffer(28, 5, 20, 0) == 0                     # begrenzt auf die Steckdosen-Plätze
    assert SC.rule_of_thumb_buffer(10, 5, 15, 3) == 2                                                                     # 1,5 wird aufgerundet
    assert SC.plug_slots(3, 5) == 15 and SC.plug_slots(0, 5) == 0


def test_default_noise_seed_is_derived_from_the_event_seed():
    assert SC.default_noise_seed(0) == C.NOISE_SEED_OFFSET and SC.default_noise_seed(2) == 2 * C.NOISE_SEED_MULTIPLIER + C.NOISE_SEED_OFFSET
