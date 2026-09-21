"""Ablauf im Block: Einlagern nach der Puffer-Regel, Abholen in wahrer Reihenfolge, Umstapeln der Blocker; dazu die Reefer-Zähler.

Beim Abholen werden nur die Container über dem Ziel umgestapelt (jeder Hub zählt als eine Umstapelung). Ein Reefer, der ohne Steckdose steht (weil auf den Steckdosen-Stapeln kein Platz
war), bleibt bis zur Abholung ohne Strom (Annahme). Gezählt wird das Ereignis "Reefer kommt ohne Strom an", nicht die Dauer.

Eine Ankunft ohne Strom heißt "blockiert", wenn auf den Steckdosen-Plätzen zu diesem Zeitpunkt mindestens ein Normalcontainer steht, sonst "Kapazität erschöpft" (alle Steckdosen-Plätze
tragen Reefer; das gilt auch bei 0 Steckdosen-Stapeln). Das ist eine Momentaufnahme, keine Aussage über Gegenfaktisches."""

from dataclasses import dataclass

from rfr_rules import place, plugged_set


@dataclass(frozen=True)
class Step:
    """Zustand nach einem Ereignis (nur wenn record=True)."""
    kind: str               # "A" Ankunft, "D" Abholung
    container: int
    stack: int              # Ankunft: gewählter Stapel; Abholung: Stapel, aus dem abgeholt wurde
    moved: tuple            # Abholung: umgestapelte Container (oberster zuerst), sonst ()
    stacks: tuple           # Blockzustand, Tupel von Tupeln (unten nach oben)
    moves_so_far: int
    unpowered_now: tuple    # Reefer, die jetzt ohne Strom stehen
    arrival_unpowered: bool  # die Ankunft dieses Schritts war ein Reefer ohne Strom


@dataclass(frozen=True)
class Result:
    moves: int
    retrievals: int
    retrievals_with_move: int
    max_stack_height: int
    cumulative: tuple       # kumulierte Umstapelungen nach jedem Ereignis
    steps: tuple            # leer, wenn nicht aufgezeichnet
    reefer_arrivals: int
    unpowered: int          # Reefer-Ankünfte ohne Strom
    blocked: int            # davon durch Normalcontainer blockiert
    capacity_short: int     # davon Kapazität erschöpft
    unpowered_relocations: int   # Reefer, die beim Umstapeln ohne Strom landeten
    plug_utilisation: object     # mittlerer Anteil der Steckdosen-Plätze mit Reefern nach einem Ereignis; None ohne Steckdosen

    @property
    def moves_per_retrieval(self):
        return self.moves / self.retrievals if self.retrievals else 0.0

    @property
    def share_retrievals_with_move(self):
        return self.retrievals_with_move / self.retrievals if self.retrievals else 0.0


def run(instance, estimates, reefer, plug_stacks, buffer, record=False):
    """Simuliert die Ereignisfolge der Instanz mit Puffer `buffer` (0 = egal, alle Steckdosen-Plätze = reserviert)."""
    H = instance.max_height
    plugged = plugged_set(plug_stacks)
    slots = plug_stacks * H
    stacks = [[] for _ in range(instance.n_stacks)]
    where = {}
    moves = retrievals = with_move = max_height_seen = 0
    reefer_arrivals = unpowered = blocked = capacity_short = unpowered_relocations = 0
    util_sum = 0.0
    cumulative, steps = [], []

    def reefers_on_plug():
        return sum(1 for k in plugged for x in stacks[k] if reefer[x])

    for kind, c in instance.events:
        moved = []
        arrival_unpowered = False
        if kind == "A":
            i, powered = place(stacks, H, plugged, reefer[c], estimates[c], estimates, buffer)
            if reefer[c]:
                reefer_arrivals += 1
                if not powered:
                    unpowered += 1
                    arrival_unpowered = True
                    if reefers_on_plug() < slots:
                        blocked += 1
                    else:
                        capacity_short += 1
            stacks[i].append(c)
            where[c] = i
            max_height_seen = max(max_height_seen, len(stacks[i]))
            stack_used = i
        else:
            x = where[c]
            s = stacks[x]
            while s[-1] != c:
                b = s.pop()
                j, powered = place(stacks, H, plugged, reefer[b], estimates[b], estimates, buffer, exclude=x)
                stacks[j].append(b)
                where[b] = j
                moved.append(b)
                if reefer[b] and not powered:
                    unpowered_relocations += 1
                max_height_seen = max(max_height_seen, len(stacks[j]))
            s.pop()
            del where[c]
            retrievals += 1
            if moved:
                with_move += 1
            moves += len(moved)
            stack_used = x
        cumulative.append(moves)
        if slots:
            util_sum += reefers_on_plug() / slots
        if record:
            now = tuple(sorted(cc for k, s2 in enumerate(stacks) if k not in plugged for cc in s2 if reefer[cc]))
            steps.append(Step(kind, c, stack_used, tuple(moved), tuple(tuple(s2) for s2 in stacks), moves, now, arrival_unpowered))

    utilisation = util_sum / len(instance.events) if slots else None
    return Result(moves, retrievals, with_move, max_height_seen, tuple(cumulative), tuple(steps), reefer_arrivals, unpowered, blocked, capacity_short, unpowered_relocations, utilisation)
