"""JSON save/load helpers with friendly errors."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from .project_model import ProjectModel
except ImportError:  # pragma: no cover
    from project_model import ProjectModel


class SaveSystemError(RuntimeError):
    """Raised when a project cannot be saved or loaded."""


def save_project(project: ProjectModel, path: str | Path) -> Path:
    target = Path(path)
    if target.suffix.lower() != ".json":
        target = target.with_suffix(".json")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(project.to_dict(), indent=2), encoding="utf-8")
    except OSError as exc:
        raise SaveSystemError(f"Could not save project: {exc}") from exc
    return target


def load_project(path: str | Path) -> ProjectModel:
    source = Path(path)
    try:
        raw = source.read_text(encoding="utf-8")
        data: Any = json.loads(raw)
    except OSError as exc:
        raise SaveSystemError(f"Could not read project: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SaveSystemError(f"Project JSON is invalid: {exc}") from exc
    if not isinstance(data, dict):
        raise SaveSystemError("Project file must contain a JSON object.")
    return ProjectModel.from_dict(data)
