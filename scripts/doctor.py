#!/usr/bin/env python3
"""Self-check: is this machine and configuration ready to run the pipeline?

Run this first on a new machine, and again whenever something "just
stopped working". It prints one PASS / WARN / FAIL line per check and
exits 1 when any check FAILs, 0 otherwise.

Checks:
- Python version is 3.9 or newer.
- A real config/config.json exists (not just the fictional example),
  and the key fields (sender_name, sender_email, sender_company,
  product, target_markets) are filled with the operator's own values,
  not the example placeholders.
- Environment variables are present or absent (values are never
  printed): SMTP_HOST / SMTP_USER / SMTP_PASS, the Hunter keys variable
  named in config, and any one search key (SERPER / TAVILY / BRAVE).
- DNS works: an MX lookup for a well-known domain returns records
  (uses scripts/domain_check.py, so it exercises the same resolver
  discovery, including the Windows ipconfig path).
- The SMTP server answers a TCP connection and greeting. No login is
  attempted unless --smtp-login is given.
- Sender conflict: SMTP_FROM and the config sender_email both set and
  different is a WARN, with the address that will actually be used
  (resolution order: SMTP_FROM > config sender_email > SMTP_USER).

Usage:
    python3 doctor.py [--smtp-login]
"""
import argparse
import os
import socket
import sys

import _config

KEY_FIELDS = ("sender_name", "sender_email", "sender_company",
              "product", "target_markets")

_RESULTS = []


def report(level, label, detail=""):
    _RESULTS.append(level)
    line = f"[{level}] {label}"
    if detail:
        line += f" — {detail}"
    print(line)


def _example_values():
    import json
    path = os.path.join(_config.repo_root(), "config",
                        "config.example.json")
    try:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
    except (OSError, ValueError):
        pass
    return {}


def check_python():
    version = sys.version_info
    label = f"Python {version.major}.{version.minor}.{version.micro}"
    if version >= (3, 9):
        report("PASS", label)
    else:
        report("FAIL", label, "this pipeline needs Python 3.9 or newer")


def check_config():
    path = _config.config_path()
    cfg = _config.load()
    example = _example_values()
    if os.path.basename(path) == "config.example.json":
        report("FAIL", "config/config.json",
               "not found; scripts are running on the fictional example "
               "values. Run the onboarding interview "
               "(prompts/00-onboarding.md) first")
    else:
        report("PASS", "config/config.json", "found")
    for field in KEY_FIELDS:
        value = cfg.get(field)
        if not value:
            report("FAIL", f"config field {field}", "missing or empty")
        elif example.get(field) == value:
            report("FAIL", f"config field {field}",
                   "still holds the fictional example value; replace it "
                   "with your own")
        else:
            report("PASS", f"config field {field}", "set")


def check_env():
    for name in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS"):
        if os.environ.get(name):
            report("PASS", f"env {name}", "set")
        else:
            report("WARN", f"env {name}",
                   "not set; real sends will be refused until it is")
    hunter_env = _config.get("hunter_api_keys_env", "HUNTER_API_KEYS")
    if os.environ.get(hunter_env):
        report("PASS", f"env {hunter_env}", "set (Hunter keys)")
    else:
        report("WARN", f"env {hunter_env}",
               "not set; Hunter verification is unavailable")
    search_keys = [name for name in ("SERPER_API_KEY", "TAVILY_API_KEY",
                                     "BRAVE_API_KEY")
                   if os.environ.get(name)]
    if search_keys:
        report("PASS", "search key", f"{search_keys[0]} is set")
    else:
        report("WARN", "search key",
               "none of SERPER_API_KEY / TAVILY_API_KEY / BRAVE_API_KEY "
               "is set; the search layer will run in FALLBACK mode")


def check_dns():
    import domain_check
    try:
        records = domain_check.lookup_mx("gmail.com")
    except Exception as exc:  # noqa: BLE001 - report, never crash
        report("FAIL", "DNS MX lookup", f"error: {exc}")
        return
    if records:
        report("PASS", "DNS MX lookup",
               f"gmail.com -> {len(records)} MX record(s)")
    else:
        report("FAIL", "DNS MX lookup",
               "no MX records returned for gmail.com; outbound DNS "
               "(UDP 53) or the system resolver appears blocked, and "
               "domain_check will report domains as having no MX")


def check_smtp(login):
    host = os.environ.get("SMTP_HOST", "")
    if not host:
        report("WARN", "SMTP connectivity", "SMTP_HOST not set; skipped")
        return
    try:
        port = int(os.environ.get("SMTP_PORT", "587"))
    except ValueError:
        report("FAIL", "SMTP connectivity",
               f"SMTP_PORT is not a number: "
               f"{os.environ.get('SMTP_PORT')!r}")
        return
    import send_mail
    mode = send_mail.connection_mode(port)
    try:
        with socket.create_connection((host, port), timeout=10) as sock:
            banner = sock.recv(128).decode("utf-8", "replace").strip()
    except OSError as exc:
        report("FAIL", "SMTP connectivity",
               f"cannot connect to {host}:{port} ({mode}): {exc}")
        return
    if not banner.startswith("220"):
        report("WARN", "SMTP connectivity",
               f"{host}:{port} answered without a 220 greeting ({mode})")
        return
    report("PASS", "SMTP connectivity",
           f"{host}:{port} greeted ({mode})")
    if not login:
        return
    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASS", "")
    if not (user and password):
        report("WARN", "SMTP login",
               "SMTP_USER / SMTP_PASS not both set; login not attempted")
        return
    import smtplib
    try:
        if send_mail.use_ssl(port):
            with smtplib.SMTP_SSL(host, port, timeout=15) as smtp:
                smtp.login(user, password)
        else:
            with smtplib.SMTP(host, port, timeout=15) as smtp:
                smtp.starttls()
                smtp.login(user, password)
        report("PASS", "SMTP login", f"authenticated as {user}")
    except (OSError, smtplib.SMTPException) as exc:
        report("FAIL", "SMTP login", f"{exc} (connection mode: {mode})")


def check_sender_conflict():
    import send_mail
    smtp_from = os.environ.get("SMTP_FROM", "")
    config_sender = _config.get("sender_email", "") or ""
    if smtp_from and config_sender and smtp_from != config_sender:
        report("WARN", "sender address conflict",
               f"SMTP_FROM is {smtp_from} but config sender_email is "
               f"{config_sender}; sends will use SMTP_FROM "
               "(priority: SMTP_FROM > config sender_email > SMTP_USER)")
    else:
        effective = send_mail.resolve_sender(os.environ.get("SMTP_USER", ""))
        if effective:
            report("PASS", "sender address",
                   f"sends will go out as {effective}")
        else:
            report("WARN", "sender address",
                   "no From address resolvable yet (SMTP_FROM, config "
                   "sender_email, and SMTP_USER are all empty)")


def _guarded(fn, *args):
    """Run one check; a crashed check is a FAIL line, never a traceback."""
    try:
        fn(*args)
    except Exception as exc:  # noqa: BLE001 - report, never crash
        report("FAIL", fn.__name__, f"check raised an error: {exc}")


def main():
    parser = argparse.ArgumentParser(
        description="Self-check the machine, config, and credentials.")
    parser.add_argument("--smtp-login", action="store_true",
                        help="Also try an SMTP login (default: connect "
                             "and read the greeting only).")
    args = parser.parse_args()

    _guarded(check_python)
    _guarded(check_config)
    _guarded(check_env)
    _guarded(check_dns)
    _guarded(check_smtp, args.smtp_login)
    _guarded(check_sender_conflict)

    fails = _RESULTS.count("FAIL")
    warns = _RESULTS.count("WARN")
    passes = _RESULTS.count("PASS")
    print(f"\ndoctor: {passes} PASS, {warns} WARN, {fails} FAIL")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
