"""Plotly-Figuren (alle Achsen fest, kein Zoomen: Touch-Scrollen bleibt nicht am Diagramm hängen)."""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import zpf_constants as C


def _fixed(fig, height=380):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=40, b=10), legend=dict(orientation="h", y=-0.2))
    return fig


def fig_hand(days, s_values, stress, water_days, sstar, sw, over):
    """Handbeispiel: Feuchte über die Tage mit Stressbeginn, Welkepunkt, Fäulnisgrenze und Gießtagen (alle Werte als float)."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=days, y=s_values, mode="lines+markers", name="Feuchte zu Beginn des Tages", line=dict(color=C.COLOR_LINE)))
    for y, label, col in ((sstar, "Stressbeginn s*", C.COLOR_BAD), (sw, "Welkepunkt", "gray"), (over, "Fäulnisgrenze", C.COLOR_MEASURE)):
        fig.add_hline(y=y, line_dash="dot", line_color=col, annotation_text=label, annotation_position="top left")
    if water_days:
        fig.add_trace(go.Scatter(
            x=list(water_days), y=[1.0] * len(water_days), mode="markers", name="gegossen",
            marker=dict(symbol="triangle-down", size=12, color=C.COLOR_CALENDAR),
        ))
    fig.update_yaxes(range=[0, 1.1], title="relative Bodenfeuchte")
    fig.update_xaxes(title="Tag")
    return _fixed(fig, 330)


def fig_year(traj, water, check, sstar, sw, title):
    """Ein Jahr einer Pflanze: Feuchte, Gießtage (Dreiecke), Kontrolltage (kleine Punkte unten)."""
    days = np.arange(len(traj))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=days, y=traj, mode="lines", name="Feuchte", line=dict(color=C.COLOR_LINE, width=1.5)))
    wd = days[water]
    fig.add_trace(go.Scatter(x=wd, y=np.ones(len(wd)), mode="markers", name="gegossen",
                             marker=dict(symbol="triangle-down", size=7, color=C.COLOR_CALENDAR)))
    cd = days[check & ~water]
    if len(cd):
        fig.add_trace(go.Scatter(x=cd, y=np.full(len(cd), 0.03), mode="markers", name="kontrolliert",
                                 marker=dict(size=3, color="gray")))
    fig.add_hline(y=sstar, line_dash="dot", line_color=C.COLOR_BAD, annotation_text="Stressbeginn", annotation_position="top left")
    fig.add_hline(y=sw, line_dash="dot", line_color="gray", annotation_text="Welkepunkt", annotation_position="bottom left")
    fig.update_yaxes(range=[0, 1.1], title="relative Bodenfeuchte")
    fig.update_xaxes(title="Tag im Jahr")
    fig.update_layout(title=title)
    return _fixed(fig, 340)


def fig_strategies(rows, w):
    """Verlust je Strategie, zerlegt in Trockenstress, Fäulnis, Gießen, Kontrolle (gewichtet)."""
    names = [r["name"] for r in rows]
    fig = go.Figure()
    parts = (
        ("Trockenstress", [r["dry"] for r in rows], C.COLOR_LINE),
        ("Fäulnis (gewichtet)", [w[0] * r["rot"] for r in rows], C.COLOR_BAD),
        ("Gießen (gewichtet)", [w[1] * r["nw"] for r in rows], C.COLOR_CALENDAR),
        ("Kontrolle (gewichtet)", [w[2] * r["nc"] for r in rows], C.COLOR_MEASURE),
    )
    for label, vals, col in parts:
        fig.add_trace(go.Bar(y=names, x=vals, name=label, orientation="h", marker_color=col))
    fig.update_layout(barmode="stack", yaxis=dict(autorange="reversed"))
    fig.update_xaxes(title="Verlust je Pflanze und Jahr")
    return _fixed(fig, 120 + 38 * len(rows))


def fig_crossing(grid, w_rot, current=None):
    """Heatmap des Kreuzungspunkts: Abstand der besten Messstrategie zum besten Kalender in % (negativ = Messen besser)."""
    rows = [r for r in grid if abs(r["w_rot"] - w_rot) < 1e-9]
    ccs = sorted({r["cc"] for r in rows})
    sigmas = sorted({r["sigma"] for r in rows})
    z = [[next(r["rel_pct"] for r in rows if r["cc"] == c and r["sigma"] == s) for c in ccs] for s in sigmas]
    text = [[f"{v:+.0f} %" for v in row] for row in z]
    lim = 30.0
    fig = go.Figure(go.Heatmap(
        z=z, x=[f"{c:g}" for c in ccs], y=[f"{s:g}" for s in sigmas], text=text, texttemplate="%{text}",
        colorscale="RdBu", zmin=-lim, zmax=lim, zmid=0, colorbar=dict(title="Messen gegen<br>Kalender (%)"),
        hovertemplate="Kontrollkosten %{x}, Rauschen %{y}: %{text}<extra></extra>",
    ))
    if current and current[0] in ccs and current[1] in sigmas:
        # auf Kategorieachsen zählen Positionen (0, 1, ...), nicht die Beschriftungen: Text wie "0.02" würde als Zahl gelesen und die Marke verrutschen
        fig.add_annotation(x=ccs.index(current[0]), y=sigmas.index(current[1]), text="◎", showarrow=False, font=dict(size=26, color="black"))
    fig.update_xaxes(title="Kosten je Kontrolle", type="category")
    fig.update_yaxes(title="Messrauschen", type="category")
    return _fixed(fig, 330)


def fig_turnover(curves, turn):
    """Verlust bei „alle gießen" gegen „keine gießen" über die Abwesenheit, je Klasse."""
    names = list(curves)
    fig = make_subplots(rows=1, cols=len(names), subplot_titles=names, shared_yaxes=False)
    for i, name in enumerate(names, start=1):
        a = [r[0] for r in curves[name]]
        fig.add_trace(go.Scatter(x=a, y=[r[1] for r in curves[name]], name="alle gießen", mode="lines",
                                 line=dict(color=C.COLOR_CALENDAR), showlegend=i == 1, legendgroup="a"), row=1, col=i)
        fig.add_trace(go.Scatter(x=a, y=[r[2] for r in curves[name]], name="keine gießen", mode="lines",
                                 line=dict(color=C.COLOR_BAD, dash="dash"), showlegend=i == 1, legendgroup="k"), row=1, col=i)
        if isinstance(turn.get(name), (int, float)):
            fig.add_vline(x=turn[name], line_dash="dot", line_color="gray", row=1, col=i)
        fig.update_xaxes(title="Tage Abwesenheit", row=1, col=i, fixedrange=True)
        fig.update_yaxes(fixedrange=True, row=1, col=i)
    fig.update_yaxes(title="Verlust je Pflanze", row=1, col=1)
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=50, b=10), legend=dict(orientation="h", y=-0.25))
    return fig


def fig_aids(aids):
    """Nutzen von Docht, Schatten und beidem je Klasse. aids: {Hilfe: {Klasse: Nutzen}}."""
    fig = go.Figure()
    for name, vals in aids.items():
        fig.add_trace(go.Bar(x=list(vals), y=list(vals.values()), name=name))
    fig.update_layout(barmode="group")
    fig.update_yaxes(title="Stress-Tage weniger je Pflanze")
    return _fixed(fig, 320)
