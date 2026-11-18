"""Jede Zahl der README („Befunde") wird hier nachgerechnet, mit den Reglerwerten und Zufalls-Seeds, die die README nennt.

Neu gerechnete Zahlen werden als Band verglichen (relative Toleranz), nicht bitgenau: unter Linux ändert sich die letzte Binärstelle von
exp/cos, und Gleichstände bei der Abstimmung können einen Parameter verschieben (DEMO-PLAYBOOK §5). Das vorgerechnete Raster (data/kreuzung.csv) wird
exakt gelesen. Die Zahlen der Vormessung (pflanzenpflege-planung/) sind Erwartungen; hier stehen die Zahlen dieses Codes."""

import csv
import itertools
from pathlib import Path

import numpy as np
import pytest

import zpf_absence as AB
import zpf_algorithm as A
import zpf_constants as C
import zpf_grid as G
import zpf_hand as H
import zpf_plants as PL
import zpf_strategies as ST

ROOT = Path(__file__).resolve().parent.parent
STD = dict(amp=0.4, ar=0.95, w=(5.0, 0.3, 0.02), sigma=0.15, v=3, paths=100, seed=1000)


@pytest.fixture(scope="module")
def plants():
    return PL.make_plants()


@pytest.fixture(scope="module")
def table(plants):
    rows = ST.compare(plants, STD["amp"], STD["ar"], STD["w"], STD["sigma"], STD["v"], STD["paths"], STD["seed"])
    return {r["name"]: r for r in rows}


# ----------------------------------------------------------------------------------------------------------- Akt 1, Standardfall
def test_standardfall_verluste(table):
    expected = {
        "Wochentakt für alle (7 Tage)": 67.9,
        "Kalender je Pflanze (ein Abstand, abgestimmt)": 23.6,
        "Kalender Sommer/Winter je Pflanze (abgestimmt)": 19.1,
        "Schwelle, alle 3 Tage prüfen (abgestimmt)": 21.2,
        "Adaptive Kontrolle f = 0.5 (abgestimmt)": 18.3,
        "Adaptive Kontrolle f = 0.75 (abgestimmt)": 18.5,
        "Kalender, Lerner (Probieren)": 22.7,
        "Adaptive Kontrolle, Lerner (Probieren)": 20.2,
    }
    for name, value in expected.items():
        assert table[name]["loss"] == pytest.approx(value, rel=0.04), name


def test_standardfall_abgeleitete_aussagen(table):
    wt = table["Wochentakt für alle (7 Tage)"]["loss"]
    ein = table["Kalender je Pflanze (ein Abstand, abgestimmt)"]["loss"]
    sw = table["Kalender Sommer/Winter je Pflanze (abgestimmt)"]["loss"]
    ad = table["Adaptive Kontrolle f = 0.5 (abgestimmt)"]["loss"]
    lk = table["Kalender, Lerner (Probieren)"]["loss"]
    la = table["Adaptive Kontrolle, Lerner (Probieren)"]["loss"]
    assert wt / sw == pytest.approx(3.5, abs=0.3)  # Wochentakt rund 3,5-mal so schlecht wie der Sommer/Winter-Kalender
    assert 100 * (sw - ein) / ein == pytest.approx(-19, abs=2.5)  # Jahreszeit im Kalender: rund -19 %
    assert 100 * (ad - sw) / sw == pytest.approx(-4, abs=2.5)  # Messen knapp vor dem besten Kalender
    sch = table["Schwelle, alle 3 Tage prüfen (abgestimmt)"]["loss"]
    assert 100 * (sch - sw) / sw == pytest.approx(11, abs=3)  # die einfache Schwelle liegt rund 11 % über dem besten Kalender
    assert 100 * (lk - sw) / sw == pytest.approx(19, abs=3)  # Kalender durch Probieren rund 19 % über dem abgestimmten
    assert 100 * (la - lk) / lk == pytest.approx(-11, abs=3)  # lernend gegen lernend: adaptive Kontrolle rund 11 % besser
    assert wt > ein > sw  # Rangfolge der Kalender


def test_wochentakt_trifft_die_sukkulenten_am_haertesten(table):
    bc = table["Wochentakt für alle (7 Tage)"]["by_class"]
    assert bc["Sukkulente"] == pytest.approx(132, rel=0.05)
    assert bc["Sukkulente"] > bc["Durstig"] > bc["Zimmerpflanze"]


def test_kontrollzahlen(table):
    assert table["Schwelle, alle 3 Tage prüfen (abgestimmt)"]["nc"] == 121  # Tage 3, 6, ..., 363
    assert table["Wochentakt für alle (7 Tage)"]["nc"] == 0
    assert table["Adaptive Kontrolle f = 0.5 (abgestimmt)"]["nc"] == pytest.approx(173, rel=0.05)


# ----------------------------------------------------------------------------------------------------------- Raster
def _grid_rel(w, sigma, cc):
    rows = G.load()
    return next(r["rel_pct"] for r in rows if r["w_rot"] == w and r["sigma"] == sigma and r["cc"] == cc)


def test_raster_ist_vollstaendig():
    rows = G.load()
    assert len(rows) == len(C.GRID_WROT) * len(C.GRID_CC) * len(C.GRID_SIGMA) == 60
    assert {r["measure"] for r in rows} <= {"Schwelle alle 1 Tage", "Schwelle alle 3 Tage", "Schwelle alle 7 Tage",
                                            "Adaptive Kontrolle f = 0.5", "Adaptive Kontrolle f = 0.75"}


def test_raster_zellen_der_readme():
    # exakter Sensor, Kontrolle gratis: Messen klar vorn; mit Kontrollkosten 0,05 kippt es bei Fäulnisgewicht 5
    assert _grid_rel(5.0, 0.0, 0.0) == pytest.approx(-39, abs=1)
    assert _grid_rel(5.0, 0.0, 0.02) == pytest.approx(-21, abs=1)
    assert _grid_rel(5.0, 0.0, 0.05) == pytest.approx(2, abs=1)
    assert _grid_rel(5.0, 0.0, 0.1) == pytest.approx(35, abs=1)
    # grobe Fingerprobe (Rauschen 0,3): Messen verliert in jeder Zelle
    assert all(r["rel_pct"] > 0 for r in G.load() if r["sigma"] == 0.3)
    assert min(r["rel_pct"] for r in G.load() if r["sigma"] == 0.3) == pytest.approx(15, abs=1)
    # Rauschen 0,2 ohne Kontrollkosten: bei Fäulnisgewicht 1 und 20 vorn (-9 und -16 %)
    assert _grid_rel(1.0, 0.2, 0.0) == pytest.approx(-9, abs=1)
    assert _grid_rel(5.0, 0.2, 0.0) == pytest.approx(-12, abs=1)
    assert _grid_rel(20.0, 0.2, 0.0) == pytest.approx(-16, abs=1)
    # genauer Sensor, Kontrolle 0,05: Fäulnisgewicht 20 noch vorn (-10 %), Gewicht 1 schon hinten (+9 %)
    assert _grid_rel(20.0, 0.0, 0.05) == pytest.approx(-10, abs=1)
    assert _grid_rel(1.0, 0.0, 0.05) == pytest.approx(9, abs=1)


def test_raster_kalenderverlust_je_gewicht():
    cal = {w: next(r["cal_loss"] for r in G.load() if r["w_rot"] == w) for w in C.GRID_WROT}
    assert cal[1.0] == pytest.approx(17.87, abs=0.01) and cal[5.0] == pytest.approx(19.10, abs=0.2) and cal[20.0] == pytest.approx(21.6, abs=0.5)
    # der Kalender-Verlust ist je Gewicht in allen Zellen gleich (er hängt weder an Kontrollkosten noch an Rauschen)
    for w in C.GRID_WROT:
        assert len({r["cal_loss"] for r in G.load() if r["w_rot"] == w}) == 1


def test_raster_csv_hat_dieselben_zahlen_wie_die_datei_auf_der_platte():
    with open(ROOT / "data" / "kreuzung.csv", encoding="utf-8", newline="") as fh:
        n = sum(1 for _ in csv.DictReader(fh))
    assert n == 60


# ----------------------------------------------------------------------------------------------------------- Akt 2
def _calendar_spec(plants, w):
    rows = ST.compare(plants, 0.4, 0.95, (w, 0.3, 0.02), 0.15, 3, 20, 1, include_lerner=False)
    return next(r for r in rows if r["name"].startswith("Kalender Sommer"))["spec"]


def _turnover(plants, spec, w, d0):
    pol = ST.make_policy(spec, plants, 0.0)
    s0 = AB.departure_state(plants, 0.4, pol, d0, 100, 1000, 0.95)
    turn, _ = AB.turnover_day(plants, 0.4, d0, s0, lambda a: AB.absence_noise(100, a, plants.n, 1001, 0.95)[0], w)
    return turn, s0


@pytest.fixture(scope="module")
def turnover(plants):
    out = {}
    for w in (1.0, 5.0, 20.0):
        spec = _calendar_spec(plants, w)  # der Kalender wird je Fäulnisgewicht neu abgestimmt (nicht einmal für alle)
        for d0 in (195, 15):
            out[(w, d0)] = _turnover(plants, spec, w, d0)
    return out


def _check(value, expected):
    if isinstance(expected, str):
        assert value == expected
    else:
        assert isinstance(value, int) and abs(value - expected) <= 1  # ±1 Tag: Gleichstände der Abstimmung, plattformabhängig


def test_umschlagpunkte_der_readme(turnover):
    table = {
        (1.0, 195): dict(Sukkulente=10, Zimmerpflanze="immer", Durstig="immer"),
        (5.0, 195): dict(Sukkulente=10, Zimmerpflanze="immer", Durstig="immer"),
        (20.0, 195): dict(Sukkulente=10, Zimmerpflanze=9, Durstig="immer"),
        (1.0, 15): dict(Sukkulente=12, Zimmerpflanze=7, Durstig="immer"),
        (5.0, 15): dict(Sukkulente=18, Zimmerpflanze=12, Durstig="immer"),
        (20.0, 15): dict(Sukkulente=27, Zimmerpflanze="nie", Durstig="immer"),
    }
    for key, exp in table.items():
        for name, e in exp.items():
            _check(turnover[key][0][name], e)


def test_umschlagpunkt_waechst_im_winter_mit_dem_faeulnisgewicht(turnover):
    for name in ("Sukkulente",):
        vals = [turnover[(w, 15)][0][name] for w in (1.0, 5.0, 20.0)]
        assert vals[0] < vals[1] < vals[2]
    assert all(turnover[(w, d0)][0]["Durstig"] == "immer" for w in (1.0, 5.0, 20.0) for d0 in (195, 15))


def test_hilfen_im_hochsommer(plants, turnover):
    s0 = turnover[(5.0, 195)][1]
    allw = np.ones(plants.n, bool)
    res = {}
    for a_days in (7, 28):
        noise = AB.absence_noise(100, a_days, plants.n, 1001, 0.95)[0]
        base = AB.absence(plants, 0.4, 195, a_days, s0, allw, noise)
        dock = AB.absence(plants, 0.4, 195, a_days, s0, allw, noise, dock=allw, reservoir=0.5)
        shade = AB.absence(plants, 0.4, 195, a_days, s0, allw, noise, shade=allw, shade_f=0.5)
        res[a_days] = (AB.class_means(plants, base["dry"]), AB.class_means(plants, base["dry"] - dock["dry"]),
                       AB.class_means(plants, base["dry"] - shade["dry"]))
    assert res[7][0]["Alle"] == pytest.approx(0.45, abs=0.05)
    assert res[28][0]["Alle"] == pytest.approx(16.5, abs=0.8)
    d7 = res[7][1]
    assert d7["Durstig"] == pytest.approx(0.95, abs=0.1) and d7["Zimmerpflanze"] == pytest.approx(0.31, abs=0.1) and d7["Sukkulente"] == pytest.approx(0.0, abs=0.02)
    d28, s28 = res[28][1], res[28][2]
    assert d28["Sukkulente"] > d28["Zimmerpflanze"] > d28["Durstig"]  # bei den Standard-Annahmen
    assert d28["Sukkulente"] == pytest.approx(6.5, abs=0.5) and d28["Durstig"] == pytest.approx(5.0, abs=0.5)
    assert s28["Alle"] > d28["Alle"]  # Schatten (Faktor 0,5) nützt mehr als der Docht (Vorrat 0,5)
    assert s28["Alle"] == pytest.approx(8.2, abs=0.5) and d28["Alle"] == pytest.approx(5.6, abs=0.5)


def test_nachbar_gleichmaessig_ist_fast_optimal(plants, turnover):
    s0 = turnover[(5.0, 195)][1]
    allw = np.ones(plants.n, bool)
    expected = {(14, 0): 48.0, (14, 1): 11.0, (14, 2): 3.5, (21, 0): 115.5, (21, 1): 43.1, (21, 2): 16.4}
    for a_days in (14, 21):
        ntr = AB.absence_noise(100, a_days, plants.n, 31, 0.95)[0]
        nte = AB.absence_noise(100, a_days, plants.n, 41, 0.95)[0]
        none_v = AB.absence(plants, 0.4, 195, a_days, s0, allw, nte)["dry"].sum(axis=1).mean()
        assert none_v == pytest.approx(expected[(a_days, 0)], rel=0.06)
        for k in (1, 2):
            best, bv = None, np.inf
            for days in itertools.combinations(range(1, a_days), k):
                v = AB.absence(plants, 0.4, 195, a_days, s0, allw, ntr, visits=days)["dry"].sum(axis=1).mean()
                if v < bv:
                    best, bv = days, v
            even = tuple(int(round(a_days * (j + 1) / (k + 1))) for j in range(k))
            v_best = AB.absence(plants, 0.4, 195, a_days, s0, allw, nte, visits=best)["dry"].sum(axis=1).mean()
            v_even = AB.absence(plants, 0.4, 195, a_days, s0, allw, nte, visits=even)["dry"].sum(axis=1).mean()
            assert abs(v_even - v_best) <= 0.1  # höchstens 0,1 Stress-Tage Unterschied (Summe aller 12 Pflanzen)
            assert v_even == pytest.approx(expected[(a_days, k)], rel=0.08)


# ----------------------------------------------------------------------------------------------------------- Handbeispiel und Orakel-Instanz
def test_handbeispiel_zahlen_der_readme():
    from fractions import Fraction as F

    assert len(H.threshold_days(365)) == 36
    assert H.absence_stress(14) == F(103544, 50625) and float(H.absence_stress(14)) == pytest.approx(2.0453, abs=5e-5)
    assert H.absence_stress(14, reservoir=F(1, 2)) == 0 and H.absence_stress(14, visits=(10,)) == 0
    assert H.rot(F(7, 10), F(1, 2)) == F(2, 5)
    assert H.best_plan_dp(20) == F(3, 10)
