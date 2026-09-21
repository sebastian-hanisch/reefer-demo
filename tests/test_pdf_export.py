import re

import pytest

import rfr_constants as C
import rfr_evaluation as E
import rfr_simulation as SIM
from rfr_evaluation import BlockResult
from rfr_pdf_export import diagnosis_text, generate_rfr_pdf, pdf_text, short_name, verdict_text

EG, PU, RS = C.RULE_EGAL, C.RULE_PUFFER, C.RULE_RESERVIERT
P = E.Params(8, 5, 80, 300, 20, 3, 50, 6)


def _make(p=P, seed=490, sample=None, curve=None, compress=False):
    inst, est, reefer = E.make_block(p, seed)
    outs = E.run_rules(p, inst, est, reefer)
    diag = E.diagnose(outs)
    return generate_rfr_pdf(p, seed, inst, outs, diag, sample=sample, curve=curve, compress=compress), inst, outs, diag


def _texts(data):
    """Alle Textstücke des (unkomprimierten) PDFs als Liste, Latin-1 gelesen, PDF-Escapes aufgelöst."""
    raw = re.findall(rb"\((.*?)\)\s*Tj", data)
    return [t.decode("latin-1").replace(r"\(", "(").replace(r"\)", ")").replace(r"\\", "\\") for t in raw]


def br(seed, un=(5, 2, 0), mv=(100, 104, 130)):
    keys = (EG, PU, RS)
    return BlockResult(seed, 100, 20, dict(zip(keys, mv)), dict(zip(keys, un)), dict(zip(keys, un)), dict(zip(keys, (0, 0, 0))), dict(zip(keys, (0.3, 0.3, 0.3))))


# ---------- Sonderzeichen: mit den GENAUEN Zeichen testen (fpdf2 stürzt bei "–" und "€" ab) ----------
EXPECTED = {"–": "-", "—": "-", "−": "-", "€": "EUR", "Σ": "Summe", "δ": "Delta", "σ": "sigma", "≥": ">=", "≤": "<=", "→": "->", "≈": "ca.", "„": '"', "“": '"', "’": "'", "·": "-",
            "±": "+-", "⚠️": "(!)", "⚠": "(!)", "⚡": "", "✅": "", "ℹ️": ""}


@pytest.mark.parametrize("char,replacement", list(EXPECTED.items()))
def test_pdf_text_replaces_every_known_troublemaker_with_a_readable_equivalent(char, replacement):
    out = pdf_text(f"a{char}b")
    out.encode("latin-1")
    assert out == f"a{replacement}b"


def test_pdf_text_keeps_umlauts_and_times_sign_and_replaces_unknown():
    assert pdf_text("Füllgrad äöüß ÄÖÜ × 3") == "Füllgrad äöüß ÄÖÜ × 3"
    assert pdf_text("日本語").encode("latin-1") == b"???"
    assert "?" in pdf_text("🛡️ Puffer")


def test_short_names_have_no_emoji_and_survive_latin_1():
    for key in C.RULE_KEYS:
        assert pdf_text(short_name(key)) == short_name(key) and "<br>" not in short_name(key)
    assert [short_name(k) for k in C.RULE_KEYS] == ["Egal", "Puffer", "Reserviert"]


# ---------- Sätze ----------
def test_verdict_text_covers_all_states_and_survives_latin_1():
    better = tuple(br(i, un=(5 + i % 2, 2, 0)) for i in range(20))
    worse = tuple(br(i, un=(2, 5 + i % 2, 0)) for i in range(20))
    unclear = tuple(br(i, un=(3, 3 + (1 if i % 2 else -1), 0)) for i in range(20))
    for sample, expected in ((better, "% weniger Reefer ohne Strom"), (worse, "% mehr Reefer ohne Strom"), (unclear, "kein klarer Unterschied")):
        text = verdict_text(sample, "L", PU, EG, "unpowered", "Reefer ohne Strom")
        assert text.startswith("L:") and expected in text
        text.encode("latin-1")
    assert "im Mittel 64 % weniger Reefer ohne Strom" in verdict_text(better, "L", PU, EG, "unpowered", "Reefer ohne Strom")               # (2 - 5,5) / 5,5 = -63,6 %: ohne Vorzeichen
    assert "im Mittel 175 % mehr Reefer ohne Strom" in verdict_text(worse, "L", PU, EG, "unpowered", "Reefer ohne Strom")
    assert "in 0 % der Blöcke ist es umgekehrt" in verdict_text(better, "L", PU, EG, "unpowered", "Reefer ohne Strom")
    assert "in 0 % der Blöcke ist es besser" in verdict_text(worse, "L", PU, EG, "unpowered", "Reefer ohne Strom")
    assert "gemittelt über die Blöcke" in verdict_text(unclear, "L", PU, EG, "unpowered", "Reefer ohne Strom")


def test_verdict_text_without_a_percentage_when_the_reference_needs_nothing():
    res = tuple(br(i, un=(0, 1, 0)) for i in range(5))
    t = verdict_text(res, "L", PU, EG, "unpowered", "Reefer ohne Strom")
    assert "+1.00 Reefer ohne Strom" not in t and "1.00 mehr Reefer ohne Strom" in t and "%" not in t.split("(")[0]


def test_verdict_text_better_without_a_percentage_is_defensive_and_does_not_crash(monkeypatch):
    monkeypatch.setattr(E, "verdict", lambda res, key, ref, field="unpowered": E.Verdict("better", -2.0, 0.5, None, 20, field))
    t = verdict_text(tuple(br(i) for i in range(4)), "L", PU, EG, "unpowered", "Reefer ohne Strom")
    assert "im Mittel 2.00 weniger Reefer ohne Strom (-2.00 je Block" in t and "%" not in t.split("(")[0]


@pytest.mark.parametrize("kind,expected", [("no_reefers", "kein Reefer"), ("ok", "Mit Puffer 6 bekommt jeder Reefer Strom"), ("blocked", "weil Normalcontainer die Steckdosen belegen"),
                                           ("capacity", "es fehlen Steckdosen-Stapel")])
def test_diagnosis_text_kinds(kind, expected):
    d = E.Diagnosis(kind, 4, 3, 1, 26.0)
    text = diagnosis_text(d, 6, 6, 15)
    assert expected in text and "+26 % Umstapelungen" in text
    text.encode("latin-1")
    assert "Umstapelungen kosten" not in diagnosis_text(E.Diagnosis(kind, 4, 3, 1, None), 6, 6, 15)
    if kind == "blocked":
        assert "Faustregel: 6" in text and "4 Reefer stehen ohne Strom, 3 davon" in text
    if kind == "capacity":
        assert "alle 15 Steckdosen-Plätze" in text


# ---------- Inhalt ----------
def test_pdf_is_a_valid_document_with_all_sections_without_sample():
    data, inst, outs, diag = _make()
    assert data.startswith(b"%PDF") and data.endswith(b"%%EOF\n") and len(data) > 2000
    text = _texts(data)
    for label in ("Reefer im Block: Wer darf auf die Steckdosen?", "Szenario", "Zusammenfassung", "Regelvergleich (dieser Block)", "Hinweise zum Modell"):
        assert label in text, label
    assert "Stichprobe und Urteil" not in text and "Puffer-Kurve" not in text


def test_pdf_scenario_block_pairs_every_label_with_its_own_value():
    data, inst, outs, diag = _make()
    text = _texts(data)

    def value(label):
        return text[text.index(label) + 1]
    assert value("Block") == "8 Stapel, 5 Lagen, Füllgrad 80 % (höchstens 28 Container gleichzeitig)"
    assert value("Container") == f"300, davon Reefer-Anteil 20 % ({outs[1].result.reefer_arrivals} Reefer in diesem Block)"
    assert value("Steckdosen-Stapel") == "3 (15 Steckdosen-Plätze)" and value("Puffer / Faustregel") == "6 / 6"
    assert value("Schätzfehler der Abfahrt") == "50 % der mittleren Standzeit" and value("Seed") == "490"


def test_pdf_summary_quotes_each_rule_with_its_own_counts():
    data, inst, outs, diag = _make()
    text = _texts(data)
    for o in outs:
        line = text[text.index(short_name(o.key), text.index("Zusammenfassung")) + 1]
        assert line == f"{o.result.unpowered} Reefer ohne Strom, {o.result.moves} Umstapelungen ({o.result.moves_per_retrieval:.2f} je Abholung)"
    assert any(diagnosis_text(diag, 6, 6, 15)[:40] in t for t in text)


def test_pdf_rule_table_has_one_row_per_rule_with_the_right_cells():
    data, inst, outs, diag = _make(seed=490)
    text = _texts(data)
    start = text.index("Regelvergleich (dieser Block)") + 9                      # acht Kopfzellen
    assert text[start - 8: start] == ["Regel", "Puffer", "ohne Strom", "blockiert", "Kapazität", "Umstapelungen", "je Abholung", "Auslastung (%)"]
    for i, o in enumerate(outs):
        r = o.result
        row = text[start + 8 * i: start + 8 * i + 8]
        assert row == [short_name(o.key), str(o.buffer), str(r.unpowered), str(r.blocked), str(r.capacity_short), str(r.moves), f"{r.moves_per_retrieval:.2f}", f"{r.plug_utilisation * 100:.0f}"]


def test_pdf_with_sample_and_curve_adds_the_sections_and_quotes_the_verdicts():
    inst, est, reefer = E.make_block(P, 490)
    sample = E.sample(P, 8)
    curve = E.buffer_curve(P, 3)
    data, *_ = _make(sample=sample, curve=curve)
    text = _texts(data)
    assert "Stichprobe und Urteil" in text and "Puffer-Kurve" in text
    joined = " ".join(text)
    for label, key, ref, field, unit in (("Puffer gegen Steckdosen egal, Reefer ohne Strom", PU, EG, "unpowered", "Reefer ohne Strom"),
                                         ("Puffer gegen Steckdosen egal, Umstapelungen", PU, EG, "moves_pr", "Umstapelungen je Abholung"),
                                         ("Steckdosen reserviert gegen Puffer, Umstapelungen", RS, PU, "moves_pr", "Umstapelungen je Abholung")):
        assert verdict_text(sample, label, key, ref, field, unit)[:60] in joined
    start = text.index("Puffer-Kurve") + 6
    s = curve.series["Puffer"]
    assert text[start: start + 5] == [str(curve.xs[0]), f"{s['unpowered'][0]:.2f}", f"{s['blocked'][0]:.2f}", f"{s['capacity_short'][0]:.2f}", f"{s['moves_pr'][0]:.3f}"]
    assert f"Mittel je Block über {curve.n_blocks} Blöcke" in joined


def test_pdf_sample_table_quotes_the_means_per_rule():
    sample = E.sample(P, 6)
    data, *_ = _make(sample=sample)
    text = _texts(data)
    start = text.index("Stichprobe und Urteil") + 4                              # drei Kopfzellen
    for i, k in enumerate(C.RULE_KEYS):
        assert text[start + 3 * i: start + 3 * i + 3] == [short_name(k), f"{E.mean_of(sample, k):.2f}", f"{E.mean_of(sample, k, 'moves_pr'):.3f}"]


# ---------- Ränder ----------
@pytest.mark.parametrize("plugs,reefer_pct", [(0, 20), (3, 0), (7, 50), (1, 10)])
def test_pdf_is_generated_for_the_edge_cases_compressed_and_uncompressed(plugs, reefer_pct):
    p = P._replace(plug_stacks=plugs, reefer_pct=reefer_pct, buffer=min(6, plugs * 5))
    for compress in (True, False):
        data, *_ = _make(p, sample=E.sample(p, 3), curve=E.buffer_curve(p, 2), compress=compress)
        assert data.startswith(b"%PDF") and len(data) > 1500


def test_pdf_without_plug_stacks_has_no_curve_section_and_shows_a_dash_for_the_utilisation():
    p = P._replace(plug_stacks=0, buffer=0)
    data, *_ = _make(p, curve=E.buffer_curve(p, 2))
    text = _texts(data)
    assert "Puffer-Kurve" not in text and "-" in text[text.index("Regelvergleich (dieser Block)") + 9 + 7: text.index("Regelvergleich (dieser Block)") + 9 + 8]


def test_pdf_utf8_only_characters_in_scenario_texts_do_not_crash():
    inst, est, reefer = E.make_block(P, 3)
    outs = E.run_rules(P, inst, est, reefer)
    diag = E.Diagnosis("blocked", 2, 2, 0, None)
    assert generate_rfr_pdf(P, 3, inst, outs, diag)[:4] == b"%PDF"


def test_simulation_result_type_is_what_the_pdf_reads():
    r = SIM.Result(1, 1, 1, 1, (1,), (), 1, 0, 0, 0, 0, None)
    assert r.moves_per_retrieval == 1.0 and r.plug_utilisation is None
