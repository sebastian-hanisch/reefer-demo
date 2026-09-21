"""Plotly-Figuren der Reefer-Demo: Blockansicht, Puffer-Kurve, Steckdosen-Kurve, Verteilung, Regelvergleich, kumulierte Umstapelungen.

Konventionen des Portfolios: Achsen `fixedrange` (Touch-Scrollen), Vorlage plotly_white, Marker-Linien in mittlerem Grau, Überschriften stehen als Markdown ÜBER dem Diagramm. Plotly wird erst
in den Funktionen importiert, damit die reine Rechnung ohne Plotly testbar bleibt.
"""

import rfr_constants as C

LEGEND_BOTTOM = dict(orientation="h", yref="container", yanchor="bottom", y=0.0, x=0)

STACK_W = 1.0
STACK_GAP = 0.3
BOX_PAD = 0.06
BOX_H = 0.88


def _lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


# ---------------------------------------------------------------------------------------------------
# Blockansicht
# ---------------------------------------------------------------------------------------------------
def block_title(label, moves_so_far, unpowered_now):
    """Zweizeiliger Titel: in halbbreiten Spalten ist eine Zeile zu lang und wird abgeschnitten."""
    return f"<b>{label}</b><br><sub>Umstapelungen bisher: {moves_so_far} · Reefer ohne Strom jetzt: {unpowered_now}</sub>"


def state_at(instance, result, event_index):
    """Blockzustand nach `event_index` Ereignissen (0 = leer vor dem ersten Ereignis): (stacks, moved, arrived, step); result muss mit record=True gerechnet sein."""
    if event_index == 0:
        return tuple(() for _ in range(instance.n_stacks)), (), None, None
    step = result.steps[event_index - 1]
    return step.stacks, step.moved, (step.container if step.kind == "A" else None), step


def block_figure(stacks, max_height, plug_stacks, reefer, departure, title, moved=(), arrived=None, unpowered=()):
    """Block als Stapel von Containern: blau = Reefer, grau = Normalcontainer, Steckdosen-Stapel gelb hinterlegt mit ⚡, roter Rand = Reefer ohne Strom, oranger Rand = gerade umgestapelt,
    grüner Rand = gerade angekommen."""
    import plotly.graph_objects as go

    present = [c for s in stacks for c in s]
    rank = {c: r for r, c in enumerate(sorted(present, key=lambda k: departure[k]))}
    no_power = set(unpowered)

    fig = go.Figure()
    n = len(stacks)
    for i in range(n):
        x0 = i * (STACK_W + STACK_GAP)
        plug = i < plug_stacks
        fig.add_shape(type="rect", x0=x0, x1=x0 + STACK_W, y0=0, y1=max_height, layer="below", fillcolor=C.PLUG_STACK_BG if plug else C.PLAIN_STACK_BG,
                      line=dict(color=C.PLUG_LINE if plug else C.STACK_LINE, width=1))
        if plug:
            fig.add_annotation(x=x0 + STACK_W / 2, y=max_height + 0.02, text="⚡", showarrow=False, yanchor="bottom", font=dict(size=13))

    xs, ys, texts, hovers = [], [], [], []
    for i, s in enumerate(stacks):
        x0 = i * (STACK_W + STACK_GAP)
        for t, c in enumerate(s):
            is_reefer = bool(reefer[c])
            if c in no_power:
                border = C.UNPOWERED_COLOR
            elif c in moved:
                border = C.MOVED_COLOR
            elif c == arrived:
                border = C.ARRIVED_COLOR
            else:
                border = None
            fig.add_shape(type="rect", x0=x0 + BOX_PAD, x1=x0 + STACK_W - BOX_PAD, y0=t + (1 - BOX_H) / 2, y1=t + (1 - BOX_H) / 2 + BOX_H, layer="below",
                          fillcolor=C.REEFER_COLOR if is_reefer else C.NORMAL_COLOR, line=dict(color=border, width=3) if border else dict(width=0))
            xs.append(x0 + STACK_W / 2)
            ys.append(t + 0.5)
            texts.append("R" if is_reefer else "")
            state = []
            if c in no_power:
                state.append("ohne Strom")
            if c in moved:
                state.append("gerade umgestapelt")
            if c == arrived:
                state.append("gerade angekommen")
            hovers.append(f"<b>{'Reefer' if is_reefer else 'Normalcontainer'} {c}</b>{' · ' + ', '.join(state) if state else ''}<br>Stapel {i + 1}{' (Steckdose)' if i < plug_stacks else ''}, "
                          f"Ebene {t + 1}<br>Abfahrt in Reihenfolge: {rank[c] + 1} von {len(present)}")
    # eine Text-Spur trägt "R" UND den Hover (Linien-Hover wäre punktbasiert; die Zentren der Container sind die Punkte)
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="text", text=texts, textfont=dict(size=12, color="white"), hovertext=hovers, hoverinfo="text", showlegend=False))
    total_w = n * STACK_W + (n - 1) * STACK_GAP
    fig.update_layout(title=dict(text=title, font=dict(size=14), x=0.02), template="plotly_white", showlegend=False, hovermode="closest",
                      height=C.BLOCK_FIGURE_BASE_PX + 14 + max_height * C.BLOCK_FIGURE_TIER_PX, margin=dict(l=8, r=8, t=58, b=8))
    fig.update_xaxes(range=[-0.1, total_w + 0.1], visible=False)
    fig.update_yaxes(range=[-0.05, max_height + 0.55], visible=False)
    return _lock_axes(fig)


# ---------------------------------------------------------------------------------------------------
# Kurven
# ---------------------------------------------------------------------------------------------------
def _vline(fig, x, text, color=None, dash="dot", position="top"):
    fig.add_vline(x=x, line=dict(color=color or C.MARKER_LINE_COLOR, width=2, dash=dash), annotation_text=text, annotation_position=position, annotation_font=dict(size=11))


def buffer_curve_figures(curve, current, thumb):
    """Zwei Diagramme über dem Puffer: (Umstapelungen je Abholung, Reefer ohne Strom als Stapel blockiert / Kapazität). Marken: eingestellter Puffer und Faustregel."""
    import plotly.graph_objects as go

    s = curve.series["Puffer"]
    xs = list(curve.xs)
    moves = go.Figure(go.Scatter(x=xs, y=list(s["moves_pr"]), mode="lines+markers", name="Umstapelungen je Abholung", line=dict(color=C.RULE_COLORS[C.RULE_PUFFER], width=2.5),
                                 marker=dict(size=6), hovertemplate="Puffer %{x}<br>%{y:.3f} Umstapelungen je Abholung<extra></extra>"))
    moves.update_layout(template="plotly_white", height=C.CHART_HEIGHT - 120, margin=dict(t=25, b=45), xaxis_title="Puffer B (freie Steckdosen-Plätze)", yaxis_title="Umstapelungen je Abholung",
                        hovermode="closest", showlegend=False)
    lo, hi = min(s["moves_pr"]), max(s["moves_pr"])
    pad = max((hi - lo) * 0.25, 0.005)
    moves.update_yaxes(range=[lo - pad, hi + pad])                      # Liniendiagramm mit abgesetzter Achse (nicht bei 0): es geht um den Verlauf
    power = go.Figure()
    power.add_trace(go.Bar(x=xs, y=list(s["blocked"]), name="durch Normalcontainer blockiert", marker_color=C.BLOCKED_COLOR, hovertemplate="Puffer %{x}<br>%{y:.2f} blockiert<extra></extra>"))
    power.add_trace(go.Bar(x=xs, y=list(s["capacity_short"]), name="Kapazität erschöpft", marker_color=C.CAPACITY_COLOR, hovertemplate="Puffer %{x}<br>%{y:.2f} Kapazität<extra></extra>"))
    power.update_layout(template="plotly_white", barmode="stack", height=C.CHART_HEIGHT - 60, margin=dict(t=25, b=100), legend=LEGEND_BOTTOM, xaxis_title="Puffer B (freie Steckdosen-Plätze)",
                        yaxis_title="Reefer ohne Strom je Block")
    power.update_xaxes(type="linear")
    for fig in (moves, power):
        if current in xs:
            _vline(fig, current, "eingestellt")
        if thumb in xs and thumb != current:
            _vline(fig, thumb, "Faustregel", color=C.RULE_COLORS[C.RULE_PUFFER], dash="dash", position="bottom")
    return _lock_axes(moves), _lock_axes(power)


def plug_curve_figure(curve, current_plugs):
    """Reefer ohne Strom je Block über der Zahl der Steckdosen-Stapel für die drei Regeln."""
    import plotly.graph_objects as go

    fig = go.Figure()
    colors = {"egal": C.RULE_COLORS[C.RULE_EGAL], "Puffer (Faustregel)": C.RULE_COLORS[C.RULE_PUFFER], "reserviert": C.RULE_COLORS[C.RULE_RESERVIERT]}
    for name, s in curve.series.items():
        fig.add_trace(go.Scatter(x=list(curve.xs), y=list(s["unpowered"]), mode="lines+markers", name=name, line=dict(color=colors[name], width=2.5), marker=dict(size=6),
                                 text=[f"<b>{name}</b><br>{x} Steckdosen-Stapel<br>{v:.2f} Reefer ohne Strom, {m:.3f} Umstapelungen je Abholung" for x, v, m in zip(curve.xs, s["unpowered"], s["moves_pr"])],
                                 hovertemplate="%{text}<extra></extra>"))
    if current_plugs in curve.xs:
        _vline(fig, current_plugs, "eingestellt")
    fig.update_layout(template="plotly_white", height=C.CHART_HEIGHT, legend=LEGEND_BOTTOM, margin=dict(t=30, b=110), hovermode="closest", xaxis_title="Steckdosen-Stapel",
                      yaxis_title="Reefer ohne Strom je Block")
    fig.update_xaxes(tickmode="array", tickvals=list(curve.xs))
    fig.update_yaxes(rangemode="tozero")
    return _lock_axes(fig)


# ---------------------------------------------------------------------------------------------------
# Verteilung und Vergleich
# ---------------------------------------------------------------------------------------------------
def distribution_figure(dists, labels, reference_label, unit):
    """Je Zeile ein gestapelter Balken: Anteil der Blöcke mit weniger / gleich vielen / mehr (unit) als die Referenz."""
    import plotly.graph_objects as go

    fig = go.Figure()
    for attr, name in (("better", f"weniger {unit} als {reference_label}"), ("equal", "gleich viele"), ("worse", f"mehr {unit} als {reference_label}")):
        shares = [getattr(d, attr) * 100 for d in dists]
        fig.add_trace(go.Bar(y=labels, x=shares, orientation="h", name=name, marker_color=C.OUTCOME_COLORS[attr], text=[f"{v:.0f} %" if v >= 6 else "" for v in shares], textposition="inside",
                             insidetextanchor="middle", hovertemplate=f"<b>%{{y}}</b><br>{name}: %{{x:.0f}} % der Blöcke<extra></extra>"))
    fig.update_layout(barmode="stack", template="plotly_white", height=150 + 70 * len(dists), legend=dict(LEGEND_BOTTOM, y=-0.45, traceorder="normal"), margin=dict(t=20, b=110, l=10),
                      xaxis_title="Anteil der Blöcke (%)")
    fig.update_xaxes(range=[0, 100])
    fig.update_yaxes(autorange="reversed")
    return _lock_axes(fig)


def unpowered_bar_figure(outcomes):
    """Reefer ohne Strom je Regel, gestapelt in durch Normalcontainer blockiert und Kapazität erschöpft (ein Block)."""
    import plotly.graph_objects as go

    labels = [C.RULE_SHORT[o.key] for o in outcomes]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=labels, y=[o.result.blocked for o in outcomes], name="durch Normalcontainer blockiert", marker_color=C.BLOCKED_COLOR, hovertemplate="<b>%{x}</b><br>%{y} blockiert<extra></extra>"))
    fig.add_trace(go.Bar(x=labels, y=[o.result.capacity_short for o in outcomes], name="Kapazität erschöpft", marker_color=C.CAPACITY_COLOR, hovertemplate="<b>%{x}</b><br>%{y} Kapazität<extra></extra>"))
    top = max([o.result.unpowered for o in outcomes] + [1])
    fig.update_layout(template="plotly_white", barmode="stack", height=C.CHART_HEIGHT - 60, legend=LEGEND_BOTTOM, margin=dict(t=25, b=100), yaxis_title="Reefer ohne Strom")
    fig.update_yaxes(range=[0, top * 1.25])
    return _lock_axes(fig)


def moves_bar_figure(outcomes):
    """Umstapelungen gesamt je Regel (ein Block)."""
    import plotly.graph_objects as go

    fig = go.Figure(go.Bar(x=[C.RULE_SHORT[o.key] for o in outcomes], y=[o.result.moves for o in outcomes], marker_color=[C.RULE_COLORS[o.key] for o in outcomes],
                           text=[o.result.moves for o in outcomes], textposition="outside", hovertemplate="<b>%{x}</b><br>%{y} Umstapelungen<extra></extra>", showlegend=False))
    fig.update_layout(template="plotly_white", height=C.CHART_HEIGHT - 60, margin=dict(t=25, b=45), yaxis_title="Umstapelungen gesamt")
    fig.update_yaxes(range=[0, max(o.result.moves for o in outcomes) * 1.2 + 1])
    return _lock_axes(fig)


def cumulative_figure(outcomes, focus_key, cursor=None):
    """Kumulierte Umstapelungen der Regel `focus_key` gegen die Referenz über die Ereignisse."""
    import plotly.graph_objects as go

    by_key = {o.key: o for o in outcomes}
    keys = [C.BASELINE] if focus_key == C.BASELINE else [C.BASELINE, focus_key]
    fig = go.Figure()
    for key in keys:
        o = by_key[key]
        cum = (0,) + tuple(o.result.cumulative)
        fig.add_trace(go.Scatter(x=list(range(len(cum))), y=list(cum), mode="lines", name=o.label, line=dict(color=C.RULE_COLORS[key], width=2.5, shape="hv"),
                                 hovertemplate=f"<b>{o.label}</b><br>nach Ereignis %{{x}}: %{{y}} Umstapelungen<extra></extra>"))
    if cursor is not None:
        fig.add_vline(x=cursor, line=dict(color=C.MARKER_LINE_COLOR, width=2, dash="dot"))
    fig.update_layout(template="plotly_white", height=C.CHART_HEIGHT - 80, legend=LEGEND_BOTTOM, margin=dict(t=20, b=90), xaxis_title="Ereignis (Ankunft oder Abholung)",
                      yaxis_title="Umstapelungen kumuliert", hovermode="x unified")
    fig.update_yaxes(rangemode="tozero")
    return _lock_axes(fig)


def describe_step(step, event, n_events, reefer):
    """Ein Satz zum Zustand nach `event` Ereignissen (step = None bei 0)."""
    if step is None:
        return f"Vor dem ersten Ereignis: der Block ist leer (Ereignis 0 von {n_events})."
    kind = "Reefer" if reefer[step.container] else "Normalcontainer"
    if step.kind == "A":
        text = f"Ereignis {event} von {n_events}: {kind} {step.container} kommt an und wird auf Stapel {step.stack + 1} gestellt"
        if step.arrival_unpowered:
            text += " (⚠️ ohne Strom: alle Steckdosen-Plätze sind belegt)"
        return text + "."
    text = f"Ereignis {event} von {n_events}: {kind} {step.container} wird aus Stapel {step.stack + 1} abgeholt"
    if step.moved:
        text += f", davor {len(step.moved)} Container umgestapelt"
    return text + "."
