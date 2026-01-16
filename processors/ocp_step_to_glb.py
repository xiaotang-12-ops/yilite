# -*- coding: utf-8 -*-
"""
OCP(OpenCASCADE) 兜底的 STEP -> GLB 转换：
- 用于处理 trimesh/cascadio 在加载/三角化阶段卡死或失败的 STEP 文件。
- 默认只在回退路径启用，允许用更粗的三角化参数生成可用的 GLB。
"""

from __future__ import annotations

import os
import re
import shutil
import signal
import tempfile
from dataclasses import dataclass
from multiprocessing import Process, Queue
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple


_CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")


def _decode_maybe_chinese(text: str) -> str:
    if not text:
        return ""
    if _CHINESE_RE.search(text):
        return text
    try:
        raw_bytes = str(text).encode("latin1", errors="ignore")
    except Exception:
        return str(text)
    for enc in ("gb18030", "gbk", "utf-8"):
        try:
            decoded = raw_bytes.decode(enc, errors="ignore")
        except Exception:
            continue
        if decoded and _CHINESE_RE.search(decoded):
            return decoded
    return str(text)


def _contains_any(text: str, keywords: Sequence[str]) -> bool:
    if not text:
        return False
    lowered = text.lower()
    for keyword in keywords:
        if not keyword:
            continue
        if keyword in text or keyword.lower() in lowered:
            return True
    return False


def _trailing_int(text: str) -> Optional[int]:
    match = re.search(r"(\d+)$", text or "")
    if not match:
        return None
    try:
        return int(match.group(1))
    except Exception:
        return None


def _safe_node_name(name: str, used: Set[str], fallback_prefix: str, index: int) -> str:
    base = (name or "").strip()
    if not base:
        base = f"{fallback_prefix}{index:05d}"
    base = re.sub(r"[\r\n\t]+", " ", base)
    base = base.replace("\\", "_").replace("/", "_")
    candidate = base
    suffix = 1
    while candidate in used:
        suffix += 1
        candidate = f"{base}_{suffix}"
    used.add(candidate)
    return candidate


def _terminate_process(process: Process) -> None:
    if not process.is_alive():
        return
    process.terminate()
    process.join(timeout=5)
    if not process.is_alive():
        return
    if process.pid:
        try:
            os.kill(process.pid, getattr(signal, "SIGKILL", signal.SIGTERM))
        except Exception:
            pass
    process.join(timeout=2)


@dataclass(frozen=True)
class OcpFallbackOptions:
    enabled: bool = True
    timeout_seconds: int = 600
    linear_deflection: float = 1.0
    angular_deflection: float = 0.5
    max_meshes: int = 500
    collapse_leaf_threshold: int = 800
    brush_keywords: Tuple[str, ...] = ("毛刷", "刷片", "刷丝", "brush", "bristle")

    @classmethod
    def from_env(cls) -> "OcpFallbackOptions":
        def _bool(name: str, default: bool) -> bool:
            raw = os.getenv(name)
            if raw is None:
                return default
            return raw.strip().lower() in ("1", "true", "yes", "y", "on")

        def _int(name: str, default: int) -> int:
            raw = os.getenv(name)
            if not raw:
                return default
            try:
                return int(raw)
            except Exception:
                return default

        def _float(name: str, default: float) -> float:
            raw = os.getenv(name)
            if not raw:
                return default
            try:
                return float(raw)
            except Exception:
                return default

        return cls(
            enabled=_bool("OCP_STEP_FALLBACK", True),
            timeout_seconds=_int("OCP_STEP_FALLBACK_TIMEOUT_SECONDS", 600),
            linear_deflection=_float("OCP_MESH_LINEAR_DEFLECTION", 1.0),
            angular_deflection=_float("OCP_MESH_ANGULAR_DEFLECTION", 0.5),
            max_meshes=_int("OCP_MAX_MESHES", 500),
            collapse_leaf_threshold=_int("OCP_COLLAPSE_LEAF_THRESHOLD", 800),
        )


def _read_step_with_xde(step_path: str) -> Tuple[Any, Any]:
    from OCP.STEPCAFControl import STEPCAFControl_Reader
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.TDocStd import TDocStd_Document
    from OCP.XCAFApp import XCAFApp_Application
    from OCP.XCAFDoc import XCAFDoc_DocumentTool

    # cadquery-ocp 暴露的是 GetApplication_s（pythonocc-core 中通常叫 GetApplication）
    app = XCAFApp_Application.GetApplication_s()
    doc = TDocStd_Document(TCollection_ExtendedString("ocp-doc"))

    reader = STEPCAFControl_Reader()
    reader.SetColorMode(True)
    reader.SetNameMode(True)
    reader.SetLayerMode(True)

    status = reader.ReadFile(str(step_path))
    if int(status) != 1:
        raise RuntimeError(f"STEP 读取失败: status={status}")

    ok = reader.Transfer(doc)
    if not ok:
        raise RuntimeError("STEP Transfer(doc) 失败")

    shape_tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    return doc, shape_tool


def _label_entry(label: Any) -> str:
    try:
        from OCP.TCollection import TCollection_AsciiString
        from OCP.TDF import TDF_Tool

        entry = TCollection_AsciiString()
        TDF_Tool.Entry(label, entry)
        return entry.ToCString()
    except Exception:
        return ""


def _label_name(label: Any) -> str:
    try:
        from OCP.TDataStd import TDataStd_Name

        attr = TDataStd_Name()
        if label.FindAttribute(TDataStd_Name.GetID_s(), attr):
            value = attr.Get()
            try:
                return _decode_maybe_chinese(value.ToExtString())
            except Exception:
                return _decode_maybe_chinese(str(value))
    except Exception:
        pass

    entry = _label_entry(label)
    return entry or "Unnamed"


def _collect_components(shape_tool: Any, label: Any) -> List[Any]:
    try:
        from OCP.TDF import TDF_LabelSequence

        seq = TDF_LabelSequence()
        shape_tool.GetComponents_s(label, seq)
        return [seq.Value(i + 1) for i in range(seq.Length())]
    except Exception:
        return []


def _collect_free_shapes(shape_tool: Any) -> List[Any]:
    try:
        from OCP.TDF import TDF_LabelSequence

        seq = TDF_LabelSequence()
        shape_tool.GetFreeShapes(seq)
        return [seq.Value(i + 1) for i in range(seq.Length())]
    except Exception:
        return []


def _count_leaf_parts(shape_tool: Any, root: Any, memo: Dict[str, int]) -> int:
    key = _label_entry(root) or str(id(root))
    if key in memo:
        return memo[key]

    try:
        is_assembly = bool(shape_tool.IsAssembly_s(root))
    except Exception:
        is_assembly = False

    if not is_assembly:
        memo[key] = 1
        return 1

    children = _collect_components(shape_tool, root)
    if not children:
        memo[key] = 1
        return 1

    total = 0
    for child in children:
        total += _count_leaf_parts(shape_tool, child, memo)
    memo[key] = total
    return total


def _select_mesh_labels(
    shape_tool: Any,
    roots: List[Any],
    options: OcpFallbackOptions,
) -> List[Tuple[Any, str, str, int]]:
    """
    返回 [(label, node_name, geometry_name, leaf_count)] 列表；默认尽量保留层级，但在叶子数量过大时折叠。
    说明：OCP 兜底用于“卡死/超大模型”，因此这里优先保证可生成与可渲染。
    """
    leaf_memo: Dict[str, int] = {}
    selected: List[Tuple[Any, str, str, int]] = []

    def _ref_label(label: Any) -> Optional[Any]:
        try:
            if bool(shape_tool.IsReference_s(label)):
                from OCP.TDF import TDF_Label

                ref = TDF_Label()
                if shape_tool.GetReferredShape_s(label, ref):
                    return ref
        except Exception:
            pass
        return None

    def _node_name(label: Any) -> str:
        name = _label_name(label)
        if name and name != "Unnamed":
            return name
        entry = _label_entry(label)
        return entry or "Unnamed"

    def _geometry_name(label: Any) -> str:
        ref = _ref_label(label)
        if ref is not None:
            ref_name = _label_name(ref)
            if ref_name:
                return ref_name
        return _label_name(label) or _label_entry(label) or "Unnamed"

    def _walk(label: Any, depth: int) -> None:
        node_name = _node_name(label)
        geom_name = _geometry_name(label)
        detect_name = geom_name or node_name

        try:
            is_assembly = bool(shape_tool.IsAssembly_s(label))
        except Exception:
            is_assembly = False

        if not is_assembly:
            selected.append((label, node_name, geom_name, 1))
            return

        leaf_count = _count_leaf_parts(shape_tool, label, leaf_memo)

        if _contains_any(detect_name, options.brush_keywords) and _trailing_int(detect_name) is not None:
            selected.append((label, node_name, geom_name, leaf_count))
            return

        # 不轻易折叠根节点（depth==0），优先下钻拿到更像“组件”的层级
        if depth > 0 and leaf_count >= options.collapse_leaf_threshold:
            selected.append((label, node_name, geom_name, leaf_count))
            return

        children = _collect_components(shape_tool, label)
        if not children:
            selected.append((label, node_name, geom_name, leaf_count))
            return

        for child in children:
            _walk(child, depth + 1)

    for root in roots:
        _walk(root, 0)

    if len(selected) <= options.max_meshes:
        return selected

    # 过多：回退到“根的直接子组件”
    fallback: List[Tuple[Any, str, str, int]] = []
    for root in roots:
        children = _collect_components(shape_tool, root)
        if not children:
            fallback.append((root, _node_name(root), _geometry_name(root), _count_leaf_parts(shape_tool, root, leaf_memo)))
            continue
        for child in children:
            fallback.append((child, _node_name(child), _geometry_name(child), _count_leaf_parts(shape_tool, child, leaf_memo)))

    if len(fallback) <= options.max_meshes:
        return fallback

    # 仍然过多：最终回退为每个 root 一个 mesh（极端兜底）
    return [(_root, _node_name(_root), _geometry_name(_root), _count_leaf_parts(shape_tool, _root, leaf_memo)) for _root in roots]


def _ocp_worker(step_path: str, output_path: str, scale_factor: float, queue: Queue) -> None:
    try:
        import numpy as np
        import trimesh
        from OCP.BRepMesh import BRepMesh_IncrementalMesh
        from OCP.StlAPI import StlAPI_Writer

        options = OcpFallbackOptions.from_env()
        if not options.enabled:
            queue.put({"success": False, "error": "OCP fallback disabled", "message": "ocp转换失败"})
            return

        step_path = str(step_path)
        output_path = str(output_path)

        _, shape_tool = _read_step_with_xde(step_path)
        roots = _collect_free_shapes(shape_tool)
        if not roots:
            queue.put({"success": False, "error": "XDE 未找到任何 FreeShapes", "message": "ocp转换失败"})
            return

        selected = _select_mesh_labels(shape_tool, roots, options)

        tmp_dir = Path(tempfile.mkdtemp(prefix="ocp_step_"))
        used_nodes: Set[str] = set()
        used_geometry: Set[str] = set()

        try:
            scene = trimesh.Scene()

            writer = StlAPI_Writer()
            try:
                writer.SetASCIIMode(False)
            except Exception:
                pass

            for idx, (label, node_name_raw, geom_name_raw, leaf_count) in enumerate(selected):
                node_name = _safe_node_name(node_name_raw, used_nodes, "node_", idx)
                geom_name = _safe_node_name(geom_name_raw, used_geometry, "geom_", idx)

                try:
                    shape = shape_tool.GetShape_s(label)
                except Exception:
                    continue

                if not shape or getattr(shape, "IsNull", lambda: True)():
                    continue

                # 先用可控参数做三角化，再导出 STL；避免在 Python 层手撸三角化数组导致过慢
                try:
                    BRepMesh_IncrementalMesh(
                        shape,
                        float(options.linear_deflection),
                        False,
                        float(options.angular_deflection),
                        True,
                    )
                except Exception:
                    # 即使失败也尝试继续写 STL（部分 OCCT 会在写出时自行网格化）
                    pass

                stl_path = tmp_dir / f"{idx:05d}.stl"
                try:
                    writer.Write(shape, str(stl_path))
                except Exception:
                    continue
                if not stl_path.exists() or stl_path.stat().st_size == 0:
                    continue

                mesh = trimesh.load(str(stl_path), force="mesh")
                if getattr(mesh, "is_empty", False):
                    continue

                # node_name 尽量保留 NAUO；geometry_name 尽量保留零件/组件名（用于 BOM 代号提取）
                scene.add_geometry(
                    mesh,
                    node_name=node_name,
                    geom_name=geom_name,
                    transform=np.eye(4),
                )

            if scene.is_empty:
                queue.put({"success": False, "error": "OCP 转换后 Scene 为空", "message": "ocp转换失败"})
                return

            if scale_factor != 1.0:
                scene.apply_scale(scale_factor)

            # 可选：复用现有自动简化逻辑（只在超大节点模型触发）
            simplification_report = None
            try:
                from processors.glb_simplifier import auto_simplify_scene

                scene_simplified, simplification_report = auto_simplify_scene(scene)
                if simplification_report and simplification_report.get("applied"):
                    scene = scene_simplified
            except Exception:
                pass

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            glb_data = scene.export(file_type="glb")
            Path(output_path).write_bytes(glb_data)

            parts_info = []
            for node_name in scene.graph.nodes_geometry:
                try:
                    _, geom_name = scene.graph[node_name]
                except Exception:
                    geom_name = ""
                parts_info.append({"node_name": str(node_name), "geometry_name": str(geom_name)})

            queue.put(
                {
                    "success": True,
                    "output_path": output_path,
                    "message": "转换成功",
                    "method": "ocp",
                    "log": f"使用OCP兜底转换 {step_path} -> {output_path}",
                    "parts_count": len(parts_info),
                    "parts_info": parts_info,
                    "simplification": simplification_report,
                    "ocp": {
                        "selected_nodes": len(selected),
                        "max_meshes": options.max_meshes,
                        "linear_deflection": options.linear_deflection,
                        "angular_deflection": options.angular_deflection,
                        "collapse_leaf_threshold": options.collapse_leaf_threshold,
                    },
                }
            )
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
    except Exception as e:
        queue.put({"success": False, "error": str(e), "message": "ocp转换失败"})


def convert_step_to_glb_with_ocp(
    step_path: str,
    output_path: str,
    scale_factor: float = 1.0,
    timeout_seconds: Optional[int] = None,
) -> Dict[str, Any]:
    """
    使用 OCP 进行 STEP -> GLB 转换（带硬超时）。
    """
    options = OcpFallbackOptions.from_env()
    if not options.enabled:
        return {"success": False, "error": "OCP fallback disabled", "message": "ocp转换失败"}

    timeout = int(timeout_seconds or options.timeout_seconds)
    result_queue: Queue = Queue()
    process: Process = Process(target=_ocp_worker, args=(step_path, output_path, scale_factor, result_queue))
    process.start()
    process.join(timeout)

    if process.is_alive():
        _terminate_process(process)
        return {
            "success": False,
            "error": f"OCP STEP->GLB 转换超时（{timeout}s）",
            "message": "ocp转换超时",
        }

    if result_queue.empty():
        return {"success": False, "error": "OCP 转换进程未返回结果", "message": "ocp转换失败"}

    return result_queue.get()
