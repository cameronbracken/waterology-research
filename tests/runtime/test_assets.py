from pathlib import Path

import pytest

from waterology.runtime.assets import AssetCatalog, AssetNotFoundError


def test_catalog_uses_an_explicit_source_root(tmp_path: Path) -> None:
    skill = tmp_path / "skills" / "example" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: example\ndescription: Use when testing.\n---\n")

    catalog = AssetCatalog.discover(tmp_path)

    assert catalog.path("skills/example/SKILL.md") == skill.resolve()
    assert catalog.skill_directories() == (skill.parent.resolve(),)


def test_catalog_rejects_parent_traversal(tmp_path: Path) -> None:
    (tmp_path / "skills").mkdir()
    catalog = AssetCatalog.discover(tmp_path)

    with pytest.raises(AssetNotFoundError, match="outside the asset root"):
        catalog.path("../secret.txt")
