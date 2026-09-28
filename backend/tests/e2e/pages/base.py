
import os

from playwright.sync_api import Locator, Page, expect

FRONTEND_URL = os.environ.get("E2E_FRONTEND_URL", "http://localhost:3000")


def field(page: Page, label: str) -> Locator:
    group = page.locator(".form-group").filter(has=page.get_by_text(label, exact=True))
    return group.locator("input, select, textarea").first


class BasePage:
    path = "/"

    def __init__(self, page: Page):
        self.page = page

    def open(self):
        self.page.goto(f"{FRONTEND_URL}{self.path}")
        return self

    @property
    def sidebar(self) -> Locator:
        return self.page.locator("aside.sidebar")

    def navigate_to(self, link_text: str):
        self.sidebar.get_by_role("link", name=link_text, exact=True).click()

    def signed_in_username(self) -> Locator:
        return self.sidebar.locator(".user-name")

    def log_out(self):
        self.sidebar.get_by_role("button", name="Log out").click()

    def expect_heading(self, text: str):
        expect(self.page.locator("h1.page-title")).to_have_text(text)
