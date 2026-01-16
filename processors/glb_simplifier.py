# -*- coding: utf-8 -*-
"""
GLB/Scene 简化器：在不改变用户源文件的前提下，将“特征级”高重复零件合并为更粗粒度的组件 mesh，
以降低 Web 端渲染与交互成本。
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import numpy as np


_CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")


def _decode_name(name: Any) -> str:
    if not name:
        return ""

    text = str(name)
    if _CHINESE_RE.search(text):
        return text

    if text.isascii():
        return text

    for raw_enc in ("latin1", "cp1252"):
        try:
            raw_bytes = text.encode(raw_enc, errors="ignore")
        except Exception:
            continue
        for target in ("gb18030", "gbk", "utf-8"):
            try:
                decoded = raw_bytes.decode(target, errors="ignore")
            except Exception:
                continue
            if decoded and _CHINESE_RE.search(decoded):
                return decoded

    return text


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


@dataclass(frozen=True)
class AutoSimplifyOptions:
    enabled: bool = True
    trigger_nodes_geometry: int = 5000
    min_root_descendant_geometry: int = 200
    min_total_collapsed_geometry: int = 2000
    brush_keywords: Tuple[str, ...] = ("毛刷", "刷片", "刷丝", "brush", "bristle")

    @classmethod
    def from_env(cls) -> "AutoSimplifyOptions":
        def _int_env(name: str, default: int) -> int:
            raw = os.getenv(name)
            if not raw:
                return default
            try:
                return int(raw)
            except Exception:
                return default

        def _bool_env(name: str, default: bool) -> bool:
            raw = os.getenv(name)
            if raw is None:
                return default
            return raw.strip().lower() in ("1", "true", "yes", "y", "on")

        return cls(
            enabled=_bool_env("AUTO_SIMPLIFY_GLB", True),
            trigger_nodes_geometry=_int_env("AUTO_SIMPLIFY_TRIGGER_NODES_GEOMETRY", 5000),
            min_root_descendant_geometry=_int_env("AUTO_SIMPLIFY_MIN_ROOT_DESC_GEOM", 200),
            min_total_collapsed_geometry=_int_env("AUTO_SIMPLIFY_MIN_TOTAL_COLLAPSED", 2000),
        )


@dataclass
class SimplificationGroup:
    root_node: str
    root_node_decoded: str
    root_transform_world: np.ndarray
    descendant_geometry_nodes: List[str]

    @property
    def descendant_geometry_count(self) -> int:
        return len(self.descendant_geometry_nodes)


def _iter_descendant_geometry_nodes(scene: Any, root_node: str) -> Iterable[str]:
    forest = scene.graph.transforms
    for node in forest.successors(root_node):
        try:
            _, geom_name = scene.graph[node]
        except Exception:
            continue
        if geom_name:
            yield node


def _pick_simplification_groups(scene: Any, options: AutoSimplifyOptions) -> List[SimplificationGroup]:
    forest = scene.graph.transforms

    candidates: List[Tuple[str, str]] = []
    for node in scene.graph.nodes:
        try:
            _, geom_name = scene.graph[node]
        except Exception:
            continue
        if geom_name is not None:
            continue
        decoded = _decode_name(node)
        if not _contains_any(decoded, options.brush_keywords):
            continue
        if _trailing_int(decoded) is None:
            continue
        candidates.append((str(node), decoded))

    if not candidates:
        return []

    counted: List[Tuple[int, str, str, List[str]]] = []
    for raw_node, decoded in candidates:
        try:
            descendants = list(_iter_descendant_geometry_nodes(scene, raw_node))
        except Exception:
            continue
        if len(descendants) < options.min_root_descendant_geometry:
            continue
        counted.append((len(descendants), raw_node, decoded, descendants))

    if not counted:
        return []

    counted.sort(key=lambda x: x[0], reverse=True)

    selected: List[SimplificationGroup] = []
    blocked: Set[str] = set()
    for _, raw_node, decoded, descendants in counted:
        if raw_node in blocked:
            continue
        try:
            root_transform, _ = scene.graph.get(frame_from="world", frame_to=raw_node)
        except Exception:
            continue
        selected.append(
            SimplificationGroup(
                root_node=raw_node,
                root_node_decoded=decoded,
                root_transform_world=np.asarray(root_transform, dtype=float),
                descendant_geometry_nodes=descendants,
            )
        )
        blocked.add(raw_node)
        try:
            blocked.update(forest.successors(raw_node))
        except Exception:
            pass

    return selected


def _apply_groups_to_scene(scene: Any, groups: List[SimplificationGroup]) -> Tuple[Any, Dict[str, Any]]:
    import trimesh

    if not groups:
        return scene, {"applied": False, "reason": "no_groups"}

    remove_nodes: Set[str] = set()
    for group in groups:
        remove_nodes.update(group.descendant_geometry_nodes)

    new_scene = trimesh.Scene()

    kept_nodes = 0
    kept_geometry = 0

    for node in scene.graph.nodes_geometry:
        node_str = str(node)
        if node_str in remove_nodes:
            continue
        try:
            transform, geom_name = scene.graph.get(frame_from="world", frame_to=node_str)
        except Exception:
            continue
        if not geom_name or geom_name not in scene.geometry:
            continue
        geom = scene.geometry[geom_name]
        new_scene.add_geometry(
            geom,
            node_name=node_str,
            geom_name=str(geom_name),
            transform=np.asarray(transform, dtype=float),
        )
        kept_nodes += 1
        kept_geometry += 1

    merged_nodes = 0
    merged_geometry = 0

    for group in groups:
        root_transform = group.root_transform_world
        try:
            inv_root = np.linalg.inv(root_transform)
        except Exception:
            inv_root = np.linalg.pinv(root_transform)

        meshes: List[trimesh.Trimesh] = []
        for child in group.descendant_geometry_nodes:
            try:
                child_transform, child_geom_name = scene.graph.get(frame_from="world", frame_to=child)
            except Exception:
                continue
            if not child_geom_name or child_geom_name not in scene.geometry:
                continue

            mesh = scene.geometry[child_geom_name]
            if not isinstance(mesh, trimesh.Trimesh):
                continue

            local_transform = inv_root @ np.asarray(child_transform, dtype=float)
            mesh_local = mesh.copy()
            mesh_local.apply_transform(local_transform)
            meshes.append(mesh_local)

        if not meshes:
            continue

        merged = trimesh.util.concatenate(meshes)
        node_name = group.root_node_decoded
        geom_name = f"{node_name}__merged"
        new_scene.add_geometry(
            merged,
            node_name=node_name,
            geom_name=geom_name,
            transform=root_transform,
        )
        merged_nodes += 1
        merged_geometry += 1

    report = {
        "applied": True,
        "kept_nodes_geometry": kept_nodes,
        "kept_geometry": kept_geometry,
        "merged_nodes_geometry": merged_nodes,
        "merged_geometry": merged_geometry,
        "removed_nodes_geometry": len(remove_nodes),
        "groups": [
            {
                "root_node": g.root_node,
                "root_node_decoded": g.root_node_decoded,
                "descendant_geometry_count": g.descendant_geometry_count,
            }
            for g in groups
        ],
    }
    return new_scene, report


def auto_simplify_scene(scene: Any, options: Optional[AutoSimplifyOptions] = None) -> Tuple[Any, Dict[str, Any]]:
    """
    根据阈值自动简化 Scene；如果不满足触发条件，返回原 scene。
    """
    import trimesh

    opts = options or AutoSimplifyOptions.from_env()
    if not opts.enabled:
        return scene, {"applied": False, "reason": "disabled"}

    if not isinstance(scene, trimesh.Scene):
        return scene, {"applied": False, "reason": "not_scene"}

    nodes_geometry_before = len(list(scene.graph.nodes_geometry))
    if nodes_geometry_before < opts.trigger_nodes_geometry:
        return scene, {
            "applied": False,
            "reason": "below_threshold",
            "nodes_geometry": nodes_geometry_before,
            "trigger_nodes_geometry": opts.trigger_nodes_geometry,
        }

    groups = _pick_simplification_groups(scene, opts)
    if not groups:
        return scene, {"applied": False, "reason": "no_candidate_groups"}

    total_collapsed = sum(g.descendant_geometry_count for g in groups)
    if total_collapsed < opts.min_total_collapsed_geometry:
        return scene, {
            "applied": False,
            "reason": "insufficient_collapsed",
            "total_collapsed": total_collapsed,
            "min_total_collapsed_geometry": opts.min_total_collapsed_geometry,
        }

    simplified, report = _apply_groups_to_scene(scene, groups)
    report.update(
        {
            "nodes_geometry_before": nodes_geometry_before,
            "nodes_geometry_after": len(list(simplified.graph.nodes_geometry)),
            "groups_count": len(groups),
            "total_collapsed_geometry": total_collapsed,
        }
    )
    return simplified, report

