from playwright.sync_api import Locator

from tests.e2e.pages.base import BasePage, field


class AuthPage(BasePage):
    """The sign-in / registration screen at /auth."""

    path = "/auth"

    def log_in(self, email: str, password: str):
        field(self.page, "Email").fill(email)
        field(self.page, "Password").fill(password)
        self.page.get_by_role("button", name="Sign In", exact=True).click()

    def register(self, username: str, email: str, password: str):
        self.page.locator(".auth-toggle").get_by_role("button", name="Register").click()
        field(self.page, "Username").fill(username)
        field(self.page, "Email").fill(email)
        field(self.page, "Password").fill(password)
        self.page.get_by_role("button", name="Create Account").click()

    def wait_until_signed_in(self):
        self.page.wait_for_url(lambda url: "/auth" not in url, timeout=10_000)

    @property
    def error(self) -> Locator:
        return self.page.locator(".auth-error")
