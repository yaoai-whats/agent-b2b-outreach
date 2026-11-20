#!/usr/bin/env python3
"""Send gate-passed letters over SMTP, with the safety checks in code.

Credentials come from the environment only, never from files:
    SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASS, SMTP_FROM

Connection mode: port 465, or SMTP_USE_SSL=1/true in the environment,
means implicit TLS via smtplib.SMTP_SSL (the mode QQ Mail, 163 Mail, and
Aliyun Mail expect on their default port). Any other port uses plain
SMTP upgraded with STARTTLS. Send errors name the mode in use so a
wrong-mode failure is recognisable instead of a bare disconnect.

From address resolution order (first set value wins):
    1. the SMTP_FROM environment variable
    2. sender_email in the config file (see scripts/_config.py)
    3. SMTP_USER
scripts/doctor.py warns when SMTP_FROM and the config sender_email are
both set and differ, because the letters are then sent from a different
address than the one the config advertises.

Modes:
- Default is a dry run: every check runs, the letters that would be
  sent are printed, nothing leaves the machine.
- Add --send to actually send.

Input:
- Single letter (default): --lead <leads.jsonl> --line N builds the
  letter for that row with letter_builder.py logic (sender/product/
  value from config); or --letter-file <file> sends a letter file in
  the letter_builder output format ("To: ...", "Subject: ...", blank
  line, body), with recipient checks taken from --lead's matching row
  when a leads file is also given, else from --to-status.
- Batch (--batch, with --lead): every row whose email_status is
  sendable (optionally narrowed to one label with --to-status) is
  processed in file order: letter built, quality gate, then the same
  five checks per letter. Rows the exclusion check (check 2) would
  refuse are screened out before the loop, printed with their reason,
  and counted as "excluded" in the closing summary. Letters are spaced
  by --interval seconds (default 60) plus a random 0-30 second jitter
  (in a dry run the wait is reported, not slept). The run stops when
  the daily cap is reached (cap minus today's recorded sends, counting
  this run's sends) or when the bounce circuit breaker trips; the stop
  reason is printed.

Mandatory checks before any send (a failed check refuses the send and
says why; there is no override flag):
1. Recipient status: the lead row's email_status must be hunter_valid
   or public_confirmed. accept_all_unconfirmed, unverified, and invalid
   addresses are refused.
2. Exclusions: the recipient must not be excluded. Excluded means the
   address or its domain appears in config/blocklist.json; a cold
   email was already sent to this address or to this company (the
   send-state sent/followups records — this script is the cold path,
   follow-ups go through the tracker flow, never through here); or
   the feedback log records an unsubscribe or a bounce for this
   address.
3. Quality gate: the letter must pass scripts/quality_gate.py.
4. Daily cap: sends recorded in data/send-state.json for today (plus
   this run's sends) must be below daily_send_cap (see config).
5. Bounce circuit breaker: when data/outreach-feedback.json exists,
   refuse when today's bounces reach bounce_breaker_daily, or when the
   bounce rate among the most recent bounce_breaker_window sends
   reaches bounce_breaker_rate (thresholds from config).

Every message carries Date, Message-ID (domain taken from the From
address), Reply-To, and a mailto List-Unsubscribe header.

Every attempt, sent or dry-run, is appended to data/send-log.jsonl.
Real sends are also recorded in data/send-state.json ({"sent": [...]},
the shape scripts/build_tracker.py reads).
"""
import argparse
import json
import os
import random
import smtplib
import sys
import time
from datetime import datetime
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid

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


def default_blocklist_path():
    """The operator's blocklist: config/blocklist.json in the repo."""
    return os.path.join(_config.repo_root(), "config", "blocklist.json")


def load_blocklist(path):
    """Blocklist entries; a missing or malformed file means no entries."""
    data = _load_json(path, {"entries": []})
    if isinstance(data, dict):
        entries = data.get("entries", [])
        if isinstance(entries, list):
            return entries
    return []


def recipient_of(lead):
    """The address a letter to this lead row would go to.

    Mirrors letter_builder.build_email: useful_email first, then the
    first recorded email.
    """
    emails = lead.get("emails") or []
    return (lead.get("useful_email") or (emails[0] if emails else "") or "")


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


def resolve_sender(user=""):
    """From address: SMTP_FROM env > config sender_email > SMTP_USER."""
    return (os.environ.get("SMTP_FROM", "")
            or _config.get("sender_email", "")
            or user)


def use_ssl(port):
    """Implicit TLS when the port is 465 or SMTP_USE_SSL says so."""
    flag = os.environ.get("SMTP_USE_SSL", "").strip().lower()
    return flag in ("1", "true", "yes", "on") or int(port) == 465


def connection_mode(port):
    return "SMTP_SSL (implicit TLS)" if use_ssl(port) else "SMTP + STARTTLS"


def build_message(sender, to_addr, subject, body):
    """Assemble the message with the headers bulk senders are scored on."""
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg["Date"] = format_datetime(datetime.now().astimezone())
    domain = sender.rsplit("@", 1)[-1].strip() if "@" in sender else ""
    msg["Message-ID"] = make_msgid(domain=domain or None)
    msg["Reply-To"] = sender
    msg["List-Unsubscribe"] = f"<mailto:{sender}?subject=unsubscribe>"
    msg.set_content(body)
    return msg


def build_letter_for_lead(lead):
    """(to, subject, body) for one lead row via letter_builder logic.

    Raises ValueError (from letter_builder) when the row is not ready,
    e.g. it has no researched observation yet.
    """
    import letter_builder
    points = _config.get("value_points", [])
    value_point = None
    if points:
        value_point = points[letter_builder._variant_idx(lead, 3) % len(points)]
    return letter_builder.build_email(
        lead,
        _config.get("sender_name", ""),
        _config.get("sender_company", ""),
        _config.get("product", ""),
        value_point or "")


def _deliver(sender, to_addr, subject, body):
    """Send one assembled letter. Returns (ok, error_text)."""
    host = os.environ.get("SMTP_HOST", "")
    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASS", "")
    port = int(os.environ.get("SMTP_PORT", "587"))
    mode = connection_mode(port)
    msg = build_message(sender, to_addr, subject, body)
    try:
        if use_ssl(port):
            with smtplib.SMTP_SSL(host, port, timeout=30) as smtp:
                smtp.login(user, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=30) as smtp:
                smtp.starttls()
                smtp.login(user, password)
                smtp.send_message(msg)
    except (OSError, smtplib.SMTPException) as exc:
        return False, (f"{exc} (connection mode: {mode}, server "
                       f"{host}:{port}; if the server closed the "
                       "connection immediately, the mode is usually "
                       "wrong: port 465 expects implicit TLS, port 587 "
                       "expects STARTTLS)")
    return True, ""


class Sender:
    """Runs the five mandatory checks and one send attempt per letter.

    Shared by single-letter and batch modes so both enforce identical
    rules. `extra_today` counts letters already sent (or dry-run
    approved) earlier in this run, so a batch cannot walk past the
    daily cap on state that only updates on disk between runs.
    """

    def __init__(self, state, state_path, log_path, feedback_path, send,
                 blocklist_path=None):
        self.state = state
        self.state_path = state_path
        self.log_path = log_path
        self.feedback_path = feedback_path
        self.send = send
        self.extra_today = 0
        self.blocklist_path = blocklist_path or default_blocklist_path()
        self.blocklist_entries = load_blocklist(self.blocklist_path)
        feedback = _load_json(feedback_path, {"entries": []})
        self.feedback_entries = (feedback.get("entries", [])
                                 if isinstance(feedback, dict) else [])

    def exclusion_reason(self, to_addr, company):
        """Why this recipient is excluded, or None when they are clear.

        The three sources, in order: config/blocklist.json (address or
        domain), the send-state records (this cold path never re-sends
        to an address or company it already contacted), and the
        feedback log (unsubscribe or bounce for this address).
        """
        addr = (to_addr or "").strip().lower()
        domain = addr.rsplit("@", 1)[-1] if "@" in addr else ""
        for entry in self.blocklist_entries:
            entry_email = (entry.get("email") or "").strip().lower()
            entry_domain = (entry.get("domain") or "").strip().lower()
            if addr and entry_email == addr:
                return (f"blocklist: {addr} is listed in "
                        f"config/blocklist.json (reason: "
                        f"{entry.get('reason', 'unspecified')}, added "
                        f"{entry.get('added_at', 'unknown date')})")
            if domain and entry_domain == domain:
                return (f"blocklist: domain {domain} is listed in "
                        f"config/blocklist.json (reason: "
                        f"{entry.get('reason', 'unspecified')}, added "
                        f"{entry.get('added_at', 'unknown date')})")
        records = (self.state.get("sent", [])
                   + self.state.get("followups", []))
        for record in records:
            sent_to = (record.get("to") or "").strip().lower()
            when = str(record.get("sent_at", ""))[:10] or "unknown date"
            if addr and sent_to == addr:
                return (f"already contacted: a cold email was already "
                        f"sent to {addr} on {when}; follow-ups go "
                        "through the tracker flow, not this script")
            if company and record.get("company") == company:
                return (f"already contacted: {company} already has a "
                        f"send record on {when} (to {sent_to or '?'})")
        for entry in self.feedback_entries:
            if (entry.get("email") or "").strip().lower() != addr or not addr:
                continue
            if entry.get("type") == "unsubscribe":
                return (f"unsubscribed: {addr} asked to unsubscribe on "
                        f"{entry.get('date', 'unknown date')}; never "
                        "contact this address again")
            if entry.get("type") == "bounce":
                return (f"previously bounced: mail to {addr} bounced "
                        f"on {entry.get('date', 'unknown date')}")
        return None

    def _log(self, company, to_addr, subject, outcome, reason=""):
        _append_jsonl(self.log_path, {
            "at": datetime.now().isoformat(timespec="seconds"),
            "mode": "send" if self.send else "dry-run",
            "outcome": outcome, "reason": reason,
            "company": company, "to": to_addr, "subject": subject})

    def attempt(self, to_addr, subject, body, status, company, gate_name):
        """Process one letter.

        Returns (outcome, reason, stop): outcome is "sent", "would_send",
        "refused", or "error"; stop is True when the run must halt (daily
        cap reached or bounce breaker tripped).
        """
        # Check 1: recipient verification status.
        if status not in SENDABLE_STATUSES:
            reason = (f"recipient status is {status!r}; only hunter_valid "
                      "or public_confirmed addresses may be sent to")
            self._log(company, to_addr, subject, "refused", reason)
            return "refused", reason, False

        # Check 2: exclusions (blocklist, already contacted,
        # unsubscribed, previously bounced).
        excluded = self.exclusion_reason(to_addr, company)
        if excluded:
            self._log(company, to_addr, subject, "refused", excluded)
            return "refused", excluded, False

        # Check 3: quality gate.
        import quality_gate
        failures = quality_gate.check_email(gate_name, subject, body)
        if failures:
            reason = "quality gate failed: " + "; ".join(failures)
            self._log(company, to_addr, subject, "refused", reason)
            return "refused", reason, False

        # Check 4: daily cap (recorded sends + this run's sends).
        cap = _config.get("daily_send_cap", 30)
        sent_today = sum(1 for e in self.state.get("sent", [])
                         if str(e.get("sent_at", "")).startswith(_today()))
        sent_today += self.extra_today
        if sent_today >= cap:
            reason = f"daily send cap reached ({sent_today}/{cap} today)"
            self._log(company, to_addr, subject, "refused", reason)
            return "refused", reason, True

        # Check 5: bounce circuit breaker.
        breaker = check_breaker(self.feedback_path, self.state)
        if breaker:
            self._log(company, to_addr, subject, "refused", breaker)
            return "refused", breaker, True

        if not self.send:
            self.extra_today += 1
            self._log(company, to_addr, subject, "would_send")
            return "would_send", "", False

        user = os.environ.get("SMTP_USER", "")
        sender = resolve_sender(user)
        host = os.environ.get("SMTP_HOST", "")
        password = os.environ.get("SMTP_PASS", "")
        if not (host and user and password and sender):
            reason = ("missing SMTP credentials in the environment "
                      "(SMTP_HOST, SMTP_USER, SMTP_PASS, and a From "
                      "address via SMTP_FROM, config sender_email, or "
                      "SMTP_USER)")
            self._log(company, to_addr, subject, "refused", reason)
            return "refused", reason, False
        ok, error = _deliver(sender, to_addr, subject, body)
        if not ok:
            self._log(company, to_addr, subject, "error", error)
            return "error", error, False
        self.state.setdefault("sent", []).append({
            "company": company, "to": to_addr,
            "sent_at": datetime.now().isoformat(timespec="seconds"),
            "subject": subject})
        with open(self.state_path, "w", encoding="utf-8") as fh:
            json.dump(self.state, fh, ensure_ascii=False, indent=2)
        self.extra_today += 1
        self._log(company, to_addr, subject, "sent")
        return "sent", "", False


def _missing_creds_note():
    missing = [name for name in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS")
               if not os.environ.get(name)]
    if missing:
        print("NOTE: SMTP credentials not set ("
              + ", ".join(missing)
              + "); a real --send would be refused until they are "
                "provided in the environment.")


def main():
    parser = argparse.ArgumentParser(
        description="Send letters with status, exclusion, gate, cap, "
                    "and breaker checks.")
    parser.add_argument("--lead", default=None, help="Path to a leads .jsonl file.")
    parser.add_argument("--line", type=int, default=1,
                        help="1-based lead row (single mode, with --lead).")
    parser.add_argument("--letter-file", default=None,
                        help="Letter file in letter_builder output format "
                             "(single mode).")
    parser.add_argument("--to-status", default=None,
                        help="Verification label of the recipient (with "
                             "--letter-file and no matching lead row). In "
                             "--batch mode: only process rows carrying "
                             "exactly this label.")
    parser.add_argument("--batch", action="store_true",
                        help="Process every sendable row in --lead "
                             "instead of a single row.")
    parser.add_argument("--interval", type=float, default=60,
                        help="Seconds between batch letters, plus a "
                             "random 0-30s jitter (default 60).")
    parser.add_argument("--send", action="store_true",
                        help="Actually send. Without this flag: dry run.")
    args = parser.parse_args()

    state_path = _config.data_path("send-state.json")
    log_path = _config.data_path("send-log.jsonl")
    feedback_path = _config.data_path("outreach-feedback.json")
    state = _load_json(state_path, {"sent": []})
    sender = Sender(state, state_path, log_path, feedback_path, args.send)

    if args.batch:
        if not args.lead:
            parser.error("--batch requires --lead <leads.jsonl>")
        with open(args.lead, encoding="utf-8") as fh:
            rows = [json.loads(line) for line in fh if line.strip()]
        eligible = []
        for row in rows:
            status = row.get("email_status")
            if status not in SENDABLE_STATUSES:
                continue
            if args.to_status and status != args.to_status:
                continue
            eligible.append(row)
        print(f"BATCH {'SEND' if args.send else 'DRY RUN'}: "
              f"{len(eligible)} sendable row(s) in {args.lead}"
              + (f" with status {args.to_status}" if args.to_status else ""))
        if not args.send:
            print(f"From: {resolve_sender(os.environ.get('SMTP_USER', ''))}")
            _missing_creds_note()
        counts = {"sent": 0, "would_send": 0, "refused": 0, "error": 0,
                  "skipped": 0, "excluded": 0}
        # Exclusion prescreen (check 2): rows the exclusion check
        # would refuse are named here with their reason and counted,
        # instead of being refused silently inside the send loop.
        # attempt() still re-checks every letter that does go through.
        sendable = []
        for row in eligible:
            reason = sender.exclusion_reason(recipient_of(row),
                                             row.get("company", ""))
            if reason:
                counts["excluded"] += 1
                print(f"EXCLUDED {row.get('company', '')}: {reason}")
            else:
                sendable.append(row)
        eligible = sendable
        stop_reason = ""
        for idx, lead in enumerate(eligible):
            company = lead.get("company", "")
            try:
                to_addr, subject, body = build_letter_for_lead(lead)
            except ValueError as exc:
                counts["skipped"] += 1
                print(f"SKIP {company}: {exc}")
                continue
            import letter_builder
            gate_name = letter_builder.extract_name(lead.get("contact", ""))
            outcome, reason, stop = sender.attempt(
                to_addr, subject, body, lead.get("email_status"),
                company, gate_name)
            counts[outcome] += 1
            if outcome in ("sent", "would_send"):
                print(f"{'SENT' if outcome == 'sent' else 'WOULD SEND'}: "
                      f"{to_addr} ({company})")
            else:
                print(f"{outcome.upper()}: {company}: {reason}")
            if stop:
                stop_reason = reason
                break
            if idx < len(eligible) - 1:
                delay = args.interval + random.uniform(0, 30)
                if args.send:
                    time.sleep(delay)
                else:
                    print(f"(dry run: would wait {delay:.0f}s before "
                          "the next letter)")
        print(json.dumps({"batch": counts, "stopped": stop_reason or None},
                         ensure_ascii=False))
        return 1 if counts["error"] else 0

    # Single-letter mode.
    lead = None
    if args.lead:
        with open(args.lead, encoding="utf-8") as fh:
            rows = [json.loads(line) for line in fh if line.strip()]
        lead = rows[args.line - 1]

    if args.letter_file:
        to_addr, subject, body = parse_letter_file(args.letter_file)
        if lead is not None:
            status = lead.get("email_status")
            company = lead.get("company", "")
        else:
            status = args.to_status
            company = ""
    elif lead is not None:
        try:
            to_addr, subject, body = build_letter_for_lead(lead)
        except ValueError as exc:
            print(f"REFUSED: {exc}")
            return 2
        status = lead.get("email_status")
        company = lead.get("company", "")
    else:
        parser.error("give --lead (with --line) or --letter-file")

    gate_name = ""
    if lead is not None:
        import letter_builder
        gate_name = letter_builder.extract_name(lead.get("contact", ""))

    outcome, reason, _stop = sender.attempt(
        to_addr, subject, body, status, company, gate_name)
    if outcome == "would_send":
        _missing_creds_note()
        print("DRY RUN (nothing sent). Would send:")
        print(f"From: {resolve_sender(os.environ.get('SMTP_USER', ''))}")
        print(f"To: {to_addr}")
        print(f"Subject: {subject}")
        print()
        print(body)
        return 0
    if outcome == "sent":
        print(f"SENT: {to_addr} ({company})")
        return 0
    if outcome == "error":
        print(f"SEND ERROR: {reason}")
        return 1
    print(f"REFUSED: {reason}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
