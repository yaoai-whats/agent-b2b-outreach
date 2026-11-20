# 06 — Exclusions and Failsafes

> Fictional example values throughout. Your real exclusions live in your private config and blocklist, never in this repository.

## Exclusion mechanisms

Three layers, all checked before scanning, enriching, and sending. A match at any layer skips the company and records the reason on its row.

### Layer 1 — Blocklist (`config/blocklist.json`)

Companies that must never be contacted: existing customers, companies that asked not to be contacted, hard-bounce domains you have retired, and anyone a human has manually barred. Matching is by domain first, then by company name plus country. Structure and one fictional entry: `config/blocklist.example.json`. The mechanism is the deliverable; the contents are yours and stay private.

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

## Audit habit

Every skip, stop, and override writes a reason to the lead row or the feedback log. At the monthly review, sample the exclusion decisions: false exclusions cost pipeline, missed exclusions cost reputation, and the second is worse.
