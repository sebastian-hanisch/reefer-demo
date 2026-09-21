"""Regler-Spezifikation, Permalink, Presets und Seed-Knopf (Standardmuster aus dem OR-Demo-Portfolio, siehe dsp_presets.py / stk_presets.py).

Zwei Regler haben berechnete Grenzen: Steckdosen-Stapel (höchstens Stapel minus 1) und Puffer (höchstens alle Steckdosen-Plätze). `clamp_settings` begrenzt sie, statt sie zu verwerfen;
die App ruft es vor dem Erzeugen der Regler auf (Permalink, Preset, geänderte Stapelzahl)."""

import math
import random
from dataclasses import dataclass
from typing import Callable, Optional

import streamlit as st

import rfr_constants as C


def _view(raw):
    if raw not in C.RIGHT_VIEW_KEYS:
        raise ValueError(raw)
    return raw


def _int_text(value):
    return str(int(value))


@dataclass(frozen=True)
class SettingSpec:
    url_param: str
    caster: Callable
    default: object
    lo: Optional[float] = None
    hi: Optional[float] = None
    step: Optional[int] = None
    encoder: Callable = _int_text


SETTING_SPECS = {
    "n_stacks_slider": SettingSpec("ns", int, C.N_STACKS_DEFAULT, *C.N_STACKS_RANGE, 1),
    "max_height_slider": SettingSpec("mh", int, C.MAX_HEIGHT_DEFAULT, *C.MAX_HEIGHT_RANGE, 1),
    "fill_slider": SettingSpec("fp", int, C.FILL_PCT_DEFAULT, *C.FILL_PCT_RANGE, C.FILL_PCT_STEP),
    "n_containers_slider": SettingSpec("nc", int, C.N_CONTAINERS_DEFAULT, *C.N_CONTAINERS_RANGE, C.N_CONTAINERS_STEP),
    "reefer_slider": SettingSpec("rp", int, C.REEFER_PCT_DEFAULT, *C.REEFER_PCT_RANGE, C.REEFER_PCT_STEP),
    "plugs_slider": SettingSpec("ps", int, C.PLUG_STACKS_DEFAULT, *C.PLUG_STACKS_RANGE, 1),
    "sigma_slider": SettingSpec("sg", int, C.SIGMA_PCT_DEFAULT, *C.SIGMA_PCT_RANGE, C.SIGMA_PCT_STEP),
    "buffer_slider": SettingSpec("bf", int, C.BUFFER_DEFAULT, *C.BUFFER_RANGE, 1),
    "seed_input": SettingSpec("seed", int, C.SEED_DEFAULT, *C.SEED_RANGE, 1),
    "view_radio": SettingSpec("vw", _view, C.VIEW_DEFAULT, encoder=str),
}

PRESET_STATE_KEYS = {
    "n_stacks": "n_stacks_slider", "max_height": "max_height_slider", "fill_pct": "fill_slider", "n_containers": "n_containers_slider", "reefer_pct": "reefer_slider",
    "plug_stacks": "plugs_slider", "sigma_pct": "sigma_slider", "buffer": "buffer_slider", "seed": "seed_input",
}


def bounds(state_key):
    spec = SETTING_SPECS[state_key]
    return spec.lo, spec.hi


def parse_setting(spec, raw):
    """Wert aus der Adresszeile: umwandeln, auf den Bereich begrenzen, auf die Schrittweite runden. None, wenn er sich nicht auswerten lässt."""
    try:
        value = spec.caster(raw)
    except (ValueError, TypeError):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if spec.lo is not None:
        value = max(spec.lo, value)
    if spec.hi is not None:
        value = min(spec.hi, value)
    if spec.step and spec.step > 1 and spec.lo is not None:
        value = spec.lo + round((value - spec.lo) / spec.step) * spec.step
        value = min(spec.hi, value)
    return value


def dependent_limits(n_stacks, max_height, plug_stacks):
    """(höchste Zahl Steckdosen-Stapel, höchster Puffer) zu den Einstellungen: Stapel minus 1 und alle Steckdosen-Plätze."""
    plug_max = max(0, n_stacks - 1)
    return plug_max, min(plug_stacks, plug_max) * max_height


def clamp_settings(n_stacks, max_height, plug_stacks, buffer):
    """(Steckdosen-Stapel, Puffer) auf ihre berechneten Grenzen begrenzt."""
    plug_max, _ = dependent_limits(n_stacks, max_height, plug_stacks)
    plugs = max(0, min(int(plug_stacks), plug_max))
    _, buffer_max = dependent_limits(n_stacks, max_height, plugs)
    return plugs, max(0, min(int(buffer), buffer_max))


def limit_dependent_state():
    """Begrenzt die beiden abhängigen Regler im session_state (vor dem Erzeugen der Widgets aufrufen)."""
    s = st.session_state
    plugs, buffer = clamp_settings(s["n_stacks_slider"], s["max_height_slider"], s["plugs_slider"], s["buffer_slider"])
    s["plugs_slider"], s["buffer_slider"] = plugs, buffer


def init_session_state_defaults():
    for state_key, spec in SETTING_SPECS.items():
        if state_key not in st.session_state:
            st.session_state[state_key] = spec.default


def load_permalink_settings():
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    for state_key, spec in SETTING_SPECS.items():
        if spec.url_param in qp:
            value = parse_setting(spec, qp[spec.url_param])
            if value is not None:
                st.session_state[state_key] = value
    st.session_state["permalink_loaded"] = True


def sync_query_params(values):
    """values: dict state_key -> aktueller Wert (aus den Widgets, damit dieselbe Änderung, die gerade gerendert wurde, sofort in der Adresszeile landet)."""
    try:
        for state_key, value in values.items():
            st.query_params[SETTING_SPECS[state_key].url_param] = SETTING_SPECS[state_key].encoder(value)
    except Exception:
        pass


def apply_preset(name):
    for field, state_key in PRESET_STATE_KEYS.items():
        st.session_state[state_key] = C.PRESETS[name][field]


def randomize_seed():
    """Würfelt einen neuen Seed für den Block."""
    st.session_state["seed_input"] = random.randint(*C.SEED_RANGE)
