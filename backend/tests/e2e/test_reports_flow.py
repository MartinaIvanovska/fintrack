
import csv
import io
from datetime import datetime

import pytest
from playwright.sync_api import expect

from tests.e2e.pages import ReportsPage

pytestmark = pytest.mark.e2e


@pytest.fixture
def month_with_data(api):
    api.add_transaction("Salary", 3000, "Salary", type_="income")
    api.add_transaction("Groceries", 120, "Food & Dining")
    api.add_transaction("Lunch", 30, "Food & Dining")


def test_generated_report_shows_the_months_figures(logged_in_page, month_with_data):
    reports = ReportsPage(logged_in_page).open()
    reports.generate()

    expect(reports.stat("Total Income")).to_have_text("$3,000.00")
    expect(reports.stat("Total Expenses")).to_have_text("$150.00")
    expect(reports.stat("Net Savings")).to_have_text("$2,850.00")
    expect(reports.stat("Savings Rate")).to_have_text("95.0%")
    expect(reports.stat("Top Category")).to_have_text("Food & Dining")
    expect(reports.stat("Largest Expense")).to_have_text("Groceries ($120.00)")


def test_csv_download_contains_every_transaction(logged_in_page, month_with_data):
    reports = ReportsPage(logged_in_page).open()
    reports.generate()

    download = reports.export_csv()

    now = datetime.utcnow()
    assert download.suggested_filename == f"report_{now.year}-{now.month:02d}.csv"
    header, *rows = list(csv.reader(io.StringIO(open(download.path(), encoding="utf-8").read(), newline="")))
    assert header == ["Date", "Type", "Description", "Amount", "Category", "Payment Method", "Merchant"]
    assert sorted((r[2], r[3], r[4]) for r in rows) == [
        ("Groceries", "120.0", "Food & Dining"),
        ("Lunch", "30.0", "Food & Dining"),
        ("Salary", "3000.0", "Salary"),
    ]
