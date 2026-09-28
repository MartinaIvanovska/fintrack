
import uuid

import pytest
from playwright.sync_api import expect

from tests.e2e.pages import AuthPage, SettingsPage

pytestmark = pytest.mark.e2e


def test_profile_update_is_saved(logged_in_page):
    settings = SettingsPage(logged_in_page).open()
    new_name = f"renamed_{uuid.uuid4().hex[:6]}"

    settings.update_profile(username=new_name)

    expect(settings.profile_message).to_have_text("Profile updated successfully!")
    logged_in_page.reload()
    expect(settings.signed_in_username()).to_have_text(new_name)


@pytest.mark.xfail(strict=True, reason="the sidebar keeps the old username until the page is reloaded")
def test_sidebar_shows_the_new_username_straight_away(logged_in_page):
    settings = SettingsPage(logged_in_page).open()
    new_name = f"renamed_{uuid.uuid4().hex[:6]}"

    settings.update_profile(username=new_name)

    expect(settings.profile_message).to_be_visible()
    expect(settings.signed_in_username()).to_have_text(new_name)


def test_mismatching_new_passwords_are_caught_in_the_browser(logged_in_page, fresh_user_credentials):
    settings = SettingsPage(logged_in_page).open()
    settings.change_password(fresh_user_credentials["password"], "new-password-1", confirm="different-2")
    expect(settings.password_message).to_have_text("Passwords do not match")


def test_wrong_current_password_is_reported(logged_in_page):
    settings = SettingsPage(logged_in_page).open()
    settings.change_password("not-my-password", "new-password-1")
    expect(settings.password_message).to_have_text("Current password is incorrect")


def test_changed_password_is_used_at_the_next_sign_in(logged_in_page, fresh_user_credentials):
    settings = SettingsPage(logged_in_page).open()
    settings.change_password(fresh_user_credentials["password"], "brand-new-password-9")
    expect(settings.password_message).to_have_text("Password changed successfully!")

    settings.log_out()
    auth = AuthPage(logged_in_page)
    auth.log_in(fresh_user_credentials["email"], "brand-new-password-9")
    auth.wait_until_signed_in()
    expect(auth.signed_in_username()).to_have_text(fresh_user_credentials["username"])
