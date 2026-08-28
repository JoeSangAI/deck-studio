# PPT God 项目快照与三种页面生产类型

## 1. 唯一状态源

PPT God 是制作期唯一状态源。Codex 通过 Workflow Core 更新内容、视觉职责、证据、生产类型、家族、
问题和审批；Deck Studio 只读取：

```text
GET /projects/{id}/project-snapshot
```

不得为新项目手工创建或双写 `page_plan.json`、`route_manifest.json`、`page_families.json`。需要离线验证
时，把接口原始响应保存为一次性只读 `project_snapshot.json`；它不能反向成为编辑源。所有 mutation 携带
`expected_revision`；HTTP 409 时读取返回的 `latest_snapshot`，保留用户刚完成的修改后提交最小变化。

## 2. 四个 Gate 与正式接口

| Gate | key | 用户确认内容 |
|---|---|---|
| 内容与页序 | `content_order` | 逐页内容、顺序、章节和转场 |
| 视觉证据与页面路线 | `visual_evidence_route` | 视觉职责、证据选择和生产类型 |
| 页面家族与构造样张 | `family_prototypes` | 家族代表页和已批准生产类型 |
| 整套终验 | `final_review` | 历史问题复验、结构 QA 和正式导出许可 |

```text
GET   /projects/{id}/workflow
POST  /projects/{id}/workflow/enable
PATCH /projects/{id}/workflow/slides
POST  /projects/{id}/workflow/gates/{gate}/{approve|reopen}
GET   /projects/{id}/workflow/issues
POST  /projects/{id}/workflow/issues
PATCH /projects/{id}/workflow/issues/{issue_id}
GET   /projects/{id}/project-snapshot
GET   /projects/{id}/exports/final/preflight
POST  /projects/{id}/exports/draft
POST  /projects/{id}/exports/final
POST  /projects/{id}/codex-handoff
```

## 3. 三种生产类型

| `production_type` | 页面结构 | 优先场景 | 硬验收 |
|---|---|---|---|
| `image_integrated` | 一张完整 16:9 页面图 + 获准小覆盖物 | 视觉冲击、章节、金句、封面、文案冻结页 | 有可用 `image_path`；PPTX 中恰好一个全页图，无原生核心对象 |
| `hybrid` | 一张完整视觉底图 + 少量原生关键对象 | 视觉完成度高，同时要改标题、数字、视频或图表 | 同时有 `image_path` 与 `layout_spec`；PPTX 有全页底图和原生核心对象 |
| `native_editable` | 原生文字、图片、图表、表格、流程和媒体 | 实时数据、复杂关系、课堂操作、持续复用 | 有 `layout_spec`；PPTX 有真实原生内容，不能用全页图冒充 |

`source_ref` 是跨类型来源属性，不是第四种生产类型。已有优质原生页保持结构并记录母稿来源；批准整页图
可记录来源后按 `image_integrated` 使用。默认追求视觉质量；关键内容需要修改时优先 `hybrid`；结构本身
必须编辑时使用 `native_editable`。

## 4. 三种视觉职责

- `evidence`：页面让听众相信一个事实，必须有用户确认的视觉证据。
- `expressive`：页面建立情绪、场景、隐喻或概念，不强制事实证据。
- `text_led`：页面以章节、金句、转场或纯文字为主，不为了填空强塞图片。

视觉职责和生产类型正交。同一张证据页可以是一体图、混合页或原生页；类型由最终使用方式决定。

## 5. 真实 `project_snapshot` 结构

正式接口返回顶层 `project`、`workflow` 与完整 `slides`：

```json
{
  "project": {
    "id": "project-id",
    "title": "项目标题",
    "content_plan_confirmed": true,
    "selected_style": "...",
    "intent_contract": {}
  },
  "workflow": {
    "project_id": "project-id",
    "workflow_version": "1.0",
    "revision": 12,
    "enabled": true,
    "gates": {
      "content_order": {"status": "approved", "approved_revision": 4, "approved_at": "..."},
      "visual_evidence_route": {"status": "approved", "approved_revision": 8, "approved_at": "..."},
      "family_prototypes": {"status": "approved", "approved_revision": 10, "approved_at": "..."},
      "final_review": {"status": "pending", "approved_revision": null, "approved_at": null}
    },
    "families": {
      "content": {
        "label": "内容",
        "status": "approved",
        "representative_slide_id": "slide-id",
        "approved_production_types": ["image_integrated", "hybrid"]
      }
    },
    "assets": [{
      "id": "asset-id",
      "slide_id": "slide-id",
      "role": "product",
      "process_mode": "blend",
      "fidelity": "exact",
      "source_ref": {},
      "review_status": "confirmed",
      "user_locked": true,
      "file_path": "/absolute/product.png",
      "exists": true
    }],
    "issues": [],
    "blockers": []
  },
  "slides": [{
    "id": "slide-id",
    "page_num": 1,
    "type": "content",
    "content_json": {},
    "visual_json": {},
    "prompt_text": "...",
    "image_path": "/absolute/page-1.png",
    "layout_spec": null,
    "production_type": "image_integrated",
    "visual_role": "evidence",
    "evidence_state": {},
    "source_ref": null
  }]
}
```

不要为验证器发明顶层 `gates`、逐页 `assets[]`、第二份家族数组或嵌入式预检结果。正式预检来自独立
`GET /projects/{id}/exports/final/preflight` 响应。

## 6. 证据与用户锁

证据型页面执行两轮止损：

1. 第一轮查项目材料、用户素材、已归档原件和官方来源。
2. 第二轮做定向搜索或候选生成。
3. 无合格结果时写 `status: gap`、两轮 `search_rounds` 和缺口，只暂停该页。

`evidence_state.status` 只取 `unreviewed | candidate | confirmed | gap | waived`。候选最多三项；
`confirmed` 必须选中 `workflow.assets` 中的实际资产。`waived` 只在用户明确批准无需证据或批准替代处理时
使用，并保存 `user_decision`。`gap` 不能同时选中素材。

资产 `fidelity` 只取 `exact | reference | generated`。用户明确提供的原件写 `fidelity: exact`；用户确认
使用的任意候选写 `user_locked: true` 并保持其原有 fidelity，PPT God 拒绝自动替换。系统只检查清晰度、
比例和技术可用性。可能被误认成真实案例、真实投放或真实结果的生成素材，观众页显示“示意图 / AI 生成”。

## 7. 页面家族与样张

`workflow.families` 是以家族 key 索引的对象。核心 key 为 `cover | section | quote | data | content`；
稳定重复约三页的特殊形式可使用项目 key。每个实际家族必须有一个 `representative_slide_id`。
同一家族首次出现某种构造方式时，把它加入 `approved_production_types`；这表示对应样张已经由用户批准，
不能只改字段绕过样张 Gate。

## 8. 装配不变量

- `image_integrated`：一个全页图片；只允许获准精确小覆盖物，无原生核心正文、图表或形状。
- `hybrid`：一个全页底图，并保留标题、数字、图表或媒体等已确认的原生核心对象。
- `native_editable`：保留原生文字、形状、图表、表格、图片和媒体关系；禁止整页截图化。
- 用户锁定资产不能被相似图、模型重画或旧版本替代。
- 源稿音视频未获授权替换时，继续使用 `verify_pptx.py` 核对媒体关系和字节。

```bash
python3 templates/verify_page_plan.py project_snapshot.json
python3 templates/verify_page_families.py project_snapshot.json
python3 templates/verify_route_integrity.py final.pptx project_snapshot.json
python3 templates/verify_workflow_ready.py project_snapshot.json final_preflight.json
```

## 9. 问题、复验与导出

`workflow.issues[]` 保存原始反馈、页码、影响范围、严重度、修正版本和复验结果。严重度为
`blocking | warning`；状态为 `open | in_progress | resolved_pending_verification | closed`。问题只有在
`verification_result.passed: true` 且记录 `correction_version` 后才能关闭。

正式导出先查询预检。响应必须满足：`ok: true`、`workflow_revision` 等于快照 `workflow.revision`、
`ready_count` 等于页面总数且 `blockers` 为空。草稿使用独立接口并明确标识为草稿。

## 10. 专业路由与旧项目

`knowledge_route` 和 `specialist_route` 与 `production_type` 正交。分众页面完整读取
[focusmedia-integration.md](focusmedia-integration.md)，媒体资产遵循标准框体、真实环境、创意锁定和专项
验收。

旧 `mode: image` 只在用户主动启用新 Workflow 时映射为 `image_integrated`；旧 `mode: code` 映射为
`native_editable`。四个 Gate 从待确认开始。旧四条 `production_route` 与三份人工 JSON 只保留只读审计，
不得继续双写。
