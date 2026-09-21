"""Szenario: Ereignisfolge im Containerblock, verrauschte Abfahrtsschätzung, Reefer-Zuordnung und Steckdosen-Stapel.

Ein Block besteht aus n_stacks Stapeln der Höhe max_height; die ersten plug_stacks Stapel haben in jeder Lage eine Steckdose. Container kommen und gehen in einer Ereignisfolge
("A" = Ankunft, "D" = Abholung); die wahre Abfahrt ist der Index des "D"-Ereignisses. Ein Teil der Container sind Reefer (brauchen Strom). Die Ereignisfolge und die Schätzung sind
bitgleich zur Stapelplanung-Demo."""

import random
from dataclasses import dataclass

import rfr_constants as C


@dataclass(frozen=True)
class Instance:
    n_stacks: int
    max_height: int
    fill: float            # Anteil von (n_stacks - 1) * max_height, 0 < fill <= 1
    n_containers: int
    seed: int
    capacity: int          # höchste gleichzeitige Belegung
    events: tuple          # ((kind, container), ...), kind in {"A", "D"}
    arrival: dict          # container -> Index des Ankunfts-Ereignisses
    departure: dict        # container -> Index des Abholungs-Ereignisses (wahre Abfahrt)
    mean_dwell: float      # mittlere Standzeit in Ereignisschritten

    @property
    def n_events(self):
        return len(self.events)


def capacity_for(n_stacks, max_height, fill):
    """Höchste gleichzeitige Belegung. Bis (n_stacks - 1) * max_height + 1 Container finden beim Abholen immer Platz zum Umstapeln."""
    return max(1, round(fill * (n_stacks - 1) * max_height))


def generate_instance(n_stacks, max_height, fill, n_containers, seed):
    if n_stacks < 2:
        raise ValueError("Mindestens 2 Stapel nötig (sonst gibt es kein Umstapeln).")
    if max_height < 1:
        raise ValueError("Stapelhöhe muss mindestens 1 sein.")
    if not 0 < fill <= 1:
        raise ValueError("Füllgrad muss in (0, 1] liegen.")
    if n_containers < 1:
        raise ValueError("Mindestens 1 Container nötig.")

    rng = random.Random(seed)
    cap = capacity_for(n_stacks, max_height, fill)
    events, present, arrived = [], [], 0
    while arrived < n_containers or present:
        may_arrive = arrived < n_containers and (not present or (len(present) < cap and rng.random() < C.P_ARRIVAL))
        if may_arrive:
            events.append(("A", arrived))
            present.append(arrived)
            arrived += 1
        else:
            container = present.pop(rng.randrange(len(present)))
            events.append(("D", container))

    arrival = {c: t for t, (kind, c) in enumerate(events) if kind == "A"}
    departure = {c: t for t, (kind, c) in enumerate(events) if kind == "D"}
    mean_dwell = sum(departure[c] - arrival[c] for c in departure) / len(departure)
    return Instance(n_stacks=n_stacks, max_height=max_height, fill=fill, n_containers=n_containers, seed=seed, capacity=cap, events=tuple(events), arrival=arrival, departure=departure,
                    mean_dwell=mean_dwell)


def default_noise_seed(seed):
    return seed * C.NOISE_SEED_MULTIPLIER + C.NOISE_SEED_OFFSET


def estimate_departures(instance, sigma, noise_seed=None):
    """Geschätzte Abfahrt je Container: wahre Abfahrt + Gauß-Rauschen (sigma als Bruchteil der mittleren Standzeit; dieselben Zufallszahlen, größeres sigma streckt nur die Fehler)."""
    if sigma < 0:
        raise ValueError("sigma darf nicht negativ sein.")
    rng = random.Random(default_noise_seed(instance.seed) if noise_seed is None else noise_seed)
    scale = sigma * instance.mean_dwell
    return {c: d + rng.gauss(0.0, 1.0) * scale for c, d in instance.departure.items()}


def reefer_flags(instance, reefer_pct, seed=None):
    """Welche Container Reefer sind: unabhängig je Container mit Wahrscheinlichkeit reefer_pct / 100, eigener Zufallsstrom (aus dem Ereignis-Seed abgeleitet)."""
    if not 0 <= reefer_pct <= 100:
        raise ValueError("Reefer-Anteil muss zwischen 0 und 100 % liegen.")
    s = instance.seed if seed is None else seed
    rng = random.Random(s * C.REEFER_SEED_MULTIPLIER + C.REEFER_SEED_OFFSET)
    share = reefer_pct / 100
    return {c: rng.random() < share for c in range(instance.n_containers)}


def plug_slots(plug_stacks, max_height):
    return plug_stacks * max_height


def rule_of_thumb_buffer(capacity, max_height, reefer_pct, plug_stacks):
    """Faustregel für den Puffer: erwartete Zahl Reefer im Block (Reefer-Anteil mal Belegungsgrenze, halbe Werte nach oben), höchstens alle Steckdosen-Plätze."""
    expected = (2 * reefer_pct * capacity + 100) // 200
    return min(plug_slots(plug_stacks, max_height), expected)
