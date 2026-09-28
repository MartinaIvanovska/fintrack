
import pytest
import schemathesis
from hypothesis import HealthCheck, settings
from schemathesis.checks import content_type_conformance, not_a_server_error, response_schema_conformance

from app.main import app

pytestmark = pytest.mark.api

schemathesis.experimental.OPEN_API_3_1.enable()

schema = schemathesis.from_dict(app.openapi())

CHECKS = (not_a_server_error, content_type_conformance, response_schema_conformance)

NAIVE_TIMESTAMP = "created_at has no timezone, but the schema promises an RFC 3339 date-time"
MALFORMED_ID = "a malformed id in the URL returns 500"
MALFORMED_CATEGORY = "a malformed category_id in the body returns 500"
INVALID_MONTH = "an invalid month_year returns 500"

KNOWN_FAILURES = {
    ("POST", "/api/auth/register"): NAIVE_TIMESTAMP,
    ("POST", "/api/auth/login"): NAIVE_TIMESTAMP,
    ("GET", "/api/auth/me"): NAIVE_TIMESTAMP,
    ("PUT", "/api/auth/me"): NAIVE_TIMESTAMP,
    ("GET", "/api/transactions"): "an unparsable start_date/end_date returns 500",
    ("POST", "/api/transactions"): MALFORMED_CATEGORY,
    ("PUT", "/api/transactions/{tx_id}"): MALFORMED_ID,
    ("DELETE", "/api/transactions/{tx_id}"): MALFORMED_ID,
    ("DELETE", "/api/categories/{cat_id}"): MALFORMED_ID,
    ("POST", "/api/budgets"): f"{INVALID_MONTH}; {MALFORMED_CATEGORY}",
    ("PUT", "/api/budgets/{budget_id}"): MALFORMED_ID,
    ("DELETE", "/api/budgets/{budget_id}"): MALFORMED_ID,
    ("GET", "/api/reports"): INVALID_MONTH,
    ("GET", "/api/reports/export/csv"): f"{INVALID_MONTH}; returns text/csv but the schema documents application/json",
}

MAY_FAIL = {
    ("POST", "/api/auth/change-password"): "a NUL byte in a password returns 500",
}


@schema.parametrize()
@settings(
    max_examples=50,
    derandomize=True,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow, HealthCheck.filter_too_much],
)
def test_api_operation(case, api_base_url, auth_headers, fresh_data, request):
    operation = (case.method, case.path)
    if operation in KNOWN_FAILURES:
        request.applymarker(pytest.mark.xfail(strict=True, reason=KNOWN_FAILURES[operation]))
    elif operation in MAY_FAIL:
        request.applymarker(pytest.mark.xfail(strict=False, reason=MAY_FAIL[operation]))

    response = case.call(base_url=api_base_url, headers=auth_headers, timeout=10)
    case.validate_response(response, checks=CHECKS)
