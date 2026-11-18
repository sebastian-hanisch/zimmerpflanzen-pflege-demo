"""Kern gegen Handrechnung: jede Einheit der Dynamik und der Strategien an der Mini-Instanz (Zimmerpflanze, D = 9, s* = 0,4, Welkepunkt 0,15,
Fäulnisgrenze 0,75, k = 1/15, ohne Streuung, Rauschen und Jahreszeit). Die Brüche stehen in zpf_hand.py; die vektorisierte Fassung der App muss sie treffen."""

from fractions import Fraction as F

import numpy as np
import pytest
from conftest import deterministic_run

import zpf_absence as AB
import zpf_algorithm as A
import zpf_hand as H

SS, SW = 0.4, 0.15


def test_rho_und_zeta_an_drei_punkten():
    # oberhalb des Stressbeginns volle Rate, am Welkepunkt Stillstand, dazwischen linear: (0,275 - 0,15)/(0,4 - 0,15) = 1/2
    assert A.rho(0.9, SS, SW) == 1.0 and A.rho(0.15, SS, SW) == 0.0 and A.rho(0.275, SS, SW) == pytest.approx(0.5)
    assert A.zeta(0.4, SS, SW) == 0.0 and A.zeta(0.275, SS, SW) == pytest.approx(0.5) and A.zeta(0.1, SS, SW) == 1.0


def test_ein_tag_austrocknung_von_hand():
    assert A.dry_step(1.0, 1 / 15, SS, SW) == pytest.approx(14 / 15)  # volle Rate
    assert A.dry_step(0.275, 0.1, SS, SW) == pytest.approx(0.275 - 0.1 * 0.5)  # halbe Rate bei halber Strecke
    assert A.dry_step(0.16, 5.0, SS, SW) == pytest.approx(0.15)  # nie unter dem Welkepunkt


def test_faeulnisschaden_von_hand():
    # Sukkulente (Grenze 1/2) gegossen bei Feuchte 7/10: (7/10 - 1/2)/(1 - 1/2) = 2/5; unter der Grenze 0; ohne Grenze (1,0) immer 0
    assert float(A.rot_damage(0.7, 0.5)) == pytest.approx(0.4)
    assert float(A.rot_damage(0.4, 0.5)) == 0.0 and float(A.rot_damage(1.0, 1.0)) == 0.0
    assert H.rot(F(7, 10), F(1, 2)) == F(2, 5)


def test_jahreszeitfaktor():
    assert A.season_factor(0, 0.4) == pytest.approx(0.6)  # Tag 0: Winter, 40 % langsamer
    assert A.season_factor(182.5, 0.4) == pytest.approx(1.4)  # Hochsommer
    assert A.season_factor(100, 0.0) == 1.0


def test_verlustformel():
    assert A.loss_from(2.0, 0.5, 10, 100, (5.0, 0.3, 0.02)) == pytest.approx(2 + 2.5 + 3 + 2)


def test_handbeispiel_schwelle_36_giessvorgaenge_ohne_stress(mini_plants):
    pl = mini_plants
    th = np.where(pl.cls == 1, 0.4, 0.0)
    res = deterministic_run(A, pl, A.Schwelle(th, 0.0, 1))
    m = pl.cls == 1
    assert np.allclose(res["nw"][:, m], 36) and np.allclose(res["dry"][:, m], 0)
    days = H.threshold_days(365)
    assert len(days) == 36 and days[:3] == [10, 20, 30]  # Tage 10, 20, ..., 360


def test_takt_10_gleich_36_giessvorgaenge(mini_plants):
    res = deterministic_run(A, mini_plants, A.Takt(np.full(mini_plants.n, 10)))
    assert np.allclose(res["nw"], 36)


def test_takt_saison_mit_gleichen_abstaenden_wie_takt(mini_plants):
    res = deterministic_run(A, mini_plants, A.TaktSaison(np.full(mini_plants.n, 10), np.full(mini_plants.n, 10)))
    assert np.allclose(res["nw"], 36)


def test_takt_saison_schaltet_im_winter_um(mini_plants):
    pl = mini_plants
    res = deterministic_run(A, pl, A.TaktSaison(np.full(pl.n, 20), np.full(pl.n, 5)), record=True)
    days = np.where(res["water"][0, 0])[0]
    assert days[0] == 20 and (np.diff(days[days < 91]) == 20).all()  # Winter: Abstand 20
    assert (np.diff(days[(days > 91) & (days < 274)]) == 5).all()  # Sommer: Abstand 5


def test_schwelle_zaehlt_kontrollen_nur_an_pruftagen(mini_plants):
    res = deterministic_run(A, mini_plants, A.Schwelle(np.full(mini_plants.n, 0.4), 0.0, 3))
    assert np.allclose(res["nc"], 121)  # Tage 3, 6, ..., 363


def test_gieszeit_setzt_auf_voll_und_feuchte_nie_unter_welkepunkt(plants):
    res = A.run(plants, 0.4, A.Takt(np.full(plants.n, 9)), 3, 5, record=True)
    tr = res["traj"]
    assert (tr >= plants.sw[None, :, None] - 1e-12).all() and (tr <= 1.0).all()
    assert (tr[res["water"]] == 1.0).all()


def test_ohne_giessen_faellt_die_feuchte_nur(plants):
    res = A.run(plants, 0.4, A.Takt(np.full(plants.n, 1000)), 2, 5, record=True)
    assert (np.diff(res["traj"], axis=2) <= 1e-12).all()


def test_stress_je_jahr_liegt_zwischen_0_und_365(plants):
    res = A.run(plants, 0.4, A.Takt(np.full(plants.n, 1000)), 2, 5)
    assert (res["dry"] >= 0).all() and (res["dry"] <= 365).all()


def test_urlaub_von_hand(mini_plants):
    pl = mini_plants
    m = pl.cls == 1
    s0 = np.ones((1, pl.n))
    noise = np.ones((1, 40, pl.n))
    allw = np.ones(pl.n, bool)
    exact = H.absence_stress(14)
    assert exact == F(103544, 50625)  # von Hand: t = 10..13 mit Stress 0,2667 / 0,4622 / 0,6056 / 0,7108
    assert AB.absence(pl, 0.0, 0, 9, s0, allw, noise)["dry"][0, m] == pytest.approx(0, abs=1e-9)
    assert AB.absence(pl, 0.0, 0, 14, s0, allw, noise)["dry"][0, m] == pytest.approx(float(exact), rel=1e-12)
    assert AB.absence(pl, 0.0, 0, 14, s0, allw, noise, dock=allw)["dry"][0, m] == pytest.approx(0, abs=1e-9)  # Docht 0,5 überbrückt 14 Tage
    assert AB.absence(pl, 0.0, 0, 14, s0, allw, noise, visits=(10,))["dry"][0, m] == pytest.approx(0, abs=1e-9)


def test_urlaub_ohne_giessen_vor_abreise_hat_keinen_faeulnisschaden(mini_plants):
    pl = mini_plants
    s0 = np.full((1, pl.n), 0.5)
    noise = np.ones((1, 3, pl.n))
    r = AB.absence(pl, 0.0, 0, 3, s0, np.zeros(pl.n, bool), noise)
    assert (r["rot"] == 0).all()  # kein Gießen, kein Fäulnisschaden


def test_abgestimmter_takt_schlaegt_wochentakt(plants):
    w = (5.0, 0.3, 0.02)
    Ts = A.tune(plants, 0.4, w, lambda g, n: A.Takt(np.full(n, g)), (4, 7, 10, 14), S=10, ar=0.95)
    tuned = A.loss(A.run(plants, 0.4, A.Takt([float(t) for t in Ts]), 20, 77, ar=0.95), w).mean()
    week = A.loss(A.run(plants, 0.4, A.Takt(np.full(plants.n, 7)), 20, 77, ar=0.95), w).mean()
    assert tuned < week
