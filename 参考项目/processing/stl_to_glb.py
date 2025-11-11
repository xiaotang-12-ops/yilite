#!/usr/bin/env python3
"""
Convert STL meshes into GLB files that can be consumed by the prototype viewer.

Example usage (from repo root):

  python processing/stl_to_glb.py . --output-dir glb

The script walks the input path recursively for *.stl files and writes a GLB next
to each match inside the chosen output directory.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Iterable

import trimesh


def find_stl_files(source: Path) -> Iterable[Path]:
    if source.is_file():
        return [source] if source.suffix.lower() == ".stl" else []
    return sorted(source.rglob("*.stl"))


def convert_file(stl_path: Path, output_dir: Path, scale: float) -> Path:
    mesh = trimesh.load(stl_path, force="scene")
    if mesh.is_empty:
        raise RuntimeError(f"{stl_path} did not contain any geometry")

    if scale != 1.0:
        # Apply optional unit scale (e.g. mm -> m uses 0.001)
        mesh.apply_scale(scale)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / (stl_path.stem + ".glb")

    mesh.export(output_path, file_type="glb")
    return output_path


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="STL file or directory to scan")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("glb"),
        help="Directory where GLB files will be stored (default: ./glb)",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=0.001,
        help="Uniform scale factor to apply before export (default: 0.001 for mm -> m)",
    )

    args = parser.parse_args(argv)

    stl_files = list(find_stl_files(args.source))
    if not stl_files:
        print("No STL files found.", file=sys.stderr)
        return 1

    for stl in stl_files:
        print(f"Converting {stl} ...", flush=True)
        try:
            output_path = convert_file(stl, args.output_dir, args.scale)
        except Exception as exc:  # pragma: no cover - helper
            print(f"  Failed: {exc}", file=sys.stderr)
            continue
        print(f"  -> {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
