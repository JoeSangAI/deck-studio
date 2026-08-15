# 阶段 3：执行（Execute）

## 目标
按设计稿和页型批次修改：先验证代表页，再复用同一规则批量执行，避免逐页重复推理，也避免未经验证就
一次性重做整册。

## 必做事项

### 3.1 代表页 → 同页型批次 → contact sheet

- 单页独有问题：只改该页并渲染该页。
- 多页共享同一视觉规则：每种页型先选一张代表页，修改并渲染通过后，再批量应用到同页型页面。
- 每个批次完成后生成一张轻量 WebP contact sheet 做整体检查；不要默认把批次内每页逐张打开。
- 自动检查覆盖全部页面；只有 contact sheet 发现问题、用户点名或属于高风险页型的页面才单独降采样查看。

节奏：
```
确定页型 A → 改代表页 A1 → 渲染确认
批量处理 A2–A8 → contact sheet 检查 → 只修异常页
确定页型 B → 改代表页 B1 → 渲染确认
```

### 3.1.1 限制工具探索

优先使用 `presentations` Skill 已给出的稳定接口和示例。遇到缺失操作时，只允许一次针对性文档搜索和
一个最小探针；仍不明确就切换到已知可靠的编辑路线。不要在交付任务中反复读取整套 API 文档或创建
多个一次性 probe 脚本。

处理三页以上的同类页面时，把字体、颜色、间距、页眉页脚和卡片等写成共享 helper，把每页差异写成
结构化数据。不要为重复版式手写上千行逐页代码。

### 3.2 关键操作清单

#### 图片缩放（必须保比例）
```python
ratio = orig_w / orig_h
new_w = ratio * target_h
new_h = target_w / ratio  # 二选一，按需
```

详见 `templates/preserve_ratio.py`

#### 窄容器两行文本
```python
# 主信息（日期）在上，副信息（周数）在下
p1.alignment = PP_ALIGN.CENTER
r1.text = "12.21-12.27"
r1.font.size = Pt(10)
p2 = tf.add_paragraph()
p2.alignment = PP_ALIGN.CENTER
r2.text = "(1周)"
r2.font.size = Pt(8)
```

详见 `templates/two_line_text.py`

#### Z-order 调整
```python
# 把指定元素移到 spTree 末尾（最上层）
for i, child in enumerate(spTree):
    tag = child.tag.split('}')[-1]
    if tag in ['pic', 'sp', 'grpSp']:
        # 判定条件：名字/类型
        if '目标名字' in child.xml:
            spTree.remove(child)
            spTree.append(child)
```

详见 `knowledge/z-order-rules.md`

#### 日期 → 累计天数 → x 坐标
```python
def date_to_cumulative(m, d):
    days_map = {6: 0, 7: 30, 8: 61, 9: 92, 10: 122, 11: 153, 12: 183, 1: 214}
    return days_map[m] + d - 1
```

#### 装饰线删除
**直接删元素**比"挪位置 + 改颜色"更可靠。

#### 装饰线去重/复用（新增前必做）
```python
def in_header_band(shape):
    return shape.top < Inches(1.05)

def is_decorative_line(shape):
    # line 或极薄矩形都算装饰线
    return shape.shape_type == 9 or (shape.height < Pt(8) and shape.width > Inches(1.0))

header_lines = [s for s in slide.shapes if in_header_band(s) and is_decorative_line(s)]
```

执行规则：
- 同一页眉区域已有长线时，不再新增第二条长线；只复用原线或统一颜色/粗细。
- 长线、短强调线、页脚线按角色分组，每个角色最多保留一条。
- 若新增装饰线与图片 bbox 相交，先删线或移动到图片区外，不移动图片主体。
- 图片 top < 1.0" 且图片跨过页眉线位置时，这页默认禁用页眉装饰。

#### 重复标题冲突处理
```python
top_titles = [
    s for s in slide.shapes
    if s.has_text_frame and s.text_frame.text.strip()
    and s.top < Inches(0.8) and s.width > Inches(8)
]
```

执行规则：
- 如果同时存在 `PLACEHOLDER` 标题和模板标题（常见名称：`标题 1`、`Title 1`），先对照原稿截图判断哪个可见。
- 原稿不可见的占位标题不要删除文本；用背景色 + 1pt 字号隐藏，确保 `verify_pptx.py` 仍能通过文本保真。
- 不要把所有 likely title 移到同一个坐标；同页多标题时只统一可见标题的字体/颜色。

#### 复杂截图/社媒案例页跳过文本重染
以下页面默认不批量重染内部文本：
- 笔记本/手机界面截图页
- 社交媒体话题效果页
- 图片上叠加白字、黑字、红字的复合图层页
- 多张截图拼贴且文字直接压在截图/遮罩上的页面

这类页面只处理外层标题、logo、页眉；内部说明文字保持原色，避免黑字变白、白字变黑导致信息丢失。

#### 小插图资产抠图
GPT Image 2 生成的小插图默认是白底或纯色底，不请求透明底。生成后先做本地抠图：

```bash
python3 templates/illustration_cutout.py input.png \
  --output output_cutout.png \
  --mode auto \
  --fallback-card output_card.png
```

执行规则：
- 只在稀疏页、概念页、章节页使用；密集页默认不用。
- 抠图脚本只删除边缘连通背景，避免误删主体内部白色细节。
- 抠图失败时使用 fallback card 或弃用插图，不强行透明化。
- 插入 PPT 时等比缩放，放在正文和 logo 下层，不压字。

#### 可编辑图表生成
图表必须来自已确认数据或用户提供的 `chart_spec.json`，不从语气或标题里猜数值。

```bash
python3 templates/chart_builder.py input.pptx \
  --output output.pptx \
  --spec chart_spec.json \
  --primary "#C9A84C" \
  --secondary "#4A3F35"
```

执行规则：
- `line` / `bar` / `column` / `pie` / `radar` 使用 PPT 原生 chart。
- `series.values` 必须和 `categories` 等长；`pie` 只能一个 series。
- 图表插入后检查标签、图例、坐标轴是否互相压住。
- 图表属于内容层，不能被装饰线、插图或截图覆盖。

### 3.3 边改边记
每改一处，立刻在脑子里过一遍：
- 这个改动有没有副作用？
- 有没有破坏 z-order？
- 有没有让其他元素错位？

如果改完发现新问题，**先停下，回退**，不要继续改。

## 3.4 视觉统一（用 reskin_cli.py）

如果分析阶段发现"配色字体乱"是主要问题，可以用 reskin_cli.py 一键处理：

```bash
python3 templates/reskin_cli.py input.pptx \
  --output output.pptx \
  --primary "#D89A3D" --secondary "#3D2B1F" \
  --title-font "Arial" --body-font "微软雅黑"
```

**reskin_cli 做了什么**：
- 统一主标题字体（仅宽度 > 10 英寸的大文本框，不动正文/图表/脚注）
- 元素少的页面：可选顶部/底部强调线
- 跳过 `--skip-slides` 指定的页（封面/章节页/封底）
- 自动验证文字/图片/视频完整保留

使用 `--accent-bar-top` / `--accent-bar-bottom` 前，必须先确认模板没有已有同角色装饰线；如果原模板已有页眉/页脚线，优先跳过新增装饰线。

**reskin_cli 不会做什么**（需要 execute 阶段手动处理）：
- 不修图压字、文字溢出
- 不改 Z-order
- 不重排日期轴

## 3.5 高清产品底图（仅适用于可编辑 / 混合页）

本节只用于页面路由为 `editable`、且标题与正文需要保留为 PowerPoint 原生文字的场景。不要把这套
“无字底图 + 原生文字层”的做法套用到 `image` 路由页。

当页面路由为 `image`（如封面、章节、金句页）时，必须先执行已批准的 `production_route`：无精确
视觉资产用 `ppt-god-full-image`；包含真实媒体、产品、人物或批准页面用
`reference-fusion`，实际参考文件与 checksum 必须进入运行清单。后一条先由专业图片能力完成并验收，
再用 PPT God `import-slide-image` 原样接回原项目。专业成品不能进入通用图片模型二次生成；
`gen_deck.py` 对 `full-slide` 分众资产只做 checksum 校验与精确复制。生成后逐字、逐行检查，只定向
重出问题页。

Logo、二维码、法务标识和截图等必须精确的小资产按 `overlay_policy` 处理：真实文件逐项登记，
数量与路线清单一致，并预留自然连续的安全区。屏幕创意先在分众标准带框阶段精确合成；环境阶段
使用带框图与真实环境图做参考融合，最终结果不得整机平贴或补贴屏幕。

当封面/封底需要产品匹配时：

1. 用产品图提取色系和构图方向，生成**无文字、无 logo、无产品标签**的 16:9 高清底图。
2. 真实产品图只作为 PPT 图层按比例叠加；若原图低清，只做局部主体或参考，不放大铺满。
3. 标题卡必须用深色文字 + 高对比浅底，不能依赖半透明白字。
4. logo 用 PNG/JPEG 资源，避免 SVG/bin 在 PowerPoint 中出现红叉。
5. 导出后检查最终 PPTX，而不是只看生成底图。

详见 `knowledge/product-backgrounds.md`。

## 3.6 PowerPoint 兼容兜底

如果出现“渲染预览 OK，但 PowerPoint 打开不 OK”：

1. 查最终 PPTX 的 `ppt/slides/slideN.xml`，确认关键文字的 `a:srgbClr` 和 `sz` 是否真实写入。
2. 如果 artifact-tool/python-pptx 的样式没有落到 XML，做**窄范围**后处理：
   - 只改指定 slide、指定 shape id、指定文本的颜色/字号/位置
   - 不批量改全局主题
   - 改完必须重新渲染最终 PPTX 并跑 `templates/verify_pptx.py`
3. SVG/bin/logo 失效时，替换成 PNG/JPEG；不要保留可能红叉的资源。
4. 兜底操作写入案例，说明“预览和 PowerPoint 实际打开不一致”的根因。

详见 `knowledge/pptx-compatibility.md`。

## 3.7 新增内容图层顺序

新增小插图或图表时，按以下顺序确认层级：

```
背景 / 底图 → 装饰元素 → 原始图片 / 图表 / 插图 → 正文文字 → 标题 / logo
```

如果图表或插图与原始内容冲突，优先缩小或弃用新增元素，不移动用户原始关键信息。

## 3.8 字体与字号规范化

1. 从设计稿读取字体家族和允许字号阶梯，不在执行脚本里临时发明字号。
2. 给所有可编辑 run 显式设置字体；需要兼容时同时写入 `a:latin`、`a:ea`、`a:cs`。
3. 按语义角色映射字号，而不是按当前字号机械取整。普通页主标题、卡片标题、正文和来源必须分别处理。
4. 合并不同尺寸或不同母版的页面后，清理缩放产生的碎片字号。
5. 因规范化产生溢出时，优先扩大文本框、调整换行或重排内容；不要退回单页特例小数字号。
6. 执行后运行：

```bash
python3 templates/typography_audit.py output.pptx \
  --allowed-fonts "目标中文字体" \
  --allowed-sizes "7.5,9,10.5,12,13.5,15,16.5,18,21,24,30,36,44" \
  --fail-on-inherited
```

## 反面示例（禁止）

- ❌ 未验证代表页就一次性写一个大脚本跑完整册
- ❌ 对同一页型机械执行“改一页、渲染一页、查看一页”
- ❌ 把重复视觉规则复制成上千行逐页代码
- ❌ 为一个编辑操作反复读 API 文档并创建多个 probe 脚本
- ❌ 用 try/except 吞错（掩盖问题）
- ❌ 改 Z-order 时不用 replace_all（容易漏）
- ❌ 模板已有页眉线时继续新增一条平行线
- ❌ 图片顶到页眉安全区时仍加横线
- ❌ 把隐藏占位标题重新染成可见标题
- ❌ 对复杂截图页批量重染内部文字，导致白底黑字变白字
- ❌ 把低清产品截图直接放大成封面/封底背景
- ❌ 生成含伪文字/伪 logo 的 AI 背景后再用遮罩“遮一下”
- ❌ GPT Image 2 插图请求透明底，或把伪文字插图放进 PPT
- ❌ 图表数据来源不明时自行补数
- ❌ 图表、插图插入后不检查是否压住文字/logo
- ❌ 只看中间预览，不检查最终 PPTX 中的真实文字颜色/资源类型
