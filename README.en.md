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
# 1. Copy and edit the config (never commit your real config)
cp config/config.example.json config/config.json
#    Edit: product, keywords, HS codes, markets, sender identity, caps.

# 2. Copy the blocklist structure and add your own exclusions
cp config/blocklist.example.json config/blocklist.json

# 3. Put API keys in the environment only (never in files)
export HUNTER_API_KEYS="key-one,key-two"

# 4. Check a Hunter account balance through the rotation pool
python3 scripts/hunter_pool.py account

# 5. Add leads (manually or via the scan prompt), then render the ranked table
python3 scripts/render.py --input data/leads.example.jsonl --output /tmp/ranked.md

# 6. Build a letter for one lead and run the quality gate
python3 scripts/letter_builder.py --lead data/leads.example.jsonl --line 1
python3 scripts/quality_gate.py --help

# 7. Build the follow-up tracker
python3 scripts/build_tracker.py --help
```

To run the pipeline with an AI agent, give the agent `AGENTS.md` first, then hand it one stage prompt at a time from `prompts/`.

## Configuration

All business-specific values live in one file: `config/config.json` (start from `config/config.example.json`).

Key groups:

- **Offer:** `product`, `product_keywords`, `hs_codes`, `value_points`
- **Markets:** `target_markets`, `excluded_markets` (markets you choose not to serve, with your own reasons)
- **Buyers:** `buyer_categories`, `decision_maker_titles`, `fit_signals`, `scoring_weights`
- **Exclusions:** `exclusion_rules` (your own rules, for example suspected competitors or existing customers), plus `config/blocklist.json`
- **Sender:** `sender_name`, `sender_company`, `sender_email`, `notification_email`
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
├── prompts/                   One platform-agnostic prompt per pipeline stage
├── scripts/                   Hunter pool, quality gate, letter builder, renderer, tracker
└── templates/
    └── letter-templates.md    Fill-in letter templates (standard + channel partner)
```

## Safety and compliance

- **Public information only.** This system is designed to work from information companies publish themselves: their websites, public directories, trade-show exhibitor lists, and public trade data. Do not use leaked, purchased-without-basis, or scraped-behind-login personal data.
- **Follow the anti-spam law of every target market.** Requirements differ by country (for example opt-out and identification rules, business-address disclosure, and stricter consent rules in some jurisdictions). Check the rules for each market in your `target_markets` before sending, honour every opt-out immediately, and never email a contact again after an unsubscribe or a hard bounce.
- **Keys live in environment variables only.** Never write API keys, passwords, or mailbox credentials into config files, prompts, logs, or this repository. `config/config.json` and `.env` are git-ignored by default.
- **Human confirmation for commercial commitments.** The agent must never auto-quote prices, promise stock, delivery dates, exclusivity, or payment terms in a reply. Those always need a human. See the confirmation list in `AGENTS.md`.
- **Respect sending limits.** Ramp up gradually, respect `daily_send_cap`, and let the bounce circuit breaker stop sending automatically (see `docs/06-exclusions-and-failsafes.md`).

## License

MIT. See `LICENSE`.

---

## 中文说明（简要）

这是一套可复用的 B2B 获客流水线：先写清理想客户画像，再从“正在买的人”入手多渠道找公司，找到具名决策人并验证邮箱后，按契合度、可触达度、证据强度三维打分，最后发送经过质检的个性化开发信，并把退信与回复回写到评分里形成闭环。

仓库内所有示例均为虚构企业 Guangzhou BrightTable Ceramics（虚构陶瓷餐具出口商）。使用前把 `config/config.example.json` 复制为你自己的配置，填入你的产品、市场、发件人信息与发送上限；API 密钥只放环境变量，不要写进任何文件。带 AI 智能体运行时，先让它读 `AGENTS.md`，再按 `prompts/` 里五个阶段逐段执行。发送前请自行确认目标市场适用的反垃圾邮件法规，并立即尊重一切退订请求。
