# -*- coding: utf-8 -*-
"""
STEP 装配层级解析器
通过正则直接解析 STEP 文本，提取 PRODUCT / PRODUCT_DEFINITION /
PRODUCT_DEFINITION_FORMATION(_WITH_SPECIFIED_SOURCE) / NEXT_ASSEMBLY_USAGE_OCCURRENCE。
"""

from __future__ import annotations

import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any


# 正则模式：保持与验证脚本一致
PRODUCT_PATTERN = r"#(\d+)\s*=\s*PRODUCT\s*\(\s*'([^']*)'[^)]*\)"
PRODUCT_DEF_PATTERN = r"#(\d+)\s*=\s*PRODUCT_DEFINITION\s*\(\s*'[^']*'\s*,\s*'[^']*'\s*,\s*#(\d+)"
PRODUCT_DF_PATTERN = r"#(\d+)\s*=\s*PRODUCT_DEFINITION_FORMATION[_A-Z]*\s*\(\s*'[^']*'\s*,\s*'[^']*'\s*,\s*#(\d+)"
NAUO_PATTERN = r"#(\d+)\s*=\s*NEXT_ASSEMBLY_USAGE_OCCURRENCE\s*\(\s*'([^']*)'\s*,\s*'[^']*'\s*,\s*'[^']*'\s*,\s*#(\d+)\s*,\s*#(\d+)"


def parse_step_hierarchy(step_file_path: str) -> Dict[str, Any]:
    """
    解析 STEP 文件装配层级。

    Args:
        step_file_path: STEP 文件路径

    Returns:
        {
            "hierarchy": {parent_name: [child_names]},
            "stats": {...}
        }
    """
    path = Path(step_file_path)
    if not path.exists():
        raise FileNotFoundError(f"STEP 文件不存在: {step_file_path}")

    # 尝试多种编码，优先使用 GBK（中国大陆 STEP 文件常用编码）
    content = None
    for encoding in ['gbk', 'gb18030', 'gb2312', 'utf-8']:
        try:
            content = path.read_text(encoding=encoding, errors='strict')
            break
        except (UnicodeDecodeError, LookupError):
            continue

    # 如果所有编码都失败，使用 GBK + replace 模式
    if content is None:
        content = path.read_text(encoding='gbk', errors='replace')

    products: Dict[str, str] = {}
    for match in re.finditer(PRODUCT_PATTERN, content):
        prod_id, prod_name = match.group(1), match.group(2)
        products[prod_id] = prod_name

    prod_defs: Dict[str, str] = {}
    for match in re.finditer(PRODUCT_DEF_PATTERN, content):
        pd_id, pdf_id = match.group(1), match.group(2)
        prod_defs[pd_id] = pdf_id

    pdfs: Dict[str, str] = {}
    for match in re.finditer(PRODUCT_DF_PATTERN, content):
        pdf_id, prod_id = match.group(1), match.group(2)
        pdfs[pdf_id] = prod_id

    pd_to_name: Dict[str, str] = {}
    for pd_id, pdf_id in prod_defs.items():
        product_id = pdfs.get(pdf_id)
        if product_id and product_id in products:
            pd_to_name[pd_id] = products[product_id]

    nauos: List[Dict[str, str]] = []
    for match in re.finditer(NAUO_PATTERN, content):
        nauo_id, nauo_name, parent_pd, child_pd = (
            match.group(1),
            match.group(2),
            match.group(3),
            match.group(4),
        )
        nauos.append(
            {
                "nauo_id": nauo_id,
                "nauo_name": nauo_name,
                "parent_pd": parent_pd,
                "child_pd": child_pd,
                "parent_name": pd_to_name.get(parent_pd, f"Unknown#{parent_pd}"),
                "child_name": pd_to_name.get(child_pd, f"Unknown#{child_pd}"),
            }
        )

    hierarchy: Dict[str, List[str]] = defaultdict(list)
    for nauo in nauos:
        hierarchy[nauo["parent_name"]].append(nauo["child_name"])

    # 只返回层级结构和统计信息，去掉冗余的原始数据
    return {
        "hierarchy": dict(hierarchy),
        # ✅ 保留 NAUO 边信息（用于后续按父级上下文构建 node_name 映射，避免同名件串件/丢重复件）
        # 说明：nauo_name 是 STEP 中 NEXT_ASSEMBLY_USAGE_OCCURRENCE 的名字字段，通常与GLB节点名同源；
        #      后续可通过 glb parts_info 将其展开到真实 node_name（含 _1/_2 后缀）。
        "nauo_edges": nauos,
        "stats": {
            "total_products": len(products),
            "total_nauos": len(nauos),
            "total_assemblies": len(hierarchy),
        },
    }


def collect_leaf_parts(hierarchy: Dict[str, List[str]], root: str) -> List[str]:
    """
    从给定装配体（root）收集所有叶子零件名称。
    """
    leaves: List[str] = []
    visited = set()

    def _dfs(node: str) -> None:
        if node in visited:
            return
        visited.add(node)
        children = hierarchy.get(node, [])
        if not children:
            leaves.append(node)
            return
        for child in children:
            if child in hierarchy:
                _dfs(child)
            else:
                leaves.append(child)

    _dfs(root)
    return leaves
