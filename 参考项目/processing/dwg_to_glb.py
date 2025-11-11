"""Batch convert DWG drawings to GLB via Blender.

Pipeline:
DWG --(ODAFileConverter)--> DXF --(Blender python script)--> GLB

Dependencies:
  * ODA/Teigha File Converter (set env var ODA_CONVERTER)
  * Blender installed with DXF import add-on enabled
  * Environment variable BLENDER_EXE pointing to blender.exe

Optional env vars:
  ODA_INPUT_VERSION, ODA_OUTPUT_VERSION, ODA_OUTPUT_FORMAT (default DXF),
  ODA_RECURSIVE, ODA_AUDIT, ODA_LOG, ODA_CMD_TEMPLATE,
  BLENDER_GLTF_TEMPLATE (command template for glTF export)

usage:
  python processing/dwg_to_glb.py 测试-CAD --output processing/converted --keep-dxf
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterable, List, Optional, Tuple


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert DWG files to GLB with Blender")
    parser.add_argument("input", help="Root folder containing DWG files")
    parser.add_argument("--output", "-o", default="processing/converted", help="Directory to store generated GLBs")
    parser.add_argument("--keep-dxf", action="store_true", help="Keep intermediate DXF files alongside GLB")
    parser.add_argument("--blender-python", default=None, help="Optional custom Blender python script path")
    args = parser.parse_args()

    oda_path = Path(os.environ.get("ODA_CONVERTER", "")).expanduser()
    blender_exec = Path(os.environ.get("BLENDER_EXE", "")).expanduser()

    if not oda_path.exists():
        sys.exit("ODA_CONVERTER is not configured or file does not exist")
    if not blender_exec.exists():
        sys.exit("BLENDER_EXE is not configured or file does not exist")

    blender_script_path = Path(args.blender_python) if args.blender_python else create_blender_script()

    input_root = Path(args.input).resolve()
    if not input_root.exists():
        sys.exit(f"Input path not found: {input_root}")

    output_root = Path(args.output).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    dwg_files = list(iter_dwg_files(input_root))
    if not dwg_files:
        print(f"No DWG files under {input_root}")
        return

    print(f"Found {len(dwg_files)} DWG files. Starting conversion...")
    converted = 0
    for dwg in dwg_files:
        rel = dwg.relative_to(input_root)
        target_dir = (output_root / rel.parent).resolve()
        target_dir.mkdir(parents=True, exist_ok=True)
        try:
            glb_path, dxf_retained = convert_single(
                dwg_path=dwg,
                target_dir=target_dir,
                oda_binary=oda_path,
                blender_binary=blender_exec,
                blender_script=blender_script_path,
                keep_dxf=args.keep_dxf,
            )
            converted += 1
            print(f"✔ {dwg} -> {glb_path}")
            if dxf_retained:
                print(f"  ↳ retained DXF at {dxf_retained}")
        except Exception as exc:  # pragma: no cover
            print(f"✘ Failed to convert {dwg}: {exc}", file=sys.stderr)
    print(f"Conversion finished: {converted}/{len(dwg_files)} succeeded. Output in {output_root}")

    if args.blender_python is None:
        blender_script_path.unlink(missing_ok=True)


def iter_dwg_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*.dwg"):
        if path.is_file():
            yield path


def convert_single(
    dwg_path: Path,
    target_dir: Path,
    oda_binary: Path,
    blender_binary: Path,
    blender_script: Path,
    *,
    keep_dxf: bool = False,
) -> Tuple[Path, Optional[Path]]:
    input_version = os.environ.get("ODA_INPUT_VERSION", "ACAD2018")
    output_version = os.environ.get("ODA_OUTPUT_VERSION", "ACAD2018")
    output_format = os.environ.get("ODA_OUTPUT_FORMAT", "DXF")
    recurse = os.environ.get("ODA_RECURSIVE", "0")
    audit = os.environ.get("ODA_AUDIT", "1")
    log_flag = os.environ.get("ODA_LOG", "0")
    oda_template = os.environ.get(
        "ODA_CMD_TEMPLATE",
        '"{converter}" "{input_dir}" "{output_dir}" {input_version} {output_version} {output_format} {recurse} {audit} {log}',
    )
    blender_template = os.environ.get(
        "BLENDER_GLTF_TEMPLATE",
        '"{blender}" --background --factory-startup --python "{script}" -- "{input_dxf}" "{output_glb}"',
    )

    with TemporaryDirectory(prefix=f"dwg2glb_{dwg_path.stem}_") as tmp:
        tmp_dir = Path(tmp)
        stage_input = tmp_dir / "in"
        stage_output = tmp_dir / "out"
        stage_input.mkdir(parents=True)
        stage_output.mkdir(parents=True)
        shadow = stage_input / dwg_path.name
        shadow.write_bytes(dwg_path.read_bytes())

        oda_cmd = oda_template.format(
            converter=str(oda_binary),
            input_dir=str(stage_input),
            output_dir=str(stage_output),
            input_version=input_version,
            output_version=output_version,
            output_format=output_format,
            recurse=recurse,
            audit=audit,
            log=log_flag,
        )
        run_command(oda_cmd)

        dxf_candidates: List[Path] = list(stage_output.rglob("*.dxf")) + list(stage_output.rglob("*.DXF"))
        if not dxf_candidates:
            raise RuntimeError("ODA converter did not produce any DXF file")
        dxf_path_tmp = dxf_candidates[0]

        glb_path = target_dir / f"{dwg_path.stem}.glb"
        blender_cmd = blender_template.format(
            blender=str(blender_binary),
            script=str(blender_script),
            input_dxf=str(dxf_path_tmp),
            output_glb=str(glb_path),
        )
        run_command(blender_cmd)

        retained: Optional[Path]
        if keep_dxf:
            retained = target_dir / f"{dwg_path.stem}.dxf"
            retained.write_bytes(dxf_path_tmp.read_bytes())
        else:
            retained = None

    return glb_path, retained


def create_blender_script() -> Path:
    script = Path.cwd() / "processing" / "_blender_import_export.py"
    script.write_text(
        """
import bpy
import sys
from pathlib import Path

argv = sys.argv
if '--' not in argv:
    raise SystemExit('No arguments passed to blender script')
args = argv[argv.index('--') + 1:]
input_path = Path(args[0])
output_path = Path(args[1])

bpy.ops.wm.read_factory_settings(use_empty=True)

bpy.ops.import_scene.autocad_dxf(filepath=str(input_path))

bpy.ops.export_scene.gltf(filepath=str(output_path), export_format='GLB', export_apply=True)
""",
        encoding="utf-8",
    )
    return script


def run_command(cmd: str) -> None:
    print(f"$ {cmd}")
    completed = subprocess.run(cmd, shell=True)
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {completed.returncode}: {cmd}")


if __name__ == "__main__":
    main()
