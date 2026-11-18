"""Gemeinsame Fixtures: Pflanzen und die Mini-Instanz, an der jede Einheit von Hand geprüft wird (DEMO-PLAYBOOK §1b)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import zpf_plants as PL  # noqa: E402
import zpf_strategies as ST  # noqa: E402


@pytest.fixture(scope="session")
def plants():
    """Die zwölf Pflanzen der App (Streuung der Trockenzeit 25 %)."""
    return PL.make_plants()


@pytest.fixture(scope="session")
def mini_plants():
    """Zwölf Pflanzen ohne Streuung: Zimmerpflanzen haben genau D = 9, s* = 0,4, Welkepunkt 0,15, Fäulnisgrenze 0,75 (Handbeispiel)."""
    return PL.make_plants(het=0.0)


@pytest.fixture(scope="module")
def fast_tuning():
    """Für App-Tests: kleine Abstimmgitter, damit ein Lauf der App Sekunden statt einer halben Minute dauert (nur die Gitter, nicht die Regeln).
    Modul-Umfang: test_claims.py rechnet mit den echten Gittern und darf die Verkleinerung nie sehen."""
    mp = pytest.MonkeyPatch()
    mp.setattr(ST, "T_GRID", (5, 10))
    mp.setattr(ST, "PAIR_GRID", ((6, 6), (12, 6)))
    mp.setattr(ST, "TH_GRID", (0.4, 0.6))
    mp.setattr(ST, "LERNER_GRID", ((2, 0.15),))
    mp.setattr(ST, "LERNADAPTIV_GRID", ((0.06, 0.02),))
    yield
    mp.undo()


def deterministic_run(A, plants, pol, amp=0.0, S=2, days=365, record=False):
    """Lauf ohne Zufall (kein Wetter-, kein Pflanzenrauschen): reine Dynamik."""
    return A.run(plants, amp, pol, S, 1, days=days, ar=0.0, common_sd=0.0, indiv_sd=0.0, record=record)
