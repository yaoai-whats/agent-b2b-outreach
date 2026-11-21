# 03 — Email Verification

> Fictional example addresses use `@example.com` and fictional subdomains of it. Set your verification budget and allowed tiers in config.

## What counts as a useful email

A **useful email** is an address you can reasonably expect to land in front of someone who can act on a wholesale enquiry:

- A decision-maker's personal work address (the primary target).
- A purchasing, buying, or wholesale department address.
- A company's main public entry address (the equivalents of info, sales, contact, hello, office in the market's language) — acceptable as a co-recipient alongside a personal address, or as a fallback when it is the only route.

**Not useful** (never counts as making a company reachable, and never used as a fallback):

- Customer-service, support, returns, or order-processing mailboxes.
- Narrow functional mailboxes (media uploads, press-only, careers, and similar single-purpose addresses).
- Any address labelled `invalid` or `accept_all_unconfirmed` (below).

If a Tier S or Tier A company only has non-useful addresses, treat it as having no email and send it back to enrichment.

## The verification ladder (cheapest first)

Climb only as high as the company's value justifies. Stop at the first rung that confirms the address.

1. **Exact public match (free, strongest).** Search the exact candidate address. If it appears on a public page, catalogue, or official document, label it `public_confirmed`.
2. **Syntax and MX screen (free, weak).** Confirms the address is well-formed and the domain runs mail. It cannot confirm the mailbox exists. Never present this as verification.
3. **Pattern establishment (free).** Collect real published addresses at the same domain. Two or more sharing one pattern (for example `first.last@`) establishes the pattern; store it on the lead row (`email_pattern`) so the next person at that company needs no fresh research. Conflicting format directories do not establish a pattern; only real addresses do.
4. **Paid verifier (costs credits).** Use a verifier service (for example via `scripts/hunter_pool.py`):
   - Pattern established: verify the inferred candidate with the verifier endpoint (cheaper per check).
   - Pattern not established: use the finder endpoint (name plus domain), which infers and verifies together.
   - Budget rule (see config): reserve paid checks for your top tiers. Record a "no result" outcome per company and do not pay to re-check the same company inside the cooldown window set in config.

## Domain Search: a people-and-address source before the finder

Hunter's Domain Search endpoint (`python3 scripts/hunter_pool.py domain-search <domain>`) returns, in one call, the people and addresses Hunter associates with a domain: names, positions, and email addresses with a confidence score. Its place in this system is upstream of the finder, not a rung of the ladder:

- Use it during enrichment when the website path has not produced a decision-maker, or has produced too few published addresses to establish a pattern. Its returns feed pattern establishment (rung 3) and give the finder (rung 4) fewer blind calls to make.
- Per Hunter's billing rules, a Domain Search call is charged when it returns results. Cache the result per domain, do not repeat the call for the same domain inside the cooldown window set in config, and reserve it for the tiers allowed paid spend in config.
- A Domain Search return is evidence of where an address was seen, not proof that the mailbox exists. Each returned address still needs rung 1 or rung 4 before it can be labelled sendable.

## The five labels

| Label | Meaning | Send? |
|---|---|---|
| `hunter_valid` | A verifier returned deliverable **and** the domain is not accept-all. The label name is generic: any equivalent verifier result counts. | Yes |
| `public_confirmed` | The exact address is published on a public page or official document. | Yes |
| `unverified` | Inferred or collected but not confirmed by rung 1 or 4. | No |
| `invalid` | A verifier or a hard bounce confirmed the mailbox does not exist. If the address came from an inferred pattern, record that pattern as dead for the company. | No, and do not retry the same pattern |
| `accept_all_unconfirmed` | The domain accepts mail to any address, so no check can confirm this mailbox. | No. Park the candidate and look for another route. |

Only `hunter_valid` and `public_confirmed` addresses may be recipients. A personal address may be sent together with the company's main entry address in the same letter.

## Accept-all domains, explained

Some mail servers accept every address at the domain and discard unknown mailboxes silently, or bounce them later. Consequences:

- A verifier "pass" on an accept-all domain proves nothing about the specific mailbox.
- Accept-all personal addresses therefore stay `accept_all_unconfirmed` forever; there is no check that upgrades them.
- Having MX records does not tell you whether a domain is accept-all. Test for accept-all separately (a probe to a random non-existent address, or the verifier's accept-all flag).
- Real bounce data is the final word: if accept-all addresses from a sender's history bounce at a high rate, that is a reason to keep the no-send rule, not to relax it.

## Domain checks before any candidate work

1. MX lookup: no MX means the domain has no business mail; stop and use fallback routes (form, phone).
2. Accept-all probe: determines which labels are even achievable for this domain.

Run both before generating candidates. Guessing first and verifying later wastes most of the verification budget on addresses that were never plausible.

Both checks are implemented in `scripts/domain_check.py` (pure standard library, no dependencies):

```bash
python3 scripts/domain_check.py example.com
# {"domain": "example.com", "domain_mx": ["mx1.example.com", ...],
#  "domain_accept_all": true | false | "unknown"}

python3 scripts/domain_check.py --leads data/leads.jsonl --write
# fills domain_mx / domain_accept_all on every row that is missing them
```

The MX lookup is a hand-built DNS query over UDP with a system `nslookup` fallback. The accept-all probe opens a short SMTP conversation with the first MX host and asks about a random non-existent address. Two practical warnings:

- **Port 25 is often blocked** (many networks, cloud hosts, and mail providers refuse outbound or inbound SMTP probing). A failed probe is recorded as `"unknown"` (stored as `null` on the lead row), never as a guess in either direction. An `unknown` accept-all result means the paid verifier's accept-all flag and real bounce data carry the decision for that domain.
- The two checks stay independent on purpose: a domain can have valid MX records and still be accept-all, and the probe result never changes the MX result.
