---
name: deck-studio
description: >-
  Unified PPT production and refinement workspace for creating a new deck, improving an existing
  PPTX, revising or merging decks, and choosing the right image-integrated, hybrid, or native-editable
  production type. Preserves one coherent narrative and visual system, confirms visual evidence,
  supports high-impact image pages, keeps required objects editable, and verifies the exact final PPTX.
  Use when the user asks to make, redesign, polish, merge, revise, or finish a PPT, deck, presentation,
  slides, or PowerPoint.
---

# PPT 工作台

把从零制作、已有稿精修、继续修改和混合装配放在同一条生产链上。主 Skill 只负责识别入口、串联
阶段门、选择细则并验收最终 PPTX；字段、脚本和专项知识各归其位，不在这里重复展开。

## 北极星

- 交付对象是一套完整、连贯、可使用的 PPTX，不是若干独立漂亮页面。
- 视觉质量优先；只有真实编辑、数据、媒体或现场操作需求才让页面承担更多原生结构。
- 需要事实支撑的页面只使用经用户确认的合适证据，不拿次优素材填空。
- 用户指定的 Logo、产品、人物、截图、批准创意和媒体资产默认锁定；先用真实产品，不重画替代。
- 图片一体型、混合型和原生可编辑型共享同一视觉母系统，并在同一 PPTX 中确定性装配。
- 原生可编辑页必须以真实 PPT 对象交付，禁止用截图或栅格化页面冒充。
- 最终验收实际 PPTX、播放路径和整册关系，不用“生成成功”或中间预览代替完成。

## 1. 权威源与职责

正式项目的制作期唯一状态源是 PPT God。内容、页序、证据、页面类型、家族样张、反馈问题和 Gate 状态
都写回同一项目；Deck Studio 只读取 PPT God 导出的只读 `project_snapshot`，不得手工维护
`page_plan.json`、`route_manifest.json` 或 `page_families.json`。

| 角色 | 负责 | 不负责 |
|---|---|---|
| Codex 主 Agent | 理解内容、查找原件、调用专业 Skill、生成缺失证据、选择页面类型、写结构规格、最终复核 | 另建一份长期状态清单 |
| PPT God | 单一状态、四个 Gate、证据与问题记录、轻量编辑、确定性预览、装配和导出 | 另起一套自主搜索与生成 Agent |
| Deck Studio | 生产方法、专项路由、结构验证和最终 PPTX 验收 | 覆盖 PPT God 的项目状态 |

已有稿先确认唯一母稿和允许变化边界。用户提供更新文件时，新文件立即成为权威源；旧稿只作来源证据。
局部修图必须编辑用户指定原图，并运行
`templates/verify_local_image_edit.py source.png edited.png --mask x1,y1,x2,y2`。

## 2. 四个用户 Gate

正式生产前完整读取 [references/capability-model.md](references/capability-model.md) 与
[references/production-routing.md](references/production-routing.md)。前者是四个 Gate、视觉母系统和失效范围
的唯一详细说明；后者是 `project_snapshot`、页面类型、证据与装配的唯一详细契约。

### Gate 1：内容与页序

Codex 逐页锁定标题、唯一主张、讲述责任、页序和转场，用户按章节确认。内容反馈只使受影响章节和下游
状态失效。运行：

```bash
python3 templates/verify_page_plan.py project_snapshot.json
```

### Gate 2：视觉证据与页面路线

每页先确定视觉职责，再确定生产类型：

| 视觉职责 | 说明 |
|---|---|
| `evidence` | 人物、产品、界面、数据、案例结果、媒体环境、前后对比等真实证据 |
| `expressive` | 场景、隐喻、氛围和概念表达 |
| `text_led` | 章节、金句、过渡和纯文字页 |

| 生产类型 | 说明 |
|---|---|
| `image_integrated` | 一张完整 16:9 图承担核心文字、画面和构图；只允许精确小覆盖物 |
| `hybrid` | 图片底图承担视觉，关键标题、数据、图表或视频等少量对象保持原生 |
| `native_editable` | 结构本身用原生文字、图片、图表、表格、流程和媒体实现 |

默认优先 `image_integrated`。关键内容需要修改时优先 `hybrid`；实时数据、复杂图表、原生视频、课堂操作
或结构关系必须编辑时使用 `native_editable`。已有优质原生页面优先保留结构并微调。

证据型页面必须经过用户确认。用户指定素材直接锁定，只检查清晰度、比例和技术可用性：第一轮查项目
材料、用户素材和官方来源；第二轮做定向搜索或候选生成。两轮仍无合格结果时，记录已查范围和证据缺口，
暂停该页并请用户补充或批准生成证据；其他页面继续。每页最多一个主推荐和两个真正有价值的备选。

### Gate 3：页面家族与构造样张

核心家族是封面、章节、金句、数据和内容。案例、流程、视频、互动先作为功能标签；形成至少约三页的
稳定重复形式时，才升级为项目专属家族。每个实际使用的家族确认一张视觉代表页；同一家族首次出现
`hybrid` 或从零 `native_editable` 时，再分别确认一张构造样张。代表页通过只授权同页型批次。

```bash
python3 templates/verify_page_families.py project_snapshot.json
```

### Gate 4：整套终验与正式导出

采用问题优先、全套轻量接触表和高风险页复核。草稿可在 Gate 未完成时单独导出并明确标识；正式导出
要求四个 Gate 有效、没有未关闭阻断问题、所有页面装配成功。任一页面失败时整体失败，不插空白页，
不自动降级，不复用过期文件。

```bash
python3 templates/verify_workflow_ready.py project_snapshot.json final_preflight.json
```

## 3. 生产与专项路由

若已安装 `presentations` Skill，完整读取并遵守其 PPTX 生产与验证要求。Codex 负责搜索与生成，PPT God
负责状态、审批、轻改、确定性渲染、装配和导出。

- `image_integrated`：经确认的证据和内容进入 PPT God 整页生成；Logo、二维码、法务标识等精确小资产
  可后贴。涉及真实产品、人物、设备或批准创意时，先独立生成或确认素材，再进入整页生成。
- `hybrid`：一张已批准的完整视觉底图 + 少量原生关键对象；不得在底图上覆盖第二套大块 UI。
- `native_editable`：使用原生文字、形状、图表、表格、图片和媒体关系；从零构造必须先通过家族样张。
- `source_ref` 是跨类型的来源属性，不再是一种页面类型。已有优质原生页可在保持原关系后标记来源。
- `knowledge_route` 和 `specialist_route` 与生产类型正交，只说明事实来源和专业视觉生产者。

任一页面涉及分众传媒、Focus Media、电梯电视/LCD、智能屏、框架海报、分众方法论、历史案例或真实
媒体环境时，完整读取 [references/focusmedia-integration.md](references/focusmedia-integration.md)，并使用
`focusmedia-knowledge` 与 `focusmedia-image-gen`。专业 Skill 输出的标准框体、媒体类型、安装关系和
真实环境证据不得被通用模型重新解释。

## 4. 反馈与增量修改

用户在 PPT God 完成批准、拒绝、替换素材、切换路线和短文案修改；复杂自由反馈在 Codex 提交。反馈记录
必须保存原话、页码、影响范围、状态、修正预览和复验结果。“已处理”不等于关闭，复验通过后才能关闭。

默认失效范围：资产变化只影响引用页；家族样式变化只影响该家族；章节叙事变化影响该章节及转场；
正式验收随后失效。总控 Agent 保持唯一页序、家族系统、素材映射和合册责任。需要并行时，子任务只能
领取不重叠页段、证据搜索或素材生成，不能修改全局结构。

## 5. 验收最终 PPTX

所有路线完整读取 [knowledge/quality-bar.md](knowledge/quality-bar.md)、
[knowledge/check-list.md](knowledge/check-list.md) 和 [workflows/04-verify.md](workflows/04-verify.md)。最低执行：

1. 渲染最终 PPTX，用一张轻量 WebP contact sheet 检查整册；异常页和高风险页再单独查看。
2. 运行 `templates/verify_page_plan.py project_snapshot.json` 和
   `templates/verify_page_families.py project_snapshot.json`。
3. 运行 `templates/verify_route_integrity.py final.pptx project_snapshot.json`，检查三种生产类型、精确素材和
   原生页是否被栅格化。
4. 运行 `templates/verify_workflow_ready.py project_snapshot.json final_preflight.json`，确认四个 Gate、问题、
   全页装配和预检 revision 均有效。
5. 对已有稿运行 `templates/verify_pptx.py source.pptx output.pptx`；未授权修改媒体时追加
   `--require-media-preserved`，保留视频与音频关系和字节。
6. 新增或重做页运行 `templates/typography_audit.py`，按需使用 `--include-slides`、`--allowed-fonts` 和
   `--fail-on-inherited`；同底色家族运行 `templates/verify_background_consistency.py`。
7. 分众项目叠加专项 Output Check；重查用户曾指出的全部问题类型。

任何一项失败都回到对应 Gate 修根因。最终只向用户交付通过验收的 PPTX；过程快照、候选图和中间清单
留在 PPT God 项目内，不作为正式交付物。

## 高效执行约束

- 多页共享视觉规则时，先验证每种页型的一张代表页，再批量执行；高风险复杂页另设锚点。
- 每个阶段主上下文最多查看一张轻量 WebP contact sheet；只对异常页和高风险页查看降采样单页。
- 缺少编辑操作时只做一次针对性文档搜索和一个最小探针；仍不明确就切换已知路线。
- 用户指定素材、真实产品与证据优先；任何自动化不得把“相似”当作“原件”。

## 6. 兼容旧项目

旧 `mode: image/code` 项目按项目主动启用新流程：`image → image_integrated`，`code → native_editable`；
四个 Gate 从待确认开始。旧三份 JSON 仅供历史审计，验证函数仍可读取，但新 CLI、文档和生产流程不再
接受它们。不得把旧清单重新导入后继续双写。

## 7. 能力积累

真实反馈先进入具体案例，再决定是否升级方法：个案进 `cases/`，稳定知识进 `knowledge/`，确定性能力进
`templates/` 或 `scripts/`。未经用户确认，不写案例或长期记忆。

### 升级抽象门

1. **先找所有者**：同一规则只进入一个文档；已有所有者时修改原处。
2. **看证据强度**：跨两个项目重复、属于稳定机制，或用户明确声明为长期偏好，才升级。
3. **写出反例**：找不到不适用场景和清楚边界，就不升级为硬规则。
4. **匹配自由度**：审美写原则，稳定流程写步骤，客观不变量进入脚本。
5. **去项目化**：客户名、页码、指定字体、指定色值和具体构图只留在案例或项目视觉契约。
6. **控制成本**：小任务可用简短契约解决时，不强制创建清单、配置或新文件。

升级后至少做一个正例和一个反例回归。
