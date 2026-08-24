from dataclasses import dataclass
from importlib import resources
from pathlib import Path


class AssetNotFoundError(ValueError):
    pass


@dataclass(frozen=True)
class AssetCatalog:
    root: Path

    @classmethod
    def discover(cls, source_root: Path | None = None) -> "AssetCatalog":
        if source_root is not None:
            return cls(source_root.resolve())

        checkout = Path(__file__).resolve().parents[3]
        if (checkout / "skills").is_dir() and (checkout / "pyproject.toml").is_file():
            return cls(checkout)

        packaged = Path(str(resources.files("waterology_assets")))
        if (packaged / "skills").is_dir():
            return cls(packaged.resolve())
        raise AssetNotFoundError("Waterology assets are missing")

    def path(self, relative: str) -> Path:
        candidate = (self.root / relative).resolve()
        try:
            candidate.relative_to(self.root.resolve())
        except ValueError as error:
            raise AssetNotFoundError(f"Asset is outside the asset root: {relative}") from error
        if not candidate.exists():
            raise AssetNotFoundError(f"Asset does not exist: {relative}")
        return candidate

    def skill_directories(self) -> tuple[Path, ...]:
        return tuple(sorted(path.parent.resolve() for path in self.root.glob("skills/*/SKILL.md")))
