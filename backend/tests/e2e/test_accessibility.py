
from datetime import datetime

import pytest
from axe_playwright_python.sync_playwright import Axe

from tests.e2e.pages import AuthPage
from tests.e2e.pages.base import FRONTEND_URL

pytestmark = pytest.mark.e2e

axe = Axe()


BASELINE = {
    "sign-in": {"color-contrast", "landmark-one-main", "region"},
    "dashboard": {"color-contrast", "heading-order"},
    "expenses": {"button-name", "color-contrast", "empty-table-header"},
    "income": {"color-contrast", "empty-table-header"},
    "budgets": {"button-name", "color-contrast", "label"},
    "reports": {"color-contrast", "label"},
    "settings": {"color-contrast", "heading-order", "label"},
    "analytics": {"color-contrast", "heading-order"},
    "subscriptions": {"color-contrast", "heading-order"},
    "add-expense-dialog": {"button-name", "color-contrast", "empty-table-header", "label", "select-name"},
    "generated-report": {"color-contrast", "label"},
}


def describe(violations: list) -> str:
    return "\n".join(
        f"  {v['id']} [{v['impact']}] {v['help']} - e.g. {v['nodes'][0]['target']}" for v in violations
    )


def assert_matches_baseline(page, screen: str):
    violations = axe.run(page).response["violations"]
    found = {v["id"] for v in violations}
    expected = BASELINE.get(screen, set())

    new = [v for v in violations if v["id"] not in expected]
    assert not new, f"new accessibility violations on {screen}:\n{describe(new)}"
    fixed = expected - found
    assert not fixed, f"{screen} no longer violates {sorted(fixed)} - remove them from BASELINE"


@pytest.fixture
def seeded_page(logged_in_page, api):
    api.add_transaction("Groceries", 42, "Food & Dining")
    api._http.post("/api/budgets", json={
        "category_id": api.category_id("Food & Dining"),
        "month_year": datetime.utcnow().strftime("%Y-%m"), "limit_amount": 100,
    }).raise_for_status()
    return logged_in_page


def test_sign_in_screen(page):
    AuthPage(page).open()
    page.wait_for_load_state("networkidle")
    assert_matches_baseline(page, "sign-in")


@pytest.mark.parametrize(
    "screen, path",
    [
        ("dashboard", "/"), ("expenses", "/expenses"), ("income", "/income"), ("budgets", "/budgets"),
        ("reports", "/reports"), ("settings", "/settings"), ("analytics", "/analytics"),
        ("subscriptions", "/subscriptions"),
    ],
    ids=lambda v: v if not v.startswith("/") else None,
)
def test_signed_in_screen(seeded_page, screen, path):
    seeded_page.goto(f"{FRONTEND_URL}{path}")
    seeded_page.wait_for_load_state("networkidle")
    assert_matches_baseline(seeded_page, screen)


def test_add_expense_dialog(seeded_page):
    seeded_page.goto(f"{FRONTEND_URL}/expenses")
    seeded_page.get_by_role("button", name="Add Expense").click()
    assert_matches_baseline(seeded_page, "add-expense-dialog")


def test_generated_report(seeded_page):
    seeded_page.goto(f"{FRONTEND_URL}/reports")
    seeded_page.get_by_role("button", name="Generate Report").click()
    seeded_page.get_by_text("Report for").wait_for()
    assert_matches_baseline(seeded_page, "generated-report")
