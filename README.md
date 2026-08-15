<div align="center">

# Deck Studio

### 一套 PPT，逐页选择最合适的做法

面向 Codex、Claude Code 等 Agent 的统一 PPT 生产 Skill：先锁定内容，再逐页选择可编辑、纯图、混合或精修路线，最终验收真实 PPTX。

[![License: MIT](https://img.shields.io/badge/License-MIT-F0528A.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-111111.svg)](https://www.python.org/)
[![Tests: 94 passed](https://img.shields.io/badge/tests-94%20passed-A8F04F.svg)](#本地验证)
[![PPTX: editable](https://img.shields.io/badge/PPTX-editable-428FEA.svg)](#四种生产路线)

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

## 它解决三个关键问题

| 关键判断 | Deck Studio 的做法 | 直接收益 |
| --- | --- | --- |
| **内容是否定了** | 先确认听众、目标、逐页主张和证据；客户可见文案与内部工作注记分离 | 制作过程中不再反复漂移口径 |
| **这一页该怎么做** | 每页单独选择可编辑、纯图、混合或来源保留方式 | 视觉强度与后续可修改性可以同时成立 |
| **最后文件能否交付** | 检查最终 PPTX 的文字、字体、背景、媒体关系、页面路线与整册一致性 | 发现截图看不出来的结构与兼容问题 |

**材料或旧稿 → 内容锁定 → 逐页选路 → 装配整册 → 验收最终 PPTX**

## 四种生产路线

![Deck Studio 为可编辑、纯图、混合和旧稿精修页面分别选择生产路线](assets/readme/route-board.svg)

| 路线 | 适合场景 | 交付重点 |
| --- | --- | --- |
| **可编辑** | 数据、表格、案例、多媒体、持续修改 | 保留原生文本、图表和对象关系 |
| **纯图** | 演讲、发布、课程、视觉冲击优先 | 文案冻结、逐页校对、整套视觉一致 |
| **混合** | 客户提案、策略汇报、品牌方案 | 正文可编辑，少量关键页使用整页视觉 |
| **精修** | 已有 PPT 内容基本成立 | 保留内容关系，统一设计并修复兼容问题 |

## 交付前，检查真实文件

![Deck Studio 使用整册总览和文件级审计检查最终 PPTX](assets/readme/verification-board.svg)

Deck Studio 的验收对象是最终 `.pptx`。仓库提供 94 项回归测试，以及可以直接运行的整册审计、字体检查、背景一致性、页面路线完整性与改稿保真工具。

## 适合哪些任务

| 任务 | 输入 | 典型结果 |
| --- | --- | --- |
| 从零制作 | 主题、文档、Markdown、逐字稿、图片素材 | 先形成逐页内容，再生产完整 PPTX |
| 已有稿精修 | 当前 PPTX + 明确修改目标 | 内容关系尽量保留，视觉与兼容问题被系统修复 |
| 继续修改 | 上一版成稿 + 新反馈 | 基于完整现状更新，避免只看当前批次造成内容丢失 |
| 合并改版 | 多份 PPT、页面或来源素材 | 统一页序、叙事、视觉系统和交付标准 |

## 它如何工作

1. 识别任务属于从零制作、已有稿精修、继续修改还是合并重做。
2. 对会改变叙事的任务先完成逐页内容锁定。
3. 根据页面用途选择可编辑、纯图、来源保留或参考融合路线。
4. 按页型家族统一字体、背景、边距、图像关系和改造强度。
5. 装配最终 PPTX，并运行与任务风险匹配的验证工具。

完整生产规范见 [SKILL.md](SKILL.md)。

<details>
<summary><strong>自带的质量工具</strong></summary>

- `templates/deck_audit.py`：审计整册结构、字体和资源；
- `templates/verify_pptx.py`：核对已有稿修改后的内容与资源保真；
- `templates/typography_audit.py`：检查字体家族、继承字体和字号阶梯；
- `templates/verify_background_consistency.py`：检查同类页面的精确背景色；
- `templates/verify_route_integrity.py`：检查可编辑页、纯图页和 Overlay 是否符合路线清单；
- `templates/verify_page_plan.py`：检查逐页内容与生产契约；
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

当前公开版本已在独立的 Python 3.11 环境中重新安装依赖，并通过全部 94 项测试。

<details>
<summary><strong>项目目录</strong></summary>

- `SKILL.md`：统一入口与生产路由；
- `workflows/`：已有稿精修六阶段；
- `references/`：纯图、混合与可选集成规则；
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
