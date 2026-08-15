---
name: deck-studio
description: >-
  Unified PPT production and refinement workspace for creating a new deck, improving an existing
  PPTX, revising or merging decks, and choosing the right editable, full-image, or hybrid production
  route. Preserves one coherent narrative and visual system, keeps information-heavy and multimedia
  content editable when needed, supports high-impact image pages, absorbs the former PPT Polish
  audit and repair workflow, and verifies the exact final PowerPoint artifact. Use when the user asks
  to make, redesign, polish, merge, revise, or finish a PPT, deck, presentation, slides, or PowerPoint.
---

# PPT 工作台

把“从零制作”和“已有稿精修”作为同一条 PPT 生产链。先判断最终用途和验收标准，再决定每一页用
可编辑、纯图或混合方式实现。不要让制作工具反过来决定内容结构。

## 北极星

- 最终交付对象是一套完整、连贯、可使用的 PPT，不是若干独立漂亮页面。
- 页数服务于把事情讲清楚，不设武断配额，也不为压页数牺牲论证完整性。
- 信息密集、数据、案例、多媒体和未来高频修改优先保持可编辑。
- 封面、章节、金句和关键情绪页可用纯图换取视觉冲击。
- 全册必须先定义字体家族、语义字号阶梯、Logo 安全区和页面边距；“统一”是同一层级同一规则，
  不是把所有文字设成同一字号。
- 全册必须定义页面背景规则；同类页面使用完全相同的底色值，不得混用肉眼接近但实际不同的白、
  暖灰或浅黄。整页图片等例外页型必须在页面路由中明确记录。
- 视觉统一的基本单位是“页型家族”，不是整册套一个模板。代表页通过只授权同页型批次；目录、
  章节、结构页、复杂证据页必须分别定义路由、锚点、改造强度和验收标准。
- 复杂案例、政策截图、设备说明和图墙页优先保护原有图文关系，只统一外壳；不得为了统一标题、
  色块或卡片而遮住标签、正文、截图或证据。
- 用户可能只能判断“这里不好看”而无法逐项描述。Agent 仍要主动检查视觉重心、图片关系、文字
  层级、色块语义、留白和同类页面一致性，不能把审美诊断转嫁给用户。
- 纯图页必须是有意识的页面选择；不得在合并或美化时把本应可编辑的整套正文栅格化。
- 最终验收的是实际 PPTX、真实播放路径和整册关系，不是代码成功、导出成功或中间预览。

## 1. 先识别入口

### 从零制作

读取用户材料，补齐听众、目的、场景、主线、素材、风格和硬约束。只问无法从材料推断且会改变
方向的问题。先形成页面规划和内容权威源，再生产页面。

### 内容锁定门

对客户提案、汇报和其他叙事责任较高的任务，正式设计前必须先把逐页内容逻辑给用户看懂并获得明确
确认。这个门同时适用于从零制作，以及会改变已有稿页数、顺序、主张、证据或转场的重写任务；纯视觉
精修且内容完全不动时不强制。

先在对话中用人能直接判断的逐页表呈现，再把确认结果固化为 `page_plan.json`。每页把发布内容与
工作注记分开：

- `public`：已处于可直接交付状态的客户可见文案，至少包含 `title` 与该页唯一的 `claim`；其他可见
  文案继续放在这个对象内；
- `notes`：只供策划、讲解和资料治理使用，包含 `audience_question`、`purpose`、`claim_key`、
  `evidence_source`、`speaker_line`、`transition` 与 `excludes`；
- `mode`、`production_route` 与 `overlay_policy` 保留在页级根字段：前者决定 PPT 对象形态，后两者
  决定页面如何生产、是否允许在 PPT 装配阶段后贴精确小资产。媒体图内部如何制作由
  `specialist_route` 与 `media_contract` 决定，不借用 `overlay_policy` 表达。

生成 `public` 时，把每个字段视为已经发布给外部听众的内容，只表达听众需要理解的事实、判断、行动
和必要来源。口径选择、作者决策、制作过程、待确认事项和讲解提示进入 `notes`。所有构建器、页面组件
和图片生成提示只允许读取 `public` 或已经批准复用的原始页面；`notes` 不得进入可见对象或生图提示。

`mode`、`knowledge_route`、`specialist_route` 是三条正交路线：分别决定 PPT 实现、事实来源和专业
媒体图生产。`production_route` 细分页面基底如何获得，`overlay_policy` 只限定 PPT 页面装配时精确
小资产如何后贴。它们
可以同页并存，不能互相替代。只有涉及分众知识或媒体时才增加专业路线，普通 PPT 不额外制造配置。

用户明确确认后，记录 `status: approved`、`approved_by`、`content_version` 和 `approval_scope`，再运行
`templates/verify_page_plan.py page_plan.json`。未通过或尚未确认时，只允许做结构探索和代表页风格
样张，不得生成正式页面、正式媒体环境图或批量生产整册。

如果一页承担两个独立问题或两个主张，先拆页或删减，不要靠更多卡片把冲突塞回一页。如果用户指出
“重复、逻辑不清、没话找话、这一页到底想说什么”，立即停止视觉修补，退回逐页内容图；受影响页面及
其前后转场重新确认后才恢复生产。后续局部内容变化只使受影响页及相邻转场失效，不必无条件推翻整册。

### 已有 PPT 精修

把用户提供的最新 PPTX 视为内容权威源。先审计整册与高风险页，再按
[workflows/00-router.md](workflows/00-router.md) 至 [workflows/05-deliver.md](workflows/05-deliver.md)
执行。默认保留原文案、原图、原事实和页数，除非用户明确授权改变。

### 继续修改、合并或重做

先确认最新文件和已接受版本。重建“保留、替换、新增、删除”的变更边界；不要把旧稿、不同 Agent
的局部稿或中间导出当成并列权威源。

若修改会改变内容逻辑，先执行“内容锁定门”，不能把它当成普通美化任务直接开工。

## 2. 锁定内容与整册责任

每套 PPT 只保留一个内容权威源：

- 从零制作：经确认的页面规划、网页大纲或结构化内容稿；派生配置不手改。
- 已有稿精修：用户最新 PPTX + 明确变更清单。
- 混合或多人并行：由总控 Agent 维护统一页序、叙事、视觉系统、素材映射和验收清单。

若用户要求并行制作，主 Agent 继续负责讨论、挖掘隐性知识和锁定方向；生产 Agent 只在边界明确后
制作分配页面。主 Agent 必须完成合册、去重、转场、交互和最终验证，不能把局部产物直接拼接交付。

### 已有稿的母稿与变更契约

修改已有 PPT 前，必须先形成可核验的变更契约：

- **唯一母稿**：只把用户最新确认的 PPTX 作为 canonical source；旧稿和局部稿只作背景或差异证据。
- **风格锚点**：从母稿真实内容页中，为本次涉及的页型各选 2–3 页作为视觉锚点，记录版式、字体、
  色彩、图片处理、留白和装饰语法。新增内容页必须对齐内容页锚点，不能拿封面或章节 KV 另起一套
  视觉系统。
- **页型家族**：为每个改动页标记 `image-led | native-redesign | shell-unify | preserve`，并记录同页型
  的标题、字体、背景、边距、图片处理和允许改动范围。样张确认只适用于它覆盖的页型。
- **允许改变**：逐项列出允许新增、替换、删除、重排或重写的对象。
- **必须保持**：逐项列出不得变化的文案、事实、真实 Logo、客户素材、照片主体、媒体关系和页面。

把同一契约传给所有生产参与者，并在合册时逐项验收。没有被列入“允许改变”的对象默认保持不变。
当改动覆盖 3 页以上、涉及 2 个以上页型或准备批量应用规则时，运行
`templates/verify_page_families.py page_families.json`；所有改动页必须且只能归属一个页型家族，每个
家族必须有代表页和视觉契约，`shell-unify` 还必须声明 `must_preserve`。只改 1–2 页且不批量复用
规则时，在变更契约中简要写明页型和保护边界即可，不为形式完整额外创建清单。

若任务是局部修图，必须编辑用户指定的原图；不得用重新生成整张相似画面替代局部修改。用矩形或
蒙版标出允许变化区域，保留区域外的像素、Logo、文字、人物、设备与空间关系应保持不变。可运行
`templates/verify_local_image_edit.py source.png edited.png --mask x1,y1,x2,y2` 做边界验证。

## 3. 选择生产路由

完整读取 [references/production-routing.md](references/production-routing.md)，按最终使用方式而不是 Agent
熟悉程度选择：

- **可编辑路线**：信息密集、数据图表、客户案例、多媒体、事实敏感或需要持续修改。
- **纯图路线**：演讲驱动、视觉冲击优先、文字已冻结且后续编辑需求低。
- **混合路线**：正文可编辑，封面、章节、金句或少量关键视觉页纯图；多数客户提案优先考虑。
- **精修路线**：已有 PPT 内容基本成立，主要问题是视觉、结构、可读性或兼容性。

不要把“代码生成”和“好看”对立。可编辑路线仍应从客户 KV、品牌色、Logo、安全区和固定视觉语法
建立整册设计系统；必要时再用精修能力提升完成度。

每页必须明确一种 `production_route`：

- `source-preserve`：复杂原页、案例、证据页或已批准页面；绑定唯一母稿路径、文件 checksum 和页码，
  原生复制对象与媒体关系。需要局部修改时配 `overlay_policy: local-patch` 和明确蒙版。
- `native-editable`：数据、表格、事实敏感内容、持续修改页面；必须使用 `mode: editable`。
- `ppt-god-full-image`：文字冻结、视觉冲击优先且没有精确媒体硬件的整页图；必须使用
  `mode: image`，默认不后叠正文。
- `reference-fusion`：整页图中包含真实媒体、产品、人物或其他必须保真的视觉资产；必须带实际
  存在且 checksum 匹配的 `reference_assets`，由专业图片 Skill 或支持参考编辑的图片能力完成。
  若整册由 PPT God 管理，验收通过后用 `import-slide-image` 将完整页面图接回原项目。

`overlay_policy` 只取 `none | logo-only | precision-assets | local-patch`。`precision-assets` 仅允许 Logo、
二维码、法务标识和截图等需要像素级准确的小对象。屏幕或海报创意不属于 PPT Overlay：它必须先在
专业媒体路线的标准带框图中锁定。人物主体和页面主构图也进入参考融合。

### 分众项目扩展

当项目、客户材料或任一页面涉及分众传媒、Focus Media、电梯电视/LCD、智能屏、框架海报、分众
方法论、历史案例或真实媒体环境时，先完整读取
[references/focusmedia-integration.md](references/focusmedia-integration.md)，再按其中要求完整读取
`focusmedia-knowledge` 与 `focusmedia-image-gen` Skill。

该引用统一负责分众知识查询、原件解析、标准框体、媒体资产链、页面契约、桥接命令和最终验收。
普通 PPT 不加载该引用，也不增加分众字段。分众入口、真实参考或专业验收缺失时停止对应页面，不降级
为通用知识或通用生图。

## 4. 执行所选路线

### 可编辑或混合

使用当前可用的专业 PowerPoint 生产能力生成原生文本、形状、图表和媒体关系。若已安装
`presentations` Skill，完整读取并遵守它的 PPTX 生成与验证要求。

- 标题、正文、图表、表格、视频入口和需要继续修改的对象保持原生可编辑。
- 客户 Logo、产品图、截图、二维码、最终 KV 和事实证据使用原始资产，不重新生成。
- 路由为 `image` 的封面、章节和金句页，按 PPT God 方法让图片模型一次生成包含标题与正文的
  完整 16:9 页面；不要默认拆成“无字底图 + 二次文字层”。生成后逐字、逐行检查，只有实际出现
  错字或排版问题时才改单页。
- 图片页验收必须同时满足：最终文案已在成图内逐字正确呈现；默认只保留单一整页图片。只有路线
  清单明确批准的 Logo 或 `precision-assets` 可以后贴，且数量必须与清单一致；不得后叠标题、正文、
  屏幕创意、整台媒体设备或用于掩盖生图错误的图层。若不满足，视为图片路由失败，必须整页重生或使用图片
  编辑模型修正后再交付。
- Logo 是纯图页的例外：图片模型不得生成 Logo；导出时必须使用已确认的真实 Logo 资产作为独立
  PPT 图层后贴，并保留稳定位置、尺寸和安全呼吸区。
- 合并不同来源页面后，必须显式统一字体并把零散字号收敛到语义字号阶梯；不得保留大量
  `inherit` 字体或 15.8、17.2、18.8 等由缩放产生的碎片字号。
- 对本轮新增或重做的可编辑页单独运行限定范围的字体审计；保留页中的历史字体不能成为新增页
  字体回退的借口。
- 嵌入或链接视频时验证实际点击/播放路径；截图或封面图不能冒充可播放视频。
- 混合装配时只把明确标记为 `image` 的页面做成全页图片；其他页面不得因合册而栅格化。
- 完成初稿后，可使用本 Skill 的精修工作流统一样式和修复细节。

### 纯图

先完整读取：

- [references/interview.md](references/interview.md)
- [references/outline-schema.md](references/outline-schema.md)
- [references/prompt-cookbook.md](references/prompt-cookbook.md)
- [references/pitfalls.md](references/pitfalls.md)

执行：访谈与页面规划 → 逐页叙事图确认 → 网页大纲定稿 → 派生 `deck.json` → 代表页样张 → 批量生图
→ 逐页校对 → 装配 PPTX。文字只活在大纲 HTML 的同一 `section` 中，`deck.json` 是派生物。错页只
重出单页。

### 已有稿精修

按六阶段执行：`router → analyze → design → execute → verify → deliver`。需要时调用：

- `templates/deck_audit.py`：整册审计
- `templates/reskin_cli.py`：视觉统一
- `templates/verify_pptx.py`：内容与资源保真
- `templates/chart_builder.py`：可编辑图表

需要 AI 氛围底图时走当前图片生成 Skill，并把产物作为明确的图片资产装配、检查；不要使用
`reskin_cli.py --ai-bg`，该旧参数从未形成可验证装配闭环，现会明确失败。

详细知识按问题读取 `knowledge/`，交付底线读取
[knowledge/quality-bar.md](knowledge/quality-bar.md) 和 [knowledge/check-list.md](knowledge/check-list.md)。

## 高效执行约束

- 多页共享同一视觉规则时，先验证每种页型的一张代表页，再批量执行；不要逐页重复设计和渲染。
  已通过的代表页不能外推到未覆盖的页型，高风险复杂页必须另设锚点或采用 `shell-unify`。
- 每个阶段主上下文最多查看一张轻量 WebP contact sheet。“逐页检查”是 contact sheet + 全量自动检查，
  不是依次打开所有单页；只对异常页和高风险页查看降采样单页。
- 缺少编辑操作时只做一次针对性文档搜索和一个最小探针；仍不明确就切换已知路线，不在交付任务中
  反复研究 API。

## 5. 最终验证

在说“完成”前必须：

1. 打开或渲染最终 PPTX，而不是中间文件；
2. 用一张轻量 WebP contact sheet 逐页检查全部改动页和整册关系；只把其中发现问题或属于高风险页型的
   页面单独降采样检查，不把原尺寸总览或全部单页图片依次注入主上下文；
3. 重查用户此前指出过的问题类型；
4. 检查文字溢出、遮挡、换行、比例、层级、Logo、品牌色、图表和多媒体交互；
5. 对已有稿运行 `templates/verify_pptx.py source.pptx output.pptx` 与文件完整性检查；
6. 运行 `templates/typography_audit.py`，确认字体家族、继承字体和字号阶梯符合本次设计系统；
   对新增或重做页使用 `--include-slides`、`--allowed-fonts` 和 `--fail-on-inherited` 做限定范围硬检查；
7. 若视觉契约定义了统一底色，运行 `templates/verify_background_consistency.py final.pptx --expected <HEX> --exclude-slides <纯图页>`，确认所有同类页面使用同一精确色值；
8. 对混合稿维护含 `mode`、`production_route`、`overlay_policy` 的页面路线清单，并运行
   `templates/verify_route_integrity.py final.pptx route_manifest.json`，确认可编辑页仍含原生
   文本/图表/媒体，纯图页、Overlay 和专业资产只出现在批准的页型和数量；
9. 对多页、跨页型或批量任务运行 `templates/verify_page_families.py page_families.json`，确认改动页
   家族覆盖完整且没有跨家族误用；局部 1–2 页任务只核对变更契约；
10. 把所有新增页和显著改版页放入同一张轻量 contact sheet，与变更契约指定的同页型风格锚点并排核验；
   同时按页型家族检查标题尺度、背景、构图母题和改造强度，不能只看单页是否漂亮；
11. 对局部修图运行 `templates/verify_local_image_edit.py`，确认允许区域外没有未授权变化；
12. 对分众项目完整执行
    [references/focusmedia-integration.md](references/focusmedia-integration.md) 的知识、原件、媒体资产与
    Output Check 验收；
13. 明确区分已直接验证、合理推断和仍待用户确认的内容。

任何一项不通过，都回到对应生产阶段修复根因，不能用“导出成功”替代成品验收。

## 6. 能力积累

真实反馈先进入具体案例，再决定是否升级方法：

- 个案问题与解法：本地 `cases/`（默认不进入公共仓库）
- 稳定视觉与兼容知识：`knowledge/`
- 可重复确定性能力：`templates/` 或 `scripts/`
- 纯图产线规则：`references/`

只有跨案例成立的规律才进入主流程；不要把一次性偏好写成所有 PPT 的硬规则。

### 升级抽象门

每次把真实反馈升级进 Skill 前，先做一次范围审计：

1. **先找所有者**：确认这是 Deck Studio 的长期职责，不是某个客户品牌、单一生成工具或一次性
   项目的局部事实。
2. **再看证据强度**：至少满足一项才可进入主流程——两个不同项目重复出现；根因属于 PPTX/Office
   等稳定机制；或用户明确声明为跨项目长期偏好。只有一个案例且例外很多时，留在 `cases/` 或
   条件性 `knowledge/` 中。
3. **写出反例**：主动提出一个不该使用该规则的合理场景。若找不到清楚边界，不把它写成硬规则。
4. **匹配自由度**：审美判断和页型选择用条件性原则；稳定操作流程用步骤；字体落盘、页数、背景
   色和路由完整性等客观不变量才做脚本与硬门槛。
5. **去项目化**：客户名、页码、指定字体、指定色值和具体构图只留在案例或项目视觉契约；主流程
   只保留选择方法和验收机制。
6. **控制成本**：新步骤带来的可靠性收益必须大于流程负担。小任务可用简短契约解决时，不强制
   创建清单、配置或新文件。

升级后至少做一个反例检查和一个正例回归；如果规则只在原案例成立，就降级回案例知识。
