# Deck Studio × 分众知识与媒体集成

## 目录

1. 何时读取与职责边界
2. 页面路由
3. 分众知识与原件
4. 分众媒体资产链
5. 页面与资产契约
6. 输出验收

## 1. 何时读取与职责边界

当项目、客户材料或任一页面涉及分众传媒、Focus Media、电梯电视/LCD、智能屏、框架海报、分众方法论、
历史案例或真实媒体环境时，完整读取本文件，并完整读取 `focusmedia-knowledge` 与
`focusmedia-image-gen` Skill。普通 PPT 不加载本文件，也不增加分众字段。

本文件是 Deck Studio 与两个分众 Skill 之间的集成权威源：

- Deck Studio 负责整册叙事、页面职责、PPT 路由、资产装配和最终文件验收。
- `focusmedia-knowledge` 负责正式知识、来源、事实冲突和历史 PPT/PDF 原页定位。
- `focusmedia-image-gen` 负责媒体术语、标准框体、真实环境参考、物理比例、参考融合和媒体 Output Check。
- `scripts/focusmedia_bridge.py` 只发现并调用两个正式入口，不复制它们的知识或图片逻辑。

专业 Skill 的领域判断优先于通用图片规则。入口、真实参考或验收缺失时停止对应页面，不降级到通用
生图，也不凭常识补写分众事实。

## 2. 页面路由

每页分别决定：

- `mode`：PPT 中保持 `editable` 或整页 `image`；
- `knowledge_route`：事实或原页从哪里取得；
- `specialist_route`：媒体视觉由哪个专业 Skill 生产；
- `production_route`：页面基底如何产生；
- `overlay_policy`：PPT 装配阶段允许后贴哪些精确小资产。

分众媒体专业成品有两种用法：

- `specialist_asset_scope: media-visual`：成品只是页面视觉素材。使用 `mode: editable` +
  `production_route: native-editable`，媒体图原样放置，标题、解释和数据保持原生可编辑。
- `specialist_asset_scope: full-slide`：专业链路已完成最终 16:9 页面。使用 `mode: image` +
  `production_route: reference-fusion`，整页 PNG 原样复制或通过 PPT God `import-slide-image` 导入。

页面同时有环境图和标题、数据或策略判断时，默认使用 `media-visual`。`ppt-god-full-image` 只生产不含
精确媒体硬件的页面；专业成品不再交给 PPT God 或通用图片模型重画。

## 3. 分众知识与原件

普通内容判断先查询已审阅的正式 Markdown：

```bash
python3 scripts/focusmedia_bridge.py query "需要核实的问题" > knowledge-result.json
```

同一主题在相关页面复用结果。查询为空时停止知识路线，不自动进入研究库、原始 PPT/PDF 或在线连接器。
入口调用失败时才运行：

```bash
python3 scripts/focusmedia_bridge.py doctor
```

把返回的 `query`、`mode`、`status`、`candidate_only` 和带 `source_id`、`locator` 的 `evidence` 原样放入
`knowledge_contract`。只有页面明确需要客户投放效果、原始数据、真实案例截图或原版证据页时，才查询
和解析原件：

```bash
python3 scripts/focusmedia_bridge.py source "需要的原件页面" > source-candidates.json
python3 scripts/focusmedia_bridge.py resolve "frag_xxx" > source-result.json
```

确认来源权威、日期、范围和事实冲突后再选候选。PPTX 来源复制唯一原始 slide 并继承媒体关系；PDF
来源使用无改写整页图。不得用相似重制页冒充原页。

## 4. 分众媒体资产链

环境图必须完成两个阶段：

1. **标准带框图**：使用已验证完整框体，只在允许替换的屏幕或海报区域精确合成客户创意，输出带
   checksum 的 `framed_asset`。
2. **环境图**：以真实环境图作为空间权威，以 `framed_asset` 锁定硬件与创意，通过模型参考融合完成
   透视、受光、反射、接触阴影和安装关系。输出后不得平贴整台设备或补贴屏幕内容。

当前可正式使用的标准框体：

| 媒介 | `hardware_standard` | 标准文件 |
|---|---|---|
| 楼宇 LCD | `lcd-32` | `lcd-32-standard.png` |
| 32 英寸智能屏 | `smart-32` | `smart-32-standard.png` |
| 海报框架 | `poster-frame-standard` | `poster-frame-standard.png` |

智能屏规格中只有 `smart-32` 已完成优化与验证；19 寸和 25 寸资产暂不调用。未来规格必须同时具备完整
标准框体、获批 manifest、几何规则和回归测试。

先解析标准框体和真实环境参考：

```bash
python3 scripts/focusmedia_bridge.py select-standard --media LCD
python3 scripts/focusmedia_bridge.py select-reference \
  --media LCD --scene elevator-hall --angle front \
  --shot-size mid --people nopeople --max-grade A
```

保留返回的参考 ID、绝对路径、checksum、媒体类型和硬件标准。候选带 `edit_transport` 时，保留原始
参考图，另派生最大边 2048px 的等比传输副本；最终验收仍以原图为准。

## 5. 页面与资产契约

涉及媒体露出的页面必须包含：

- `requires_focusmedia_media: true`；
- `specialist_route: "focusmedia-image-gen"`；
- `specialist_asset_scope: media-visual | full-slide`；
- `media_contract`：`medium`、`scene`、`hardware_standard`、`creative_source`、`output_type`、
  `integration_mode`、`must_preserve`、`acceptance_checks`；
- `reference_assets`：每项带 ID、绝对路径、checksum、角色和媒体类型；
- 环境图使用实际 `framed_asset`，记录 ID、路径、checksum、媒体类型与硬件标准；
- 最终专业成品记录为 `specialist_asset` 和 `specialist_asset_sha256`。

`output_type: framed-demo` 使用 `integration_mode: framed-standard-composite`；
`output_type: environment-image` 使用 `integration_mode: environment-reference-fusion`。

用户提供的广告画面、Logo、二维码、产品图和已确认创意都是事实资产。屏幕或海报创意在标准带框阶段
锁定，不进入 PPT Overlay。封面和封底只要出现分众媒体，也执行同一契约。

## 6. 输出验收

专业链路完成最终页面后，按 `focusmedia-image-gen` Output Check 生成与最终 PNG checksum 绑定的
`media_validation_report`。至少记录：

```json
{
  "schema_version": 2,
  "status": "passed",
  "validator": "focusmedia-image-gen/output-check",
  "validated_by": "<Agent 或人员>",
  "output": {"path": "pptimg/M01.png", "sha256": "<最终整页图>"},
  "specialist_asset": {"path": "assets/focusmedia-M01.png", "sha256": "<专业媒体图>"},
  "framed_asset": {"id": "fm-framed-001", "path": "assets/framed.png", "sha256": "<带框图>"},
  "media_contract": {
    "medium": "LCD",
    "hardware_standard": "lcd-32",
    "scene": "elevator-hall",
    "output_type": "environment-image",
    "integration_mode": "environment-reference-fusion"
  },
  "environment_assembly": {
    "method": "reference-anchored-model-edit",
    "post_overlay_applied": false
  },
  "reference_assets": [{"id": "fm-lcd-001", "sha256": "<真实环境参考>"}],
  "checks": {
    "media_type": "passed",
    "hardware_geometry": "passed",
    "installation_logic": "passed",
    "creative_accuracy": "passed",
    "environment_integration": "passed",
    "scale": "passed",
    "no_flat_environment_composite": "passed"
  }
}
```

只有不涉及环境尺度的带框演示图可把 `scale` 写为 `not_applicable`，并提供
`scale_not_applicable_reason`。其他检查不得跳过。重新生成最终图片后，旧报告因 checksum 不匹配自动
失效。

交付前运行：

```bash
python3 templates/verify_page_plan.py page_plan.json
python3 templates/verify_focusmedia_output.py deck.json
python3 templates/verify_route_integrity.py final.pptx route_manifest.json
```

再按专业 Skill 检查媒体类型、硬件结构、安装逻辑、创意准确性、环境融合、比例以及环境无平贴结果。
任一项失败，回到原始环境参考与已确认带框图重新融合。
