"""Inhalt der App: Tabs, Kernfragen, Expander (per Titel, nie per Index), Handbeispiel, PDF-Knopf, Gleichheit von App- und README-Text."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import zpf_texts as TX

pytestmark = pytest.mark.usefixtures("fast_tuning")
ROOT = Path(__file__).resolve().parent.parent
APP = str(ROOT / "app.py")


@pytest.fixture(scope="module")
def at():
    a = AppTest.from_file(APP, default_timeout=300)
    a.run()
    assert not a.exception, [str(e) for e in a.exception]
    return a


def test_vier_tabs_in_fester_reihenfolge(at):
    assert [t.label for t in at.tabs] == ["✋ Von Hand", "🔬 Akt 1: Kalender oder Messen?", "🏖️ Akt 2: Urlaub", "⚠️ Grenzen"]


def test_expander_stehen_unter_ihren_titeln(at):
    labels = {e.label for e in at.expander}
    assert {
        "🔧 Wie wir das erreichen – vollständiger Methodenvergleich",
        "📐 Mathematische Formulierung",
        "⚠️ Annahmen, Grenzen und bekannte Probleme",
    } <= labels


def test_kernfragen_haben_ein_verdikt(at):
    texts = [e.value for e in list(at.success) + list(at.info) + list(at.warning)]
    assert any("Lernend gegen lernend" in t for t in texts)  # Verdikt zu Akt 1 (Lerner)
    assert any("vor der Abreise" in t for t in texts)         # Umschlagpunkte zu Akt 2


def test_handbeispiel_zeigt_den_exakten_bruch(at):
    metric = next(m for m in at.metric if m.label == "Trockenstress in der Abwesenheit")
    assert metric.value == "2.0453" and "103544/50625" in metric.delta


def test_handbeispiel_regler_aendern_den_bruch():
    a = AppTest.from_file(APP, default_timeout=300)
    a.run()
    a.slider(key="hand_a").set_value(9).run()
    assert next(m for m in a.metric if m.label == "Trockenstress in der Abwesenheit").value == "0.0000"
    a.slider(key="hand_a").set_value(14).run()
    a.checkbox(key="hand_dock").set_value(True).run()
    assert next(m for m in a.metric if m.label == "Trockenstress in der Abwesenheit").value == "0.0000"


def test_pdf_knopf_ist_da(at):
    assert any(getattr(el, "type", "") == "download_button" or "download" in str(type(el)).lower() for el in at.main)


def test_annahmentext_der_app_steht_in_der_readme():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert TX.ASSUMPTIONS_MARKDOWN.strip() in readme
