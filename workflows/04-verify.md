# 阶段 4：验证（Verify）

## 目标
改完后不能直接交付。必须自己跑一遍 `knowledge/check-list.md` 的全部检查。

## 必做事项

### 4.1 渲染全图
```bash
soffice --headless --convert-to pdf output.pptx
pdftoppm -r 200 output.pdf verify -png
```

渲染对象必须是**最终交付 PPTX**，不要用中间导出图或未后处理的临时文件。

### 4.1.1 分层视觉检查

按以下顺序验证，后层只处理前层发现的风险：

1. 对全部页面运行自动保真、字体、溢出、资源和包完整性检查；
2. 用 `scripts/contact_sheet.py` 或 artifact-tool montage 导出一张轻量 WebP 总览，建议
   `slideWidth=320`、4–5 列；主上下文只查看一次，不使用原尺寸 PNG 总览；
3. 同时按页型家族生成并排视图，检查同家族标题尺度、背景、构图母题、图片处理和改造强度；
4. 从总览中标记异常页和高风险页，只把这些页面降采样到约 1280–1500px 后单独查看；
5. 单页修复后只重新渲染该页和受影响的 contact sheet，不重新逐张查看全部已通过页面。

contact sheet 是逐页视觉总览，不等于跳过页面；自动检查负责文字和结构，单页大图负责解决明确视觉
问题。不要用 `detail=original` 依次打开全部改动页。

### 4.2 逐页对照检查清单
在 contact sheet 和自动检查中对每一页，对照 `knowledge/check-list.md`：

- [ ] 没有装饰线压图
- [ ] 没有图片压字
- [ ] 没有文字溢出
- [ ] 元素比例正确
- [ ] Z-order 正确
- [ ] 字体一致
- [ ] 配色统一
- [ ] ...

同时对照 `knowledge/quality-bar.md`。硬门槛不通过时不能交付。

### 4.2.1 自动保真检查

用户要求内容不变时，必须跑：

```bash
python3 templates/verify_pptx.py source.pptx output.pptx
# 仅用于多页、跨页型或批量任务
python3 templates/verify_page_plan.py project_snapshot.json
python3 templates/verify_page_families.py project_snapshot.json
python3 templates/verify_route_integrity.py output.pptx project_snapshot.json
python3 templates/verify_workflow_ready.py project_snapshot.json final_preflight.json
python3 templates/typography_audit.py output.pptx
python3 templates/typography_audit.py output.pptx \
  --include-slides <新增或重做页> \
  --allowed-fonts "<目标字体>" \
  --fail-on-inherited
unzip -t output.pptx
# 含分众媒体整页图时，先完整读取 references/focusmedia-integration.md
python3 templates/verify_focusmedia_output.py deck.json
```

最低通过项：
- 页数一致
- 原稿可见文字在新版对应页保留
- 图片数量未异常减少
- 没有 SVG/bin/logo 导致的高风险资源（或已明确替换）
- 关键文本颜色/字号存在于最终 PPTX XML
- 字体家族、继承字体与字号阶梯符合本次设计系统
- 多页、跨页型或批量任务中，本轮所有改动页均且仅属于一个已定义页型家族
- 分众媒体页的最终图片、参考 ID/checksum、媒体契约和六项 Output Check 与验收报告一致
- `image_integrated` 页只有一张全页位图及获准小覆盖物，`hybrid` 页保留关键原生对象，
  `native_editable` 页未被栅格化
- 四个 Gate 已批准、阻断问题已关闭并复验、正式预检 revision 与项目 revision 一致

### 4.3 找差异
对比"原始 PPT"和"修改后 PPT"的截图：
- 哪些问题已修复？
- 哪些问题没改？
- 哪些问题是新引入的？

额外检查：
- PowerPoint 截图里是否有红叉/坏图占位符
- 封面/封底标题在真实打开状态是否清楚
- AI 背景是否糊、是否补丁感、是否含伪文字/伪 logo
- 小插图是否真透明、是否误删主体、是否压住文字/logo
- 可编辑图表是否保留为 PPT chart、数据是否和 spec 一致
- P3/P4 这类时间轴页，年度/月份/标签是否压边框
- 页眉/页脚是否出现重复装饰线，尤其是原模板已有线又新增线的页面
- 顶部 1 英寸内有图片墙/截图时，是否有装饰线穿过图片
- 是否存在多个标题在页眉区重叠；重点检查占位标题被重新染出的页面
- 复杂截图/社媒案例页的叠加文字是否完整可见，不能只看 `verify_pptx.py` 文本存在

### 4.3.1 反馈高风险页抽查

用户反馈过一次的问题类型，后续同类 deck 必须增加抽查：

| 问题类型 | 必查页面 |
|----------|----------|
| 装饰线重复 | 所有内容页页眉/页脚，尤其是带 logo 模板页 |
| 装饰线压图 | 顶部图片墙、活动照片、全屏截图页 |
| 标题冲突 | 顶区有 2 个以上宽文本框，或占位符标题 + 模板标题同时存在的页 |
| 信息丢失 | 社媒截图页、电脑屏幕页、深色遮罩上叠文字的页 |
| 页型规则误用 | 所有未被代表页直接覆盖的页型，尤其是复杂证据页 |
| 字体回退 | 所有新增或重做的可编辑页，特别是深色图片页上的大标题 |
| 底色不一致 | 所有声明为同一正文家族的页面 |
| 视觉关系不成立 | 用户评价“不好看”“位置奇怪”但未给像素级修改要求的页面 |

自动文本保真只能证明“XML 里还有字”，不能证明“肉眼可见”。这些问题必须通过最终截图或
PowerPoint/WPS 实际打开检查。用户点名页、显著重做页和最高风险页至少各抽一页真实打开。

### 4.4 准备对比报告
```
| 页面 | 原问题 | 改后状态 | 是否通过 |
|------|--------|----------|----------|
| P2   | 文字溢出 | 已加换行 | ✅ |
| P3   | 日期轴错位 | 已重排 | ✅ |
| P5   | 装饰线压图 | 已删除 | ✅ |
| P8   | 图片压字 | 已调整 | ✅ |
```

## 验证不过怎么办

1. **回到 analyze 阶段**：是不是漏识别了问题？
2. **回到 design 阶段**：方案是不是没覆盖？
3. **回到 execute 阶段**：代码是不是写错了？
4. **不要原地继续改**：先诊断根因再动手
5. **预览和 PowerPoint 不一致**：查 XML 和资源类型，再做窄范围兜底

## 反面示例（禁止）

- ❌ 改完不渲染就说"应该好了"
- ❌ 渲染了一页就交付（"其他页应该差不多"）
- ❌ 不对比就交付（"我记得改过了"）
- ❌ 验证时发现新问题但不回退（"应该没人会看到"）
- ❌ 只看 artifact/LibreOffice 预览，不看最终 PPTX 的真实样式和资源
- ❌ 只跑文本保真就认为没有信息丢失，忽略文字颜色/层级导致的视觉不可见
