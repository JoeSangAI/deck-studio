# 大纲 HTML Schema — 视觉布局描述

`assets/outline-template.html` 是一套设计过的幻灯片查看器母版：深色顶栏、章节缩略图卡片墙、1280×720
灯箱、翻页、页码、网页版/纯图版切换和讲稿层。PPT God `project_snapshot` 保存正式内容、页序、证据、
生产类型和批准状态；HTML 只描述网页版布局和纯图 prompt 的视觉槽位。`outline_to_deck.py` 把两者合并为
一次性 `deck.json` 运行清单。

正式制作时，观众文字只从 `project_snapshot.slides[]` 读取。HTML 的富内容和 `data-*` 可用于无 PPT God
状态的模板演示；一旦提供快照，它们只控制布局、背景、图像提示和讲稿呈现，不能覆盖正式文字。
`deck.json` 永远是派生物，不手改。

## 目录
1. 文件结构
2. deck-config 块
3. section 属性
4. section 内部内容（手排富 HTML）
5. 模板内建版式 CSS class（手排用）
6. 版式键表（data-layout → 纯图 prompt）
7. 派生 → prompt 的映射
8. 改字→重出图工作流

## 1. 文件结构

```
<script type="application/json" id="deck-config"> … </script>   ← deck 级配置（style 只驱动纯图版）
… 查看器 chrome（顶栏 #top / 卡片墙容器 #outline / 灯箱 #lb），内建勿动 …
<div class="stage" id="stage">
  <section class="page …" data-id data-ch data-title data-sum …> …手排富 HTML… </section>
  … 每页一个；删掉模板里的示例 section，换成你的 …
</div>
```

正式页序以 `project_snapshot.slides[].page_num` 为准，section 数量和顺序必须与之匹配。图片文件名由
`data-id` 决定（`pptimg/<id>.png`）；需要重排时先在 PPT God 改页序，再同步 HTML 布局顺序。

## 2. deck-config 块

deck 级配置的唯一权威源，`outline_to_deck.py` 读这里。`style` 槽位**只驱动「纯图版」图像 prompt，不影响网页版 CSS**（网页版皮肤固定在模板 CSS：暖纸 `#fcfbf8` + 朱砂红 `#c0392b` + 无衬线）。字段：

| 字段 | 说明 | 默认 |
|---|---|---|
| `title` | deck 标题（顶栏 + 浏览器标题） | — |
| `size` | 生图尺寸，宽高各须被 16 整除 | `3840x2160`（草稿 `2048x1152`） |
| `quality` | gpt-image-2 质量 | `high` |
| `workers` | 并发数 | `1`（稳定默认；确认额度与服务承载后才提高，最多 4） |
| `style` | 风格槽位对象（见下） | dedao 风格 |

`style` 槽位（详见 [prompt-cookbook.md](prompt-cookbook.md) §7）：`mode`(dark/light) · `accent_name` · `accent_hex` · `scene_domain`（全局主场景，无 data-bg 的页用它） · `material` · `tone_words`。**母版现在预填 dedao 图像风格**：`mode: dark` + 强调色朱砂红 `#c0392b` + `scene_domain` 电影感实拍 + `material` 暖光纪实 + film grain。（脚本内建的槽位 fallback 仍是 warm gold `#c79a5b`——仅当某槽留空时兜底，母版已填满。）

## 3. section 属性

| 属性 | 必填 | 说明 |
|---|---|---|
| `data-id` | 是 | 唯一页 id（`S01`/`K01`…）。决定图片名 `pptimg/<id>.png`，重复报错退出 |
| `data-ch` | 是 | 章节（`01 · 第一章`），卡片墙按它分组 |
| `data-title` | 模板演示时 | 无 project_snapshot 时的页标题；正式项目由快照覆盖 |
| `data-sum` | 模板演示时 | 无 project_snapshot 时的内容摘要；正式项目由快照覆盖 |
| `data-layout` | 否 | 纯图版式键（§6）。缺省按 class 推断：`finale`→back-cover、`divi`→divider、否则 content。未知键回退 content 并告警 |
| `data-kicker` | 否 | 纯图版 kicker。缺省回退 `.kick` 文本，再回退 `data-ch` |
| `data-sub` | 否 | 纯图版副题 / caption（仅纯图版用；**无 `.sub` 回退**，要进图就得写这个属性） |
| `data-bg` | 否 | 本页背景场景（英文，原样进纯图 prompt）。不填用全局 `scene_domain` |
| `data-photo` | 否 | 锁脸照相对路径（相对大纲 HTML，如 `assets/name.jpg`）。仅 `kol` 版式需要 |

## 4. section 内部内容（手排富 HTML）

**核心变化：网页版每页是你用模板内建版式 class 逐页手排的富 HTML，不再是填 `ul.items`。richness 来自逐页手排。** 灯箱 / 卡片墙直接渲染这段。

- 用 §5 的版式 class 拼版（`.kick` 起手 + `.stats`/`.pts`/`.two`/`.ladder`/… 之一撑内容）。
- 图标用 sprite：`<svg class="ic"><use href="#i-target"/></svg>`（`#i-*` 全集见 §5）。
- 讲稿：section 内放一个 `<div class="pnotes">…</div>`，只在灯箱讲稿层（N 键）显示，投影 / 纯图版不含。
- 正式项目的纯图 prompt 文字来自快照；富 HTML 和 `data-*` 只提供视觉布局与无快照模板演示。

## 5. 模板内建版式 CSS class（手排用）

模板 CSS 段内建的成套版式，直接拼用（class 名即语义）。以下为**真实存在**的版式 class（读自模板 `<style>`）：

| class | 用途 | 关键子元素 |
|---|---|---|
| `.kick` | 小标签 kicker 行（朱砂红 + 前置短横） | — |
| `h1`/`h2`/`h3` · `.lead` · `.sub` | 标题层级 / 引言 / 副题；`.r`=强调色字，h1 内 `.conv`=弱化连接符 | — |
| `.title-top` · `.title-meta` | 封面顶部标签 / 底部元信息行 | `.title-meta` 内 `span`+`i`(圆点) |
| `.divi` | 分隔页 | `.bn`(大描边号) · `h2` |
| `.stats` | 玻璃数据面板网格 | `.c` · `.ic` · `.n`(+`.u` 单位) · `.t` · `.s`(来源) |
| `.pts` | 带图标要点列表 | `li` · `b` · `.bn`(编号) · `.ic` |
| `.src` | 数据来源脚注行 | — |
| `.feat` | 单能力特写（左图右文） | `.art`+`.ic` · `h2` · `.desc` · 配 `.figs` |
| `.figs` | 数字组 | `.f`+`.fn`(数)+`.fl`(标签)+`.fs`(注) |
| `.mgrid` | 图标矩阵格 | `.m`+`.ic`+`.t` |
| `.two` | 两栏对照 | `.m`+`.h`(+`.ic`+`h3`)+`p`+`.eg`(例句) |
| `.seg` | 人群 / 分段卡 | `.badge`(+`.code`+`.ic`) · `.who` · `h2` · `.matrix` · `.desc` · `.cases`(+`.cn`+`.cl`) |
| `.funnel` | 递降漏斗 | `.fr`+`.d`(序号)+`.c`(+`.tx`+`.ft`+`.fs`+`.track`) |
| `.gap` | 虚线强调 callout | `.ic` · `.lb`(标签) · `p`(+`.r`) |
| `.chain-v` | 纵向链路 | `.cv`(+`.hl` 高亮)+`.k`(键)+`.d`(说明) |
| `.flow` | 系统环 / 流程条 | `.n`(+`.s` 副标)+`.a`(箭头) · 配 `.survey` 脚注 |
| `.hw` | 作业 / 清单行 | `.r`(+`.no`)+`.ic`+`h3`+`p`+`.tag`(+`.ok`/`.bad`) |
| `.ladder` | 台阶递进 | `.st`(+`.live` 当前)+`.ic`+`h3`+`p`+`.pr`(+`.todo`) |
| `.finale` | 收尾页 | `h1` · `.sign`(署名) |

图标 sprite（`#i-*`，用 `<use href="#i-…"/>`，共 25 个）：`growth heart bars money userplus robot film factory net target person store cart book users hub mid mask star dots link edit doc live globe`。

版式 / 图标不够用：手写内联样式或加自己的 class（网页版随便扩），纯图版不受影响（它只读 data-*）。

## 6. 版式键表（data-layout → 纯图 prompt）

**本表 key 只作用于「纯图版」prompt**（公式见 [prompt-cookbook.md](prompt-cookbook.md) §3–4）。**层 ← `data-layout`，缺省时按 class 推断**（`finale`→`back-cover`、`divi`→`divider`、否则 `content`）。选键规则：先按页型（封面/分隔/转场/大主张/封底）定特殊页，其余内容页按"内容形态"选。下表"用到的字段"现在指 data 属性：title←`data-title`、items←`data-sum` 分条、kicker←`data-kicker`/`.kick`/`data-ch`、sub←`data-sub`、bg←`data-bg`。

| key | 页型 | 用到的字段 | 渲染成 |
|---|---|---|---|
| `cover` | 封面 | title, sub, bg | 居中大标题 + 副题行 |
| `back-cover` | 封底 | title, sub, bg | 呼应封面的收尾页 |
| `divider` | 章节分隔 | kicker(章名), title(章标语), bg | 专属场景 + 章标语 |
| `transition` / `quote` | 转场金句 | title(金句), sub(注解), bg | 一句话金句页 |
| `big-idea` | 核心大主张 | title, items(3 支柱), bg | 光束 + 大标题 + 支柱 |
| `spotlight` | 机会/空位 | title(空位陈述), sub, items(我方主张) | 聚光空位 + 箭头 |
| `stats` | 数据 | title, items(3 数据), sub(来源) | 玻璃数据面板 |
| `bullets` / `points` | 论点 | title, items | 若干带线图标的要点 |
| `chips` | 关键词/心智 | items, sub | 横排标签 chips |
| `cards` | 支柱/卖点 | title, items(`标题 — 副句`) | 细长卡片 |
| `steps` / `flow` | 流程/路径 | items | 横向箭头流程 |
| `funnel` | 层级转化 | items | 递降漏斗 |
| `quadrant` | 象限/优先级 | items | 2×2 象限 |
| `two-col` | 两组对照 | items(取前 2) | 左右分栏 |
| `table` | 对应关系 | items(`行 — 值/值`) | 优雅表格 |
| `list` / `toc` | 目录/清单 | items | 编号纵列（自动加 01/02…） |
| `persona` | 人群画像 | items(`人群 · 规模 · 特征`) | 人群卡 |
| `kol` | 真人锁脸 | data-photo, kicker(标签), title(姓名), sub(身份), `items[0]`(slogan) | 右人左字，走 `/images/edits` |
| `content` | 兜底 | title, items | 通用精致排布 |

版式不够用时，在 `outline_to_deck.py` 增加有清楚边界的新 key，并用测试锁定；不要手改派生出的
`deck.json`，否则它会成为第二个内容源。

## 7. 派生 → prompt 的映射

`outline_to_deck.py` 遍历 `soup.select("section.page")`，每页 prompt = `build_style(deck-config.style)` + 该 layout 的英文公式，字段取值：

| prompt 字段 | 取自 | 缺省 |
|---|---|---|
| id | `data-id` | `S%02d`（DOM 序） |
| layout | `data-layout` | class 推断（finale→back-cover / divi→divider / 否则 content） |
| title | `data-title` | section 内 h1/h2 文本 |
| items | `data-sum` 按 `" / "` 拆 | 空 |
| kicker | `data-kicker` | `.kick` 文本 → `data-ch` |
| sub | `data-sub` | 空 |
| bg | `data-bg` | `deck-config.style.scene_domain` |
| photo | `data-photo` | 无（有则该页走 `/images/edits` 锁脸） |

公式骨架由 `outline_to_deck.py` 唯一执行；[prompt-cookbook.md](prompt-cookbook.md) 只解释当前行为。
改公式时先改脚本和测试，再更新说明；若说明滞后，以已测试脚本为准。`data-id` 重复直接报错退出；
未知 `data-layout` 回退 content 并告警。

自检：派生后先 `gen_deck.py deck.json --dry-run` 打印每页 prompt，肉眼过一遍再进样张门。

传入 PPT God 的只读 `project_snapshot` 后，派生器以 `slides[].content_json` 为唯一文字来源，并携带
`production_type`、`visual_role`、`type`、`evidence_state`、`source_ref`、`image_path`、`layout_spec`，以及
按 `slide_id` 从 `workflow.assets[]` 取出的资产。专业路由和媒体验收元数据只在真实快照中存在时携带；
这些字段不从 HTML、提示词或人工 JSON 猜测。

分众媒体页还会携带真实存在的 `media_contract` 与页面绑定资产。图片一体页的 `image_path` 是专业链路的
最终成品时，纯图生成器精确复制它，不会把它作为 photo 再送入通用图片模型。混合页和原生可编辑页由
PPT God 装配。

## 8. 改字→重出图工作流

```
先在 PPT God 修改并保存页面内容，再获取当前 revision 的 project_snapshot
按需改大纲 HTML 里该页的视觉布局描述
python outline_to_deck.py outline.html --project-snapshot project_snapshot.json
python gen_deck.py deck.json --only S07 --force  # 只重生那一页（缓存跳过其余）
python inline_html.py deck.json outline.html     # 需要自包含 HTML 时刷新
```

永远单页增量，永不整片重跑（4K 一张 120–140s + 计费）。
