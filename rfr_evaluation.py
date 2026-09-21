"""Auswertung: ein Block mit allen Regeln, Stichprobe über viele Blöcke, Puffer-Kurve, Steckdosen-Kurve, gepaarte Differenz, Verteilung, Urteil und Diagnose.

Reine Rechnung ohne Streamlit. Kosten sind Reefer ohne Strom und Umstapelungen je Abholung (weniger ist besser, nicht zu einer Zahl vermischt); alle Vergleiche sind gepaart (dieselben Blöcke);
Unterschied = Regel minus Referenz "egal", negativ = besser."""

import math
import statistics
from dataclasses import dataclass
from typing import NamedTuple

import rfr_constants as C
import rfr_rules as R
import rfr_scenario as SC
import rfr_simulation as SIM


class Params(NamedTuple):
    """Alle Einstellungen, die einen Block bestimmen (ohne Seed)."""
    n_stacks: int
    max_height: int
    fill_pct: int
    n_containers: int
    reefer_pct: int
    plug_stacks: int
    sigma_pct: int
    buffer: int


def capacity_of(p):
    return SC.capacity_for(p.n_stacks, p.max_height, p.fill_pct / 100)


def slots_of(p):
    return SC.plug_slots(p.plug_stacks, p.max_height)


def thumb_of(p):
    return SC.rule_of_thumb_buffer(capacity_of(p), p.max_height, p.reefer_pct, p.plug_stacks)


def make_block(p, seed):
    """(Instanz, Schätzungen, Reefer-Zuordnung) zu den Einstellungen und dem Seed."""
    inst = SC.generate_instance(p.n_stacks, p.max_height, p.fill_pct / 100, p.n_containers, seed)
    return inst, SC.estimate_departures(inst, p.sigma_pct / 100), SC.reefer_flags(inst, p.reefer_pct)


# ---------------------------------------------------------------------------------------------------
# Ein Block, alle Regeln
# ---------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Outcome:
    key: str
    label: str
    buffer: int
    result: SIM.Result


def run_rules(p, inst, est, reefer, record=False):
    """Die drei Regeln (Reihenfolge C.RULE_KEYS) auf demselben Block."""
    out = []
    for key in C.RULE_KEYS:
        b = R.buffer_for(key, p.buffer, p.plug_stacks, p.max_height)
        out.append(Outcome(key, C.RULE_LABELS[key], b, SIM.run(inst, est, reefer, p.plug_stacks, b, record=record)))
    return out


def outcome_of(outcomes, key):
    return next(o for o in outcomes if o.key == key)


# ---------------------------------------------------------------------------------------------------
# Stichprobe
# ---------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class BlockResult:
    seed: int
    retrievals: int
    reefer_arrivals: int
    moves: dict             # Regel -> Umstapelungen
    unpowered: dict         # Regel -> Reefer ohne Strom
    blocked: dict
    capacity_short: dict
    utilisation: dict       # Regel -> mittlere Steckdosen-Auslastung (None ohne Steckdosen)

    def moves_per_retrieval(self, key):
        return self.moves[key] / self.retrievals if self.retrievals else 0.0


def _block_result(seed, outcomes):
    by = {o.key: o.result for o in outcomes}
    first = next(iter(by.values()))
    return BlockResult(seed, first.retrievals, first.reefer_arrivals, {k: r.moves for k, r in by.items()}, {k: r.unpowered for k, r in by.items()}, {k: r.blocked for k, r in by.items()},
                       {k: r.capacity_short for k, r in by.items()}, {k: r.plug_utilisation for k, r in by.items()})


def block_result(p, seed):
    """Ein Block (Seed) mit allen Regeln als BlockResult (ohne Schritte)."""
    inst, est, reefer = make_block(p, seed)
    return _block_result(seed, run_rules(p, inst, est, reefer))


def sample(p, n=C.SAMPLE_BLOCKS):
    """n Blöcke (Seeds 0 .. n-1, unabhängig vom eingestellten Seed) mit allen Regeln."""
    return tuple(block_result(p, seed) for seed in range(n))


def mean_of(results, key, field="unpowered"):
    """Mittel je Block: 'unpowered', 'blocked', 'capacity_short', 'moves' oder 'moves_pr' (Umstapelungen je Abholung)."""
    if field == "moves_pr":
        return statistics.fmean(r.moves_per_retrieval(key) for r in results)
    return statistics.fmean(getattr(r, field)[key] for r in results)


def mean_utilisation(results, key):
    vals = [r.utilisation[key] for r in results if r.utilisation[key] is not None]
    return statistics.fmean(vals) if vals else None


def paired(results, key, reference, field="unpowered"):
    """Gepaarte Differenz key - reference je Block (negativ = besser)."""
    if field == "moves_pr":
        return [r.moves_per_retrieval(key) - r.moves_per_retrieval(reference) for r in results]
    return [getattr(r, field)[key] - getattr(r, field)[reference] for r in results]


def _se(d):
    return statistics.stdev(d) / math.sqrt(len(d)) if len(d) > 1 else 0.0


@dataclass(frozen=True)
class Distribution:
    key: str
    field: str
    n: int
    better: float
    equal: float
    worse: float
    mean_gain: float        # eingesparte Einheiten je Block (positiv = besser als die Referenz)
    median_gain: float


def distribution(results, key, reference, field="unpowered"):
    """Anteile der Blöcke mit weniger / gleich vielen / mehr als die Referenz; für 'moves_pr' wird mit den ganzzahligen Umstapelungen verglichen (Gleichheit ohne Gleitkommavergleich)."""
    d = paired(results, key, reference, "moves" if field == "moves_pr" else field)
    n = len(d)
    better, worse = sum(1 for x in d if x < 0), sum(1 for x in d if x > 0)
    g = paired(results, key, reference, field)
    return Distribution(key, field, n, better / n, (n - better - worse) / n, worse / n, -statistics.fmean(g), -statistics.median(g))


@dataclass(frozen=True)
class Verdict:
    kind: str               # "better" (weniger) | "worse" | "unclear"
    diff: float             # Regel minus Referenz je Block (negativ = besser)
    se: float
    pct: object             # Unterschied in % der Referenz; None, wenn die Referenz im Mittel 0 ist
    n: int
    field: str


def verdict(results, key, reference, field="unpowered"):
    """Bewertung gegen die Referenz. 'Klar' heißt: Unterschied > VERDICT_Z Standardfehler der gepaarten Differenz; sonst 'unclear'."""
    d = paired(results, key, reference, field)
    diff, se = statistics.fmean(d), _se(d)
    ref_mean = mean_of(results, reference, field)
    if se == 0:
        kind = "unclear" if diff == 0 else ("better" if diff < 0 else "worse")
    else:
        kind = "unclear" if abs(diff) <= C.VERDICT_Z * se else ("better" if diff < 0 else "worse")
    return Verdict(kind, diff, se, 100.0 * diff / ref_mean if ref_mean else None, len(d), field)


# ---------------------------------------------------------------------------------------------------
# Kurven
# ---------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Curve:
    xs: tuple               # Puffer-Werte beziehungsweise Zahl der Steckdosen-Stapel
    series: dict            # Name -> {"moves_pr": (...), "unpowered": (...), "blocked": (...), "capacity_short": (...)} je x
    n_blocks: int


def buffer_points(slots, current, thumb, max_points=C.CURVE_MAX_POINTS):
    """Puffer-Werte der Kurve: alle 0..slots, wenn es höchstens max_points sind, sonst ein gleichmäßiges Raster; der eingestellte Wert und die Faustregel sind immer dabei."""
    if slots + 1 <= max_points:
        pts = set(range(slots + 1))
    else:
        pts = {round(i * slots / (max_points - 1)) for i in range(max_points)}
    pts |= {min(max(current, 0), slots), min(max(thumb, 0), slots)}
    return tuple(sorted(pts))


def _means(runs):
    return {k: tuple(statistics.fmean(v) for v in zip(*[r[k] for r in runs])) for k in runs[0]}


def buffer_curve(p, n=C.CURVE_BLOCKS):
    """Umstapelungen je Abholung und Reefer ohne Strom über dem Puffer (Mittel über n Blöcke)."""
    xs = buffer_points(slots_of(p), p.buffer, thumb_of(p))
    per_block = []
    for seed in range(n):
        inst, est, reefer = make_block(p, seed)
        rows = {k: [] for k in ("moves_pr", "unpowered", "blocked", "capacity_short")}
        for b in xs:
            r = SIM.run(inst, est, reefer, p.plug_stacks, b)
            rows["moves_pr"].append(r.moves_per_retrieval)
            rows["unpowered"].append(r.unpowered)
            rows["blocked"].append(r.blocked)
            rows["capacity_short"].append(r.capacity_short)
        per_block.append(rows)
    return Curve(xs, {"Puffer": _means(per_block)}, n)


def plug_curve(p, n=C.CURVE_BLOCKS):
    """Reefer ohne Strom (und Umstapelungen) über der Zahl der Steckdosen-Stapel 0 .. n_stacks - 1 für die drei Regeln; der Puffer folgt je Stapelzahl der Faustregel."""
    xs = tuple(range(p.n_stacks))
    names = {C.RULE_EGAL: "egal", C.RULE_PUFFER: "Puffer (Faustregel)", C.RULE_RESERVIERT: "reserviert"}
    per_block = []
    for seed in range(n):
        inst = SC.generate_instance(p.n_stacks, p.max_height, p.fill_pct / 100, p.n_containers, seed)
        est, reefer = SC.estimate_departures(inst, p.sigma_pct / 100), SC.reefer_flags(inst, p.reefer_pct)
        rows = {names[k]: {f: [] for f in ("moves_pr", "unpowered", "blocked", "capacity_short")} for k in C.RULE_KEYS}
        for s in xs:
            slots = SC.plug_slots(s, p.max_height)
            thumb = SC.rule_of_thumb_buffer(capacity_of(p), p.max_height, p.reefer_pct, s)
            for key, b in ((C.RULE_EGAL, 0), (C.RULE_PUFFER, thumb), (C.RULE_RESERVIERT, slots)):
                r = SIM.run(inst, est, reefer, s, b)
                row = rows[names[key]]
                row["moves_pr"].append(r.moves_per_retrieval)
                row["unpowered"].append(r.unpowered)
                row["blocked"].append(r.blocked)
                row["capacity_short"].append(r.capacity_short)
        per_block.append(rows)
    series = {name: _means([blk[name] for blk in per_block]) for name in per_block[0]}
    return Curve(xs, series, n)


# ---------------------------------------------------------------------------------------------------
# Diagnose (bedingte Meldung)
# ---------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Diagnosis:
    kind: str               # "no_reefers" | "ok" | "blocked" | "capacity"
    unpowered: int
    blocked: int
    capacity_short: int
    reserve_extra_moves_pct: object      # Aufschlag der strengen Regel gegen egal in %; None, wenn egal keine Umstapelung braucht


def diagnose(outcomes):
    """Was fehlt diesem Block: Kapazität (mehr Steckdosen-Stapel), Puffer (Normalcontainer blockieren Steckdosen) oder nichts. Beurteilt wird die Puffer-Regel."""
    puf, egal, res = (outcome_of(outcomes, k).result for k in (C.RULE_PUFFER, C.RULE_EGAL, C.RULE_RESERVIERT))
    extra = 100.0 * (res.moves - egal.moves) / egal.moves if egal.moves else None
    if puf.reefer_arrivals == 0:
        kind = "no_reefers"
    elif puf.unpowered == 0:
        kind = "ok"
    else:
        kind = "blocked" if puf.blocked >= puf.capacity_short else "capacity"
    return Diagnosis(kind, puf.unpowered, puf.blocked, puf.capacity_short, extra)


def suggested_event(result):
    """Startpunkt des Schrittreglers: die erste Ankunft eines Reefers ohne Strom, sonst eine Abholung mit Umstapelung bei hoher Belegung, sonst das Ende."""
    for k, s in enumerate(result.steps):
        if s.arrival_unpowered:
            return k + 1
    best = None
    for k, s in enumerate(result.steps):
        if s.kind == "D" and s.moved:
            filled = sum(len(x) for x in s.stacks)
            if best is None or filled > best[0]:
                best = (filled, k + 1)
    return best[1] if best else len(result.steps)
