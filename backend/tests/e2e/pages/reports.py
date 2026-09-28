from playwright.sync_api import Download, Locator

from tests.e2e.pages.base import BasePage


class ReportsPage(BasePage):

    path = "/reports"

    def generate(self):
        self.page.get_by_role("button", name="Generate Report").click()

    def stat(self, label: str) -> Locator:
        return self.page.locator(".report-stat", has=self.page.locator(".rs-label", has_text=label)).locator(".rs-value")

    def export_csv(self) -> Download:
        with self.page.expect_download() as download:
            self.page.get_by_role("button", name="Export CSV").click()
        return download.value
