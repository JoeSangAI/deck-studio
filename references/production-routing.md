# PPT 生产路由与混合装配

## 目录

1. 先看最终使用方式
2. 四种路线
3. 页面级路由
4. 混合装配不变量
5. 并行生产契约
6. 验收

## 1. 先看最终使用方式

不要从“哪个工具方便”开始。先判断：

- 听众是现场听讲还是会后自行阅读？
- 后续是否需要频繁改字、换数据、换案例或换品牌？
- 是否包含视频、音频、图表、表格、二维码或可点击入口？
- 内容的事实准确性和可追溯性有多高？
- 视觉冲击和编辑自由哪个更重要？

页数不是独立目标。以论证完整、现场节奏和阅读负担共同决定；密集页应拆开，但不要为了“控制在
几页”删除必要证据。

## 2. 四种路线

| 路线 | 优先场景 | 主要风险 | 必守动作 |
|---|---|---|---|
| 可编辑 | 客户方案、数据报告、案例库、多媒体、反复修改 | 程序感、版式平 | 先建立 KV 派生的视觉系统，再用原生对象实现 |
| 纯图 | 演讲、发布、课程大场、视觉气氛优先 | 错字、不可编辑、事实难修 | 文字冻结、样张门、逐页校对 |
| 混合 | 既要视觉冲击又要可修改的提案 | 合并时风格割裂或全稿栅格化 | 页面级标注路线、统一母版、验证可编辑性 |
| 精修 | 已有内容成立但观感、结构或兼容性差 | 内容误改、补丁式美化 | 先审计和保真，再修根因 |

### 现场讲述型分享

当听众主要通过讲述者理解内容，页面负责制造节奏、记忆点和视觉证据时，默认从纯图路线开始判断。
截图、视频、真实照片、数据、原始证据和需要精确编辑的页面转入可编辑路线。这个默认值不规定图片页
比例；每一张可编辑页都应有来自内容或播放要求的明确理由，不能只因为代码生成更方便。

## 3. 页面级路由

通常适合纯图：

- 封面、封底；
- 章节页、转场页、金句页；
- 单一主张或情绪性强、文字很少的关键页；
- 已冻结且不承载精确数据的品牌氛围页。

通常必须可编辑：

- 数据图表、表格、时间轴和报价；
- 客户案例、研究证据、复杂文字和频繁更新内容；
- 视频、音频、二维码、链接和交互入口；
- Logo、产品 UI、截图、法务文案和事实敏感页面；
- 需要客户自行修改或复用的正文页。

页面路由由两层组成。`mode` 决定 PPT 中的对象形态，`production_route` 决定基底怎样产生：

| `production_route` | 适用情况 | 必经证据 |
|---|---|---|
| `source-preserve` | 复杂原页、案例、证据页、已批准页面 | `source_lock` 绑定唯一母稿绝对路径、checksum、类型和页码 |
| `native-editable` | 数据、事实、持续修改与多媒体页面 | `mode: editable` 和原生对象验收 |
| `ppt-god-full-image` | 无精确硬件资产的完整视觉页 | `mode: image`、冻结文案、整页校对 |
| `reference-fusion` | 含真实媒体、产品、人物或批准页面的完整视觉页 | 非空 `reference_assets`，每项含 ID、绝对路径、checksum 和角色 |

`overlay_policy` 独立取值：

- `none`：无后贴层；
- `logo-only`：只允许一张已确认真实 Logo，并写 `allow_logo_overlay: true`；
- `precision-assets`：只允许 Logo、二维码、法务标识或截图，逐项写入 `overlay_assets`；
- `local-patch`：只用于 `source-preserve` 的局部修补，必须带 `edit_mask` 并验证蒙版外不变。

Overlay 是 PPT 页面装配概念，不负责制作媒体图。屏幕或海报创意先进入标准带框图；媒体进入环境时
使用专业参考融合。页面中的人物主体和主构图同样不能靠 Overlay 拼成。

当前 PPT God CLI 的稳定 Agent 路径提供全页生成和 `import-slide-image`，未提供上传本地参考资产并
绑定指定页面的命令。因此默认分工是：`ppt-god-full-image` 直接交给 PPT God；`reference-fusion`
由专业图片能力完成并验收，再原样导入 PPT God。专业成品不再交给通用模型二次重画。若未来 CLI
正式支持参考资产上传，只有在回读确认页面
绑定的 reference ID 非空且与 `reference_assets` 一致后，才可把融合环节迁入 PPT God。

### 专业媒体扩展

当页面涉及分众知识、历史原页或分众媒体硬件时，完整读取
[focusmedia-integration.md](focusmedia-integration.md)。该引用统一拥有专业 Skill 分工、知识与原件
路由、标准带框图、环境参考融合、页面资产契约和验收规则；本文件只保留通用页面路由。

## 4. 混合装配不变量

每页只做三项正交决策：

- `mode: editable | image`：PPT 内如何实现；
- `knowledge_route`：事实、方法或原页从哪里取得；
- `specialist_route`：专业媒体视觉由哪个 Skill 生产。

后一项不能替代前两项。同一页可以同时使用知识来源、专业媒体视觉和明确的 PPT 实现路线。

路线清单使用：

```json
{
  "slides": [
    {
      "slide": 1,
      "mode": "image",
      "production_route": "ppt-god-full-image",
      "overlay_policy": "logo-only",
      "allow_logo_overlay": true,
      "overlay_assets": [{
        "id": "brand-logo",
        "path": "/absolute/path/brand-logo.png",
        "sha256": "<64位文件checksum>",
        "role": "logo"
      }]
    },
    {"slide": 2, "mode": "editable", "production_route": "native-editable", "overlay_policy": "none", "requires": ["text"]},
    {"slide": 8, "mode": "editable", "production_route": "native-editable", "overlay_policy": "none", "requires": ["chart"]},
    {"slide": 12, "mode": "editable", "production_route": "native-editable", "overlay_policy": "none", "requires": ["media"]}
  ]
}
```

- `editable` 页必须保留原生文本、形状、图表、表格和媒体关系。
- `image` 页才允许整页铺图；页面文字默认由图片模型在同一次整页生成中完成，逐页校对后只重出
  错页，不默认再叠加第二套文字层。
- Logo 不得由模型仿造；整页图需要真实 Logo 时，使用已确认的独立图层后贴。二维码、法务标识和
  其他必须精确的品牌资产同理。屏幕创意在专业带框阶段完成，不进入这里的 Overlay 清单。
- 图片页默认没有后贴层；`logo-only` 只允许一张已确认 Logo，`precision-assets` 的实际图片数量必须
  与清单一致。不得把整台设备、人物或多张构图贴片伪装成纯图页。
- 不得把可编辑稿导出成图片后再合并，哪怕这样更方便统一风格。
- 所有路线共用同一尺寸、品牌色、字体层级、Logo 位置、安全区和页码逻辑。
- 合并后重新验证页序、章节转场、视频点击、外链、字体替换和 PowerPoint 实际打开效果。
- 合并后运行 `templates/verify_route_integrity.py final.pptx route_manifest.json`。可编辑页被整页图片化、
  缺少声明的文字/图表/媒体，图片页不是唯一整页图（真实 Logo 小图层除外），或存在未分类页面时
  都不能交付。专业媒体页面再叠加对应集成引用的资产一致性门槛。

## 5. 客户提案的逐页叙事门

客户提案、汇报和其他叙事责任较高的任务，在批量生产前维护 `page_plan.json`：

```json
{
  "status": "approved",
  "approved_by": "Joe",
  "content_version": "v1",
  "approval_scope": "全册逐页叙事与路由",
  "slides": [
    {
      "slide": 1,
      "public": {
        "title": "三个问题共同指向一个增长机会",
        "claim": "核心场景触达能够同时推动品牌认知与消费行动"
      },
      "notes": {
        "audience_question": "这次方案解决什么增长问题？",
        "purpose": "让客户知道这次沟通要解决什么",
        "claim_key": "growth-opportunity",
        "evidence_source": "客户 Brief 第 2 页",
        "speaker_line": "先看三个问题背后的共同结构。",
        "transition": "下一页解释共同结构",
        "excludes": "不在本页展开媒体执行细节"
      },
      "mode": "image",
      "production_route": "ppt-god-full-image",
      "overlay_policy": "none"
    }
  ]
}
```

- 每页只有一个主结论；`public` 是所有客户可见文案的唯一来源。
- `notes.evidence_source` 必须可追溯，不能写成空泛的“综合判断”；`notes.speaker_line` 是这一页现场
  真正要说的一句话，`notes.transition` 说明为什么下一页自然出现。
- 封面、目录和章节页也必须说明它们在叙事中的作用；不适用的证据来源写明 `not_applicable`，不得留空。
- 运行 `templates/verify_page_plan.py page_plan.json`。若同时已有路线清单，再传
  `--route-manifest route_manifest.json`；页数、页序、`mode`、`production_route`、
  `overlay_policy`、`knowledge_route` 和 `specialist_route` 必须一致。
- `status` 不是 `approved`、确认人为空或校验失败时，只允许继续讨论结构和制作代表页样张，不得批量生产整册。

### 分众知识与媒体

页面涉及分众知识、原件或媒体时，完整读取
[focusmedia-integration.md](focusmedia-integration.md)，按其中的桥接命令、页面契约、两段式媒体资产链
和 Output Check 执行。普通客户提案不加载该引用。

## 6. 并行生产契约

只有方向、页序、视觉系统、素材归属和交付格式已经锁定时，才适合并行制作。

- 主 Agent 保持与用户的讨论连续性，负责发现隐性标准和修改总规划。
- 生产 Agent 领取清楚的页段和素材，不另起一套叙事或视觉体系。
- 数据、案例核查等独立工作可以提前并行；整册方向未锁定时不批量生产页面。
- 总控 Agent 对合册结果负责：统一标题层级、去重、补转场、修交互、做整册 QA。

## 7. 验收

除常规视觉检查外，混合稿必须额外确认：

1. 预定可编辑页是否仍可单独修改文字、图表和媒体；
2. 纯图页是否仅限已选页型；
3. 视频是否可直接点击或播放，而不是只有截图；
4. 多来源页面是否形成一套叙事，而不是“完整案例”“此前案例”等拼接痕迹；
5. 整册是否使用同一品牌系统，例外品牌色只出现在合理的案例语境。
