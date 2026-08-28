# -*- coding: utf-8 -*-
"""Derive a runtime deck manifest from an outline and PPT God project snapshot.

Each <section class="page" data-id data-layout ...> becomes one deck slide whose
image prompt = [STYLE block built from #deck-config] + [layout formula filled with
audience copy from the PPT God snapshot]. HTML supplies visual layout only when a
snapshot is present. deck.json is derived and must never be hand-edited.

Usage:
  python outline_to_deck.py outline.html                 # -> deck.json next to it
  python outline_to_deck.py outline.html --out deck.json
  python outline_to_deck.py outline.html --project-snapshot project_snapshot.json

Requires: beautifulsoup4  (uv pip install beautifulsoup4)
The executable formulas in this module are authoritative. The prompt cookbook
explains them but is not a second implementation source.
"""
import argparse
import json
import os
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from bs4 import BeautifulSoup

SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from templates.project_snapshot_contract import (
    is_project_snapshot,
    load_json_source,
    snapshot_slide_family,
    snapshot_assets,
    validate_content_gate,
)

NUM = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six"}
LOCK = ("Keep text MEDIUM-sized and medium-weight, elegant and readable, "
        "well-composed with breathing room.")


def q(text):
    return "'" + text.replace("'", "’") + "'"


def qjoin(items, sep=", "):
    return sep.join(q(x) for x in items)


def count_word(items):
    return NUM.get(len(items), str(len(items)))


def build_style(style, size):
    accent = "%s (%s)" % (style.get("accent_name", "warm gold"),
                          style.get("accent_hex", "#c79a5b"))
    tone = style.get("tone_words", "expensive, magazine-quality")
    material = style.get("material", "").strip()
    material_clause = (" %s for material atmosphere." % material) if material else ""
    if style.get("mode") == "light":
        bg_clause = ("A softly-lit BRIGHT cinematic background photograph (gently out of "
                     "focus) gives the page atmosphere and depth, with a soft bright gradient "
                     "overlay (slightly deeper tone where text sits) for legibility")
        type_color = "deep charcoal"
    else:
        bg_clause = ("A softly-lit cinematic background photograph (gently out of focus) "
                     "gives the page atmosphere and depth, with an elegant dark gradient "
                     "overlay (deeper where text sits) for legibility")
        type_color = "clean"
    return (
        "Ultra-premium 16:9 editorial keynote slide, %s, ART-DIRECTED like a high-end brand "
        "campaign deck — NOT a plain text-on-a-flat-color slide. %s. Sophisticated layered, "
        "asymmetric composition, clear visual hierarchy, generous breathing room. Typography: "
        "refined MEDIUM-WEIGHT %s modern sans-serif Chinese with standard square (方块字) "
        "proportions — elegant and clearly readable, but NOT oversized and NOT heavy/bold; a "
        "small letter-spaced kicker, a medium title, small body text. %s thin hairline rules "
        "and small tasteful accents.%s Cohesive, %s. Render every Chinese character and number "
        "correctly and crisply. " % (size, bg_clause, type_color, accent, material_clause, tone)
    )


def kicker_clause(kicker, accent_name):
    return "Small %s kicker %s; " % (accent_name, q(kicker)) if kicker else ""


def build_content(layout, kicker, title, sub, bg, items, accent_name, text_side):
    """Return the per-page clause after the STYLE block (content/data page types)."""
    head = "Background: %s. The text sits over %s. %s" % (
        bg, text_side, kicker_clause(kicker, accent_name))
    if title:
        head += "medium title %s. " % q(title)
    n = count_word(items)

    if layout in ("bullets", "points"):
        body = "%s calm points with thin %s line-icons: %s. " % (n, accent_name, qjoin(items))
    elif layout == "stats":
        body = "%s elegant glass-like stat panels with thin %s borders: %s. " % (
            n, accent_name, qjoin(items))
    elif layout == "chips":
        body = "%s refined chips in a row: %s. " % (n, qjoin(items))
    elif layout in ("steps", "flow"):
        body = "A horizontal %d-step flow with %s connectors: %s. " % (
            len(items), accent_name, qjoin(items, " → "))
    elif layout == "cards":
        body = "%s refined slim cards with small %s line-icons, each a medium card title + a small line: %s. " % (
            n, accent_name, qjoin(items))
    elif layout in ("list", "toc"):
        numbered = ["%02d %s" % (i + 1, x) for i, x in enumerate(items)]
        body = "A clean vertical numbered list: %s, each with a thin %s divider line. " % (
            qjoin(numbered), accent_name)
    elif layout == "table":
        body = "A clean elegant table: %s. " % qjoin(items)
    elif layout in ("two-col", "twocol"):
        if len(items) >= 2:
            body = "Left keywords %s; right a note %s. " % (q(items[0]), q(items[1]))
        else:
            body = "Two balanced columns: %s. " % qjoin(items)
    elif layout == "quadrant":
        body = "A subtle 2x2 quadrant with one highlighted %s quadrant and muted others: %s. " % (
            accent_name, qjoin(items))
    elif layout == "funnel":
        body = "A descending funnel: %s. " % qjoin(items, " / ")
    elif layout == "persona":
        body = "%s refined persona cards: %s. " % (n, qjoin(items))
    else:  # default / "content"
        body = "Render these as %s refined elements with small %s accents: %s. " % (
            n, accent_name, qjoin(items)) if items else ""
    caption = "Small caption %s. " % q(sub) if sub else ""
    return head + body + caption + LOCK


def build_special(layout, kicker, title, sub, bg, items, style):
    """Cover / divider / transition / big-idea / back-cover / spotlight / kol."""
    accent_name = style.get("accent_name", "warm gold")
    grad = "a soft bright gradient" if style.get("mode") == "light" else "dark gradient"

    if layout == "cover":
        return ("COVER. Background: %s. Centered: an elegant medium-large title %s; "
                "below a small line %s. Atmospheric, refined, not bold. " % (
                    bg, q(title), q(sub or "")) + LOCK)
    if layout in ("back-cover", "backcover"):
        return ("BACK-COVER. Background: %s at dusk, deep mood. Centered: an elegant title "
                "%s; a small line below %s. Minimal, refined. " % (bg, q(title), q(sub or "")))
    if layout == "divider":
        return ("SECTION DIVIDER. Background: %s, cinematic, atmospheric, %s. Centered-left: "
                "a small %s tag %s, a large but elegant (not heavy) title %s. Minimal, premium, "
                "lots of mood. Render the Chinese text crisply. " % (
                    bg, grad, accent_name, q(kicker or ""), q(title)))
    if layout in ("transition", "quote"):
        return ("SECTION TRANSITION. Background: %s at dusk, deep mood. Centered: an elegant "
                "(not heavy) line %s; a small subtitle %s. " % (bg, q(title), q(sub or "")))
    if layout in ("big-idea", "bigidea"):
        pillars = (" Below, %d refined pillars: %s." % (len(items), qjoin(items, " / "))
                   if items else "")
        return ("BIG-IDEA slide. Background: %s with a single hero light beam, deep mood. "
                "Small kicker 'BIG IDEA'. A large elegant %s title %s.%s Medium text, not heavy. " % (
                    bg, accent_name, q(title), pillars))
    if layout == "spotlight":
        chips = (" An arrow to %s." % qjoin(items) if items else "")
        return ("Background: %s with a single warm spotlight on an empty space. A large "
                "highlighted %s panel %s. Below, a small line %s.%s " % (
                    bg, accent_name, q(title), q(sub or ""), chips) + LOCK)
    if layout == "kol":
        slogan = items[0] if items else ""
        clean = "clean and dark" if style.get("mode") != "light" else "clean and bright"
        return (
            "Keep the EXACT face, identity and likeness of the person in the provided photo — "
            "preserve their recognizable facial features, age and hairstyle precisely. Re-create "
            "THIS SAME PERSON in a premium cinematic 16:9 brand key-visual photograph, set in %s; "
            "soft flattering light, moody, photorealistic editorial quality. Place the person on "
            "the RIGHT half; keep the LEFT half %s. In that clean area render refined modern "
            "sans-serif Chinese text with STANDARD SQUARE character proportions (each character "
            "fits a 1:1 square box — natural 方块字, NOT condensed, NOT stretched, NOT italic) and "
            "a REGULAR/MEDIUM weight (NOT bold): a small letter-spaced %s tag %s at top; a "
            "medium-large white title %s; a small grey line %s; a %s slogan %s. Make the type "
            "MEDIUM-LARGE and clearly prominent while keeping REGULAR/MEDIUM weight and square "
            "proportions. Render every Chinese character correctly and crisply. No watermark, no "
            "extra logos, no extra people, no caricature." % (
                bg, clean, accent_name, q(kicker or ""), q(title), q(sub or ""),
                accent_name, q(slogan)))
    return None


SPECIAL = {"cover", "back-cover", "backcover", "divider", "transition", "quote",
           "big-idea", "bigidea", "spotlight", "kol"}
KNOWN = SPECIAL | {"bullets", "points", "stats", "chips", "steps", "flow", "cards",
                   "list", "toc", "table", "two-col", "twocol", "quadrant", "funnel",
                   "persona", "content"}


def infer_layout(sec):
    classes = sec.get("class", [])
    if "finale" in classes:
        return "back-cover"
    if "divi" in classes:
        return "divider"
    return "content"


def text_of(node, selector):
    el = node.select_one(selector)
    return el.get_text(" ", strip=True) if el else ""


def _public_from_snapshot(slide):
    """Return audience copy from a snapshot slide without inventing a sidecar schema."""
    public = slide.get("public")
    if not isinstance(public, dict):
        public = slide.get("content")
    if not isinstance(public, dict):
        public = slide.get("content_json")
    if not isinstance(public, dict):
        public = slide
    if isinstance(public.get("text_content"), dict):
        public = public["text_content"]
    title = str(public.get("title") or public.get("headline") or "").strip()
    if not title:
        sys.exit("project snapshot slide %s has no audience title" % slide.get("page_num"))
    body = public.get("body")
    if body is None:
        body = public.get("copy") or []
    if isinstance(body, str):
        body = [body]
    return {
        "kicker": str(public.get("kicker") or "").strip(),
        "title": title,
        "claim": str(public.get("claim") or public.get("subtitle") or "").strip(),
        "body": [str(item).strip() for item in body if str(item).strip()],
        "source_line": str(public.get("source_line") or "").strip(),
    }


def parse_outline(html_path, project_snapshot=None):
    soup = BeautifulSoup(open(html_path, encoding="utf-8").read(), "html.parser")
    cfg_tag = soup.select_one("#deck-config")
    cfg = json.loads(cfg_tag.get_text()) if cfg_tag else {}
    style = cfg.get("style", {})
    scene = style.get("scene_domain", "an upscale modern interior at golden hour")
    size = cfg.get("size", "3840x2160")
    style_block = build_style(style, size)
    accent_name = style.get("accent_name", "warm gold")
    text_side = ("the softly shaded side" if style.get("mode") == "light"
                 else "the darker gradient side")

    slides, ids, unknown = [], [], []
    sections = soup.select("section.page")
    if not sections:
        sys.exit("no <section class=\"page\"> found in " + html_path)
    snapshot_slides = []
    legacy_slides = []
    if project_snapshot is not None:
        if is_project_snapshot(project_snapshot):
            snapshot_slides = sorted(
                project_snapshot.get("slides") or [], key=lambda item: item["page_num"]
            )
        else:
            # Read-only compatibility for existing Python callers and archived
            # regression fixtures. The CLI never accepts this legacy sidecar.
            legacy_slides = sorted(
                project_snapshot.get("slides") or [],
                key=lambda item: item.get("slide", item.get("page_num", 0)),
            )
        state_slides = snapshot_slides or legacy_slides
        if len(state_slides) != len(sections):
            sys.exit(
                "project state has %d slides but outline has %d sections"
                % (len(state_slides), len(sections))
            )

    for i, sec in enumerate(sections):
        sid = sec.get("data-id") or ("S%02d" % (i + 1))
        layout = (sec.get("data-layout") or infer_layout(sec)).strip()
        kicker = (sec.get("data-kicker") or text_of(sec, ".kick")
                  or sec.get("data-ch", "")).strip()
        bg = (sec.get("data-bg") or scene).strip()
        photo = (sec.get("data-photo") or "").strip()
        title = (sec.get("data-title") or text_of(sec, ".title, h1, h2")).strip()
        sub = (sec.get("data-sub") or "").strip()
        items = [x.strip() for x in (sec.get("data-sum") or "").split(" / ")
                 if x.strip()]

        # Once a snapshot is supplied, it is the only source of audience copy and
        # production state. HTML remains a visual/layout description only.
        state_slides = snapshot_slides or legacy_slides
        if state_slides:
            public = _public_from_snapshot(state_slides[i])
            kicker = public["kicker"]
            title = public["title"]
            sub = public["claim"]
            items = list(public["body"])
            source_line = public["source_line"]
            if source_line:
                items.append(source_line)

        if layout not in KNOWN:
            unknown.append("%s:%s" % (sid, layout))

        clause = build_special(layout, kicker, title, sub, bg, items, style)
        if clause is None:
            clause = build_content(layout, kicker, title, sub, bg, items, accent_name, text_side)
        prompt = style_block + clause

        slide = {"id": sid, "prompt": prompt}
        if photo:
            slide["photo"] = photo
        if state_slides:
            snapshot_slide = state_slides[i]
            for field in (
                "page_num",
                "production_type",
                "visual_role",
                "type",
                "evidence_state",
                "source_ref",
                "image_path",
                "layout_spec",
                "visual_json",
                "prompt_text",
                "knowledge_route",
                "knowledge_contract",
                "specialist_route",
                "media_contract",
                "media_validation_report",
                # Legacy audit-only fields retained for in-process callers.
                "mode",
                "production_route",
                "overlay_policy",
                "overlay_assets",
                "edit_mask",
                "source_lock",
                "reference_assets",
                "specialist_asset",
                "specialist_asset_scope",
                "framed_asset",
            ):
                if snapshot_slide.get(field) not in (None, ""):
                    slide[field] = snapshot_slide[field]
            if snapshot_slides:
                slide["family"] = snapshot_slide_family(project_snapshot, snapshot_slide)
                slide_id = str(snapshot_slide.get("id") or "")
                bound_assets = [
                    asset for asset in snapshot_assets(project_snapshot)
                    if str(asset.get("slide_id") or "") == slide_id
                ]
                if bound_assets:
                    slide["assets"] = bound_assets
        slides.append(slide)
        ids.append(sid)

    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        sys.exit("duplicate data-id: %s" % ", ".join(dupes))
    if unknown:
        print("WARN unknown data-layout (fell back to generic): " + ", ".join(unknown))

    return {
        "outdir": "pptimg",
        "size": size,
        "quality": cfg.get("quality", "high"),
        "workers": cfg.get("workers", 1),
        "slides": slides,
    }


def main():
    parser = argparse.ArgumentParser(description="derive deck.json from an outline HTML")
    parser.add_argument("outline", help="path to outline HTML")
    parser.add_argument("--out", help="output deck.json (default: deck.json next to outline)")
    parser.add_argument(
        "--project-snapshot",
        required=True,
        help="read-only project_snapshot JSON file or URL from PPT God",
    )
    args = parser.parse_args()

    project_snapshot = load_json_source(args.project_snapshot)
    errors = validate_content_gate(project_snapshot)
    if errors:
        sys.exit("project snapshot rejected: " + "; ".join(errors))

    deck = parse_outline(args.outline, project_snapshot)
    out = args.out or os.path.join(os.path.dirname(os.path.abspath(args.outline)), "deck.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(deck, f, ensure_ascii=False, indent=2)
        f.write("\n")
    edit_sources = sum(
        1
        for slide in deck["slides"]
        if slide.get("photo") or slide.get("specialist_asset")
    )
    print("wrote %s  |  %d slides (%d with edit source)  |  size %s  outdir %s" % (
        out, len(deck["slides"]), edit_sources, deck["size"], deck["outdir"]))
    print("next: sample-gate with gen_deck.py --only <id1>,<id2>  (never batch before the gate)")


if __name__ == "__main__":
    main()
