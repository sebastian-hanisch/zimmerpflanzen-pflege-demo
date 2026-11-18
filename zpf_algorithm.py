"""Kern: Austrocknung der Zimmerpflanzen, Strategien (Kalender, Schwelle, adaptive Kontrolle, Lerner), Abstimmung.

Modell (alle Zahlen Annahmen, siehe zpf_constants): relative Bodenfeuchte s zwischen Welkepunkt s_w und 1 (= frisch gegossen).
Austrocknung je Tag: rate * rho(s), rho(s) = clip((s - s_w)/(s* - s_w), 0, 1): oberhalb des Stressbeginns s* linear, darunter langsamer,
am Welkepunkt Stillstand (lineare Vereinfachung in Anlehnung an Porporato, Laio, Ridolfi, Rodriguez-Iturbe 2001; nur Abstract gelesen).
Trockenstress je Tag zeta = clip((s* - s)/(s* - s_w), 0, 1). Gießen setzt s auf 1. Fäulnisschaden nur beim Gießen auf noch feuchte
Erde: (s - Grenze)/(1 - Grenze), wenn die Pflanze eine Grenze hat. Verlust = Trockenstress + w_rot * Fäulnis + c_w * Gießen + c_c * Kontrolle.
"""

import numpy as np

import zpf_constants as C


# ------------------------------------------------------------------ Grundregeln (je Einheit von Hand nachgerechnet, tests/)
def rho(s, sstar, sw):
    """Anteil der vollen Austrocknungsrate bei Feuchte s."""
    return np.clip((s - sw) / (sstar - sw), 0, 1)


def zeta(s, sstar, sw):
    """Trockenstress eines Tages, 0 bis 1."""
    return np.clip((sstar - s) / (sstar - sw), 0, 1)


def rot_damage(s, over):
    """Fäulnisschaden beim Gießen auf Erde der Feuchte s; 0 ohne Fäulnisgrenze (over = 1)."""
    return np.where(over < 1.0, np.clip((s - over) / (1 - over + 1e-12), 0, 1), 0.0)


def dry_step(s, rate, sstar, sw):
    """Ein Tag Austrocknung (nie unter dem Welkepunkt)."""
    return np.maximum(s - rate * rho(s, sstar, sw), sw)


def season_factor(day, amp):
    """Jahreszeit: Winter (Tag 0) langsamer, Hochsommer schneller: 1 - amp * cos(2 pi day / 365)."""
    return 1 - amp * np.cos(2 * np.pi * day / 365)


def loss_from(dry, rot, nw, nc, w):
    """w = (Fäulnisgewicht, Kosten je Gießen, Kosten je Kontrolle)."""
    return dry + w[0] * rot + w[1] * nw + w[2] * nc


# ------------------------------------------------------------------ Strategien
class Takt:
    """Fester Gießabstand je Pflanze, keine Kontrolle."""

    def __init__(self, T):
        self.T = np.asarray(T, dtype=float)

    def reset(self, S, P):
        pass

    def act(self, d, s, meas):
        w = np.broadcast_to((d > 0) & (d % self.T[None, :] == 0), s.shape)
        return w, np.zeros(s.shape, bool)


class TaktSaison:
    """Zwei feste Abstände: Winter (Tag < 91 oder >= 274 im Jahr) und Sommer."""

    def __init__(self, T_w, T_s):
        self.T_w = np.asarray(T_w, dtype=float)
        self.T_s = np.asarray(T_s, dtype=float)

    def reset(self, S, P):
        self.last = np.zeros((S, P))

    def act(self, d, s, meas):
        dd = d % 365
        T = self.T_w if (dd < 91 or dd >= 274) else self.T_s
        w = (d > 0) & ((d - self.last) >= T[None, :])
        self.last = np.where(w, d, self.last)
        return w, np.zeros(s.shape, bool)


class Schwelle:
    """Alle v Tage die Feuchte prüfen (verrauscht, sd = sigma), gießen wenn der Schätzwert unter theta liegt."""

    def __init__(self, theta, sigma, v):
        self.theta = np.asarray(theta, dtype=float)
        self.sigma, self.v = sigma, v

    def reset(self, S, P):
        pass

    def act(self, d, s, meas):
        if d % self.v != 0 or d == 0:
            z = np.zeros(s.shape, bool)
            return z, z
        s_hat = s + self.sigma * meas
        chk = np.ones(s.shape, bool)
        return chk & (s_hat < self.theta[None, :]), chk


class Adaptiv:
    """Nächste Kontrolle aus geschätzter Trockenrate: floor(f * (s_eff - theta)/k_hat) Tage, 1 bis vmax.
    Rate k_hat aus dem gesamten Abfall seit dem letzten Gießen (Anker s = 1 ist bekannt); Entscheidung auf einer
    Mischung (mix) aus Messung und Modellwert."""

    def __init__(self, theta, sigma, f, vmax, k_prior, lam=0.5, mix=0.5):
        self.theta = np.asarray(theta, dtype=float)
        self.sigma, self.f, self.vmax = sigma, f, vmax
        self.k_prior = np.asarray(k_prior, dtype=float)
        self.lam, self.mix = lam, mix

    def reset(self, S, P):
        self.next = np.ones((S, P))
        self.t_w = np.zeros((S, P))
        self.k_cycle = np.broadcast_to(self.k_prior, (S, P)).copy()
        self.th = self.theta[None, :] if self.theta.ndim == 1 else self.theta

    def act(self, d, s, meas):
        chk = d >= self.next
        s_hat = s + self.sigma * meas
        slope = np.maximum((1 - s_hat) / np.maximum(d - self.t_w, 1), 1e-3)
        k_use = self.lam * slope + (1 - self.lam) * self.k_cycle
        s_dec = (1 - self.mix) * s_hat + self.mix * (1 - k_use * (d - self.t_w))
        water = chk & (s_dec < self.th)
        self.k_cycle = np.where(water, k_use, self.k_cycle)
        s_eff = np.where(water, 1.0, s_dec)
        self.t_w = np.where(water, d, self.t_w)
        gap = np.floor(self.f * (s_eff - self.th) / k_use)
        self.next = np.where(chk, d + np.clip(gap, 1, self.vmax), self.next)
        return water, chk


class Lerner:
    """Kalender durch Probieren: Abstand T je Pflanze startet bei T0 und wird nach jedem Gießen angepasst.
    Welke gesehen (Stress >= 0,5 seit dem letzten Gießen): T - delta; sonst Fingerprobe beim Gießen (verrauscht, eine Kontrolle):
    Schätzwert > s* + margin: T + delta."""

    def __init__(self, plants, T0, delta, margin, sigma):
        self.pl = plants
        self.T0, self.delta, self.margin, self.sigma = np.asarray(T0, dtype=float), delta, margin, sigma

    def reset(self, S, P):
        self.T = np.broadcast_to(self.T0, (S, P)).copy()
        self.last = np.zeros((S, P))
        self.wilt = np.zeros((S, P), bool)

    def act(self, d, s, meas):
        pl = self.pl
        self.wilt |= zeta(s, pl.sstar, pl.sw) >= 0.5
        due = (d > 0) & ((d - self.last) >= np.round(self.T))
        s_hat = s + self.sigma * meas
        down = due & self.wilt
        up = due & ~self.wilt & (s_hat > pl.sstar + self.margin)
        self.T = np.where(down, np.maximum(self.T - self.delta, 1.0), np.where(up, np.minimum(self.T + self.delta, 60.0), self.T))
        self.last = np.where(due, d, self.last)
        self.wilt = np.where(due, False, self.wilt)
        return due, due.copy()


class LernAdaptiv:
    """Adaptive Kontrolle mit gelerntem Schwellenwert (Treppenverfahren): nach jedem Gießen theta + a bei gesehener Welke, sonst theta - b."""

    def __init__(self, plants, theta0, a, b, sigma, f=0.5, vmax=7, mix=0.5, lam=0.5):
        self.pl = plants
        self.theta0, self.a, self.b, self.sigma = np.asarray(theta0, float), a, b, sigma
        self.f, self.vmax, self.mix, self.lam = f, vmax, mix, lam

    def reset(self, S, P):
        self.theta = np.broadcast_to(self.theta0, (S, P)).copy()
        self.wilt = np.zeros((S, P), bool)
        self.next = np.ones((S, P))
        self.t_w = np.zeros((S, P))
        self.k_cycle = np.broadcast_to(self.pl.k_prior, (S, P)).copy()

    def act(self, d, s, meas):
        pl = self.pl
        self.wilt |= zeta(s, pl.sstar, pl.sw) >= 0.5
        s_hat = s + self.sigma * meas
        chk = d >= self.next
        slope = np.maximum((1 - s_hat) / np.maximum(d - self.t_w, 1), 1e-3)
        k_use = self.lam * slope + (1 - self.lam) * self.k_cycle
        s_dec = (1 - self.mix) * s_hat + self.mix * (1 - k_use * (d - self.t_w))
        water = chk & (s_dec < self.theta)
        self.k_cycle = np.where(water, k_use, self.k_cycle)
        s_eff = np.where(water, 1.0, s_dec)
        self.t_w = np.where(water, d, self.t_w)
        gap = np.floor(self.f * (s_eff - self.theta) / k_use)
        self.next = np.where(chk, d + np.clip(gap, 1, self.vmax), self.next)
        up, down = water & self.wilt, water & ~self.wilt
        self.theta = np.clip(np.where(up, self.theta + self.a, np.where(down, self.theta - self.b, self.theta)), 0.1, 1.3)
        self.wilt = np.where(water, False, self.wilt)
        return water, chk


# ------------------------------------------------------------------ Simulation
def weather(S, days, P, seed, ar, common_sd=C.COMMON_SD, indiv_sd=C.INDIV_SD):
    """Zufallsfaktoren der Austrocknung (S, days, P) und Messrauschen N(0,1) (S, days, P). Gleiche Pfade für alle Strategien."""
    rng = np.random.default_rng(seed)
    common = np.exp(rng.normal(-0.5 * common_sd**2, common_sd, (S, days, 1))) if common_sd > 0 else np.ones((S, days, 1))
    indiv = np.exp(rng.normal(-0.5 * indiv_sd**2, indiv_sd, (S, days, P))) if indiv_sd > 0 else np.ones((S, days, P))
    meas = rng.normal(0, 1, (S, days, P))
    if ar > 0 and common_sd > 0:
        x = np.zeros((S, days, 1))
        eps = rng.normal(0, common_sd * np.sqrt(1 - ar**2), (S, days, 1))
        x[:, 0] = rng.normal(0, common_sd, (S, 1))
        for t in range(1, days):
            x[:, t] = ar * x[:, t - 1] + eps[:, t]
        common = np.exp(x - 0.5 * common_sd**2)
    return common * indiv, meas


def run(plants, amp, pol, S, seed0, days=C.DAYS, ar=C.DEFAULT_AR, common_sd=C.COMMON_SD, indiv_sd=C.INDIV_SD, record=False):
    """Simuliert S Pfade zu `days` Tagen. Rückgabe: Mittel je Jahr von Stress, Fäulnis, Gießen, Kontrollen (S, P);
    mit record=True zusätzlich die Feuchte-Verläufe (S, P, days) und die Gieß-/Kontrolltage (bool)."""
    P = plants.n
    noise, meas = weather(S, days, P, seed0, ar, common_sd, indiv_sd)
    s = np.ones((S, P))
    ny = max(1, days // 365)
    dry_y, rot_y, nw_y, nc_y = (np.zeros((S, P, ny)) for _ in range(4))
    if record:
        traj = np.zeros((S, P, days))
        wat = np.zeros((S, P, days), bool)
        chk_rec = np.zeros((S, P, days), bool)
    pol.reset(S, P)
    over = plants.over[None, :]
    for d in range(days):
        yr = min(d // 365, ny - 1)
        water, check = pol.act(d, s, meas[:, d, :])
        rot_y[:, :, yr] += np.where(water, rot_damage(s, over), 0.0)
        s = np.where(water, 1.0, s)
        nw_y[:, :, yr] += water
        nc_y[:, :, yr] += check
        dry_y[:, :, yr] += zeta(s, plants.sstar, plants.sw)
        if record:
            traj[:, :, d] = s
            wat[:, :, d] = water
            chk_rec[:, :, d] = check
        rate = plants.k * season_factor(d, amp) * noise[:, d, :]
        s = dry_step(s, rate, plants.sstar, plants.sw)
    res = dict(dry=dry_y.mean(2), rot=rot_y.mean(2), nw=nw_y.mean(2), nc=nc_y.mean(2), dry_y=dry_y, rot_y=rot_y, nw_y=nw_y, nc_y=nc_y)
    if record:
        res.update(traj=traj, water=wat, check=chk_rec)
    return res


def loss(res, w):
    return loss_from(res["dry"], res["rot"], res["nw"], res["nc"], w)


def tune(plants, amp, w, make, grid, S=C.TRAIN_PATHS, seed0=C.TRAIN_SEED, **kw):
    """Je Pflanze den Parameter mit dem kleinsten mittleren Verlust auf den Trainingspfaden wählen (Gleichstand: erster)."""
    best = np.full(plants.n, np.inf)
    arg = [None] * plants.n
    for g in grid:
        res = run(plants, amp, make(g, plants.n), S, seed0, **kw)
        l = loss(res, w).mean(axis=0)
        for i in range(plants.n):
            if l[i] < best[i] - 1e-12:
                best[i] = l[i]
                arg[i] = g
    return arg


def tune_pooled(plants, amp, w, make, grid, years_for_loss=2, S=30, seed0=C.TRAIN_SEED, **kw):
    """Ein Parameter für alle Pflanzen (Lerner): kleinster mittlerer Verlust der ersten `years_for_loss` Jahre (Lernkosten eingeschlossen)."""
    best, arg = np.inf, None
    for g in grid:
        res = run(plants, amp, make(g), S, seed0, **kw)
        ly = loss_from(res["dry_y"], res["rot_y"], res["nw_y"], res["nc_y"], w).mean(axis=(0, 1))
        v = ly[:years_for_loss].mean()
        if v < best:
            best, arg = v, g
    return arg
