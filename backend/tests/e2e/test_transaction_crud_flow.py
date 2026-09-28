
import pytest
from playwright.sync_api import expect

from tests.e2e.pages import TransactionsPage

pytestmark = pytest.mark.e2e


def test_login_create_edit_delete_transaction(logged_in_page):
    expenses = TransactionsPage(logged_in_page, "expense")
    expenses.navigate_to("Expenses")
    expenses.expect_heading("Expenses")

    expenses.add("E2E Coffee Run", 12.50, category="Food & Dining", merchant="Corner Cafe")
    row = expenses.row("E2E Coffee Run")
    expect(row).to_contain_text("$12.50")
    expect(row).to_contain_text("Food & Dining")
    expect(row).to_contain_text("Corner Cafe")

    expenses.edit("E2E Coffee Run", description="E2E Coffee Run (edited)", amount=15)
    expect(expenses.row("E2E Coffee Run (edited)")).to_contain_text("$15.00")

    expenses.delete("E2E Coffee Run (edited)")
    expect(logged_in_page.get_by_text("No expense entries yet")).to_be_visible()


def test_income_is_listed_separately_from_expenses(logged_in_page):
    income = TransactionsPage(logged_in_page, "income").open()
    income.add("E2E Salary", 2500, category="Salary")
    expect(income.row("E2E Salary")).to_contain_text("+$2,500.00")

    expenses = TransactionsPage(logged_in_page, "expense")
    expenses.navigate_to("Expenses")
    expect(expenses.row("E2E Salary")).to_have_count(0)


def test_search_filters_the_table(logged_in_page, api):
    api.add_transaction("Weekly groceries", 60, "Food & Dining")
    api.add_transaction("Bus ticket", 2.5, "Transport")

    expenses = TransactionsPage(logged_in_page, "expense").open()
    expenses.search("grocer")

    expect(expenses.row("Weekly groceries")).to_be_visible()
    expect(expenses.row("Bus ticket")).to_have_count(0)
