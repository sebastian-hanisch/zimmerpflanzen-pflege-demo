"""Zimmerpflanzen gießen: Kalender oder Messen? - interaktive Fall-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Akt 1: Gießkalender gegen Messen der Bodenfeuchte (verrauscht, mit Kontrollkosten). Akt 2: Urlaub, wann sich Gießen vor der Abreise lohnt.
Alle Pflanzenzahlen sind Annahmen (README, „Ehrliche Grenzen“). Lauffähig mit: streamlit run app.py
"""

from fractions import Fraction

import numpy as np
import streamlit as st

import zpf_absence as AB
import zpf_algorithm as A
import zpf_constants as C
import zpf_evaluation as EV
import zpf_grid as G
import zpf_hand as H
import zpf_plants as PL
import zpf_strategies as ST
import zpf_texts as TX
import zpf_visualization as V
from zpf_layout import dunkles_design, kopf_css
from zpf_pdf_export import build_pdf
from zpf_presets import (
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    randomize_seed,
    sidebar_presets,
    sync_query_params,
)

st.set_page_config(page_title="Zimmerpflanzen gießen – Sebastian Hanisch", layout="wide")

PLANTS = PL.make_plants()
SEASON_NAMES = {C.SEASON_SUMMER: "Hochsommer", C.SEASON_WINTER: "Winter"}


@st.cache_data(show_spinner="Strategien werden abgestimmt und verglichen (Größenordnung 10 bis 30 Sekunden) ...")
def _compare(amp, ar, sigma, cc, cw, wrot, v, paths, seed):
    return ST.compare(PLANTS, amp, ar, (wrot, cw, cc), sigma, v, paths, seed)


@st.cache_data(show_spinner="Urlaub wird gerechnet ...")
def _urlaub(amp, ar, wrot, season, paths, seed, spec):
    pol = ST.make_policy(spec, PLANTS, 0.0)
    d0 = C.ABREISE_TAG[season]
    s0 = AB.departure_state(PLANTS, amp, pol, d0, paths, seed, ar)
    turn, curves = AB.turnover_day(
        PLANTS, amp, d0, s0, lambda a: AB.absence_noise(paths, a, PLANTS.n, seed + 1, ar)[0], wrot,
    )
    return s0, turn, curves


@st.cache_data(show_spinner=False)
def _grid():
    return G.load()


# Fester Kopf: nur der Titel bleibt beim Scrollen oben (Stylesheet in zpf_layout.py).
st.html(kopf_css(dunkles_design()))
with st.container(key="kopf"):
    st.title("🪴 Zimmerpflanzen gießen: Kalender oder Messen?")
st.markdown(
    """
Zwölf Zimmerpflanzen trocknen je nach **Art, Jahreszeit und Wetter** unterschiedlich schnell aus. **Akt 1** fragt: Reicht ein gut abgestimmter **Gießkalender**, oder lohnt es, die **Bodenfeuchte zu messen**, wenn die Messung rauscht und jede Kontrolle etwas kostet? **Akt 2** fragt: Soll man **vor dem Urlaub** noch gießen, und was bringen **Docht, Schatten und ein Nachbar**?

Alle Pflanzenzahlen sind **Annahmen** (Modellrechnung, keine Pflegeempfehlung). Direkt darunter erklärt der Expander **💬 In einfachen Worten** das Ganze ohne Formeln. Weiter unten: die **Kernfragen**, dann die Expander **🔧 Wie wir das erreichen – vollständiger Methodenvergleich**, **📐 Mathematische Formulierung** und **⚠️ Annahmen, Grenzen und bekannte Probleme**.
"""
)

# erklaerseite:einfach:start (erzeugt von tools/set_demo_explainer.py (Website-Repo) aus tools/content/explainers/giess-kalender-erklaert.json, nicht von Hand ändern)
with st.expander("💬 In einfachen Worten"):
    st.markdown(
        """
Zwölf erfundene Zimmerpflanzen trocknen unterschiedlich schnell aus: Kakteen langsam, durstige Arten schnell, im Winter langsamer als im Sommer. Gießt man nach einem **festen Kalender**, oder prüft man die Erde und gießt **nach Messung**? Die Anwendung stellt beide Wege nebeneinander und rechnet für jeden, wie viel Trockenheit und wie viel Fäulnis er verursacht, was das Gießen kostet und was jede Kontrolle an Aufmerksamkeit kostet.

Ein auf jede Pflanze abgestimmter Kalender ist stark. Messen lohnt erst, wenn die Messung genau ist und das Nachschauen wenig kostet; eine grobe Fingerprobe verliert gegen den Kalender. Im zweiten Teil geht es um den Urlaub: Soll man vor der Abreise noch gießen? Das hängt von der Pflanzenart, der Jahreszeit und davon ab, wie schwer Fäulnis wiegt. Docht, Schatten und ein Nachbar helfen. Alle Zahlen der Pflanzen sind Annahmen.

[Ausführlich und verständlich erklärt, mit Fachteil](https://sebastianhanisch.net/giess-kalender-erklaert.html)
        """
    )
# erklaerseite:einfach:end
st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    sidebar_presets()  # Schnellstart oben, das aktive Preset ist hervorgehoben
    st.header("⚙️ Einstellungen")
    st.markdown("**Pflanzen und Wetter**")
    amp = st.slider("Jahreszeit (Amplitude)", *bounds("amp_slider"), key="amp_slider", step=0.05,
                    help="0 = Austrocknung das ganze Jahr gleich schnell; 0,4 = im Winter 40 % langsamer, im Hochsommer 40 % schneller als im Mittel.")
    ar = st.slider("Wetter hängt zusammen (Autokorrelation)", *bounds("ar_slider"), key="ar_slider", step=0.01,
                   help="0 = jeder Tag unabhängig; nahe 1 = warme oder kühle Phasen halten lange an (Heizung, Hitzewelle).")
    st.markdown("**Messen und Kosten**")
    sigma = st.slider("Messrauschen", *bounds("sigma_slider"), key="sigma_slider", step=0.05,
                      help="Streuung der geschätzten Feuchte (Fingerprobe) um den wahren Wert, in Feuchte-Einheiten (0 bis 1).")
    cc = st.slider("Kosten je Kontrolle", *bounds("cc_slider"), key="cc_slider", step=0.005, format="%.3f",
                   help="Aufmerksamkeit für eine Kontrolle, in Tagen vollen Trockenstresses.")
    cw = st.slider("Kosten je Gießen", *bounds("cw_slider"), key="cw_slider", step=0.05,
                   help="Aufwand für einmal Gießen, in Tagen vollen Trockenstresses.")
    wrot = st.slider("Gewicht der Fäulnis", *bounds("wrot_slider"), key="wrot_slider", step=1.0,
                     help="Wie schwer das Gießen auf noch feuchte Erde wiegt (nur Sukkulenten und Zimmerpflanzen haben eine Fäulnisgrenze).")
    v = st.slider("Kontrollabstand der Schwelle (Tage)", *bounds("v_slider"), key="v_slider",
                  help="Wie oft die einfache Schwellenregel die Feuchte prüft.")
    st.markdown("**Urlaub (Akt 2)**")
    a_days = st.slider("Abwesenheit (Tage)", *bounds("a_slider"), key="a_slider")
    season = st.radio("Abreise", [C.SEASON_SUMMER, C.SEASON_WINTER], key="season_radio", format_func=SEASON_NAMES.get, horizontal=True,
                      help="Hochsommer = Tag 195 im Jahr, Winter = Tag 15.")
    dock = st.slider("Docht-Vorrat", *bounds("dock_slider"), key="dock_slider", step=0.25,
                     help="Wie viel Austrocknung der Docht ausgleicht, in Feuchte-Einheiten (Annahme).")
    shade = st.slider("Schatten-Faktor", *bounds("shade_slider"), key="shade_slider", step=0.1,
                      help="Austrocknung im Schatten als Anteil der normalen (Annahme; Lichtmangel nicht modelliert).")
    visits = st.slider("Besuche des Nachbarn", *bounds("visits_slider"), key="visits_slider",
                       help="Der Nachbar gießt alle Pflanzen auf voll, gleichmäßig über die Abwesenheit verteilt.")
    st.markdown("**Rechnung**")
    paths = st.slider("Auswertepfade", *bounds("paths_slider"), key="paths_slider", step=10,
                      help="Wie viele Zufallsjahre (Akt 1) bzw. Urlaube (Akt 2) ausgewertet werden.")
    seed = st.number_input("Zufalls-Seed", *bounds("seed_input"), key="seed_input", step=1)
    st.button("🎲 Neuen Zufalls-Seed würfeln", width="stretch", on_click=randomize_seed)

sync_query_params({
    "amp_slider": float(amp), "ar_slider": float(ar), "sigma_slider": float(sigma), "cc_slider": float(cc), "cw_slider": float(cw),
    "wrot_slider": float(wrot), "v_slider": int(v), "a_slider": int(a_days), "season_radio": int(season), "dock_slider": float(dock),
    "shade_slider": float(shade), "visits_slider": int(visits), "paths_slider": int(paths), "seed_input": int(seed),
})

W = (float(wrot), float(cw), float(cc))
rows = _compare(float(amp), float(ar), float(sigma), float(cc), float(cw), float(wrot), int(v), int(paths), int(seed))
sw_row = next(r for r in rows if r["name"].startswith("Kalender Sommer/Winter"))
s0, turn, curves = _urlaub(float(amp), float(ar), float(wrot), int(season), int(paths), int(seed), sw_row["spec"])

tab_hand, tab1, tab2, tab_limits = st.tabs(["✋ Von Hand", "🔬 Akt 1: Kalender oder Messen?", "🏖️ Akt 2: Urlaub", "⚠️ Grenzen"])

# --- Von Hand ------------------------------------------------------------------------------------------------------------------------------
with tab_hand:
    st.markdown(
        "Eine **Zimmerpflanze** ohne Streuung, ohne Rauschen, ohne Jahreszeit: 9 Tage von voll bis Stressbeginn bei Feuchte 0,4 (Austrocknung 1/15 je Tag), "
        "Welkepunkt 0,15, Fäulnisgrenze 0,75. Alle Zahlen hier sind **exakte Brüche**, jede lässt sich von Hand nachrechnen."
    )
    days_hand = 20
    gdays = H.threshold_days(days_hand)
    traj, stress, n_w = H.trajectory(days_hand, gdays)
    st.plotly_chart(
        V.fig_hand(list(range(days_hand)), [float(x) for x in traj], [float(x) for x in stress], gdays, float(H.SSTAR), float(H.SW), float(H.OVER)),
        width="stretch", key="hand_chart",
    )
    n_year = len(H.threshold_days(365))
    st.markdown(
        f"**Schwellenregel (Feuchte täglich genau messen, gießen unter 0,4):** Am Tag 10 ist die Feuchte 1 − 10/15 = 1/3 und liegt unter 0,4, "
        f"gegossen wird an den Tagen {', '.join(map(str, gdays))} dieses Ausschnitts; im Jahr sind es **{n_year} Gießvorgänge** ohne Trockenstress."
    )
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Urlaub, voll gegossen abgereist**")
        a_hand = st.slider("Abwesenheit (Tage)", 3, 21, 14, key="hand_a")
        use_dock = st.checkbox("Docht mit Vorrat 1/2", key="hand_dock")
        use_visit = st.checkbox("Nachbar gießt am Tag 10", key="hand_visit")
        val = H.absence_stress(a_hand, visits=(10,) if use_visit else (), reservoir=Fraction(1, 2) if use_dock else Fraction(0))
        st.metric("Trockenstress in der Abwesenheit", f"{float(val):.4f}", delta=f"= {val} (exakter Bruch)" if val else "kein Stress", delta_color="off")
    with c2:
        st.markdown("**Fäulnis beim Gießen auf feuchte Erde**")
        st.markdown(
            "Eine Sukkulente (Fäulnisgrenze 1/2) wird bei Feuchte 7/10 gegossen: Schaden = (7/10 − 1/2)/(1 − 1/2) = "
            f"**{H.rot(Fraction(7, 10), Fraction(1, 2))}**. Wäre die Erde schon unter 1/2, wäre der Schaden 0."
        )
        plan = H.best_plan_dp(20)
        st.markdown(
            f"**Gegenprobe:** Die exakte Rückwärtsrechnung über alle Gießpläne der ersten 20 Tage (Fäulnisgewicht 5, Gießen 3/10) ergibt als kleinsten Verlust "
            f"**{float(plan):.1f}**: einmal gießen, am Tag 10 (Schwellenregel und Takt 10 liegen gleich)."
        )

# --- Akt 1 ---------------------------------------------------------------------------------------------------------------------------------
cal_best = min((r for r in rows if r["group"] == "Kalender" and not r["name"].startswith("Wochentakt")), key=lambda r: r["loss"])
meas_best = min((r for r in rows if r["group"] == "Messen"), key=lambda r: r["loss"])
week = next(r for r in rows if r["name"].startswith("Wochentakt"))
lern_cal = next(r for r in rows if r["name"] == "Kalender, Lerner (Probieren)")
lern_meas = next(r for r in rows if r["name"] == "Adaptive Kontrolle, Lerner (Probieren)")

with tab1:
    st.markdown("## 📊 Ergebnis: Verlust je Pflanze und Jahr")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Wochentakt für alle", f"{week['loss']:.1f}", delta="Strohmann", delta_color="off")
    m2.metric("Bester Kalender", f"{cal_best['loss']:.1f}", delta=f"{cal_best['loss'] - week['loss']:+.1f} gegen Wochentakt", delta_color="inverse")
    m3.metric("Beste Messstrategie", f"{meas_best['loss']:.1f}", delta=f"{meas_best['loss'] - cal_best['loss']:+.1f} gegen besten Kalender", delta_color="inverse")
    m4.metric("Lerner (Jahr 3)", f"{min(lern_cal['loss'], lern_meas['loss']):.1f}", delta="durch Probieren", delta_color="off")
    st.caption(
        "Verlust = Trockenstress (Tage) + Gewichte x (Fäulnis, Gießen, Kontrollen). Delta: mein Wert minus Referenz, negativ ist besser. "
        "Abgestimmte Strategien sind auf dem Modell selbst abgestimmt (Quasi-Orakel); die Lerner finden ihre Pflanzenparameter durch Probieren."
    )
    table = [
        {
            "Strategie": r["name"], "Gruppe": r["group"], "Verlust": round(r["loss"], 2), "Trockenstress": round(r["dry"], 2),
            "Fäulnis": round(r["rot"], 2), "Gießen": round(r["nw"], 1), "Kontrollen": round(r["nc"], 1),
            **{k: round(x, 2) for k, x in r["by_class"].items()},
        }
        for r in rows
    ]
    st.dataframe(table, hide_index=True, width="stretch")
    st.plotly_chart(V.fig_strategies(rows, W), width="stretch", key="strat_chart")

    st.markdown("### Ein Jahr einer Pflanze")
    pc1, pc2 = st.columns(2)
    labels = [f"{C.KLASSEN_NAMEN[PLANTS.cls[i]]} {i + 1}" for i in range(PLANTS.n)]
    plant_i = pc1.selectbox("Pflanze", range(PLANTS.n), format_func=lambda i: labels[i], index=4, key="plant_select")
    strat_name = pc2.selectbox("Strategie", [r["name"] for r in rows], index=2, key="strat_select")
    row_sel = next(r for r in rows if r["name"] == strat_name)
    pol = ST.make_policy(row_sel["spec"], PLANTS, float(sigma))
    days_sim = 365 * row_sel["years"]
    rec = A.run(PLANTS, float(amp), pol, 1, int(seed), days=days_sim, ar=float(ar), record=True)
    sl = slice(days_sim - 365, days_sim)
    st.plotly_chart(
        V.fig_year(rec["traj"][0, plant_i, sl], rec["water"][0, plant_i, sl], rec["check"][0, plant_i, sl],
                   float(PLANTS.sstar[plant_i]), float(PLANTS.sw[plant_i]), f"{labels[plant_i]}: {strat_name}" + (" (Jahr 3)" if row_sel["years"] == 3 else "")),
        width="stretch", key="year_chart",
    )
    st.caption("Ein Beispielpfad. Dreiecke: gegossen; graue Punkte: Kontrolle ohne Gießen. Bei den Lernern ist das dritte Jahr gezeigt.")

    st.markdown("### Kreuzungspunkt: wann lohnt Messen? (vorgerechnetes Raster)")
    grid = _grid()
    if grid:
        w_near = min(C.GRID_WROT, key=lambda x: abs(x - float(wrot)))
        st.plotly_chart(V.fig_crossing(grid, w_near, current=(min(C.GRID_CC, key=lambda x: abs(x - float(cc))), min(C.GRID_SIGMA, key=lambda x: abs(x - float(sigma))))),
                        width="stretch", key="cross_chart")
        st.caption(
            f"Beste Messstrategie gegen besten Kalender in Prozent des Kalender-Verlusts (rot: Messen schlechter, blau: Messen besser), "
            f"Fäulnisgewicht {w_near:g} (nächstliegender Wert des Rasters), Jahreszeit 0,4, Wetter 0,95, Gießen 0,3. ◎ markiert die nächstliegende Zelle zu Ihren Reglern."
        )
    else:
        st.info("Das Referenzraster fehlt (data/kreuzung.csv).")

# --- Akt 2 ---------------------------------------------------------------------------------------------------------------------------------
with tab2:
    d0 = C.ABREISE_TAG[int(season)]
    st.markdown(f"## 🏖️ {a_days} Tage weg, Abreise {SEASON_NAMES[int(season)]}")
    st.markdown("### Vor der Abreise gießen? Verlust über die Dauer der Abwesenheit")
    st.plotly_chart(V.fig_turnover(curves, turn), width="stretch", key="turn_chart")
    for name in C.KLASSEN_NAMEN:
        st.markdown("- " + EV.umschlag_text(name, turn[name]))
    st.caption(
        f"Verlust = Trockenstress + {wrot:g} x Fäulnis je Pflanze; Abreisezustand = Feuchte am Abreisetag unter dem abgestimmten Sommer/Winter-Kalender; "
        f"{paths} Urlaube. Im Winter hängt der Umschlagpunkt stark am Fäulnisgewicht, im Hochsommer kaum."
    )
    noise = AB.absence_noise(int(paths), int(a_days), PLANTS.n, int(seed) + 1, float(ar))[0]
    P = PLANTS.n
    allw, nonew = np.ones(P, bool), np.zeros(P, bool)
    base = AB.absence(PLANTS, float(amp), d0, int(a_days), s0, allw, noise)
    skip = AB.absence(PLANTS, float(amp), d0, int(a_days), s0, nonew, noise)
    base_loss = AB.class_means(PLANTS, base["dry"] + float(wrot) * base["rot"])
    skip_loss = AB.class_means(PLANTS, skip["dry"] + float(wrot) * skip["rot"])
    st.markdown(f"### Bei {a_days} Tagen: alle gießen gegen keine gießen")
    st.dataframe(
        [{"Klasse": k, "alle gießen": round(base_loss[k], 2), "keine gießen": round(skip_loss[k], 2),
          "besser": "gießen" if base_loss[k] < skip_loss[k] else "nicht gießen"} for k in list(C.KLASSEN_NAMEN) + ["Alle"]],
        hide_index=True, width="stretch",
    )
    st.markdown("### Hilfen (alle vor der Abreise gegossen)")
    allm = np.ones(P, bool)
    k_vis = int(visits)
    vis_days = tuple(int(round(a_days * (j + 1) / (k_vis + 1))) for j in range(k_vis))
    variants = {
        "Docht": AB.absence(PLANTS, float(amp), d0, int(a_days), s0, allw, noise, dock=allm, reservoir=float(dock)),
        "Schatten": AB.absence(PLANTS, float(amp), d0, int(a_days), s0, allw, noise, shade=allm, shade_f=float(shade)),
        "Docht + Schatten": AB.absence(PLANTS, float(amp), d0, int(a_days), s0, allw, noise, dock=allm, shade=allm, reservoir=float(dock), shade_f=float(shade)),
    }
    if k_vis:
        variants[f"Nachbar ({k_vis}x, Tage {', '.join(map(str, vis_days))})"] = AB.absence(PLANTS, float(amp), d0, int(a_days), s0, allw, noise, visits=vis_days)
    aids = {name: AB.class_means(PLANTS, base["dry"] - r["dry"]) for name, r in variants.items()}
    aids = {name: {k: x for k, x in vals.items() if k != "Alle"} for name, vals in aids.items()}
    st.plotly_chart(V.fig_aids(aids), width="stretch", key="aids_chart")
    st.caption(
        f"Nutzen = Trockenstress-Tage ohne Hilfe minus mit Hilfe, je Pflanze. Ohne Hilfe im Mittel {base['dry'].mean():.2f} Stress-Tage. "
        f"Docht-Vorrat {dock:g}, Schatten-Faktor {shade:g} (Annahmen). Gleichmäßig verteilte Nachbarbesuche liegen höchstens 0,1 Stress-Tage (Summe aller Pflanzen) hinter dem besten Plan (Aufzählung aller Besuchstage bei 14 und 21 Tagen, bis zu zwei Besuche)."
    )

# --- Grenzen -------------------------------------------------------------------------------------------------------------------------------
with tab_limits:
    st.markdown(TX.ASSUMPTIONS_MARKDOWN)

# --- Kernfragen ----------------------------------------------------------------------------------------------------------------------------
st.markdown("## ❓ Kernfragen")
st.markdown("**Akt 1: Lohnt Messen bei diesen Kosten?**")
kind, text = EV.kreuz_verdikt(meas_best["loss"], cal_best["loss"], meas_best["name"], cal_best["name"])
getattr(st, kind)(text)
kind2, text2 = EV.lerner_verdikt(lern_cal["loss"], lern_meas["loss"])
getattr(st, kind2)(text2)
st.markdown("**Akt 2: Ab wie vielen Tagen lohnt Gießen vor der Abreise?**")
st.info(" ".join(EV.umschlag_text(n, turn[n]) for n in C.KLASSEN_NAMEN))

pdf_bytes = build_pdf(
    {"Jahreszeit": amp, "Wetter": ar, "Rauschen": sigma, "Kontrolle": cc, "Gießen": cw, "Fäulnis": wrot, "Kontrollabstand": v, "Seed": seed, "Pfade": paths},
    rows, W, turn, int(a_days), SEASON_NAMES[int(season)],
)
st.download_button("📄 Ergebnis als PDF", data=pdf_bytes, file_name="zimmerpflanzen-pflege.pdf", mime="application/pdf", key="pdf_download")

st.markdown("---")

# --- Expander ------------------------------------------------------------------------------------------------------------------------------
with st.expander("🔧 Wie wir das erreichen – vollständiger Methodenvergleich"):
    st.markdown(TX.METHODS_MARKDOWN)

with st.expander("📐 Mathematische Formulierung"):
    # erklaerseite:lesehilfe:start (erzeugt von tools/set_demo_explainer.py (Website-Repo) aus tools/content/explainers/giess-kalender-erklaert.json, nicht von Hand ändern)
    st.markdown(
        r"""
**Lesehilfe.** Gegeben sind zwölf Pflanzen mit je einer Trockenzeit, einem Stressbeginn, einem Welkepunkt und einer Fäulnisgrenze, ein Jahreszeit- und Wetterfaktor sowie Kosten für Gießen und Kontrolle. Gesucht sind Gießzeitpunkte, die den Verlust je Pflanze und Jahr klein halten, wenn die Bodenfeuchte nur verrauscht gemessen werden kann.

| Symbol | Bedeutung |
|---|---|
| $s_t$ | relative Bodenfeuchte zu Beginn von Tag $t$ (1 = frisch gegossen) |
| $s_w$, $s^*$ | Welkepunkt, Stressbeginn (Feuchte, ab der die Pflanze leidet) |
| $g$ | Fäulnisgrenze (1 = keine) |
| $k$ | Austrocknung je Tag oberhalb des Stressbeginns, $k=(1-s^*)/D$ mit $D$ Tagen von voll bis Stressbeginn |
| $\alpha$ | Amplitude der Jahreszeit |
| $\varepsilon_t,\eta_t$ | Wetterfaktor aller Pflanzen (zusammenhängend) und Faktor je Pflanze, beide mit Mittel 1 |
| $W$ | Menge der Gießtage |
| $\sigma$, $z_t$ | Messrauschen und Standardnormalzahl |
| $w_{\mathrm{rot}}$, $c_w$, $c_c$ | Gewichte für Fäulnis, Gießen, Kontrolle |

[Schritt für Schritt erklärt, mit Herleitung und Literatur](https://sebastianhanisch.net/giess-kalender-erklaert.html#fachleute)
        """
    )
    # erklaerseite:lesehilfe:end
    st.markdown(
        r"""
$$
\rho(s)=\operatorname{clip}\!\left(\frac{s-s_w}{s^*-s_w},0,1\right)
$$
"""
    )
    st.markdown(
        r"""
$$
s_{t+1}=\max\!\Big(s_t-r_t\,\rho(s_t),\;s_w\Big),\qquad r_t=k\Big(1-\alpha\cos\frac{2\pi t}{365}\Big)\,\varepsilon_t\,\eta_t
$$
"""
    )
    st.markdown(
        r"""
$$
\zeta(s)=\operatorname{clip}\!\left(\frac{s^*-s}{s^*-s_w},0,1\right),\qquad q(s)=\operatorname{clip}\!\left(\frac{s-g}{1-g},0,1\right)\ \text{(nur für }g<1\text{)}
$$
"""
    )
    st.markdown(
        r"""
$$
L=\sum_{t}\zeta(s_t)+w_{\mathrm{rot}}\sum_{t\in W}q(s_t)+c_w\,|W|+c_c\,N_{\mathrm{Kontrollen}},\qquad \hat s_t=s_t+\sigma z_t
$$
"""
    )
    st.markdown(TX.MATH_NOTE)

with st.expander("⚠️ Annahmen, Grenzen und bekannte Probleme"):
    st.markdown(TX.ASSUMPTIONS_MARKDOWN)

st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zu den Demos: [Interaktive Demos](https://sebastianhanisch.net/demos.html)."
)
