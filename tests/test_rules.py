import pytest

import rfr_constants as C
import rfr_rules as R

INF = float("inf")


def est_of(*tops):
    """Schätzungen für Container 0..n-1."""
    return {i: t for i, t in enumerate(tops)}


def test_bestfit_prefers_the_tightest_stack_that_blocks_nothing_earlier():
    stacks = [[0], [1], [2], []]
    est = est_of(10.0, 5.0, 20.0)
    assert R.bestfit(stacks, [0, 1, 2, 3], 8.0, est) == 0            # kleinstes oberes ê >= 8 ist 10
    assert R.bestfit(stacks, [1, 2, 3], 8.0, est) == 2               # 20 vor dem leeren Stapel (unendlich)
    assert R.bestfit(stacks, [1, 3], 8.0, est) == 3                  # 5 blockiert, der leere Stapel nicht
    assert R.bestfit(stacks, [0, 1, 2, 3], 10.0, est) == 0           # ê gleich zählt als nicht blockierend


def test_bestfit_when_everything_blocks_takes_the_stack_with_the_latest_top():
    stacks = [[0], [1]]
    est = est_of(3.0, 7.0)
    assert R.bestfit(stacks, [0, 1], 9.0, est) == 1


def test_bestfit_breaks_ties_by_the_first_candidate_in_the_given_order():
    stacks = [[0], [1], [], []]
    est = est_of(10.0, 10.0)
    assert R.bestfit(stacks, [0, 1], 5.0, est) == 0 and R.bestfit(stacks, [1, 0], 5.0, est) == 1
    assert R.bestfit(stacks, [2, 3], 5.0, est) == 2                  # zwei leere Stapel: der erste
    assert R.bestfit([[0], [1]], [0, 1], 9.0, est_of(3.0, 3.0)) == 0  # alle blockieren gleich stark: der erste


def test_plugged_set_is_the_first_stacks():
    assert R.plugged_set(3) == frozenset({0, 1, 2}) and R.plugged_set(0) == frozenset()


def test_reefer_goes_to_a_plug_stack_with_room_else_unpowered_elsewhere():
    plugged = R.plugged_set(2)
    stacks = [[0], [], [1]]
    est = est_of(10.0, 9.0)
    assert R.place(stacks, 2, plugged, True, 5.0, est, buffer=0) == (0, True)            # Bestfit unter den Steckdosen-Stapeln 0 und 1
    full = [[0, 1], [2, 3], [4]]
    est = {i: float(10 + i) for i in range(5)}
    i, powered = R.place(full, 2, plugged, True, 5.0, est, buffer=0)
    assert (i, powered) == (2, False)                                                     # Steckdosen-Stapel voll: ohne Strom
    assert R.place([[0, 1], [2], [3]], 2, plugged, True, 5.0, est, buffer=0) == (1, True)


def test_normal_container_uses_a_plug_stack_only_while_the_buffer_stays_free():
    plugged = R.plugged_set(1)                       # ein Steckdosen-Stapel der Höhe 3: drei Plätze
    est = {0: 9.0, 1: 5.0, 2: 6.0}
    stacks = [[0], [1], [2]]                         # Steckdosen-Stapel enthält 0 (ê 9): eng passend für ê 8
    assert R.place(stacks, 3, plugged, False, 8.0, est, buffer=0)[0] == 0        # frei 2, 2 - 1 >= 0: erlaubt, Bestfit wählt Stapel 0
    assert R.place(stacks, 3, plugged, False, 8.0, est, buffer=1)[0] == 0        # frei 2, 2 - 1 >= 1: erlaubt
    assert R.place(stacks, 3, plugged, False, 8.0, est, buffer=2)[0] in (1, 2)   # 2 - 1 >= 2 nicht erfüllt: nur die übrigen Stapel
    assert R.place([[0, 3], [1], [2]], 3, plugged, False, 8.0, {**est, 3: 4.0}, buffer=1)[0] in (1, 2)   # frei 1: 1 - 1 >= 1 nicht erfüllt


def test_reserved_falls_back_to_all_stacks_when_only_plug_stacks_have_room():
    plugged = R.plugged_set(1)
    stacks = [[], [1, 2], [3, 4]]
    est = {i: float(i) for i in range(5)}
    assert R.place(stacks, 2, plugged, False, 0.5, est, buffer=99) == (0, True)


def test_buffer_zero_is_bestfit_over_all_stacks_and_a_huge_buffer_is_bestfit_over_plain_stacks_in_index_order():
    """Die Kandidatenliste bleibt in Stapelindex-Reihenfolge, damit Gleichstände nicht von der Regel abhängen."""
    plugged = R.plugged_set(2)
    est = {0: 9.0, 1: 9.0, 2: 9.0, 3: 9.0}
    stacks = [[0], [1], [2], [3]]
    assert R.place(stacks, 3, plugged, False, 5.0, est, buffer=0)[0] == 0        # Gleichstand: Stapel 0 (Steckdosen-Stapel steht links)
    assert R.place(stacks, 3, plugged, False, 5.0, est, buffer=99)[0] == 2       # nur Stapel ohne Steckdose, Gleichstand: der erste
    assert R.place([[0], [1], [], []], 3, plugged, False, 5.0, est, buffer=99)[0] == 2


def test_relocation_excludes_the_source_stack():
    plugged = R.plugged_set(1)
    stacks = [[0, 1], [], []]
    est = {0: 5.0, 1: 4.0}
    assert R.place(stacks, 2, plugged, False, 4.0, est, buffer=0, exclude=0)[0] == 1
    assert R.place(stacks, 2, plugged, True, 4.0, est, buffer=0, exclude=0) == (1, False)    # einziger Steckdosen-Stapel ist die Quelle: ohne Strom


def test_no_room_raises():
    with pytest.raises(ValueError):
        R.place([[0], [1]], 1, R.plugged_set(1), False, 1.0, {0: 1.0, 1: 2.0}, buffer=0)
    with pytest.raises(ValueError):
        R.place([[0, 1], []], 2, R.plugged_set(0), True, 1.0, {0: 1.0, 1: 2.0}, buffer=0, exclude=1)


def test_buffer_for_maps_the_three_rules_and_caps_the_buffer():
    assert R.buffer_for(C.RULE_EGAL, 6, 3, 5) == 0 and R.buffer_for(C.RULE_RESERVIERT, 6, 3, 5) == 15
    assert R.buffer_for(C.RULE_PUFFER, 6, 3, 5) == 6 and R.buffer_for(C.RULE_PUFFER, 99, 3, 5) == 15 and R.buffer_for(C.RULE_PUFFER, -2, 3, 5) == 0
    assert R.buffer_for(C.RULE_PUFFER, 6, 0, 5) == 0 and R.buffer_for(C.RULE_RESERVIERT, 6, 0, 5) == 0
    with pytest.raises(ValueError):
        R.buffer_for("unbekannt", 1, 1, 1)


def test_free_plug_slots_counts_the_free_places_of_the_plug_stacks_only():
    assert R.free_plug_slots([[0], [1, 2], []], 3, R.plugged_set(2)) == 2 + 1
    assert R.free_plug_slots([[0], [1, 2], []], 3, R.plugged_set(0)) == 0
