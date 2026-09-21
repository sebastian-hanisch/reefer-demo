"""Die Preset-Kriterien einzeln an ihren Schwellen: künstliche Werte, bei denen genau ein Kriterium kippt (Muster aus der Stapelplanung- und Doppelspiel-Demo).

`many(n, un=..., blocked=...)` verteilt die angegebenen SUMMEN gleichmäßig auf n Blöcke (un=(8, 2, 0) bei n = 10 heißt: Mittel 0,8 / 0,2 / 0 Reefer ohne Strom je Block); die Umstapelungen
`mv` gelten je Block."""

import pytest

import rfr_constants as C
import rfr_stories as ST
from rfr_evaluation import BlockResult

EG, PU, RS = C.RULE_EGAL, C.RULE_PUFFER, C.RULE_RESERVIERT


def blk(seed, un=(10, 2, 0), mv=(1000, 1010, 1300), blocked=None, cap=None, ret=1000):
    keys = (EG, PU, RS)
    blocked = blocked if blocked is not None else un
    cap = cap if cap is not None else tuple(u - b for u, b in zip(un, blocked))
    return BlockResult(seed, ret, 100, dict(zip(keys, mv)), dict(zip(keys, un)), dict(zip(keys, blocked)), dict(zip(keys, cap)), dict(zip(keys, (0.3, 0.3, 0.3))))


def _spread(total, n, i):
    return total // n + (1 if i < total % n else 0)


def many(n, un=(10, 2, 0), mv=(1000, 1010, 1300), blocked=None, ret=1000):
    out = []
    for i in range(n):
        u = tuple(_spread(t, n, i) for t in un)
        b = tuple(_spread(t, n, i) for t in blocked) if blocked is not None else u
        out.append(blk(i, un=u, blocked=b, mv=mv, ret=ret))
    return tuple(out)


def flags(name, results):
    return [ok for ok, _ in ST.criteria(name, results)]


def test_many_spreads_the_totals():
    res = many(10, un=(8, 2, 0))
    assert sum(r.unpowered[EG] for r in res) == 8 and sum(r.unpowered[PU] for r in res) == 2 and all(r.unpowered[RS] == 0 for r in res)
    assert [r.unpowered[EG] for r in many(4, un=(6, 0, 0))] == [2, 2, 1, 1]


def test_unknown_preset_raises():
    with pytest.raises(KeyError):
        ST.criteria("unbekannt", many(2))
    with pytest.raises(KeyError):
        ST.holds("unbekannt", blk(0))


def test_extra_moves_pct():
    res = many(3, mv=(1000, 1030, 1200))
    assert ST.extra_moves_pct(res, PU) == pytest.approx(3.0) and ST.extra_moves_pct(res, RS) == pytest.approx(20.0) and ST.extra_moves_pct(res, EG) == 0


# ---------------------------------------------------------------------------------------------------
# Kriterien über viele Blöcke, je Schwelle
# ---------------------------------------------------------------------------------------------------
def test_passend_thresholds():
    assert flags("Passend", many(10, un=(10, 2, 0), mv=(1000, 1040, 1100))) == [True, True, True, True]
    assert flags("Passend", many(10, un=(7, 1, 0), mv=(1000, 1040, 1100)))[0] is False                # Mittel 0,7 < 0,8
    assert flags("Passend", many(10, un=(8, 2, 0), mv=(1000, 1040, 1100)))[:2] == [True, True]         # 0,8 gerade erfüllt, Puffer 0,2 = 25 % gerade erfüllt
    assert flags("Passend", many(10, un=(8, 3, 0), mv=(1000, 1040, 1100)))[1] is False                 # 0,3 > 25 % von 0,8
    assert flags("Passend", many(10, un=(10, 2, 0), mv=(1000, 1041, 1100)))[2] is False                # +4,1 %
    assert flags("Passend", many(10, un=(10, 2, 0), mv=(1000, 1040, 1100)))[2] is True                 # +4,0 % gerade erfüllt
    assert flags("Passend", many(10, un=(10, 2, 0), mv=(1000, 1040, 1099)))[3] is False                # reserviert +9,9 %
    assert flags("Passend", many(10, un=(10, 2, 0), mv=(1000, 1040, 1100)))[3] is True                 # +10 % gerade erfüllt


def test_zu_wenige_thresholds():
    ok = many(10, un=(40, 15, 12), blocked=(40, 15, 0), mv=(1000, 990, 985))
    assert flags("Zu wenige", ok) == [True, True, True, True]
    assert flags("Zu wenige", many(10, un=(40, 15, 9), blocked=(40, 15, 0), mv=(1000, 990, 985)))[0] is False       # reserviert 0,9 < 1,0
    assert flags("Zu wenige", many(10, un=(40, 15, 10), blocked=(40, 15, 0), mv=(1000, 990, 985)))[0] is True       # 1,0 gerade erfüllt
    one = many(20, un=(80, 30, 24), blocked=(80, 30, 1), mv=(1000, 990, 985))
    two = many(20, un=(80, 30, 24), blocked=(80, 30, 2), mv=(1000, 990, 985))
    assert flags("Zu wenige", one)[1] is True and flags("Zu wenige", two)[1] is False                              # blockiert 0,05 gerade erfüllt, 0,1 nicht
    assert flags("Zu wenige", many(10, un=(29, 15, 10), blocked=(29, 15, 0), mv=(1000, 990, 985)))[2] is False    # egal 2,9 < 3 x 1,0
    assert flags("Zu wenige", many(10, un=(30, 15, 10), blocked=(30, 15, 0), mv=(1000, 990, 985)))[2] is True     # 3,0 gerade erfüllt
    assert flags("Zu wenige", many(10, un=(40, 15, 12), blocked=(40, 15, 0), mv=(1000, 1031, 985)))[3] is False    # Puffer +3,1 %
    assert flags("Zu wenige", many(10, un=(40, 15, 12), blocked=(40, 15, 0), mv=(1000, 970, 985)))[3] is True      # Puffer -3,0 % gerade erfüllt
    assert flags("Zu wenige", many(10, un=(40, 15, 12), blocked=(40, 15, 0), mv=(1000, 969, 985)))[3] is False
    assert flags("Zu wenige", many(10, un=(40, 15, 12), blocked=(40, 15, 0), mv=(1000, 990, 1031)))[3] is False    # reserviert +3,1 %


def test_zu_viele_thresholds():
    assert flags("Zu viele", many(10, un=(1, 0, 0), mv=(1000, 1020, 1300))) == [True, True, True]
    assert flags("Zu viele", many(10, un=(2, 0, 0), mv=(1000, 1020, 1300)))[0] is False                # 0,2 > 0,1
    assert flags("Zu viele", many(10, un=(1, 0, 0), mv=(1000, 1020, 1299)))[1] is False                # +29,9 %
    assert flags("Zu viele", many(10, un=(1, 0, 0), mv=(1000, 1020, 1300)))[1] is True                 # +30 % gerade erfüllt
    assert flags("Zu viele", many(10, un=(1, 0, 0), mv=(1000, 1021, 1300)))[2] is False                # Puffer +2,1 %
    assert flags("Zu viele", many(10, un=(1, 0, 0), mv=(1000, 980, 1300)))[2] is True                  # -2,0 % gerade erfüllt
    assert flags("Zu viele", many(10, un=(1, 0, 0), mv=(1000, 979, 1300)))[2] is False


def test_unsicher_thresholds():
    assert flags("Unsicher", many(10, un=(8, 2, 0), mv=(900, 910, 1000), ret=1000)) == [True, True]
    assert flags("Unsicher", many(10, un=(8, 3, 0), mv=(900, 910, 1000), ret=1000))[0] is False
    assert flags("Unsicher", many(10, un=(8, 2, 0), mv=(899, 910, 1000), ret=1000))[1] is False        # 0,899 < 0,9


def test_grosser_block_thresholds():
    assert flags("Großer Block", many(10, un=(15, 3, 0), mv=(1000, 1040, 1100))) == [True, True, True]
    assert flags("Großer Block", many(10, un=(14, 3, 0), mv=(1000, 1040, 1100)))[0] is False           # 1,4 < 1,5
    assert flags("Großer Block", many(10, un=(16, 5, 0), mv=(1000, 1040, 1100)))[1] is False           # 0,5 > 25 % von 1,6
    assert flags("Großer Block", many(10, un=(16, 4, 0), mv=(1000, 1040, 1100)))[1] is True            # 0,4 = 25 % gerade erfüllt
    assert flags("Großer Block", many(10, un=(15, 3, 0), mv=(1000, 1041, 1100)))[2] is False           # +4,1 %


# ---------------------------------------------------------------------------------------------------
# Kriterien an dem einen Block, je Schwelle (ganze Zahlen)
# ---------------------------------------------------------------------------------------------------
def test_holds_passend():
    assert ST.holds("Passend", blk(0, un=(1, 0, 0), mv=(200, 210, 210)))                              # reserviert genau +5 %
    assert not ST.holds("Passend", blk(0, un=(0, 0, 0), mv=(200, 210, 210)))                          # egal hat keinen Reefer ohne Strom
    assert not ST.holds("Passend", blk(0, un=(1, 1, 0), mv=(200, 210, 210)))                          # Puffer schützt nicht
    assert not ST.holds("Passend", blk(0, un=(1, 0, 0), mv=(200, 210, 209)))                          # reserviert nur +4,5 %


def test_holds_zu_wenige():
    assert ST.holds("Zu wenige", blk(0, un=(9, 1, 1), blocked=(9, 1, 0)))
    assert not ST.holds("Zu wenige", blk(0, un=(9, 1, 0), blocked=(9, 1, 0)))                         # keine Kapazität erschöpft bei reserviert
    assert not ST.holds("Zu wenige", blk(0, un=(9, 1, 1), blocked=(9, 1, 1)))                         # reserviert hat blockierte
    assert not ST.holds("Zu wenige", blk(0, un=(3, 1, 1), blocked=(3, 1, 0)))                         # egal nur 3, gebraucht 1 + 3
    assert ST.holds("Zu wenige", blk(0, un=(4, 1, 1), blocked=(4, 1, 0)))                             # egal = reserviert + 3 gerade erfüllt


def test_holds_zu_viele():
    assert ST.holds("Zu viele", blk(0, un=(0, 0, 0), mv=(200, 200, 240)))
    assert not ST.holds("Zu viele", blk(0, un=(1, 0, 0), mv=(200, 200, 240)))
    assert not ST.holds("Zu viele", blk(0, un=(0, 1, 0), mv=(200, 200, 240)))
    assert not ST.holds("Zu viele", blk(0, un=(0, 0, 0), mv=(200, 200, 239)))                         # +19,5 %


def test_holds_unsicher_and_grosser_block():
    assert ST.holds("Unsicher", blk(0, un=(2, 1, 0))) and not ST.holds("Unsicher", blk(0, un=(0, 0, 0))) and not ST.holds("Unsicher", blk(0, un=(2, 2, 0)))
    assert ST.holds("Unsicher", blk(0, un=(3, 1, 0))) and not ST.holds("Unsicher", blk(0, un=(3, 2, 0)))
    assert ST.holds("Großer Block", blk(0, un=(2, 1, 0))) and ST.holds("Großer Block", blk(0, un=(3, 1, 0)))
    assert not ST.holds("Großer Block", blk(0, un=(1, 0, 0))) and not ST.holds("Großer Block", blk(0, un=(3, 2, 0)))


def test_key_values_lists_only_the_typical_measures_of_the_preset():
    res = many(4, un=(40, 8, 0), mv=(1000, 1010, 1300))
    kv = ST.key_values("Passend", res)
    assert set(kv) == {(EG, "unpowered"), (RS, "moves")} and kv[(EG, "unpowered")] == 10 and kv[(RS, "moves")] == 1300
    assert set(ST.key_values("Zu wenige", res)) == {(EG, "unpowered"), (RS, "unpowered")}
    assert {n for n, _, _ in ST.TYPICAL} == set(C.PRESETS)
