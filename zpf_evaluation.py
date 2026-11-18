"""Kennzahlen und Verdikte (reine Funktionen, tests/test_verdicts.py prüft jede Schwelle und jede Zahl im Text)."""

import zpf_constants as C


def pct_diff(a, b):
    """(a - b)/b in Prozent; None bei b = 0 (kein Bezug)."""
    if b == 0:
        return None
    return 100.0 * (a - b) / b


def kreuz_verdikt(measure_loss, calendar_loss, measure_name, calendar_name):
    """Satz zum Vergleich der besten Messstrategie mit dem besten Kalender. Rückgabe (Art, Text), Art: success | info | warning."""
    d = pct_diff(measure_loss, calendar_loss)
    if d is None:
        return "info", "Der Kalender hat keinen Verlust: ein Vergleich in Prozent ist nicht möglich."
    if d <= -5.0:
        return "success", (
            f"**Messen lohnt hier:** {measure_name} liegt mit {measure_loss:.1f} um {abs(d):.0f} % unter dem besten Kalender "
            f"({calendar_name}, {calendar_loss:.1f}). Bezugsgröße: Verlust je Pflanze und Jahr in Tagen vollen Trockenstresses."
        )
    if d < -1.0:
        return "info", (
            f"**Messen liegt knapp vorn:** {measure_name} {measure_loss:.1f} gegen {calendar_loss:.1f} des besten Kalenders "
            f"({abs(d):.1f} % weniger). Der Abstand ist klein gegen die Unsicherheit der Annahmen."
        )
    if d <= 1.0:
        return "info", f"**Gleichauf:** {measure_name} {measure_loss:.1f}, bester Kalender {calendar_loss:.1f} (Abstand {d:+.1f} %)."
    return "warning", (
        f"**Der Kalender gewinnt:** {calendar_name} {calendar_loss:.1f} gegen {measure_loss:.1f} der besten Messstrategie "
        f"({measure_name}), Messen kostet {d:.1f} % mehr."
    )


def lerner_verdikt(lern_calendar_loss, lern_measure_loss):
    """Lernend gegen lernend: Kalender durch Probieren gegen adaptive Kontrolle durch Probieren (Jahr 3)."""
    d = pct_diff(lern_measure_loss, lern_calendar_loss)
    if d is None:
        return "info", "Kein Vergleich möglich (Verlust 0)."
    if d <= -5.0:
        return "success", f"**Lernend gegen lernend gewinnt die Messung:** {abs(d):.0f} % weniger Verlust als der Kalender durch Probieren."
    if d < 5.0:
        return "info", f"**Lernend gegen lernend gleichauf** (Abstand {d:+.1f} %)."
    return "warning", f"**Lernend gegen lernend gewinnt der Kalender:** Messung {d:.0f} % schlechter."


def umschlag_text(name, value):
    """Satz zum Umschlagpunkt einer Klasse: `value` = Tage oder 'immer' / 'nie'."""
    if value == "immer":
        return f"{name}: vor der Abreise gießen lohnt schon bei kurzer Abwesenheit (ab {C.A_MIN} Tagen)."
    if value == "nie":
        return f"{name}: vor der Abreise nicht gießen, solange die Abwesenheit höchstens {C.A_MAX} Tage dauert."
    return f"{name}: vor der Abreise gießen lohnt ab {value} Tagen Abwesenheit, darunter nicht."


def ratio(loss_a, loss_b):
    """Verhältnis a/b als Zahl (None bei b = 0), z. B. für den Wochentakt gegen den abgestimmten Kalender."""
    if loss_b == 0:
        return None
    return loss_a / loss_b
