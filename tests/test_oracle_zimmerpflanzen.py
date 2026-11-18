"""Orakel-Tests (ORACLE-PLAYBOOK): unabhängige Rechenwege für den Kern.

(A1) Mini-Instanz in exakten Brüchen: Aufzählung aller Gießpläne gegen Rückwärtsrechnung gegen Schwellenregel gegen die vektorisierte Simulation.
(A2) Instanz mit Jahreszeit (eine Zimmerpflanze, deterministisch, 365 Tage): Rückwärtsrechnung über (Tag, Tag des letzten Gießens) in reinem Python
     gegen die besten Regeln (Takt, Sommer/Winter-Takt, Schwelle) und gegen die Simulation der App mit dem DP-Plan.
(B) Python-Tagesschleife je Pflanze gegen die NumPy-Fassung, gleiche Zufallszahlen.
(C) Urlaub: Tagesschleife gegen die NumPy-Fassung.
"""

import itertools
import math
from fractions import Fraction as F

import numpy as np
import pytest
from conftest import deterministic_run

import zpf_absence as AB
import zpf_algorithm as A
import zpf_hand as H


# ------------------------------------------------------------------------------------------------------------------ (A1)
def test_a1_aufzaehlung_gleich_rueckwaertsrechnung_gleich_schwelle():
    T = 20
    best = None
    for r in range(0, 6):
        for days in itertools.combinations(range(1, T), r):
            l = H.plan_loss(set(days), T)
            if best is None or l < best[0]:
                best = (l, days)
    assert best[0] == F(3, 10) and best[1] == (10,)  # einmal gießen (Kosten 3/10), Tag 10
    assert H.best_plan_dp(T) == best[0]
    assert H.plan_loss(set(H.threshold_days(T)), T) == F(3, 10)
    assert H.plan_loss({10}, T) == F(3, 10)


def test_a1_simulation_der_app_trifft_den_bruch(mini_plants):
    pl = mini_plants
    m = int(np.where(pl.cls == 1)[0][0])

    class Plan:
        def __init__(self, days):
            self.days = set(days)

        def reset(self, S, P):
            pass

        def act(self, d, s, meas):
            return np.full(s.shape, d in self.days), np.zeros(s.shape, bool)

    res = deterministic_run(A, pl, Plan({10}), S=1, days=365)
    sim_loss = float(res["dry"][0, m] + 5 * res["rot"][0, m] + 0.3 * res["nw"][0, m])
    assert sim_loss == pytest.approx(float(H.plan_loss({10}, 365)), abs=1e-12)  # ein Jahr, einmal gießen: Stress der restlichen Tage
    plan_many = set(range(10, 365, 10))
    res = deterministic_run(A, pl, Plan(plan_many), S=1, days=365)
    sim_loss = float(res["dry"][0, m] + 5 * res["rot"][0, m] + 0.3 * res["nw"][0, m])
    assert sim_loss == pytest.approx(float(H.plan_loss(plan_many, 365)), abs=1e-9)


# ------------------------------------------------------------------------------------------------------------------ (A2)
K, SS, SW, OVER, W_ROT, C_W, AMP = 1 / 15, 0.40, 0.15, 0.75, 5.0, 0.3, 0.4


def _fac(d):
    return 1 - AMP * math.cos(2 * math.pi * d / 365)


def _step(s, d):
    rho = min(max((s - SW) / (SS - SW), 0.0), 1.0)
    return max(s - K * _fac(d) * rho, SW)


def _zeta(s):
    return min(max((SS - s) / (SS - SW), 0.0), 1.0)


def _table(n=365):
    tab = [[None] * n for _ in range(n)]
    for last in range(n):
        s = 1.0
        for d in range(last, n):
            tab[last][d] = s
            s = _step(s, d)
    return tab


def _plan_cost(tab, days, n=365):
    last, cost = 0, 0.0
    for d in range(n):
        s = tab[last][d]
        if d in days:
            cost += W_ROT * max((s - OVER) / (1 - OVER), 0.0) + C_W
            last, s = d, 1.0
        cost += _zeta(s)
    return cost


def _dp(tab, n=365):
    V = [[0.0] * n for _ in range(n + 1)]
    choice = [[False] * n for _ in range(n)]
    for d in range(n - 1, -1, -1):
        for last in range(d + 1):
            s = tab[last][d]
            no = _zeta(s) + V[d + 1][last]
            yes = (W_ROT * max((s - OVER) / (1 - OVER), 0.0) + C_W + V[d + 1][d]) if d > 0 else math.inf
            if yes < no:
                V[d][last], choice[d][last] = yes, True
            else:
                V[d][last] = no
    last, days = 0, []
    for d in range(n):
        if choice[d][last]:
            days.append(d)
            last = d
    return V[0][0], days


@pytest.fixture(scope="module")
def seasonal():
    tab = _table()
    opt, days = _dp(tab)
    return tab, opt, days


def test_a2_dp_nachgerechnet_und_regeln_liegen_darueber(seasonal):
    tab, opt, days = seasonal
    assert _plan_cost(tab, set(days)) == pytest.approx(opt, abs=1e-9)  # der DP-Plan, einzeln nachgerechnet
    best_takt = min((_plan_cost(tab, set(range(T, 365, T))), T) for T in range(2, 31))
    best_sw = None
    for tw in range(2, 31):
        for ts in range(2, 31):
            last, dd = 0, set()
            for d in range(1, 365):
                T = tw if (d < 91 or d >= 274) else ts
                if d - last >= T:
                    dd.add(d)
                    last = d
            c = _plan_cost(tab, dd)
            if best_sw is None or c < best_sw[0]:
                best_sw = (c, tw, ts)
    def thr(theta):
        last, dd = 0, set()
        for d in range(1, 365):
            if tab[last][d] < theta:
                dd.add(d)
                last = d
        return dd
    best_th = min((_plan_cost(tab, thr(t)), t) for t in [round(0.1 + 0.01 * i, 2) for i in range(90)])
    assert opt == pytest.approx(11.1197, abs=1e-3) and len(days) == 37
    assert best_takt[0] == pytest.approx(15.076, abs=1e-3) and best_takt[1] == 8
    assert best_sw[0] == pytest.approx(12.994, abs=1e-3) and best_sw[1:] == (11, 7)
    assert best_th[0] == pytest.approx(11.208, abs=1e-3) and best_th[1] == 0.39
    assert opt < best_th[0] < best_sw[0] < best_takt[0]  # alle drei Regeln liegen über der Rückwärtsrechnung, drei verschiedene Werte
    assert sorted(thr(0.39))[:8] == days[:8]  # die Schwelle trifft die ersten acht Gießtage des Optimums


def test_a2_simulation_der_app_mit_dem_dp_plan(seasonal, mini_plants):
    tab, opt, days = seasonal
    pl = mini_plants
    m = int(np.where(pl.cls == 1)[0][0])
    dayset = set(days)

    class Plan:
        def reset(self, S, P):
            pass

        def act(self, d, s, meas):
            return np.full(s.shape, d in dayset), np.zeros(s.shape, bool)

    res = deterministic_run(A, pl, Plan(), amp=AMP, S=1)
    sim = float(res["dry"][0, m] + W_ROT * res["rot"][0, m] + C_W * res["nw"][0, m])
    assert sim == pytest.approx(opt, abs=1e-9)  # die vektorisierte Simulation trifft die Rückwärtsrechnung
    res_t = deterministic_run(A, pl, A.Takt(np.full(pl.n, 8)), amp=AMP, S=1)
    sim_t = float(res_t["dry"][0, m] + W_ROT * res_t["rot"][0, m] + C_W * res_t["nw"][0, m])
    assert sim_t == pytest.approx(_plan_cost(tab, set(range(8, 365, 8))), abs=1e-9)


# ------------------------------------------------------------------------------------------------------------------ (B)
def _loop_year(plants, amp, noise, meas, policy, p, s_idx, sigma=0.0, theta=0.0, T=0, v=1):
    """Eine Pflanze, ein Pfad: Tagesschleife in reinem Python. policy: 'takt' oder 'schwelle'."""
    s, last = 1.0, 0
    out = []
    for d in range(365):
        water = False
        if policy == "takt":
            water = d > 0 and d % T == 0
        else:
            if d > 0 and d % v == 0:
                water = (s + sigma * meas[s_idx, d, p]) < theta
        if water:
            s = 1.0
        out.append(s)
        rate = plants.k[p] * (1 - amp * math.cos(2 * math.pi * d / 365)) * noise[s_idx, d, p]
        rho = min(max((s - plants.sw[p]) / (plants.sstar[p] - plants.sw[p]), 0.0), 1.0)
        s = max(s - rate * rho, plants.sw[p])
    return out


@pytest.mark.parametrize("policy", ["takt", "schwelle"])
def test_b_tagesschleife_gleich_numpy(plants, policy):
    S, amp, ar = 2, 0.4, 0.95
    noise, meas = A.weather(S, 365, plants.n, 21, ar)
    if policy == "takt":
        pol = A.Takt(np.full(plants.n, 9))
        kw = dict(T=9)
    else:
        pol = A.Schwelle(np.full(plants.n, 0.5), 0.15, 3)
        kw = dict(sigma=0.15, theta=0.5, v=3)
    res = A.run(plants, amp, pol, S, 21, ar=ar, record=True)
    for si in range(S):
        for p in range(plants.n):
            loop = _loop_year(plants, amp, noise, meas, policy, p, si, **kw)
            assert np.allclose(res["traj"][si, p], loop, atol=1e-12), (si, p)


# ------------------------------------------------------------------------------------------------------------------ (C)
def test_c_urlaub_tagesschleife_gleich_numpy(plants):
    S, n_days, d0, amp = 3, 21, 195, 0.4
    noise = AB.absence_noise(S, n_days, plants.n, 8, 0.95)[0]
    rng = np.random.default_rng(3)
    s0 = rng.uniform(0.2, 1.0, (S, plants.n))
    water = rng.random(plants.n) < 0.5
    dock = rng.random(plants.n) < 0.5
    shade = rng.random(plants.n) < 0.5
    vec = AB.absence(plants, amp, d0, n_days, s0, water, noise, dock=dock, shade=shade, visits=(7, 14), reservoir=0.5, shade_f=0.5)
    for si in range(S):
        for p in range(plants.n):
            s = 1.0 if water[p] else s0[si, p]
            rot = max((s0[si, p] - plants.over[p]) / (1 - plants.over[p]), 0.0) if (water[p] and plants.over[p] < 1) else 0.0
            dry = welk = 0.0
            res = 0.5 if dock[p] else 0.0
            for t in range(n_days):
                if t in (7, 14):
                    if plants.over[p] < 1:
                        rot += max((s - plants.over[p]) / (1 - plants.over[p]), 0.0)
                    s = 1.0
                z = min(max((plants.sstar[p] - s) / (plants.sstar[p] - plants.sw[p]), 0.0), 1.0)
                dry += z
                welk += z >= 0.5
                rate = plants.k[p] * (1 - amp * math.cos(2 * math.pi * (d0 + t) / 365)) * noise[si, t, p] * (0.5 if shade[p] else 1.0)
                rho = min(max((s - plants.sw[p]) / (plants.sstar[p] - plants.sw[p]), 0.0), 1.0)
                s_new = max(s - rate * rho, plants.sw[p])
                refill = min(s - s_new, res)
                res -= refill
                s = s_new + refill
            assert vec["dry"][si, p] == pytest.approx(dry, abs=1e-10)
            assert vec["welk"][si, p] == welk
            assert vec["rot"][si, p] == pytest.approx(rot, abs=1e-10)
