"""Strategien abstimmen und auf denselben Zufallspfaden vergleichen (Tabelle in Akt 1, Referenzraster).

Abgestimmte Strategien (Kalender, Schwelle, adaptive Kontrolle) bekommen ihren Parameter je Pflanze auf getrennten Trainingspfaden
und sind damit ein Quasi-Orakel: sie sind auf dem Modell selbst abgestimmt. Die Lerner finden ihre Parameter durch Probieren (drei Jahre,
ausgewiesen wird Jahr 3, Lernkosten also nicht enthalten)."""

import numpy as np

import zpf_algorithm as A
import zpf_constants as C
import zpf_plants as PL

TH_GRID = tuple(float(x) for x in np.round(np.arange(0.15, 0.96, 0.05), 2))
PAIR_GRID = tuple((a, b) for a in range(2, 31, 2) for b in range(2, 31, 2))
LERNER_GRID = tuple((d, m) for d in (1, 2, 3) for m in (0.05, 0.15, 0.30))
LERNADAPTIV_GRID = tuple((a, b) for a in (0.03, 0.06, 0.10) for b in (0.01, 0.02, 0.04))
T_GRID = tuple(range(1, 36))
LEARN_DAYS = 3 * 365


def make_policy(spec, plants, sigma):
    kind = spec["kind"]
    if kind == "takt":
        return A.Takt(spec["T"])
    if kind == "takt_saison":
        return A.TaktSaison(spec["T_w"], spec["T_s"])
    if kind == "schwelle":
        return A.Schwelle(spec["theta"], sigma, spec["v"])
    if kind == "adaptiv":
        return A.Adaptiv(spec["theta"], sigma, spec["f"], 7, plants.k_prior)
    if kind == "lerner":
        T0 = [round(C.KLASSEN[c][2]) for c in plants.cls]
        return A.Lerner(plants, T0, spec["delta"], spec["margin"], sigma)
    if kind == "lernadaptiv":
        return A.LernAdaptiv(plants, plants.sstar + 0.10, spec["a"], spec["b"], sigma)
    raise ValueError(kind)


def _row(name, group, plants, res, w, year=None):
    if year is None:
        dry, rot, nw, nc = res["dry"], res["rot"], res["nw"], res["nc"]
    else:
        dry, rot, nw, nc = (res[k][:, :, year] for k in ("dry_y", "rot_y", "nw_y", "nc_y"))
    l = A.loss_from(dry, rot, nw, nc, w)
    by_class = {n: float(l[:, plants.cls == i].mean()) for i, n in enumerate(C.KLASSEN_NAMEN)}
    return dict(
        name=name, group=group, loss=float(l.mean()), dry=float(dry.mean()), rot=float(rot.mean()),
        nw=float(nw.mean()), nc=float(nc.mean()), by_class=by_class,
    )


def tuned_specs(plants, amp, ar, w, sigma, v, S=C.TRAIN_PATHS, include_lerner=True):
    """Alle Strategien abstimmen. Rückgabe: Liste (Name, Gruppe, Spezifikation, Jahre) in fester Reihenfolge."""
    out = [("Wochentakt für alle (7 Tage)", "Kalender", dict(kind="takt", T=[7.0] * plants.n), 1)]
    Ts = A.tune(plants, amp, w, lambda g, n: A.Takt(np.full(n, g)), T_GRID, S=S, ar=ar)
    out.append(("Kalender je Pflanze (ein Abstand, abgestimmt)", "Kalender", dict(kind="takt", T=[float(t) for t in Ts]), 1))
    pairs = A.tune(plants, amp, w, lambda g, n: A.TaktSaison(np.full(n, g[0]), np.full(n, g[1])), PAIR_GRID, S=S, ar=ar)
    out.append((
        "Kalender Sommer/Winter je Pflanze (abgestimmt)", "Kalender",
        dict(kind="takt_saison", T_w=[float(p[0]) for p in pairs], T_s=[float(p[1]) for p in pairs]), 1,
    ))
    th = A.tune(plants, amp, w, lambda g, n: A.Schwelle(np.full(n, g), sigma, v), TH_GRID, S=S, ar=ar)
    out.append((f"Schwelle, alle {v} Tage prüfen (abgestimmt)", "Messen", dict(kind="schwelle", theta=list(th), v=v), 1))
    for f in (0.5, 0.75):
        th = A.tune(
            plants, amp, w, lambda g, n, f=f: A.Adaptiv(np.full(n, g), sigma, f, 7, plants.k_prior), TH_GRID, S=S, ar=ar,
        )
        out.append((f"Adaptive Kontrolle f = {f} (abgestimmt)", "Messen", dict(kind="adaptiv", theta=list(th), f=f), 1))
    if include_lerner:
        T0 = [round(C.KLASSEN[c][2]) for c in plants.cls]
        d, m = A.tune_pooled(
            plants, amp, w, lambda g: A.Lerner(plants, T0, g[0], g[1], sigma), LERNER_GRID, days=LEARN_DAYS, ar=ar,
        )
        out.append(("Kalender, Lerner (Probieren)", "Lerner", dict(kind="lerner", delta=d, margin=m), 3))
        a, b = A.tune_pooled(
            plants, amp, w, lambda g: A.LernAdaptiv(plants, plants.sstar + 0.10, g[0], g[1], sigma), LERNADAPTIV_GRID,
            days=LEARN_DAYS, ar=ar,
        )
        out.append(("Adaptive Kontrolle, Lerner (Probieren)", "Lerner", dict(kind="lernadaptiv", a=a, b=b), 3))
    return out


def compare(plants, amp, ar, w, sigma, v, S_eval, seed_eval, include_lerner=True):
    """Tabelle der Strategien. Rückgabe: Liste von Zeilen (dict) mit `spec` für spätere Verläufe."""
    rows = []
    for name, group, spec, years in tuned_specs(plants, amp, ar, w, sigma, v, include_lerner=include_lerner):
        pol = make_policy(spec, plants, sigma)
        if years == 1:
            res = A.run(plants, amp, pol, S_eval, seed_eval, ar=ar)
            row = _row(name, group, plants, res, w)
        else:
            res = A.run(plants, amp, pol, S_eval, seed_eval, days=LEARN_DAYS, ar=ar)
            row = _row(name, group, plants, res, w, year=2)
        row["spec"] = spec
        row["years"] = years
        rows.append(row)
    return rows


def best_of(rows, group, exclude=()):
    cand = [r for r in rows if r["group"] == group and r["name"] not in exclude]
    return min(cand, key=lambda r: r["loss"]) if cand else None
