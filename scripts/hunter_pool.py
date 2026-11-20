#!/usr/bin/env python3
"""Hunter API key-rotation pool (generic).

Keys are read from the environment variable named by the HUNTER_KEYS_ENV
setting below, defaulting to HUNTER_API_KEYS, as a comma-separated list:

    export HUNTER_API_KEYS="key-one,key-two,key-three"

Behaviour:
- Calls use the first key in the list.
- When a key reports a quota, credit, or rate-limit failure (or an auth
  failure), it is marked exhausted for this process and the next key is
  tried, in list order.
- Key values are never printed. The CLI prints only result data and, for
  the account command, remaining-credit figures.

Usage as a module:
    from hunter_pool import call
    data = call("/email-verifier", {"email": "person@example.com"})

CLI:
    python3 hunter_pool.py account
    python3 hunter_pool.py verifier <email>
    python3 hunter_pool.py finder <first_name> <last_name> <domain>
"""
import json
import os
import sys
import urllib.parse
import urllib.request

BASE = "https://api.hunter.io/v2"
KEYS_ENV = os.environ.get("HUNTER_KEYS_ENV", "HUNTER_API_KEYS")
QUOTA_HINTS = ("quota", "credit", "limit exceeded", "too many requests", "429")

_exhausted = set()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse redirects so a key is never forwarded to another host."""

    def redirect_request(self, *args):
        raise RuntimeError("redirect refused")


def _load_keys():
    raw = os.environ.get(KEYS_ENV, "")
    return [k.strip() for k in raw.split(",") if k.strip()]


def _is_quota_error(exc):
    text = str(exc).lower()
    return any(hint in text for hint in QUOTA_HINTS)


def _direct_call(key, path, params):
    url = BASE + path + "?" + urllib.parse.urlencode({**params, "api_key": key})
    req = urllib.request.Request(url)
    with urllib.request.build_opener(NoRedirect()).open(req, timeout=30) as resp:
        return json.load(resp)


def call(path, params):
    """Call the Hunter API, rotating keys on quota or auth failure."""
    keys = [k for k in _load_keys() if k not in _exhausted]
    if not keys:
        raise RuntimeError(
            f"no usable keys: set {KEYS_ENV} to a comma-separated key list")
    last_exc = None
    for key in keys:
        try:
            return _direct_call(key, path, params)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if _is_quota_error(exc) or "401" in str(exc) or "403" in str(exc):
                _exhausted.add(key)
                continue
            raise
    if last_exc:
        raise last_exc
    raise RuntimeError("all Hunter keys exhausted")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "account"
    if cmd == "account":
        print(json.dumps(call("/account", {}).get("data", {}), ensure_ascii=False))
    elif cmd == "verifier" and len(sys.argv) == 3:
        print(json.dumps(
            call("/email-verifier", {"email": sys.argv[2]}).get("data", {}),
            ensure_ascii=False))
    elif cmd == "finder" and len(sys.argv) == 5:
        print(json.dumps(
            call("/email-finder", {"first_name": sys.argv[2],
                                   "last_name": sys.argv[3],
                                   "domain": sys.argv[4]}).get("data", {}),
            ensure_ascii=False))
    else:
        print(json.dumps({"error": "usage: account | verifier <email> | "
                                   "finder <first> <last> <domain>"}))
        sys.exit(2)
