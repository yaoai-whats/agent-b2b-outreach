# 06 — Exclusions and Failsafes

> Fictional example values throughout. Your real exclusions live in your private config and blocklist, never in this repository.

## Exclusion mechanisms

Three layers, all checked before scanning, enriching, and sending. A match at any layer skips the company and records the reason on its row.

### Layer 1 — Blocklist (`config/blocklist.json`)

Companies that must never be contacted: existing customers, companies that asked not to be contacted, hard-bounce domains you have retired, and anyone a human has manually barred. Matching is by domain first, then by company name plus country. Structure and one fictional entry: `config/blocklist.example.json`. The mechanism is the deliverable; the contents are yours and stay private.

This layer is enforced in code at send time, not only in prose: `scripts/send_mail.py` refuses any recipient whose address or domain appears in a blocklist entry (entries may carry an `email`, a `domain`, or both), and `scripts/read_inbox.py` appends unsubscribe senders automatically — address and domain, reason `unsubscribe` — so the promise below, that an unsubscribed address and company leave every future batch, holds without a human moving data between files.

### Layer 2 — Excluded markets (`excluded_markets` in config)

Markets you choose not to serve, each with your own reason recorded next to it. Reasons are business decisions, for example payment risk, logistics cost, regulatory burden, or a deliberate focus choice. List the market and the reason in config; the pipeline treats the whole market as out of scope for scanning, enrichment, and sending. Review the list at the monthly review: a market excluded for a temporary reason may belong back in scope.

### Layer 3 — Exclusion rules (`exclusion_rules` in config)

Your own company-level rules, written as plain-language criteria the executing agent applies during scanning and batch selection. Examples of the *kind* of rule operators define (write yours in your own words in config):

- Suspected competitors: companies that manufacture or own a brand in your core category go to the intelligence pool, never the outreach pool.
- Existing relationships: any company already in a commercial relationship is handled by its owner, not by cold outreach.
- Role-based caution: where a contact's profile suggests they are a peer or reseller of your own supply side rather than a buyer, a human decides before any send.
- Channel conflicts: companies bound by an exclusive arrangement with a direct competitor are noted and approached only on human instruction.

Rules are applied conservatively: when a rule plausibly matches and the facts are unclear, the company is held for human judgement rather than sent.

## Failsafes

### Bounce circuit breaker (automatic stop)

Sending stops automatically, and a human is notified, when **either** threshold is met:

- **3 or more hard bounces in a single day**, or
- **15% or more bounces among the most recent 20 sends**.

While stopped: no batch is prepared or sent, the inbox stage keeps running, and the cause is investigated before any restart. Common causes are a stale list segment, a broken verification step, or an accept-all segment that slipped through. Restart at the reduced ramp in `schedules.md`, not at full cap. Thresholds are configurable (`bounce_breaker_daily`, `bounce_breaker_rate`, `bounce_breaker_window` in config); loosening them requires human confirmation (see `AGENTS.md`).

### Other automatic stops

- **Unsubscribe received:** the address, and by default the company, leaves all future batches immediately.
- **Hard bounce on an address:** the address is labelled `invalid`, the company returns to enrichment, and the pattern that produced the address is recorded as suspect.
- **Quality-gate failure spike:** if a batch's gate failures jump, stop and fix the template or data rather than hand-approving exceptions.
- **Key exhaustion:** if all verification keys in the rotation pool are exhausted, enrichment pauses its paid rung; free rungs continue. Keys are never printed in logs or reports, only their remaining-credit figures.

### Human-confirmation failsafe

Commercial commitments in replies (pricing, stock, dates, exclusivity, terms) are never made by the executing agent. The full list is in `AGENTS.md`. When in doubt, the agent drafts and waits.

## Market regulations (read before the first send to any market)

Cold outreach rules differ sharply by market, and this system does not replace legal judgement. Confirm the current rules for every target market separately before sending to it; the notes below are orientation, not advice.

- **Germany (UWG):** B2B cold email generally requires the recipient's prior consent; unsolicited outreach carries the highest legal risk of the common target markets, including warning letters from competitors. Treat Germany as opt-in unless you have confirmed a specific lawful basis.
- **United States (CAN-SPAM):** an opt-out regime. Commercial email is permitted without prior consent if it carries truthful headers, a real postal address, and a working unsubscribe that is honoured promptly.
- **United Kingdom (PECR):** corporate subscribers are treated more leniently than individuals, and B2B email to company addresses is often workable with a clear opt-out, but sole traders and partnerships count as individuals and the rules still need checking per list.

The pattern behind the differences: some markets are opt-in, some are opt-out, and several split by whether the recipient is a company or a person. Record the basis you confirmed for each market in your private notes before its first batch, and re-check when rules change.

## Audit habit

Every skip, stop, and override writes a reason to the lead row or the feedback log. At the monthly review, sample the exclusion decisions: false exclusions cost pipeline, missed exclusions cost reputation, and the second is worse.
