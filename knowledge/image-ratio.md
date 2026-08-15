# 图片比例保护

## 核心原则

**图片缩放必须保比例**。只改 width 或只改 height = 图片变形，这是 PPT 常见硬伤。

## 比例计算公式

```python
ratio = orig_w / orig_h  # 原始宽高比

# 已知目标高度，求宽度
new_w = ratio * target_h

# 已知目标宽度，求高度
new_h = target_w / ratio
```

## 关键场景

### 场景 1：固定高度，调宽度
```python
# 把图片高度统一为 4.0"
target_h = 4.0
new_w = (orig_w / orig_h) * target_h
```

### 场景 2：固定宽度，调高度
```python
# 把图片宽度统一为 2.5"
target_w = 2.5
new_h = target_w / (orig_w / orig_h)
```

### 场景 3：限制最大边界（contain 模式）
```python
# 在 max_w x max_h 的框内最大化
def fit_contain(orig_w, orig_h, max_w, max_h):
    ratio = orig_w / orig_h
    if max_w / max_h > ratio:
        # 框更宽 → 高度受限
        new_h = max_h
        new_w = ratio * new_h
    else:
        # 框更高 → 宽度受限
        new_w = max_w
        new_h = new_w / ratio
    return new_w, new_h
```

## 批量处理多图同高

如果 4 张图需要统一高度（如 PPT 同列展示），用 `templates/preserve_ratio.py`：

```python
from templates.preserve_ratio import unify_height

target_h = 4.5
for pic in slide.shapes:
    if pic.shape_type == 13:  # PICTURE
        new_w, new_h = unify_height(pic.image.size, target_h)
        pic.width = Emu(new_w * 914400)
        pic.height = Emu(new_h * 914400)
```

## 比例不变形但位置错怎么办

**问题**：图按比例缩了，但和文字对不齐。
**原因**：只缩了图，没动文字位置。
**解法**：同步调整文字 y 坐标 / 字号。

**新规则**：调整一组元素（图片 + 文字）时，先算整体的"中心点"或"基线"，再定位。

## 反面示例（禁止）

- ❌ 只设 width 让 height 自动（PPT 不会自动，高度会变 0 或默认）
- ❌ 用 `pic.width = pic.width * 0.8` 缩放（不精确，累积误差）
- ❌ 缩放后不验证（变形问题在 16:9 看不出来，在 4:3 才暴露）
