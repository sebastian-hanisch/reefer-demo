"""Tests der Regler-Spezifikation: Permalink-Auswertung (begrenzen, einrasten, Müll ignorieren), berechnete Grenzen, Presets innerhalb der Reglergrenzen, Konsistenz mit den Konstanten."""

import rfr_constants as C
import rfr_presets as P

S = P.SETTING_SPECS


def test_parse_clamps_to_range():
    spec = S["n_stacks_slider"]
    assert P.parse_setting(spec, "99") == 12 and P.parse_setting(spec, "-5") == 4 and P.parse_setting(spec, "9") == 9
    assert P.parse_setting(S["max_height_slider"], "1") == 2 and P.parse_setting(S["max_height_slider"], "7") == 6
    assert P.parse_setting(S["seed_input"], "12345") == 9999


def test_parse_snaps_to_step_from_lower_bound():
    fill, cont, reefer, sigma = S["fill_slider"], S["n_containers_slider"], S["reefer_slider"], S["sigma_slider"]
    assert P.parse_setting(fill, "83") == 80 and P.parse_setting(fill, "86") == 90 and P.parse_setting(fill, "100") == 100 and P.parse_setting(fill, "1") == 40
    assert P.parse_setting(fill, "85") == 80                                             # Python rundet halbe Werte zur geraden Zahl (Bankers Rounding): 4,5 Schritte -> 4
    assert P.parse_setting(cont, "320") == 300 and P.parse_setting(cont, "330") == 350 and P.parse_setting(cont, "10") == 100 and P.parse_setting(cont, "999") == 500
    assert P.parse_setting(reefer, "22") == 20 and P.parse_setting(reefer, "23") == 25 and P.parse_setting(reefer, "0") == 0 and P.parse_setting(reefer, "80") == 50
    assert P.parse_setting(sigma, "60") == 50 and P.parse_setting(sigma, "70") == 75 and P.parse_setting(sigma, "500") == 200


def test_step_grid_starts_at_the_lower_bound_not_at_zero():
    spec = P.SettingSpec("x", int, 1, 1, 21, 5)
    assert [P.parse_setting(spec, str(v)) for v in (1, 3, 4, 7, 9, 14, 19, 21)] == [1, 1, 6, 6, 11, 16, 21, 21]


def test_parse_ignores_garbage():
    for key in ("n_stacks_slider", "seed_input", "reefer_slider", "plugs_slider", "buffer_slider"):
        assert P.parse_setting(S[key], "abc") is None and P.parse_setting(S[key], None) is None and P.parse_setting(S[key], "") is None
    assert P.parse_setting(S["n_stacks_slider"], "8.5") is None                       # nur ganze Zahlen
    assert P.parse_setting(S["view_radio"], "junk") is None
    assert P.parse_setting(S["view_radio"], "egal") is None                           # die Referenz steht immer links, ist keine Wahl rechts
    assert P.parse_setting(S["view_radio"], "reserviert") == "reserviert" and P.parse_setting(S["view_radio"], "puffer") == "puffer"


def test_specs_match_constants_and_defaults_inside_bounds():
    assert S["n_stacks_slider"].default == C.N_STACKS_DEFAULT == 8 and S["seed_input"].default == C.SEED_DEFAULT == 490 and S["buffer_slider"].default == C.BUFFER_DEFAULT == 6
    assert S["plugs_slider"].hi == C.N_STACKS_RANGE[1] - 1 and S["buffer_slider"].hi == S["plugs_slider"].hi * C.MAX_HEIGHT_RANGE[1]
    for key, spec in S.items():
        assert P.bounds(key) == (spec.lo, spec.hi)
        if spec.lo is not None:
            assert spec.lo <= spec.default <= spec.hi
            if spec.step and spec.step > 1:
                assert (spec.default - spec.lo) % spec.step == 0
    assert len({spec.url_param for spec in S.values()}) == len(S) and {spec.url_param for spec in S.values()} == {"ns", "mh", "fp", "nc", "rp", "ps", "sg", "bf", "seed", "vw"}
    assert S["view_radio"].default in C.RIGHT_VIEW_KEYS and C.BASELINE not in C.RIGHT_VIEW_KEYS


def test_every_preset_is_inside_bounds_on_the_step_and_respects_the_dependent_limits():
    assert list(C.PRESETS) == ["Passend", "Zu wenige", "Zu viele", "Unsicher", "Großer Block"] and all(len(n) <= 16 for n in C.PRESETS)
    for name, p in C.PRESETS.items():
        assert set(p) == set(P.PRESET_STATE_KEYS)
        for field, state_key in P.PRESET_STATE_KEYS.items():
            spec = S[state_key]
            assert spec.lo <= p[field] <= spec.hi, (name, field)
            if spec.step and spec.step > 1:
                assert (p[field] - spec.lo) % spec.step == 0, (name, field)
        assert P.clamp_settings(p["n_stacks"], p["max_height"], p["plug_stacks"], p["buffer"]) == (p["plug_stacks"], p["buffer"]), name        # berechnete Grenzen halten
    assert len({p["seed"] for p in C.PRESETS.values()}) == 1                                                                                    # eine gemeinsame Block-Nummer


def test_preset_buffers_are_the_rule_of_thumb():
    import rfr_scenario as SC
    for name, p in C.PRESETS.items():
        cap = SC.capacity_for(p["n_stacks"], p["max_height"], p["fill_pct"] / 100)
        assert p["buffer"] == SC.rule_of_thumb_buffer(cap, p["max_height"], p["reefer_pct"], p["plug_stacks"]), name


def test_dependent_limits():
    assert P.dependent_limits(8, 5, 3) == (7, 15) and P.dependent_limits(4, 2, 3) == (3, 6) and P.dependent_limits(8, 5, 0) == (7, 0)
    assert P.dependent_limits(8, 5, 99) == (7, 35)                                                        # Steckdosen-Stapel werden zuerst auf Stapel - 1 begrenzt


def test_clamp_settings_limits_instead_of_dropping():
    assert P.clamp_settings(8, 5, 3, 6) == (3, 6)
    assert P.clamp_settings(8, 5, 3, 99) == (3, 15)                                                       # Puffer über den Steckdosen-Plätzen
    assert P.clamp_settings(4, 5, 11, 99) == (3, 15)                                                      # Steckdosen-Stapel über Stapel minus 1, dann Puffer
    assert P.clamp_settings(8, 5, 0, 6) == (0, 0) and P.clamp_settings(8, 5, -2, -3) == (0, 0)
    assert P.clamp_settings(5, 2, 4, 8) == (4, 8) and P.clamp_settings(5, 2, 4, 9) == (4, 8)


def test_encoders_roundtrip_through_parse():
    for key, spec in S.items():
        assert P.parse_setting(spec, spec.encoder(spec.default)) == spec.default


def test_preset_state_keys_map_the_right_sliders():
    assert P.PRESET_STATE_KEYS == {"n_stacks": "n_stacks_slider", "max_height": "max_height_slider", "fill_pct": "fill_slider", "n_containers": "n_containers_slider",
                                   "reefer_pct": "reefer_slider", "plug_stacks": "plugs_slider", "sigma_pct": "sigma_slider", "buffer": "buffer_slider", "seed": "seed_input"}
