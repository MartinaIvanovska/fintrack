"""Page objects for the Fintrack UI (one class per screen)."""
from tests.e2e.pages.auth import AuthPage
from tests.e2e.pages.budgets import BudgetsPage
from tests.e2e.pages.reports import ReportsPage
from tests.e2e.pages.settings import SettingsPage
from tests.e2e.pages.transactions import TransactionsPage

__all__ = ["AuthPage", "BudgetsPage", "ReportsPage", "SettingsPage", "TransactionsPage"]
