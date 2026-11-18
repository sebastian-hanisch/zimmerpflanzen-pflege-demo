"""Konstanten: Pflanzenklassen, Regler-Grenzen, feste Annahmen, Farben und Presets.

ALLE Zahlen zu den Pflanzen (Trockenzeit, Stressbeginn, Welkepunkt, Fäulnisgrenze, Streuung) sind Annahmen: für Zimmerpflanzen
gibt es keine begutachtete Quelle (siehe README, „Ehrliche Grenzen“)."""

DAYS = 365
HET = 0.25            # Streuung der Trockenzeit je Pflanze (logarithmisch normal, sd)
PLANT_SEED = 12345
COMMON_SD = 0.25      # gemeinsamer Wetterfaktor, sd des Logarithmus
INDIV_SD = 0.15       # Faktor je Pflanze und Tag, sd des Logarithmus

# Klasse, Anzahl, Tage von voll bis Stressbeginn (Mittel), Stressbeginn s*, Welkepunkt s_w, Fäulnisgrenze (1,0 = keine)
KLASSEN = (
    ("Sukkulente", 4, 21.0, 0.25, 0.10, 0.50),
    ("Zimmerpflanze", 5, 9.0, 0.40, 0.15, 0.75),
    ("Durstig", 3, 5.0, 0.55, 0.25, 1.00),
)
KLASSEN_NAMEN = tuple(k[0] for k in KLASSEN)

# Regler: Name -> (Minimum, Maximum, Standard)
AMP_MIN, AMP_MAX, DEFAULT_AMP = 0.0, 0.6, 0.4          # Jahreszeit-Amplitude der Austrocknung
AR_MIN, AR_MAX, DEFAULT_AR = 0.0, 0.98, 0.95           # Autokorrelation des Wetterfaktors
SIGMA_MIN, SIGMA_MAX, DEFAULT_SIGMA = 0.0, 0.4, 0.15   # Messrauschen (sd, in Feuchte-Einheiten)
CC_MIN, CC_MAX, DEFAULT_CC = 0.0, 0.1, 0.02            # Kosten je Kontrolle
CW_MIN, CW_MAX, DEFAULT_CW = 0.0, 1.0, 0.3             # Kosten je Gießen
WROT_MIN, WROT_MAX, DEFAULT_WROT = 0.0, 30.0, 5.0      # Gewicht der Fäulnis
V_MIN, V_MAX, DEFAULT_V = 1, 7, 3                      # Kontrollabstand der einfachen Schwelle (Tage)
A_MIN, A_MAX, DEFAULT_A = 3, 35, 14                    # Abwesenheit (Tage)
SEASON_SUMMER, SEASON_WINTER = 0, 1
DEFAULT_SEASON = SEASON_SUMMER
DOCK_MIN, DOCK_MAX, DEFAULT_DOCK = 0.0, 1.5, 0.5       # Docht-Vorrat in Feuchte-Einheiten
SHADE_MIN, SHADE_MAX, DEFAULT_SHADE = 0.3, 1.0, 0.5    # Faktor der Austrocknung im Schatten
VISITS_MIN, VISITS_MAX, DEFAULT_VISITS = 0, 3, 0       # Besuche des Nachbarn
PATHS_MIN, PATHS_MAX, DEFAULT_PATHS = 20, 100, 40      # Auswertepfade (Jahre bzw. Urlaube)
SEED_MAX, DEFAULT_SEED = 999999, 1000

TRAIN_PATHS = 20      # Trainingspfade der Abstimmung (live)
TRAIN_SEED = 1
ABREISE_TAG = {SEASON_SUMMER: 195, SEASON_WINTER: 15}
A_GRID = tuple(range(3, 36))   # Abwesenheiten der Umschlagpunkt-Kurve

# Referenzraster (vorgerechnet, data/kreuzung.csv): Kontrollkosten x Messrauschen je Fäulnisgewicht
GRID_CC = (0.0, 0.01, 0.02, 0.05, 0.10)
GRID_SIGMA = (0.0, 0.1, 0.2, 0.3)
GRID_WROT = (1.0, 5.0, 20.0)

COLOR_CALENDAR = "#2F6B65"
COLOR_MEASURE = "#b5651d"
COLOR_BAD = "#a94442"
COLOR_LINE = "#4c78a8"

PRESETS = {
    "Standard (Voreinstellung)": {},
    "Exakter Sensor (Rauschen 0, Kontrolle gratis)": {"sigma": 0.0, "cc": 0.0},
    "Grobe Fingerprobe (Rauschen 0,30)": {"sigma": 0.30},
    "Ohne Jahreszeit": {"amp": 0.0},
    "Sukkulenten vorsichtig (Fäulnisgewicht 20)": {"wrot": 20.0},
    "Urlaub im Sommer, 21 Tage": {"A": 21, "season": SEASON_SUMMER},
    "Urlaub im Winter, 28 Tage": {"A": 28, "season": SEASON_WINTER},
}
PRESET_HELP = {
    "Standard (Voreinstellung)": "Jahreszeit 0,4, Wetter stark zusammenhängend (0,95), Fingerprobe mit Rauschen 0,15, Kontrolle 0,02, Gießen 0,3, Fäulnisgewicht 5.",
    "Exakter Sensor (Rauschen 0, Kontrolle gratis)": "Ein genauer, kostenloser Sensor: Wann lohnt Messen dann gegenüber dem besten Kalender?",
    "Grobe Fingerprobe (Rauschen 0,30)": "Die Fingerprobe schätzt die Feuchte nur grob (Rauschen 0,30): Messen verliert gegen den Kalender.",
    "Ohne Jahreszeit": "Austrocknung das ganze Jahr gleich schnell (Amplitude 0): ein fester Kalender ist besonders stark.",
    "Sukkulenten vorsichtig (Fäulnisgewicht 20)": "Fäulnisgewicht 20 statt 5: Sukkulenten werden im Winter erst ab etwa 27 Tagen Abwesenheit vor der Abreise gegossen, im Hochsommer ab etwa 10 Tagen (Akt 2).",
    "Urlaub im Sommer, 21 Tage": "Abwesenheit 21 Tage ab Hochsommer (Tag 195).",
    "Urlaub im Winter, 28 Tage": "Abwesenheit 28 Tage ab Mitte Januar (Tag 15).",
}
