"""Abnahme der Presets an ECHTEN Daten: jede Geschichte trägt im Mittel über 200 Blöcke (Seeds 0-199) UND an dem einen Block, den das Preset zeigt; der gezeigte Block ist typisch, nicht der
schönste Einzelfall. Alles ganzzahlig und deterministisch (kein Löser, keine Zeitgrenze)."""

import pytest

import rfr_constants as C
import rfr_evaluation as E
import rfr_stories as ST

POPULATION = 200
NAMES = list(C.PRESETS)
_POP = {}


def params(name):
    p = C.PRESETS[name]
    return E.Params(p["n_stacks"], p["max_height"], p["fill_pct"], p["n_containers"], p["reefer_pct"], p["plug_stacks"], p["sigma_pct"], p["buffer"])


def population(name):
    if name not in _POP:
        _POP[name] = E.sample(params(name), POPULATION)
    return _POP[name]


@pytest.mark.parametrize("name", NAMES)
def test_story_holds_on_average_over_the_population(name):
    for ok, text in ST.criteria(name, population(name)):
        assert ok, f"{name}: {text}"


@pytest.mark.parametrize("name", NAMES)
def test_story_holds_at_the_block_the_preset_shows(name):
    seed = C.PRESETS[name]["seed"]
    assert ST.holds(name, E.block_result(params(name), seed)), name


def test_the_preset_seed_lies_outside_the_population():
    assert all(p["seed"] >= POPULATION for p in C.PRESETS.values())


@pytest.mark.parametrize("name", NAMES)
def test_the_shown_block_is_typical_for_every_key_measure(name):
    """Jede Kennzahl des gezeigten Blocks liegt zwischen dem 10. und 90. Perzentil der Grundgesamtheit."""
    shown = E.block_result(params(name), C.PRESETS[name]["seed"])
    for n, key, field in ST.TYPICAL:
        if n != name:
            continue
        values = sorted(getattr(r, field)[key] for r in population(name))
        lo, hi = values[int(0.1 * len(values))], values[int(0.9 * len(values)) - 1]
        assert lo <= getattr(shown, field)[key] <= hi, (name, key, field, getattr(shown, field)[key], (lo, hi))


def test_criteria_are_not_trivially_true_for_the_wrong_preset():
    """Die Geschichten unterscheiden sich: an den Daten eines anderen Presets kippt mindestens ein Kriterium."""
    assert not all(ok for ok, _ in ST.criteria("Zu wenige", population("Passend")))
    assert not all(ok for ok, _ in ST.criteria("Zu viele", population("Passend")))
    assert not all(ok for ok, _ in ST.criteria("Passend", population("Zu viele")))


def test_the_population_reproduces_the_messreihe_for_passend():
    """sweep4.json: egal 1,065 / Puffer 0,015 Reefer ohne Strom je Block, Umstapelungen je Abholung 0,778 / 0,798 / 0,933."""
    pop = population("Passend")
    assert E.mean_of(pop, C.RULE_EGAL) == pytest.approx(1.065, abs=1e-3) and E.mean_of(pop, C.RULE_PUFFER) == pytest.approx(0.015, abs=1e-3) and E.mean_of(pop, C.RULE_RESERVIERT) == 0
    assert [E.mean_of(pop, k, "moves_pr") for k in C.RULE_KEYS] == pytest.approx([0.778, 0.798, 0.933], abs=6e-4)
