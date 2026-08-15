from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]


def test_format_unification_uses_batched_compact_visual_qa():
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    execute = (SKILL_ROOT / "workflows" / "03-execute.md").read_text(
        encoding="utf-8"
    )
    verify = (SKILL_ROOT / "workflows" / "04-verify.md").read_text(
        encoding="utf-8"
    )

    assert "先验证每种页型的一张代表页，再批量执行" in skill
    assert "每个阶段主上下文最多查看一张轻量 WebP contact sheet" in skill
    assert "只做一次针对性文档搜索和一个最小探针" in skill
    assert "不要默认把批次内每页逐张打开" in execute
    assert "不要用 `detail=original` 依次打开全部改动页" in verify


def test_representative_page_only_authorizes_its_family():
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    design = (SKILL_ROOT / "workflows" / "02-design.md").read_text(
        encoding="utf-8"
    )
    checklist = (SKILL_ROOT / "knowledge" / "check-list.md").read_text(
        encoding="utf-8"
    )

    assert "代表页通过只授权同页型批次" in skill
    assert "代表页确认只批准其所属家族" in design
    assert "代表页只能批准同家族批次" in checklist
    assert "verify_page_families.py" in skill
    assert "当改动覆盖 3 页以上、涉及 2 个以上页型或准备批量应用规则时" in skill


def test_skill_upgrades_pass_an_abstraction_gate():
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")

    assert "### 升级抽象门" in skill
    assert "写出反例" in skill
    assert "客户名、页码、指定字体、指定色值和具体构图只留在案例" in skill
    assert "小任务可用简短契约解决时" in skill
    assert "创建清单、配置或新文件" in skill


def test_rewritten_pages_have_scoped_typography_gate():
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    verify = (SKILL_ROOT / "workflows" / "04-verify.md").read_text(
        encoding="utf-8"
    )

    assert "--include-slides" in skill
    assert "--allowed-fonts" in verify
    assert "--fail-on-inherited" in verify


def test_focusmedia_routes_are_first_class_and_orthogonal():
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    readme = (SKILL_ROOT / "README.md").read_text(encoding="utf-8")
    routing = (SKILL_ROOT / "references" / "production-routing.md").read_text(
        encoding="utf-8"
    )
    focusmedia = (
        SKILL_ROOT / "references" / "focusmedia-integration.md"
    ).read_text(encoding="utf-8")

    assert "knowledge_route" in skill
    assert "specialist_route" in skill
    assert "references/focusmedia-integration.md" in skill
    assert "references/focusmedia-integration.md" in readme
    assert "focusmedia-integration.md" in routing
    assert "reference-fusion" in skill
    assert "media_validation_report" in focusmedia
    assert "verify_focusmedia_output.py" in focusmedia
    assert "标准带框图" in focusmedia
    assert "不得平贴整台设备" in focusmedia
    assert "specialist_asset_scope" in focusmedia
    assert "不再交给 PPT God 或通用图片模型重画" in focusmedia
    assert "普通 PPT 不加载" in focusmedia
    assert "media_validation_report" not in skill


def test_retired_ai_background_generator_is_removed():
    assert not (SKILL_ROOT / "templates" / "ai_bg.py").exists()


def test_pure_image_defaults_are_bounded_and_source_safe():
    template = (SKILL_ROOT / "assets" / "outline-template.html").read_text(
        encoding="utf-8"
    )
    pitfalls = (SKILL_ROOT / "references" / "pitfalls.md").read_text(
        encoding="utf-8"
    )

    assert '"workers": 1' in template
    assert "不得扫描其他产品配置" in pitfalls
    assert "不要手改派生出的" in pitfalls
