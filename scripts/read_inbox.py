#!/usr/bin/env python3
"""Read the sending mailbox over IMAP and classify what arrived.

Credentials come from the environment only:
    IMAP_HOST, IMAP_USER, IMAP_PASS  (optional IMAP_PORT, default 993)

The mailbox is opened READ-ONLY (no message is deleted, moved, or
flagged) and the most recent N messages are fetched (--limit, default
50). Each message is classified:

- bounce:      a real delivery failure, judged conservatively because a
               false bounce feeds the sending circuit breaker. A message
               counts as a bounce only when the sender is a
               mailer-daemon / postmaster address, OR the message is a
               standard delivery status notification (multipart/report
               with report-type=delivery-status, or a
               message/delivery-status part), OR the subject carries a
               strong bounce phrase (undeliverable, delivery has failed,
               returned mail, ...). Ordinary business subjects that merely
               contain the words "delivery" or "failure" (a delivery
               schedule, a failure-rate question) are replies, not
               bounces.
- unsubscribe: the subject or the body asks to unsubscribe or stop
               contact (unsubscribe / remove me / do not contact /
               opt out). The subject counts because the mailto
               List-Unsubscribe header scripts/send_mail.py emits
               produces exactly that shape when a recipient clicks it:
               subject "unsubscribe", empty body.
- reply:       everything else.

Bounce entries are attributed to the address that actually failed,
never to the daemon that reported it: the per-recipient blocks of the
message/delivery-status part name the failed recipient in
Final-Recipient (Original-Recipient as fallback), and that address —
matched against the lead rows like any sender — becomes the entry's
email, so scripts/send_mail.py later refuses that exact address as
previously bounced and the breaker math sees the right company. One
entry is written per failed recipient. A recipient block whose
Action is "delayed" is recorded with type "delayed" instead of
"bounce": a delay is a soft failure, and recording it as a bounce
would refuse a live address forever and feed the circuit breaker.
Success receipts (delivered / relayed / expanded) are not recorded.
When no recipient can be parsed out of a bounce, the entry falls back
to the sender address with an empty company, and Stage 4's human
matching (prompts/04-inbox.md) takes it from there.

Classified entries are appended to data/outreach-feedback.json in that
file's existing shape ({"entries": [{"company", "date", "email",
"type", "summary"}]}, the shape scripts/build_tracker.py reads).
Company matching uses the sender address against the emails recorded
on lead rows in data/leads.jsonl when that file exists; unmatched
messages are recorded with an empty company so a human can match them.
Messages already recorded (same sender, subject, and date) are skipped,
so re-running the script does not duplicate entries.

Unsubscribe senders are also appended to config/blocklist.json
automatically (address and domain, reason "unsubscribe"), which
closes the loop: scripts/send_mail.py refuses blocklisted recipients,
so an unsubscribed address is never mailed again. A failed blocklist
write only prints a warning; it never aborts the inbox run. Bounce
addresses are NOT auto-blocklisted: the sending side already refuses
them by reading the feedback log, and the blocklist stays a
human-curated list plus confirmed unsubscribes.
"""
import argparse
import email
import email.policy
import imaplib
import json
import os
import re
import sys
from datetime import datetime

import _config

BOUNCE_SENDERS = ("mailer-daemon", "postmaster", "mail-daemon")
# Strong bounce phrases only. Bare words like "delivery" or "failure" must
# never appear here: real buyers write subjects such as "Re: delivery
# schedule for 500 sets" or "Re: LED tube failure rate", and a false bounce
# both loses the buyer and feeds the sending circuit breaker.
BOUNCE_SUBJECTS = ("undeliverable", "delivery has failed",
                   "mail delivery failed", "returned mail",
                   "undelivered mail", "delivery status notification")
UNSUB_WORDS = ("unsubscribe", "remove me", "do not contact",
               "don't contact", "stop emailing", "opt out", "opt-out")


def _decode(value):
    if not value:
        return ""
    try:
        return str(email.header.make_header(email.header.decode_header(value)))
    except Exception:  # noqa: BLE001
        return str(value)


def _body_text(msg):
    try:
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        return payload.decode(
                            part.get_content_charset() or "utf-8", "replace")
            return ""
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode(msg.get_content_charset() or "utf-8",
                                  "replace")
        return str(msg.get_payload() or "")
    except Exception:  # noqa: BLE001
        return ""


def _is_dsn(msg):
    """True when the message is a standard delivery status notification.

    Either the top-level content type is multipart/report with
    report-type=delivery-status, or some part is message/delivery-status.
    """
    try:
        if msg.get_content_type() == "multipart/report" and \
                (msg.get_param("report-type") or "").lower() == \
                "delivery-status":
            return True
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "message/delivery-status":
                    return True
    except Exception:  # noqa: BLE001 - a malformed message is not a DSN
        return False
    return False


def classify(from_addr, subject, body, is_dsn=False):
    """Classify one message as "bounce", "unsubscribe", or "reply".

    A bounce is declared only on strong evidence: a daemon sender, a
    standard DSN structure (is_dsn), or a strong bounce phrase in the
    subject. Everything else falls through to the unsubscribe check and
    then to "reply".
    """
    low_from = from_addr.lower()
    if any(hint in low_from for hint in BOUNCE_SENDERS):
        return "bounce"
    if is_dsn:
        return "bounce"
    low_subject = subject.lower()
    if any(phrase in low_subject for phrase in BOUNCE_SUBJECTS):
        return "bounce"
    low_body = body.lower()
    if any(word in low_subject or word in low_body for word in UNSUB_WORDS):
        return "unsubscribe"
    return "reply"


def _recipient_address(raw):
    """Bare address out of a DSN recipient header value.

    Values look like "rfc822; buyer@example.com" (sometimes with the
    address in angle brackets). Returns "" when no address is present.
    """
    value = (raw or "").strip()
    if ";" in value:
        value = value.rsplit(";", 1)[-1].strip()
    value = value.strip("<>").strip().lower()
    return value if "@" in value else ""


def parse_dsn_recipients(msg):
    """Recipients named by a delivery status notification.

    Returns a list of {"email", "action", "status"} dicts taken from
    the per-recipient blocks of any message/delivery-status part
    (Final-Recipient preferred, Original-Recipient as fallback). When
    no structured block parses, the plain-text body is scanned for
    Final-Recipient / Original-Recipient lines, the shape many MTAs
    use in the human-readable part; those carry no Action, so they
    come back with an empty action and are treated as failures by the
    caller. Returns [] when the message names nobody.
    """
    found = []
    seen = set()

    def _add(addr, action, status):
        if addr and addr not in seen:
            seen.add(addr)
            found.append({"email": addr, "action": action,
                          "status": status})

    try:
        for part in msg.walk():
            if part.get_content_type() != "message/delivery-status":
                continue
            payload = part.get_payload()
            if not isinstance(payload, list):
                continue
            # The first block is per-message; the rest are per-recipient.
            for block in payload[1:]:
                addr = _recipient_address(block.get("Final-Recipient", "")) \
                    or _recipient_address(
                        block.get("Original-Recipient", ""))
                _add(addr,
                     (block.get("Action", "") or "").strip().lower(),
                     (block.get("Status", "") or "").strip())
    except Exception:  # noqa: BLE001 - a malformed DSN names nobody
        pass
    if not found:
        for match in re.finditer(
                r"(?:Final|Original)-Recipient:\s*rfc822;\s*"
                r"<?([^\s<>;]+@[^\s<>;]+)>?",
                _body_text(msg), re.IGNORECASE):
            _add(match.group(1).lower(), "", "")
    return found


def feedback_entries_for(msg, email_to_company):
    """Feedback-log entries for one fetched message (usually one).

    Non-bounces produce a single entry keyed by the sender, exactly
    as before. A bounce produces one entry per failed recipient named
    in its DSN, keyed by that recipient (see parse_dsn_recipients):
    the daemon's From address is not the customer, and recording it
    would leave the real address unrefused and the company unmatched.
    Delayed recipients are recorded as type "delayed"; success
    receipts are not recorded at all. A bounce whose DSN names nobody
    falls back to a single entry keyed by the sender.
    """
    from_addr = email.utils.parseaddr(
        _decode(msg.get("From", "")))[1].lower()
    subject = _decode(msg.get("Subject", ""))
    body = _body_text(msg)
    kind = classify(from_addr, subject, body, is_dsn=_is_dsn(msg))
    date_str = ""
    if msg.get("Date"):
        try:
            date_str = email.utils.parsedate_to_datetime(
                msg["Date"]).strftime("%Y-%m-%d")
        except (TypeError, ValueError):
            date_str = ""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    base = {"date": date_str, "summary": subject[:200]}
    if kind != "bounce":
        return [dict(base, company=email_to_company.get(from_addr, ""),
                     email=from_addr, type=kind)]
    recipients = parse_dsn_recipients(msg)
    entries = []
    for recip in recipients:
        if recip["action"] in ("delivered", "relayed", "expanded"):
            continue
        entries.append(dict(
            base,
            company=email_to_company.get(recip["email"], ""),
            email=recip["email"],
            type="delayed" if recip["action"] == "delayed" else "bounce"))
    if entries or recipients:
        return entries
    return [dict(base, company=email_to_company.get(from_addr, ""),
                 email=from_addr, type="bounce")]


def default_blocklist_path():
    """The operator's blocklist: config/blocklist.json in the repo."""
    return os.path.join(_config.repo_root(), "config", "blocklist.json")


def add_to_blocklist(path, email_addr, company, date_str):
    """Append an unsubscribe entry for this sender. True when added.

    The entry carries both the address and its domain so the sending
    side refuses the person and the company alike (the docs/06
    promise: an unsubscribed address and company leave every future
    batch). An address already covered — by an entry naming the
    address, or by an unsubscribe entry naming its domain — is not
    added twice. Raises OSError / ValueError on write problems; the
    caller downgrades those to a warning.
    """
    addr = (email_addr or "").strip().lower()
    if not addr or "@" not in addr:
        return False
    domain = addr.rsplit("@", 1)[-1]
    data = {"entries": []}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict) \
                or not isinstance(data.get("entries", []), list):
            # Never "repair" a wrong-shaped blocklist by starting
            # from empty: the write below would silently erase every
            # existing entry. Refuse; the caller warns, and the
            # feedback log still records the unsubscribe, so the
            # sending side refuses the address from there.
            raise ValueError(
                f"blocklist file {path} has the wrong shape (expected "
                "a JSON object with an \"entries\" list); refusing to "
                "overwrite it")
    entries = data.setdefault("entries", [])
    for entry in entries:
        if (entry.get("email") or "").strip().lower() == addr:
            return False
        if (entry.get("domain") or "").strip().lower() == domain \
                and entry.get("reason") == "unsubscribe":
            return False
    entries.append({
        "added_at": date_str,
        "company": company or "",
        "country": "",
        "domain": domain,
        "email": addr,
        "reason": "unsubscribe",
        "note": "Added automatically by read_inbox.py: this address "
                "asked to unsubscribe.",
    })
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Fetch and classify recent inbox mail (read-only).")
    parser.add_argument("--limit", type=int, default=50,
                        help="How many recent messages to fetch (default 50).")
    parser.add_argument("--mailbox", default="INBOX")
    parser.add_argument("--feedback", default=None,
                        help="Feedback file path (default data/outreach-feedback.json).")
    parser.add_argument("--leads", default=None,
                        help="Leads file for company matching (default data/leads.jsonl).")
    parser.add_argument("--blocklist", default=None,
                        help="Blocklist file unsubscribe senders are "
                             "appended to (default config/blocklist.json).")
    args = parser.parse_args()

    host = os.environ.get("IMAP_HOST", "")
    user = os.environ.get("IMAP_USER", "")
    password = os.environ.get("IMAP_PASS", "")
    port = int(os.environ.get("IMAP_PORT", "993"))
    if not (host and user and password):
        print("REFUSED: missing IMAP credentials in the environment "
              "(IMAP_HOST, IMAP_USER, IMAP_PASS)")
        return 1

    feedback_path = args.feedback or _config.data_path("outreach-feedback.json")
    leads_path = args.leads or _config.data_path("leads.jsonl")

    email_to_company = {}
    if os.path.exists(leads_path):
        with open(leads_path, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                row = json.loads(line)
                for addr in row.get("emails", []) or []:
                    email_to_company[addr.lower()] = row.get("company", "")
                if row.get("useful_email"):
                    email_to_company[row["useful_email"].lower()] = \
                        row.get("company", "")

    if os.path.exists(feedback_path):
        try:
            with open(feedback_path, encoding="utf-8") as fh:
                feedback = json.load(fh)
        except (OSError, ValueError) as exc:
            print(f"REFUSED: feedback file {feedback_path} exists but "
                  f"could not be read as JSON ({exc}); fix or restore "
                  "it rather than starting from an empty history — "
                  "the log is safety data (unsubscribes, bounces)")
            return 1
        if not isinstance(feedback, dict):
            print(f"REFUSED: feedback file {feedback_path} has the "
                  "wrong shape (expected a JSON object); fix or "
                  "restore it rather than starting from an empty "
                  "history")
            return 1
    else:
        feedback = {"entries": []}
    seen = {(e.get("email", ""), e.get("summary", ""), e.get("date", ""))
            for e in feedback.get("entries", [])}

    try:
        imap = imaplib.IMAP4_SSL(host, port)
        imap.login(user, password)
        imap.select(args.mailbox, readonly=True)
        _typ, data = imap.search(None, "ALL")
        ids = data[0].split()[-args.limit:] if data and data[0] else []
        fetched = []
        for msg_id in ids:
            _typ, msg_data = imap.fetch(msg_id, "(RFC822)")
            if not msg_data or not msg_data[0]:
                continue
            msg = email.message_from_bytes(msg_data[0][1],
                                           policy=email.policy.default)
            fetched.extend(feedback_entries_for(msg, email_to_company))
        imap.logout()
    except (imaplib.IMAP4.error, OSError) as exc:
        print(f"IMAP ERROR: {exc}")
        return 1

    added = 0
    for entry in fetched:
        key = (entry["email"], entry["summary"], entry["date"])
        if key in seen:
            continue
        feedback.setdefault("entries", []).append(entry)
        seen.add(key)
        added += 1
    if added:
        os.makedirs(os.path.dirname(os.path.abspath(feedback_path)),
                    exist_ok=True)
        with open(feedback_path, "w", encoding="utf-8") as fh:
            json.dump(feedback, fh, ensure_ascii=False, indent=2)
    blocklist_path = args.blocklist or default_blocklist_path()
    blocklisted = 0
    for entry in fetched:
        if entry["type"] != "unsubscribe":
            continue
        try:
            if add_to_blocklist(blocklist_path, entry["email"],
                                entry["company"], entry["date"]):
                blocklisted += 1
        except (OSError, ValueError) as exc:
            print(f"WARNING: could not add {entry['email']} to the "
                  f"blocklist ({blocklist_path}): {exc}",
                  file=sys.stderr)

    counts = {}
    for entry in fetched:
        counts[entry["type"]] = counts.get(entry["type"], 0) + 1
    print(json.dumps({"fetched": len(fetched), "added": added,
                      "blocklisted": blocklisted,
                      "by_type": counts}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
