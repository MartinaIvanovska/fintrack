"""
Load test for the Fintrack API with Locust.

Each simulated user registers its own account, seeds a realistic history
(24 transactions over the last three months and a budget), then keeps using
the app the way a person would: mostly lists and the dashboard, sometimes
adding a transaction, rarely exporting a report. Requests made only to set
up data are named "[setup] ..." and are left out of the acceptance criteria.

Acceptance criteria (checked when the run ends; the process exits with 1 if
any is missed, so the run can gate CI):
  - failure ratio of measured requests <= PERF_MAX_FAIL_RATIO (default 1 %)
  - 95th percentile of every measured endpoint <= PERF_MAX_P95_MS (default 1000 ms)

Run (see docker-compose.yml, profile "perf"):
  docker compose --profile perf run --rm locust
"""
import os
import random
import uuid
from datetime import datetime, timedelta

from locust import HttpUser, between, events, task

MAX_FAIL_RATIO = float(os.environ.get("PERF_MAX_FAIL_RATIO", "0.01"))
MAX_P95_MS = float(os.environ.get("PERF_MAX_P95_MS", "1000"))
SETUP = "[setup] "

WORDS = ["groceries", "coffee", "fuel", "rent", "cinema", "books", "lunch", "taxi", "gym", "pharmacy"]


class FintrackUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        unique = uuid.uuid4().hex[:12]
        resp = self.client.post("/api/auth/register", name=f"{SETUP}POST /api/auth/register", json={
            "username": f"perf_{unique}", "email": f"perf-{unique}@example.com", "password": "perf-password-1",
        })
        resp.raise_for_status()
        self.client.headers["Authorization"] = f"Bearer {resp.json()['access_token']}"

        categories = self.client.get("/api/categories", name=f"{SETUP}GET /api/categories").json()
        self.expense_categories = [c["id"] for c in categories if c["type"] == "expense"]
        self.income_category = next(c["id"] for c in categories if c["type"] == "income")
        self.month = datetime.utcnow().strftime("%Y-%m")

        today = datetime.utcnow()
        for i in range(24):
            self._add_transaction(date=today - timedelta(days=random.randint(0, 90)), name=f"{SETUP}POST /api/transactions")
        self.client.post("/api/budgets", name=f"{SETUP}POST /api/budgets", json={
            "category_id": self.expense_categories[0], "month_year": self.month, "limit_amount": 500,
        })

    def _add_transaction(self, date=None, name="POST /api/transactions"):
        income = random.random() < 0.15
        self.client.post("/api/transactions", name=name, json={
            "type": "income" if income else "expense",
            "amount": round(random.uniform(3000, 4000) if income else random.uniform(2, 150), 2),
            "date": (date or datetime.utcnow()).replace(microsecond=0).isoformat(),
            "category_id": self.income_category if income else random.choice(self.expense_categories),
            "description": random.choice(WORDS),
        })

    # --- what a user does, weighted by how often --------------------------------
    @task(5)
    def list_expenses(self):
        self.client.get("/api/transactions", name="GET /api/transactions",
                        params={"type": "expense", "page": 1, "page_size": 15})

    @task(4)
    def dashboard(self):
        self.client.get("/api/dashboard", name="GET /api/dashboard")

    @task(2)
    def search(self):
        self.client.get("/api/transactions", name="GET /api/transactions?search",
                        params={"type": "expense", "search": random.choice(WORDS)[:4]})

    @task(2)
    def add_expense(self):
        self._add_transaction()

    @task(2)
    def budgets(self):
        self.client.get("/api/budgets", name="GET /api/budgets", params={"month_year": self.month})

    @task(1)
    def categories(self):
        self.client.get("/api/categories", name="GET /api/categories")

    @task(1)
    def profile(self):
        self.client.get("/api/auth/me", name="GET /api/auth/me")

    @task(1)
    def report(self):
        self.client.get("/api/reports", name="GET /api/reports", params={"month_year": self.month})

    @task(1)
    def export_csv(self):
        self.client.get("/api/reports/export/csv", name="GET /api/reports/export/csv", params={"month_year": self.month})


@events.quitting.add_listener
def check_acceptance_criteria(environment, **_):
    measured = [e for e in environment.stats.entries.values() if not e.name.startswith(SETUP)]
    requests = sum(e.num_requests for e in measured)
    failures = sum(e.num_failures for e in measured)
    fail_ratio = failures / requests if requests else 1.0
    slow = {e.name: e.get_response_time_percentile(0.95) for e in measured
            if e.num_requests and e.get_response_time_percentile(0.95) > MAX_P95_MS}

    print(f"\nAcceptance criteria: {requests} measured requests, failure ratio {fail_ratio:.2%} "
          f"(max {MAX_FAIL_RATIO:.0%}), p95 limit {MAX_P95_MS:.0f} ms per endpoint")
    problems = []
    if not requests:
        problems.append("no measured requests were made")
    if fail_ratio > MAX_FAIL_RATIO:
        problems.append(f"failure ratio {fail_ratio:.2%} is above {MAX_FAIL_RATIO:.0%}")
    problems += [f"{name}: p95 {p95:.0f} ms is above {MAX_P95_MS:.0f} ms" for name, p95 in slow.items()]
    for p in problems:
        print(f"  FAIL - {p}")
    if not problems:
        print("  PASS")
    environment.process_exit_code = 1 if problems else 0
