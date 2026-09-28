
import re

import pytest
from playwright.sync_api import expect

from tests.e2e.pages import BudgetsPage
from tests.e2e.pages.base import field

pytestmark = pytest.mark.e2e


def test_new_budget_starts_empty_and_can_be_deleted(logged_in_page):
    budgets = BudgetsPage(logged_in_page).open()
    budgets.add("Food & Dining", 100)

    card = budgets.card("Food & Dining")
    expect(card).to_contain_text("$0 / $100")
    expect(card).to_contain_text("0%")
    expect(card).to_contain_text("$100 left")
    expect(card).not_to_have_class(re.compile(r"budget-card--(warning|over)"))

    budgets.delete("Food & Dining")
    expect(logged_in_page.get_by_text("No budgets set")).to_be_visible()


@pytest.mark.parametrize(
    "spent, state, percent, remaining",
    [
        (79, None, "79%", "$21 left"),
        (80, "warning", "80%", "$20 left"),
        (99, "warning", "99%", "$1 left"),
        (120, "over", "100%", "$20 over"),
    ],
    ids=["79%-normal", "80%-warning", "99%-warning", "120%-over"],
)
def test_card_state_follows_spending(logged_in_page, api, spent, state, percent, remaining):
    budgets = BudgetsPage(logged_in_page).open()
    budgets.add("Food & Dining", 100)
    api.add_transaction("Groceries", spent, "Food & Dining")
    logged_in_page.reload()

    card = budgets.card("Food & Dining")
    expect(card).to_contain_text(percent)
    expect(card).to_contain_text(remaining)
    if state:
        expect(card).to_have_class(re.compile(rf"\bbudget-card--{state}\b"))
    else:
        expect(card).not_to_have_class(re.compile(r"budget-card--(warning|over)"))


@pytest.mark.xfail(strict=True, reason='spending exactly the limit is shown as "$0 over"')
def test_spending_exactly_the_limit_is_not_shown_as_over_budget(logged_in_page, api):
    budgets = BudgetsPage(logged_in_page).open()
    budgets.add("Food & Dining", 100)
    api.add_transaction("Groceries", 100, "Food & Dining")
    logged_in_page.reload()

    expect(budgets.card("Food & Dining")).not_to_contain_text("over")


def test_a_budgeted_category_is_not_offered_again(logged_in_page):
    budgets = BudgetsPage(logged_in_page).open()
    budgets.add("Food & Dining", 100)

    logged_in_page.get_by_role("button", name="Add Budget").click()
    options = field(logged_in_page, "Category *").locator("option")
    expect(options.filter(has_text="Food & Dining")).to_have_count(0)
    expect(options.filter(has_text="Transport")).to_have_count(1)
