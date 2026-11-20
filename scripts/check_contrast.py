"""Fail if the GCTT colour tokens fall below WCAG AA contrast."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "static" / "css" / "input.css"

TOKEN_RE = re.compile(r"(--[a-z0-9-]+)\s*:\s*([^;]+);")
LIGHT_RE = re.compile(r":root\s*\{(.*?)\}", re.DOTALL)
DARK_RE = re.compile(r"@variant\s+dark\s*\{\s*:root\s*\{(.*?)\}", re.DOTALL)

PAIRS = (
    ("ink", "canvas"),
    ("ink", "surface"),
    ("ink", "raised"),
    ("muted", "surface"),
    ("muted", "raised"),
    ("subtle", "surface"),
    ("accent", "surface"),
    ("accent", "canvas"),
    ("accent", "raised"),
    ("on-accent", "accent"),
    ("success", "surface"),
    ("warning", "surface"),
    ("danger", "surface"),
    ("night-ink", "night"),
    ("night-muted", "night"),
    ("night-accent", "night"),
)


def read_tokens(block: str) -> dict[str, str]:
    return {name: value.strip() for name, value in TOKEN_RE.findall(block)}


def channels(value: str) -> tuple[float, float, float]:
    value = value.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(character * 2 for character in value)
    if not re.fullmatch(r"[0-9a-fA-F]{6}", value):
        raise ValueError(value)
    return tuple(int(value[index : index + 2], 16) / 255 for index in (0, 2, 4))


def luminance(value: str) -> float:
    red, green, blue = channels(value)

    def linear(channel: float) -> float:
        return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4

    return 0.2126 * linear(red) + 0.7152 * linear(green) + 0.0722 * linear(blue)


def ratio(foreground: str, background: str) -> float:
    first, second = luminance(foreground), luminance(background)
    return (max(first, second) + 0.05) / (min(first, second) + 0.05)


def main() -> int:
    text = CSS.read_text(encoding="utf-8")
    light = read_tokens(LIGHT_RE.search(text).group(1))
    dark_match = DARK_RE.search(text)
    dark = {**light, **read_tokens(dark_match.group(1))} if dark_match else light

    failures: list[str] = []
    for theme, palette in (("light", light), ("dark", dark)):
        for foreground, background in PAIRS:
            if foreground not in palette or background not in palette:
                continue
            try:
                value = ratio(palette[foreground], palette[background])
            except ValueError:
                continue
            mark = "ok" if value >= 4.5 else "FAIL"
            print(f"{theme:5} {foreground:13} on {background:13} {value:5.2f}:1  {mark}")
            if value < 4.5:
                failures.append(f"{theme}: {foreground} on {background} = {value:.2f}:1")

    if failures:
        print("\nContrast failures:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    print("\nAll token contrast pairs pass 4.5:1.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
