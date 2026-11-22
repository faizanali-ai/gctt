#!/usr/bin/env python3
"""Generate transparent 32-bit RGBA PNGs and vector SVGs from brand assets."""
from __future__ import annotations

import subprocess
from pathlib import Path

try:
    import vtracer
except ImportError:
    vtracer = None

STATIC_IMAGES = Path(__file__).resolve().parent.parent / "static" / "images"

ASSETS = [
    {
        "input": "logo-horizontal.png",
        "bg_color": "white",
        "fuzz": "10%",
        "out_png": "logo-horizontal.png",
        "out_svg": "logo-horizontal.svg",
    },
    {
        "input": "logo-horizontal-dark.png",
        "bg_color": "#1f1e23",
        "fuzz": "8%",
        "out_png": "logo-horizontal-dark.png",
        "out_svg": "logo-horizontal-dark.svg",
    },
    {
        "input": "logo-stacked.png",
        "bg_color": "white",
        "fuzz": "10%",
        "out_png": "logo-stacked.png",
        "out_svg": "logo-stacked.svg",
    },
    {
        "input": "logo-stacked-dark.png",
        "bg_color": "#1e1d23",
        "fuzz": "8%",
        "out_png": "logo-stacked-dark.png",
        "out_svg": "logo-stacked-dark.svg",
    },
    {
        "input": "logo-main.png",
        "bg_color": "white",
        "fuzz": "10%",
        "out_png": "logo-main.png",
        "out_svg": "logo-main.svg",
    },
    {
        "input": "logo-main-dark.png",
        "bg_color": "#1e1e23",
        "fuzz": "8%",
        "out_png": "logo-main-dark.png",
        "out_svg": "logo-main-dark.svg",
    },
    {
        "input": "logo-icon-512.png",
        "bg_color": "white",
        "fuzz": "10%",
        "out_png": "logo-icon-512.png",
        "out_svg": "logo-icon.svg",
    },
]


def make_transparent_png(src: Path, dst: Path, bg_color: str, fuzz: str) -> None:
    temp_dst = dst.with_suffix(".tmp.png")
    cmd = [
        "magick",
        str(src),
        "-fuzz",
        fuzz,
        "-transparent",
        bg_color,
        f"png32:{temp_dst}",
    ]
    subprocess.run(cmd, check=True)
    temp_dst.replace(dst)
    print(f"  ✓ Processed transparent PNG: {dst.name}")


def trace_svg(src_png: Path, dst_svg: Path) -> None:
    if vtracer is None:
        raise RuntimeError("vtracer is required for SVG vector generation.")
    vtracer.convert_image_to_svg_py(
        str(src_png),
        str(dst_svg),
        colormode="color",
        hierarchical="stacked",
        mode="spline",
        filter_speckle=4,
        color_precision=8,
        layer_difference=16,
        corner_threshold=60,
        length_threshold=4.0,
        max_iterations=10,
        splice_threshold=45,
        path_precision=3,
    )
    print(f"  ✓ Generated vector SVG: {dst_svg.name}")


def main() -> None:
    print(f"Generating transparent brand assets in {STATIC_IMAGES}...")
    for asset in ASSETS:
        src = STATIC_IMAGES / asset["input"]
        dst_png = STATIC_IMAGES / asset["out_png"]
        dst_svg = STATIC_IMAGES / asset["out_svg"]

        make_transparent_png(src, dst_png, asset["bg_color"], asset["fuzz"])
        trace_svg(dst_png, dst_svg)

    print("All transparent PNGs and vector SVGs generated successfully!")


if __name__ == "__main__":
    main()
