# Data — `leads.jsonl` Field Reference

One JSON object per line, one line per company. The file is the single living database: every pipeline stage appends or updates rows in place. `data/leads.example.jsonl` in this repository holds exactly 3 fictional sample rows; your real `data/leads.jsonl` is git-ignored.

> All example values are fictional (Guangzhou BrightTable Ceramics is a fictional example business; sample buyers are fictional; all addresses use `example.com` domains).

| Field | Meaning | Values / format |
|---|---|---|
| `company` | Company name as the company writes it | String |
| `domain` | Website domain; deduplication primary key | String, lowercase, no scheme |
| `country` | Country of the company's main buying office | String |
| `buyer_category` | Buyer type from config | One of `buyer_categories` in config, for example `tableware wholesalers` |
| `profile` | One or two sentences on what the company does and why it fits | String |
| `observation` | One factual clause from the company's public information (published range, programme, or channel activity), written by the researching agent; used verbatim as the letter's observation sentence | String; a row without one is not ready for Stage 3 |
| `source_channel` | Discovery channel | `trade_data`, `maps`, `directory`, `trade_show`, `web_search`, `distributor_network` |
| `source_url` | Evidence link for the discovery | URL string |
| `added_at` | Date the row entered the database | `YYYY-MM-DD` |
| `import_signal` | Whether a public trade record supports buying activity | `true`, `false`, or `null` when unchecked |
| `import_detail` | Short note on the trade record (count, recency, code) | String, may be empty |
| `contact` | Decision-maker name as found, before cleaning | String; empty when none found |
| `contact_title` | Decision-maker role | String |
| `contact_evidence_url` | Public page proving the person and role | URL string |
| `has_contact` | Whether a named decision-maker is recorded | Boolean |
| `emails` | All known addresses for the company | Array of strings |
| `email_pattern` | Established address pattern at the domain | For example `first.last`, `first_initial.last`; empty until two real addresses establish it |
| `email_status` | Verification label of the best address | `hunter_valid`, `public_confirmed`, `unverified`, `invalid`, `accept_all_unconfirmed` |
| `email_status_raw` | Verifier or checker detail behind the label | String |
| `useful_email` | The address cleared for sending | String; empty when none qualifies |
| `useful_email_kind` | Why it is useful | `decision_maker`, `purchasing_department`, `main_entry` |
| `domain_mx` | MX check result | Boolean or `null` |
| `domain_accept_all` | Accept-all probe result | Boolean or `null` |
| `tier` | Scoring tier | `S`, `A`, `B`, `C` |
| `score_fit` | Fit dimension score | Number 0 to 5 |
| `score_contactability` | Contactability dimension score | Number 0 to 5 |
| `score_evidence` | Evidence dimension score | Number 0 to 5 |
| `actionable` | Reachable and cleared for batch selection | Boolean |
| `excluded_reason` | Why the row is excluded, when it is | String; empty when not excluded |
| `outreach_status` | Pipeline state | `new`, `enriched`, `sent`, `replied`, `bounced`, `unsubscribed`, `sequence_complete`, `excluded` |
| `last_touch_at` | Date of the most recent letter or follow-up | `YYYY-MM-DD` or empty |
| `followups_sent` | Follow-ups sent so far | Integer, never above `followup_max` in config |

## Rules

- Deduplicate on `domain`; without a website, match on company name plus country.
- Never overwrite a conflicting field silently: keep the better-evidenced value and note the conflict in `profile` or the run report.
- `useful_email` may only be set when `email_status` is `hunter_valid` or `public_confirmed`.
- Every send, bounce, reply, and unsubscribe updates the row in the same run it is observed.
