[**中文**](README.md) | [English](README.en.md)

# B2B 获客系统

一套可复用、配置驱动的 B2B 获客流水线：找买家、验证决策人联系方式、发送通过质检的个性化开发信、跟踪跟进，全程不买客户名单数据库。

> **全文示例均为虚构**：本仓库所有示例使用虚构企业 **Guangzhou BrightTable Ceramics（虚构陶瓷餐具出口商）**。使用前，请把 `config/` 里的每一个值换成你自己的业务信息。

## 这套系统解决什么问题

多数中小出口商和 B2B 卖家都卡在同一件事上：目录网站卖的名单早就过期，群发模板信又容易把发件域名发废。这套系统走相反的路：

1. 先写清理想客户画像（ICP）：到底谁会买、为什么买。
2. 从“已经在买同类产品的人”入手（海关/贸易数据），再用五个渠道把网撒宽。
3. 写信之前，先找到具名决策人，并验证好他的邮箱。
4. 给每家公司按三个独立维度打分（契合度、可触达度、证据强度），不用一个凭感觉的总分。
5. 开发信短、个性化、过质检门才许发；每一封退信和回复都回写进评分，下一轮更准。

## 五阶段流水线

| 阶段 | 名称 | 输入 | 输出 |
|---|---|---|---|
| 1 | 扫客 | `config/config.example.json`（复制成你自己的 config） | 新候选公司写入 `data/leads.jsonl` |
| 2 | 补全 | 缺可触达邮箱的候选公司 | 决策人姓名、职位、已验证邮箱、邮箱格式 |
| 3 | 备批发送 | 已排序、可触达、未发过的公司 | 通过 `scripts/quality_gate.py` 质检的开发信 |
| 4 | 收件箱 | 你的邮箱（回复、退信、退订） | 更新客户状态、反馈记录、退信熔断检查 |
| 5 | 跟进 | 已发未回复的公司 | 最多跟进 2 次，间隔 30 天，每次带新内容 |

先读 `AGENTS.md`（执行 Agent 的总地图），再读 `docs/01-methodology.md`（十步方法全文），节奏建议见 `schedules.md`。

## 快速开始

```bash
# 1. 复制并编辑配置（真实 config 永远不要提交进仓库）
cp config/config.example.json config/config.json
#    改：产品、关键词、HS 编码、目标市场、发件人信息、每日发送上限

# 2. 复制黑名单结构，填入你自己的排除对象
cp config/blocklist.example.json config/blocklist.json

# 3. API 密钥只放环境变量，绝不写进任何文件
export HUNTER_API_KEYS="key-one,key-two"     # Hunter 邮箱查找/验证（可选，三方轮换）
export SERPER_API_KEY="your-key"             # 搜索层，三选一即可（Serper 优先）

# 4. 查 Hunter 轮换池余额
python3 scripts/hunter_pool.py account

# 5. 加入客户（手动或用扫客提示词），生成排序总表
python3 scripts/render.py --input data/leads.example.jsonl --output /tmp/ranked.md

# 6. 给一家客户生成开发信并过质检门
python3 scripts/letter_builder.py --lead data/leads.example.jsonl --line 1
python3 scripts/quality_gate.py --help

# 7. 生成跟进表
python3 scripts/build_tracker.py --help
```

用 AI 智能体（Codex、WorkBuddy、Claude 等）跑这条流水线时：先让它读 `AGENTS.md`，再从 `prompts/` 里按阶段逐个把提示词交给它执行。

## 搜索层与执行 Agent 能力要求

找公司、找决策人、验邮箱三步都要联网搜索，**统一走 `scripts/web_search.py`**，不要依赖执行 Agent 自带的搜索：各家搜索后端覆盖差很多，本地语言职位词和小行业目录站尤其明显，结果会直接影响客户质量。

- `search` 子命令：按关键词找公司、找人，可带 `--country` / `--lang`；
- `exact` 子命令：候选邮箱原样加引号全网精确搜索，公开出现过才算验实；
- `fetch` 子命令：打开官网、目录、海关数据页读原文，只看搜索摘要不许下结论。

脚本按顺序用第一个配置好的搜索 API：`SERPER_API_KEY`（Serper，Google 索引，验邮箱精确匹配最稳）→ `TAVILY_API_KEY` → `BRAVE_API_KEY`，三家都有免费额度，配任意一个即可。一个都没配时脚本会退出并给出 FALLBACK 提示，此时才许用 Agent 自带搜索顶上，但要在运行日志注明“搜索层降级”，验真结果降一档处理。

执行 Agent 的最低能力四样：网页搜索、打开读网页、运行 Python、读写文件。缺任何一样，都要在运行日志里明说哪一步降级了。

## 配置说明

所有业务变量只放一个文件：`config/config.json`（从 `config/config.example.json` 复制）。

- **产品**：`product`、`product_keywords`、`hs_codes`、`value_points`
- **市场**：`target_markets`、`excluded_markets`（你自己选择不做的市场，逐个写明原因）
- **买家**：`buyer_categories`、`decision_maker_titles`、`fit_signals`、`scoring_weights`
- **排除规则**：`exclusion_rules`（你自己的规则，例如疑似同行、已有客户），另加 `config/blocklist.json`
- **发件人**：`sender_name`、`sender_company`、`sender_email`、`notification_email`
- **发送安全**：`daily_send_cap`（每日上限）、`followup_interval_days`、`followup_max`、退信熔断阈值
- **密钥**：`hunter_api_keys_env` 指向存放密钥的环境变量名（默认 `HUNTER_API_KEYS`），密钥本身永不进文件

## 仓库结构

```
.
├── README.md                  本文件（中文主说明）
├── README.en.md               English version
├── AGENTS.md                  执行 Agent 的总地图（先读这个）
├── LICENSE                    MIT
├── schedules.md               五阶段建议节奏
├── config/
│   ├── config.example.json    全部业务变量（虚构示例值）
│   └── blocklist.example.json 黑名单结构 + 1 条虚构示例
├── data/
│   ├── README.md              leads.jsonl 字段说明
│   └── leads.example.jsonl    3 家虚构示例公司
├── docs/                      方法、评分、验证、信件、跟进、防线六篇
├── prompts/                   五个阶段各一份平台无关的提示词
├── scripts/                   搜索层、Hunter 轮换、质检门、信件生成、总表、跟进表
└── templates/
    └── letter-templates.md    开发信填空模板（标准版 + 渠道伙伴版）
```

## 安全与合规

- **只用公开信息**：这套系统只使用公司自己公开的信息——官网、公开目录、展会名单、公开贸易数据。不要使用泄露的、无合法来源购买的、或绕过登录抓取的个人数据。
- **遵守每个目标市场的反垃圾邮件法规**：各国要求不同（退订与身份披露、商业地址公示、部分法域更严格的事先同意规则）。发送前先核对 `target_markets` 里每个市场的规则，收到退订立即执行，退信或退订过的地址永不再发。
- **密钥只放环境变量**：API 密钥、密码、邮箱凭据绝不写进配置文件、提示词、日志或仓库；`config/config.json` 与 `.env` 默认已被 git 忽略。
- **商务承诺必须人工确认**：Agent 绝不允许在回复里自行报价、承诺库存、交期、独家或付款条件，这些一律由人决定（清单见 AGENTS.md）。
- **尊重发送上限**：发送量逐步爬坡，守住 `daily_send_cap`，退信熔断触发就自动停发（见 `docs/06-exclusions-and-failsafes.md`）。

## 许可

MIT，见 `LICENSE`。
