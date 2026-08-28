# PPTX / PowerPoint 兼容性

## 核心原则

**最终验的是用户打开的 PPTX，不是脚本中间预览。** 不同渲染器对字体、SVG、透明度、主题色、图片格式的处理可能不同。

## 常见问题

### 1. 预览文字是深色，PowerPoint 打开发白

**根因**：
- 样式只改了渲染层，没写进最终 `ppt/slides/slideN.xml`
- 文本 run 仍保留旧的 `a:srgbClr`
- theme color 覆盖了显式设置

**修法**：
- 检查最终 PPTX XML 中目标文本附近的 `a:rPr` / `a:defRPr`
- 指定 shape id 做窄范围颜色/字号修正
- 修完重新渲染最终 PPTX

### 2. logo 在 PowerPoint 里变红叉

**根因**：
- SVG 被打包成 `.bin`
- content-type 与实际资源不匹配
- PowerPoint/Mac 对该 SVG 兼容性差

**修法**：
- 从原 logo 生成透明 PNG
- 替换掉 SVG/bin 图片资源
- 不要用截图里的红叉占位继续交付

### 3. 半透明背景在不同软件里变脏

**根因**：
- 透明 PNG 下面露出旧黑底/灰底
- shape fill alpha 被不同渲染器解释不同

**修法**：
- 生成不透明 RGB 背景图
- 或把底层全页矩形设成同色暖底
- 不依赖“透明叠透明”的多层效果

### 4. 字体替换导致换行变化

**根因**：
- Mac/Windows 字体不同
- 中文字体回退后字宽变化
- 文本框高度太紧

**修法**：
- 中文正文优先 `微软雅黑` / `思源黑体`
- 重要标题给 10%-15% 宽度余量
- 不要让文本框高度刚好等于估算行高

### 5. 生成接口的字体属性没有写入 PPTX

**症状**：
- 代码里“设置了字体”，最终页仍回退为衬线字体或系统默认字体
- 整册主要字体统计正确，但个别新增页字体异常

**根因**：
- 生成接口使用了错误或过期的样式属性名
- 只设置了 Latin 字体，没有写入 East Asian 字体
- 验证只看整册占比，没有限定到本轮新增页

**修法**：
- 先做一个最小文本框探针并检查最终 PPTX XML，确认接口真正写入目标字体
- 给新增可编辑 run 显式写入 Latin / East Asian / Complex Script 字体
- 对本轮新增或重做页单独运行：

```bash
python3 templates/typography_audit.py output.pptx \
  --include-slides "2,6,10-11,19,22,26,35" \
  --allowed-fonts "微软雅黑" \
  --fail-on-inherited
```

不要用“整册大部分文字是目标字体”替代新增页硬检查。

### 6. 局部换图后，嵌入视频悄悄消失

**症状**：
- 页面外观正常，视频封面仍在，但点击后无法播放
- 修改前有嵌入视频，修改后的 `ppt/media/` 或页面媒体关系已经减少

**根因**：
- 编辑库重新序列化整页时没有保留 PowerPoint 的 `video` / `media` 双关系
- 用截图或封面图替换了视频形状，却没有保留原始媒体包
- 只检查页面渲染结果，没有核对 PPTX 包内媒体关系与文件字节

**修法**：
- 对含视频页面优先做包级、窄范围替换，保留未触及的媒体文件和关系
- 若本轮没有授权修改音视频，交付前运行：

```bash
python3 templates/verify_pptx.py source.pptx output.pptx \
  --require-media-preserved
```

- 该检查按页去重 PowerPoint 指向同一文件的 `video` / `media` 关系，并比较嵌入文件指纹；任何减少、
  替换或静默丢失都直接报错

## 最小兜底流程

1. 记录问题页、shape id、目标文本。
2. 解包 PPTX 到 scratch 目录。
3. 只修改对应 `ppt/slides/slideN.xml` 中目标 shape。
4. 重新压包。
5. `unzip -t` 检查完整性。
6. 重新渲染最终 PPTX。
7. 跑 `templates/verify_pptx.py`。

不要做全局主题替换，不要批量改所有 `a:srgbClr`。

## XML 快速定位

```bash
python3 - <<'PY'
from zipfile import ZipFile
from pathlib import Path

ppt = Path("output.pptx")
with ZipFile(ppt) as z:
    xml = z.read("ppt/slides/slide1.xml").decode("utf-8")
target = "标题文字"
i = xml.find(target)
print(xml[max(0, i-800):i+400])
PY
```

## 交付前硬检查

- `unzip -t output.pptx`
- 最终 PPTX 渲染截图，不是中间 PNG
- 关键文字颜色在 XML 中真实存在
- 没有高风险 SVG/bin logo
- 用户截图中出现过的问题页必须单独复看
