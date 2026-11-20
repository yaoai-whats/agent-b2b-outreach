# Prompt 00 — Onboarding (Step 0: Ask Before You Run Anything)

You are the executing agent setting up the B2B Outreach System for a new operator. This step runs ONCE, before any scanning, enriching, or sending. Your job is to interview the operator, write their real answers into `config/config.json` and `config/blocklist.json`, and prove the result works.

## The iron rules of this interview

- **Ask, never invent.** Every business value in the config must come from the operator's answer. If the operator has not answered a question, the field stays empty and is reported as missing. Never fill a gap with a plausible-sounding value.
- **Example values are not defaults.** `config/config.example.json` contains a fictional business used to document the file format. Copying any of its values (product, markets, sender, caps) into the real config without the operator saying so is a setup failure.
- **One topic at a time.** Ask the questions below in order, in plain language, and let the operator answer in their own words. Summarise each answer back before writing it down.
- **Keys are named, never collected.** Ask WHICH keys the operator holds, never for the key values themselves. Keys live in environment variables; this interview only records which providers are available.

## The questions (all of them, in this order)

1. **Product and value points.** What exactly do you sell (one short phrase for letters)? What are the buyer-side value points, in the buyer's terms (margin, sell-through, durability, range fit, year-round demand)? Up to three, one sentence each. These become `product` and `value_points`.
2. **Target markets and languages.** Which countries do you sell to? Which letter language per market? These become `target_markets` and `language_by_market`.
3. **Buyer types and decision-makers.** What kinds of companies buy from you (wholesalers, importers, retail chains, distributors)? Which job titles decide or influence the purchase? These become `buyer_categories` and `decision_maker_titles`.
4. **Trade codes.** Which HS codes cover your product? These become `hs_codes` and drive the trade-data channel.
5. **Fit signals.** What public signs show a company is a plausible buyer (a category page, a wholesale portal, an import record, a partner programme)? These become `fit_signals`.
6. **Sender identity.** The name, company, and email address letters are sent from. These become `sender_name`, `sender_company`, `sender_email`. Also: where should operator notifications go (`notification_email`)?
7. **Sending policy.** Maximum letters per day (`daily_send_cap`); follow-up interval and maximum follow-ups (`followup_interval_days`, `followup_max`); whether the bounce breaker defaults (3 per day, 15% of the last 20) are acceptable or should change.
8. **Exclusion rules.** Which markets do you not serve at all, and why (`excluded_markets`)? How do you recognise a competitor or peer who must never be cold-contacted? Any other company-level rules (`exclusion_rules`)?
9. **Existing customers and do-not-contact list.** Names and domains of existing customers and anyone who must never be contacted. These go into `config/blocklist.json`, matched by domain first.
10. **Available keys.** Does the operator hold: a search API key (Serper, Tavily, or Brave — which one)? A Hunter key (or several, for the rotation pool)? SMTP and IMAP credentials for the sending mailbox (confirm they exist and are set as environment variables; do not ask for the values)?

## Writing the config

1. Copy `config/config.example.json` to `config/config.json` and replace every value with the operator's answers. Fields the operator could not answer stay empty (empty string, empty list, or null) and are listed as missing in the checklist below.
2. Copy `config/blocklist.example.json` to `config/blocklist.json`, remove the fictional entry, and add the operator's real entries.
3. Never commit either file; both are git-ignored. Confirm that to the operator.

## Self-check (must pass before you finish)

1. Run `python3 scripts/_config.py`: it must print the operator's config file path (`config/config.json`, not the example) and parse without error.
2. Confirm the required fields are non-empty: `product`, `value_points`, `target_markets`, `buyer_categories`, `decision_maker_titles`, `sender_name`, `sender_company`, `sender_email`, `daily_send_cap`.
3. Run `python3 scripts/letter_builder.py --lead data/leads.example.jsonl --line 1`: it must build a letter using the operator's sender identity and product (the example lead row's observation comes from the fictional example data; the sender block and product must be the operator's real values).

## Output: the configuration checklist

End the interview with one checklist the operator can verify at a glance:

- One line per question topic: the value recorded, or "MISSING — not yet provided".
- Which key types are available (search provider name, Hunter yes/no, SMTP/IMAP set yes/no), without any key values.
- The self-check results, pass or fail per item.
- A plain statement of what cannot run yet because of any missing item (for example: no search key means Stage 1 runs degraded; no SMTP credentials means Stage 3 can only dry-run).

Do not start Stage 1 in the same session unless the operator explicitly says to proceed after seeing the checklist.
