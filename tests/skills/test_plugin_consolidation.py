import re
from pathlib import Path

import yaml

from waterology.runtime.assets import AssetCatalog

ROOT = Path(__file__).resolve().parents[2]


def skill_metadata(name: str) -> dict[str, object]:
    text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
    return yaml.safe_load(text.split("---", 2)[1])


def test_plugin_consolidation_skills_are_discoverable() -> None:
    catalog = AssetCatalog.discover()
    names = {directory.name for directory in catalog.skill_directories()}

    assert {"writing-style", "research-software-quality"} <= names
    for name in ("writing-style", "research-software-quality"):
        metadata = skill_metadata(name)
        assert metadata["name"] == name
        assert str(metadata["description"]).startswith("Use when ")


def test_writing_workflows_use_the_shared_style_skill() -> None:
    consumers = (
        ROOT / "agent-definitions/reviewer.md",
        ROOT / "agent-definitions/writer.md",
        ROOT / "skills/audit-reproducibility/SKILL.md",
        ROOT / "skills/autoresearch/SKILL.md",
        ROOT / "skills/deep-research/SKILL.md",
        ROOT / "skills/eli5/SKILL.md",
        ROOT / "skills/figure-composer/SKILL.md",
        ROOT / "skills/figure-style/SKILL.md",
        ROOT / "skills/literature-review/SKILL.md",
        ROOT / "skills/ml-training-recipe/SKILL.md",
        ROOT / "skills/paper-code-audit/SKILL.md",
        ROOT / "skills/paper-writing/SKILL.md",
        ROOT / "skills/paper-narrative/SKILL.md",
        ROOT / "skills/pdf-explore/SKILL.md",
        ROOT / "skills/publish-blog-post/SKILL.md",
        ROOT / "skills/replication/SKILL.md",
        ROOT / "skills/research-review/SKILL.md",
        ROOT / "skills/session-log/SKILL.md",
        ROOT / "skills/source-comparison/SKILL.md",
        ROOT / "skills/watch/SKILL.md",
    )

    for path in consumers:
        assert "writing-style" in path.read_text(encoding="utf-8"), path


def test_canonical_agents_use_proportional_quality_guidance() -> None:
    for path in sorted((ROOT / "agent-definitions").glob("*.md")):
        assert "research-software-quality" in path.read_text(encoding="utf-8"), path


def test_project_guidance_uses_waterology_replacement_skills() -> None:
    guidance = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert "writing-style" in guidance
    assert "research-software-quality" in guidance
    assert "superpowers:writing-skills" not in guidance

    conventions = (ROOT / "skills/project-conventions/SKILL.md").read_text(encoding="utf-8")
    assert "research-software-quality" in conventions
    assert "Relationship to superpowers" not in conventions
    assert "Run constraints only" in conventions
    assert "Do not run constraints for read only work" in conventions
    assert "Do not repeat a successful run" in conventions

    assert "Skip them for read only work and unchanged validated content" in guidance


def test_local_preferences_resolver_is_packaged_without_personal_content() -> None:
    conventions = (ROOT / "skills/project-conventions/SKILL.md").read_text()
    reference = ROOT / "skills/project-conventions/references/local-preferences.md"
    assert "references/local-preferences.md" in conventions
    assert "waterology config context project-conventions" in conventions
    assert "WATEROLOGY_CONFIG" in reference.read_text()
    assert "repository hygiene" in conventions.lower()


def test_research_workflows_write_to_docs_directory() -> None:
    all_workflows = (
        *sorted((ROOT / "commands").glob("*.md")),
        *sorted((ROOT / "skills").glob("*/SKILL.md")),
    )

    for path in all_workflows:
        assert "outputs/" not in path.read_text(encoding="utf-8"), path

    path_consumers = (
        ROOT / "skills/deep-research/SKILL.md",
        ROOT / "skills/deep-research/references/workflow.md",
        ROOT / "skills/literature-review/SKILL.md",
        ROOT / "skills/research-review/SKILL.md",
        ROOT / "skills/source-summarization/references/workflow.md",
    )
    for path in path_consumers:
        assert "docs/" in path.read_text(encoding="utf-8"), path


def test_worktree_decision_fixtures_cover_the_cutoff() -> None:
    fixture_path = ROOT / "skills/research-software-quality/references/worktree-cases.yaml"
    data = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))
    decisions = {case["id"]: case["decision"] for case in data["cases"]}

    assert decisions == {
        "already-isolated": "reuse",
        "behavioral-edit": "create",
        "clean-documentation": "work-in-place",
        "concurrent-writer": "create",
        "dirty-checkout": "create",
        "related-multi-file-change": "create",
    }


def test_worktree_guidance_standardizes_location_and_manager() -> None:
    path = ROOT / "skills/research-software-quality/references/worktrees.md"
    guidance = path.read_text(encoding="utf-8")

    assert "Worktrunk" in guidance
    assert "command -v wt" in guidance
    assert 'worktree-path="{{ repo_path }}/.worktrees/' in guidance
    assert "Git worktree fallback" in guidance


def test_session_log_is_portable_and_owns_its_artifact_contract() -> None:
    text = (ROOT / "skills/session-log/SKILL.md").read_text(encoding="utf-8")

    assert "`/log`" not in text
    assert "notes/<date>-session.md" in text
    assert "open questions" in text.lower()
    assert "external claims" in text.lower()


def test_paper_code_audit_is_portable_and_owns_its_evidence_contract() -> None:
    text = (ROOT / "skills/paper-code-audit/SKILL.md").read_text(encoding="utf-8")

    assert "`/audit`" not in text
    assert "docs/.plans/<slug>.md" in text
    assert "docs/<slug>-audit.md" in text
    assert "README" in text
    assert "verifier" in text


def test_source_comparison_is_portable_and_owns_its_matrix_contract() -> None:
    text = (ROOT / "skills/source-comparison/SKILL.md").read_text(encoding="utf-8")

    assert "`/compare`" not in text
    assert "docs/.plans/<slug>.md" in text
    assert "docs/<slug>-comparison.md" in text
    assert "evidence type" in text.lower()
    assert "agreement" in text.lower()
    assert "verifier" in text
    assert "verify every source URL and inline citation directly" in text
    assert "delegate verification" in text


def test_watch_is_portable_and_separates_baseline_from_scheduling() -> None:
    text = (ROOT / "skills/watch/SKILL.md").read_text(encoding="utf-8")

    assert "`/watch`" not in text
    assert "`/loop" not in text
    assert "docs/.plans/<slug>.md" in text
    assert "docs/<slug>-baseline.md" in text
    assert "Scheduling: manual" in text
    assert "explicitly asks" in text


def test_paper_writing_is_portable_and_preserves_result_provenance() -> None:
    text = (ROOT / "skills/paper-writing/SKILL.md").read_text(encoding="utf-8")

    assert "`/draft`" not in text
    assert "docs/.plans/<slug>.md" in text
    assert "papers/<slug>.md" in text
    assert "computed number" in text
    assert "placeholder" in text
    assert "writer" in text and "verifier" in text


def test_literature_review_is_portable_and_preserves_multihop_search() -> None:
    text = (ROOT / "skills/literature-review/SKILL.md").read_text(encoding="utf-8")

    assert "`/lit`" not in text
    assert "docs/.plans/<slug>.md" in text
    assert "docs/<slug>.provenance.md" in text
    assert "hop" in text.lower()
    assert "publication corpus" in text.lower()
    assert "verifier" in text and "reviewer" in text


def test_research_review_is_portable_and_leaves_a_review_when_blocked() -> None:
    text = (ROOT / "skills/research-review/SKILL.md").read_text(encoding="utf-8")

    assert "`/review`" not in text
    assert "docs/.plans/<slug>-review-plan.md" in text
    assert "docs/.drafts/<slug>-review-evidence.md" in text
    assert "docs/<slug>-review.md" in text
    assert "Verification: BLOCKED" in text
    assert "reviewer" in text


def test_ml_training_recipe_is_portable_and_checks_dataset_usability() -> None:
    text = (ROOT / "skills/ml-training-recipe/SKILL.md").read_text(encoding="utf-8")

    assert "`/recipe`" not in text
    assert "docs/.plans/<slug>-recipe.md" in text
    assert "docs/.drafts/<slug>-recipe-research.md" in text
    assert "docs/<slug>-recipe.provenance.md" in text
    assert "dataset" in text.lower() and "unverified" in text
    assert "implementation" in text.lower()
    assert "researcher" in text


def test_replication_is_portable_and_requires_environment_authorization() -> None:
    text = (ROOT / "skills/replication/SKILL.md").read_text(encoding="utf-8")

    assert "`/replicate`" not in text
    assert "explicit environment" in text.lower()
    assert "do not install" in text.lower()
    assert "until the user confirms" in text.lower()
    for assessment in (
        "aligned",
        "partially aligned",
        "inconclusive under this setup",
        "not attempted",
    ):
        assert f"`{assessment}`" in text
    assert "CHANGELOG.md" in text
    assert "claim ledger" in text.lower()


def test_autoresearch_is_portable_bounded_and_reproducible() -> None:
    text = (ROOT / "skills/autoresearch/SKILL.md").read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    rule = (ROOT / "skills/autoresearch/references/experiment-tree.md").read_text(encoding="utf-8")
    token_rule = (ROOT / "skills/autoresearch/references/token-discipline.md").read_text(
        encoding="utf-8"
    )

    assert "`/autoresearch" not in text
    assert "Engineering" in text and "Research" in text
    assert "Do not request permission again" in text
    assert "Begin in the same turn" in normalized
    assert "durable goal or continuation mechanism" in normalized
    assert "Do not ask the user to issue a separate goal command" in normalized
    assert "waterology study create" in text
    assert "waterology study advance" in text
    assert "never fall back" in text.lower()
    assert "TORC" in text
    assert "retry cap" in text and "iteration/time budget" in text
    assert "autoresearch.jsonl" in text
    assert "experiment-tree.md" in text
    assert "[token-discipline.md](references/token-discipline.md)" in text
    assert "does not generate code" in text
    assert "`/autoresearch" not in rule
    assert "fixed benchmark" in token_rule.lower()
    assert "in tree mode" in token_rule.lower()
    assert "machine readable status file" in token_rule.lower()
    assert "minimum context" in token_rule.lower()
    assert "authoritative evidence" in token_rule.lower()


def test_deep_research_is_portable_and_preserves_durable_delivery() -> None:
    skill = (ROOT / "skills/deep-research/SKILL.md").read_text(encoding="utf-8")
    workflow_path = ROOT / "skills/deep-research/references/workflow.md"

    assert "`/deepresearch`" not in skill
    assert "references/workflow.md" in skill
    assert workflow_path.is_file()

    workflow = workflow_path.read_text(encoding="utf-8")
    for artifact in (
        "docs/.plans/<slug>.md",
        "docs/.drafts/<slug>-draft.md",
        "docs/.drafts/<slug>-cited.md",
        "<slug>.provenance.md",
    ):
        assert artifact in workflow
    assert "explicit confirmation" in workflow.lower()
    assert "direct search" in workflow.lower()
    assert workflow.index("`verifier`") < workflow.index("`reviewer`")
    assert "Verification: BLOCKED" in workflow


def test_source_summarization_is_portable_bounded_and_single_source() -> None:
    skill_path = ROOT / "skills/source-summarization/SKILL.md"
    workflow_path = ROOT / "skills/source-summarization/references/workflow.md"

    assert skill_path.is_file()
    assert workflow_path.is_file()
    skill = skill_path.read_text(encoding="utf-8")
    workflow = workflow_path.read_text(encoding="utf-8")
    eli5 = (ROOT / "skills/eli5/SKILL.md").read_text(encoding="utf-8")

    assert "references/workflow.md" in skill
    assert "`/summarize`" not in skill
    assert "`/summarize`" not in eli5
    assert "source-summarization" in eli5
    assert "docs/<slug>-summary.md" in workflow
    assert "window-size > overlap" in workflow
    assert "tier1-threshold < tier2-threshold" in workflow
    for tier in ("Tier 1", "Tier 2", "Tier 3"):
        assert tier in workflow
    assert "researcher" in workflow
    assert "Coverage gaps" in workflow
    assert "single confirmed source" in workflow.lower()
    assert "Do not seek by byte offset" in workflow
    assert "decoded string" in workflow

    researcher = (ROOT / "agent-definitions/researcher.md").read_text(encoding="utf-8")
    assert "Single source chunk mode" in researcher
    assert "five source minimum does not apply" in researcher.lower()
    assert "Do not search the web" in researcher


def test_agent_delegation_is_portable_and_explicit_about_ownership() -> None:
    skill_path = ROOT / "skills/agent-delegation/SKILL.md"

    assert skill_path.is_file()
    skill = skill_path.read_text(encoding="utf-8")
    assert "`orx" not in skill.lower()
    assert "worktree" in skill.lower()
    assert "compute" in skill.lower()
    assert "definition of done" in skill.lower()
    assert "nothing merges" in skill.lower()
    assert "output path" in skill.lower()


def test_canonical_agents_enforce_the_receiving_delegation_contract() -> None:
    for path in sorted((ROOT / "agent-definitions").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        body = text.split("---", 2)[2]
        if body.lstrip().startswith("<!--"):
            body = body.split("-->", 1)[1]
        assert "## Delegated task contract" in text, path
        assert "worktree" in text.lower(), path
        assert "compute" in text.lower(), path
        assert "output path" in text.lower(), path
        assert "do not merge" in text.lower(), path
        assert "orx" not in body.lower(), path


def test_research_skills_are_portable() -> None:
    names = (
        "agent-delegation",
        "autoresearch",
        "bib-validate",
        "capture-environment",
        "compile-latex",
        "deep-research",
        "eli5",
        "figure-composer",
        "figure-style",
        "literature-review",
        "ml-training-recipe",
        "myst-to-quarto",
        "paper-code-audit",
        "paper-narrative",
        "paper-writing",
        "pdf-explore",
        "replication",
        "research-review",
        "session-log",
        "simulation-study",
        "source-comparison",
        "source-summarization",
        "pipeline-manifest",
        "watch",
    )

    for name in names:
        path = ROOT / "skills" / name / "SKILL.md"
        text = path.read_text(encoding="utf-8")
        assert "CLAUDE_PLUGIN_ROOT" not in text, path
        assert "WebFetch" not in text, path
        for command in (
            "deepresearch",
            "lit",
            "draft",
            "review",
            "audit",
            "compare",
            "replicate",
            "recipe",
            "summarize",
            "watch",
            "log",
            "autoresearch",
        ):
            assert f"`/{command}" not in text, path


def test_skills_and_rules_leave_attribution_in_the_ledger() -> None:
    for directory in (ROOT / "skills", ROOT / "rules"):
        for path in directory.rglob("*"):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            assert "<!--" not in text, path
            assert "attribution.md" not in text.lower(), path
            assert "adapted from" not in text.lower(), path
            assert "copyright" not in text.lower(), path


def test_attribution_records_pinned_delegation_source_and_generated_commands() -> None:
    text = (ROOT / "ATTRIBUTION.md").read_text(encoding="utf-8")

    assert "agent-skills/orx-agent-delegation/SKILL.md" in text
    assert "13049867497de8fd5e15253cd818462629edd690" in text
    assert "generated Claude compatibility shims" in text
    assert "source-summarization" in text

    for path in sorted((ROOT / "commands").glob("*.md")):
        command = path.read_text(encoding="utf-8")
        assert "<!-- Generated from skills/" in command, path
        assert "<!-- Adapted from" not in command, path
        assert not re.search(r"commit\s+[0-9a-f]{40}", command), path


def test_personalized_skills_have_resolvable_plugin_only_fallbacks() -> None:
    for name in (
        "writing-style",
        "setup-environment",
        "publish-blog-post",
        "figure-style",
        "paper-writing",
    ):
        path = ROOT / "skills" / name / "SKILL.md"
        text = path.read_text()
        assert "../project-conventions/references/local-preferences.md" in text
        assert (path.parent / "../project-conventions/references/local-preferences.md").is_file()
    writing = (ROOT / "skills/writing-style/SKILL.md").read_text()
    assert "`preferences.files`, `writing.files`, `writing.papers`" in writing
