# 《骰之侵略者 / Dicevaders》知识库

> 用于构建自动化操作 Agent 的游戏资料与视觉识别原型。仓库记录的数据来源为游戏安装文件提取（dicevader-wiki.vercel.app 图鉴站，build `25892943`，补丁 1.0c / 2026-10-15），辅以社区攻略与官方 Steam 信息。实际安装版本、规则效果和自动化能力需单独验证。

## Agent 开发入口

面向 **Windows + NVIDIA GPU** 的当前开发方案见 [技术选型](docs/agent-design/README.md)、[架构设计](docs/agent-design/architecture.md)和[实施与验收计划](docs/agent-design/delivery-plan.md)。推荐先完成 Python 状态机、视觉识别、规则局部搜索和点阵点击，再评估可选的 Qwen3-14B 策略辅助层。

09–11 号文档保留为早期讨论，涉及部署顺序、规则覆盖、模型与硬件、重试和训练评估时，以新方案为准。当前仓库尚未实现完整 Agent，也未完成真实游戏对局验收。

## 基本信息

| 项目 | 内容 |
|---|---|
| 游戏名 | Dicevaders（中文：骰之侵略者 / 日文：ダイスベイダーズ） |
| Steam App ID | 3917700 |
| 开发商 / 发行 | Pengonauts / Playstack |
| 发售日 | 2026-09-29 |
| 平台 | Windows、macOS、Nintendo Switch / Switch 2 |
| 价格 | US$14.99（国区首发 ¥88 → ¥54） |
| 类型 | 骰子 Roguelike 卡组构筑（deckbuilder） |
| 世界观 | 《StarVaders（星之侵略者）》宇宙反转：你扮演外星 Boss 入侵地球，前作人类英雄「驾驶员 Pilot」作为 Boss 防守 |
| 内容规模 | 10 名指挥官、60+ 单位（另含异界变体）、120+ 神器、30 星座、6 章难度、13 个多元宇宙挑战、每日挑战、无尽模式、27 成就 |

## 文件索引

| 文件 | 内容 |
|---|---|
| `dicevaders_data.json` | **机器可读全量数据**（供 Agent 直接读取）：280 神器/专长、84 单位、16 Boss、10 指挥官、6 章、6 调整项、13 挑战、11 每日调整、27 成就、30 星座、17 法术、术语/关键词/规则 |
| `00_总览与核心系统.md` | 官方中英术语表、计分公式、回合循环、资源、组合阶梯、模式与存档 |
| `01_指挥官.md` | 10 名指挥官（官方名+内部键+解锁条件+专属神器/专长+打法） |
| `02_Boss与章节攻略.md` | 16 名 Boss（驾驶员）、六章结构、第 6 章/终极地球四 Boss 数值与机制 |
| `03_单位.md` | 84 个单位（官方中英文名 + 完整效果描述） |
| `04_神器与专长.md` | 280 项神器/专长（按稀有度分组，含中英文效果 + 等级成长） |
| `05_法术与商店.md` | 17 个商店法术 |
| `06_章节与挑战.md` | 六章、6 个难度调整项、13 个多元宇宙挑战、每日调整、27 成就 |
| `07_自动化Agent指南.md` | 面向自动化操作：状态空间、动作空间、关键规则、术语陷阱、数据使用说明 |
| `08_星座.md` | 30 个星座内部键 + 10 个神器星座英文名与专属神器 |
| `09_Agent架构与模型选型.md` | 早期模型讨论，部分能力与性能推断已由当前方案修正 |
| `10_自动化Agent技术选型.md` | 早期局部决策、自进化、结构化日志草案 |
| `11_本地模型微调训练方案.md` | 早期训练草案，固定显存/训练时长估算不可作为容量保证 |
| [Agent 开发设计](docs/agent-design/README.md) | 当前技术选型、源码现状核对、Windows/NVIDIA 部署路径 |
| [Agent 架构](docs/agent-design/architecture.md) | 状态与动作契约、规则搜索、输入验证、日志和离线迭代 |
| [实施与验收](docs/agent-design/delivery-plan.md) | 开发任务、阶段依赖、故障用例、指标与模型准入 |
| `vision/` | 截图识别原型：380 张 sprite 模板、模板匹配、独立 OCR 接口、图标归列与截图工具 |

## 视觉识别模块（vision/）

从游戏 sprite 图集切出 380 张模板图（84 个单位、151 个神器、64 个专长、2 个特殊图标、20 个 Boss 技能、17 个法术、10 个指挥官、16 个 Boss、16 个关键词图标）。现有 NumPy FFT 模板匹配输出图标命中，`state.py` 将命中归列并导出 `BoardState`；数值 OCR 尚未接入，骰子、资源、目标和行坐标仍需补齐，同类实体多实例识别也需改造。详见 [vision 说明](vision/README.md)和[现状核对](docs/agent-design/README.md#3-仓库现状核对)。

## 关键术语速查（官方中文 → 英文）

挪移=Budge、时空点=Chrono、力量=STR、临时倍率=Mult、骰子威力=Dice Power、迷你骰=Mini-Dice、基础骰=Base Dice、护盾=Shield、充能=Charge、电击=Shock、重复=Repeat、心心=Heart、怒火=Rage、蜂蜜=Honey、商店稀有度=Shop Rarity、专长=Perk、神器=Artifact、衍生物=Token。

## 数据可信度说明（重要）

1. **数据来源**：仓库记录 `dicevaders_data.json` 与 03/04/05/06 文件的数据提取自游戏安装文件（GameAssembly.dll）。内部键使用 `k` 或 `key`，中英文名保留提取内容。数据对应 `meta.build` 声明的版本，不代表用户当前安装补丁；效果描述也不等于完整、已验证的可执行规则。
2. **社区补充**：00/01/02/07 文件中的打法、Boss 数值、冷知识来自社区攻略（逗游、gemelog、tahalog、GrindnStrat、Steam 指南），已标注来源与日期，个别数值可能随补丁变动。
3. **已知陷阱**：`dicevaders.wiki`（.wiki 域）存在 AI 生成/臆造内容风险，本库已剔除；以游戏数据文件 + dicevadersguide.wiki + 逗游/gemelog 为准。
4. **描述标记**：数据中 `[#]`=随神器等级成长的数值；`{k.X}`=关键词引用（如 `{k.S}`=得分时、`{k.A}`=触发箭头、`{k.Attack}`=力量、`{k.DicePower}`=骰子威力）；`{f.keyword}…{f.end}`=关键词高亮、`{icons.X}`=图标；`▶`=触发效果分隔（▶之前为条件/代价，▶之后才是被触发时执行的效果）。`<color=…><b>…</b></color>` 为富文本强调标记，可忽略。
5. **`artifacts` 数组实为 6 类实体的合集**（用 `kind` 字段区分）：`artifact`(151 神器)、`perk`(54 专长)、`starter`(10 起始专长)、`pilot`(20 个 Boss 技能)、`constellation`(30 星座)、`special`(15 特殊状态如锁定栏位/Income/Bab)。Boss 技能官方名见 02 文件，星座见 08 文件。
