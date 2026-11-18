"""Presets: gültige Werte, Hilfetexte, Standard-Preset = Standardeinstellungen, Schlüssel gedeckt."""

import zpf_constants as C
import zpf_presets as P


def test_every_preset_has_help():
    assert set(C.PRESETS) == set(C.PRESET_HELP)
    assert all(C.PRESET_HELP[n] for n in C.PRESETS)


def test_preset_keys_are_known_settings():
    for name, preset in C.PRESETS.items():
        assert set(preset) <= set(P.PRESET_KEYS), name


def test_preset_values_are_inside_the_slider_bounds():
    for name, preset in C.PRESETS.items():
        for key, value in preset.items():
            spec = P.SETTING_SPECS[P.PRESET_KEYS[key]]
            assert spec.lo <= value <= spec.hi, (name, key, value)


def test_default_preset_changes_nothing():
    assert C.PRESETS["Standard (Voreinstellung)"] == {}


def test_setting_specs_cover_every_preset_key():
    assert set(P.PRESET_KEYS.values()) == set(P.SETTING_SPECS)


def test_defaults_inside_bounds():
    for key, spec in P.SETTING_SPECS.items():
        assert spec.lo <= spec.default <= spec.hi, key
