# Zimmerpflanzen gießen: Kalender oder Messen? – Streamlit-Demo

<!-- TODO nach dem Deploy: direkt hierher den Live-Link setzen (Leerzeile davor und danach):
**[→ Demo live ausprobieren](https://sebastianhanisch-zimmerpflanzen-pflege-demo.streamlit.app/)** -->

Fall-Demo für die Website „Sebastian Hanisch – Operations Research und Machine Learning“ (`demos.html`). Zwölf Zimmerpflanzen in drei Klassen (4 Sukkulenten, 5 Zimmerpflanzen, 3 durstige) trocknen je nach Art, Jahreszeit und Wetter unterschiedlich schnell aus. **Akt 1** vergleicht Gießkalender (je Pflanze abgestimmt, mit Sommer- und Winterabstand) mit Strategien, die die Bodenfeuchte messen (Schwelle, adaptive Kontrolle), wenn die Messung rauscht und jede Kontrolle etwas kostet; dazu zwei Lerner, die ihre Parameter durch Probieren finden statt durch Abstimmung. **Akt 2** fragt, ob man vor einem Urlaub noch gießen soll, und was Docht, Schatten und Nachbarbesuche bringen. Ein Tab „Von Hand“ rechnet eine Pflanze in exakten Brüchen.

Alle Pflanzenzahlen sind **Annahmen**: für Zimmerpflanzen fand eine Websuche am 18. November 2026 keine begutachtete Quelle. Die Demo zeigt, was bei diesen Annahmen passiert, nicht wie sich eine bestimmte Pflanze verhält, und gibt keine Pflegeempfehlung.

## Warum dieses Problem

Oft hört man „nach Gefühl statt nach Plan gießen“ (Fingerprobe statt Kalender). Ob das im Modell der Demo stimmt, hängt an vier Dingen, die sich messen lassen: wie genau die Messung ist, was eine Kontrolle kostet, wie schwer Fäulnis wiegt und wie stark sich die Austrocknung mit Jahreszeit und Wetter ändert. **Kernfrage:** Lohnt Messen gegenüber einem gut abgestimmten Kalender, und wann kippt das?

## Modell

Relative Bodenfeuchte *s* zwischen Welkepunkt und 1 (frisch gegossen). Austrocknung je Tag `rate · rho(s)`: oberhalb des Stressbeginns *s\** voll, darunter linear langsamer, am Welkepunkt Stillstand (lineare Vereinfachung in Anlehnung an Porporato, Laio, Ridolfi und Rodriguez-Iturbe 2001, Teil III der Reihe „Plants in water-controlled ecosystems“, Advances in Water Resources 24; nur das Abstract gelesen, das Beginn und Maximum des Stresses nennt, die lineare Form ist eine eigene Annahme). Die Rate hängt an Art, Jahreszeit (Amplitude als Regler) und zwei Zufallsfaktoren (Wetter aller Pflanzen mit Autokorrelation, Faktor je Pflanze). Trockenstress je Tag aus *s*, Fäulnisschaden nur beim Gießen auf noch feuchte Erde. Verlust je Pflanze und Jahr = Trockenstress (Tage) + Gewichte mal (Fäulnis, Gießen, Kontrollen). Gießen setzt immer auf voll. Alle Formeln stehen im 📐-Expander der App (Formeln, Ablauf und Zufallsfaktoren im Abschnitt „Modell“). Kern: `zpf_algorithm.py`, Urlaub: `zpf_absence.py`.

**Klassen der Pflanzen (Annahmen, `zpf_constants.KLASSEN`):** Sukkulenten (4 Pflanzen): Median der Trockenzeit 21 Tage, Stressbeginn 0,25, Welkepunkt 0,10, Fäulnisgrenze 0,50. Zimmerpflanzen (5): 9 Tage, 0,40, 0,15, 0,75. Durstige (3): 5 Tage, 0,55, 0,25, keine Fäulnisgrenze. Streuung der Trockenzeit je Pflanze logarithmisch normal mit Streuung 0,25. Zufallsfaktoren der Austrocknung (logarithmisch normal): Wetter aller Pflanzen mit Streuung 0,25 und der Autokorrelation des Reglers, Faktor je Pflanze und Tag mit Streuung 0,15.

**Ablauf eines Tages und Anfangswerte (Annahmen):** Tag 0 ist der 1. Januar (Jahreszeitfaktor 1 − Amplitude, die langsamste Austrocknung des Jahres), alle Pflanzen starten frisch gegossen (Feuchte 1). Jeder Tag läuft so ab: (1) Die Strategie entscheidet auf Grundlage der Feuchte zu Tagesbeginn; eine Kontrolle liefert den Schätzwert Feuchte plus Messrauschen mal Standardnormalzahl, ohne Beschneiden. (2) Beim Gießen entsteht der Fäulnisschaden aus der Feuchte vor dem Gießen, danach ist die Feuchte 1. (3) Der Trockenstress des Tages wird aus der Feuchte nach dem Gießen gezählt. (4) Die Feuchte trocknet aus: neue Feuchte = größerer Wert aus (Feuchte − Rate · rho, Welkepunkt). Die Rate ist k · (1 − Amplitude · cos(2π · Tag / 365)) · Wetterfaktor · Pflanzenfaktor, mit k = (1 − Stressbeginn) / Trockenzeit der Pflanze. Beide Zufallsfaktoren haben den Mittelwert 1: Das Wetter ist im Logarithmus ein AR(1)-Prozess (Koeffizient = Autokorrelation des Reglers, Standard 0,95; Streuung im Gleichgewicht 0,25), der Faktor je Pflanze ist an jedem Tag unabhängig (Streuung 0,15). Welke heißt Trockenstress von mindestens 0,5 an einem Tag. Die Strategien sind in `zpf_algorithm.py` und `zpf_strategies.py` festgelegt, die Zahlen dazu im Folgenden.

**Strategien im Einzelnen (Annahmen):** Die adaptive Kontrolle schätzt die Trockenrate als Mischung zu je 0,5 aus der Neigung seit dem Gießen und der Rate des letzten Zyklus (am Anfang der Wert der Klasse), entscheidet auf einer Mischung zu je 0,5 aus Messung und Modellwert, wählt den nächsten Kontrollabstand zwischen 1 und 7 Tagen und nutzt den Faktor *f* = 0,5 oder 0,75. Der Kalender-Lerner startet beim gerundeten Klassenwert der Trockenzeit, ändert den Abstand um *δ* aus {1, 2, 3} Tagen (zwischen 1 und 60 Tagen) und gilt eine Fingerprobe als „feucht“, wenn der Schätzwert über Stressbeginn plus *m* mit *m* aus {0,05; 0,15; 0,30} liegt; *δ* und *m* sind für alle Pflanzen gemeinsam abgestimmt. Der adaptive Lerner startet mit der Schwelle Stressbeginn plus 0,10 und ändert sie um *a* aus {0,03; 0,06; 0,10} bei gesehener Welke oder um *b* aus {0,01; 0,02; 0,04} sonst.

**Urlaub (Annahmen):** Abreise am Tag 195 (Sommer) oder am Tag 15 (Winter); der Zustand bei der Abreise stammt aus dem abgestimmten Kalender je Pflanze. Verglichen werden „vor der Abreise alle gießen“ und „keine gießen“. Der Docht hat einen Vorrat in Feuchte-Einheiten (Standard 0,5, Regler bis 1,5), der den Tagesverlust ausgleicht, bis er leer ist; der Schatten multipliziert die Austrocknung mit einem Faktor (Standard 0,5, Regler von 0,3 bis 1,0); der Nachbar gießt an den gewählten Tagen (0 bis 3 Besuche) alle Pflanzen auf voll, auch das kann Fäulnis auslösen.

## Methodik

Die Ein-Jahres-Strategien laufen auf **denselben Zufallspfaden** (Wetter und Messrauschen), die beiden Lerner (Jahr 3 eines Dreijahreslaufs) auf eigenen Pfaden desselben Zufalls-Seeds; die Auswertepfade sind von den Trainingspfaden der Abstimmung getrennt. Wochentakt für alle (Strohmann), Kalender je Pflanze (ein Abstand, abgestimmt), Kalender Sommer/Winter (zwei Abstände je Pflanze, abgestimmt; Winter heißt Tag vor 91 oder ab 274 des Jahres), Schwelle (alle *v* Tage verrauscht messen), adaptive Kontrolle (nächste Kontrolle aus der geschätzten Trockenrate, Entscheidung auf Mischung aus Messung und Modellwert), Kalender-Lerner und adaptiver Lerner (Parameter durch Probieren über drei Jahre, ausgewiesen wird Jahr 3). **Die abgestimmten Strategien sind ein Quasi-Orakel**: ihr Parameter je Pflanze ist auf Trainingspfaden desselben Modells abgestimmt; die Lerner finden die Pflanzenparameter durch Probieren, ihre Lernregel und die Startwerte (aus der Pflanzenklasse) sind aber auf dem Modell abgestimmt bzw. bekannt. Das vorgerechnete Raster „Kreuzungspunkt“ (`data/kreuzung.csv`, `python zpf_grid.py`) vergleicht in 60 Zellen (Kontrollkosten, Messrauschen, Fäulnisgewicht) die beste Messstrategie mit dem besten Kalender. Der Urlaub vergleicht „alle gießen“ mit „keine gießen“ über die Abwesenheit (Umschlagpunkt) und misst Docht, Schatten und Nachbarbesuche.

## Befunde (gemessen, keine Behauptungen)

Verlust je Pflanze und Jahr in Tagen vollen Trockenstresses. Standardfall: Jahreszeit 0,4, Wetter 0,95, Messrauschen 0,15, Gewichte 5 / 0,3 / 0,02 (Fäulnis, Gießen, Kontrolle), 100 Auswertejahre (Regler „Auswertepfade“, die App startet mit 40), Zufalls-Seed 1000. Die Zahlen der Tabelle werden in `tests/test_claims.py` und `tests/test_oracle_zimmerpflanzen.py` nachgerechnet (neu gerechnet als Band, das Raster exakt gelesen). Die Werte sind Mittel über die Auswertepfade ohne Standardfehler; Abstände von wenigen Prozent können im Zufall liegen. Das vorgerechnete Raster hat feste Parameter: Jahreszeit 0,4, Wetter 0,95, Gießen 0,3, 100 Auswertejahre, Zufalls-Seed 1000.

| Frage | Befund |
|---|---|
| Wochentakt für alle gegen den besten Kalender | 67,9 gegen 19,1 (rund 3,5-mal so viel); Sukkulenten allein 132 |
| Was bringt die Jahreszeit im Kalender? | ein Abstand je Pflanze 23,6, Sommer/Winter-Abstände 19,1 (−19 %) |
| Messen gegen den besten Kalender (Rauschen 0,15, Kontrolle 0,02) | adaptive Kontrolle 18,3 (rund −4 %), einfache Schwelle alle 3 Tage 21,2 (+11 %); gilt bei Wetter-Autokorrelation 0,95, bei unabhängigem Wetter (0) liegt der beste Kalender vorn |
| Lernend gegen lernend (Jahr 3 eines Dreijahreslaufs, eigene Zufallspfade) | Kalender durch Probieren 22,7 (+19 % über dem abgestimmten Kalender); adaptive Kontrolle durch Probieren 20,2 (−11 % gegen den Kalender-Lerner) |
| Raster: exakter Sensor (Rauschen 0), Fäulnisgewicht 5 | Messen gegen besten Kalender: −39 % bei kostenloser Kontrolle, −21 % bei 0,02, +2 % bei 0,05, +35 % bei 0,10 |
| Raster: grobe Fingerprobe (Rauschen 0,3) | Messen ist in allen 15 Zellen schlechter, mindestens +15 % |
| Raster: Rauschen 0,2, Kontrolle gratis | −9 % (Fäulnisgewicht 1), −12 % (5), −16 % (20) |
| Raster: genauer Sensor, Kontrolle 0,05 | +9 % (Fäulnisgewicht 1), +2 % (5), −10 % (20) |
| Umschlagpunkt Sukkulenten (Gießen vor der Abreise lohnt ab so vielen Tagen), Fäulnisgewicht 1 / 5 / 20 | Hochsommer 10 / 10 / 10; Winter 12 / 18 / 27 (je nach Plattform und Pfadzahl ±1 Tag, Gleichstände der Abstimmung) |
| Umschlagpunkt Zimmerpflanzen, Fäulnisgewicht 1 / 5 / 20 | Hochsommer immer / immer / 9; Winter 7 / 12 / nie (bis 35 Tage); durstige Pflanzen: immer gießen (immer = schon ab 3 Tagen, dem kleinsten gerechneten Wert; Durstige haben keine Fäulnisgrenze) |
| Docht (Vorrat 0,5), Hochsommer, Nutzen je Pflanze in Stress-Tagen | 7 Tage Abwesenheit: Durstige 0,95, Zimmerpflanzen 0,31, Sukkulenten 0,00; 28 Tage: Sukkulenten 6,5, Zimmerpflanzen 5,4, Durstige 5,0 |
| Schatten (Faktor 0,5) gegen Docht, 28 Tage Hochsommer | im Mittel 8,2 gegen 5,6 Stress-Tage weniger (ohne Hilfe 16,5); gilt bei diesen Annahmen, die Reihenfolge hängt an Vorrat und Faktor |
| Nachbarbesuche, Hochsommer, Summe der Stress-Tage aller 12 Pflanzen | 14 Tage: 48,0 ohne Besuch, 11,0 mit einem, 3,5 mit zwei; 21 Tage: 115,5, 43,1, 16,4. Gleichmäßig verteilte Besuchstage liegen höchstens 0,1 Stress-Tage vom besten Plan (Aufzählung aller Tage, 14 und 21 Tage, bis zu zwei Besuche) |
| Handbeispiel (Zimmerpflanze, Brüche) | 36 Gießvorgänge im Jahr ohne Stress; 14 Tage Abwesenheit 103544/50625 ≈ 2,0453 Stress-Tage, mit Docht 1/2 oder Nachbar am Tag 10 null; Fäulnisschaden 2/5; kleinster Verlust über alle Gießpläne der ersten 20 Tage 3/10 |
| Orakel-Instanz mit Jahreszeit (eine Pflanze, deterministisch) | Rückwärtsrechnung 11,12; bester fester Takt 15,08 (+35,6 %), bester Sommer/Winter-Takt 12,99 (+16,9 %), beste Schwelle bei exakter Messung im Raster von 0,01: 11,21 (+0,8 %) |

## Ehrliche Grenzen

- **Alle Zahlen der Pflanzen sind Annahmen:** Tage von voll bis Stressbeginn (Median je Klasse 21, 9 und 5, logarithmisch normale Streuung 0,25 je Pflanze; die zwölf gezogenen Pflanzen haben im Mittel 20,0 / 8,6 / 6,1), Stressbeginn, Welkepunkt, Fäulnisgrenze, Wetter- und Jahreszeitfaktor. Für Zimmerpflanzen fand eine Websuche am 18. November 2026 keine begutachtete Quelle (nur Gartenblogs, deren Aussagen die Demo nicht als Beleg nutzt). Die Demo zeigt, was bei diesen Annahmen passiert, nicht wie sich eine bestimmte Pflanze verhält.
- **Literatur nur als Größenordnung (nur Abstracts gelesen):** Nackley u. a. 2020 (HortScience): Weihnachtssterne in 11-Liter-Töpfen im Gewächshaus zeigten beim wöchentlichen Gießen keinen Wasserstress, bis der Substratwassergehalt 0,3 m³/m³ erreichte. Van Iersel u. a. 2010 (HortScience 45(2)): Gießschwellen von 0,05 bis 0,40 m³/m³ bei Petunien; dass Wasser unter 0,20 m³/m³ als nicht verfügbar gilt, ist dort eine übernommene Allgemeinaussage. Gewächshaus, große Töpfe, andere Kulturen; die relative Feuchte der Demo (0 bis 1) ist nicht auf m³/m³ abgebildet.
- **Die abgestimmten Strategien sind ein Quasi-Orakel:** Kalender, Schwelle und adaptive Kontrolle bekommen ihren Parameter je Pflanze auf getrennten Trainingspfaden desselben Modells. Wer seinen Rhythmus nur probiert, steht gegen den abgestimmten Kalender und die abgestimmte adaptive Kontrolle schlechter; deshalb zeigt die Tabelle auch die beiden Lerner (Probieren über drei Jahre, ausgewiesen wird Jahr 3, die Lernkosten der ersten Jahre sind nicht enthalten). Auch die Lerner sind nicht frei vom Modell: ihre Lernregel (Schrittweite, Schwelle der Fingerprobe) ist auf Trainingspfaden abgestimmt, die Startwerte kommen aus der Pflanzenklasse.
- **Fäulnis nur als Ereignis** beim Gießen auf noch feuchte Erde, nicht als Dauer der Nässe. Eine Gegenprobe mit Nässedauer in der Vormessung änderte die Rangfolge der Strategien nicht, verschob aber einzelne Umschlagpunkte (zum Beispiel den der Sukkulenten im Winter) und verkleinerte den Abstand des Wochentakts; sie ist in der App nicht nachrechenbar.
- **Nicht modelliert:** Tod der Pflanze (Stress wird nur gezählt), Wechselwirkung zwischen Pflanzen (außer dem gemeinsamen Wetter), Gießmenge als Entscheidung (gegossen wird immer auf voll), Lichtmangel im Schatten (Schatten ist daher zu günstig), Umtopfen, Standortwechsel, Schädlinge.
- **Docht und Schatten:** Vorrat und Faktor sind Annahmen; die Nutzen verschieben sich mit ihnen.
- **Keine Pflegeempfehlung** für eine bestimmte Pflanze. Die Regeln sind Rechenverfahren im Modell.

## Befunde und Korrekturen gegenüber dem Plan

- **Umschlagpunkt im Hochsommer hängt in der Demo kaum am Fäulnisgewicht.** Die Vormessung stimmte den Kalender einmal auf Gewicht 5 ab und rechnete alle Gewichte mit demselben Abreisezustand (Sukkulenten im Sommer 8 / 12 / nie). Die Demo stimmt den Kalender je Gewicht neu ab (wer Fäulnis schwer wiegt, gießt auch den Kalender anders): Sukkulenten im Hochsommer 10 / 10 / 10, Zimmerpflanzen bei Gewicht 20 jetzt 9 statt „immer“. Im Winter bleibt die Abhängigkeit (12 / 18 / 27). „Der Umschlagpunkt hängt stark am Fäulnisgewicht“ gilt in der Demo deshalb nur für den Winter.
- **Preset „Urlaub im Sommer, 14 Tage“ wurde „21 Tage“**: 14 Tage im Sommer sind der Standard, beide Presets wären nicht unterscheidbar gewesen. Der Plan sah außerdem ein Preset „Von Hand“ vor; es ist ein Tab.
- **Zahlen der Vormessung sind Erwartungen:** Die Demo rechnet mit demselben Zufallsstrom wie die Vormessung (gleiche Pfade), die Abstimmung nutzt 20 statt 30 Trainingspfade; deshalb können einzelne Zellen von der Vormessung abweichen. Die Tests rechnen neu und vergleichen als Band.
- **Probieren statt Orakel** (Plan H12, H15) ist in der Demo als Tabellenzeilen „Lerner“ enthalten, die Gegenprobe „Fäulnis als Nässedauer“ (Plan H13) nicht: sie war nur in der Vormessung rechenbar.

## Verifikation

- **Kern:** je Einheit eine Handrechnung auf der Mini-Instanz (`tests/test_algorithm.py`, `zpf_hand.py` in exakten Brüchen); Strategien (Takt, Sommer/Winter-Takt, Schwelle, Kontrollzahlen).
- **Orakel:** `tests/test_oracle_zimmerpflanzen.py`: (A1) Aufzählung aller Gießpläne gegen Rückwärtsrechnung gegen Schwellenregel in Brüchen, dazu die Simulation der App; (A2) Rückwärtsrechnung über (Tag, Tag des letzten Gießens) in reinem Python für die Instanz mit Jahreszeit, mit Takt, Sommer/Winter-Takt und Schwelle gegen den Plan und die Simulation der App; (B) Python-Tagesschleife gegen die NumPy-Fassung mit denselben Zufallszahlen (Takt und Schwelle, 2 Pfade × 12 Pflanzen); (C) Urlaub, Tagesschleife gegen NumPy mit Docht, Schatten, Besuchen.
- **Behauptungen:** `tests/test_claims.py` rechnet die Zahlen der Tabelle oben nach (als Band; das Raster exakt), `tests/test_oracle_zimmerpflanzen.py` die Orakel-Instanz.
- **Verdikte, Presets, Randfälle:** `tests/test_verdicts.py`, `tests/test_presets.py`, `tests/test_edge_cases.py` (ein Pfad, ohne Zufall, kürzeste und längste Abwesenheit, Rauschen 0, alle Gewichte 0).
- **Oberfläche:** AppTest-Rauchtest (jeder Button, jeder Regler am Minimum und Maximum) und Inhaltstest (`tests/test_app.py`, `tests/test_app_content.py`); Layout (Schnellstart oben, fester Kopf, aktives Preset hervorgehoben, `tests/test_layout.py`); Footer; Laufzeit-Importe. Für die App-Tests werden die Abstimmgitter verkleinert (nur die Gitter, nicht die Regeln), damit ein Lauf der App Sekunden dauert.
- **Zufall:** NumPy-Zufallsstrom (`default_rng`); Neu-Rechnen-Tests als Band, weil `exp`/`cos` unter Linux in der letzten Binärstelle abweichen können.

## Tests

102 Tests (`pytest --collect-only -q tests`): Handrechnungen je Einheit, Orakel, Behauptungen der README, Verdikte, Presets, Randfälle, AppTest, Layout, Footer. Die Behauptungstests und die Rasterprüfung dauern am längsten (rund eine Minute); die App-Tests laufen mit verkleinerten Abstimmgittern.

## Dateistruktur

| Datei | Zweck |
|---|---|
| `.github/workflows/tests.yml` | CI: Push, Pull Request, wöchentlicher Canary |
| `.gitignore` | venv, Caches, Streamlit-Secrets |
| `.streamlit/config.toml` | Streamlit-Einstellungen (keine Nutzungsstatistik) |
| `app.py` | Streamlit-App: Tabs „Von Hand“, „Akt 1“, „Akt 2“, „Grenzen“, Kernfragen, Expander |
| `data/kreuzung.csv` | vorgerechnetes Raster „Kreuzungspunkt“ (60 Zellen), erzeugt von `zpf_grid.py` |
| `requirements-dev.txt` | Laufzeit plus pytest |
| `requirements.txt` | Laufzeit-Bibliotheken (ungepinnt) |
| `zpf_absence.py` | Urlaub: Abreisezustand, Abwesenheit mit Docht, Schatten, Besuchen, Umschlagpunkt |
| `zpf_algorithm.py` | Kern: Dynamik, Strategien (Kalender, Schwelle, adaptive Kontrolle, Lerner), Simulation, Abstimmung |
| `zpf_constants.py` | Pflanzenklassen, Regler-Grenzen, Annahmen, Farben, Presets |
| `zpf_evaluation.py` | Kennzahlen und Verdikte |
| `zpf_grid.py` | Referenzraster erzeugen und lesen |
| `zpf_hand.py` | Handbeispiel in exakten Brüchen, Rückwärtsrechnung der Mini-Instanz |
| `zpf_layout.py` | Fester Kopf (Stylesheet) |
| `zpf_pdf_export.py` | PDF-Export (fpdf2) |
| `zpf_plants.py` | die zwölf Pflanzen |
| `zpf_presets.py` | Permalink, Presets (Schnellstart in der Seitenleiste, aktives Preset hervorgehoben), Zufalls-Seed-Button |
| `zpf_strategies.py` | Abstimmung aller Strategien, Vergleichstabelle |
| `zpf_texts.py` | Texte, die App und README gemeinsam führen |
| `zpf_visualization.py` | Plotly-Abbildungen (Achsen gesperrt) |
| `tests/` | Kern, Orakel, Behauptungen, Verdikte, Presets, Randfälle, Oberfläche, Layout, Footer, Laufzeit-Importe |

## Bewusst nicht umgesetzt

- **Eigene Pflanzen eintragen** (Liste mit Art und Topfgröße): erst in einer Folgefassung.
- **Gießmenge als Entscheidung:** gegossen wird immer auf „voll“. Eine Gegenprobe mit Fäulnis als Nässedauer (Vormessung) zeigt, dass dann die Nässe nach dem Gießen den Verlust bestimmt und die Menge wichtig würde.
- **Tod der Pflanze, Wechselwirkung zwischen Pflanzen (außer dem gemeinsamen Wetter), Lichtmangel im Schatten:** nicht modelliert.
- **Lerner für den Schwellenwert der einfachen Schwelle:** nur Kalender-Lerner und adaptiver Lerner.

## Lokal ausführen

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

## Tests ausführen

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Das Raster neu erzeugen (einige Minuten): `python zpf_grid.py`.

Gebaut mit Streamlit, Plotly, NumPy und fpdf2.

---

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zu den Demos: [Interaktive Demos](https://sebastianhanisch.net/demos.html).
