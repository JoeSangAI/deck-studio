# Z-order 层级规则

## 核心原则

**Z-order = 视觉层级，错一层全乱**。背景被文字挡住 / 装饰线压在图片上 / Logo 被遮住，都是 z-order 错误。

## 标准层级（从下到上）

```
[0] 背景图（最大层、铺满整个 slide）
[1] 背景色块 / 大面积装饰
[2] 装饰线 / 小色块 / 几何图形
[3] 内容图片 / 图表
[4] 内容文字 / 标签
[5] Logo / 角标 / 页码
```

## 常见 z-order 错误

### 错误 1：装饰线压在图片上
- **症状**：P5-P8 底部装饰线穿过图片底部
- **根因**：装饰线后于图片添加到 spTree
- **修法**：**删除装饰线**（不是"挪位置"）

### 错误 2：背景图压住文字
- **症状**：封面文字看不清
- **根因**：背景图作为 `grpSp` 整体放在最上层
- **修法**：把 `grpSp` 移到 spTree 最前（最底层）

```python
for i, child in enumerate(spTree):
    if child.tag.split('}')[-1] == 'grpSp':
        spTree.remove(child)
        spTree.append(child)  # 移到最后（在 XML 中是最上层，但视觉最底）
```

### 错误 3：Logo 被装饰线遮住
- **症状**：右下角 Logo 模糊
- **根因**：装饰线 z-order 高于 Logo
- **修法**：把装饰线移到 Logo 之前

## 调试方法

### 方法 1：看 XML 顺序
打开 `slide1.xml`，`<p:spTree>` 下的子元素顺序就是 z-order（**后添加 = 在更上层**）。

### 方法 2：临时染色
把所有元素临时染成不同颜色，肉眼判断谁在上谁在下。

### 方法 3：删元素
怀疑哪个元素有问题 → 删掉它 → 看其他元素是否变正常。
- 如果是 → 确认是该元素的 z-order 错了
- 如果不是 → 该元素无关，找下一个

## Z-order 调整代码

```python
from lxml import etree

def move_to_top(slide, element_name):
    """把指定名字的元素移到 spTree 最上层"""
    spTree = slide.shapes._spTree
    target = None
    for child in spTree:
        if element_name in child.xml:
            target = child
            break
    if target is not None:
        spTree.remove(target)
        spTree.append(target)


def move_to_bottom(slide, element_name):
    """把指定名字的元素移到 spTree 最下层（视觉最底）"""
    spTree = slide.shapes._spTree
    target = None
    for child in spTree:
        if element_name in child.xml:
            target = child
            break
    if target is not None:
        spTree.remove(target)
        spTree.insert(0, target)  # 插到第一个位置
```

## 反面示例（禁止）

- ❌ 用"挪位置"代替"改 z-order"（位置对但被遮，问题没解决）
- ❌ 加更多元素去"挡"错位元素（堆叠污染）
- ❌ 不看 XML 就猜 z-order（"我觉得它在上面"）
