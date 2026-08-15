# 小插图资产生成规则

## 核心原则

**小插图是可移动图层，不是整页背景。** 插图只承担视觉锚点和概念辅助，不承载正文、logo、产品包装文字或关键事实。

## 什么时候用

- 页面稀疏，只有标题和少量说明，缺少第一视觉
- 章节页、概念页、方法论页需要轻量视觉锚点
- 原页面没有真实素材，且插图不会改变事实含义
- 用户明确要求增加插图或视觉符号

## 什么时候不用

- 页面已经密集，新增元素会降低可读性
- 页面有产品图、客户截图、现场照片等真实证明物
- 插图可能被误解为真实产品、真实场景或真实数据
- 用户要求只保留原图原文，不新增视觉素材

## 生成路线

```
[0] GPT Image 2 生成白底/纯色底小插图：无文字、无 logo、无水印
[1] templates/illustration_cutout.py 本地抠图：只删除边缘连通背景
[2] 透明 PNG 插入 PPT：作为独立图片图层，等比缩放
```

GPT Image 2 不支持透明底。不要请求透明背景；默认生成白底或极浅灰底。若主体本身有大量白色，改用与主体反差明显的纯色底。

## Prompt 约束

```text
Create a small clean editorial illustration asset on a plain white background.
Subject: [one concrete object or concept].
Style: modern business presentation, simple shapes, crisp edges, no shadows crossing the full canvas.
Composition: centered subject with clear margin around it.
Absolute constraints: no text, no letters, no numbers, no logo, no watermark, no UI screenshots, no product labels.
Background: pure white or one flat solid color only.
```

## 抠图命令

```bash
python3 templates/illustration_cutout.py input.png \
  --output output_cutout.png \
  --mode auto \
  --fallback-card output_card.png
```

`illustration_cutout.py` 只删除和画面边缘连通的背景区域。插图内部的白色区域如果被主体轮廓包围，应保留为不透明，避免误删高光、纸张、屏幕等白色细节。

## 插入规则

- 插图放在内容图层，不放在文字层上方
- 与标题、正文、logo 至少保留 0.15 英寸间距
- 等比缩放，最长边通常不超过页面短边的 35%
- 需要压低存在感时调透明度或缩小，不把插图做成整页底图
- 页面已有真实图片时，插图只可做小型辅助符号，不抢主体

## 失败信号

- 生成图里出现任何文字、数字、logo、水印
- 抠图后主体边缘明显破碎或白色主体被误删
- 插图看起来像真实产品或真实客户案例
- 插图压住标题、正文、页码或 logo
- 页面从信息页变成海报页，主信息反而不清楚

出现失败信号时，优先弃用插图；必要时使用白底/浅色底 fallback card，不强行透明化。
