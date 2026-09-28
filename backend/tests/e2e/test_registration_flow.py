
import re
import uuid

import pytest
from playwright.sync_api import expect

from tests.e2e.pages import AuthPage
from tests.e2e.pages.base import BasePage

pytestmark = pytest.mark.e2e


def test_register_new_user_lands_on_dashboard(page):
    unique = uuid.uuid4().hex[:10]
    username = f"e2e_reg_{unique}"

    auth = AuthPage(page).open()
    auth.register(username, f"e2e-reg-{unique}@example.com", "brand-new-password-1")
    auth.wait_until_signed_in()

    shell = BasePage(page)
    shell.expect_heading("Dashboard")
    expect(shell.signed_in_username()).to_have_text(username)


def test_registering_an_existing_email_shows_an_error(page, fresh_user_credentials):
    auth = AuthPage(page).open()
    auth.register(f"other_{uuid.uuid4().hex[:6]}", fresh_user_credentials["email"], "whatever-pw-1")

    expect(auth.error).to_have_text("Email already registered")
    expect(page).to_have_url(re.compile(r"/auth$"))
