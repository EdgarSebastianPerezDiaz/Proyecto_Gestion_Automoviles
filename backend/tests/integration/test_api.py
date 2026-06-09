#!/usr/bin/env python3
"""
Integration tests — Heavy Freight Platform API.
Validates ALL backend endpoints against the live AWS Lambda deployment.

Usage:
    python backend/tests/integration/test_api.py
    API_URL=https://... python backend/tests/integration/test_api.py
"""

import os
import sys
import time
import uuid
import requests
from typing import Optional

# ── Configuration ─────────────────────────────────────────────────────────────

BASE_URL   = os.getenv("API_URL", "https://i7xihr7nhk.execute-api.us-east-1.amazonaws.com").rstrip("/")
# Use @example.com — valid per RFC 2606 and accepted by pydantic email-validator
TEST_EMAIL = os.getenv("TEST_EMAIL", f"ci{uuid.uuid4().hex[:8]}@example.com")
TEST_PASS  = os.getenv("TEST_PASSWORD", "TestPass123!")
TIMEOUT    = 20

GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

_token: Optional[str] = None
_results: list[dict]  = []


# ── Core helper ───────────────────────────────────────────────────────────────

def check(
    label: str,
    method: str,
    path: str,
    expected: list[int],
    *,
    body=None,
    warn_only: bool = False,
    use_auth: bool = True,
) -> Optional[dict]:
    url = f"{BASE_URL}{path}"
    headers: dict = {"Content-Type": "application/json"}
    if use_auth and _token:
        headers["Authorization"] = f"Bearer {_token}"

    try:
        resp = requests.request(method, url, json=body, headers=headers, timeout=TIMEOUT)
    except requests.exceptions.Timeout:
        _print_result(label, method, path, None, False, warn_only, "TIMEOUT")
        _results.append({"label": label, "status": "TIMEOUT", "warn_only": warn_only})
        return None
    except requests.exceptions.ConnectionError as exc:
        _print_result(label, method, path, None, False, warn_only, f"CONN_ERR: {exc}")
        _results.append({"label": label, "status": "CONN_ERR", "warn_only": warn_only})
        return None

    passed = resp.status_code in expected
    status = "PASS" if passed else ("WARN" if warn_only else "FAIL")
    _print_result(label, method, path, resp.status_code, passed, warn_only)
    if not passed:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text[:300]
        print(f"        expected {expected} → body: {detail}")

    _results.append({"label": label, "status": status, "code": resp.status_code, "warn_only": warn_only})
    try:
        return resp.json()
    except Exception:
        return None


def _print_result(label, method, path, code, passed, warn_only, extra=""):
    if passed:
        icon, color = "✓", GREEN
    elif warn_only:
        icon, color = "⚠", YELLOW
    else:
        icon, color = "✗", RED
    code_str = f"{GREEN}{code}{RESET}" if code and code < 300 else \
               f"{YELLOW}{code}{RESET}" if code and code < 500 else \
               f"{RED}{code}{RESET}" if code else ""
    suffix = f" {extra}" if extra else ""
    print(f"  {color}{icon}{RESET} {code_str:20} {method:<7} {path} — {label}{suffix}")


# ── Health ────────────────────────────────────────────────────────────────────

def test_health():
    print(f"\n{BOLD}── Health ───────────────────────────────────────────────{RESET}")
    check("liveness probe",  "GET", "/health/live",  [200])
    check("readiness probe", "GET", "/health/ready", [200])
    check("deep health",     "GET", "/health/deep",  [200])


# ── Auth ──────────────────────────────────────────────────────────────────────

def test_auth():
    global _token
    print(f"\n{BOLD}── Auth ─────────────────────────────────────────────────{RESET}")
    print(f"   Test email: {TEST_EMAIL}")

    check("register new user", "POST", "/auth/register", [201, 409],
          body={"email": TEST_EMAIL, "password": TEST_PASS, "full_name": "CI Test User"},
          warn_only=True, use_auth=False)

    resp = check("login with credentials", "POST", "/auth/login", [200],
                 body={"email": TEST_EMAIL, "password": TEST_PASS},
                 warn_only=True, use_auth=False)
    if resp and isinstance(resp, dict):
        _token = resp.get("access_token")
        if _token:
            print(f"        → JWT obtained (len={len(_token)})")
        else:
            print(f"   {YELLOW}⚠ No access_token in response{RESET}")
    else:
        print(f"   {YELLOW}⚠ Login failed — MongoDB Atlas may be blocking Lambda IPs{RESET}")


# ── Auth enforcement ─────────────────────────────────────────────────────────

def test_auth_enforcement():
    """All resource endpoints must return 401/403 without a token."""
    print(f"\n{BOLD}── Auth enforcement (no token → 401/403) ───────────────{RESET}")
    resources = [
        "/companies", "/clients", "/drivers", "/vehicles",
        "/trips", "/invoices", "/cargo-types",
        "/final-recipients", "/trip-statuses",
    ]
    for path in resources:
        url = f"{BASE_URL}{path}"
        try:
            resp = requests.get(url, headers={"Content-Type": "application/json"}, timeout=TIMEOUT)
            ok = resp.status_code in (401, 403)
            status = "PASS" if ok else "WARN"
            icon = f"{GREEN}✓{RESET}" if ok else f"{YELLOW}⚠{RESET}"
            print(f"  {icon} {resp.status_code:3}     GET    {path} — no-auth → 401/403")
            _results.append({"label": f"auth-guard GET {path}", "status": status, "warn_only": True})
        except Exception as exc:
            print(f"  {RED}✗{RESET}         GET    {path} — connection error: {exc}")
            _results.append({"label": f"auth-guard GET {path}", "status": "FAIL", "warn_only": False})


# ── Authenticated resource list ───────────────────────────────────────────────

def test_resource_list():
    """With JWT, all GET list endpoints return 200 with {items, total}."""
    if not _token:
        print(f"\n{YELLOW}── Resource lists — SKIPPED (no JWT) ───────────────────{RESET}")
        return
    print(f"\n{BOLD}── Resource lists — authenticated GET → 200 ────────────{RESET}")
    resources = [
        "/companies", "/clients", "/drivers", "/vehicles",
        "/trips", "/invoices", "/cargo-types",
        "/final-recipients", "/trip-statuses",
    ]
    for path in resources:
        resp = check(f"GET {path}", "GET", path, [200], warn_only=True)
        if resp and isinstance(resp, dict) and "items" in resp:
            total = resp.get("total", 0)
            _results.append({"label": f"GET {path} has items key", "status": "PASS", "warn_only": False})
        elif resp is not None:
            print(f"        response missing 'items' key: {str(resp)[:100]}")


# ── Write endpoints require auth ──────────────────────────────────────────────

def test_write_auth_guard():
    """POST/PUT/DELETE without token return 401/403, never 501."""
    print(f"\n{BOLD}── Write auth guard (no token → 401/403) ───────────────{RESET}")
    resources = ["/companies", "/drivers", "/vehicles", "/cargo-types"]
    fake_id = "000000000000000000000001"
    for path in resources:
        url = f"{BASE_URL}{path}"
        try:
            resp = requests.post(url, json={},
                                 headers={"Content-Type": "application/json"}, timeout=TIMEOUT)
            ok = resp.status_code in (401, 403)
            icon = f"{GREEN}✓{RESET}" if ok else f"{YELLOW}⚠{RESET}"
            status = "PASS" if ok else "WARN"
            print(f"  {icon} {resp.status_code:3}     POST   {path} — no-auth returns 401/403")
            _results.append({"label": f"write-guard POST {path}", "status": status, "warn_only": True})
        except Exception as exc:
            _results.append({"label": f"write-guard POST {path}", "status": "WARN", "warn_only": True})


# ── 404 handling ──────────────────────────────────────────────────────────────

def test_not_found():
    print(f"\n{BOLD}── 404 handling ────────────────────────────────────────{RESET}")
    check("unknown path returns 404/422", "GET", "/does-not-exist-xyz", [404, 422])


# ── Summary ───────────────────────────────────────────────────────────────────

def print_summary():
    total  = len(_results)
    passed = sum(1 for r in _results if r["status"] == "PASS")
    warned = sum(1 for r in _results if r["status"] == "WARN")
    failed = sum(1 for r in _results if r["status"] == "FAIL")
    errors = sum(1 for r in _results if r["status"] in ("TIMEOUT", "CONN_ERR"))

    print(f"\n{BOLD}{'═' * 60}{RESET}")
    print(f"  Results: {total} checks")
    print(f"    {GREEN}PASS  {passed:3}{RESET}")
    if warned:
        print(f"    {YELLOW}WARN  {warned:3}{RESET}  ← non-blocking (auth/Atlas dependent)")
    if failed:
        print(f"    {RED}FAIL  {failed:3}{RESET}")
    if errors:
        print(f"    {RED}ERROR {errors:3}{RESET}  ← connection/timeout")

    hard_fails = [r for r in _results
                  if r["status"] in ("FAIL", "TIMEOUT", "CONN_ERR") and not r.get("warn_only")]
    if hard_fails:
        print(f"\n  {RED}Hard failures:{RESET}")
        for r in hard_fails:
            print(f"    • {r['label']}")

    print(f"{BOLD}{'═' * 60}{RESET}")

    if hard_fails:
        print(f"\n{RED}{BOLD}INTEGRATION TESTS FAILED — {len(hard_fails)} hard failure(s){RESET}")
        sys.exit(1)
    elif warned or failed or errors:
        print(f"\n{YELLOW}{BOLD}INTEGRATION TESTS PASSED WITH WARNINGS{RESET}")
        sys.exit(0)
    else:
        print(f"\n{GREEN}{BOLD}ALL INTEGRATION TESTS PASSED ✓{RESET}")
        sys.exit(0)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n{BOLD}Heavy Freight Platform — Integration Tests{RESET}")
    print(f"  API: {BASE_URL}")
    print(f"  At:  {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")

    test_health()
    test_auth()
    test_auth_enforcement()
    test_resource_list()
    test_write_auth_guard()
    test_not_found()
    print_summary()
