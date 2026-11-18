"""Texte, die App und README gemeinsam führen (ein Test vergleicht beide Fassungen)."""

ASSUMPTIONS_MARKDOWN = """
- **Alle Zahlen der Pflanzen sind Annahmen:** Tage von voll bis Stressbeginn (Median je Klasse 21, 9 und 5, logarithmisch normale Streuung 0,25 je Pflanze; die zwölf gezogenen Pflanzen haben im Mittel 20,0 / 8,6 / 6,1), Stressbeginn, Welkepunkt, Fäulnisgrenze, Wetter- und Jahreszeitfaktor. Für Zimmerpflanzen fand eine Websuche am 18. November 2026 keine begutachtete Quelle (nur Gartenblogs, deren Aussagen die Demo nicht als Beleg nutzt). Die Demo zeigt, was bei diesen Annahmen passiert, nicht wie sich eine bestimmte Pflanze verhält.
- **Literatur nur als Größenordnung (nur Abstracts gelesen):** Nackley u. a. 2020 (HortScience): Weihnachtssterne in 11-Liter-Töpfen im Gewächshaus zeigten beim wöchentlichen Gießen keinen Wasserstress, bis der Substratwassergehalt 0,3 m³/m³ erreichte. Van Iersel u. a. 2010 (HortScience 45(2)): Gießschwellen von 0,05 bis 0,40 m³/m³ bei Petunien; dass Wasser unter 0,20 m³/m³ als nicht verfügbar gilt, ist dort eine übernommene Allgemeinaussage. Gewächshaus, große Töpfe, andere Kulturen; die relative Feuchte der Demo (0 bis 1) ist nicht auf m³/m³ abgebildet.
- **Die abgestimmten Strategien sind ein Quasi-Orakel:** Kalender, Schwelle und adaptive Kontrolle bekommen ihren Parameter je Pflanze auf getrennten Trainingspfaden desselben Modells. Wer seinen Rhythmus nur probiert, steht gegen den abgestimmten Kalender und die abgestimmte adaptive Kontrolle schlechter; deshalb zeigt die Tabelle auch die beiden Lerner (Probieren über drei Jahre, ausgewiesen wird Jahr 3, die Lernkosten der ersten Jahre sind nicht enthalten). Auch die Lerner sind nicht frei vom Modell: ihre Lernregel (Schrittweite, Schwelle der Fingerprobe) ist auf Trainingspfaden abgestimmt, die Startwerte kommen aus der Pflanzenklasse.
- **Fäulnis nur als Ereignis** beim Gießen auf noch feuchte Erde, nicht als Dauer der Nässe. Eine Gegenprobe mit Nässedauer in der Vormessung änderte die Rangfolge der Strategien nicht, verschob aber einzelne Umschlagpunkte (zum Beispiel den der Sukkulenten im Winter) und verkleinerte den Abstand des Wochentakts; sie ist in der App nicht nachrechenbar.
- **Nicht modelliert:** Tod der Pflanze (Stress wird nur gezählt), Wechselwirkung zwischen Pflanzen (außer dem gemeinsamen Wetter), Gießmenge als Entscheidung (gegossen wird immer auf voll), Lichtmangel im Schatten (Schatten ist daher zu günstig), Umtopfen, Standortwechsel, Schädlinge.
- **Docht und Schatten:** Vorrat und Faktor sind Annahmen; die Nutzen verschieben sich mit ihnen.
- **Keine Pflegeempfehlung** für eine bestimmte Pflanze. Die Regeln sind Rechenverfahren im Modell.
"""

MATH_HELP = """
**Lesehilfe.** Gegeben: zwölf Pflanzen mit je einer Trockenzeit, einem Stressbeginn, einem Welkepunkt und einer Fäulnisgrenze, ein Jahreszeit- und Wetterfaktor, Kosten für Gießen und Kontrolle. Gesucht: Gießzeitpunkte, die den Verlust je Pflanze und Jahr klein halten, wenn die Bodenfeuchte nur verrauscht gemessen werden kann.

| Symbol | Bedeutung |
|---|---|
| $s_t$ | relative Bodenfeuchte zu Beginn von Tag $t$ (1 = frisch gegossen) |
| $s_w$, $s^*$ | Welkepunkt, Stressbeginn (Feuchte, ab der die Pflanze leidet) |
| $g$ | Fäulnisgrenze (1 = keine) |
| $k$ | Austrocknung je Tag oberhalb des Stressbeginns, $k=(1-s^*)/D$ mit $D$ Tagen von voll bis Stressbeginn |
| $\\alpha$ | Amplitude der Jahreszeit |
| $\\varepsilon_t,\\eta_t$ | Wetterfaktor aller Pflanzen (zusammenhängend) und Faktor je Pflanze, beide mit Mittel 1 |
| $W$ | Menge der Gießtage |
| $\\sigma$, $z_t$ | Messrauschen und Standardnormalzahl |
| $w_{\\mathrm{rot}}$, $c_w$, $c_c$ | Gewichte für Fäulnis, Gießen, Kontrolle |
"""

MATH_BLOCKS = (
    r"\rho(s)=\operatorname{clip}\!\left(\frac{s-s_w}{s^*-s_w},0,1\right)",
    r"s_{t+1}=\max\!\Big(s_t-r_t\,\rho(s_t),\;s_w\Big),\qquad r_t=k\Big(1-\alpha\cos\frac{2\pi t}{365}\Big)\,\varepsilon_t\,\eta_t",
    r"\zeta(s)=\operatorname{clip}\!\left(\frac{s^*-s}{s^*-s_w},0,1\right),\qquad q(s)=\operatorname{clip}\!\left(\frac{s-g}{1-g},0,1\right)\ \text{(nur für }g<1\text{)}",
    r"L=\sum_{t}\zeta(s_t)+w_{\mathrm{rot}}\sum_{t\in W}q(s_t)+c_w\,|W|+c_c\,N_{\mathrm{Kontrollen}},\qquad \hat s_t=s_t+\sigma z_t",
)

MATH_NOTE = (
    "Gießen setzt $s_t=1$ (die Feuchte nach dem Gießen ist immer voll). Start: Tag $t=0$ ist der 1. Januar, alle Pflanzen beginnen mit $s_0=1$; Ablauf eines Tages und Zufallsprozess stehen im Abschnitt „Modell“ der README "
    "(Wertebereiche: $s_t\\in[s_w,1]$, $t=0,\\dots,364$); $\\varepsilon_t$ ist logarithmisch normal mit Streuung 0,25 und Autokorrelation "
    "(Regler), $\\eta_t$ logarithmisch normal mit Streuung 0,15. Die Strategien wählen $W$ und die Kontrolltage; sie sind keine "
    "Optimierung im Sinne eines gelösten Programms, sondern Regeln mit abgestimmten Parametern."
)

METHODS_MARKDOWN = """
| Strategie | Regel | Parameter |
|---|---|---|
| Wochentakt für alle | alle Pflanzen alle 7 Tage gießen | keiner (Strohmann: Art und Jahreszeit bleiben unberücksichtigt) |
| Kalender je Pflanze | alle $T$ Tage gießen | $T$ je Pflanze auf Trainingspfaden abgestimmt |
| Kalender Sommer/Winter | Abstand $T_w$ im Winter (Tag < 91 oder ≥ 274), $T_s$ im Sommer | beide je Pflanze abgestimmt |
| Schwelle | alle $v$ Tage Feuchte schätzen, gießen wenn der Schätzwert unter $\\theta$ liegt | $\\theta$ je Pflanze abgestimmt, $v$ Regler |
| Adaptive Kontrolle | nächste Kontrolle nach $\\lfloor f\\,(\\hat s-\\theta)/\\hat k\\rfloor$ Tagen (1 bis 7), Rate $\\hat k$ aus dem Abfall seit dem Gießen, Entscheidung auf Mischung aus Messung und Modellwert | $\\theta$ je Pflanze abgestimmt, $f$ = 0,5 oder 0,75 |
| Kalender, Lerner | Abstand $T$ startet bei der Trockenzeit der Klasse; nach Welke $-\\delta$ Tage, sonst bei feuchter Fingerprobe beim Gießen $+\\delta$ | $\\delta$ und Schwelle der Fingerprobe gemeinsam für alle Pflanzen auf Trainingspfaden |
| Adaptive Kontrolle, Lerner | wie adaptiv, aber $\\theta$ je Pflanze durch Probieren: nach gesehener Welke $+a$, sonst $-b$ | $a$, $b$ gemeinsam abgestimmt |

Die Ein-Jahres-Strategien laufen auf denselben Zufallspfaden (Wetter und Messrauschen), die beiden Lerner (Jahr 3 eines Dreijahreslaufs) auf eigenen Pfaden desselben Zufalls-Seeds; die Auswertepfade sind von den Trainingspfaden getrennt.
Die Lerner laufen drei Jahre; die Tabelle zeigt Jahr 3.
"""
