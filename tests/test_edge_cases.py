"""Randfälle: ein Pfad, ohne Zufall, kürzeste und längste Abwesenheit, Rauschen 0, alle Gewichte 0."""

import numpy as np
import pytest

import zpf_absence as AB
import zpf_algorithm as A
import zpf_constants as C
import zpf_strategies as ST


def test_ein_pfad(plants):
    res = A.run(plants, C.DEFAULT_AMP, A.Takt(np.full(plants.n, 7)), 1, 3)
    assert res["dry"].shape == (1, plants.n) and np.isfinite(res["dry"]).all()


def test_ohne_jahreszeit_und_ohne_wetter_sind_alle_pfade_gleich(plants):
    res = A.run(plants, 0.0, A.Takt(np.full(plants.n, 7)), 2, 3, ar=0.0, common_sd=0.0, indiv_sd=0.0)
    assert np.allclose(res["dry"][0], res["dry"][1])


@pytest.mark.parametrize("n_days", [C.A_MIN, C.A_MAX])
def test_urlaub_an_den_grenzen(plants, n_days):
    S = 4
    s0 = np.ones((S, plants.n))
    noise = AB.absence_noise(S, n_days, plants.n, 5, 0.95)[0]
    allm = np.ones(plants.n, bool)
    r = AB.absence(plants, 0.4, 195, n_days, s0, allm, noise, dock=allm, shade=allm, visits=(1,))
    assert np.isfinite(r["dry"]).all() and (r["dry"] >= 0).all()


def test_messrauschen_null_kontrolle_gratis(plants):
    rows = ST.compare(plants, 0.4, 0.95, (5.0, 0.3, 0.0), 0.0, 3, 5, 9, include_lerner=False)
    assert all(np.isfinite(r["loss"]) for r in rows)


def test_alle_gewichte_null_nur_trockenstress_zaehlt(plants):
    rows = ST.compare(plants, 0.4, 0.95, (0.0, 0.0, 0.0), 0.15, 3, 5, 9, include_lerner=False)
    assert rows[0]["loss"] == pytest.approx(rows[0]["dry"])


def test_umschlagpunkt_bei_einer_dauer_ist_immer_oder_nie(plants):
    S = 3
    s0 = np.ones((S, plants.n))
    turn, curves = AB.turnover_day(plants, 0.4, 195, s0, lambda a: AB.absence_noise(S, a, plants.n, 5, 0.95)[0], 5.0, a_grid=(5,))
    assert all(v in ("immer", "nie") for v in turn.values())
    assert all(len(c) == 1 for c in curves.values())
