
import re

import pytest
from playwright.sync_api import expect

from tests.e2e.pages import AuthPage
from tests.e2e.pages.base import FRONTEND_URL, BasePage

pytestmark = pytest.mark.e2e

ON_AUTH_PAGE = re.compile(r"/auth$")


@pytest.mark.parametrize("path", ["/", "/expenses", "/budgets", "/reports", "/settings"])
def test_protected_pages_redirect_to_sign_in(page, path):
    page.goto(f"{FRONTEND_URL}{path}")
    expect(page).to_have_url(ON_AUTH_PAGE)
    expect(page.get_by_role("button", name="Sign In", exact=True)).to_be_visible()


def test_logging_out_ends_the_session(logged_in_page):
    shell = BasePage(logged_in_page)
    shell.log_out()
    expect(logged_in_page).to_have_url(ON_AUTH_PAGE)

    logged_in_page.goto(f"{FRONTEND_URL}/budgets")
    expect(logged_in_page).to_have_url(ON_AUTH_PAGE)


def test_session_survives_a_page_reload(logged_in_page, fresh_user_credentials):
    logged_in_page.reload()
    shell = BasePage(logged_in_page)
    shell.expect_heading("Dashboard")
    expect(shell.signed_in_username()).to_have_text(fresh_user_credentials["username"])


def test_a_broken_stored_token_signs_the_user_out(logged_in_page):
    logged_in_page.evaluate("localStorage.setItem('token', 'not-a-valid-token')")
    logged_in_page.reload()
    expect(logged_in_page).to_have_url(ON_AUTH_PAGE)


@pytest.mark.xfail(strict=True, reason="a failed sign-in (401) triggers the global session-expired redirect, so no error is shown")
def test_wrong_password_shows_an_error_message(page, fresh_user_credentials):
    auth = AuthPage(page).open()
    auth.log_in(fresh_user_credentials["email"], "wrong-password")
    expect(auth.error).to_have_text("Invalid email or password")
