# Prompt Cookbook — 每页 prompt 由脚本派生的公式书

deck-studio 里**每页 prompt 不是手写的**，是 `outline_to_deck.py` 从大纲 HTML 每个 `section.page` 派生的：
`prompt = build_style(deck-config.style) + [该 data-layout 的英文公式]`，填入 title(`data-title`) / items(`data-sum` 按 ` / ` 拆) / sub(`data-sub`) / kicker(`data-kicker`/`.kick`/`data-ch`) / bg(`data-bg`)。
你只拧两个旋钮：(a) 每页 `<section data-layout>` 键，(b) deck-config `style` 槽位。本文件解释脚本实现的公式和旋钮怎么调；不要手改派生出的 `deck.json`。

> **权威边界**：内容文字只在大纲 HTML；公式实现只在 `scripts/outline_to_deck.py`。本说明用于理解
> 和审阅，不是第二份可执行实现。改公式时用测试锁定脚本，再同步更新本表。

## 目录

1. STYLE 全局块（build_style）
2. 内容页公式（build_content 包壳）
3. 特殊页公式（build_special）
4. 内容页版式词汇表（build_content body）
5. 背景场景写法（data-bg / scene_domain）
6. 真人锁脸页（kol 版式 / /images/edits）
7. 换风格改哪里（deck-config.style 槽位）
8. 文字渲染规则

## 1. STYLE 全局块

`build_style(style, size)` 每页自动拼在 prompt 开头，你**只填 deck-config.style 槽位**，不手写这段。它**只驱动纯图版图像，不动网页版 CSS**（网页版皮肤固定在模板：暖纸 `#fcfbf8` + 朱砂红 `#c0392b`）。母版现在预填 dedao 风格（dark + 朱砂红 `#c0392b` + 电影感实拍纪实）；下面这段是**槽位留空时的脚本 fallback 产出**（黑金 editorial，warm gold）：

```
Ultra-premium 16:9 editorial keynote slide, {size}, ART-DIRECTED like a high-end brand campaign deck — NOT a plain text-on-a-flat-color slide. A softly-lit cinematic background photograph (gently out of focus) gives the page atmosphere and depth, with an elegant dark gradient overlay (deeper where text sits) for legibility. Sophisticated layered, asymmetric composition, clear visual hierarchy, generous breathing room. Typography: refined MEDIUM-WEIGHT clean modern sans-serif Chinese with standard square (方块字) proportions — elegant and clearly readable, but NOT oversized and NOT heavy/bold; a small letter-spaced kicker, a medium title, small body text. warm gold (#c79a5b) thin hairline rules and small tasteful accents. brass accents, gentle bokeh for material atmosphere. Cohesive, expensive, magazine-quality. Render every Chinese character and number correctly and crisply. 
```
（末尾 `brass accents, gentle bokeh for material atmosphere.` 来自 `material` 槽位，留空则省略。）

每个短语的职责（换风格时哪些能动见 §7）：
- `ART-DIRECTED … NOT a plain text-on-a-flat-color slide`：防退化成字幕板。
- `cinematic background photograph (gently out of focus) + dark gradient overlay (deeper where text sits)`：给氛围又保可读；**页面级的虚化/压字区在这里已声明**，所以 data-bg 只需给场景主体（§5）。
- `MEDIUM-WEIGHT … NOT oversized … NOT heavy/bold` + `standard square (方块字) proportions`：字号字重字形铁律（返工换来的结论），全片一致。
- 结尾 `Render every Chinese character and number correctly and crisply`：保中文不画错。

被 style 槽位替换的位置：`{size}`←`deck-config.size`；`dark gradient` 段 / `clean` 字色←`mode`（light 时换 BRIGHT 背景 + soft bright gradient + `deep charcoal` 字色）；`warm gold (#c79a5b)`←`accent_name (accent_hex)`；`brass accents, gentle bokeh for material atmosphere.`←`material`（留空则省略）；`expensive, magazine-quality`←`tone_words`。

## 2. 内容页公式（build_content 包壳）

所有**非特殊**版式共用一个壳，body 由版式决定（§4）：

```
Background: {data-bg}. The text sits over {text_side}. [Small {accent_name} kicker '{kicker}'; ] [medium title '{title}'. ] <§4 的 body 句式> [Small caption '{sub}'. ] Keep text MEDIUM-sized and medium-weight, elegant and readable, well-composed with breathing room.
```

- `{text_side}` 随 `mode` 变：dark = `the darker gradient side`，light = `the softly shaded side`（与 §1 的渐变方向一致）。
- `kicker` 段在 kicker（`data-kicker`/`.kick`/`data-ch` 任一）非空时出现（几乎总在）；`title` 段仅在 title（`data-title` 或 h1/h2）非空时出现；`caption` 段仅在 `data-sub` 非空时出现。
- 结尾 LOCK 句每页恒带，锁字号字重。
- kicker 用 `accent_name`（如 warm gold），不带 hex。

## 3. 特殊页公式（build_special）

特殊页**不套 §2 的壳**，各自是独立整句（同样拼在 STYLE 块之后）。`{accent}` = `accent_name`；`{grad}` = dark 时 `dark gradient`、light 时 `a soft bright gradient`。

| key | 脚本句式骨架 |
|---|---|
| `cover` | `COVER. Background: {bg}. Centered: an elegant medium-large title '{title}'; below a small line '{sub}'. Atmospheric, refined, not bold. ` + LOCK |
| `back-cover` | `BACK-COVER. Background: {bg} at dusk, deep mood. Centered: an elegant title '{title}'; a small line below '{sub}'. Minimal, refined. ` |
| `divider` | `SECTION DIVIDER. Background: {bg}, cinematic, atmospheric, {grad}. Centered-left: a small {accent} tag '{kicker}', a large but elegant (not heavy) title '{title}'. Minimal, premium, lots of mood. Render the Chinese text crisply. ` |
| `transition`（别名 `quote`） | `SECTION TRANSITION. Background: {bg} at dusk, deep mood. Centered: an elegant (not heavy) line '{title}'; a small subtitle '{sub}'. ` |
| `big-idea` | `BIG-IDEA slide. Background: {bg} with a single hero light beam, deep mood. Small kicker 'BIG IDEA'. A large elegant {accent} title '{title}'.[ Below, {n} refined pillars: '…' / '…' / ….] Medium text, not heavy. ` |
| `spotlight` | `Background: {bg} with a single warm spotlight on an empty space. A large highlighted {accent} panel '{title}'. Below, a small line '{sub}'.[ An arrow to '…', ….] ` + LOCK |
| `kol` | 见 §6（走 `/images/edits`） |

要点：全片只有 `cover` 主标题、`big-idea` 标题、`divider` 标题可 large，且脚本已写死 `elegant / not heavy`。`big-idea` 的 kicker 固定为 `'BIG IDEA'`（不取 data-kicker）；pillars 段仅在有 items 时出现。`spotlight` 的 items 渲成"箭头指向我方主张"，仅在有 items 时出现。

## 4. 内容页版式词汇表（build_content body）

`data-layout` 选键规则：特殊页型先按 §3；其余按"内容形态"选下表。body 句式里 `'…'` = `data-sum` 按 ` / ` 拆出的每条逐字（脚本 `q()` 加单引号，直引号 `'` 会被换成 `'`）。`{N}` = 条目数英文词（One…Six，>6 用数字）；`{accent}` = accent_name。

| key | 渲染成 | 脚本 body 句式骨架 |
|---|---|---|
| `stats` | 玻璃数据面板 | `{N} elegant glass-like stat panels with thin {accent} borders: '…', '…', …. ` |
| `bullets`（别名 `points`） | 带线图标要点 | `{N} calm points with thin {accent} line-icons: '…', …. ` |
| `chips` | 横排标签 | `{N} refined chips in a row: '…', …. ` |
| `steps`（别名 `flow`） | 横向箭头流程 | `A horizontal {n}-step flow with {accent} connectors: '…' → '…' → …. ` |
| `cards` | 细长卡片 | `{N} refined slim cards with small {accent} line-icons, each a medium card title + a small line: '标题 — 副句', …. ` |
| `list`（别名 `toc`） | 编号纵列 | `A clean vertical numbered list: '01 …', '02 …', …, each with a thin {accent} divider line. `（自动前缀 01/02） |
| `table` | 优雅表格 | `A clean elegant table: '行 — 值/值', …. ` |
| `two-col`（别名 `twocol`） | 左右分栏 | `Left keywords '{items[0]}'; right a note '{items[1]}'. `（只用前 2 项；<2 项则 `Two balanced columns: …`） |
| `quadrant` | 2×2 象限 | `A subtle 2x2 quadrant with one highlighted {accent} quadrant and muted others: '…', …. ` |
| `funnel` | 递降漏斗 | `A descending funnel: '…' / '…' / …. ` |
| `persona` | 人群卡 | `{N} refined persona cards: '人群 · 规模 · 特征', …. ` |
| `content`（兜底/未知键回退） | 通用精致排布 | `Render these as {N} refined elements with small {accent} accents: '…', …. `（无 items 则无 body） |

版式不够用时，先用最接近的 key；若确有稳定的新页型，在 `outline_to_deck.py` 的
`build_content` 增加有边界的新 key，并补测试与本表说明。不要通过手改 `deck.json` 制造旁路。

## 5. 背景场景写法（data-bg / scene_domain）

- 每页 `data-bg`（英文）原样进 `Background: {bg}.`；不填则用全局 `deck-config.style.scene_domain`（默认 `an upscale modern interior at golden hour`）。
- **只需给场景主体**：`a moody upscale modern kitchen at golden hour with premium dark appliances` 式一句。虚化/渐变已由 STYLE 全局块负责（§1），重点页可在 data-bg 里追加 `in warm bokeh` / `softly out of focus` 强化，非必须。
- **全局主场景保统一**：把可复用的一句设为 `scene_domain`，无专属意象的页一律 fallback 到它；有主题的页写专属 data-bg（数据页配货架/产品、渠道页配内容流、人群页配家庭生活流）。
- mood 服务叙事：谨慎话题 `moody/restrained`，机会话题 `bright/confident/rising light`，庆典 `festive/vibrant`。
- 场景里可自然植入产品（`premium dark steam oven … softly out of focus`）——"氛围里带货"，不是产品图。

## 6. 真人锁脸页（kol 版式）

大纲里 `data-layout="kol"` + `data-photo="assets/name.jpg"`，脚本对该页走 `/images/edits`（multipart 传照片）。字段映射：`data-bg`→动作场景、`data-kicker`→标签、`data-title`→姓名、`data-sub`→身份一句话、`data-sum` 首条(`items[0]`)→专属 slogan。脚本 `build_special` kol 分支产出（`{clean}` = dark 时 `clean and dark`、light 时 `clean and bright`）：

```
Keep the EXACT face, identity and likeness of the person in the provided photo — preserve their recognizable facial features, age and hairstyle precisely. Re-create THIS SAME PERSON in a premium cinematic 16:9 brand key-visual photograph, set in {data-bg}; soft flattering light, moody, photorealistic editorial quality. Place the person on the RIGHT half; keep the LEFT half {clean}. In that clean area render refined modern sans-serif Chinese text with STANDARD SQUARE character proportions (each character fits a 1:1 square box — natural 方块字, NOT condensed, NOT stretched, NOT italic) and a REGULAR/MEDIUM weight (NOT bold): a small letter-spaced {accent} tag '{kicker}' at top; a medium-large white title '{姓名}'; a small grey line '{身份}'; a {accent} slogan '{slogan}'. Make the type MEDIUM-LARGE and clearly prominent while keeping REGULAR/MEDIUM weight and square proportions. Render every Chinese character correctly and crisply. No watermark, no extra logos, no extra people, no caricature.
```

要点：
- **构图铁律**：人物右半、左半净区放文字（脚本已写死）。`data-bg` 要给"正在做招牌事"的动作场景（`wok-frying a glossy dish in an upscale dark kitchen at golden hour`），比站姿有内容。
- **文字三件套已内建**：方块字 1:1 + REGULAR/MEDIUM 字重 + MEDIUM-LARGE 字号，三个都在句里，别删。
- 照片预处理：脸清晰正面为佳；短边 <760px 先放大（PIL `LANCZOS` 到短边 760 + `UnsharpMask(radius=2.2, percent=120, threshold=2)`，quality 94）；原照 <300px 锁脸明显变弱，尽量换高清照。
- **没有本人照片就不画真人**：改用代表性模特，在 data-bg 或手改 prompt 里显式写 `a representative model, NOT a real celebrity, NOT any real person's face`。

## 7. 换风格改哪里（deck-config.style 槽位）

**不可变项**（烧进 `build_style`，不改脚本就动不了，也不该动）：ART-DIRECTED 声明 / cinematic 背景照 + 渐变压字区 / asymmetric + breathing room / MEDIUM-WEIGHT · NOT oversized · NOT heavy/bold · 方块字 / `Render every Chinese character…crisply` / kicker·title·body 三级字阶。

**可变槽位**（只改 `deck-config.style`，重跑 `outline_to_deck.py` 即生效）。**母版预填 dedao 风格**（`mode: dark` + `accent 朱砂红 #c0392b` + `scene_domain` 电影感实拍 + `material` 暖光纪实/film grain + `tone_words` premium, documentary-quality）；下表末列是**槽位留空时的脚本 fallback**（黑金 warm gold）：

| 槽位 | 作用 | 脚本 fallback（槽留空时） | 换风格示例 |
|---|---|---|---|
| `mode` | 整体明暗 | `dark` | `light`：BRIGHT 背景 + soft bright gradient + deep charcoal 字 |
| `accent_name` + `accent_hex` | 强调色（hairline/tag/连接线） | `warm gold` / `#c79a5b` | 母版 `vermilion red`/`#c0392b`；也可 `electric blue`/`#3b82f6`、`jade green`/`#2f7d5d`，hex 必给 |
| `scene_domain` | 全局主场景（无 data-bg 页的 fallback） | `an upscale modern interior at golden hour` | 母版 电影感实拍；科技 `sleek data center, glowing interfaces`；制造 `precision factory floor, robotic arms`；金融 `glass skyline office at dusk` |
| `tone_words` | STYLE 收尾语气词 | `expensive, magazine-quality` | 母版 `premium, documentary-quality`；`precise, engineered, architectural` |
| `material` | 材质氛围（拼进 STYLE `… for material atmosphere.`；留空则整句省略） | `brass accents, gentle bokeh` | 母版 `warm documentary light, gentle film grain`；科技 `glass and brushed metal, subtle circuit glow` |

**黑金 dark 与 dedao 朱砂红 dark 两域是实战过验的**；其它新配色/新域/light 模式都是同公式外推——样张门（先出 1–2 张给用户确认，见 pitfalls）不可跳过，light 模式样张阶段重点看文字可读性。

## 8. 文字渲染规则

- 要出现在画面里的中文/数字，只写进大纲的 `data-title` / `data-sub` / `data-sum`（按 ` / ` 分条）；脚本 `q()` 自动加英文单引号进 prompt，模型只画引号内的字。（网页版富 HTML 里的文字不进纯图版 prompt。）
- `data-sum` 每条 ≤ 12 字左右，标签式；长句拆成 `'主短语 — 副短语'` 结构（cards/table 版式尤其）。
- 数字符号照抄（`-8.5%`、`>90%`、`≈`、`CR5`）；生成后**必逐页校对**——中文渲染强但非 100%，错字页只重出该单页（`gen_deck.py --only <id> --force`）。
- kicker 中英混排（`市场洞察 · MARKET`）是风格记号，整套统一。
- 不要指望模型自由发挥文案：大纲里没写的字就不该出现，出现了多余文字算废页。
