"""Einlagerungsregel mit Steckdosen-Puffer und Bestfit.

Alle drei Regeln der Demo sind eine Familie mit dem Puffer B (Plätze mit Steckdose, die nach dem Einlagern eines Normalcontainers auf einem Steckdosen-Stapel mindestens frei bleiben):
B = 0 ist "Steckdosen egal", B >= Zahl der Steckdosen-Plätze ist "Steckdosen reserviert". Reefer kommen immer per Bestfit auf einen Steckdosen-Stapel (wenn dort Platz ist).

Alle Regeln geben Bestfit die Kandidaten in derselben Reihenfolge (Stapelindex): die Gleichstands-Reihenfolge ist eine Modellwahl und darf nicht von der Regel abhängen, sonst entsteht
ein Scheinvorteil (siehe tests/test_rules.py).
"""

import rfr_constants as C

INF = float("inf")


def plugged_set(plug_stacks):
    """Die Steckdosen-Stapel sind die ersten plug_stacks Stapel (links)."""
    return frozenset(range(plug_stacks))


def bestfit(stacks, cand, e_own, est):
    """Nichts Früheres blockieren, möglichst eng: Stapel mit dem kleinsten obersten ê >= eigenem ê (leere Stapel zählen als unendlich). Blockiert jeder Kandidat, der Stapel mit dem
    größten obersten ê (kleinster Schaden). Gleichstand: erster Kandidat in der übergebenen Reihenfolge."""
    good = bad = None
    for i in cand:
        s = stacks[i]
        top = est[s[-1]] if s else INF
        if top >= e_own:
            if good is None or top < good[0]:
                good = (top, i)
        elif bad is None or top > bad[0]:
            bad = (top, i)
    return (good or bad)[1]


def free_plug_slots(stacks, max_height, plugged):
    return sum(max_height - len(stacks[k]) for k in plugged)


def place(stacks, max_height, plugged, is_reefer, e_own, est, buffer, exclude=None):
    """Stapel für einen Container: (Index, mit_Strom). Beim Umstapeln ist exclude der Stapel, aus dem der Blocker stammt.

    Reefer: Bestfit unter den Steckdosen-Stapeln mit Platz; ist keiner frei, Bestfit unter allen (dann ohne Strom).
    Normalcontainer: auf einen Steckdosen-Stapel nur, wenn danach mindestens `buffer` Steckdosen-Plätze frei bleiben; sonst nur auf die übrigen Stapel (gibt es dort keinen Platz, auf alle)."""
    cand = [i for i in range(len(stacks)) if i != exclude and len(stacks[i]) < max_height]
    if not cand:
        raise ValueError("Kein Stapel mit freiem Platz: Belegung liegt über der zulässigen Grenze.")
    if is_reefer:
        on_plug = [i for i in cand if i in plugged]
        if on_plug:
            return bestfit(stacks, on_plug, e_own, est), True
        return bestfit(stacks, cand, e_own, est), False
    allowed = cand if free_plug_slots(stacks, max_height, plugged) - 1 >= buffer else [i for i in cand if i not in plugged]
    return bestfit(stacks, allowed if allowed else cand, e_own, est), True


def buffer_for(rule_key, buffer, plug_stacks, max_height):
    """Puffer B der Regel: egal 0, reserviert alle Steckdosen-Plätze, Puffer der eingestellte Wert (auf die Steckdosen-Plätze begrenzt)."""
    slots = plug_stacks * max_height
    if rule_key == C.RULE_EGAL:
        return 0
    if rule_key == C.RULE_RESERVIERT:
        return slots
    if rule_key == C.RULE_PUFFER:
        return max(0, min(int(buffer), slots))
    raise ValueError(f"Unbekannte Regel: {rule_key!r}")
