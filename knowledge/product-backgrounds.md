# 产品/AI 背景生成规则

## 核心原则

**AI 生成高清底图，真实产品图承担品牌真实性。** 不要把用户给的低清截图拉满全屏当背景；这会产生模糊、补丁感和廉价感。

## 什么时候用

- 封面、章节页、封底需要和产品/品牌更匹配
- 用户给了产品图，但分辨率不足以做全屏背景
- 原 PPT 背景太空、太黑、太模板化
- 需要从产品色系生成统一视觉系统

## 什么时候不用

- 用户明确要求保留原图原样，不要重构背景
- 产品图本身是高质量摄影且可直接裁切
- 页面是密集信息页，背景应退到浅色/无干扰

## 三层结构

```
[0] 高清无字氛围底图：AI 生成，16:9，无文字/无 logo/无产品标签
[1] 真实产品主体：用户给的产品图或官方图，等比缩放，不拉伸
[2] PPT 可编辑文字/logo：标题、口号、页码、品牌 logo
```

文字和 logo 不要烘焙进 AI 图里，避免错字、伪标和不可编辑。

## Prompt 模板

### 封面/章节页

```text
Use case: ads-marketing / product-mockup background
Asset type: 16:9 PowerPoint cover background
Primary request: Create a premium high-resolution abstract product-themed background inspired by the reference product's amber yellow, warm orange, and subtle medicine/healthcare packaging feeling.
Scene/backdrop: clean studio-like gradient, warm amber-gold light, soft tabletop plane, subtle depth, elegant commercial presentation style.
Composition: right side has open space for product placement, left side has clean readable title area, no heavy texture.
Absolute constraints: no text, no letters, no numbers, no logo, no watermark, no fake product packaging, no bottle labels, no people.
Output: sharp, clean, 16:9, suitable as a PPT background.
```

### 封底/感谢页

```text
Create a premium 16:9 closing slide background with warm amber-gold gradient, soft radial glow, clean tabletop plane, refined business proposal mood.
Leave a centered safe area for a text card and a lower safe area for logo.
No text, no letters, no numbers, no logos, no watermarks, no product labels.
```

## 产品图叠加规则

- 先记录原始像素尺寸和宽高比：`ratio = w / h`
- 只用 contain/cover 中的一种明确策略，不能任意拉伸
- 产品主体不要压住标题安全区
- 如果产品图低清：
  - 只放在中等尺寸作为主体
  - 或只作为 AI 生成参考
  - 不全屏放大
- 产品包装上的真实文字可以保留，但不要让它和 PPT 标题抢视觉

## 标题卡规则

- 半透明卡片上文字必须深色，优先 `#3A2412` / `#2B1A0D`
- 不要用白字叠在浅黄/浅米卡片上
- 卡片透明度不要过高，保证文字背景稳定
- 标题卡与产品主体至少留出 24px 视觉间隔

## 失败信号

- 背景中出现 AI 乱造的中文/英文/数字
- 产品包装文字变形、错字或像糊在背景里
- 产品主体被拉宽/拉高
- 封面像把截图加了遮罩和色块“补出来”
- PowerPoint 打开后标题发白、logo 红叉

出现上述情况，废弃该底图路线，重新生成无字背景或改用抽象底图。

## 验证

交付前至少验证：

1. 最终 PPTX 渲染的封面和封底截图
2. 产品主体宽高比与原图接近
3. 背景图中没有伪文字/伪 logo
4. 标题和副标题在 PowerPoint 实际打开中可读
5. logo 资源不是易失效的 SVG/bin
