from playwright.sync_api import Locator, expect

from tests.e2e.pages.base import BasePage, field


class BudgetsPage(BasePage):

    path = "/budgets"

    def card(self, category: str) -> Locator:
        return self.page.locator(".budget-card", has=self.page.locator(".budget-cat-name", has_text=category))

    def add(self, category: str, limit):
        self.page.get_by_role("button", name="Add Budget").click()
        field(self.page, "Category *").select_option(label=category)
        field(self.page, "Monthly Limit ($) *").fill(str(limit))
        # Scoped to the modal: an empty page shows its own "Create Budget" button too.
        self.page.locator(".modal").get_by_role("button", name="Create Budget").click()
        expect(self.card(category)).to_be_visible()

    def delete(self, category: str):
        self.page.once("dialog", lambda dialog: dialog.accept())
        self.card(category).locator(".icon-btn--danger").click()
        expect(self.card(category)).to_have_count(0)
