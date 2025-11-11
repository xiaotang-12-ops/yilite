import bpy
import sys
from pathlib import Path

argv = sys.argv
if '--' not in argv:
    raise SystemExit('No arguments passed to blender script')
args = argv[argv.index('--') + 1:]
if len(args) < 2:
    raise SystemExit('Need input DXF and output GLB paths')
input_path = Path(args[0])
output_path = Path(args[1])

bpy.ops.wm.read_factory_settings(use_empty=True)

try:
    bpy.ops.import_scene.autocad_dxf(filepath=str(input_path))
except Exception as exc:
    raise SystemExit(f'DXF import failed: {exc}')

try:
    bpy.ops.export_scene.gltf(filepath=str(output_path), export_format='GLB', export_apply=True)
except Exception as exc:
    raise SystemExit(f'glTF export failed: {exc}')
