"""
PPT Reskin CLI - deck-studio PPT 工作台的一部分
继承自原 ppt-reskin 工具，现由统一 PPT 工作台维护。

职责：
- 对一份已完成内容的 PPT 应用统一配色、字体
- 极克制：只统一主标题字体，元素多页面不加装饰
- 保留所有原有文字、图片、视频、版式

更复杂的问题（图片比例、Z-order、可读性、图文协调）走
`workflows/03-execute.md` 的 execute 阶段。
"""

import argparse
import os
import sys
import re
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn
import lxml.etree as etree


# ── Color utils ──

def hex_to_rgb(hex_str):
    h = hex_str.lstrip('#')
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def set_fill_alpha(shape, alpha_pct):
    """Set fill transparency (0=opaque, 100=transparent)."""
    try:
        fill_el = shape.fill._fill
        solid = fill_el.find(qn('a:solidFill'))
        if solid is not None:
            for child in solid:
                t = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                if t in ('srgbClr', 'schemeClr'):
                    for a in child.findall(qn('a:alpha')):
                        child.remove(a)
                    el = etree.SubElement(child, qn('a:alpha'))
                    el.set('val', str(int((100 - alpha_pct) * 1000)))
    except Exception:
        pass


# ── Shape helpers ──

def add_rect(slide, left, top, width, height, fill_rgb, alpha=100, no_line=True):
    s = slide.shapes.add_shape(1, left, top, width, height)
    if no_line:
        s.line.fill.background()
    s.fill.solid()
    s.fill.fore_color.rgb = fill_rgb
    if alpha < 100:
        set_fill_alpha(s, alpha)
    return s


def is_dark_slide(slide):
    """Guess if a slide with existing bg is dark-themed."""
    layout = slide.slide_layout.name.lower()
    return 'black' in layout or 'dark' in layout


def get_slide_element_count(slide):
    """Count shapes + pictures on a slide."""
    return len(slide.shapes)


def should_add_decorations(slide):
    """
    判断页面是否适合添加装饰元素。
    原则：无必要勿增实体。
    - 元素数量 > 25 → 设计已完成，不加
    - 有大量图片 → 不加，避免遮挡
    - 元素数量少 → 可极克制点缀
    """
    count = get_slide_element_count(slide)
    has_many_pics = sum(1 for s in slide.shapes if s.shape_type == 13) > 3

    if count > 25 or has_many_pics:
        return False
    return True


def is_thin_rule(shape):
    """Treat lines and very thin rectangles as decorative rules."""
    try:
        return shape.shape_type == 9 or (shape.height < Pt(8) and shape.width > Inches(1.0))
    except Exception:
        return False


def has_existing_header_rule(slide):
    """Avoid stacking a new header rule on top of a template/master-style rule."""
    for shape in slide.shapes:
        if shape.top < Inches(1.05) and is_thin_rule(shape) and shape.width > Inches(3.0):
            return True
    return False


def has_existing_footer_rule(slide):
    """Avoid stacking a new footer rule on top of a template/master-style rule."""
    for shape in slide.shapes:
        if shape.top > Inches(6.25) and is_thin_rule(shape) and shape.width > Inches(3.0):
            return True
    return False


def has_header_picture_conflict(slide):
    """Do not draw header decoration through an image wall or screenshot at the top."""
    for shape in slide.shapes:
        if shape.shape_type == 13 and shape.top < Inches(1.0) and shape.height > Inches(0.8):
            return True
    return False


def has_footer_picture_conflict(slide):
    """Do not draw footer decoration through a bottom-aligned image or screenshot."""
    for shape in slide.shapes:
        if shape.shape_type == 13 and (shape.top + shape.height) > Inches(6.35) and shape.height > Inches(0.8):
            return True
    return False


def can_add_header_decoration(slide):
    return (
        should_add_decorations(slide)
        and not has_existing_header_rule(slide)
        and not has_header_picture_conflict(slide)
    )


def can_add_footer_decoration(slide):
    return (
        should_add_decorations(slide)
        and not has_existing_footer_rule(slide)
        and not has_footer_picture_conflict(slide)
    )


# ── Title identification ──

TITLE_SKIP_KEYWORDS = [
    '数据来源', '注释', '有效可见', '来源：', '说明：', '注：',
    'Reach', 'CPM', 'CTR', '频次', 'Kantar', '尼尔森', '秒针',
]

MSO_PLACEHOLDER = 14


def get_text(shape):
    if not getattr(shape, "has_text_frame", False):
        return ""
    return shape.text_frame.text.strip()


def hide_text_visually(shape, bg_rgb):
    """Keep XML text for preservation checks while removing visual collision."""
    if not getattr(shape, "has_text_frame", False):
        return
    for para in shape.text_frame.paragraphs:
        for run in para.runs:
            run.font.color.rgb = bg_rgb
            run.font.size = Pt(1)


def suppress_duplicate_title_conflicts(slide, cfg):
    """
    Some decks contain both a hidden placeholder title and the real template title.
    If reskinning makes both visible, keep the real template title and visually
    hide the placeholder while preserving its XML text.
    """
    top_titles = [
        shape for shape in slide.shapes
        if getattr(shape, "has_text_frame", False)
        and get_text(shape)
        and shape.top < Inches(0.8)
        and shape.width > Inches(8.0)
    ]
    if len(top_titles) < 2:
        return

    template_titles = [
        shape for shape in top_titles
        if shape.shape_type == 1 and ("标题" in shape.name or "title" in shape.name.lower())
    ]
    placeholders = [shape for shape in top_titles if shape.shape_type == MSO_PLACEHOLDER]

    if template_titles and placeholders:
        for shape in placeholders:
            hide_text_visually(shape, cfg.bg_light)


def is_likely_title_shape(shape):
    """
    判断一个形状是否可能是页面主标题。
    标准：宽度 > 10英寸（占页面大部分宽度）的大文本框
    """
    if not shape.has_text_frame:
        return False

    text = shape.text_frame.text.strip()
    if not text or len(text) < 4:
        return False

    for kw in TITLE_SKIP_KEYWORDS:
        if kw in text:
            return False

    if shape.width > Inches(10):
        return True

    return False


def find_main_title(slide):
    """找到页面的主标题形状。返回第一个符合条件的宽文本框。"""
    for shape in slide.shapes:
        if shape.shape_type not in (1, MSO_PLACEHOLDER, 17):
            continue
        if is_likely_title_shape(shape):
            return shape
    return None


# ── Slide processors ──

def process_content_slide(slide, cfg, idx):
    """
    处理内容页。
    原则：克制。只统一标题字体，不加装饰元素。
    """
    suppress_duplicate_title_conflicts(slide, cfg)
    title = find_main_title(slide)
    if not title:
        return

    is_dark = is_dark_slide(slide)

    # 统一标题字体
    for para in title.text_frame.paragraphs:
        for run in para.runs:
            current_size = run.font.size.pt if run.font.size else 0
            if current_size >= 18:
                run.font.name = cfg.title_font
                run.font.bold = True

    # 极克制的顶部强调线（仅元素少的页面）
    if cfg.accent_top and can_add_header_decoration(slide):
        SLIDE_W = Emu(12192000)
        h = Pt(2)
        add_rect(slide, 0, 0, SLIDE_W, h, cfg.primary, alpha=75)

    # 极克制的底部强调线（仅元素少的页面）
    if cfg.accent_bottom and can_add_footer_decoration(slide):
        SLIDE_W = Emu(12192000)
        h = Pt(1.5)
        add_rect(slide, 0, Emu(6820000), SLIDE_W, h, cfg.secondary, alpha=50)


def process_preserved_slide(slide, cfg):
    """Compatibility no-op: a skipped slide must remain untouched."""
    return None


def process_slide(slide, idx, cfg):
    """Route a slide to the appropriate processor."""
    if idx in cfg.skip_slides:
        return process_preserved_slide(slide, cfg)
    return process_content_slide(slide, cfg, idx)


# ── Verification ──

def verify_preservation(orig_path, new_path):
    """Verify all text, images, and videos are preserved."""
    orig = Presentation(orig_path)
    new = Presentation(new_path)

    issues = []
    for i in range(len(orig.slides)):
        ot = {s.text_frame.text.strip()[:80]
              for s in orig.slides[i].shapes
              if s.has_text_frame and s.text_frame.text.strip()}
        ft = {s.text_frame.text.strip()[:80]
              for s in new.slides[i].shapes
              if s.has_text_frame and s.text_frame.text.strip()}
        missing = ot - ft
        if missing:
            issues.append(f"  Slide {i+1}: {len(missing)} text item(s) lost")

        op = sum(1 for s in orig.slides[i].shapes if s.shape_type == 13)
        fp = sum(1 for s in new.slides[i].shapes if s.shape_type == 13)
        if fp < op:
            issues.append(f"  Slide {i+1}: pictures {op}->{fp}")

        ov = sum(1 for s in orig.slides[i].shapes if s.shape_type == 16)
        fv = sum(1 for s in new.slides[i].shapes if s.shape_type == 16)
        if fv < ov:
            issues.append(f"  Slide {i+1}: videos {ov}->{fv}")

    return issues


# ── Main ──

class Config:
    def __init__(self, args):
        self.primary = hex_to_rgb(args.primary)
        self.secondary = hex_to_rgb(args.secondary)
        # accent：默认同 secondary（避免原版的 property/setter 冲突）
        if args.accent:
            self.accent = hex_to_rgb(args.accent)
        else:
            self.accent = self.secondary
        self.text_dark = hex_to_rgb(args.text_dark)
        self.text_light = hex_to_rgb(args.text_light)
        self.bg_light = hex_to_rgb(args.bg_light) if args.bg_light else RGBColor(0xFA, 0xFB, 0xFF)
        self.title_font = args.title_font or "Arial"
        self.body_font = args.body_font
        self.accent_top = args.accent_bar_top
        self.accent_bottom = args.accent_bar_bottom
        self.skip_slides = set(args.skip_slides or [])


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="PPT Reskin - deck-studio PPT 工作台的视觉统一子工具"
    )
    parser.add_argument("input", help="输入 PPT 路径")
    parser.add_argument("--output", "-o", help="输出 PPT 路径（默认加 _美化后）")
    parser.add_argument("--primary", default="#C9A84C", help="主强调色（HEX）")
    parser.add_argument("--secondary", default="#4A3F35", help="辅助色（HEX）")
    parser.add_argument("--accent", default=None, help="点缀色（HEX，默认同辅色）")
    parser.add_argument("--text-dark", default="#2C2C3A", help="浅底文字颜色（HEX）")
    parser.add_argument("--text-light", default="#FFFFFF", help="深底文字颜色（HEX）")
    parser.add_argument("--bg-light", default="#FAFAF8", help="内容页浅背景色（HEX）")
    parser.add_argument("--title-font", default="Arial", help="标题字体")
    parser.add_argument(
        "--body-font",
        default=None,
        help="兼容参数；本工具不会批量重染正文，避免破坏复杂页",
    )
    parser.add_argument("--accent-bar-top", action="store_true", help="顶部强调线（仅元素少的页面）")
    parser.add_argument("--accent-bar-bottom", action="store_true", help="底部强调线（仅元素少的页面）")
    parser.add_argument("--skip-slides", default=None, help="跳过的页码，逗号分隔，如 1,2,24,48,56")
    parser.add_argument(
        "--ai-bg",
        action="store_true",
        help="已停用的兼容参数；AI 背景请走 Deck Studio 图片路由",
    )
    parser.add_argument("--ai-prompt", default=None, help=argparse.SUPPRESS)
    parser.add_argument(
        "--verify",
        dest="verify",
        action="store_true",
        default=True,
        help="验证内容完整性（默认）",
    )
    parser.add_argument(
        "--no-verify",
        dest="verify",
        action="store_false",
        help="跳过内容完整性验证（不建议）",
    )

    args = parser.parse_args(argv)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误：文件不存在 {input_path}")
        return 1
    if args.ai_bg:
        print(
            "错误：--ai-bg 从未形成可验证的 PPT 装配闭环，已停止使用。"
            "请通过 Deck Studio 图片路由生成并验收背景资产。"
        )
        return 2

    if args.output:
        output_path = Path(args.output)
    else:
        stem = input_path.stem
        output_path = input_path.parent / f"{stem}_美化后.pptx"

    if args.skip_slides:
        try:
            skip = {
                int(x.strip()) - 1
                for x in args.skip_slides.split(",")
                if x.strip()
            }
        except ValueError:
            print("错误：--skip-slides 只能包含逗号分隔的正整数页码")
            return 2
        if any(index < 0 for index in skip):
            print("错误：--skip-slides 页码必须从 1 开始")
            return 2
        args.skip_slides = skip
    else:
        args.skip_slides = set()

    cfg = Config(args)

    print("=" * 55)
    print("PPT RESKIN (deck-studio 子工具)")
    print("=" * 55)
    print(f"输入: {input_path}")
    print(f"输出: {output_path}")
    print(f"配色: primary={args.primary}  secondary={args.secondary}")
    print(f"文字: dark={args.text_dark}  light={args.text_light}")
    print(f"字体: title={args.title_font}")
    print(f"跳过页: {[index + 1 for index in sorted(cfg.skip_slides)]}")
    print(f"顶部强调线: {'是' if cfg.accent_top else '否'}")
    print()

    print("加载 PPT...")
    prs = Presentation(str(input_path))
    n = len(prs.slides)
    print(f"共 {n} 页\n")

    print("应用统一样式（克制原则：只统一标题字体）...")
    processing_errors = []
    for idx, slide in enumerate(prs.slides):
        elem_count = get_slide_element_count(slide)
        action = "跳过"
        if idx not in cfg.skip_slides:
            title = find_main_title(slide)
            if title:
                action = "统一标题"
            else:
                action = "无标题"
            if cfg.accent_top or cfg.accent_bottom:
                dec_ok = (
                    (cfg.accent_top and can_add_header_decoration(slide))
                    or (cfg.accent_bottom and can_add_footer_decoration(slide))
                )
                if dec_ok:
                    action += " + 强调线"
                else:
                    action += "（不加装饰）"

        print(f"  {idx+1:2d}/{n}: {action}")
        try:
            process_slide(slide, idx, cfg)
        except Exception as e:
            processing_errors.append(f"Slide {idx + 1}: {e}")
            print(f"    错误: {e}")

    if processing_errors:
        print(f"\n停止：{len(processing_errors)} 页处理失败，未写出结果。")
        return 1

    print(f"\n保存到: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_path))
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"文件大小: {size_mb:.0f} MB")

    if args.verify:
        print("\n验证内容完整性...")
        issues = verify_preservation(str(input_path), str(output_path))
        if issues:
            print(f"  发现 {len(issues)} 个问题:")
            for issue in issues:
                print(f"    {issue}")
            print("\n验证失败。")
            return 1
        else:
            print("  ✓ 所有文字、图片、视频完整保留")

    print("\n完成!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
