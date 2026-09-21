"""Wiederverwendbares Panel zur Darstellung einer Regel im Regelvergleich (je Regel ein Tab)."""

import streamlit as st

import rfr_constants as C
from rfr_visualization import cumulative_figure


def render_rule_panel(prefix, outcome, outcomes, plug_stacks):
    """Beschreibung, Kennzahlen (2 x 2) und kumulierte Umstapelkurve einer Regel. Deltas lesen sich immer als "diese Regel minus Steckdosen egal" (weniger ist besser)."""
    base = next(o for o in outcomes if o.key == C.BASELINE).result
    r = outcome.result
    is_base = outcome.key == C.BASELINE

    st.markdown(C.RULE_DESCRIPTIONS[outcome.key])
    st.caption(f"Puffer B = {outcome.buffer}. Reefer kommen bei allen Regeln per Bestfit auf einen Steckdosen-Stapel; beim Umstapeln gilt dieselbe Regel wie beim Einlagern.")

    row1, row2 = st.columns(2), st.columns(2)
    row1[0].metric("Reefer ohne Strom", f"{r.unpowered}", delta=None if is_base else f"{r.unpowered - base.unpowered:+d}", delta_color="inverse",
                   help="Reefer, die ankamen, als kein Steckdosen-Platz frei war (gezählt wird das Ereignis, nicht die Dauer).")
    row1[1].metric("davon blockiert", f"{r.blocked}", delta=None if is_base else f"{r.blocked - base.blocked:+d}", delta_color="inverse",
                   help="Ohne Strom, weil zu diesem Zeitpunkt ein Normalcontainer auf einem Steckdosen-Platz stand (der Rest: Kapazität erschöpft, alle Steckdosen-Plätze trugen Reefer).")
    row2[0].metric("Umstapelungen je Abholung", f"{r.moves_per_retrieval:.2f}", delta=None if is_base else f"{r.moves_per_retrieval - base.moves_per_retrieval:+.2f}", delta_color="inverse",
                   help="Unproduktive Kranhübe je abgeholtem Container über den ganzen Ablauf.")
    row2[1].metric("Steckdosen-Auslastung", "–" if r.plug_utilisation is None else f"{r.plug_utilisation * 100:.0f} %",
                   help="Mittlerer Anteil der Steckdosen-Plätze, auf denen ein Reefer steht." if plug_stacks else "Ohne Steckdosen-Stapel gibt es keine Steckdosen-Plätze.")

    st.plotly_chart(cumulative_figure(outcomes, outcome.key), width="stretch", key=f"{prefix}_cumulative_chart")
