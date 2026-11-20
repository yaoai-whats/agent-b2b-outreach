#!/usr/bin/env python3
"""Build the follow-up tracker from lead, send, and feedback state.

Inputs (all JSON, all optional except leads):
- leads.jsonl: one company per line (see data/README.md for fields).
- send-state.json: {"sent": [{"company": ..., "sent_at": "YYYY-MM-DD", ...}],
                    "followups": [{"company": ..., "sent_at": ...}],
                    "scheduled": [{"company": ..., "plan": "YYYY-MM-DD"}],
                    "cancelled": [{"company": ..., "reason": ...}]}
- feedback.json: {"entries": [{"company": ..., "date": ..., "type":
                    "reply" | "bounce" | "unsubscribe", "summary": ...}]}

Outputs:
- A CSV tracker (UTF-8 with BOM, opens cleanly in spreadsheet apps).
- A short Markdown overview with counts by outreach status.

Status priority: feedback outcome (reply / bounce / unsubscribe) beats sent,
which beats scheduled, which beats excluded, which beats candidate.

Follow-up logic follows docs/05-followup-policy.md: interval and maximum
come from --interval-days and --max-followups (defaults 30 and 2, matching
config keys followup_interval_days and followup_max).

Usage:
    python3 build_tracker.py --leads data/leads.jsonl \
        --send-state data/send-state.json --feedback data/feedback.json \
        --out-csv out/tracker.csv --out-md out/tracker-overview.md
"""
import argparse
import csv
import json
import os
from datetime import datetime

STATUS_ORDER = {"replied": 0, "bounced": 1, "unsubscribed": 2, "sent": 3,
                "scheduled": 4, "candidate": 5, "excluded": 6, "needs_contact": 7}
TIER_ORDER = {"S": 0, "A": 1, "B": 2, "C": 3}


def load_json(path, default):
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return default


def load_leads(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def main():
    parser = argparse.ArgumentParser(description="Build the follow-up tracker.")
    parser.add_argument("--leads", default="data/leads.jsonl")
    parser.add_argument("--send-state", default="data/send-state.json")
    parser.add_argument("--feedback", default="data/feedback.json")
    parser.add_argument("--out-csv", default="out/tracker.csv")
    parser.add_argument("--out-md", default="out/tracker-overview.md")
    parser.add_argument("--interval-days", type=int, default=30)
    parser.add_argument("--max-followups", type=int, default=2)
    args = parser.parse_args()

    leads = load_leads(args.leads)
    send_state = load_json(args.send_state, {})
    feedback = load_json(args.feedback, {"entries": []})

    sent = {e["company"]: e for e in send_state.get("sent", [])}
    cancelled = {e["company"]: e.get("reason", "")
                 for e in send_state.get("cancelled", [])}
    scheduled = {}
    for entry in send_state.get("schedule", send_state.get("scheduled", [])):
        name = entry["company"]
        if name not in sent and name not in cancelled:
            scheduled[name] = entry.get("plan", "")
    followups = {}
    for entry in send_state.get("followups", []):
        followups.setdefault(entry["company"], []).append(entry)
    fb_by_company = {}
    for entry in feedback.get("entries", []):
        fb_by_company.setdefault(entry["company"], []).append(entry)

    rows = []
    counts = {}
    for lead in leads:
        name = lead["company"]
        status, last_touch, feedback_txt, next_action = "", "", "", ""
        entries = fb_by_company.get(name, [])
        fu_list = followups.get(name, [])

        if entries:
            feedback_txt = "; ".join(
                f"{e['date']} {e['type']}: {e.get('summary', '')}" for e in entries)
            last_type = entries[-1]["type"]
            if last_type == "reply":
                status = "replied"
                next_action = "human to handle the reply"
            elif last_type == "unsubscribe":
                status = "unsubscribed"
                next_action = "do not contact again"
            elif last_type == "bounce":
                status = "bounced"
                next_action = "address invalid; back to enrichment"
        if not status and name in sent:
            status = "sent"
            last_touch = sent[name].get("sent_at", "")
            if fu_list:
                last_touch = fu_list[-1].get("sent_at", last_touch)
            if len(fu_list) >= args.max_followups:
                next_action = "sequence complete; stop"
            elif last_touch:
                try:
                    days = (datetime.now()
                            - datetime.strptime(last_touch[:10], "%Y-%m-%d")).days
                    if days >= args.interval_days:
                        next_action = (f"follow-up {len(fu_list) + 1} eligible "
                                       f"(interval met, needs new content)")
                except ValueError:
                    pass
        if not status and name in scheduled:
            status = "scheduled"
            last_touch = "planned " + scheduled[name]
        if not status:
            if lead.get("excluded_reason") or name in cancelled:
                status = "excluded"
            elif lead.get("actionable"):
                status = "candidate"
            else:
                status = "needs_contact"

        counts[status] = counts.get(status, 0) + 1
        rows.append({
            "company": name,
            "country": lead.get("country", ""),
            "tier": lead.get("tier", ""),
            "buyer_category": lead.get("buyer_category", ""),
            "contact": lead.get("contact", ""),
            "useful_email": lead.get("useful_email", ""),
            "email_status": lead.get("email_status", ""),
            "outreach_status": status,
            "last_touch": last_touch,
            "followups_sent": len(fu_list),
            "feedback": feedback_txt,
            "next_action": next_action,
            "excluded_reason": lead.get("excluded_reason", ""),
            "added_at": lead.get("added_at", ""),
        })

    rows.sort(key=lambda r: (STATUS_ORDER.get(r["outreach_status"], 9),
                             TIER_ORDER.get(r["tier"], 9)))

    os.makedirs(os.path.dirname(os.path.abspath(args.out_csv)), exist_ok=True)
    with open(args.out_csv, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)

    lines = ["# Follow-Up Tracker Overview", "",
             f"Generated: {datetime.now():%Y-%m-%d %H:%M}",
             f"Companies tracked: {len(rows)}", ""]
    for key in sorted(counts, key=lambda k: STATUS_ORDER.get(k, 9)):
        lines.append(f"- {key}: {counts[key]}")
    os.makedirs(os.path.dirname(os.path.abspath(args.out_md)), exist_ok=True)
    with open(args.out_md, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
