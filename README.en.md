[中文](README.md) | **English**

# B2B Outreach System

A reusable, config-driven pipeline for finding B2B buyers, verifying decision-maker contacts, sending personalised first-touch letters, and tracking follow-ups — without buying a lead database.

> **Fictional example throughout:** All examples in this repository use a fictional company, **Guangzhou BrightTable Ceramics** (fictional example), a fictional exporter of ceramic tableware sets. Replace every value in `config/` with your own business before use.

## What this system does

Most small exporters and B2B sellers face the same problem: directories sell stale lists, and generic cold email burns your domain. This system takes the opposite approach:

1. Define exactly who should buy from you (an ICP profile).
2. Start from buyers who are *already buying* similar products (trade / customs data), then widen the net through five discovery channels.
3. Find a named decision-maker and a *verified* email before you write anything.
4. Score every company on three separate axes (fit, contactability, evidence) instead of one gut-feel number.
5. Send short, personalised, quality-gated letters, then feed every bounce and reply back into the scoring so the next round is sharper.

## The five-stage pipeline

| Stage | Name | Input | Output |
|---|---|---|---|
| 1 | Scan | `config/config.example.json` (copied to your private config) | New candidate companies in `data/leads.jsonl` |
| 2 | Enrich | Candidates without a verified contact | Decision-maker name, role, verified email, email pattern |
| 3 | Batch | Ranked, reachable, unsent companies | Personalised letters that passed `scripts/quality_gate.py` |
| 4 | Inbox | Your mailbox (replies, bounces, unsubscribes) | Updated lead status, feedback log, circuit-breaker check |
| 5 | Follow-up | Sent companies with no reply | At most 2 follow-ups, 30 days apart, each with new content |

See `AGENTS.md` for the agent operating map, `docs/01-methodology.md` for the full ten-step method, and `schedules.md` for suggested cadence.

## Quick Start

```bash
# 0. Run onboarding first (required for a new operator): have the executing
#    agent read prompts/00-onboarding.md. It interviews you about your
#    product, markets, buyers, sender identity, sending policy, and
#    exclusion rules, writes the answers into config/config.json and
#    config/blocklist.json, and prints a configuration checklist.
#    Never skip this and start from the example values.

# 1. Copy and edit the config (never commit your real config)
cp config/config.example.json config/config.json
#    Edit: product, keywords, HS codes, markets, sender identity, caps.

# 2. Copy the blocklist structure and add your own exclusions
cp config/blocklist.example.json config/blocklist.json

# 3. Put API keys in the environment only (never in files)
export HUNTER_API_KEYS="key-one,key-two"

# 4. Run the self-check: Python version, config still on example values,
#    missing environment variables, DNS/MX reachability, SMTP
#    connectivity, and sender-address conflicts, reported as
#    PASS / WARN / FAIL lines (fix every FAIL before continuing)
python3 scripts/doctor.py

# 5. Check a Hunter account balance through the rotation pool
python3 scripts/hunter_pool.py account

# 6. Add leads (manually or via the scan prompt), then render the ranked table
python3 scripts/render.py --input data/leads.example.jsonl --output /tmp/ranked.md

# 7. Build a letter for one lead and run the quality gate
python3 scripts/letter_builder.py --lead data/leads.example.jsonl --line 1
python3 scripts/quality_gate.py --help

# 8. Build the follow-up tracker
python3 scripts/build_tracker.py --help
```

> **Windows note:** read `python3` above as `python` (or `py -3`) on Windows; every other argument is identical. The scripts use only the Python standard library and run on Windows as-is; `scripts/domain_check.py` discovers DNS servers from `ipconfig /all` output on Windows and parses both English and Chinese system output.

To run the pipeline with an AI agent, give the agent `AGENTS.md` first, then hand it one stage prompt at a time from `prompts/`.

## Configuration

Business-specific values are centralised in one file: `config/config.json` (start from `config/config.example.json`). This is enforced, not aspirational: every script reads the file through `scripts/_config.py` (sender identity, product, daily cap, breaker thresholds all come from there), and a script's command-line arguments may override config values for a single run. For a first setup, do not fill the file in by hand: run the Step 0 onboarding interview (`prompts/00-onboarding.md`) and let the executing agent ask and record the answers.

Domain-level checks (MX lookup and the accept-all probe) are implemented in `scripts/domain_check.py` with the standard library only. Sending and inbox processing are in-repo too: `scripts/send_mail.py` (SMTP, credentials from environment variables only, dry-run by default, with recipient-status, exclusion, daily-cap, and bounce-breaker checks built in) and `scripts/read_inbox.py` (read-only IMAP fetch that classifies replies, bounces, and unsubscribes; unsubscribe senders are appended to `config/blocklist.json` automatically, so the exclusion check refuses them in every later send and the opt-out loop needs no manual step).

Sending has two modes: single (`--lead ... --line N`) and batch (`--batch --lead data/leads.jsonl`). Batch mode processes every sendable row in order — letter built, quality gate, the same five checks per letter (recipient status, exclusions, quality gate, daily cap, bounce breaker) — spaced by 60 seconds plus a random 0–30 second jitter by default; it stops when the daily cap (`daily_send_cap` minus today's recorded sends) is reached or when the bounce circuit breaker trips, and prints the stop reason. The exclusion check also runs as an up-front batch prescreen: rows matching the blocklist (`config/blocklist.json`, by address or domain), addresses or companies already sent a cold email, and addresses with an unsubscribe or bounce in the feedback log are printed with their reason and counted as "excluded" in the run summary, so nobody is ever mailed twice. Both modes are dry runs unless `--send` is given. The SMTP connection mode follows the port: 465 (or `SMTP_USE_SSL=1`) uses implicit TLS, the default mode of QQ Mail, 163 Mail, and Aliyun Mail; other ports use STARTTLS, and error messages name the mode in use.

Key groups:

- **Offer:** `product`, `product_keywords`, `hs_codes`, `value_points`
- **Markets:** `target_markets`, `excluded_markets` (markets you choose not to serve, with your own reasons)
- **Buyers:** `buyer_categories`, `decision_maker_titles`, `fit_signals`, `scoring_weights`
- **Exclusions:** `exclusion_rules` (your own rules, for example suspected competitors or existing customers), plus `config/blocklist.json`
- **Sender:** `sender_name`, `sender_company`, `sender_email`, `notification_email`. The actual From address follows a fixed priority: the `SMTP_FROM` environment variable > `sender_email` in config > `SMTP_USER`; when the first two are both set and differ, `SMTP_FROM` wins and `scripts/doctor.py` warns about it
- **Sending safety:** `daily_send_cap`, `followup_interval_days`, `followup_max`, bounce circuit-breaker thresholds
- **Keys:** `hunter_api_keys_env` names the environment variable that holds your keys (`HUNTER_API_KEYS` by default)

## Repository layout

```text
.
├── README.md                  This file
├── AGENTS.md                  Operating map for the executing agent
├── LICENSE                    MIT
├── schedules.md               Suggested cadence for the five stages
├── config/
│   ├── config.example.json    All business variables (fictional example values)
│   └── blocklist.example.json Blocklist structure + one fictional entry
├── data/
│   ├── README.md              leads.jsonl field reference
│   └── leads.example.jsonl    Exactly 3 fictional sample companies
├── docs/                      Method, scoring, verification, letter, follow-up, failsafe guides
├── prompts/                   Step 0 onboarding plus one platform-agnostic prompt per pipeline stage
├── scripts/                   Config loader, self-check, search layer, domain check, Hunter pool, quality gate, letter builder, sender, inbox reader, dedupe, renderer, tracker
├── tests/                     Standard-library unittest regression tests (python3 -m unittest discover -s tests)
└── templates/
    └── letter-templates.md    Fill-in letter templates (standard + channel partner)
```

## Safety and compliance

- **Public information only.** This system is designed to work from information companies publish themselves: their websites, public directories, trade-show exhibitor lists, and public trade data. Do not use leaked, purchased-without-basis, or scraped-behind-login personal data.
- **Follow the anti-spam law of every target market.** Requirements differ by country (for example opt-out and identification rules, business-address disclosure, and stricter consent rules in some jurisdictions). Check the rules for each market in your `target_markets` before sending, honour every opt-out immediately, and never email a contact again after an unsubscribe or a hard bounce. Note Germany in particular: under the UWG, B2B cold email generally requires prior consent, making it the highest-risk common target market; see the market-regulations section of `docs/06-exclusions-and-failsafes.md`.
- **Keys live in environment variables only.** Never write API keys, passwords, or mailbox credentials into config files, prompts, logs, or this repository. `config/config.json` and `.env` are git-ignored by default.
- **Human confirmation for commercial commitments.** The agent must never auto-quote prices, promise stock, delivery dates, exclusivity, or payment terms in a reply. Those always need a human. See the confirmation list in `AGENTS.md`.
- **Respect sending limits.** Ramp up gradually, respect `daily_send_cap`, and let the bounce circuit breaker stop sending automatically (see `docs/06-exclusions-and-failsafes.md`).

## License

MIT. See `LICENSE`.

---

## 中文说明（简要）

这是一套可复用的 B2B 获客流水线：先写清理想客户画像，再从“正在买的人”入手多渠道找公司，找到具名决策人并验证邮箱后，按契合度、可触达度、证据强度三维打分，最后发送经过质检的个性化开发信，并把退信与回复回写到评分里形成闭环。

仓库内所有示例均为虚构企业 Guangzhou BrightTable Ceramics（虚构陶瓷餐具出口商）。使用前把 `config/config.example.json` 复制为你自己的配置，填入你的产品、市场、发件人信息与发送上限；API 密钥只放环境变量，不要写进任何文件。带 AI 智能体运行时，先让它读 `AGENTS.md`，再按 `prompts/` 里五个阶段逐段执行。发送前请自行确认目标市场适用的反垃圾邮件法规，并立即尊重一切退订请求。
