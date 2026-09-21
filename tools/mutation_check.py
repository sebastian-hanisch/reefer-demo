"""Fehler-Einbau-Test: baut einzelne Fehler in die Module ein und prüft, ob die Tests (ohne AppTests) sie finden.

Aufruf (im Projektordner): ./venv/Scripts/python.exe tools/mutation_check.py [Teilstring des Dateinamens]
Jeder Mutant ersetzt genau eine Stelle; Überlebende sind entweder gleichwertig (kein sichtbarer Unterschied) oder eine Lücke der Tests. Die Kopie liegt in einem temporären Ordner;
PYTHONDONTWRITEBYTECODE=1, damit veralteter Bytecode keine Überlebenden vortäuscht; Quelltexte als LF (Windows-Python schreibt sonst CRLF und die Zeichenketten unten finden nichts)."""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PY = sys.executable
TIMEOUT = 240                      # Sekunden je Mutant; Endlosschleifen zählen als gefunden

MUTANTS = [
    # rfr_scenario.py
    ("rfr_scenario.py", "len(present) < cap and", "len(present) <= cap and"),
    ("rfr_scenario.py", "round(fill * (n_stacks - 1) * max_height)", "round(fill * n_stacks * max_height)"),
    ("rfr_scenario.py", "scale = sigma * instance.mean_dwell", "scale = sigma"),
    ("rfr_scenario.py", "share = reefer_pct / 100", "share = reefer_pct / 10"),
    ("rfr_scenario.py", "s = instance.seed if seed is None else seed", "s = 0 if seed is None else seed"),
    ("rfr_scenario.py", "(2 * reefer_pct * capacity + 100) // 200", "(2 * reefer_pct * capacity + 99) // 200"),
    ("rfr_scenario.py", "return min(plug_slots(plug_stacks, max_height), expected)", "return max(plug_slots(plug_stacks, max_height), expected)"),
    ("rfr_scenario.py", "if not 0 <= reefer_pct <= 100:", "if not 0 <= reefer_pct < 100:"),
    ("rfr_scenario.py", "if n_stacks < 2:", "if n_stacks < 1:"),
    ("rfr_scenario.py", "if not 0 < fill <= 1:", "if not 0 <= fill <= 1:"),
    ("rfr_scenario.py", "return seed * C.NOISE_SEED_MULTIPLIER + C.NOISE_SEED_OFFSET", "return seed * C.NOISE_SEED_MULTIPLIER"),
    # rfr_rules.py
    ("rfr_rules.py", "if top >= e_own:", "if top > e_own:"),
    ("rfr_rules.py", "elif bad is None or top > bad[0]:", "elif bad is None or top < bad[0]:"),
    ("rfr_rules.py", "if good is None or top < good[0]:", "if good is None or top <= good[0]:"),
    ("rfr_rules.py", "- 1 >= buffer else", ">= buffer else"),
    ("rfr_rules.py", "[i for i in cand if i not in plugged]", "[i for i in cand if i in plugged]"),
    ("rfr_rules.py", "on_plug = [i for i in cand if i in plugged]", "on_plug = [i for i in cand if i not in plugged]"),
    ("rfr_rules.py", "return bestfit(stacks, cand, e_own, est), False", "return bestfit(stacks, cand, e_own, est), True"),
    ("rfr_rules.py", "bestfit(stacks, allowed if allowed else cand, e_own, est), True", "bestfit(stacks, allowed, e_own, est), True"),
    ("rfr_rules.py", "        return slots\n", "        return slots - 1\n"),
    ("rfr_rules.py", "return max(0, min(int(buffer), slots))", "return min(int(buffer), slots)"),
    ("rfr_rules.py", "    if rule_key == C.RULE_EGAL:\n        return 0", "    if rule_key == C.RULE_EGAL:\n        return 1"),
    ("rfr_rules.py", "frozenset(range(plug_stacks))", "frozenset(range(plug_stacks + 1))"),
    ("rfr_rules.py", "and len(stacks[i]) < max_height]", "and len(stacks[i]) <= max_height]"),
    ("rfr_rules.py", "if i != exclude and", "if i == exclude and"),
    ("rfr_rules.py", "return sum(max_height - len(stacks[k]) for k in plugged)", "return sum(max_height - len(stacks[k]) - 1 for k in plugged)"),
    # rfr_simulation.py
    ("rfr_simulation.py", "if reefers_on_plug() < slots:", "if reefers_on_plug() <= slots:"),
    ("rfr_simulation.py", "unpowered += 1\n", "unpowered += 2\n"),
    ("rfr_simulation.py", "capacity_short += 1", "capacity_short += 2"),
    ("rfr_simulation.py", "if reefer[b] and not powered:", "if reefer[b] and powered:"),
    ("rfr_simulation.py", "util_sum += reefers_on_plug() / slots", "util_sum += reefers_on_plug() / (slots + 1)"),
    ("rfr_simulation.py", "if slots else None\n    return", "if slots else 0.0\n    return"),
    ("rfr_simulation.py", "moves += len(moved)", "moves += 1"),
    ("rfr_simulation.py", "            if moved:\n                with_move += 1", "            if moved:\n                pass"),
    ("rfr_simulation.py", "                max_height_seen = max(max_height_seen, len(stacks[j]))", "                pass"),
    ("rfr_simulation.py", "for k, s2 in enumerate(stacks) if k not in plugged", "for k, s2 in enumerate(stacks) if k in plugged"),
    ("rfr_simulation.py", "arrival_unpowered = True", "arrival_unpowered = False"),
    ("rfr_simulation.py", "buffer, exclude=x)", "buffer)"),
    ("rfr_simulation.py", "                reefer_arrivals += 1\n", "                reefer_arrivals += 0\n"),
    ("rfr_simulation.py", "return self.retrievals_with_move / self.retrievals if self.retrievals else 0.0", "return self.retrievals_with_move / self.retrievals if self.retrievals else 1.0"),
    # rfr_evaluation.py
    ("rfr_evaluation.py", "/ math.sqrt(len(d))", "/ len(d)"),
    ("rfr_evaluation.py", "abs(diff) <= C.VERDICT_Z * se", "abs(diff) < C.VERDICT_Z * se"),
    ("rfr_evaluation.py", '("better" if diff < 0 else "worse")\n    return', '("better" if diff > 0 else "worse")\n    return'),
    ("rfr_evaluation.py", "100.0 * diff / ref_mean", "10.0 * diff / ref_mean"),
    ("rfr_evaluation.py", "better, worse = sum(1 for x in d if x < 0), sum(1 for x in d if x > 0)", "better, worse = sum(1 for x in d if x <= 0), sum(1 for x in d if x > 0)"),
    ("rfr_evaluation.py", "-statistics.median(g)", "statistics.median(g)"),
    ("rfr_evaluation.py", "-statistics.fmean(g)", "statistics.fmean(g)"),
    ("rfr_evaluation.py", "pts |= {min(max(current, 0), slots), min(max(thumb, 0), slots)}", "pts |= {min(max(current, 0), slots)}"),
    ("rfr_evaluation.py", "if slots + 1 <= max_points:", "if slots + 1 < max_points:"),
    ("rfr_evaluation.py", "(C.RULE_PUFFER, thumb)", "(C.RULE_PUFFER, 0)"),
    ("rfr_evaluation.py", "kind = \"blocked\" if puf.blocked >= puf.capacity_short else \"capacity\"", "kind = \"blocked\" if puf.blocked > puf.capacity_short else \"capacity\""),
    ("rfr_evaluation.py", "extra = 100.0 * (res.moves - egal.moves) / egal.moves if egal.moves else None", "extra = (res.moves - egal.moves) / egal.moves if egal.moves else None"),
    ("rfr_evaluation.py", "        if s.arrival_unpowered:\n            return k + 1", "        if not s.arrival_unpowered:\n            return k + 1"),
    ("rfr_evaluation.py", "if best is None or filled > best[0]:", "if best is None or filled < best[0]:"),
    ("rfr_evaluation.py", "b = R.buffer_for(key, p.buffer, p.plug_stacks, p.max_height)", "b = R.buffer_for(key, 0, p.plug_stacks, p.max_height)"),
    ("rfr_evaluation.py", "return [r.moves_per_retrieval(key) - r.moves_per_retrieval(reference) for r in results]", "return [r.moves_per_retrieval(reference) - r.moves_per_retrieval(key) for r in results]"),
    ("rfr_evaluation.py", '"moves" if field == "moves_pr" else field', "field"),
    ("rfr_evaluation.py", "p.reefer_pct, p.plug_stacks)\n\n\ndef make_block", "p.sigma_pct, p.plug_stacks)\n\n\ndef make_block"),
    ("rfr_evaluation.py", "kind = \"unclear\" if diff == 0 else (\"better\" if diff < 0 else \"worse\")", "kind = \"unclear\" if diff == 1 else (\"better\" if diff < 0 else \"worse\")"),
    ("rfr_evaluation.py", "if puf.reefer_arrivals == 0:", "if puf.reefer_arrivals == 1:"),
    # rfr_stories.py
    ("rfr_stories.py", "(un[EG] >= 0.8,", "(un[EG] > 0.8,"),
    ("rfr_stories.py", "(puf <= 4, f\"Puffer-Aufschlag der Umstapelungen <= 4 %: {puf:+.1f} %\"),\n                (res >= 10", "(puf < 4, f\"Puffer-Aufschlag der Umstapelungen <= 4 %: {puf:+.1f} %\"),\n                (res >= 10"),
    ("rfr_stories.py", "(res >= 30,", "(res > 30,"),
    ("rfr_stories.py", "(abs(puf) <= 2,", "(abs(puf) < 2,"),
    ("rfr_stories.py", "(per >= 0.9,", "(per > 0.9,"),
    ("rfr_stories.py", "(un[PU] <= 0.25 * un[EG], f\"Puffer <= 25 % davon: {un[PU]:.2f}\"),\n                (puf <= 4, f\"Puffer-Aufschlag der Umstapelungen <= 4 %: {puf:+.1f} %\"),\n                (res", "(un[PU] < 0.25 * un[EG], f\"Puffer <= 25 % davon: {un[PU]:.2f}\"),\n                (puf <= 4, f\"Puffer-Aufschlag der Umstapelungen <= 4 %: {puf:+.1f} %\"),\n                (res"),
    ("rfr_stories.py", "(blocked_res <= 0.05,", "(blocked_res < 0.05,"),
    ("rfr_stories.py", "mv[RS] * 100 >= mv[EG] * 105", "mv[RS] * 100 > mv[EG] * 105"),
    ("rfr_stories.py", "un[EG] >= un[RS] + 3", "un[EG] > un[RS] + 3"),
    ("rfr_stories.py", "mv[RS] * 100 >= mv[EG] * 120", "mv[RS] * 100 > mv[EG] * 120"),
    ("rfr_stories.py", "un[PU] <= un[EG] // 2", "un[PU] < un[EG] // 2"),
    ("rfr_stories.py", "un[EG] >= 2 and un[PU]", "un[EG] > 2 and un[PU]"),
    ("rfr_stories.py", "(un[RS] >= 1.0,", "(un[RS] > 1.0,"),
    ("rfr_stories.py", "(un[EG] >= 3 * un[RS],", "(un[EG] > 3 * un[RS],"),
    # rfr_visualization.py
    ("rfr_visualization.py", "border = C.MOVED_COLOR", "border = C.ARRIVED_COLOR"),
    ("rfr_visualization.py", "plug = i < plug_stacks\n        fig.add_shape", "plug = i <= plug_stacks\n        fig.add_shape"),
    ("rfr_visualization.py", 'texts.append("R" if is_reefer else "")', 'texts.append("R")'),
    ("rfr_visualization.py", "Abfahrt in Reihenfolge: {rank[c] + 1} von", "Abfahrt in Reihenfolge: {rank[c]} von"),
    ("rfr_visualization.py", "pad = max((hi - lo) * 0.25, 0.005)", "pad = (hi - lo) * 0.25"),
    ("rfr_visualization.py", "        if current in xs:", "        if current not in xs:"),
    ("rfr_visualization.py", "if thumb in xs and thumb != current:", "if thumb in xs and thumb == current:"),
    ("rfr_visualization.py", "cum = (0,) + tuple(o.result.cumulative)", "cum = tuple(o.result.cumulative)"),
    ("rfr_visualization.py", "top = max([o.result.unpowered for o in outcomes] + [1])", "top = max([o.result.unpowered for o in outcomes] + [0])"),
    ("rfr_visualization.py", ", davor {len(step.moved)} Container umgestapelt", ", davor {len(step.moved) + 1} Container umgestapelt"),
    ("rfr_visualization.py", "if event_index == 0:", "if event_index == 1:"),
    ("rfr_visualization.py", "(step.container if step.kind == \"A\" else None)", "(step.container if step.kind == \"D\" else None)"),
    ("rfr_visualization.py", "range=[lo - pad, hi + pad]", "range=[lo - pad, hi]"),
    ("rfr_visualization.py", "keys = [C.BASELINE] if focus_key == C.BASELINE else [C.BASELINE, focus_key]", "keys = [C.BASELINE, focus_key]"),
    # rfr_pdf_export.py
    ("rfr_pdf_export.py", 'amount = f"{abs(v.pct):.0f} % weniger"', 'amount = f"{v.pct:.0f} % weniger"'),
    ("rfr_pdf_export.py", '"-" if r.plug_utilisation is None else f"{r.plug_utilisation * 100:.0f}"', '"-" if r.plug_utilisation is None else f"{r.plug_utilisation:.0f}"'),
    ("rfr_pdf_export.py", 'if curve is not None and p.plug_stacks > 0:', 'if curve is not None:'),
    ("rfr_pdf_export.py", 'f"Mit Puffer {buffer} bekommt jeder Reefer Strom."', 'f"Mit Puffer {slots} bekommt jeder Reefer Strom."'),
    ("rfr_pdf_export.py", 'if diag.kind == "blocked":', 'if diag.kind == "capacity":'),
    ("rfr_pdf_export.py", '"⚡": "",', ''),
    # rfr_presets.py
    ("rfr_presets.py", "plug_max = max(0, n_stacks - 1)", "plug_max = max(0, n_stacks)"),
    ("rfr_presets.py", "min(plug_stacks, plug_max) * max_height", "plug_stacks * max_height"),
    ("rfr_presets.py", "plugs = max(0, min(int(plug_stacks), plug_max))", "plugs = min(int(plug_stacks), plug_max)"),
    ("rfr_presets.py", "return plugs, max(0, min(int(buffer), buffer_max))", "return plugs, min(int(buffer), buffer_max)"),
    ("rfr_presets.py", "value = spec.lo + round((value - spec.lo) / spec.step) * spec.step", "value = spec.lo + int((value - spec.lo) / spec.step) * spec.step"),
    # rfr_constants.py
    ("rfr_constants.py", "VERDICT_Z = 2.0", "VERDICT_Z = 1.0"),
    ("rfr_constants.py", "VERDICT_Z = 2.0", "VERDICT_Z = 3.0"),
    ("rfr_constants.py", "P_ARRIVAL = 0.55", "P_ARRIVAL = 0.5"),
    ("rfr_constants.py", "REEFER_SEED_OFFSET = 11", "REEFER_SEED_OFFSET = 12"),
]


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else ""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="rfr_mut_"))
    for f in ROOT.glob("*.py"):
        shutil.copy(f, tmp / f.name)
    shutil.copytree(ROOT / "tests", tmp / "tests", ignore=shutil.ignore_patterns("__pycache__"))
    for f in tmp.glob("*.py"):
        f.write_bytes(f.read_bytes().replace(b"\r\n", b"\n"))
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    survivors, errors, killed = [], [], 0
    for n, (name, old, new) in enumerate(MUTANTS, 1):
        if only and only not in name:
            continue
        path = tmp / name
        original = path.read_bytes().decode("utf-8")
        if original.count(old) != 1:
            errors.append((n, name, old[:60], original.count(old)))
            continue
        path.write_bytes(original.replace(old, new).encode("utf-8"))
        try:
            r = subprocess.run([PY, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider", "tests", "--ignore=tests/test_app.py"], cwd=tmp, env=env, capture_output=True, text=True, timeout=TIMEOUT)
            survived = r.returncode == 0
        except subprocess.TimeoutExpired:
            survived = False                    # Endlosschleife (zum Beispiel Blocker landet wieder im Quellstapel): das gilt als gefunden
            print(f"[{n:3d}] Zeitüberschreitung (als gefunden gezählt)  {name}", flush=True)
        path.write_bytes(original.encode("utf-8"))
        if survived:
            survivors.append((n, name, old[:70], new[:70]))
            print(f"[{n:3d}] ÜBERLEBT  {name}: {old[:60]!r} -> {new[:60]!r}", flush=True)
        else:
            killed += 1
            print(f"[{n:3d}] gefunden  {name}", flush=True)
    print(f"\n{killed} gefunden, {len(survivors)} überlebt, {len(errors)} Fehler in der Mutantenliste")
    for e in errors:
        print("  FEHLER (Stelle nicht eindeutig gefunden):", e)
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
