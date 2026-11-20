#!/usr/bin/env python3
"""Send one gate-passed letter over SMTP, with the safety checks in code.

Credentials come from the environment only, never from files:
    SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASS, SMTP_FROM

Modes:
- Default is a dry run: every check runs, the letter that would be sent
  is printed, nothing leaves the machine.
- Add --send to actually send.

Input, one of:
- --lead <leads.jsonl> --line N: build the letter for that row with
  letter_builder.py logic (sender/product/value from config).
- --letter-file <file>: a letter file in the letter_builder output
  format ("To: ...", "Subject: ...", blank line, body). With this mode
  the recipient checks use the To address against --lead rows when a
  leads file is also given; without one, pass --to-status with the
  recipient's verification label.

Mandatory checks before any send (a failed check refuses the send and
says why; there is no override flag):
1. Recipient status: the lead row's email_status must be hunter_valid
   or public_confirmed. accept_all_unconfirmed, unverified, and invalid
   addresses are refused.
2. Quality gate: the letter must pass scripts/quality_gate.py.
3. Daily cap: sends recorded in data/send-state.json for today must be
   below daily_send_cap (see config).
4. Bounce circuit breaker: when data/outreach-feedback.json exists,
   refuse when today's bounces reach bounce_breaker_daily, or when the
   bounce rate among the most recent bounce_breaker_window sends
   reaches bounce_breaker_rate (thresholds from config).

Every attempt, sent or dry-run, is appended to data/send-log.jsonl.
Real sends are also recorded in data/send-state.json ({"sent": [...]},
the shape scripts/build_tracker.py reads).
"""
import argparse
import json
import os
import smtplib
import sys
from datetime import datetime
from email.message import EmailMessage

import _config

SENDABLE_STATUSES = ("hunter_valid", "public_confirmed")


def _today():
    return datetime.now().strftime("%Y-%m-%d")


def _load_json(path, default):
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return default


def _append_jsonl(path, entry):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def parse_letter_file(path):
    """Parse letter_builder output: To / Subject headers, blank, body."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    to_addr, subject, body_lines = "", "", []
    in_body = False
    for line in text.splitlines():
        if in_body:
            body_lines.append(line)
        elif line.startswith("To: "):
            to_addr = line[4:].strip()
        elif line.startswith("Subject: "):
            subject = line[9:].strip()
        elif line.strip() == "":
            in_body = True
    return to_addr, subject, "\n".join(body_lines).strip("\n")


def check_breaker(feedback_path, state):
    """Return a refusal reason when the bounce breaker is tripped."""
    feedback = _load_json(feedback_path, {"entries": []})
    entries = feedback.get("entries", [])
    daily_limit = _config.get("bounce_breaker_daily", 3)
    rate_limit = _config.get("bounce_breaker_rate", 0.15)
    window = _config.get("bounce_breaker_window", 20)
    today_bounces = sum(1 for e in entries
                        if e.get("type") == "bounce" and e.get("date") == _today())
    if today_bounces >= daily_limit:
        return (f"bounce circuit breaker: {today_bounces} bounces today "
                f"(limit {daily_limit}); sending is stopped until a human "
                "investigates")
    sent = state.get("sent", [])
    if sent:
        recent = sent[-window:]
        recent_companies = {e.get("company") for e in recent}
        recent_bounces = sum(1 for e in entries
                             if e.get("type") == "bounce"
                             and e.get("company") in recent_companies)
        rate = recent_bounces / len(recent)
        if rate >= rate_limit:
            return (f"bounce circuit breaker: {recent_bounces} of the last "
                    f"{len(recent)} sends bounced ({rate:.0%}, limit "
                    f"{rate_limit:.0%}); sending is stopped")
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Send one letter with status, cap, and breaker checks.")
    parser.add_argument("--lead", default=None, help="Path to a leads .jsonl file.")
    parser.add_argument("--line", type=int, default=1,
                        help="1-based lead row (with --lead).")
    parser.add_argument("--letter-file", default=None,
                        help="Letter file in letter_builder output format.")
    parser.add_argument("--to-status", default=None,
                        help="Verification label of the recipient (only with "
                             "--letter-file and no matching lead row).")
    parser.add_argument("--send", action="store_true",
                        help="Actually send. Without this flag: dry run.")
    args = parser.parse_args()

    state_path = _config.data_path("send-state.json")
    log_path = _config.data_path("send-log.jsonl")
    feedback_path = _config.data_path("outreach-feedback.json")
    state = _load_json(state_path, {"sent": []})

    lead = None
    if args.lead:
        with open(args.lead, encoding="utf-8") as fh:
            rows = [json.loads(line) for line in fh if line.strip()]
        lead = rows[args.line - 1]

    if args.letter_file:
        to_addr, subject, body = parse_letter_file(args.letter_file)
        status = None
        if lead is not None:
            status = lead.get("email_status")
            company = lead.get("company", "")
        else:
            status = args.to_status
            company = ""
    elif lead is not None:
        import letter_builder
        try:
            points = _config.get("value_points", [])
            value_point = None
            if points:
                value_point = points[
                    letter_builder._variant_idx(lead, 3) % len(points)]
            to_addr, subject, body = letter_builder.build_email(
                lead,
                _config.get("sender_name", ""),
                _config.get("sender_company", ""),
                _config.get("product", ""),
                value_point or "")
        except ValueError as exc:
            print(f"REFUSED: {exc}")
            return 2
        status = lead.get("email_status")
        company = lead.get("company", "")
    else:
        parser.error("give --lead (with --line) or --letter-file")

    def log(mode, outcome, reason=""):
        _append_jsonl(log_path, {
            "at": datetime.now().isoformat(timespec="seconds"),
            "mode": mode, "outcome": outcome, "reason": reason,
            "company": company, "to": to_addr, "subject": subject})

    # Check 1: recipient verification status.
    if status not in SENDABLE_STATUSES:
        reason = (f"recipient status is {status!r}; only hunter_valid or "
                  "public_confirmed addresses may be sent to")
        log("send" if args.send else "dry-run", "refused", reason)
        print(f"REFUSED: {reason}")
        return 1

    # Check 2: quality gate.
    import quality_gate
    name = ""
    if lead is not None:
        import letter_builder
        name = letter_builder.extract_name(lead.get("contact", ""))
    failures = quality_gate.check_email(name, subject, body)
    if failures:
        reason = "quality gate failed: " + "; ".join(failures)
        log("send" if args.send else "dry-run", "refused", reason)
        print(f"REFUSED: {reason}")
        return 1

    # Check 3: daily cap.
    cap = _config.get("daily_send_cap", 30)
    sent_today = sum(1 for e in state.get("sent", [])
                     if str(e.get("sent_at", "")).startswith(_today()))
    if sent_today >= cap:
        reason = f"daily send cap reached ({sent_today}/{cap} today)"
        log("send" if args.send else "dry-run", "refused", reason)
        print(f"REFUSED: {reason}")
        return 1

    # Check 4: bounce circuit breaker.
    breaker = check_breaker(feedback_path, state)
    if breaker:
        log("send" if args.send else "dry-run", "refused", breaker)
        print(f"REFUSED: {breaker}")
        return 1

    if not args.send:
        log("dry-run", "would_send")
        missing_creds = [name for name in ("SMTP_HOST", "SMTP_USER",
                                           "SMTP_PASS")
                         if not os.environ.get(name)]
        if missing_creds:
            print("NOTE: SMTP credentials not set ("
                  + ", ".join(missing_creds)
                  + "); a real --send would be refused until they are "
                    "provided in the environment.")
        print("DRY RUN (nothing sent). Would send:")
        print(f"To: {to_addr}")
        print(f"Subject: {subject}")
        print()
        print(body)
        return 0

    # Real send: credentials from the environment only.
    host = os.environ.get("SMTP_HOST", "")
    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASS", "")
    sender = os.environ.get("SMTP_FROM", "") or user
    port = int(os.environ.get("SMTP_PORT", "587"))
    if not (host and user and password and sender):
        reason = ("missing SMTP credentials in the environment "
                  "(SMTP_HOST, SMTP_USER, SMTP_PASS, SMTP_FROM)")
        log("send", "refused", reason)
        print(f"REFUSED: {reason}")
        return 1
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(user, password)
            smtp.send_message(msg)
    except (OSError, smtplib.SMTPException) as exc:
        log("send", "error", str(exc))
        print(f"SEND ERROR: {exc}")
        return 1
    state.setdefault("sent", []).append({
        "company": company, "to": to_addr,
        "sent_at": datetime.now().isoformat(timespec="seconds"),
        "subject": subject})
    with open(state_path, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)
    log("send", "sent")
    print(f"SENT: {to_addr} ({company})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
