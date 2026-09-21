import pytest

import rfr_constants as C
import rfr_evaluation as E
import rfr_scenario as SC
import rfr_simulation as SIM
import rfr_visualization as V

EG, PU, RS = C.RULE_EGAL, C.RULE_PUFFER, C.RULE_RESERVIERT
P = E.Params(8, 5, 80, 300, 20, 3, 50, 6)
INST, EST, REEFER = E.make_block(P, 490)
OUTS = E.run_rules(P, INST, EST, REEFER, record=True)


def rects(fig):
    return [s for s in fig.layout.shapes if s.type == "rect"]


def axes_locked(fig):
    return bool(fig.layout.xaxis.fixedrange) and bool(fig.layout.yaxis.fixedrange)


def small_figure(stacks, plugs, reefer, **kw):
    dep = {c: 10 - c for c in range(10)}
    return V.block_figure(stacks, 3, plugs, reefer, dep, "t", **kw)


# ---------------------------------------------------------------------------------------------------
# Blockansicht
# ---------------------------------------------------------------------------------------------------
def test_block_figure_draws_a_background_per_stack_and_a_box_per_container_with_the_right_colors():
    stacks = ((0, 1), (2,), ())
    reefer = {0: True, 1: False, 2: True}
    fig = small_figure(stacks, 2, reefer)
    boxes = [s for s in rects(fig) if s.y1 - s.y0 < 1]
    backgrounds = [s for s in rects(fig) if s.y1 - s.y0 == 3]
    assert len(backgrounds) == 3 and [s.fillcolor for s in backgrounds] == [C.PLUG_STACK_BG, C.PLUG_STACK_BG, C.PLAIN_STACK_BG]
    assert [b.fillcolor for b in boxes] == [C.REEFER_COLOR, C.NORMAL_COLOR, C.REEFER_COLOR]
    assert [a.text for a in fig.layout.annotations] == ["⚡", "⚡"]                                    # eine Marke je Steckdosen-Stapel
    assert all(b.line.width == 0 for b in boxes)                                                     # keine Rahmen ohne besonderen Zustand


def test_block_figure_borders_show_unpowered_moved_and_arrived_with_that_priority():
    stacks = ((0, 1, 2), (3,))
    reefer = {0: True, 1: True, 2: False, 3: True}
    fig = small_figure(stacks, 1, reefer, moved=(1, 2), arrived=3, unpowered=(3, 1))
    boxes = [s for s in rects(fig) if s.y1 - s.y0 < 1]
    colors = [b.line.color if b.line.width else None for b in boxes]
    assert colors == [None, C.UNPOWERED_COLOR, C.MOVED_COLOR, C.UNPOWERED_COLOR]                    # 1 ohne Strom (auch umgestapelt), 2 umgestapelt, 3 ohne Strom vor angekommen
    only_arrived = [s for s in rects(small_figure(stacks, 1, reefer, arrived=2)) if s.y1 - s.y0 < 1]
    assert [b.line.color if b.line.width else None for b in only_arrived] == [None, None, C.ARRIVED_COLOR, None]


def test_block_figure_text_trace_labels_only_reefers_and_hover_names_the_state():
    stacks = ((0, 1), (2,))
    reefer = {0: True, 1: False, 2: True}
    fig = small_figure(stacks, 1, reefer, moved=(1,), arrived=2, unpowered=(2,))
    trace = fig.data[0]
    assert len(fig.data) == 1 and list(trace.text) == ["R", "", "R"] and trace.mode == "text"
    assert trace.hovertext[0].startswith("<b>Reefer 0</b>") and "Stapel 1 (Steckdose), Ebene 1" in trace.hovertext[0]
    assert "gerade umgestapelt" in trace.hovertext[1] and trace.hovertext[1].startswith("<b>Normalcontainer 1</b>")
    assert "ohne Strom" in trace.hovertext[2] and "gerade angekommen" in trace.hovertext[2] and "Stapel 2, Ebene 1" in trace.hovertext[2] and "(Steckdose)" not in trace.hovertext[2]
    assert "Abfahrt in Reihenfolge: 3 von 3" in trace.hovertext[0] and "Abfahrt in Reihenfolge: 1 von 3" in trace.hovertext[2]     # Container 2 fährt zuerst ab


def test_block_figure_handles_an_empty_block_and_locks_the_axes():
    fig = V.block_figure(((), (), ()), 5, 1, {}, {}, "leer")
    assert len(rects(fig)) == 3 and len(fig.data[0].x) == 0 and axes_locked(fig)
    assert fig.layout.xaxis.visible is False and fig.layout.yaxis.visible is False


def test_block_figure_from_a_real_step_matches_the_recorded_state():
    k = E.suggested_event(OUTS[0].result)
    stacks, moved, arrived, step = V.state_at(INST, OUTS[0].result, k)
    fig = V.block_figure(stacks, 5, 3, REEFER, INST.departure, "x", moved, arrived, step.unpowered_now)
    assert len(fig.data[0].x) == sum(len(s) for s in stacks)
    assert sum(1 for s in rects(fig) if s.line.width and s.line.color == C.UNPOWERED_COLOR) == len(step.unpowered_now) >= 1


def test_state_at_zero_is_the_empty_block_and_other_events_are_the_recorded_steps():
    stacks, moved, arrived, step = V.state_at(INST, OUTS[0].result, 0)
    assert stacks == tuple(() for _ in range(8)) and moved == () and arrived is None and step is None
    for k in (1, 50, INST.n_events):
        stacks, moved, arrived, step = V.state_at(INST, OUTS[0].result, k)
        assert stacks == OUTS[0].result.steps[k - 1].stacks and step is OUTS[0].result.steps[k - 1]
        assert (arrived is not None) == (step.kind == "A") and (arrived is None or arrived == step.container)


def test_block_title_and_describe_step():
    assert V.block_title("Regel", 7, 2) == "<b>Regel</b><br><sub>Umstapelungen bisher: 7 · Reefer ohne Strom jetzt: 2</sub>"
    assert "leer" in V.describe_step(None, 0, 10, {})
    a = SIM.Step("A", 1, 2, (), ((), (), (1,)), 0, (), False)
    assert V.describe_step(a, 3, 10, {1: True}) == "Ereignis 3 von 10: Reefer 1 kommt an und wird auf Stapel 3 gestellt."
    assert V.describe_step(SIM.Step("A", 1, 2, (), ((), (), (1,)), 0, (1,), True), 3, 10, {1: True}).endswith("(⚠️ ohne Strom: alle Steckdosen-Plätze sind belegt).")
    assert V.describe_step(a, 3, 10, {1: False}).startswith("Ereignis 3 von 10: Normalcontainer 1 kommt an")
    d = SIM.Step("D", 4, 0, (7, 8), ((), (), ()), 2, (), False)
    assert V.describe_step(d, 9, 10, {4: False}) == "Ereignis 9 von 10: Normalcontainer 4 wird aus Stapel 1 abgeholt, davor 2 Container umgestapelt."
    assert V.describe_step(SIM.Step("D", 4, 0, (), ((),), 0, (), False), 9, 10, {4: True}) == "Ereignis 9 von 10: Reefer 4 wird aus Stapel 1 abgeholt."


# ---------------------------------------------------------------------------------------------------
# Kurven
# ---------------------------------------------------------------------------------------------------
def test_buffer_curve_figures_show_the_moves_line_and_the_stacked_power_bars_with_markers():
    cv = E.buffer_curve(P, 3)
    moves, power = V.buffer_curve_figures(cv, 6, 6)
    s = cv.series["Puffer"]
    assert list(moves.data[0].x) == list(cv.xs) and list(moves.data[0].y) == list(s["moves_pr"]) and axes_locked(moves) and axes_locked(power)
    assert [t.name for t in power.data] == ["durch Normalcontainer blockiert", "Kapazität erschöpft"] and power.layout.barmode == "stack"
    assert list(power.data[0].y) == list(s["blocked"]) and list(power.data[1].y) == list(s["capacity_short"])
    assert len(moves.layout.shapes) == 1 and len(power.layout.shapes) == 1                          # eingestellt = Faustregel: eine Marke
    lo, hi = moves.layout.yaxis.range
    assert lo < min(s["moves_pr"]) and hi > max(s["moves_pr"]) and lo > 0                            # abgesetzte Achse, nicht bei 0


def test_buffer_curve_markers_current_and_thumb_differ_and_missing_points_are_skipped():
    cv = E.buffer_curve(P, 3)
    moves, power = V.buffer_curve_figures(cv, 4, 6)
    assert len(moves.layout.shapes) == 2 and {s.line.dash for s in moves.layout.shapes} == {"dot", "dash"}
    moves, power = V.buffer_curve_figures(cv, 999, 998)
    assert len(moves.layout.shapes) == 0 and len(power.layout.shapes) == 0


def test_buffer_curve_figure_with_a_flat_line_keeps_a_visible_axis_range():
    cv = E.Curve((0,), {"Puffer": {"moves_pr": (0.7,), "unpowered": (0.0,), "blocked": (0.0,), "capacity_short": (0.0,)}}, 1)
    moves, _ = V.buffer_curve_figures(cv, 0, 0)
    lo, hi = moves.layout.yaxis.range
    assert lo < 0.7 < hi


def test_plug_curve_figure_has_a_line_per_rule_with_the_series_and_a_current_marker():
    cv = E.plug_curve(P._replace(n_stacks=5, n_containers=100), 2)
    fig = V.plug_curve_figure(cv, 3)
    assert [t.name for t in fig.data] == ["egal", "Puffer (Faustregel)", "reserviert"] and axes_locked(fig)
    assert [t.line.color for t in fig.data] == [C.RULE_COLORS[EG], C.RULE_COLORS[PU], C.RULE_COLORS[RS]]
    for t, name in zip(fig.data, cv.series):
        assert list(t.x) == list(cv.xs) and list(t.y) == list(cv.series[name]["unpowered"])
    assert len(fig.layout.shapes) == 1 and len(V.plug_curve_figure(cv, 99).layout.shapes) == 0
    assert "Steckdosen-Stapel" in fig.data[0].text[1]


# ---------------------------------------------------------------------------------------------------
# Verteilung, Vergleich, kumuliert
# ---------------------------------------------------------------------------------------------------
def test_distribution_figure_stacks_three_shares_per_row_and_names_the_reference():
    res = E.sample(P, 8)
    dists = [E.distribution(res, k, EG) for k in (PU, RS)]
    fig = V.distribution_figure(dists, ["Puffer", "Reserviert"], "egal", "Reefer ohne Strom")
    assert [t.name for t in fig.data] == ["weniger Reefer ohne Strom als egal", "gleich viele", "mehr Reefer ohne Strom als egal"]
    assert list(fig.data[0].y) == ["Puffer", "Reserviert"] and [t.marker.color for t in fig.data] == [C.OUTCOME_COLORS[k] for k in ("better", "equal", "worse")]
    for i in range(2):
        assert sum(t.x[i] for t in fig.data) == pytest.approx(100)
    assert fig.layout.barmode == "stack" and axes_locked(fig)
    labels = fig.data[0].text
    assert all((lab == "") == (v < 6) for lab, v in zip(labels, fig.data[0].x))                        # kleine Anteile bleiben unbeschriftet


def test_unpowered_bar_figure_stacks_blocked_and_capacity_per_rule():
    fig = V.unpowered_bar_figure(OUTS)
    assert [t.name for t in fig.data] == ["durch Normalcontainer blockiert", "Kapazität erschöpft"] and list(fig.data[0].x) == ["Egal", "Puffer", "Reserviert"]
    assert list(fig.data[0].y) == [o.result.blocked for o in OUTS] and list(fig.data[1].y) == [o.result.capacity_short for o in OUTS]
    assert fig.layout.yaxis.range[0] == 0 and fig.layout.yaxis.range[1] >= max(o.result.unpowered for o in OUTS) and axes_locked(fig)
    empty = [E.Outcome(k, k, 0, SIM.Result(0, 1, 0, 1, (0,), (), 0, 0, 0, 0, 0, None)) for k in C.RULE_KEYS]
    assert V.unpowered_bar_figure(empty).layout.yaxis.range[1] > 0                                     # auch bei lauter Nullen eine sichtbare Achse


def test_moves_bar_figure_has_a_bar_per_rule_with_the_rule_colors():
    fig = V.moves_bar_figure(OUTS)
    assert list(fig.data[0].y) == [o.result.moves for o in OUTS] and list(fig.data[0].marker.color) == [C.RULE_COLORS[k] for k in C.RULE_KEYS]
    assert fig.layout.yaxis.range[0] == 0 and fig.layout.yaxis.range[1] > max(o.result.moves for o in OUTS) and axes_locked(fig)


def test_cumulative_figure_compares_the_focus_rule_with_the_baseline():
    fig = V.cumulative_figure(OUTS, PU, cursor=10)
    assert [t.name for t in fig.data] == [OUTS[0].label, OUTS[1].label]
    for t, o in zip(fig.data, OUTS[:2]):
        assert list(t.y) == [0] + list(o.result.cumulative) and t.line.shape == "hv"
    assert len(fig.layout.shapes) == 1 and axes_locked(fig)
    only = V.cumulative_figure(OUTS, EG)
    assert len(only.data) == 1 and len(only.layout.shapes) == 0
