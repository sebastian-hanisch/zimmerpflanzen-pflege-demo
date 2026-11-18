"""Handbeispiel in exakten Brüchen: eine Zimmerpflanze, keine Streuung, kein Rauschen, keine Jahreszeit.

D = 9 Tage von voll bis Stressbeginn, s* = 0,4, Welkepunkt 0,15, Fäulnisgrenze 0,75, Austrocknung k = 0,6/9 = 1/15 je Tag oberhalb von s*.
Dieselben Regeln wie zpf_algorithm, aber mit `fractions.Fraction`: so lässt sich jede Zahl des Beispiels von Hand nachrechnen (tests/)."""

from fractions import Fraction as F

K = F(1, 15)
SSTAR, SW, OVER = F(2, 5), F(3, 20), F(3, 4)


def rho(s):
    return min(max((s - SW) / (SSTAR - SW), F(0)), F(1))


def zeta(s):
    return min(max((SSTAR - s) / (SSTAR - SW), F(0)), F(1))


def step(s):
    """Ein Tag Austrocknung."""
    return max(s - K * rho(s), SW)


def rot(s, over=OVER):
    """Fäulnisschaden beim Gießen auf Feuchte s (Grenze `over`)."""
    return max((s - over) / (1 - over), F(0)) if over < 1 else F(0)


def trajectory(n_days, water_days=()):
    """Feuchte zu Beginn jedes Tages 0..n_days-1 (nach evtl. Gießen), Stress je Tag und Anzahl Gießvorgänge."""
    s, out, stress, n = F(1), [], [], 0
    for d in range(n_days):
        if d in water_days:
            s = F(1)
            n += 1
        out.append(s)
        stress.append(zeta(s))
        s = step(s)
    return out, stress, n


def threshold_days(n_days, theta=SSTAR):
    """Gießtage der Schwellenregel (tägliche Prüfung, exakt): gießen, wenn die Feuchte unter theta liegt."""
    s, days = F(1), []
    for d in range(n_days):
        if d > 0 and s < theta:
            days.append(d)
            s = F(1)
        s = step(s)
    return days


def absence_stress(n_days, visits=(), reservoir=F(0)):
    """Trockenstress in n_days Tagen Abwesenheit, voll gegossen abgereist; optional Besuche (Tage) und Docht-Vorrat."""
    s, dry, res = F(1), F(0), reservoir
    for t in range(n_days):
        if t in visits:
            s = F(1)
        dry += zeta(s)
        ns = step(s)
        refill = min(s - ns, res)
        res -= refill
        s = ns + refill
    return dry


def plan_loss(water_days, n_days, w_rot=5, c_w=F(3, 10)):
    """Verlust eines Gießplans über n_days Tage (Start s = 1): Stress + w_rot * Fäulnis + c_w * Gießen; Kontrolle gratis."""
    s, dry, rot_sum, n = F(1), F(0), F(0), 0
    for d in range(n_days):
        if d in water_days:
            rot_sum += rot(s)
            s = F(1)
            n += 1
        dry += zeta(s)
        s = step(s)
    return dry + w_rot * rot_sum + c_w * n


def best_plan_dp(n_days, w_rot=5, c_w=F(3, 10)):
    """Exakte Rückwärtsrechnung über (Tag, Feuchte): minimaler Verlust über alle Gießpläne (Gießen ab Tag 1)."""
    from functools import lru_cache

    @lru_cache(None)
    def v(d, s):
        if d == n_days:
            return F(0)
        best = None
        for water in (False, True):
            if water and d == 0:
                continue
            s1, cost = s, F(0)
            if water:
                cost += w_rot * rot(s) + c_w
                s1 = F(1)
            cost += zeta(s1) + v(d + 1, step(s1))
            best = cost if best is None or cost < best else best
        return best

    return v(0, F(1))
