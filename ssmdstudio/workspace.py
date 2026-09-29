from __future__ import annotations

from pathlib import Path
from typing import Any

from .project import Studio
from .store import load_yaml, slugify, write_yaml


class Workspace:
    """An optional collection of standalone SSMD Studio projects."""

    def __init__(self, root: Path, config: dict[str, Any]):
        self.root = root.resolve()
        self.config = config

    @property
    def config_path(self) -> Path:
        return self.root / ".ssmdstudio" / "workspace.yaml"

    @property
    def projects_root(self) -> Path:
        return self.root / "projects"

    @classmethod
    def init(cls, path: str | Path = ".") -> Workspace:
        root = Path(path).resolve()
        config_path = root / ".ssmdstudio" / "workspace.yaml"
        if config_path.exists():
            raise FileExistsError(f"workspace already exists at {root}")
        for ancestor in (root, *root.parents):
            if (ancestor / "project.yaml").is_file():
                raise ValueError(
                    f"cannot initialize a workspace inside an SSMD Studio project {ancestor}"
                )
        root.mkdir(parents=True, exist_ok=True)
        (root / ".ssmdstudio").mkdir(exist_ok=True)
        (root / "projects").mkdir(exist_ok=True)
        config = {"schema": "ssmdstudio.workspace.v1", "active_project": None}
        write_yaml(config_path, config)
        return cls(root, config)

    @classmethod
    def open(cls, path: str | Path = ".") -> Workspace:
        root = cls.find_root(Path(path))
        config_path = root / ".ssmdstudio" / "workspace.yaml"
        config = load_yaml(config_path)
        return cls(root, config)

    @staticmethod
    def find_root(path: Path) -> Path:
        current = path.resolve()
        if current.is_file():
            current = current.parent
        for candidate in (current, *current.parents):
            if (candidate / ".ssmdstudio" / "workspace.yaml").is_file():
                return candidate
        raise FileNotFoundError(f"no ssmdstudio workspace found from {path}")

    @property
    def active_project_id(self) -> str | None:
        value = self.config.get("active_project")
        return str(value) if value else None

    def create_project(
        self,
        project_id: str,
        *,
        title: str,
        brief: str,
        recipe: str = "funny-story",
        language: str = "en",
        audience: str = "general",
        tone: str = "warm comic",
        duration_minutes: float | None = None,
        constraints: list[str] | None = None,
    ) -> Studio:
        normalized_id = slugify(project_id)
        return Studio.init(
            self.projects_root / normalized_id,
            title=title,
            brief=brief,
            project_id=normalized_id,
            recipe=recipe,
            language=language,
            audience=audience,
            tone=tone,
            duration_minutes=duration_minutes,
            constraints=constraints,
        )

    def list_projects(self) -> list[Studio]:
        projects: list[Studio] = []
        if self.projects_root.is_dir():
            for project_file in sorted(self.projects_root.glob("*/project.yaml")):
                projects.append(Studio.open(project_file.parent))
        return projects

    def resolve_project(self, project_id: str | None = None) -> Studio:
        selected_id = project_id or self.active_project_id
        if not selected_id:
            raise ValueError("no active project selected; use `ssmdstudio project use ID`")
        normalized_id = slugify(selected_id)
        project_path = self.projects_root / normalized_id
        if not (project_path / "project.yaml").is_file():
            raise FileNotFoundError(f"workspace project {normalized_id!r} does not exist")
        return Studio.open(project_path)

    def use_project(self, project_id: str) -> Studio:
        studio = self.resolve_project(project_id)
        self.config["active_project"] = studio.config.id
        write_yaml(self.config_path, self.config)
        return studio

    def show_project(self, project_id: str | None = None) -> tuple[Studio, bool]:
        studio = self.resolve_project(project_id)
        return studio, studio.config.id == self.active_project_id
