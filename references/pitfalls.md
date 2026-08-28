# 踩坑与约束 — 规则为什么长这样

provenance：本文纪律来自一份返工三轮才过验的纯图 deck，动摇某条纪律前先看这里。

## 目录

1. 唯一权威源纪律（deck-studio 的核心设计）
2. 样张门为什么是 MUST
3. gpt-image-2 API 约束
4. codex 免费通道 vs 直连 API
5. 审图纪律
6. 装配与体积
7. 真人页红线

## 1. 唯一权威源纪律

**PPT God `project_snapshot` 是正式内容、页序、证据、生产类型和审批状态的唯一来源；HTML 只描述视觉
布局，`deck.json` 是一次性派生物。** 改字流程：

```
在 PPT God 修改页面并保存，获取同一 revision 的 project_snapshot
按需调整大纲 HTML 的视觉布局属性
python outline_to_deck.py outline.html --project-snapshot project_snapshot.json
python gen_deck.py deck.json --only S07 --force   # 只重生变动页（其余命中缓存跳过）
python inline_html.py deck.json outline.html      # 需自包含 HTML 时刷新
```

- **永远单页增量，永不整片重跑**（4K 一张 120–140s + 计费）。`--only <id> --force` 是默认姿势。
- 这取代“HTML、页面计划和脚本多处誊抄”的旧产线：内容和状态只在 PPT God 修改，HTML 不再维护
  第二份正式文案。
- 个别版式不够用时，扩展大纲 schema 或脚本中的有界版式键并补测试；不要手改派生出的
  `deck.json`，否则重派生会丢改动，也会产生第二个内容源。
- 派生后先 `gen_deck.py deck.json --dry-run` 打印每页 prompt，肉眼过一遍再进样张门。

## 2. 样张门为什么是 MUST

三轮返工烧掉数小时，固化出的教训（去客户绑定后的骨架）：

- **v2**：AI 无字背景 + 字体 HTML 文字层 + 浏览器截图 → 被否"有网页感、排版有问题"。结论：**纯图 = 模型把整页含文字直接画出来**，不走 HTML 截图路线。
- **v3**：直接生图但黑底大字粗体 → 被否"字大 ≠ 设计感、字太粗太大、页面变少"。结论：**设计感 = 氛围底图 + 渐变 + 构图分区**；字号字重取中；页数服从论证完整和节奏，不为压页数牺牲必要内容。
- **v4**：直接生图 + 艺术指导（STYLE 块）→ 过验。STYLE 块成默认基因。

根因两条：① 用户术语（"纯图/设计感/高级感"）有歧义，闷头按自己理解做整片；② 把旧结论（"AI 画不准真人脸"）当不可破约束，没花 1 次调用验证——实际 `/images/edits` 锁脸完全可行。
**所以：先出 1–2 张样张给用户确认再批量（`gen_deck.py --only <id1>,<id2>`），"AI 做不到 X" 要先验证再当约束。** `outline_to_deck.py` 结尾也提示 never batch before the gate。

## 3. gpt-image-2 API 约束

- `POST {base}/images/generations`，body `{"model":"gpt-image-2","prompt":…,"size":…,"quality":"high","n":1}`；返回 `data[0].b64_json`（偶尔给 `url`，两种都处理——`gen_deck.py` 已内建）。
- **尺寸两条规则**：① 宽高各须被 16 整除（`1920x1080` 会被拒）；② 总像素有最低预算——`1024x576` 返回 400 "below the minimum pixel budget"。4K 用 `3840x2160`，草稿用 `2048x1152`（过验最小档）。`load_config` 会拦不合规尺寸。
- 锁脸走 `POST /images/edits`（multipart，`image=` 本人照片 + 同参数）；`keep the EXACT face…re-create THIS SAME PERSON` 实测保得住本人。photo 存在的 slide 自动走 edits，不存在走 generations。
- **中文渲染强但非 100%**：短语/数字基本一字不差，仍偶发错字 → **逐页校对是流程必选项，不是可选项**。
- 节奏：4K 单张通常耗时较长。稳定默认是一张一张生成；只有代表页通过、额度与服务承载已确认时
  才提高并发，脚本上限 4。429/5xx 最多做两次有界尝试，失败后明确返回非零。
- 凭据只读环境变量 `OPENAI_API_KEY`；`OPENAI_BASE_URL` 可选，缺省使用官方地址。代理交给
  `HTTP_PROXY` / `HTTPS_PROXY` 等标准环境变量；不得扫描其他产品配置或内置本机代理地址。
- 依赖安装（本机 Python 被 uv 托管，PEP 668）：
  ```
  uv venv .venv && VIRTUAL_ENV=.venv uv pip install requests pillow python-pptx beautifulsoup4
  ```
  （`beautifulsoup4` 是 `outline_to_deck.py` 解析大纲用的，比只出图多一个。）
- **venv/工作目录别放 Temp 或 session scratchpad**：Windows 会清 Temp，venv 的 `.py` 源码被清后只剩 `__pycache__` 骨架——`import PIL` 仍成功（namespace 包假阳性），`from PIL import Image` 才报 `unknown location`。验证依赖要用 `from PIL import Image; from pptx import Presentation; import bs4`，别只 `import PIL`。

## 4. codex 免费通道 vs 直连 API

同引擎两条路，按预算/时限选：

| | codex-image skill（订阅额度） | 直连 API（本 skill 脚本） |
|---|---|---|
| 费用 | 免费 | 计费 |
| 并发 | 只能串行——起第二个 worker 会 hang、留孤儿 Codex.exe | 5–6 路稳 |
| 尺寸 | 提示性，实际只出 ~1672px 宽 | 真 4K 3840×2160 |
| 速度 | ~130s/张 | 明显更快（多路并发） |

终稿 4K/赶时间 → API；不赶时间的低成本草稿 → codex-image。codex 孤儿进程清理：`taskkill //F //IM Codex.exe`。

## 5. 审图纪律

- **4K 原图别 Read 进上下文**（单张 8–11MB，Request too large）；全片 QC 读 `contact_sheet.py` 生成的 contact sheet；单页细看先降采样到 ~1280–1500px JPG，一轮最多读 1 张大图。
- 审查机制挡图时（LIVE_MODE 下厨房场景/真人脸常被挡）：自己看不了就**把文件路径给用户打开，判断权交给用户**，别闷头卡住。
- 逐页校对五项：字正确 / 数字正确 / 版式符合 plan / 风格统一 / 字号不过大。
- 数据页（`stats`/`table`）的数字是硬伤高发区，重点核。

## 6. 装配与体积

- `assemble_pptx.py` 只用于旧图片流水线的草稿：`slide_width=12192000, slide_height=6858000`（EMU，16:9），
  blank layout，`add_picture` 全幅。它在写文件前检查全部 PNG，缺页/过小页直接失败，绝不补空白页；
  `hybrid`、`native_editable` 和正式导出统一交给 PPT God Workflow Core。
- 体积预期：4K PNG ~7MB/页。客户嫌大再瘦身：`inline_html.py` 装配时 PNG→JPEG（默认 width 1600 / quality 85），体积约 1/6、观感几乎无损——自包含 HTML 走这条。PPTX 想瘦身同理先转一页给用户比对。
- 交付到云盘/挂载盘时留意大文件复制时间。

## 7. 真人页红线

- 没本人照片不画真人；无照时用代表性模特并显式写 `NOT a real celebrity, NOT any real person's face`。
- 低清原照（<300px）锁脸效果明显弱，先要高清照，实在没有就预处理放大（prompt-cookbook §6）。
- 名人肖像/授权合规是用户与客户的责任，交付前提醒一句即可。
