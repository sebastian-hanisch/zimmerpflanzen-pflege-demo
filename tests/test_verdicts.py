"""Verdikte (reine Funktionen in zpf_evaluation.py) an handgesetzten Werten: jede Schwelle und jede Zahl im Text."""

import pytest

import zpf_evaluation as ev


def test_pct_diff_und_nenner_null():
    assert ev.pct_diff(15.0, 20.0) == pytest.approx(-25.0)
    assert ev.pct_diff(1.0, 0.0) is None and ev.ratio(1.0, 0.0) is None
    assert ev.ratio(67.9, 19.1) == pytest.approx(3.555, abs=1e-3)


@pytest.mark.parametrize(
    "measure, kind, fragment",
    [
        (19.0, "success", "Messen lohnt hier"),   # -5,0 %: Grenze gehört zu „lohnt“
        (19.1, "info", "knapp vorn"),             # -4,5 %
        (19.7, "info", "knapp vorn"),             # -1,5 %
        (19.9, "info", "Gleichauf"),              # -0,5 %
        (20.0, "info", "Gleichauf"),              # 0 %
        (20.2, "info", "Gleichauf"),              # +1,0 %: Grenze gehört zu „gleichauf“
        (20.3, "warning", "Kalender gewinnt"),    # +1,5 %
    ],
)
def test_kreuz_verdikt_schwellen(measure, kind, fragment):
    k, text = ev.kreuz_verdikt(measure, 20.0, "Schwelle", "Kalender")
    assert k == kind and fragment in text


def test_kreuz_verdikt_nennt_die_zahlen():
    _, text = ev.kreuz_verdikt(15.0, 20.0, "Schwelle", "Kalender")
    assert "15.0" in text and "20.0" in text and "25 %" in text


def test_kreuz_verdikt_ohne_bezug():
    k, text = ev.kreuz_verdikt(1.0, 0.0, "a", "b")
    assert k == "info" and "nicht möglich" in text


def test_lerner_verdikt():
    assert ev.lerner_verdikt(22.7, 20.2)[0] == "success"   # -11 %
    assert ev.lerner_verdikt(22.7, 22.9)[0] == "info"      # +0,9 %
    assert ev.lerner_verdikt(20.0, 22.0)[0] == "warning"   # +10 %
    assert "11 %" in ev.lerner_verdikt(22.7, 20.2)[1]
    assert ev.lerner_verdikt(0.0, 1.0)[0] == "info"


def test_umschlagtext():
    assert "ab 12 Tagen" in ev.umschlag_text("Sukkulente", 12)
    assert "schon bei kurzer" in ev.umschlag_text("Durstig", "immer")
    assert "nicht gießen" in ev.umschlag_text("Sukkulente", "nie")
