"""STEP 转 GLB 转换器，附带格式预检、编码检测与GLB名称修复。"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Optional

import chardet
import trimesh

from processors.file_processor import ModelProcessor, _inspect_step_file_format
from utils.logger import print_info, print_warning


class StepToGlbConverter:
    def __init__(self, model_processor: Optional[ModelProcessor] = None):
        self.model_processor = model_processor or ModelProcessor()

    def detect_encoding(self, step_path: Path) -> tuple[str, float]:
        raw = step_path.read_bytes()
        result = chardet.detect(raw[: min(len(raw), 500_000)])
        return (result.get("encoding") or "").lower(), float(result.get("confidence") or 0)

    # GB系列编码统一映射到GB18030（最完整的中文编码，兼容GB2312和GBK）
    GB_ENCODING_MAP = {
        "gb2312": "gb18030",
        "gbk": "gb18030",
        "gb18030": "gb18030",
        "hz-gb-2312": "gb18030",
        "iso-2022-cn": "gb18030",
    }

    def convert(self, step_path: str, output_path: str, scale_factor: float = 0.001) -> dict:
        """将STEP转换为GLB，自动预检格式/编码，完成后修复GLB名称。"""
        tmp_file: Optional[Path] = None
        encoding = None
        confidence = 0.0
        try:
            source_path = Path(step_path)

            # 先挡掉明显不是文本 STEP 的文件，避免被 chardet 误判成中文编码后继续跑重转换。
            step_probe = _inspect_step_file_format(str(source_path))
            if source_path.suffix.lower() in (".step", ".stp") and not step_probe.get("supported"):
                return {
                    "success": False,
                    "error": (
                        "当前系统仅支持文本 STEP（ISO-10303-21 / Part 21）导入，"
                        "该文件头部不像标准文本 STEP，更像二进制或其他 CAD 导出格式。"
                        "请让用户重新导出为标准 STEP 后再上传。"
                    ),
                    "message": "step格式不支持",
                    "step_probe": step_probe,
                }

            encoding, confidence = self.detect_encoding(source_path)
            use_path = source_path

            # 如果探测到的编码不是UTF-8且可信度较高，先转换为UTF-8临时文件
            if encoding and encoding not in ("utf-8", "utf_8") and confidence >= 0.5:
                try:
                    # 将GB系列编码统一映射到GB18030，避免字符丢失
                    actual_encoding = self.GB_ENCODING_MAP.get(encoding.lower(), encoding)
                    if actual_encoding != encoding:
                        print_info(f"🔄 编码映射: {encoding} → {actual_encoding}")

                    text = source_path.read_bytes().decode(actual_encoding, errors="replace")
                    with tempfile.NamedTemporaryFile(suffix=source_path.suffix, delete=False) as tmp:
                        tmp.write(text.encode("utf-8", errors="replace"))
                        tmp_file = Path(tmp.name)
                        use_path = tmp_file
                    print_info(f"🌐 STEP编码检测: {encoding} (confidence={confidence:.2f})，已转为UTF-8临时文件")
                except Exception as encode_err:
                    print_warning(f"编码转换失败，继续使用原文件: {encode_err}")

            result = self.model_processor.step_to_glb(
                step_path=str(use_path),
                output_path=output_path,
                scale_factor=scale_factor
            )

            # 成功后尝试修复GLB内的名称
            if result.get("success"):
                result["encoding_detected"] = encoding or "unknown"
                result["encoding_confidence"] = confidence
                self._fix_glb_names(Path(output_path))
            elif step_probe:
                result.setdefault("step_probe", step_probe)

            return result
        finally:
            if tmp_file and tmp_file.exists():
                tmp_file.unlink(missing_ok=True)

    # ---------- 内部工具 ----------
    def _fix_glb_names(self, glb_path: Path) -> None:
        """二次修复GLB内部的名称编码，避免乱码。"""
        try:
            scene = trimesh.load(glb_path, force="scene")
        except Exception as e:
            print_warning(f"GLB名称修复时加载失败: {e}")
            return

        if not isinstance(scene, trimesh.Scene):
            return

        def decode_name(name: str) -> str:
            if not name:
                return name
            if re.search(r"[\u4e00-\u9fff]", name):
                return name

            candidates = []
            # 尝试将现有字符串当作latin1/cp1252字节再按常见中文编码解码
            for raw_enc in ("latin1", "cp1252"):
                try:
                    raw_bytes = str(name).encode(raw_enc, errors="ignore")
                except Exception:
                    continue
                for target in ("gb18030", "gbk", "utf-8"):
                    try:
                        decoded = raw_bytes.decode(target, errors="ignore")
                        if decoded and re.search(r"[\u4e00-\u9fff]", decoded):
                            return decoded
                        candidates.append(decoded)
                    except Exception:
                        continue
            return candidates[0] if candidates else str(name)

        name_map = {}
        new_geometry = {}

        # 先修复 geometry 名称
        for old_name, geom in scene.geometry.items():
            fixed = decode_name(old_name) or str(old_name)
            base = fixed
            idx = 1
            candidate = base
            while candidate in new_geometry and new_geometry[candidate] is not geom:
                idx += 1
                candidate = f"{base}_{idx}"
            new_geometry[candidate] = geom
            name_map[old_name] = candidate

        if name_map:
            scene.geometry = new_geometry

            # 更新 graph 引用的 geometry 名称，使用 graph.update 保证绑定不会失效
            for node in list(scene.graph.nodes_geometry):
                try:
                    transform, geom_name = scene.graph[node]
                    fixed_geom_name = name_map.get(geom_name, geom_name)
                    scene.graph.update(
                        frame_from=None,
                        frame_to=node,
                        matrix=transform,
                        geometry=fixed_geom_name
                    )
                except Exception:
                    continue

            # 绑定完整性自检
            with_geom = [n for n in scene.graph.nodes if scene.graph[n][1] is not None]
            if scene.geometry and len(with_geom) / len(scene.geometry) < 0.95:
                print_warning(
                    f"GLB名称修复后绑定缺失：with_geom={len(with_geom)}, geometry={len(scene.geometry)}"
                )
                return

            # 重新导出覆盖
            glb_path.parent.mkdir(parents=True, exist_ok=True)
            glb_path.write_bytes(scene.export(file_type="glb"))
            print_info(f"🔤 已修复GLB名称编码: {glb_path.name}")
