"""PDF-Export des Ergebnisses (fpdf2, Helvetica-Kernschrift, nur Text und Tabellen).

Die Kernschriften kennen nur Latin-1: Umlaute und "×" sind erlaubt, aber "–" (Gedankenstrich), "−" (Minuszeichen), "€", "Σ", "≥", "≤", Emoji usw. lassen fpdf2 abstürzen. Deshalb läuft jeder Text
durch pdf_text(); Regeln erscheinen mit ihren Kurznamen ohne Emoji."""

import time

import rfr_constants as C
import rfr_evaluation as E

_REPLACEMENTS = {
    "–": "-", "—": "-", "‑": "-", "−": "-", "Σ": "Summe", "δ": "Delta", "σ": "sigma", "≥": ">=", "≤": "<=", "→": "->", "≈": "ca.", "€": "EUR", "⚡": "",
    "·": "-", "“": '"', "”": '"', "„": '"', "’": "'", "‘": "'", "±": "+-", "⚠️": "(!)", "⚠": "(!)", "✅": "", "ℹ️": "",
}
EG, PU, RS = C.RULE_EGAL, C.RULE_PUFFER, C.RULE_RESERVIERT


def pdf_text(text):
    """Text für die Helvetica-Kernschrift: bekannte Sonderzeichen ersetzen, den Rest Latin-1-sicher machen."""
    for old, new in _REPLACEMENTS.items():
        text = text.replace(old, new)
    return text.encode("latin-1", "replace").decode("latin-1")


def short_name(key):
    return C.RULE_SHORT[key]


def verdict_text(sample, label, key, reference, field, unit):
    """Ein Satz je Vergleich, wie im Kernabschnitt der App (ohne Emoji)."""
    v = E.verdict(sample, key, reference, field)
    d = E.distribution(sample, key, reference, field)
    if v.kind == "better":
        amount = f"{abs(v.pct):.0f} % weniger" if v.pct is not None else f"{abs(v.diff):.2f} weniger"
        return f"{label}: im Mittel {amount} {unit} ({v.diff:+.2f} je Block, Standardfehler {v.se:.2f}); in {d.worse * 100:.0f} % der Blöcke ist es umgekehrt."
    if v.kind == "worse":
        amount = f"{v.pct:.0f} % mehr" if v.pct is not None else f"{v.diff:.2f} mehr"
        return f"{label}: im Mittel {amount} {unit} ({v.diff:+.2f} je Block, Standardfehler {v.se:.2f}); in {d.better * 100:.0f} % der Blöcke ist es besser."
    return (f"{label}: kein klarer Unterschied, die Differenz ({v.diff:+.2f} {unit}, gemittelt über die Blöcke) liegt innerhalb des Rauschens (Standardfehler {v.se:.2f}); "
            f"besser in {d.better * 100:.0f} %, schlechter in {d.worse * 100:.0f} % der Blöcke.")


def diagnosis_text(diag, buffer, thumb, slots):
    """Die bedingte Meldung der App als Satz ohne Emoji."""
    extra = "" if diag.reserve_extra_moves_pct is None else f" Das strenge Reservieren würde {diag.reserve_extra_moves_pct:+.0f} % Umstapelungen kosten."
    if diag.kind == "no_reefers":
        return "In diesem Block kommt kein Reefer an: die Steckdosen-Stapel kosten nur Platz." + extra
    if diag.kind == "ok":
        return f"Mit Puffer {buffer} bekommt jeder Reefer Strom." + extra
    if diag.kind == "blocked":
        return f"{diag.unpowered} Reefer stehen ohne Strom, {diag.blocked} davon, weil Normalcontainer die Steckdosen belegen: ein größerer Puffer schützt sie (Faustregel: {thumb})." + extra
    return f"{diag.unpowered} Reefer stehen ohne Strom, weil alle {slots} Steckdosen-Plätze schon Reefer tragen: es fehlen Steckdosen-Stapel, keine Regel hilft." + extra


def generate_rfr_pdf(p, seed, instance, outcomes, diag, sample=None, curve=None, compress=True):
    """Ergebnis der aktuellen Einstellung als PDF: Szenario, Zusammenfassung, Regelvergleich, optional Stichprobe/Urteil und Puffer-Kurve, Hinweise.

    `p`: E.Params; `outcomes`: die drei Outcomes (eines Blocks); `diag`: E.Diagnosis; `sample`: Tupel von BlockResult oder None; `curve`: E.Curve (Puffer-Kurve) oder None."""
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    by_key = {o.key: o for o in outcomes}
    egal, puf = by_key[EG], by_key[PU]
    slots, thumb = E.slots_of(p), E.thumb_of(p)

    pdf = FPDF()
    pdf.set_compression(compress)
    pdf.add_page()

    def line(text, height=7, width=0):
        pdf.cell(width, height, pdf_text(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def heading(text):
        pdf.set_font("Helvetica", "B", 12)
        line(text, 8)
        pdf.set_font("Helvetica", "", 10)

    def pairs(rows):
        for label, value in rows:
            pdf.cell(70, 6, pdf_text(label), border=0)
            line(value, 6)

    def table(headers, widths, rows):
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(230, 230, 230)
        for header, width in zip(headers, widths):
            pdf.cell(width, 7, pdf_text(header), border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.ln(7)
        pdf.set_font("Helvetica", "", 9)
        for row in rows:
            for value, width in zip(row, widths):
                pdf.cell(width, 7, pdf_text(str(value)), border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.ln(7)

    def keep_together(height):
        """Beginnt einen Abschnitt auf einer neuen Seite, wenn er sonst über den Seitenumbruch liefe (keine halb abgeschnittenen Listen)."""
        if pdf.get_y() + height > pdf.h - pdf.b_margin:
            pdf.add_page()

    def note(text, size=8):
        pdf.set_font("Helvetica", "I", size)
        pdf.set_text_color(110, 110, 110)
        pdf.multi_cell(0, 5, pdf_text(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(0, 0, 0)

    pdf.set_font("Helvetica", "B", 16)
    line("Reefer im Block: Wer darf auf die Steckdosen?", 10)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(120, 120, 120)
    line(f"Erstellt: {time.strftime('%d.%m.%Y %H:%M')}  -  sebastianhanisch.net", 6)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    heading("Szenario")
    pairs([("Block", f"{p.n_stacks} Stapel, {p.max_height} Lagen, Füllgrad {p.fill_pct} % (höchstens {E.capacity_of(p)} Container gleichzeitig)"),
           ("Container", f"{p.n_containers}, davon Reefer-Anteil {p.reefer_pct} % ({puf.result.reefer_arrivals} Reefer in diesem Block)"),
           ("Steckdosen-Stapel", f"{p.plug_stacks} ({slots} Steckdosen-Plätze)"), ("Puffer / Faustregel", f"{puf.buffer} / {thumb}"),
           ("Schätzfehler der Abfahrt", f"{p.sigma_pct} % der mittleren Standzeit"), ("Seed", str(seed))])
    pdf.ln(3)

    heading("Zusammenfassung")
    note(diagnosis_text(diag, puf.buffer, thumb, slots), 9)
    pairs([(short_name(o.key), f"{o.result.unpowered} Reefer ohne Strom, {o.result.moves} Umstapelungen ({o.result.moves_per_retrieval:.2f} je Abholung)") for o in outcomes])
    pdf.ln(3)

    heading("Regelvergleich (dieser Block)")
    rows = []
    for o in outcomes:
        r = o.result
        rows.append([short_name(o.key), o.buffer, r.unpowered, r.blocked, r.capacity_short, r.moves, f"{r.moves_per_retrieval:.2f}",
                     "-" if r.plug_utilisation is None else f"{r.plug_utilisation * 100:.0f}"])
    table(["Regel", "Puffer", "ohne Strom", "blockiert", "Kapazität", "Umstapelungen", "je Abholung", "Auslastung (%)"], [26, 16, 24, 22, 22, 32, 24, 28], rows)
    note("Ohne Strom: Reefer, die ankamen, als kein Steckdosen-Platz frei war (Ereignis, nicht Dauer). Blockiert: ein Normalcontainer stand zu diesem Zeitpunkt auf einem Steckdosen-Platz; "
         "Kapazität: alle Steckdosen-Plätze trugen Reefer.")
    pdf.ln(3)

    if sample is not None:
        keep_together(95)
        heading("Stichprobe und Urteil")
        table(["Regel", "ohne Strom je Block", "Umstapelungen je Abholung"], [50, 55, 65],
              [[short_name(k), f"{E.mean_of(sample, k):.2f}", f"{E.mean_of(sample, k, 'moves_pr'):.3f}"] for k in C.RULE_KEYS])
        pdf.ln(2)
        pdf.set_font("Helvetica", "", 9)
        for label, key, reference, field, unit in (("Puffer gegen Steckdosen egal, Reefer ohne Strom", PU, EG, "unpowered", "Reefer ohne Strom"),
                                                   ("Puffer gegen Steckdosen egal, Umstapelungen", PU, EG, "moves_pr", "Umstapelungen je Abholung"),
                                                   ("Steckdosen reserviert gegen Puffer, Umstapelungen", RS, PU, "moves_pr", "Umstapelungen je Abholung")):
            pdf.multi_cell(0, 5, pdf_text("- " + verdict_text(sample, label, key, reference, field, unit)), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        note(f"Basis: {len(sample)} Blöcke (Seeds 0-{len(sample) - 1}, nicht der eingestellte Seed) mit den eingestellten Werten. Klar heißt: Unterschied größer als zwei Standardfehler der gepaarten Differenz.")
        pdf.ln(3)

    if curve is not None and p.plug_stacks > 0:
        keep_together(80)
        heading("Puffer-Kurve")
        s = curve.series["Puffer"]
        table(["Puffer", "ohne Strom", "davon blockiert", "Kapazität", "Umstapelungen je Abholung"], [22, 30, 36, 30, 52],
              [[b, f"{s['unpowered'][j]:.2f}", f"{s['blocked'][j]:.2f}", f"{s['capacity_short'][j]:.2f}", f"{s['moves_pr'][j]:.3f}"] for j, b in enumerate(curve.xs)])
        note(f"Mittel je Block über {curve.n_blocks} Blöcke (Seeds 0-{curve.n_blocks - 1}). Puffer 0 ist Steckdosen egal, Puffer {slots} ist alles reserviert.")
        pdf.ln(3)

    keep_together(70)
    heading("Hinweise zum Modell")
    pdf.set_font("Helvetica", "", 9)
    for text in [
        "Block, Ereignisfolge und Abfahrtsschätzung wie in der Stapelplanung; die ersten Stapel haben in jeder Lage eine Steckdose, ein Teil der Container sind Reefer (unabhängig gezogen).",
        "Ein Reefer ohne Strom bleibt es bis zur Abholung (in der Praxis wird er umgesteckt); gezählt wird das Ereignis, nicht die Dauer. Keine Anschlussleistung, Temperaturklassen oder Ladungslisten.",
        "Reefer-Racks (einreihige Gestelle ohne Blockieren) sind ein anderes Lagerkonzept und nicht modelliert.",
        "Die Faustregel für den Puffer (Reefer-Anteil mal Belegungsgrenze) ist empirisch geprüft, nicht bewiesen; die Lage der Steckdosen-Stapel und die Reihenfolge bei Gleichstand sind Modellwahlen.",
        "Alle Zahlen sind Größenordnungen aus einer Simulation mit zufälligen Blöcken, keine Messung an echten Terminals.",
    ]:
        pdf.multi_cell(0, 5, pdf_text("- " + text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    return bytes(pdf.output())
