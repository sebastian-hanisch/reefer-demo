"""Preset-Abstimmung per Sweep: trägt die Geschichte jedes Presets im MITTEL über viele Blöcke, und an dem einen Block, den das Preset zeigt?

Aufruf (im Projektordner): ./venv/Scripts/python.exe tools/tune_presets.py <modus>
  population   Grundgesamtheit (Seeds 0-199): Mittelwert-Kriterien aller Presets
  seeds        je Seed 200..699: welche Presets tragen an diesem Block, Abstand zum Median der Kennzahlen; nennt die besten gemeinsamen Seeds

Grundsätze (aus den Hafen-Demos): den Seed nicht nach dem schönsten Einzelfall wählen, sondern nahe am MEDIAN; der Preset-Seed liegt außerhalb der Grundgesamtheit (Seeds ab 200);
alle Presets teilen sich EINE Block-Nummer. Alles ist ganzzahlig und deterministisch, kein Löser: die Ergebnisse hängen nicht vom Rechner ab."""
import math
import statistics
import sys

sys.path.insert(0, ".")
import rfr_constants as C
import rfr_evaluation as E
import rfr_stories as ST

NAMES = list(C.PRESETS)
POPULATION = 200
SEEDS = range(POPULATION, POPULATION + 500)


def params(name):
    p = C.PRESETS[name]
    return E.Params(p["n_stacks"], p["max_height"], p["fill_pct"], p["n_containers"], p["reefer_pct"], p["plug_stacks"], p["sigma_pct"], p["buffer"])


def cmd_population():
    for name in NAMES:
        res = E.sample(params(name), POPULATION)
        print(f"\n### {name}")
        for ok, text in ST.criteria(name, res):
            print(("  OK   " if ok else "  FAIL ") + text)
        print("  Kennzahlen:", {f"{k}/{f}": round(v, 2) for (k, f), v in ST.key_values(name, res).items()})


def _value(r, key, field):
    return getattr(r, field)[key]


def _median(table):
    return {(n, k, f): statistics.median(_value(table[n][s], k, f) for s in table[n]) for n, k, f in ST.TYPICAL}


def _score(table, med, seed):
    return sum(abs(math.log(_value(table[n][seed], k, f) + 0.5) - math.log(med[(n, k, f)] + 0.5)) for n, k, f in ST.TYPICAL)


def cmd_seeds():
    table = {n: {s: E.block_result(params(n), s) for s in SEEDS} for n in NAMES}
    med = _median(table)
    for name in NAMES:
        print(f"{name}: trägt an {sum(ST.holds(name, table[name][s]) for s in SEEDS)} von {len(SEEDS)} Blöcken")
    allgood = sorted((s for s in SEEDS if all(ST.holds(n, table[n][s]) for n in NAMES)), key=lambda s: _score(table, med, s))
    print("\nalle fünf tragen an:", allgood[:12], f"({len(allgood)} von {len(SEEDS)})")
    for s in allgood[:6]:
        print(f"  seed {s:3d} | Abstand zum Median {_score(table, med, s):.2f} | " + ", ".join(
            f"{n}: un {table[n][s].unpowered[C.RULE_EGAL]}/{table[n][s].unpowered[C.RULE_PUFFER]}/{table[n][s].unpowered[C.RULE_RESERVIERT]}, mv "
            f"{table[n][s].moves[C.RULE_EGAL]}/{table[n][s].moves[C.RULE_PUFFER]}/{table[n][s].moves[C.RULE_RESERVIERT]}" for n in NAMES))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "population"
    {"population": cmd_population, "seeds": cmd_seeds}.get(mode, lambda: sys.exit(__doc__))()
