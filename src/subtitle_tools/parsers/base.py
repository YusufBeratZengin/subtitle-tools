"""Base classes and registry for subtitle parsers and writers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from subtitle_tools.types import SubtitleDocument


class BaseSubtitleParser(ABC):
    """Abstract base class for subtitle parsers."""

    @abstractmethod
    def parse(self, text: str) -> SubtitleDocument:
        """Parse subtitle file content string into a SubtitleDocument."""
        raise NotImplementedError


class BaseSubtitleWriter(ABC):
    """Abstract base class for subtitle writers."""

    @abstractmethod
    def write(self, doc: SubtitleDocument) -> str:
        """Serialize a SubtitleDocument into subtitle format string."""
        raise NotImplementedError
