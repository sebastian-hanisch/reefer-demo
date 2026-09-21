"""AppTest: Skelett und Footer, jedes Preset, Permalink mit berechneten Grenzen, alle Regler an Min und Max, Kennzahlen im 2 x 2-Raster, die bedingte Meldung in allen Zuständen, Stichprobe, Kurven
und Urteil, Regelvergleich, PDF, Texte."""

import pathlib

import pytest
from streamlit.proto.Metric_pb2 import Metric as MetricProto
from streamlit.testing.v1 import AppTest

import rfr_constants as C
import rfr_evaluation as E
from rfr_presets import SETTING_SPECS

APP = str(pathlib.Path(__file__).resolve().parent.parent / "app.py")
FOOTER = ("Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
          "Operations Research und Machine Learning. Interesse an einer maßgeschneiderten Lösung für "
          "Ihr Unternehmen? [Kontakt aufnehmen](https://sebastianhanisch.net/kontakt.html)")
EG, PU, RS = C.RULE_EGAL, C.RULE_PUFFER, C.RULE_RESERVIERT

# Am Preset-Block (Seed 490): Reefer ohne Strom bei Puffer (Wert, Delta gegen egal), Art der Meldung
EXPECTED = {"Passend": ("0", "-1", "ok"), "Zu wenige": ("1", "-8", "capacity"), "Zu viele": ("0", "+0", "ok"), "Unsicher": ("0", "-1", "ok"), "Großer Block": ("0", "-2", "ok")}


@pytest.fixture(autouse=True)
def clean_cache():
    """st.cache_data ist prozessweit: Tests, die Funktionen ersetzen, dürfen keine zwischengespeicherten Ergebnisse anderer Tests sehen."""
    import streamlit as st
    st.cache_data.clear()
    yield


def fresh(**query):
    at = AppTest.from_file(APP, default_timeout=180)
    for k, v in query.items():
        at.query_params[k] = v
    at.run()
    assert not at.exception, at.exception
    return at


def set_and_run(at, **values):
    for key, value in values.items():
        (at.number_input if key.endswith("_input") else at.slider)(key=key).set_value(value)
    at.run()
    assert not at.exception, at.exception
    return at


def main_metrics(at):
    return [(m.label, m.value, m.delta) for m in at.metric[:4]]


def click(at, label):
    next(b for b in at.button if b.label == label).click().run()
    assert not at.exception, at.exception
    return at


def message(at, needle):
    for group in (at.success, at.warning, at.info):
        for x in group:
            if needle in x.value:
                return x.value
    return None


# ---------------------------------------------------------------------------------------------------
# Skelett
# ---------------------------------------------------------------------------------------------------
def test_skeleton_and_footer():
    at = fresh()
    assert [h.value for h in at.sidebar.header] == ["⚙️ Einstellungen"]                # genau EIN Header
    assert len(at.title) == 1 and "Reefer" in at.title[0].value
    assert any(v.value.startswith("## 🎯") for v in at.markdown)
    assert [s.value for s in at.subheader] == ["📐 Wie viel Puffer ist richtig?"]
    assert [e.label for e in at.expander] == ["🔧 Wie wir das erreichen – Regeln im Vergleich", "Wie funktioniert diese Demo?", "📐 Mathematische Formulierung"]
    assert any(c.value == FOOTER for c in at.caption)
    presets = [b.label for b in at.button if b.label in C.PRESETS]
    assert presets == list(C.PRESETS) and len(presets) == 5 and all(len(n) <= 16 for n in presets)
    assert [s.label for s in at.sidebar.slider] == ["Stapel im Block", "Höhe (Lagen)", "Füllgrad (%)", "Container", "Reefer-Anteil (%)", "Steckdosen-Stapel", "Puffer (Steckdosen-Plätze)",
                                                    "Schätzfehler der Abfahrt (% der mittleren Standzeit)"]
    assert [n.label for n in at.sidebar.number_input] == ["Seed"] and any(b.label == "🎲 Neuer Block" for b in at.sidebar.button)


def test_main_metrics_are_2x2_for_the_puffer_rule_with_signed_deltas_against_egal():
    at = fresh()
    assert [m[0] for m in main_metrics(at)] == ["Reefer ohne Strom", "davon blockiert", "Umstapelungen je Abholung", "Steckdosen-Auslastung"]
    assert [m[1] for m in main_metrics(at)] == ["0", "0", "0.72", "24 %"]
    assert [m[2] for m in main_metrics(at)] == ["-1", "-1", "-0.06", "+3 Punkte"]
    colors = [m.proto.color for m in at.metric[:4]]
    assert colors[:3] == [MetricProto.GREEN] * 3                                          # weniger = besser = grün ("inverse")
    assert all(len(m[0]) <= 26 for m in main_metrics(at))


def test_main_caption_and_success_message_quote_the_block_and_both_rules():
    at = fresh()
    cap = [c.value for c in at.caption if "Steckdosen-Plätze" in c.value and "kommen" in c.value][0]
    assert "8 Stapel, davon 3 mit Steckdosen (15 Steckdosen-Plätze)" in cap and "höchstens 28 Container" in cap and "kommen 53 Reefer von 300 Containern an" in cap and "B = 6" in cap
    msg = message(at, "bekommt jeder der 53 Reefer Strom")
    assert "Mit Puffer 6" in msg and "bei 215 Umstapelungen (Steckdosen egal: 233 Umstapelungen und 1 Reefer ohne Strom)" in msg and "+26 % Umstapelungen" in msg


def test_core_section_metrics_show_buffer_rule_of_thumb_and_plug_slots():
    at = fresh()
    assert [(m.label, m.value) for m in at.metric[4:7]] == [("Puffer (eingestellt)", "6"), ("Faustregel", "6"), ("Steckdosen-Plätze", "15")]
    at = set_and_run(at, reefer_slider=30)
    assert [(m.label, m.value) for m in at.metric[4:7]] == [("Puffer (eingestellt)", "6"), ("Faustregel", "8"), ("Steckdosen-Plätze", "15")]


def test_the_caption_bases_name_the_sample_and_the_curves():
    at = fresh()
    caps = [c.value for c in at.caption]
    assert any("Basis: 50 Blöcke (Seeds 0-49, nicht Ihr Seed)" in c for c in caps)
    assert any("Basis: 30 Blöcke (Seeds 0-29, nicht Ihr Seed) mit Ihren Einstellungen. Puffer 0 ist Steckdosen egal, Puffer 15 ist alles reserviert" in c for c in caps)
    assert any("Basis: 30 Blöcke (Seeds 0-29); der Puffer folgt hier je Stapelzahl der Faustregel" in c for c in caps)


def test_charts_are_present_with_unique_keys():
    at = fresh()
    charts = at.get("plotly_chart")
    keys = [c.key for c in charts]
    assert len(charts) == 12                                                              # 2 Blöcke, 2 Puffer-Kurven, 2 Verteilungen, Steckdosen-Kurve, 3 Regel-Tabs, Vergleich (2)
    assert len(set(keys)) == 12 and all(keys)


# ---------------------------------------------------------------------------------------------------
# Presets, Permalink
# ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("name", list(C.PRESETS))
def test_every_preset_loads_within_widget_bounds_and_shows_its_story(name):
    at = fresh()
    click(at, name)
    p = C.PRESETS[name]
    assert at.slider(key="reefer_slider").value == p["reefer_pct"] and at.slider(key="plugs_slider").value == p["plug_stacks"] and at.slider(key="buffer_slider").value == p["buffer"]
    assert at.slider(key="n_stacks_slider").value == p["n_stacks"] and at.number_input(key="seed_input").value == p["seed"]
    for state_key, spec in SETTING_SPECS.items():
        if spec.lo is not None:
            value = at.session_state[state_key]
            assert spec.lo <= value <= spec.hi and (spec.step in (None, 1) or (value - spec.lo) % spec.step == 0)
    value, delta, kind = EXPECTED[name]
    assert main_metrics(at)[0][1:] == (value, delta)
    texts = {"ok": "bekommt jeder der", "capacity": "es fehlen Steckdosen-Stapel"}
    assert message(at, texts[kind]) is not None, name
    assert at.slider(key="plugs_slider").max == p["n_stacks"] - 1 and at.slider(key="buffer_slider").max == p["plug_stacks"] * p["max_height"]


def test_permalink_is_clamped_snapped_and_ignores_garbage():
    at = fresh(rp="23", fp="86", vw="junk", ns="abc", sg="60", nc="330")
    assert at.slider(key="reefer_slider").value == 25 and at.slider(key="fill_slider").value == 90 and at.slider(key="sigma_slider").value == 50 and at.slider(key="n_containers_slider").value == 350
    assert at.radio(key="view_radio").value == C.VIEW_DEFAULT and at.slider(key="n_stacks_slider").value == C.N_STACKS_DEFAULT


def test_permalink_limits_the_dependent_settings_instead_of_dropping_them():
    at = fresh(ns="4", ps="9", bf="99")
    assert at.slider(key="n_stacks_slider").value == 4 and at.slider(key="plugs_slider").value == 3                # Stapel minus 1
    assert at.slider(key="buffer_slider").value == 15 and at.slider(key="buffer_slider").max == 15                   # 3 Stapel mal 5 Lagen


def test_permalink_roundtrip_reflects_settings():
    at = fresh(ns="6", mh="4", fp="70", nc="200", rp="30", ps="2", sg="100", bf="5", seed="11", vw="reserviert")
    assert at.query_params["ns"] == ["6"] or at.query_params["ns"] == "6"
    values = {k: at.session_state[k] for k in SETTING_SPECS}
    assert values == {"n_stacks_slider": 6, "max_height_slider": 4, "fill_slider": 70, "n_containers_slider": 200, "reefer_slider": 30, "plugs_slider": 2, "sigma_slider": 100, "buffer_slider": 5,
                      "seed_input": 11, "view_radio": "reserviert"}
    for key, spec in SETTING_SPECS.items():
        got = at.query_params[spec.url_param]
        got = got[0] if isinstance(got, list) else got
        assert got == spec.encoder(values[key]), key


def test_changing_the_stack_count_limits_plug_stacks_and_buffer():
    at = fresh()
    click(at, "Zu viele")                                                              # 4 Steckdosen-Stapel, Puffer 3
    at = set_and_run(at, n_stacks_slider=4)
    assert at.slider(key="plugs_slider").value == 3 and at.slider(key="plugs_slider").max == 3 and at.slider(key="buffer_slider").value == 3
    at = set_and_run(at, plugs_slider=1)
    assert at.slider(key="buffer_slider").max == 5 and at.slider(key="buffer_slider").value == 3
    at = set_and_run(at, buffer_slider=5)
    at = set_and_run(at, max_height_slider=2)
    assert at.slider(key="buffer_slider").max == 2 and at.slider(key="buffer_slider").value == 2                      # Puffer folgt den Steckdosen-Plätzen


def test_new_block_button_changes_only_the_seed():
    at = fresh()
    before = {k: at.session_state[k] for k in SETTING_SPECS if k != "seed_input"}
    click(at, "🎲 Neuer Block")
    assert {k: at.session_state[k] for k in SETTING_SPECS if k != "seed_input"} == before and 0 <= at.session_state["seed_input"] <= 9999


# ---------------------------------------------------------------------------------------------------
# Bedingte Meldung
# ---------------------------------------------------------------------------------------------------
def test_message_blocked_when_normal_containers_take_the_plugs():
    at = set_and_run(fresh(), buffer_slider=0)                                          # Puffer 0 ist Steckdosen egal
    msg = message(at, "stehen ohne Strom")
    assert "**1 Reefer stehen ohne Strom**, 1 davon, weil Normalcontainer die Steckdosen belegen" in msg and "(Faustregel: 6)" in msg
    assert main_metrics(at)[0][1:] == ("1", "+0")


def test_message_capacity_when_no_plug_stack_exists():
    at = set_and_run(fresh(), plugs_slider=0)
    msg = message(at, "stehen ohne Strom")
    assert "**53 Reefer stehen ohne Strom**, weil alle 0 Steckdosen-Plätze schon Reefer tragen: es fehlen Steckdosen-Stapel, keine Regel hilft." in msg
    assert [s.label for s in at.sidebar.slider if s.label.startswith("Puffer")] == []                                # kein Puffer-Regler ohne Steckdosen
    assert any("Puffer: ohne Steckdosen-Stapel" in c.value for c in at.sidebar.caption)
    assert any("Ohne Steckdosen-Stapel gibt es keinen Puffer" in i.value for i in at.info)
    assert main_metrics(at)[3][1] == "–"                                                                              # keine Auslastung ohne Steckdosen


def test_message_capacity_names_the_plug_slots_and_the_reserve_cost():
    at = click(fresh(), "Zu wenige")
    msg = message(at, "es fehlen Steckdosen-Stapel")
    assert "**1 Reefer stehen ohne Strom**, weil alle 10 Steckdosen-Plätze schon Reefer tragen" in msg and "-9 % Umstapelungen" in msg


def test_message_without_reefers_says_the_plug_stacks_only_cost_space():
    at = set_and_run(fresh(), reefer_slider=0)
    msg = message(at, "kein Reefer an")
    assert "kommt kein Reefer an: die Steckdosen-Stapel kosten nur Platz." in msg and "+90 % Umstapelungen" in msg
    assert main_metrics(at)[0][1] == "0" and main_metrics(at)[0][2] == "+0"


# ---------------------------------------------------------------------------------------------------
# Regler an den Grenzen
# ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("key,value", [("n_stacks_slider", 4), ("n_stacks_slider", 12), ("max_height_slider", 2), ("max_height_slider", 6), ("fill_slider", 40), ("fill_slider", 100),
                                       ("n_containers_slider", 100), ("n_containers_slider", 500), ("reefer_slider", 0), ("reefer_slider", 50), ("plugs_slider", 0), ("plugs_slider", 7),
                                       ("sigma_slider", 0), ("sigma_slider", 200), ("buffer_slider", 0), ("buffer_slider", 15)])
def test_every_slider_works_at_its_minimum_and_maximum(key, value):
    at = set_and_run(fresh(), **{key: value})
    assert at.session_state[key] == value and len(at.metric) >= 7


def test_extreme_combination_runs_without_exception():
    at = fresh(ns="4", mh="2", fp="100", nc="500", rp="50", ps="3", sg="200", bf="6")
    assert not at.exception and at.slider(key="buffer_slider").max == 6
    at = fresh(ns="12", mh="6", fp="100", nc="500", rp="50", ps="11", sg="200", bf="66")
    assert not at.exception and at.slider(key="buffer_slider").value == 66


# ---------------------------------------------------------------------------------------------------
# Stichprobe, Kurven, Urteil
# ---------------------------------------------------------------------------------------------------
def test_three_verdict_sentences_with_the_right_labels():
    at = fresh()
    texts = [x.value for group in (at.success, at.warning, at.info) for x in group if "Puffer gegen" in x.value or "reserviert gegen Puffer" in x.value]
    assert len(texts) == 3
    assert any("Puffer gegen Steckdosen egal, Reefer ohne Strom" in t and "98 % weniger" in t for t in texts)
    assert any("Kein klarer Unterschied bei **Puffer gegen Steckdosen egal, Umstapelungen**" in t for t in texts)
    assert any("Steckdosen reserviert gegen Puffer, Umstapelungen" in t and "17 % mehr" in t for t in texts)


def _fake_verdict(monkeypatch, kind, pct):
    monkeypatch.setattr(E, "verdict", lambda res, key, ref, field="unpowered": E.Verdict(kind, -2.0 if kind == "better" else 2.0, 0.5, pct, 20, field))


@pytest.mark.parametrize("kind,pct,expected", [
    ("better", -40.0, "im Mittel **40 % weniger** Reefer ohne Strom (-2.00 je Block, Standardfehler 0.50)."),
    ("better", None, "im Mittel **2.00 weniger** Reefer ohne Strom (-2.00 je Block, Standardfehler 0.50)."),
    ("worse", 25.0, "im Mittel **25 % mehr** Reefer ohne Strom (+2.00 je Block, Standardfehler 0.50)."),
    ("worse", None, "im Mittel **2.00 mehr** Reefer ohne Strom (+2.00 je Block, Standardfehler 0.50)."),
])
def test_verdict_sentences_in_the_four_variants(monkeypatch, kind, pct, expected):
    _fake_verdict(monkeypatch, kind, pct)
    at = fresh()
    texts = [x.value for x in (at.success if kind == "better" else at.warning) if "im Mittel" in x.value and "Reefer ohne Strom" in x.value]
    assert len(texts) >= 1 and all(expected in t for t in texts[:1])
    assert all(t.count("(") == t.count(")") for t in texts)


def test_verdict_unclear(monkeypatch):
    _fake_verdict(monkeypatch, "unclear", 1.0)
    at = fresh()
    us = [i.value for i in at.info if "Kein klarer Unterschied" in i.value]
    assert len(us) == 3 and all("Rauschens" in u and "gemittelt über die Blöcke" in u for u in us)


def test_the_sample_does_not_depend_on_the_seed():
    at = fresh()
    before = [c.value for c in at.caption if "Im Mittel je Block" in c.value]
    at = set_and_run(at, seed_input=5)
    assert [c.value for c in at.caption if "Im Mittel je Block" in c.value] == before and len(before) == 1


# ---------------------------------------------------------------------------------------------------
# Blick in den Block
# ---------------------------------------------------------------------------------------------------
def test_event_slider_starts_at_the_first_reefer_without_power_and_resets_with_a_new_block():
    at = fresh()
    p = E.Params(8, 5, 80, 300, 20, 3, 50, 6)
    inst, est, reefer = E.make_block(p, 490)
    egal = E.outcome_of(E.run_rules(p, inst, est, reefer, record=True), EG).result
    first = next(k for k, s in enumerate(egal.steps, 1) if s.arrival_unpowered)
    assert at.slider(key="event_slider").value == first == 448 and at.slider(key="event_slider").max == 600
    at = set_and_run(at, event_slider=10)
    assert at.slider(key="event_slider").value == 10
    at = set_and_run(at, seed_input=491)
    assert at.slider(key="event_slider").value != 10


def test_captions_describe_the_event_and_the_view_radio_switches_the_right_rule():
    at = fresh()
    assert any(c.value.startswith("Ereignis 448 von 600: Reefer 237 kommt an") and "ohne Strom" in c.value for c in at.caption)
    assert at.radio(key="view_radio").value == PU and list(at.radio(key="view_radio").options) == [C.RULE_LABELS[k] for k in C.RIGHT_VIEW_KEYS]
    at = at.radio(key="view_radio").set_value(RS).run()
    assert not at.exception and at.query_params["vw"] in ("reserviert", ["reserviert"])
    assert any(C.RULE_LABELS[RS] in c.value for c in at.caption if c.value.startswith("Links Steckdosen egal"))


# ---------------------------------------------------------------------------------------------------
# Regelvergleich, PDF, Texte
# ---------------------------------------------------------------------------------------------------
def test_comparison_table_has_a_row_per_rule_with_the_right_cells():
    at = fresh()
    df = at.dataframe[0].value
    assert list(df["Regel"]) == [C.RULE_LABELS[k] for k in C.RULE_KEYS] and list(df["Puffer"]) == [0, 6, 15]
    assert list(df["Reefer ohne Strom"]) == [1, 0, 0] and list(df["Umstapelungen"]) == [233, 215, 293]
    assert list(df["davon blockiert"]) == [1, 0, 0] and list(df["davon Kapazität"]) == [0, 0, 0]
    assert list(df["Delta ohne Strom"]) == [0, -1, -1] and list(df["Delta Umstapelungen"]) == [0, -18, 60]
    assert list(df["je Abholung"]) == [0.78, 0.72, 0.98]


def test_each_rule_tab_shows_its_metrics_with_deltas_against_egal():
    at = fresh()
    labels = [m.label for m in at.metric[7:]]
    assert labels.count("Reefer ohne Strom") == 3 and labels.count("davon blockiert") == 3                           # drei Regel-Tabs
    tab_metrics = at.metric[7:]
    egal = tab_metrics[0:4]
    assert [m.delta for m in egal] == ["", "", "", ""]                                                              # Referenz ohne Delta
    puffer = tab_metrics[4:8]
    assert [m.value for m in puffer] == ["0", "0", "0.72", "24 %"] and [m.delta for m in puffer[:3]] == ["-1", "-1", "-0.06"]


def test_pdf_download_button_is_offered():
    at = fresh()
    buttons = at.get("download_button")
    assert len(buttons) == 1 and buttons[0].proto.label == "📄 Ergebnis als PDF herunterladen"


def test_texts_state_the_rules_the_assumptions_and_the_limits():
    at = fresh()
    text = "\n".join(m.value for m in at.expander[1].markdown)
    for needle in ("Steckdosen egal", "Steckdosen-Puffer", "Steckdosen reserviert", "Faustregel", "durch Normalcontainer blockiert", "Kapazität erschöpft", "Reefer-Racks",
                   "Größenordnungen aus einer Simulation", "bleibt dort bis zur Abholung"):
        assert needle in text, needle
    math = "\n".join(m.value for m in at.expander[2].markdown)
    for needle in ("Steckdosen-Plätze $K = sH$", "Bestfit", "$B \\ge K$ ist **reserviert**", "\\operatorname{round}(q \\cdot N_{\\max})", "2\\,\\mathrm{SE}"):
        assert needle in math, needle
    assert "Anschlussleistung" in text and "Temperaturklassen" in text
