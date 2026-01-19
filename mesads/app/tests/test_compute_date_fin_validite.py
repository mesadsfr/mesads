from datetime import date

from mesads.app.forms import compute_next_date_fin_validite


def test_compute_fin_validite_1():
    start_date = date(2025, 1, 10)

    assert compute_next_date_fin_validite(start_date) == date(2026, 1, 10)


def test_compute_fin_validite_2():
    start_date = date(2025, 1, 10)
    renew_date = date(2025, 1, 9)

    assert compute_next_date_fin_validite(start_date, renew_date) == date(2026, 1, 10)


def test_compute_fin_validite_3():
    start_date = date(2025, 1, 10)
    renew_date = date(2025, 10, 9)

    assert compute_next_date_fin_validite(start_date, renew_date) == date(2027, 1, 10)


def test_compute_fin_validite_4():
    start_date = date(2025, 1, 10)
    renew_date = date(2026, 1, 9)

    assert compute_next_date_fin_validite(start_date, renew_date) == date(2027, 1, 10)


def test_compute_fin_validite_5():
    start_date = date(2025, 1, 10)
    renew_date = date(2030, 10, 9)

    assert compute_next_date_fin_validite(start_date, renew_date) == date(2032, 1, 10)


def test_compute_fin_validite_6():
    start_date = date(2025, 1, 10)
    renew_date = date(2031, 1, 9)

    assert compute_next_date_fin_validite(start_date, renew_date) == date(2032, 1, 10)
