"""Referenzraster „Kreuzungspunkt": beste Messstrategie gegen den besten Kalender über Kontrollkosten x Messrauschen je Fäulnisgewicht.

Vorgerechnet (python zpf_grid.py), weil ein Raster aus 60 Zellen mit je rund 90 Abstimmläufen live zu lange dauert (Größenordnung Minuten).
Feste Annahmen des Rasters: Jahreszeit 0,4, Wetter-Autokorrelation 0,95, Kosten je Gießen 0,3, 100 Auswertejahre (Zufalls-Seed 1000),
Abstimmung auf 30 Trainingsjahren (Zufalls-Seed 1). Verlust je Pflanze und Jahr; Kalender = abgestimmter Sommer/Winter-Kalender
(unabhängig von Kontrollkosten und Rauschen), Messen = beste von Schwelle (alle 1, 3, 7 Tage) und adaptiver Kontrolle (f = 0,5; 0,75)."""

import csv
import os

import numpy as np

import zpf_algorithm as A
import zpf_constants as C
import zpf_plants as PL
import zpf_strategies as ST

GRID_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "kreuzung.csv")
FIELDS = ("w_rot", "cc", "sigma", "cal_loss", "measure_loss", "measure", "rel_pct")
AMP, AR, CW = 0.4, 0.95, C.DEFAULT_CW
S_TRAIN, S_EVAL, SEED_EVAL = 30, 100, 1000


def calendar_loss(plants, w_rot):
    w = (w_rot, CW, 0.0)
    pairs = A.tune(
        plants, AMP, w, lambda g, n: A.TaktSaison(np.full(n, g[0]), np.full(n, g[1])), ST.PAIR_GRID, S=S_TRAIN, ar=AR,
    )
    pol = A.TaktSaison([p[0] for p in pairs], [p[1] for p in pairs])
    res = A.run(plants, AMP, pol, S_EVAL, SEED_EVAL, ar=AR)
    return float(A.loss(res, w).mean())


def measure_loss(plants, w_rot, cc, sigma):
    """Beste Messstrategie (Name, Verlust) in dieser Zelle."""
    w = (w_rot, CW, cc)
    best = (None, np.inf)
    for v in (1, 3, 7):
        th = A.tune(plants, AMP, w, lambda g, n, v=v: A.Schwelle(np.full(n, g), sigma, v), ST.TH_GRID, S=S_TRAIN, ar=AR)
        res = A.run(plants, AMP, A.Schwelle(th, sigma, v), S_EVAL, SEED_EVAL, ar=AR)
        l = float(A.loss(res, w).mean())
        if l < best[1]:
            best = (f"Schwelle alle {v} Tage", l)
    for f in (0.5, 0.75):
        th = A.tune(
            plants, AMP, w, lambda g, n, f=f: A.Adaptiv(np.full(n, g), sigma, f, 7, plants.k_prior), ST.TH_GRID, S=S_TRAIN, ar=AR,
        )
        res = A.run(plants, AMP, A.Adaptiv(th, sigma, f, 7, plants.k_prior), S_EVAL, SEED_EVAL, ar=AR)
        l = float(A.loss(res, w).mean())
        if l < best[1]:
            best = (f"Adaptive Kontrolle f = {f}", l)
    return best


def build(path=GRID_PATH, verbose=True):
    plants = PL.make_plants()
    rows = []
    for w_rot in C.GRID_WROT:
        cal = calendar_loss(plants, w_rot)
        for cc in C.GRID_CC:
            for sigma in C.GRID_SIGMA:
                name, l = measure_loss(plants, w_rot, cc, sigma)
                rows.append(
                    dict(w_rot=w_rot, cc=cc, sigma=sigma, cal_loss=round(cal, 4), measure_loss=round(l, 4), measure=name,
                         rel_pct=round(100 * (l - cal) / cal, 3))
                )
                if verbose:
                    print(rows[-1], flush=True)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=FIELDS)
        wr.writeheader()
        wr.writerows(rows)
    return rows


def load(path=GRID_PATH):
    """Raster als Liste von dicts (Zahlen als float); leere Liste, wenn die Datei fehlt."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8", newline="") as fh:
        out = []
        for r in csv.DictReader(fh):
            out.append(
                dict(w_rot=float(r["w_rot"]), cc=float(r["cc"]), sigma=float(r["sigma"]), cal_loss=float(r["cal_loss"]),
                     measure_loss=float(r["measure_loss"]), measure=r["measure"], rel_pct=float(r["rel_pct"]))
            )
        return out


def cell(grid, w_rot, cc, sigma):
    """Zelle des Rasters, die den Reglerwerten am nächsten liegt (Fäulnisgewicht, Kontrollkosten, Rauschen); None bei leerem Raster."""
    if not grid:
        return None
    def dist(r):
        return (abs(r["w_rot"] - w_rot) / 20.0) * 3 + abs(r["cc"] - cc) / 0.1 + abs(r["sigma"] - sigma) / 0.3
    return min(grid, key=dist)


if __name__ == "__main__":
    build()
