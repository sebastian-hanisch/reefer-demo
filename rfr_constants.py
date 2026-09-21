"""Konstanten der Reefer-Demo.

Die Erzeugung der Ereignisfolge und der Abfahrtsschätzung ist die der Stapelplanung-Demo (bitgleich, siehe tests/test_scenario.py); die Reefer-Zuordnung und die Puffer-Regel sind die der
Messreihe (hafen-planung/messreihe_reefer), damit deren Zahlen mit diesem Code reproduzierbar sind."""

# --- Ereignisfolge (wie Stapelplanung) --------------------------------------------------------------
P_ARRIVAL = 0.55
NOISE_SEED_MULTIPLIER = 13
NOISE_SEED_OFFSET = 5
# Reefer-Zuordnung: eigener Zufallsstrom, damit sich die Ereignisfolge nicht ändert, wenn nur der Reefer-Anteil variiert wird
REEFER_SEED_MULTIPLIER = 7919
REEFER_SEED_OFFSET = 11

# --- Regler ------------------------------------------------------------------------------------------
N_STACKS_RANGE, N_STACKS_DEFAULT = (4, 12), 8
MAX_HEIGHT_RANGE, MAX_HEIGHT_DEFAULT = (2, 6), 5
FILL_PCT_RANGE, FILL_PCT_DEFAULT, FILL_PCT_STEP = (40, 100), 80, 10
N_CONTAINERS_RANGE, N_CONTAINERS_DEFAULT, N_CONTAINERS_STEP = (100, 500), 300, 50
REEFER_PCT_RANGE, REEFER_PCT_DEFAULT, REEFER_PCT_STEP = (0, 50), 20, 5
PLUG_STACKS_RANGE, PLUG_STACKS_DEFAULT = (0, N_STACKS_RANGE[1] - 1), 3          # obere Grenze der Regler-Spezifikation; der Regler in der App begrenzt auf Stapel minus 1
SIGMA_PCT_RANGE, SIGMA_PCT_DEFAULT, SIGMA_PCT_STEP = (0, 200), 50, 25
BUFFER_RANGE, BUFFER_DEFAULT = (0, PLUG_STACKS_RANGE[1] * MAX_HEIGHT_RANGE[1]), 6   # obere Grenze der Spezifikation; der Regler in der App begrenzt auf die Steckdosen-Plätze
SEED_RANGE, SEED_DEFAULT = (0, 9999), 490

# --- Regeln (eine Familie: Puffer B, B = 0 egal, B = alle Steckdosen-Plätze reserviert) -----------------
RULE_EGAL, RULE_PUFFER, RULE_RESERVIERT = "egal", "puffer", "reserviert"
RULE_KEYS = (RULE_EGAL, RULE_PUFFER, RULE_RESERVIERT)
RULE_LABELS = {RULE_EGAL: "🔌 Steckdosen egal", RULE_PUFFER: "🛡️ Steckdosen-Puffer", RULE_RESERVIERT: "🔒 Steckdosen reserviert"}
RULE_SHORT = {RULE_EGAL: "Egal", RULE_PUFFER: "Puffer", RULE_RESERVIERT: "Reserviert"}
BASELINE = RULE_EGAL
RIGHT_VIEW_KEYS = (RULE_PUFFER, RULE_RESERVIERT)
VIEW_DEFAULT = RULE_PUFFER

RULE_DESCRIPTIONS = {
    RULE_EGAL: "Normalcontainer kommen per Bestfit in irgendeinen Stapel mit Platz, ohne Rücksicht auf die Steckdosen. Das ist der Block, in dem niemand auf die Steckdosen achtet, "
               "und die Referenz für alle Vergleiche.",
    RULE_PUFFER: "Ein Normalcontainer darf auf einen Steckdosen-Stapel, solange danach noch B Plätze mit Steckdose frei bleiben; sonst kommt er auf die übrigen Stapel. "
                 "Faustregel für B: der Reefer-Anteil mal die Belegungsgrenze, also die erwartete Zahl Reefer im Block.",
    RULE_RESERVIERT: "Normalcontainer kommen nur auf Stapel ohne Steckdose (nur wenn dort nichts mehr frei ist, auch auf Steckdosen-Stapel). Der Strom ist damit vollständig geschützt, "
                     "aber den Normalcontainern fehlen die Steckdosen-Stapel.",
}

# --- Auswertung ---------------------------------------------------------------------------------------
SAMPLE_BLOCKS = 50               # Blöcke (Seeds 0 .. n-1, bewusst NICHT der eingestellte Seed) für Urteil und Verteilung
CURVE_BLOCKS = 30                # Blöcke je Punkt der beiden Kurven (Rechenzeit: der größte Block braucht rund 8 s)
VERDICT_Z = 2.0                  # klar ab mehr als VERDICT_Z Standardfehlern der gepaarten Differenz
CURVE_MAX_POINTS = 12            # höchstens so viele Puffer-Werte in der Puffer-Kurve

# --- Darstellung --------------------------------------------------------------------------------------
RULE_COLORS = {RULE_EGAL: "#8a94a3", RULE_PUFFER: "#2e7d4f", RULE_RESERVIERT: "#c77700"}
REEFER_COLOR = "#2a6fb0"
NORMAL_COLOR = "#9aa5b4"
PLUG_STACK_BG = "#fff3d6"
PLAIN_STACK_BG = "#f0f2f5"
PLUG_LINE = "#e0a800"
STACK_LINE = "#c9d1db"
UNPOWERED_COLOR = "#c0392b"
MOVED_COLOR = "#e8850c"
ARRIVED_COLOR = "#2e7d4f"
MARKER_LINE_COLOR = "#808895"
OUTCOME_COLORS = {"better": "#2e7d4f", "equal": "#8a94a3", "worse": "#c0392b"}
BLOCKED_COLOR, CAPACITY_COLOR = "#c77700", "#7a3fb0"
CHART_HEIGHT = 380
BLOCK_FIGURE_BASE_PX = 90
BLOCK_FIGURE_TIER_PX = 44
BLOCK_LEGEND_TEXT = ("Blau = Reefer (braucht Strom), grau = Normalcontainer, gelb hinterlegt = Steckdosen-Stapel, roter Rand = Reefer ohne Strom, oranger Rand = gerade umgestapelt, "
                     "grüner Rand = gerade angekommen.")

# --- Presets ------------------------------------------------------------------------------------------
PRESETS = {
    "Passend": dict(n_stacks=8, max_height=5, fill_pct=80, n_containers=300, reefer_pct=20, plug_stacks=3, sigma_pct=50, buffer=6, seed=490),
    "Zu wenige": dict(n_stacks=8, max_height=5, fill_pct=80, n_containers=300, reefer_pct=30, plug_stacks=2, sigma_pct=50, buffer=8, seed=490),
    "Zu viele": dict(n_stacks=8, max_height=5, fill_pct=80, n_containers=300, reefer_pct=10, plug_stacks=4, sigma_pct=50, buffer=3, seed=490),
    "Unsicher": dict(n_stacks=8, max_height=5, fill_pct=80, n_containers=300, reefer_pct=20, plug_stacks=3, sigma_pct=150, buffer=6, seed=490),
    "Großer Block": dict(n_stacks=10, max_height=6, fill_pct=80, n_containers=400, reefer_pct=20, plug_stacks=3, sigma_pct=50, buffer=9, seed=490),
}
