from __future__ import annotations

import argparse
from pathlib import Path

import trimesh


def convert_to_glb(input_path: Path, output_path: Path, *, merge: bool = True) -> None:
    mesh = trimesh.load(input_path, force='mesh')
    if mesh.is_empty:
        raise SystemExit(f"Failed to load mesh from {input_path}")
    if merge and isinstance(mesh, trimesh.Scene):
        mesh = mesh.dump(concatenate=True)
    if isinstance(mesh, trimesh.Scene):
        scene = mesh
    else:
        scene = trimesh.Scene(mesh)
    glb_data = scene.export(file_type='glb')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(glb_data)
    print(f"Wrote GLB: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description='Convert mesh files (STL/OBJ/PLY) to GLB using trimesh.')
    parser.add_argument('input', help='Input mesh file (STL, OBJ, etc.)')
    parser.add_argument('output', nargs='?', help='Output GLB path (default: same name with .glb)')
    parser.add_argument('--no-merge', action='store_true', help='Do not merge scene geometry before export')
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    output_path = Path(args.output) if args.output else input_path.with_suffix('.glb')
    convert_to_glb(input_path, output_path, merge=not args.no_merge)


if __name__ == '__main__':
    main()
