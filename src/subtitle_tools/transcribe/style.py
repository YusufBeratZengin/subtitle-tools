"""Validated ASS appearance, loaded from JSON or optional safe YAML."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, fields
from math import isfinite
from pathlib import Path
from typing import Literal

from subtitle_tools.types import AssStyle

_ALIGNMENT = {"bottom": 2, "middle": 5, "upper": 8}


@dataclass(frozen=True)
class Style:
    font: str = "DejaVu Sans"
    font_size: int = 72
    primary_color: str = "&H00FFFFFF"
    highlight_color: str = "&H0000FFFF"
    outline_color: str = "&H00000000"
    outline: float = 4
    bold: bool = True
    position: Literal["bottom", "middle", "upper"] = "bottom"
    margin_v: int = 320

    def __post_init__(self) -> None:
        if (
            not isinstance(self.font, str)
            or not self.font.strip()
            or any(char in self.font for char in ",\n\r{}\\")
        ):
            raise ValueError("Font must be a non-empty name without ASS separators.")
        for name, low, high in (("font_size", 1, 300), ("outline", 0, 20), ("margin_v", 0, 900)):
            value = getattr(self, name)
            if name == "outline":
                numeric = type(value) in (int, float) and isfinite(value)
            else:
                numeric = type(value) is int
            if not numeric or not low <= value <= high:
                kind = "a number" if name == "outline" else "an integer"
                raise ValueError(f"{name} must be {kind} between {low} and {high}.")
        for name in ("primary_color", "highlight_color", "outline_color"):
            value = getattr(self, name)
            if not isinstance(value, str) or re.fullmatch(r"&H[0-9a-fA-F]{8}", value) is None:
                raise ValueError(f"{name} must be an ASS &HAABBGGRR color.")
        if type(self.bold) is not bool:
            raise ValueError("bold must be a boolean.")
        if self.position not in ("bottom", "middle", "upper"):
            raise ValueError("position must be bottom, middle, or upper.")

    def to_ass_style(self) -> AssStyle:
        """Return the core ASS ``Default`` style for a 1080x1920 vertical canvas."""
        return AssStyle(
            name="Default",
            fontname=self.font,
            fontsize=self.font_size,
            primary_colour=self.primary_color,
            secondary_colour=self.highlight_color,
            outline_colour=self.outline_color,
            back_colour="&H80000000",
            bold=-1 if self.bold else 0,
            scale_x=100,
            scale_y=100,
            spacing=0,
            angle=0,
            outline=self.outline,
            shadow=0,
            alignment=_ALIGNMENT[self.position],
            margin_l=60,
            margin_r=60,
            margin_v=self.margin_v,
            encoding=1,
        )


def load_style(path: Path) -> Style:
    suffix = path.suffix.lower()
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
    elif suffix in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as exc:
            raise ValueError("YAML styles require PyYAML (pip install 'subtitle-tools[yaml]'); JSON needs no extra.") from exc
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ValueError("Style YAML is invalid or contains unsafe tags.") from exc
    else:
        raise ValueError("Style file must be JSON or YAML.")
    if not isinstance(data, dict) or any(not isinstance(key, str) for key in data):
        raise ValueError("Style must be a mapping with string keys.")
    unknown = set(data) - {field.name for field in fields(Style)}
    if unknown:
        raise ValueError("Unknown style fields: " + ", ".join(sorted(unknown)))
    return Style(**data)
