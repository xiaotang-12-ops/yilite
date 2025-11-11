from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import trimesh


def split_stl_to_glb(input_path: Path, output_path: Path) -> None:
    scene_or_mesh = trimesh.load_mesh(input_path, force='mesh')
    if isinstance(scene_or_mesh, trimesh.Scene):
        mesh = scene_or_mesh.dump(concatenate=True)
    else:
        mesh = scene_or_mesh

    components = mesh.split(only_watertight=False)
    if len(components) == 1:
        print('Warning: STL only has one connected component; output will equal input.')

    scene = trimesh.Scene()
    for idx, comp in enumerate(components, start=1):
        name = f'Part_{idx:03d}'
        # Reset origin to component centroid
        centroid = comp.centroid
        comp.apply_translation(-centroid)
        transform = np.eye(4)
        transform[:3,3] = centroid
        scene.add_geometry(comp, node_name=name, transform=transform)

    glb_data = scene.export(file_type='glb')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(glb_data)
    print(f'Wrote GLB with {len(components)} parts -> {output_path}')


def main() -> None:
    parser = argparse.ArgumentParser(description='Split STL into per-component GLB for explode animation')
    parser.add_argument('input', help='Input STL file path')
    parser.add_argument('output', nargs='?', help='Output GLB path')
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f'Input file not found: {input_path}')
    output_path = Path(args.output) if args.output else input_path.with_suffix('.split.glb')
    split_stl_to_glb(input_path, output_path)


if __name__ == '__main__':
    main()
