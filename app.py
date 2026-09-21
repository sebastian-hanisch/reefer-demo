"""
Reefer im Block – interaktive Fall-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Zusatz zur Hafen-Linie (Stapelplanung): Kühlcontainer (Reefer) brauchen Strom und dürfen nur auf Stapel mit Steckdosen. Gezeigt wird, wie viele Reefer ohne Strom ankommen, wenn Normalcontainer
die Steckdosen belegen, was das Freihalten an Umstapelungen kostet (Steckdosen-Puffer) und ab wann schlicht Steckdosen fehlen.

Lauffähig mit: streamlit run app.py
"""

import pandas as pd
import streamlit as st

import rfr_constants as C
import rfr_evaluation as E
import rfr_visualization as V
from rfr_pdf_export import generate_rfr_pdf
from rfr_presets import (apply_preset, bounds, clamp_settings, init_session_state_defaults, limit_dependent_state, load_permalink_settings, randomize_seed, SETTING_SPECS, sync_query_params)
from rfr_ui_panel import render_rule_panel

st.set_page_config(page_title="Reefer im Block – Sebastian Hanisch", layout="wide")

SCENARIO_KEYS = list(SETTING_SPECS)
EG, PU, RS = C.RULE_EGAL, C.RULE_PUFFER, C.RULE_RESERVIERT
LABEL = C.RULE_LABELS


@st.cache_data(show_spinner=False, max_entries=32)
def _compute_block(key):
    """Ein Block (Seed) mit allen drei Regeln, mit Schritten für den Blick in den Block."""
    seed = key[-1]
    p = E.Params(*key[:-1])
    inst, est, reefer = E.make_block(p, seed)
    return inst, est, reefer, E.run_rules(p, inst, est, reefer, record=True)


@st.cache_data(show_spinner=False, max_entries=16)
def _compute_sample(key):
    """Stichprobe (Seeds 0-49) und Puffer-Kurve, unabhängig vom eingestellten Seed."""
    p = E.Params(*key)
    return E.sample(p), E.buffer_curve(p)


@st.cache_data(show_spinner=False, max_entries=16)
def _compute_plug_curve(key):
    """Steckdosen-Kurve: hängt weder vom Puffer noch von der Zahl der Steckdosen-Stapel ab (die Kurve läuft über sie)."""
    return E.plug_curve(E.Params(*key))


st.title("❄️ Reefer im Block: Wer darf auf die Steckdosen?")
st.markdown(
    """
**Reefer** (Kühlcontainer) brauchen Strom und dürfen deshalb nur auf **Steckdosen-Stapel**. Stellt der Kran dort Normalcontainer ab, fehlt der Platz, wenn der nächste Reefer kommt: er steht
**ohne Strom**. Alle Steckdosen für Reefer zu reservieren schützt den Strom, verstopft aber den Rest des Blocks. Der **Steckdosen-Puffer** liegt dazwischen: Normalcontainer dürfen auf die
Steckdosen-Stapel, solange noch ein Puffer an Steckdosen-Plätzen frei bleibt. Die Demo zeigt, wie viel Puffer nötig ist, was er an Umstapelungen kostet und ab wann schlicht Steckdosen-Stapel
fehlen. Wie das Modell funktioniert, steht im Expander "Wie funktioniert diese Demo?" weiter unten, die formale Beschreibung im Expander "📐 Mathematische Formulierung".
"""
)

st.caption("🎯 Schnellstart – ein Beispielszenario laden:")
PRESET_HELP = {
    "Passend": "Die Steckdosen reichen, aber Normalcontainer belegen sie: der Puffer löst das fast kostenlos, das strenge Reservieren kostet deutlich mehr.",
    "Zu wenige": "Es fehlt Kapazität: selbst das strenge Reservieren lässt Reefer ohne Strom, denn alle Steckdosen-Plätze tragen schon Reefer. Hier helfen nur mehr Steckdosen-Stapel.",
    "Zu viele": "Steckdosen im Überfluss: fast kein Reefer bleibt ohne Strom, aber das strenge Reservieren verstopft den Block mit einem großen Aufschlag an Umstapelungen.",
    "Unsicher": "Schlechte Abfahrtsschätzung: der Strom bleibt geschützt, das Umstapeln ist aber ohnehin teurer.",
    "Großer Block": "Zehn Stapel, sechs Lagen: mehr Reefer im Block, mehr blockierte Steckdosen ohne Puffer.",
}
# Je Zeile drei Schaltflächen: bei fünf in einer Zeile werden die Namen in schmalen Fenstern abgeschnitten.
preset_names = list(C.PRESETS.keys())
for row in (preset_names[:3], preset_names[3:]):
    cols = st.columns(3)
    for col, name in zip(cols, row):
        with col:
            st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=PRESET_HELP[name])

st.caption(
    "🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, "
    "um ein Szenario zu teilen."
)

load_permalink_settings()
init_session_state_defaults()
limit_dependent_state()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    n_stacks = st.slider("Stapel im Block", *bounds("n_stacks_slider"), key="n_stacks_slider", help="Breite des Blocks; die Steckdosen-Stapel zählen davon.")
    max_height = st.slider("Höhe (Lagen)", *bounds("max_height_slider"), key="max_height_slider", help="Plätze je Stapel.")
    fill_pct = st.slider("Füllgrad (%)", *bounds("fill_slider"), step=C.FILL_PCT_STEP, format="%d%%", key="fill_slider",
                         help="Belegungsgrenze als Anteil von (Stapel − 1) × Höhe: so viel steht höchstens gleichzeitig im Block.")
    n_containers = st.slider("Container", *bounds("n_containers_slider"), step=C.N_CONTAINERS_STEP, key="n_containers_slider", help="Wie viele Container über den ganzen Ablauf ankommen und wieder abgeholt werden.")
    reefer_pct = st.slider("Reefer-Anteil (%)", *bounds("reefer_slider"), step=C.REEFER_PCT_STEP, format="%d%%", key="reefer_slider",
                           help="Anteil der Container, die Strom brauchen. Bei 0 % gibt es nichts zu schützen: die Steckdosen-Stapel kosten dann nur Platz.")
    plug_stacks = st.slider("Steckdosen-Stapel", 0, int(n_stacks) - 1, key="plugs_slider",
                            help="Die ersten Stapel (links) haben in jeder Lage eine Steckdose. Höchstens Stapel minus 1. Bei 0 steht jeder Reefer ohne Strom.")
    slots = int(plug_stacks) * int(max_height)
    thumb = E.thumb_of(E.Params(int(n_stacks), int(max_height), int(fill_pct), int(n_containers), int(reefer_pct), int(plug_stacks), 0, 0))
    if slots > 0:
        buffer = st.slider("Puffer (Steckdosen-Plätze)", 0, slots, key="buffer_slider",
                           help=f"Ein Normalcontainer darf auf einen Steckdosen-Stapel, solange danach noch so viele Plätze mit Steckdose frei bleiben. 0 = Steckdosen egal, {slots} = alle "
                                f"reserviert. Faustregel: die erwartete Zahl Reefer im Block, hier {thumb}.")
    else:
        buffer = 0
        st.caption("Puffer: ohne Steckdosen-Stapel gibt es keine Steckdosen-Plätze, die er freihalten könnte.")
    sigma_pct = st.slider("Schätzfehler der Abfahrt (% der mittleren Standzeit)", *bounds("sigma_slider"), step=C.SIGMA_PCT_STEP, format="%d%%", key="sigma_slider",
                          help="0 % = die Abfahrt ist exakt bekannt. 50 % = die Schätzung liegt typisch eine halbe mittlere Standzeit daneben. Größenordnung, nicht an Echtdaten gemessen.")
    seed = st.number_input("Seed", *bounds("seed_input"), key="seed_input", step=1, help="Bestimmt Ereignisfolge (Ankünfte und Abholungen), Reefer-Zuordnung und Schätzfehler.")
    st.button("🎲 Neuer Block", width="stretch", on_click=randomize_seed, help="Würfelt einen neuen Seed für den Block.")

plug_stacks, buffer = clamp_settings(int(n_stacks), int(max_height), int(plug_stacks), int(buffer))
sync_query_params({key: st.session_state[key] for key in SCENARIO_KEYS})

p = E.Params(int(n_stacks), int(max_height), int(fill_pct), int(n_containers), int(reefer_pct), plug_stacks, int(sigma_pct), buffer)
with st.spinner("Simuliere den Block..."):
    instance, estimates, reefer, outcomes = _compute_block(tuple(p) + (int(seed),))
by_key = {o.key: o for o in outcomes}
egal, puf, res = by_key[EG], by_key[PU], by_key[RS]
diag = E.diagnose(outcomes)
capacity, slots, thumb = E.capacity_of(p), E.slots_of(p), E.thumb_of(p)
n_reefers = sum(reefer.values())

# ---------------------------------------------------------------------------------------------------
# Hauptansicht
# ---------------------------------------------------------------------------------------------------
st.markdown("## 🎯 Wie viele Reefer stehen ohne Strom?")
st.caption(f"{p.n_stacks} Stapel, davon {p.plug_stacks} mit Steckdosen ({slots} Steckdosen-Plätze); höchstens {capacity} Container gleichzeitig im Block, davon im Mittel etwa {p.reefer_pct / 100 * capacity:.0f} "
           f"Reefer. In diesem Block kommen {puf.result.reefer_arrivals} Reefer von {instance.n_containers} Containern an. Angezeigt wird die Regel Steckdosen-Puffer mit B = {puf.buffer}; Delta = Puffer minus Steckdosen egal.")

pr, er = puf.result, egal.result
metric_rows = [st.columns(2), st.columns(2)]                  # 2 x 2: vier Spalten schneiden die Namen bei 800 px ab
m = metric_rows[0] + metric_rows[1]
m[0].metric("Reefer ohne Strom", f"{pr.unpowered}", delta=f"{pr.unpowered - er.unpowered:+d}", delta_color="inverse" if pr.unpowered != er.unpowered else "off",
            help="Reefer, die ankamen, als kein Steckdosen-Platz frei war (gezählt wird das Ereignis). Delta gegen Steckdosen egal; weniger ist besser.")
m[1].metric("davon blockiert", f"{pr.blocked}", delta=f"{pr.blocked - er.blocked:+d}", delta_color="inverse" if pr.blocked != er.blocked else "off",
            help="Ohne Strom, weil zu diesem Zeitpunkt ein Normalcontainer auf einem Steckdosen-Platz stand. Der Rest: Kapazität erschöpft (alle Steckdosen-Plätze trugen Reefer).")
m[2].metric("Umstapelungen je Abholung", f"{pr.moves_per_retrieval:.2f}", delta=f"{pr.moves_per_retrieval - er.moves_per_retrieval:+.2f}",
            delta_color="inverse" if pr.moves != er.moves else "off", help="Unproduktive Kranhübe je abgeholtem Container. Delta gegen Steckdosen egal; weniger ist besser.")
m[3].metric("Steckdosen-Auslastung", "–" if pr.plug_utilisation is None else f"{pr.plug_utilisation * 100:.0f} %",
            delta=None if pr.plug_utilisation is None or er.plug_utilisation is None else f"{(pr.plug_utilisation - er.plug_utilisation) * 100:+.0f} Punkte", delta_color="off",
            help="Mittlerer Anteil der Steckdosen-Plätze, auf denen ein Reefer steht.")

extra = diag.reserve_extra_moves_pct
extra_txt = "" if extra is None else f" Das strenge Reservieren würde dagegen {extra:+.0f} % Umstapelungen kosten."
if diag.kind == "no_reefers":
    st.info(f"ℹ️ In diesem Block kommt kein Reefer an: die Steckdosen-Stapel kosten nur Platz.{extra_txt} Erhöhen Sie den Reefer-Anteil.")
elif diag.kind == "ok":
    st.success(f"✅ Mit Puffer {puf.buffer} bekommt jeder der {pr.reefer_arrivals} Reefer Strom, bei {pr.moves} Umstapelungen (Steckdosen egal: {er.moves} Umstapelungen und "
               f"{er.unpowered} Reefer ohne Strom).{extra_txt}")
elif diag.kind == "blocked":
    st.warning(f"⚠️ **{diag.unpowered} Reefer stehen ohne Strom**, {diag.blocked} davon, weil Normalcontainer die Steckdosen belegen: ein größerer Puffer schützt sie "
               f"(Faustregel: {thumb}).{extra_txt}")
else:
    st.warning(f"⚠️ **{diag.unpowered} Reefer stehen ohne Strom**, weil alle {slots} Steckdosen-Plätze schon Reefer tragen: es fehlen Steckdosen-Stapel, keine Regel hilft.{extra_txt}")

st.markdown("#### 🔍 Blick in den Block")
right_key = st.radio("Rechts vergleichen mit", list(C.RIGHT_VIEW_KEYS), format_func=LABEL.get, key="view_radio", horizontal=True, help="Links steht immer Steckdosen egal.")
right = by_key[right_key]
scenario_key = tuple(p) + (int(seed),)
if st.session_state.get("event_owner") != scenario_key:
    st.session_state["event_slider"] = E.suggested_event(egal.result)
    st.session_state["event_owner"] = scenario_key
event = st.slider("Ereignis", 0, instance.n_events, key="event_slider",
                  help="Ein Ereignis ist eine Ankunft oder eine Abholung. Startpunkt: die erste Ankunft eines Reefers ohne Strom bei Steckdosen egal, sonst eine Abholung mit Umstapelung.")
left_col, right_col = st.columns(2)
for col, outcome, side in ((left_col, egal, "left"), (right_col, right, "right")):
    with col:
        stacks, moved, arrived, step = V.state_at(instance, outcome.result, event)
        so_far = step.moves_so_far if step is not None else 0
        now = step.unpowered_now if step is not None else ()
        title = V.block_title(f"{outcome.label} (B = {outcome.buffer})", so_far, len(now))
        st.plotly_chart(V.block_figure(stacks, p.max_height, p.plug_stacks, reefer, instance.departure, title, moved, arrived, now), width="stretch", key=f"block_chart_{side}")
        st.caption(V.describe_step(step, event, instance.n_events, reefer))
st.caption(f"Links Steckdosen egal, rechts {LABEL[right_key]}. {C.BLOCK_LEGEND_TEXT}")

pdf_slot = st.container()

st.markdown("---")

# ---------------------------------------------------------------------------------------------------
# Kernabschnitt
# ---------------------------------------------------------------------------------------------------
st.subheader("📐 Wie viel Puffer ist richtig?")
st.markdown(
    """
Kernfrage dieser Demo: Wie viel Puffer schützt den Strom, ohne den Block zu verstopfen, und ab wann hilft keine Regel mehr, weil die Steckdosen fehlen? Zwei Fragen sind getrennt:
**wie viele Steckdosen-Stapel** der Block hat (das legt die Untergrenze fest) und **wer auf ihnen stehen darf** (der Puffer). Hier live für Ihre Einstellungen gerechnet, **mit der Verteilung dazu**:
"""
)
with st.spinner("Rechne Stichprobe und Puffer-Kurve..."):
    sample_key = tuple(p)
    sample, bcurve = _compute_sample(sample_key)
g1, g2, g3 = st.columns(3)
g1.metric("Puffer (eingestellt)", f"{p.buffer}", help="Steckdosen-Plätze, die nach dem Einlagern eines Normalcontainers auf einem Steckdosen-Stapel mindestens frei bleiben.")
g2.metric("Faustregel", f"{thumb}", help="Erwartete Zahl Reefer im Block: Reefer-Anteil mal Belegungsgrenze, höchstens alle Steckdosen-Plätze. Empirisch geprüft, nicht bewiesen.")
g3.metric("Steckdosen-Plätze", f"{slots}", help="Steckdosen-Stapel mal Höhe: so viele Reefer können höchstens gleichzeitig Strom haben.")

if p.plug_stacks == 0:
    st.info("ℹ️ Ohne Steckdosen-Stapel gibt es keinen Puffer: jeder Reefer steht ohne Strom. Stellen Sie mindestens einen Steckdosen-Stapel ein.")
else:
    curve_moves, curve_power = V.buffer_curve_figures(bcurve, p.buffer, thumb)
    st.markdown("**Reefer ohne Strom über dem Puffer** (Mittel je Block; gestapelt: durch Normalcontainer blockiert und Kapazität erschöpft)")
    st.plotly_chart(curve_power, width="stretch", key="buffer_power_chart")
    st.markdown("**Umstapelungen je Abholung über dem Puffer** (Achse nicht bei 0: es geht um den Verlauf)")
    st.plotly_chart(curve_moves, width="stretch", key="buffer_moves_chart")
    st.caption(f"Basis: {bcurve.n_blocks} Blöcke (Seeds 0-{bcurve.n_blocks - 1}, nicht Ihr Seed) mit Ihren Einstellungen. Puffer 0 ist Steckdosen egal, Puffer {slots} ist alles reserviert; "
               "dazwischen liegt der Puffer. Meist ist der Strom ab der Faustregel gesichert, die Umstapelungen steigen erst danach spürbar.")


def _show_verdict(label, key, reference, field, unit):
    v = E.verdict(sample, key, reference, field)
    d = E.distribution(sample, key, reference, field)
    if v.kind == "better":
        amount = f"**{abs(v.pct):.0f} % weniger**" if v.pct is not None else f"**{abs(v.diff):.2f} weniger**"
        st.success(f"✅ **{label}**: im Mittel {amount} {unit} ({v.diff:+.2f} je Block, Standardfehler {v.se:.2f}). In **{d.worse * 100:.0f} %** der Blöcke ist es umgekehrt.")
    elif v.kind == "worse":
        amount = f"**{v.pct:.0f} % mehr**" if v.pct is not None else f"**{v.diff:.2f} mehr**"
        st.warning(f"⚠️ **{label}**: im Mittel {amount} {unit} ({v.diff:+.2f} je Block, Standardfehler {v.se:.2f}). In **{d.better * 100:.0f} %** der Blöcke ist es besser.")
    else:
        st.info(f"ℹ️ Kein klarer Unterschied bei **{label}**: die Differenz ({v.diff:+.2f} {unit}, gemittelt über die Blöcke) liegt innerhalb des Rauschens (Standardfehler {v.se:.2f}). "
                f"Besser in {d.better * 100:.0f} %, schlechter in {d.worse * 100:.0f} % der Blöcke.")


st.markdown("**Urteil über die Stichprobe** (gepaarte Differenz je Block, klar ab mehr als zwei Standardfehlern)")
_show_verdict("Puffer gegen Steckdosen egal, Reefer ohne Strom", PU, EG, "unpowered", "Reefer ohne Strom")
_show_verdict("Puffer gegen Steckdosen egal, Umstapelungen", PU, EG, "moves_pr", "Umstapelungen je Abholung")
_show_verdict("Steckdosen reserviert gegen Puffer, Umstapelungen", RS, PU, "moves_pr", "Umstapelungen je Abholung")
d_un = [E.distribution(sample, k, EG, "unpowered") for k in (PU, RS)]
d_mv = [E.distribution(sample, k, EG, "moves_pr") for k in (PU, RS)]
dcol1, dcol2 = st.columns(2)
with dcol1:
    st.markdown("**Reefer ohne Strom gegen Steckdosen egal** (Anteil der Blöcke)")
    st.plotly_chart(V.distribution_figure(d_un, [C.RULE_SHORT[k] for k in (PU, RS)], "egal", "Reefer ohne Strom"), width="stretch", key="distribution_unpowered_chart")
with dcol2:
    st.markdown("**Umstapelungen gegen Steckdosen egal** (Anteil der Blöcke)")
    st.plotly_chart(V.distribution_figure(d_mv, [C.RULE_SHORT[k] for k in (PU, RS)], "egal", "Umstapelungen"), width="stretch", key="distribution_moves_chart")
st.caption(
    f"Basis: {len(sample)} Blöcke (Seeds 0-{len(sample) - 1}, nicht Ihr Seed). Im Mittel je Block {E.mean_of(sample, EG):.2f} Reefer ohne Strom bei Steckdosen egal, {E.mean_of(sample, PU):.2f} beim Puffer und "
    f"{E.mean_of(sample, RS):.2f} bei reserviert; Umstapelungen je Abholung {E.mean_of(sample, EG, 'moves_pr'):.3f} / {E.mean_of(sample, PU, 'moves_pr'):.3f} / {E.mean_of(sample, RS, 'moves_pr'):.3f}. "
    "Gleich heißt: dieselbe Zahl im selben Block."
)

st.markdown("**Wie viele Steckdosen-Stapel braucht der Block?**")
st.plotly_chart(V.plug_curve_figure(_compute_plug_curve((p.n_stacks, p.max_height, p.fill_pct, p.n_containers, p.reefer_pct, 0, p.sigma_pct, 0)), p.plug_stacks), width="stretch", key="plug_curve_chart")
st.caption(f"Basis: {C.CURVE_BLOCKS} Blöcke (Seeds 0-{C.CURVE_BLOCKS - 1}); der Puffer folgt hier je Stapelzahl der Faustregel. Reefer ohne Strom, die auch bei reserviert bleiben, fehlen an Kapazität: "
           "sie verschwinden nur durch mehr Steckdosen-Stapel.")

with pdf_slot:
    st.download_button(
        "📄 Ergebnis als PDF herunterladen",
        data=generate_rfr_pdf(p, int(seed), instance, outcomes, diag, sample=sample, curve=bcurve),
        file_name="reefer_ergebnis.pdf", mime="application/pdf", key="primary_pdf_download",
        help="Szenario, Regelvergleich, Diagnose, Stichprobe mit Urteil und die Puffer-Kurve.")

st.markdown("---")

# ---------------------------------------------------------------------------------------------------
# Regelvergleich
# ---------------------------------------------------------------------------------------------------
with st.expander("🔧 Wie wir das erreichen – Regeln im Vergleich"):
    tabs = st.tabs([o.label for o in outcomes] + ["📊 Vergleich"])
    for tab, outcome in zip(tabs, outcomes):
        with tab:
            render_rule_panel(f"rule_{outcome.key}", outcome, outcomes, p.plug_stacks)
    with tabs[3]:
        rows = []
        for o in outcomes:
            r = o.result
            rows.append({"Regel": o.label, "Puffer": o.buffer, "Reefer ohne Strom": r.unpowered, "davon blockiert": r.blocked, "davon Kapazität": r.capacity_short,
                         "Umstapelungen": r.moves, "je Abholung": round(r.moves_per_retrieval, 2), "Auslastung": "–" if r.plug_utilisation is None else f"{r.plug_utilisation * 100:.0f} %",
                         "Delta ohne Strom": r.unpowered - er.unpowered, "Delta Umstapelungen": r.moves - er.moves})
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Reefer ohne Strom je Regel**")
            st.plotly_chart(V.unpowered_bar_figure(outcomes), width="stretch", key="comparison_unpowered_chart")
        with c2:
            st.markdown("**Umstapelungen gesamt je Regel**")
            st.plotly_chart(V.moves_bar_figure(outcomes), width="stretch", key="comparison_moves_chart")
        st.caption("Ein Block, drei Regeln. Alle Regeln sind eine Familie: Puffer 0 ist Steckdosen egal, Puffer gleich der Zahl der Steckdosen-Plätze ist alles reserviert.")

with st.expander("Wie funktioniert diese Demo?"):
    st.markdown(
        """
**Der Block.** Wie in der Stapelplanung ist ein Block eine Reihe von Stapeln gleicher Höhe. Container kommen an und werden nach einer Regel eingelagert, später in einer anderen Reihenfolge
abgeholt; liegt beim Abholen etwas im Weg, wird **umgestapelt** (jeder Hub zählt). Ankünfte und Abholungen sind zufällig; die Abfahrt kennen die Regeln nur als Schätzung mit Fehler σ.

**Steckdosen und Reefer.** Die ersten Stapel haben in jeder Lage eine Steckdose. Ein Teil der Container sind **Reefer** und brauchen Strom. Ein Reefer kommt per Bestfit auf einen
Steckdosen-Stapel mit Platz; ist keiner frei, steht er **ohne Strom** in einem anderen Stapel und bleibt dort bis zur Abholung (Annahme). Gezählt wird das Ereignis, nicht die Dauer.

**Drei Regeln für Normalcontainer**, eine Familie mit dem Puffer B:

- **Steckdosen egal** (B = 0, Referenz): Bestfit über alle Stapel mit Platz, ohne Rücksicht auf die Steckdosen. So arbeitet ein Block, in dem niemand auf die Steckdosen achtet.
- **Steckdosen-Puffer** (B): Ein Normalcontainer darf auf einen Steckdosen-Stapel, solange danach mindestens B Steckdosen-Plätze frei bleiben; sonst nur auf die übrigen Stapel.
- **Steckdosen reserviert** (B = alle Steckdosen-Plätze): Normalcontainer kommen nur auf Stapel ohne Steckdose (nur wenn dort nichts mehr frei ist, auch auf Steckdosen-Stapel).

**Faustregel.** B ≈ Reefer-Anteil × Belegungsgrenze, also die erwartete Zahl Reefer im Block. Sie hat sich an zwölf Einstellungen bewährt, ist aber empirisch und nicht bewiesen; die Puffer-Kurve
zeigt für Ihre Einstellung, wo das Knie wirklich liegt.

**Blockiert oder Kapazität.** Ein Reefer ohne Strom ist **durch Normalcontainer blockiert**, wenn zu diesem Zeitpunkt mindestens ein Normalcontainer auf einem Steckdosen-Platz stand; sonst ist die
**Kapazität erschöpft** (alle Steckdosen-Plätze tragen Reefer). Blockierte Fälle löst ein größerer Puffer, Kapazitätsfälle nur mehr Steckdosen-Stapel. Das ist eine Momentaufnahme, keine
Aussage über Gegenfaktisches.

**Warum nicht einfach reservieren?** Reserviert man alle Steckdosen für Reefer, fehlen den Normalcontainern diese Stapel: sie stehen enger, es wird mehr umgestapelt. Der Aufschlag ist am größten,
wenn die Steckdosen reichlich sind und wenige Reefer kommen.

**Stichprobe, Verteilung und Urteil.** Die Stichprobe stellt Ihre Einstellungen auf 50 Blöcke (Seeds 0 bis 49, nicht Ihr Seed) nach. Ein Unterschied gilt als klar, wenn er mehr als zwei Standardfehler
der gepaarten Differenz beträgt. Die Verteilung zeigt, in wie vielen Blöcken eine Regel weniger, gleich viele oder mehr Reefer ohne Strom beziehungsweise Umstapelungen hat als Steckdosen egal.

**Grenzen dieses Modells** (bewusst so gewählt, damit die Aussage ehrlich bleibt):

- Ein Reefer ohne Strom **bleibt** es bis zur Abholung (in der Praxis wird er umgesteckt); gezählt wird nur das Ereignis. **Keine** Anschlussleistung, Temperaturklassen oder Überwachungszeiten.
- Der Reefer-Anteil ist unabhängig je Container gezogen (keine Ladungslisten, keine Gruppen nach Schiff oder Kunde).
- **Reefer-Racks** (einreihige Gestelle ohne Blockieren) sind ein anderes Lagerkonzept und hier nicht modelliert.
- Die Lage der Steckdosen-Stapel (links) und die Reihenfolge bei Gleichstand in Bestfit sind Modellwahlen; sie verschieben alle Umstapelzahlen um wenige Prozent, nicht die Rangfolge der Regeln.
- Alle Zahlen sind **Größenordnungen aus einer Simulation, keine Messung an echten Terminals.**
        """
    )

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Block mit Steckdosen.** Stapel $i = 1, \dots, n$ der Höhe $H$; Steckdosen-Stapel $P = \{1, \dots, s\}$, Steckdosen-Plätze $K = sH$. Jeder Container $c$ ist mit Wahrscheinlichkeit $q$ ein
Reefer ($r_c = 1$). Ereignisse (Ankunft, Abholung) und die Abfahrtsschätzung $\hat e_c = e_c + \sigma \bar d\, \varepsilon_c$ wie in der Stapelplanung ($\varepsilon_c \sim \mathcal N(0,1)$, $\bar d$ mittlere Standzeit).

**Einlagerung.** Sei $A$ die Menge der Stapel mit Platz (beim Umstapeln ohne den Quellstapel) und $f$ die Zahl freier Plätze auf $P$.

- Reefer: Bestfit über $A \cap P$; ist die Menge leer, über $A$ (dann ohne Strom).
- Normalcontainer mit Puffer $B$: erlaubt sind $A$, falls $f - 1 \ge B$, sonst $A \setminus P$ (ist sie leer, wieder $A$); darin **Bestfit**: der Stapel mit dem kleinsten obersten $\hat e_{\text{oben}} \ge \hat e_c$
  (leere Stapel zählen als $\infty$), blockiert jeder, der mit dem größten $\hat e_{\text{oben}}$; Gleichstand: kleinster Stapelindex.

$B = 0$ ist **Steckdosen egal**, $B \ge K$ ist **reserviert**.

**Kennzahlen.** $U$ = Zahl der Reefer-Ankünfte, bei denen kein Stapel in $P$ Platz hat (ohne Strom), $U = U_{\text{bl}} + U_{\text{kap}}$; $U_{\text{bl}}$ zählt jene mit mindestens einem
Normalcontainer auf $P$. $M/N$ = Umstapelungen je abgeholtem Container.

**Faustregel.** $B^\ast = \min\big(K,\ \operatorname{round}(q \cdot N_{\max})\big)$ mit der Belegungsgrenze $N_{\max} = \operatorname{round}(\text{Füllgrad} \cdot (n-1)H)$ (halbe Werte werden aufgerundet).

**Vergleich über Blöcke.** Für Regel $A$ gegen die Referenz $B$ auf denselben Blöcken $b = 1, \dots, S$ ist $\Delta_b = X_A^{(b)} - X_B^{(b)}$ die Differenz einer Kennzahl $X$ (negativ = besser);
berichtet werden Mittel, Median und die Anteile der Blöcke mit $\Delta_b < 0$, $= 0$, $> 0$. Ein Unterschied gilt als klar, wenn $|\bar\Delta| > 2\,\mathrm{SE}(\Delta)$ mit dem Standardfehler der gepaarten Differenz.

Implementiert in `rfr_rules.py` (Einlagerung), `rfr_simulation.py` (Ablauf und Zähler), `rfr_evaluation.py` (Stichprobe, Kurven, Urteil) und `rfr_scenario.py` (Ereignisfolge, Reefer).
        """
    )

st.markdown("---")

st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning. Interesse an einer maßgeschneiderten Lösung für "
    "Ihr Unternehmen? [Kontakt aufnehmen](https://sebastianhanisch.net/kontakt.html)"
)
