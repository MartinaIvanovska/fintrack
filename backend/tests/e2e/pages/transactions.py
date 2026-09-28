from playwright.sync_api import Locator, expect

from tests.e2e.pages.base import BasePage, field


class TransactionsPage(BasePage):

    def __init__(self, page, kind: str = "expense"):
        super().__init__(page)
        self.kind = kind
        self.path = "/income" if kind == "income" else "/expenses"
        self.title = "Income" if kind == "income" else "Expense"

    @property
    def modal(self) -> Locator:
        return self.page.locator(".modal")

    def row(self, description: str) -> Locator:
        return self.page.locator("tbody tr", has_text=description)

    def _fill_form(self, description=None, amount=None, date=None, category=None, merchant=None):
        if description is not None:
            field(self.page, "Description *").fill(description)
        if amount is not None:
            field(self.page, "Amount *").fill(str(amount))
        if date is not None:
            field(self.page, "Date *").fill(date)
        if category is not None:
            field(self.page, "Category *").select_option(label=category)
        if merchant is not None:
            field(self.page, "Merchant").fill(merchant)

    def add(self, description: str, amount, category: str, date: str = None, merchant: str = None):
        self.page.get_by_role("button", name=f"Add {self.title}").click()
        self._fill_form(description, amount, date, category, merchant)
        self.page.get_by_role("button", name="Add Transaction").click()
        expect(self.modal).to_be_hidden()
        expect(self.row(description)).to_be_visible()

    def edit(self, current_description: str, **changes):
        self.row(current_description).locator(".icon-btn").first.click()
        self._fill_form(**changes)
        self.page.get_by_role("button", name="Save Changes").click()
        expect(self.modal).to_be_hidden()

    def delete(self, description: str):
        self.page.once("dialog", lambda dialog: dialog.accept())
        self.row(description).locator(".icon-btn--danger").click()
        expect(self.row(description)).to_have_count(0)

    def search(self, text: str):
        self.page.get_by_placeholder("Search transactions…").fill(text)
