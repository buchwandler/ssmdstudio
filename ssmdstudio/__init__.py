"""Structured authoring projects for LLM-assisted SSMD creation."""

from importlib.metadata import PackageNotFoundError, version

from .models import Character, Feedback, ProjectConfig, Scene
from .project import Studio
from .ssmd import (
    BindingResult,
    SSMDUnavailableError,
    ValidationDiagnostic,
    ValidationResult,
    check_ssmd,
    materialize_voice_bindings,
)
from .templates import TemplateLibrary
from .workspace import Workspace

try:
    __version__ = version("ssmdstudio")
except PackageNotFoundError:  # running directly from an unpacked source tree
    __version__ = "0+unknown"

__all__ = [
    "BindingResult",
    "Character",
    "Feedback",
    "ProjectConfig",
    "SSMDUnavailableError",
    "Scene",
    "Studio",
    "TemplateLibrary",
    "ValidationDiagnostic",
    "ValidationResult",
    "Workspace",
    "__version__",
    "check_ssmd",
    "materialize_voice_bindings",
]
