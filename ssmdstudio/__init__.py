"""Structured authoring projects for LLM-assisted SSMD creation."""

from importlib.metadata import PackageNotFoundError, version

from .models import Character, Feedback, ProjectConfig, Scene
from .project import Studio

try:
    __version__ = version("ssmdstudio")
except PackageNotFoundError:  # running directly from an unpacked source tree
    __version__ = "0+unknown"

__all__ = [
    "Character",
    "Feedback",
    "ProjectConfig",
    "Scene",
    "Studio",
    "__version__",
]
