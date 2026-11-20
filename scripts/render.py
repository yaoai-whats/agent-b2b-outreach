#!/usr/bin/env python3
"""Render leads.jsonl into a ranked Markdown table.

Reachable companies (actionable rows) form the main table, grouped by tier
and ranked by tier, import signal, then fit score. Rows without a useful
email go to an appendix with the reason, so nothing silently disappears.

Usage:
    python3 render.py --input data/leads.jsonl --output out/ranked.md
"""
import argparse
import json
from pathlib import Path

TIER_ORDER = {"S": 0, "A": 1, "B": 2, "C": 3}
TIER_TITLE = {
    "S": "Tier S — strong buying signal plus direct category fit",
    "A": "Tier A — direct category fit",
    "B": "Tier B — broadly related buyer",
    "C": "Tier C — unverified or on hold",
}
REASON_MAP = {
    "invalid": "address verified invalid",
    "accept_all_unconfirmed": "accept-all domain, mailbox unconfirmable",
    "unverified": "address not yet verified",
    "": "no address found",
}


def load(path):
    leads = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        row.setdefault("emails", [])
        row.setdefault("contact", "")
        row.setdefault("profile", "")
        row.setdefault("observation", "")
        row.setdefault("country", "")
        row.setdefault("email_status", "")
        row.setdefault("email_status_raw", "")
        leads.append(row)
    return leads


def sort_key(row):
    return (TIER_ORDER.get(row.get("tier", "C"), 3),
            0 if row.get("import_signal") else 1,
            -(row.get("score_fit") or 0))


def md_row(row, star=False):
    emails = "; ".join(row["emails"]) if row["emails"] else "-"
    mark = "Top: " if star else ""
    contact = row["contact"] or "-"
    obs = (row.get("observation") or "-").replace("|", "/")
    return (f"| {mark}{row['company']} | {row['country']} | {row['profile']} | "
            f"{contact} | {emails} | {row['email_status']} | {obs} |")


def render(leads):
    actionable = sorted([r for r in leads if r.get("actionable")], key=sort_key)
    rest = sorted([r for r in leads if not r.get("actionable")], key=sort_key)
    top_ids = {id(r) for r in actionable[:20]}

    parts = ["# B2B Lead Table (ranked)\n"]
    parts.append(f"> {len(leads)} companies stored; **{len(actionable)} reachable** "
                 f"(verified useful email) in the main table; {len(rest)} held in "
                 f"the appendix. Top 20 priority rows are marked.\n")

    for tier in "SABC":
        items = [r for r in actionable if r.get("tier") == tier]
        if not items:
            continue
        parts.append(f"## {TIER_TITLE[tier]} ({len(items)})\n")
        parts.append("| Company | Country | Profile | Contact | Emails | Email status | Observation |")
        parts.append("|---|---|---|---|---|---|---|")
        parts += [md_row(r, star=id(r) in top_ids) for r in items]
        parts.append("")

    parts.append(f"## Appendix: no verified useful email yet ({len(rest)})\n")
    parts.append("| Company | Country | Profile | Reason | Fallback route |")
    parts.append("|---|---|---|---|---|")
    for row in rest:
        reason = REASON_MAP.get(row["email_status"], "no address found")
        fallback = "contact form / phone" if not row["emails"] else "-"
        parts.append(f"| {row['company']} | {row['country']} | "
                     f"{row['profile'][:90]} | {reason} | {fallback} |")
    parts.append("")

    parts.append("## Summary\n")
    parts.append("| Metric | Count |")
    parts.append("|---|---|")
    parts.append(f"| Companies stored | {len(leads)} |")
    parts.append(f"| Reachable (main table) | {len(actionable)} |")
    parts.append(f"| Verifier-confirmed | "
                 f"{sum(1 for r in actionable if r['email_status'] == 'hunter_valid')} |")
    parts.append(f"| Publicly confirmed | "
                 f"{sum(1 for r in actionable if r['email_status'] == 'public_confirmed')} |")
    parts.append(f"| Held in appendix | {len(rest)} |")
    parts.append(f"| With import signal | {sum(1 for r in leads if r.get('import_signal'))} |")
    parts.append(f"| With named contact | {sum(1 for r in leads if r.get('has_contact'))} |")
    parts.append(f"| With observation | {sum(1 for r in leads if r.get('observation'))} |")
    return "\n".join(parts) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Render the ranked lead table.")
    parser.add_argument("--input", default="data/leads.jsonl")
    parser.add_argument("--output", default="out/ranked.md")
    args = parser.parse_args()
    leads = load(args.input)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render(leads), encoding="utf-8")
    reachable = sum(1 for r in leads if r.get("actionable"))
    print(f"rendered {len(leads)} leads -> {out_path} (reachable {reachable})")


if __name__ == "__main__":
    main()
