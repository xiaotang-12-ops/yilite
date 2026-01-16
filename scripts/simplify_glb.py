# -*- coding: utf-8 -*-
"""
对单个 GLB 文件做自动简化并输出新的 GLB，便于本地验证简化效果。

用法：
  python scripts/simplify_glb.py input.glb output.glb
  python scripts/simplify_glb.py input.glb output.glb --force
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from processors.glb_simplifier import AutoSimplifyOptions, auto_simplify_scene


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str, help="输入GLB路径")
    parser.add_argument("output", type=str, help="输出GLB路径")
    parser.add_argument("--force", action="store_true", help="强制尝试简化（忽略触发阈值）")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    scene = trimesh.load(str(input_path), force="scene")
    options = AutoSimplifyOptions.from_env()
    if args.force:
        options = AutoSimplifyOptions(
            enabled=True,
            trigger_nodes_geometry=0,
            min_root_descendant_geometry=options.min_root_descendant_geometry,
            min_total_collapsed_geometry=options.min_total_collapsed_geometry,
            brush_keywords=options.brush_keywords,
        )

    simplified, report = auto_simplify_scene(scene, options=options)
    output_path.write_bytes(simplified.export(file_type="glb"))

    report_path = output_path.with_suffix(output_path.suffix + ".simplify_report.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("✅ simplify_glb 完成")
    print(f"  input:  {input_path}")
    print(f"  output: {output_path}")
    print(f"  report: {report_path}")
    print(f"  applied: {report.get('applied')}")
    if report.get("applied"):
        print(f"  nodes_geometry: {report.get('nodes_geometry_before')} -> {report.get('nodes_geometry_after')}")
    else:
        print(f"  reason: {report.get('reason')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
