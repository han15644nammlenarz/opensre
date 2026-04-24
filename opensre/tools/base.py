"""Base tool interface for opensre.

All tools must inherit from BaseTool and implement the required methods.
Follows the tool contract defined in .cursor/rules/tools.mdc.
"""

from __future__ import annotations

import abc
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ToolParams:
    """Generic container for tool input parameters."""

    raw: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:  # noqa: ANN401
        """Retrieve a parameter by key with an optional default."""
        return self.raw.get(key, default)

    def require(self, key: str) -> Any:  # noqa: ANN401
        """Retrieve a required parameter; raises KeyError if absent."""
        if key not in self.raw:
            raise KeyError(f"Required parameter '{key}' is missing from tool input.")
        return self.raw[key]


@dataclass
class ToolResult:
    """Standardised result returned by every tool."""

    success: bool
    output: Any = None  # noqa: ANN401
    error: str | None = None

    @classmethod
    def ok(cls, output: Any = None) -> "ToolResult":  # noqa: ANN401
        """Convenience constructor for a successful result."""
        return cls(success=True, output=output)

    @classmethod
    def fail(cls, error: str) -> "ToolResult":
        """Convenience constructor for a failed result."""
        return cls(success=False, error=error)


class BaseTool(abc.ABC):
    """Abstract base class that every opensre tool must implement.

    Subclasses are expected to:
    - Set a unique ``my_tool_name`` class attribute.
    - Implement :meth:`is_available` to report runtime availability.
    - Implement :meth:`extract_params` to parse raw inputs.
    - Implement :meth:`run` to execute the tool logic.
    """

    #: Unique snake_case identifier for this tool (see tools.mdc).
    my_tool_name: str = ""

    def __init_subclass__(cls, **kwargs: Any) -> None:  # noqa: ANN401
        super().__init_subclass__(**kwargs)
        if not getattr(cls, "my_tool_name", ""):
            raise TypeError(
                f"Tool '{cls.__name__}' must define a non-empty 'my_tool_name' attribute."
            )

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Return True when the tool's external dependencies are reachable."""

    @abc.abstractmethod
    def extract_params(self, raw: dict[str, Any]) -> ToolParams:
        """Validate and normalise *raw* input into a :class:`ToolParams` instance."""

    @abc.abstractmethod
    def run(self, params: ToolParams) -> ToolResult:
        """Execute the tool with the given *params* and return a :class:`ToolResult`."""

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def safe_run(self, raw: dict[str, Any]) -> ToolResult:
        """End-to-end helper: validate availability, extract params, and run.

        Catches unexpected exceptions and wraps them in a failed :class:`ToolResult`
        so callers always receive a predictable return type.
        """
        if not self.is_available():
            return ToolResult.fail(f"Tool '{self.my_tool_name}' is not available.")

        try:
            params = self.extract_params(raw)
            return self.run(params)
        except KeyError as exc:
            logger.warning("[%s] Missing parameter: %s", self.my_tool_name, exc)
            return ToolResult.fail(str(exc))
        except Exception as exc:  # noqa: BLE001
            logger.exception("[%s] Unexpected error during run.", self.my_tool_name)
            return ToolResult.fail(f"Unexpected error: {exc}")

    def __repr__(self) -> str:
        return f"<{type(self).__name__} tool_name={self.my_tool_name!r}>"
