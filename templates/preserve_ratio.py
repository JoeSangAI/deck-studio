"""
图片比例保护工具
- 已知目标高度 → 求宽度
- 已知目标宽度 → 求高度
- contain 模式：在 max_w x max_h 框内最大化
"""
from pptx.util import Emu


def unify_height(orig_size, target_h_inch):
    """
    按目标高度统一图片尺寸，保持原始比例
    orig_size: (orig_w_px, orig_h_px)
    target_h_inch: 目标高度（英寸）
    return: (new_w_inch, new_h_inch)
    """
    orig_w, orig_h = orig_size
    ratio = orig_w / orig_h
    new_h = target_h_inch
    new_w = ratio * new_h
    return new_w, new_h


def unify_width(orig_size, target_w_inch):
    """
    按目标宽度统一图片尺寸，保持原始比例
    return: (new_w_inch, new_h_inch)
    """
    orig_w, orig_h = orig_size
    ratio = orig_w / orig_h
    new_w = target_w_inch
    new_h = new_w / ratio
    return new_w, new_h


def fit_contain(orig_size, max_w_inch, max_h_inch):
    """
    contain 模式：在 max_w x max_h 的框内最大化
    """
    orig_w, orig_h = orig_size
    ratio = orig_w / orig_h
    box_ratio = max_w_inch / max_h_inch

    if box_ratio > ratio:
        # 框更宽 → 高度受限
        new_h = max_h_inch
        new_w = ratio * new_h
    else:
        # 框更高 → 宽度受限
        new_w = max_w_inch
        new_h = new_w / ratio
    return new_w, new_h


def emu(inches):
    """英寸 → EMU"""
    return Emu(int(inches * 914400))


def apply_to_pic(pic, new_w_inch, new_h_inch):
    """
    把尺寸应用到 python-pptx 的 picture 对象
    """
    pic.width = emu(new_w_inch)
    pic.height = emu(new_h_inch)


if __name__ == "__main__":
    # 示例
    orig = (1920, 1080)
    print("原图 1920x1080，目标高度 4.0 英寸:")
    w, h = unify_height(orig, 4.0)
    print(f"  → {w:.2f} x {h:.2f} 英寸")

    print("\n原图 1920x1080，contain 模式 2.5x4.0 英寸:")
    w, h = fit_contain(orig, 2.5, 4.0)
    print(f"  → {w:.2f} x {h:.2f} 英寸")
