#!/usr/bin/env python3
"""Letter builder: fill the templates with per-company variant rotation.

Design notes:
- Variants (subject, intro, closing) rotate by a hash of the company domain
  (fallback: company name). The same company always receives the same
  variant; different companies do not receive byte-identical letters.
- Sender identity, product, and value points are parameters, normally read
  from your private config (see config/config.example.json). Nothing
  business-specific is hard-coded here.
- An optional channel-partner body variant serves platforms, buying groups,
  and distributor networks (set lead["is_channel_partner"] = True).

CLI:
    python3 letter_builder.py --lead data/leads.example.jsonl --line 1 \
        --sender-name "Alex Rivera" \
        --sender-company "Guangzhou BrightTable Ceramics" \
        --product "ceramic tableware sets" \
        --value "Chip-resistant stoneware keeps breakage low in freight."
"""
import argparse
import json
import re

SUBJECTS = [
    "Wholesale enquiry: {product}",
    "{product}: a low-risk line for your range",
    "Catalogue and wholesale terms: {product}",
]

INTROS = [
    "We manufacture {product} for wholesale and contract buyers.",
    "Our factory produces {product}, supplied to importers and distributors.",
    "We are a maker of {product} selling through wholesale channels.",
]

CLOSINGS = [
    "Could I send you our catalogue and wholesale terms?",
    "Shall I send over the catalogue with the wholesale price list?",
    "Would it help if I sent the catalogue and terms?",
]

BODY = """Hi {name},

I noticed {company} {observation}.

{intro} {benefit}

{closing}

Best regards,
{sender_name}
{sender_company}
"""

PARTNER_SUBJECT = "Wholesale range proposal: {product}"

PARTNER_BODY = """Hi {name},

I noticed {company} {observation}.

{intro} {benefit} For a partner range, the practical points are consistent supply across the year, one line that fits several of your sellers' shelves, and packaging ready for mixed-channel distribution.

{closing}

Best regards,
{sender_name}
{sender_company}
"""

# Observation fallback clauses, chosen by keyword hints in the lead profile.
OBSERVATIONS = [
    "carries tableware and housewares lines for wholesale accounts",
    "runs a wholesale programme in tableware and home goods, a natural fit for our range",
    "supplies tableware to hospitality buyers alongside its core housewares range",
    "is active in the home goods wholesale space",
]


def extract_name(contact):
    """Clean a raw contact field down to a greeting name.

    Rules: empty or unverified marker returns "there"; bracketed or
    parenthesised notes and honorifics are stripped; "A and B" style pairs
    keep both first names joined with "and"; a field with no usable name
    returns "there" rather than guessing.
    """
    if not contact or contact.strip() in ("", "-"):
        return "there"
    if "unverified" in contact.lower():
        return "there"
    first = contact.split("/")[0]
    first = re.split(r"[(\[,]", first)[0]
    first = re.sub(r"^(Mr|Mrs|Ms|Dr)\.?\s+", "", first.strip(), flags=re.I)
    tokens = re.findall(r"[A-Za-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u00FF'\-]+", first)
    if not tokens:
        return "there"
    if re.search(r"\band\b", first) and len(tokens) >= 2:
        return tokens[0] + " and " + tokens[1]
    return tokens[0]


def _variant_idx(lead, salt):
    """Stable per-company variant index from the domain (or company name)."""
    key = (lead.get("domain") or lead.get("company") or "").lower()
    h = 0
    for ch in key + "|" + str(salt):
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return h


def _observation_idx(lead):
    profile = (lead.get("profile") or "").lower()
    if "portal" in profile or "wholesale" in profile:
        return 1
    if "hospitality" in profile or "hotel" in profile:
        return 2
    if "tableware" in profile:
        return 0
    return 3


def build_email(lead, sender_name, sender_company, product, value_point,
                observation=None):
    """Return (to, subject, body) for one lead row."""
    name = extract_name(lead.get("contact", ""))
    company = lead["company"]
    obs = observation or OBSERVATIONS[_observation_idx(lead)]
    intro = INTROS[_variant_idx(lead, 2) % len(INTROS)].format(product=product)
    closing = CLOSINGS[_variant_idx(lead, 4) % len(CLOSINGS)]
    emails = lead.get("emails") or []
    to = lead.get("useful_email") or (emails[0] if emails else "")
    if lead.get("is_channel_partner"):
        subject = PARTNER_SUBJECT.format(product=product)
        body = PARTNER_BODY.format(
            name=name, company=company, observation=obs, intro=intro,
            benefit=value_point, closing=closing,
            sender_name=sender_name, sender_company=sender_company)
    else:
        subject = SUBJECTS[_variant_idx(lead, 1) % len(SUBJECTS)].format(
            product=product)
        body = BODY.format(
            name=name, company=company, observation=obs, intro=intro,
            benefit=value_point, closing=closing,
            sender_name=sender_name, sender_company=sender_company)
    return to, subject, body


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build one letter from a lead row.")
    parser.add_argument("--lead", required=True, help="Path to a leads .jsonl file.")
    parser.add_argument("--line", type=int, default=1,
                        help="1-based line number of the lead to build for.")
    parser.add_argument("--sender-name", required=True)
    parser.add_argument("--sender-company", required=True)
    parser.add_argument("--product", required=True)
    parser.add_argument("--value", required=True,
                        help="One buyer-side value sentence.")
    parser.add_argument("--observation", default=None,
                        help="Override the observation clause.")
    args = parser.parse_args()
    with open(args.lead, encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh if line.strip()]
    lead_row = rows[args.line - 1]
    to_addr, subj, letter_body = build_email(
        lead_row, args.sender_name, args.sender_company, args.product,
        args.value, args.observation)
    print(f"To: {to_addr}")
    print(f"Subject: {subj}")
    print()
    print(letter_body)
