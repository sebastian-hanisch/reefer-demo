"""Abnahmekriterien der Presets (Plan, Abschnitt 7): Welche Geschichte erzählt jedes Beispielszenario, und woran erkennt man, dass sie trägt?

Einzige Quelle für `tools/tune_presets.py` (Abstimmung) und `tests/test_preset_stories.py` (Abnahme). Jedes Kriterium ist eine Aussage über ein Tupel von `BlockResult`s (rfr_evaluation):
über viele Blöcke die Aussage im MITTEL (`criteria`), über den EINEN Block des Presets die Aussage an diesem Block in ganzen Zahlen (`holds`). So wird dieselbe Geschichte an der
Grundgesamtheit UND am gewählten Block geprüft: das Preset soll typisch sein, nicht der schönste Einzelfall. Alles ist ganzzahlig und deterministisch (kein Löser, keine Zeitgrenze)."""

import rfr_constants as C
import rfr_evaluation as E

EG, PU, RS = C.RULE_EGAL, C.RULE_PUFFER, C.RULE_RESERVIERT

# Kennzahlen, an denen 'typisch' gemessen wird: (Preset, Regel, Feld)
TYPICAL = (("Passend", EG, "unpowered"), ("Passend", RS, "moves"), ("Zu wenige", EG, "unpowered"), ("Zu wenige", RS, "unpowered"), ("Zu viele", RS, "moves"),
           ("Unsicher", EG, "unpowered"), ("Unsicher", EG, "moves"), ("Großer Block", EG, "unpowered"), ("Großer Block", RS, "moves"))


def extra_moves_pct(results, key):
    """Aufschlag der Umstapelungen der Regel gegen egal in % (Mittel über die Blöcke)."""
    base = E.mean_of(results, EG, "moves")
    return 100.0 * (E.mean_of(results, key, "moves") - base) / base


def criteria(name, results):
    """Mittelwert-Kriterien über viele Blöcke. Rückgabe: Liste (erfüllt, Text)."""
    un = {k: E.mean_of(results, k, "unpowered") for k in C.RULE_KEYS}
    puf, res = extra_moves_pct(results, PU), extra_moves_pct(results, RS)
    if name == "Passend":
        return [(un[EG] >= 0.8, f"egal: >= 0,8 Reefer ohne Strom je Block: {un[EG]:.2f}"),
                (un[PU] <= 0.25 * un[EG], f"Puffer <= 25 % davon: {un[PU]:.2f}"),
                (puf <= 4, f"Puffer-Aufschlag der Umstapelungen <= 4 %: {puf:+.1f} %"),
                (res >= 10, f"reserviert >= +10 % Umstapelungen: {res:+.1f} %")]
    if name == "Zu wenige":
        blocked_res = E.mean_of(results, RS, "blocked")
        return [(un[RS] >= 1.0, f"reserviert: >= 1,0 Reefer ohne Strom je Block: {un[RS]:.2f}"),
                (blocked_res <= 0.05, f"davon durch Normalcontainer blockiert <= 0,05: {blocked_res:.2f}"),
                (un[EG] >= 3 * un[RS], f"egal >= 3-mal so viele wie reserviert: {un[EG]:.2f}"),
                (abs(puf) <= 3 and abs(res) <= 3, f"Umstapelungen aller Regeln innerhalb +-3 %: Puffer {puf:+.1f} %, reserviert {res:+.1f} %")]
    if name == "Zu viele":
        return [(un[EG] <= 0.1, f"egal: <= 0,1 Reefer ohne Strom je Block: {un[EG]:.2f}"),
                (res >= 30, f"reserviert >= +30 % Umstapelungen: {res:+.1f} %"),
                (abs(puf) <= 2, f"Puffer innerhalb +-2 % Umstapelungen: {puf:+.1f} %")]
    if name == "Unsicher":
        per = E.mean_of(results, EG, "moves_pr")
        return [(un[PU] <= 0.25 * un[EG], f"Puffer <= 25 % der Reefer ohne Strom von egal: {un[PU]:.2f} gegen {un[EG]:.2f}"),
                (per >= 0.9, f"Umstapelungen je Abholung (egal) >= 0,9: {per:.2f}")]
    if name == "Großer Block":
        return [(un[EG] >= 1.5, f"egal: >= 1,5 Reefer ohne Strom je Block: {un[EG]:.2f}"),
                (un[PU] <= 0.25 * un[EG], f"Puffer <= 25 % davon: {un[PU]:.2f}"),
                (puf <= 4, f"Puffer-Aufschlag der Umstapelungen <= 4 %: {puf:+.1f} %")]
    raise KeyError(name)


def holds(name, r):
    """Gilt die Geschichte an dem EINEN Block (`BlockResult`), den das Preset zeigt? Nur ganze Zahlen (Zählwerte sind klein)."""
    un, mv = r.unpowered, r.moves
    if name == "Passend":
        return un[EG] >= 1 and un[PU] == 0 and mv[RS] * 100 >= mv[EG] * 105
    if name == "Zu wenige":
        return r.capacity_short[RS] >= 1 and r.blocked[RS] == 0 and un[EG] >= un[RS] + 3
    if name == "Zu viele":
        return un[EG] == 0 and un[PU] == 0 and mv[RS] * 100 >= mv[EG] * 120
    if name == "Unsicher":
        return un[EG] >= 1 and un[PU] * 2 <= un[EG]
    if name == "Großer Block":
        return un[EG] >= 2 and un[PU] <= un[EG] // 2
    raise KeyError(name)


def key_values(name, results):
    """Die Kennzahlen dieses Presets aus TYPICAL als {(Regel, Feld): Mittel}."""
    return {(k, f): E.mean_of(results, k, f) for n, k, f in TYPICAL if n == name}
