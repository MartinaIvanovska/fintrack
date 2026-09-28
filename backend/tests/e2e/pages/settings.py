from playwright.sync_api import Locator

from tests.e2e.pages.base import BasePage, field


class SettingsPage(BasePage):

    path = "/settings"

    def _section(self, title: str) -> Locator:
        return self.page.locator(".section-card", has=self.page.locator(".section-title", has_text=title))

    def update_profile(self, username: str = None, email: str = None):
        if username is not None:
            field(self.page, "Username").fill(username)
        if email is not None:
            field(self.page, "Email").fill(email)
        self.page.get_by_role("button", name="Save Profile").click()

    def change_password(self, current: str, new: str, confirm: str = None):
        field(self.page, "Current Password").fill(current)
        field(self.page, "New Password").fill(new)
        field(self.page, "Confirm New Password").fill(new if confirm is None else confirm)
        self._section("Change Password").get_by_role("button", name="Change Password").click()

    @property
    def profile_message(self) -> Locator:
        return self._section("Profile").locator(".form-msg")

    @property
    def password_message(self) -> Locator:
        return self._section("Change Password").locator(".form-msg")
