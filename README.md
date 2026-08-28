<div align="center">

# Deck Studio

### 一套 PPT，逐页选择最合适的生产类型

面向 Codex、Claude Code 等 Agent 的统一 PPT 生产 Skill：先锁定内容与证据，再逐页选择图片一体型、
混合型或原生可编辑型，最终验收真实 PPTX。

[![License: MIT](https://img.shields.io/badge/License-MIT-F0528A.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-111111.svg)](https://www.python.org/)
[![Tests: 126 passed](https://img.shields.io/badge/tests-126%20passed-A8F04F.svg)](#本地验证)
[![PPTX: mixed](https://img.shields.io/badge/PPTX-mixed-428FEA.svg)](#三种生产类型)

</div>

![Deck Studio 把内容锁定、逐页路由和最终 PPTX 验证放在同一条工作流中](assets/readme/hero-system.svg)

<p align="center"><sub>全部演示页面、品牌与数据均为完全虚构，不含任何客户素材。</sub></p>

> [!IMPORTANT]
> **Deck Studio 是安装到 Agent 中使用的开源 Skill，不是在线网站，也不附带模型额度。** 普通 PPT 工作流、审计和验证工具全部在仓库内，不依赖 Joe 的个人目录或本机软链接。纯图页面需要由当前 Agent 提供图片能力，或在直接运行脚本时自行配置图片模型。

## 3 分钟安装

需要 Python 3.10 或更高版本。

### Codex

```bash
git clone https://github.com/JoeSangAI/deck-studio.git ~/.codex/skills/deck-studio
cd ~/.codex/skills/deck-studio
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

### Claude Code

```bash
git clone https://github.com/JoeSangAI/deck-studio.git ~/.claude/skills/deck-studio
cd ~/.claude/skills/deck-studio
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

重启 Agent 后，直接描述任务：

```text
帮我把这份材料做成一套给管理层汇报的 PPT。先梳理逐页内容，再决定哪些页面保持可编辑。
```

```text
精修这份 PPT。内容不变，统一整册视觉，并检查最终文件。
```

## 它管理八项关键能力

| 能力 | Deck Studio 的做法 | 直接收益 |
| --- | --- | --- |
| **权威源管理** | 锁定唯一母稿、用户最新修改和本轮变更边界 | 新反馈不会与旧稿混成一团 |
| **叙事与内容锁定** | 确认逐页主张、证据、现场话术和转场 | 页面先讲对，再进入视觉生产 |
| **页面路由** | 每页单独选择图片一体型、混合型或原生可编辑型 | 视觉质量与真实编辑需求同时成立 |
| **视觉系统** | 用统一母体管理页型家族，再允许案例品牌形成变体 | 不同章节有辨识度，整册仍像同一套 PPT |
| **真实资产** | 分开管理参考资产、精确资产和生成资产，并核对文件指纹 | 使用真实产品与 Logo，同时阻止模型仿造事实 |
| **页面生产** | 按已批准家族样张生产图片一体页、混合页或原生对象页 | 工具不会反过来改变用户要的页面形态 |
| **装配与修改保真** | 每页只有一个基底，精确层、媒体和用户已确认页面按契约保留 | 避免遮挡式混搭和修改后静默丢媒体 |
| **观众验收** | 检查最终 PPTX 的可读性、品牌、媒体、路线和整册关系 | 发现截图和“导出成功”掩盖的交付问题 |

**材料或旧稿 → 内容锁定 → 逐页选路 → 装配整册 → 验收最终 PPTX**

## 三种生产类型

![Deck Studio 为图片一体型、混合型和原生可编辑型页面选择生产方式](assets/readme/route-board.svg)

| 路线 | 适合场景 | 交付重点 |
| --- | --- | --- |
| **图片一体型** | 演讲、发布、课程、视觉冲击优先 | 一张全页图承担核心文字、画面与构图 |
| **混合型** | 关键标题、数据、视频或图表需要修改 | 全页底图承担视觉，少量关键对象保持原生 |
| **原生可编辑型** | 数据、表格、流程、媒体和持续修改 | 全部所需内容以真实 PPT 对象交付 |

## 交付前，检查真实文件

![Deck Studio 使用整册总览和文件级审计检查最终 PPTX](assets/readme/verification-board.svg)

Deck Studio 的验收对象是最终 `.pptx`。仓库提供 126 项回归测试，以及可以直接运行的整册审计、字体检查、背景一致性、页面路线完整性与改稿保真工具。

## 适合哪些任务

| 任务 | 输入 | 典型结果 |
| --- | --- | --- |
| 从零制作 | 主题、文档、Markdown、逐字稿、图片素材 | 先形成逐页内容，再生产完整 PPTX |
| 已有稿精修 | 当前 PPTX + 明确修改目标 | 内容关系尽量保留，视觉与兼容问题被系统修复 |
| 继续修改 | 上一版成稿 + 新反馈 | 基于完整现状更新，避免只看当前批次造成内容丢失 |
| 合并改版 | 多份 PPT、页面或来源素材 | 统一页序、叙事、视觉系统和交付标准 |

## 它如何工作

1. 锁定唯一母稿、用户最新修改和本轮变更边界。
2. 对会改变叙事的任务先完成逐页内容锁定。
3. 根据页面视觉职责选择图片一体型、混合型或原生可编辑型，并确认真实证据。
4. 按页型家族定义统一母视觉，分别确认视觉代表页与必要的构造样张。
5. 登记真实资产，按路线生产并保留精确图片和媒体关系。
6. 装配最终 PPTX，从观众、品牌、播放和结构四个视角验收。

完整生产规范见 [SKILL.md](SKILL.md)，能力架构与阶段门见
[references/capability-model.md](references/capability-model.md)。

<details>
<summary><strong>自带的质量工具</strong></summary>

- `templates/deck_audit.py`：审计整册结构、字体和资源；
- `templates/verify_pptx.py`：核对已有稿修改后的内容与资源保真；
- `templates/typography_audit.py`：检查字体家族、继承字体和字号阶梯；
- `templates/verify_background_consistency.py`：检查同类页面的精确背景色；
- `templates/verify_route_integrity.py`：用 PPT God 项目快照检查三种页面类型的实际装配；
- `templates/verify_page_plan.py`：检查 Gate 1、逐页内容和快照基础契约；
- `templates/verify_workflow_ready.py`：结合独立正式预检检查四个 Gate、问题复验和全页装配；
- `scripts/contact_sheet.py`：生成整册轻量总览，用于视觉复核。

</details>

## 依赖与边界

- 普通 PPT 工作流、审计工具和验证脚本都在本仓库内。
- 制作纯图页面需要可用的图片生成能力；直接运行 `scripts/gen_deck.py` 时，通过环境变量提供 `OPENAI_API_KEY`，不要把密钥写入仓库。
- 分众传媒相关能力是可选扩展，仅在任务明确涉及分众知识、历史原页或媒体环境时使用。具体契约见 [分众集成说明](references/focusmedia-integration.md)；缺少这些扩展不影响普通 PPT 工作流。
- `presentations` 等专业演示文稿 Skill 可以增强原生 PPTX 生产与渲染能力，但不属于本仓库内容。

## 本地验证

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

当前版本已通过全部 126 项本地回归测试。

<details>
<summary><strong>项目目录</strong></summary>

- `SKILL.md`：统一入口、条件路由与阶段串联；
- `references/capability-model.md`：能力架构、阶段门和文档职责；
- `workflows/`：已有稿精修六阶段；
- `references/`：页面生产契约、纯图产线与可选集成规则；
- `knowledge/`：按问题读取的 PPT 设计与兼容知识；
- `templates/`：审计、修复和硬验证工具；
- `scripts/`：大纲派生、整页图生产、装配和质检；
- `tests/`：回归测试；
- `agents/openai.yaml`：Skill 展示与调用元数据。

</details>

## 公开与隐私

本地案例默认放在 `cases/`，该目录已被 Git 忽略。公开仓库中的展示图只使用虚构品牌、虚构数据与通用几何图形，避免客户名称、项目路径、真实素材和私有知识进入版本历史。

## License 与来源

本项目沿用 [MIT License](LICENSE)。初始纯图管线来自 [张拼拼·XNTJ（Max Pin）的 Deck Studio](https://github.com/xntj-ai/deck-studio)，后续版本扩展了可编辑、混合、精修、路由和验收能力。原作者版权声明保留在 License 中。

如果这个工作台对你有帮助，欢迎 Star，并通过 [Issues](https://github.com/JoeSangAI/deck-studio/issues) 提交使用问题或改进建议。
