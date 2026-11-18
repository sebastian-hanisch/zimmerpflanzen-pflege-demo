"""Permalink (Begrenzen), Presets und Zufalls-Seed-Button (Standardmuster aus dem Demo-Portfolio)."""

import random
from dataclasses import dataclass

import streamlit as st

import zpf_constants as C


@dataclass(frozen=True)
class SettingSpec:
    url_param: str
    caster: type
    default: object
    lo: float | None = None
    hi: float | None = None


SETTING_SPECS = {
    "amp_slider": SettingSpec("amp", float, C.DEFAULT_AMP, C.AMP_MIN, C.AMP_MAX),
    "ar_slider": SettingSpec("ar", float, C.DEFAULT_AR, C.AR_MIN, C.AR_MAX),
    "sigma_slider": SettingSpec("sigma", float, C.DEFAULT_SIGMA, C.SIGMA_MIN, C.SIGMA_MAX),
    "cc_slider": SettingSpec("cc", float, C.DEFAULT_CC, C.CC_MIN, C.CC_MAX),
    "cw_slider": SettingSpec("cw", float, C.DEFAULT_CW, C.CW_MIN, C.CW_MAX),
    "wrot_slider": SettingSpec("wrot", float, C.DEFAULT_WROT, C.WROT_MIN, C.WROT_MAX),
    "v_slider": SettingSpec("v", int, C.DEFAULT_V, C.V_MIN, C.V_MAX),
    "a_slider": SettingSpec("A", int, C.DEFAULT_A, C.A_MIN, C.A_MAX),
    "season_radio": SettingSpec("season", int, C.DEFAULT_SEASON, C.SEASON_SUMMER, C.SEASON_WINTER),
    "dock_slider": SettingSpec("dock", float, C.DEFAULT_DOCK, C.DOCK_MIN, C.DOCK_MAX),
    "shade_slider": SettingSpec("shade", float, C.DEFAULT_SHADE, C.SHADE_MIN, C.SHADE_MAX),
    "visits_slider": SettingSpec("visits", int, C.DEFAULT_VISITS, C.VISITS_MIN, C.VISITS_MAX),
    "paths_slider": SettingSpec("paths", int, C.DEFAULT_PATHS, C.PATHS_MIN, C.PATHS_MAX),
    "seed_input": SettingSpec("seed", int, C.DEFAULT_SEED, 0, C.SEED_MAX),
}
PRESET_KEYS = {spec.url_param: state_key for state_key, spec in SETTING_SPECS.items()}


def init_session_state_defaults():
    for state_key, spec in SETTING_SPECS.items():
        if state_key not in st.session_state:
            st.session_state[state_key] = spec.default


def bounds(state_key):
    spec = SETTING_SPECS[state_key]
    return spec.lo, spec.hi


def load_permalink_settings():
    """Einmal je Sitzung: Werte aus der Adresszeile übernehmen, auf die Reglergrenzen begrenzt."""
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    for state_key, spec in SETTING_SPECS.items():
        if spec.url_param in qp:
            try:
                value = spec.caster(qp[spec.url_param])
            except (ValueError, TypeError):
                continue
            if spec.lo is not None:
                value = max(spec.lo, value)
            if spec.hi is not None:
                value = min(spec.hi, value)
            st.session_state[state_key] = value
    st.session_state["permalink_loaded"] = True


def sync_query_params(values):
    """`values`: {state_key: aktueller Wert}; die Adresszeile spiegelt die Konfiguration."""
    try:
        for state_key, value in values.items():
            st.query_params[SETTING_SPECS[state_key].url_param] = str(value)
    except Exception:
        pass


def apply_preset(name):
    """Ein Preset setzt ALLE Regler: was es nicht nennt, geht auf den Standardwert (so wie aktives_preset vergleicht)."""
    for state_key, spec in SETTING_SPECS.items():
        st.session_state[state_key] = C.PRESETS[name].get(spec.url_param, spec.default)


def aktives_preset():
    """Name des Presets, dessen Werte GENAU den aktuellen Einstellungen entsprechen, sonst None.

    Zustandslos: verglichen wird jeder Regler aus SETTING_SPECS (ein Preset ohne Eintrag für einen Regler meint dessen
    Standardwert) mit dem Session State. Ein später ergänzter Regler braucht nur seinen Eintrag in SETTING_SPECS,
    dann hebt auch seine Änderung die Markierung auf (tests/test_layout.py prüft das für jeden Regler)."""
    preset_key_of = {state_key: key for key, state_key in PRESET_KEYS.items()}
    for name, preset in C.PRESETS.items():
        if all(
            st.session_state.get(state_key, spec.default) == preset.get(preset_key_of.get(state_key), spec.default)
            for state_key, spec in SETTING_SPECS.items()
        ):
            return name
    return None


def sidebar_presets():
    """Schnellstart oben in der Seitenleiste; das aktive Preset ist hervorgehoben (`type="primary"`)."""
    if not C.PRESETS:
        return
    st.header("🎯 Schnellstart")
    st.caption("Ein Beispielszenario laden:")
    aktiv = aktives_preset()
    for name in C.PRESETS:
        st.button(
            name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP.get(name, ""), key=f"preset_{name}",
            type="primary" if aktiv == name else "secondary",
        )


def randomize_seed():
    st.session_state["seed_input"] = random.randint(0, C.SEED_MAX)
