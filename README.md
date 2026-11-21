[**中文**](README.md) | [English](README.en.md)

# B2B 获客系统

一套可复用、配置驱动的 B2B 获客流水线：找买家、验证决策人联系方式、发送通过质检的个性化开发信、跟踪跟进，全程不买客户名单数据库。

> **全文示例均为虚构**：本仓库所有示例使用虚构企业 **Guangzhou BrightTable Ceramics（虚构陶瓷餐具出口商）**。使用前，请把 `config/` 里的每一个值换成你自己的业务信息。

## 如果你是 AI Agent（先读这里）

用户把这个仓库地址交给你、说“帮我安装并使用这个项目”时，**下面所有命令都由你来执行，不要让用户自己去敲终端**：

1. 把仓库克隆或下载到用户电脑上的一个固定目录，并记住这个目录——之后所有定时任务都以它为工作目录。
2. 通读 `AGENTS.md`，那是你的总地图；本 README 只是给人看的概览，与 `AGENTS.md` 冲突时以 `AGENTS.md` 为准。
3. 检查 `config/config.json` 是否存在。不存在就严格按 `prompts/00-onboarding.md` 执行第 0 步问询：逐项问清用户的产品、市场、买家、发件人、发送政策与排除规则，问完之前不许跑任何阶段、不许套用示例值充数。
4. 问询写完配置后，运行 `python3 scripts/doctor.py` 自检，有 FAIL 先修再继续；把配置核对清单给用户确认。
5. 用户确认后，先试跑一轮扫客（Stage 1）把结果给用户看，对口了再往下走补全与备批。
6. 用户同意长期运行后，按 `schedules.md` 里“注册定时任务”一节，用你所在平台的定时能力把各阶段注册成定时任务；你所在平台没有定时能力时，按那一节的降级办法处理，不许只口头建议用户“记得每周跑两次”。
7. 用户给你的任何密钥、邮箱授权码，只写进仓库根目录的 `.env` 文件（已被 git 忽略，全部脚本会自动读取它），不许写进 config、不许出现在日志、简报和回复里、不许回显。

用户需要准备的东西只有两样，而且等你问到那一步再要，不要一上来全索要：

- **必备一**：一个专门发开发信的邮箱（不要用主业务邮箱），以及它的 SMTP / IMAP 服务器地址和授权码（在哪一步问、怎么引导用户去邮箱设置里找，见 `prompts/00-onboarding.md` 第 10 问）。
- **必备二**：一个 Hunter 账号的 API Key（免费版每月 50 个额度，起步够用）。
- **强烈推荐（不是必备）**：一个搜索 API Key（Serper / Tavily / Brave 任一，都有免费额度）。没有它系统也能跑，但找公司和验邮箱会降级；你要主动告诉用户去哪免费申请，他暂时拿不到就按 `AGENTS.md` 的降级规则继续，不许因此卡死第一轮。

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
# 0. 先跑上手问询（第一次使用必做）：让执行 Agent 读 prompts/00-onboarding.md，
#    它会逐项问清你的产品、市场、买家、发件人、发送政策与排除规则，
#    把答案写进 config/config.json 与 config/blocklist.json，并输出配置核对清单。
#    不许跳过这一步直接套用示例值。

# 1. 复制并编辑配置（真实 config 永远不要提交进仓库）
cp config/config.example.json config/config.json
#    改：产品、关键词、HS 编码、目标市场、发件人信息、每日发送上限

# 2. 复制黑名单结构，填入你自己的排除对象
cp config/blocklist.example.json config/blocklist.json

# 3. API 密钥只放环境变量，或写进仓库根目录的 .env 文件（脚本会自动读取，
#    .env 已被 git 忽略）；绝不写进 config，绝不提交进仓库
export HUNTER_API_KEYS="key-one,key-two"     # Hunter 邮箱查找/验证（可选，三方轮换）
export SERPER_API_KEY="your-key"             # 搜索层，三选一即可（Serper 优先）

# 4. 跑一遍自检：Python 版本、配置是否还是示例值、环境变量齐不齐、
#    DNS 能不能查 MX、SMTP 服务器通不通、发件人地址有没有冲突，
#    一次列清 PASS / WARN / FAIL（有 FAIL 先修再往下走）
python3 scripts/doctor.py

# 5. 查 Hunter 轮换池余额
python3 scripts/hunter_pool.py account

# 5b. 按域名查人查邮箱（Hunter Domain Search：返回该域名下的人员与邮箱，
#     按 Hunter 计费规则、有结果才计费；只对 config 允许付费的档位使用）
python3 scripts/hunter_pool.py domain-search example.com

# 5c. 邮箱格式确立与候选生成（纯本地计算，不花额度：已知姓名-邮箱对
#     以 JSON 数组 [{"first": "...", "last": "...", "email": "..."}] 喂入 detect）
python3 scripts/email_pattern.py detect --pairs pairs.json
python3 scripts/email_pattern.py candidate --first Jane --last Doe --pattern first.last --domain example.com

# 6. 加入客户（手动或用扫客提示词），生成排序总表
python3 scripts/render.py --input data/leads.example.jsonl --output /tmp/ranked.md

# 7. 给一家客户生成开发信并过质检门
python3 scripts/letter_builder.py --lead data/leads.example.jsonl --line 1
python3 scripts/quality_gate.py --help

# 8. 生成跟进表
python3 scripts/build_tracker.py --help
```

> **Windows 用户注意**：上面命令里的 `python3` 在 Windows 上通常写作 `python`（或 `py -3`），其余参数完全相同。本仓库的脚本只用 Python 标准库，Windows 可直接跑；`scripts/domain_check.py` 的 DNS 解析在 Windows 上会自动读取 `ipconfig /all` 的 DNS 服务器配置，中英文系统输出都能解析。

用 AI 智能体（Codex、WorkBuddy、Claude 等）跑这条流水线时：先让它读 `AGENTS.md`，再从 `prompts/` 里按阶段逐个把提示词交给它执行。

## 搜索层与执行 Agent 能力要求

找公司、找决策人、验邮箱三步都要联网搜索，**统一走 `scripts/web_search.py`**，不要依赖执行 Agent 自带的搜索：各家搜索后端覆盖差很多，本地语言职位词和小行业目录站尤其明显，结果会直接影响客户质量。

- `search` 子命令：按关键词找公司、找人，可带 `--country` / `--lang`；
- `exact` 子命令：候选邮箱原样加引号全网精确搜索，公开出现过才算验实；
- `fetch` 子命令：打开官网、目录、海关数据页读原文，只看搜索摘要不许下结论；
- `maps` 子命令：地图渠道找本地买家（有 Serper Key 时走地图端点，其他搜索商回退普通搜索并在输出里标明）；
- `trade` 子命令：查贸易数据站的公开页面（这类站点没有公开 API，只能拿到搜索引擎可见的页面，须打开核实，不能当已验证的贸易记录）。

域名层面的两项检查（MX 查询、accept-all 探测）由 `scripts/domain_check.py` 用纯标准库实现，是生成候选邮箱之前必跑的步骤，见 `docs/03-email-verification.md`。发送与收件也都有仓库内脚本：`scripts/send_mail.py`（SMTP 发送，凭据只走环境变量，默认 dry-run，自带收件人状态校验、排除检查、每日上限与退信熔断）和 `scripts/read_inbox.py`（IMAP 只读拉取并分类回复、退信、退订；退订者会自动追加进 `config/blocklist.json`，之后的发送会被排除检查拦下，退订闭环不需要人工搬运）。

发送有两种模式：单封（`--lead ... --line N`）与批量（`--batch --lead data/leads.jsonl`）。批量模式会把客户库里状态合格的行逐封处理：自动组信、过质检、五道校验照旧（收件人状态、排除检查、质检门、每日上限、退信熔断），封与封之间默认间隔 60 秒加 0–30 秒随机抖动；当日封顶按 `daily_send_cap` 减去今日已发数计算，达顶即停，退信熔断触发同样立即停并说明原因。其中排除检查会先在批量开始前预筛：命中黑名单（`config/blocklist.json`，按邮箱或域名）、已经发过冷邮件的地址或公司、在反馈记录里退订过或退信过的地址，都会逐行打印原因并计入汇总的 excluded 计数，绝不重复发送。两种模式默认都是 dry-run，加 `--send` 才真发。SMTP 连接模式按端口自动选：465 端口（或环境变量 `SMTP_USE_SSL=1`）走 SSL 直连（QQ 邮箱、163、阿里云邮箱的默认模式），其余端口走 STARTTLS，报错信息会注明当前模式方便排障。

脚本按顺序用第一个配置好的搜索 API：`SERPER_API_KEY`（Serper，Google 索引，验邮箱精确匹配最稳）→ `TAVILY_API_KEY` → `BRAVE_API_KEY`，三家都有免费额度，配任意一个即可。一个都没配时脚本会退出并给出 FALLBACK 提示，此时才许用 Agent 自带搜索顶上，但要在运行日志注明“搜索层降级”，验真结果降一档处理。

执行 Agent 的最低能力四样：网页搜索、打开读网页、运行 Python、读写文件。缺任何一样，都要在运行日志里明说哪一步降级了。

## 配置说明

业务变量集中在一个文件：`config/config.json`（从 `config/config.example.json` 复制）。这不是一句口号：全部脚本都通过 `scripts/_config.py` 真读这个文件，发件人、产品、每日上限、熔断阈值都从这里取；单个脚本的命令行参数可以临时覆盖 config 的值。第一次使用时不要手填，先跑第 0 步的问询环节（`prompts/00-onboarding.md`），由执行 Agent 问清后写入。

- **产品**：`product`、`product_keywords`、`hs_codes`、`value_points`
- **市场**：`target_markets`、`excluded_markets`（你自己选择不做的市场，逐个写明原因）
- **买家**：`buyer_categories`、`decision_maker_titles`、`fit_signals`、`scoring_weights`
- **排除规则**：`exclusion_rules`（你自己的规则，例如疑似同行、已有客户），另加 `config/blocklist.json`
- **发件人**：`sender_name`、`sender_company`、`sender_email`、`notification_email`。实际发件地址的优先级是写死的：环境变量 `SMTP_FROM` > config 的 `sender_email` > `SMTP_USER`；前两者都设了且不一致时以 `SMTP_FROM` 为准，`scripts/doctor.py` 会给出警告
- **发送安全**：`daily_send_cap`（每日上限）、`followup_interval_days`、`followup_max`、退信熔断阈值
- **密钥**：`hunter_api_keys_env` 指向存放密钥的环境变量名（默认 `HUNTER_API_KEYS`）；密钥本身永不进 config，存放位置只有两个：系统环境变量，或仓库根目录的 `.env` 文件（本机私有、已被 git 忽略、全部脚本经 `scripts/_config.py` 自动读取，真实环境变量优先于 .env）

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
├── prompts/                   第 0 步问询 + 五个阶段各一份平台无关的提示词
├── scripts/                   配置加载、自检、搜索层、域名检查、Hunter 轮换、邮箱格式推断、质检门、信件生成、发送、收件箱、去重、总表、跟进表
├── tests/                     标准库 unittest 回归测试（python3 -m unittest discover -s tests）
└── templates/
    └── letter-templates.md    开发信填空模板（标准版 + 渠道伙伴版）
```

## 安全与合规

- **只用公开信息**：这套系统只使用公司自己公开的信息——官网、公开目录、展会名单、公开贸易数据。不要使用泄露的、无合法来源购买的、或绕过登录抓取的个人数据。
- **遵守每个目标市场的反垃圾邮件法规**：各国要求不同（退订与身份披露、商业地址公示、部分法域更严格的事先同意规则）。发送前先核对 `target_markets` 里每个市场的规则，收到退订立即执行，退信或退订过的地址永不再发。特别注意德国：UWG 下 B2B 冷邮件原则上要求事先同意，是常见目标市场里风险最高的一个；各市场口径对照见 `docs/06-exclusions-and-failsafes.md` 的市场法规一节。
- **密钥只放环境变量或 .env**：API 密钥、密码、邮箱凭据绝不写进配置文件、提示词、日志或仓库；本机存放用仓库根目录的 `.env`（脚本自动读取），`config/config.json` 与 `.env` 默认已被 git 忽略，绝不提交。
- **商务承诺必须人工确认**：Agent 绝不允许在回复里自行报价、承诺库存、交期、独家或付款条件，这些一律由人决定（清单见 AGENTS.md）。
- **尊重发送上限**：发送量逐步爬坡，守住 `daily_send_cap`，退信熔断触发就自动停发（见 `docs/06-exclusions-and-failsafes.md`）。

## 许可

MIT，见 `LICENSE`。
