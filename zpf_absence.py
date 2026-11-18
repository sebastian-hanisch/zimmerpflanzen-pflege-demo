"""Urlaub: A Tage ohne Gießen (Docht, Schatten, Nachbarbesuche), Abreisezustand unter dem abgestimmten Kalender.

Annahmen (nicht belegt): Docht-Vorrat in Feuchte-Einheiten gleicht den Tagesverlust aus, bis er leer ist; Schatten multipliziert die
Austrocknung mit einem Faktor (Lichtmangel nicht modelliert); der Nachbar gießt alle Pflanzen auf voll."""

import numpy as np

import zpf_algorithm as A
import zpf_constants as C


class Snap:
    """Hüllt eine Strategie und merkt sich die Feuchte zu Beginn des Abreisetags."""

    def __init__(self, pol, d0):
        self.pol, self.d0 = pol, d0

    def reset(self, S, P):
        self.pol.reset(S, P)

    def act(self, d, s, meas):
        if d == self.d0:
            self.s0 = s.copy()
        return self.pol.act(d, s, meas)


def departure_state(plants, amp, pol, d0, S, seed0, ar):
    """Bodenfeuchte aller Pflanzen am Abreisetag d0 unter der Strategie `pol` (Rückgabe (S, P))."""
    snap = Snap(pol, d0)
    A.run(plants, amp, snap, S, seed0, ar=ar)
    return snap.s0


def absence(plants, amp, d0, n_days, s0, water, noise, dock=None, shade=None, visits=(), reservoir=0.5, shade_f=0.5):
    """Verlauf über n_days Tage ab Tag d0 im Jahr. s0: Feuchte bei Abreise (S, P); water: vor der Abreise gießen (bool je Pflanze oder (S, P));
    noise: Zufallsfaktoren (S, n_days, P); visits: Tage (ab 0), an denen der Nachbar alle Pflanzen auf voll gießt.
    Rückgabe: Stress, Welk-Tage (Stress >= 0,5), Fäulnis je (S, P)."""
    S, P = s0.shape
    over = plants.over[None, :]
    water = np.broadcast_to(water, (S, P))
    rot = np.where(water, A.rot_damage(s0, over), 0.0)
    s = np.where(water, 1.0, s0)
    dry = np.zeros((S, P))
    welk = np.zeros((S, P))
    dockm = np.zeros(P, bool) if dock is None else np.asarray(dock, bool)
    shadem = np.zeros(P, bool) if shade is None else np.asarray(shade, bool)
    res = np.where(dockm, reservoir, 0.0)[None, :] * np.ones((S, 1))
    for t in range(n_days):
        if t in visits:
            rot += A.rot_damage(s, over)
            s = np.ones_like(s)
        z = A.zeta(s, plants.sstar, plants.sw)
        dry += z
        welk += z >= 0.5
        rate = plants.k * A.season_factor(d0 + t, amp) * noise[:, t, :] * np.where(shadem, shade_f, 1.0)
        s_new = A.dry_step(s, rate, plants.sstar, plants.sw)
        refill = np.minimum(s - s_new, res)
        res = res - refill
        s = s_new + refill
    return dict(dry=dry, welk=welk, rot=rot)


def absence_noise(S, n_days, P, seed, ar, common_sd=C.COMMON_SD, indiv_sd=C.INDIV_SD):
    noise, meas = A.weather(S, n_days, P, seed, ar, common_sd, indiv_sd)
    return noise, meas


def class_means(plants, arr):
    out = {name: float(arr[:, plants.cls == i].mean()) for i, name in enumerate(C.KLASSEN_NAMEN)}
    out["Alle"] = float(arr.mean())
    return out


def turnover_day(plants, amp, d0, s0, noise_for, w_rot, a_grid=C.A_GRID):
    """Umschlagpunkt je Klasse: kleinste Abwesenheit A in a_grid, ab der „alle gießen" besser ist als „keine gießen"
    (Verlust = Stress + w_rot * Fäulnis, Klassenmittel). Rückgabe {Klasse: A* | 'immer' | 'nie'} und die Kurven {Klasse: [(A, alle, keine)]}.
    noise_for(A) liefert die Zufallsfaktoren für n_days = A."""
    P = plants.n
    allw, none = np.ones(P, bool), np.zeros(P, bool)
    curves = {name: [] for name in C.KLASSEN_NAMEN}
    for a in a_grid:
        noise = noise_for(a)
        ra = absence(plants, amp, d0, a, s0, allw, noise)
        rk = absence(plants, amp, d0, a, s0, none, noise)
        la = class_means(plants, ra["dry"] + w_rot * ra["rot"])
        lk = class_means(plants, rk["dry"] + w_rot * rk["rot"])
        for name in C.KLASSEN_NAMEN:
            curves[name].append((a, la[name], lk[name]))
    result = {}
    for name, rows in curves.items():
        better = [la < lk for _, la, lk in rows]
        if better[0]:
            result[name] = "immer"
        elif not any(better):
            result[name] = "nie"
        else:
            result[name] = rows[better.index(True)][0]
    return result, curves
