"""PDF-Export (fpdf2, Kernschriften: Umlaute gehen, andere Sonderzeichen werden ersetzt)."""

from fpdf import FPDF

_REPLACE = {"–": "-", "—": "-", "≥": ">=", "≤": "<=", "→": "->", "×": "x", "·": "*", "„": '"', "“": '"', "’": "'", "≈": "~", "−": "-"}


def _latin(text):
    for a, b in _REPLACE.items():
        text = text.replace(a, b)
    return text.encode("latin-1", "replace").decode("latin-1")


def build_pdf(settings, rows, w, turn, a_days, season_name):
    """settings: dict der Reglerwerte; rows: Strategie-Tabelle (zpf_strategies.compare); w: Gewichte;
    turn: {Klasse: Umschlagpunkt}; a_days, season_name: Urlaubseinstellung."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 9, _latin("Zimmerpflanzen gießen: Kalender oder Messen?"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(
        0, 5,
        _latin("Modellrechnung mit erfundenen Parametern (keine Pflegeempfehlung). Verlust je Pflanze und Jahr in Tagen vollen Trockenstresses."),
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Einstellungen", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 5, _latin("; ".join(f"{k} = {v}" for k, v in settings.items())), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Strategien (Akt 1)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 8)
    widths = (78, 20, 20, 20, 20, 20)
    for head, wd in zip(("Strategie", "Verlust", "trocken", "Faeulnis", "giessen", "Kontr."), widths):
        pdf.cell(wd, 5, head, border=1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 8)
    for r in rows:
        vals = (r["name"], f"{r['loss']:.2f}", f"{r['dry']:.2f}", f"{r['rot']:.2f}", f"{r['nw']:.1f}", f"{r['nc']:.1f}")
        for v, wd in zip(vals, widths):
            pdf.cell(wd, 5, _latin(v)[:46], border=1)
        pdf.ln()
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, _latin(f"Urlaub (Akt 2): {a_days} Tage, Abreise {season_name}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    for name, val in turn.items():
        txt = f"{name}: Umschlagpunkt {val}" if isinstance(val, (int, float)) else f"{name}: {val}"
        pdf.cell(0, 5, _latin(txt), new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
