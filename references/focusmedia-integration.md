# Deck Studio × 分众知识与媒体集成

## 1. 何时读取与职责

项目或页面涉及分众传媒、Focus Media、电梯电视/LCD、智能屏、框架海报、分众方法论、历史案例或真实
媒体环境时，完整读取本文件，并完整读取 `focusmedia-knowledge` 与 `focusmedia-image-gen` Skill。普通 PPT
不加载本文件，也不增加分众字段。

- Codex 负责整册叙事、证据检索、页面职责、生产类型、专业 Skill 调用、资产编排和最终复核。
- PPT God 保存页面、资产、确认、问题和 Gate 状态，并执行确定性预览、装配与导出。
- `focusmedia-knowledge` 负责正式知识、来源、事实冲突和历史 PPT/PDF 原页定位。
- `focusmedia-image-gen` 负责媒体术语、标准框体、真实环境参考、物理比例、参考融合和 Output Check。
- `scripts/focusmedia_bridge.py` 只发现并调用正式入口，不复制领域知识或图片逻辑。

专业 Skill 的领域判断优先于通用图片规则。入口、真实参考或验收缺失时，把证据缺口写回 PPT God，暂停
对应页面；其他页面继续。不得降级到通用生图，也不得凭常识补写分众事实。

## 2. 页面类型与专业资产

页面的唯一制作契约来自 `project_snapshot.slides[]`：

- `visual_role`：媒体实景、案例原页和事实截图通常为 `evidence`；概念场景可为 `expressive`。
- `production_type: image_integrated`：专业链路产出最终 16:9 页面，整页 PNG 原样装配。
- `production_type: hybrid`：专业媒体图作为全页视觉底图，关键标题、数据、视频或图表保留原生对象。
- `production_type: native_editable`：专业媒体图只作为原生图片对象，页面结构和其余内容保持可编辑。

专业成品不再交给 PPT God 或通用图片模型重画。页面使用的专业资产写入
`project_snapshot.workflow.assets[]`：

- `role` 与 `process_mode` 记录专业输出、参考、覆盖物或原生对象的用途和处理方式
- `fidelity: exact | reference | generated`
- `file_path`、`source_ref`、`slide_id`、`review_status` 和 `exists`
- 用户指定创意、Logo、二维码、产品和批准原页必须为 `fidelity: exact` 与 `user_locked: true`

`specialist_route: focusmedia-image-gen` 和 `media_contract` 可以作为资产及页面的专业执行元数据保留，但
不能建立第二份路由或审批状态。

## 3. 知识与原件

普通内容判断先查询已审阅的正式 Markdown：

```bash
python3 scripts/focusmedia_bridge.py query "需要核实的问题" > knowledge-result.json
```

同一主题在相关页面复用结果。查询为空时记录已查范围，不自动进入研究库、原始 PPT/PDF 或在线连接器。
入口调用失败时才运行：

```bash
python3 scripts/focusmedia_bridge.py doctor
```

把返回的 `source_id`、`locator`、日期、范围和事实冲突写入页面 `source_ref` 或证据候选。只有页面明确需要
客户投放效果、原始数据、真实案例截图或原版证据页时，才查询和解析原件：

```bash
python3 scripts/focusmedia_bridge.py source "需要的原件页面" > source-candidates.json
python3 scripts/focusmedia_bridge.py resolve "frag_xxx" > source-result.json
```

PPTX 来源复制唯一原始 slide 并继承媒体关系；PDF 来源使用无改写整页图。不得用相似重制页冒充原页。
用户选择后把资产锁定；系统只检查清晰度、比例和技术可用性。

## 4. 两轮证据止损

1. 第一轮查项目材料、用户素材和官方来源。
2. 第二轮做定向搜索或候选生成。
3. 两轮仍无合格结果时，把搜索范围、拒绝原因、证据缺口和用户可执行动作写入 `evidence_state`，状态设为
   `gap`，仅暂停该页。不得用次优素材填充。

每页最多展示一个主推荐和两个真正有价值的备选。可能被误认为真实案例、真实投放或真实结果的 AI 生成
素材，在观众页显示“示意图 / AI 生成”。

## 5. 分众媒体资产链

环境图必须完成两个阶段：

1. **标准带框图**：使用已验证完整框体，只在允许替换的屏幕或海报区域精确合成客户创意，并把成品
   作为 `workflow.assets[]` 中页面绑定的专业输出保存。
2. **环境图**：以真实环境图作为空间权威，以 `framed_asset` 锁定硬件与创意，通过参考融合完成透视、
   受光、反射、接触阴影和安装关系。输出后不得平贴整台设备或补贴屏幕内容。

当前可正式使用的标准框体：

| 媒介 | `hardware_standard` | 标准文件 |
|---|---|---|
| 楼宇 LCD | `lcd-32` | `lcd-32-standard.png` |
| 32 英寸智能屏 | `smart-32` | `smart-32-standard.png` |
| 海报框架 | `poster-frame-standard` | `poster-frame-standard.png` |

智能屏只有 `smart-32` 已完成优化与验证；其他规格须具备完整标准框体、获批 manifest、几何规则和回归测试。

```bash
python3 scripts/focusmedia_bridge.py select-standard --media LCD
python3 scripts/focusmedia_bridge.py select-reference \
  --media LCD --scene elevator-hall --angle front \
  --shot-size mid --people nopeople --max-grade A
```

保留参考 ID、绝对路径、来源、媒体类型和硬件标准。候选带 `edit_transport` 时，保留原始参考图，另派生
最大边 2048px 的等比传输副本；最终验收仍以原图为准。

## 6. 页面与资产契约

涉及媒体露出的 slide 至少包含：

- `production_type` 与 `visual_role`
- `evidence_state`：候选、选中资产、两轮搜索记录、用户决议
- `source_ref`：来源文件、原页码、版本与保真信息
- `workflow.assets[]`：通过 `slide_id` 绑定真实参考、标准框体、带框图和专业输出
- 专业元数据：`specialist_route: focusmedia-image-gen`、`media_contract`
- 最终 `media_validation_report`

`media_contract` 至少记录 `medium`、`scene`、`hardware_standard`、`creative_source`、`output_type`、
`integration_mode`、`must_preserve` 和 `acceptance_checks`。`output_type: framed-demo` 使用
`integration_mode: framed-standard-composite`；`output_type: environment-image` 使用
`integration_mode: environment-reference-fusion`。

## 7. 输出验收

专业链路完成最终页面后，按 `focusmedia-image-gen` Output Check 生成与最终 PNG 文件版本绑定的
`media_validation_report`。至少验证：媒体类型、硬件结构、安装逻辑、创意准确性、环境融合、物理比例、
环境无平贴。只有不涉及环境尺度的带框演示图可把 `scale` 写为 `not_applicable` 并说明原因；其他检查不得
跳过。重新生成最终图片后，旧报告必须失效并重新验证。

交付前运行：

```bash
python3 templates/verify_page_plan.py project_snapshot.json
python3 templates/verify_focusmedia_output.py deck.json
python3 templates/verify_route_integrity.py final.pptx project_snapshot.json
python3 templates/verify_pptx.py source.pptx final.pptx
```

任一专业检查失败，回到原始环境参考与已确认带框图重新融合。`verify_pptx.py` 继续负责音视频、关系和
包内媒体保真，不得用页面截图替代媒体对象。
