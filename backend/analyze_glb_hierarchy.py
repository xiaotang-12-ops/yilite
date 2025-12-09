#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分析GLB/STEP文件的层级结构
用于理解为什么装配体信息丢失
"""

import trimesh
import json
from pathlib import Path
from collections import defaultdict

def analyze_glb_hierarchy(glb_path):
    """分析GLB文件的场景图层级结构"""
    print(f"=== 分析文件: {glb_path} ===\n")
    
    scene = trimesh.load(glb_path, force='scene')
    
    # 1. 基本统计
    print(f"总节点数: {len(scene.graph.nodes)}")
    print(f"有geometry的节点数: {len(list(scene.graph.nodes_geometry))}")
    print(f"geometry数量: {len(scene.geometry)}")
    
    # 2. 构建父子关系
    children_of = defaultdict(list)
    parent_of = {}
    
    for node in scene.graph.nodes:
        # 获取节点的父节点
        try:
            # scene.graph.transforms存储边的信息
            for edge, data in scene.graph.transforms.edge_data.items():
                parent, child = edge
                if parent != child:
                    children_of[parent].append(child)
                    parent_of[child] = parent
        except:
            pass
    
    # 3. 找出所有无geometry的节点（装配体）
    print("\n=== 无geometry的节点（可能是装配体）===")
    assembly_nodes = []
    for node in scene.graph.nodes:
        try:
            transform, geom_name = scene.graph[node]
            if geom_name is None:
                assembly_nodes.append(node)
                print(f"  {node}")
        except:
            pass
    
    # 4. 分析E-CW3T-VIO35挖机压实轮VIO35连接器的直接子节点
    product_node = "E-CW3T-VIO35挖机压实轮VIO35连接器"
    if product_node in children_of:
        print(f"\n=== {product_node} 的直接子节点 ===")
        for child in children_of[product_node]:
            try:
                transform, geom_name = scene.graph[child]
                if geom_name:
                    print(f"  {child} -> {geom_name}")
                else:
                    print(f"  {child} (装配体，无geometry)")
            except:
                print(f"  {child} (解析失败)")
    
    # 5. 分析每个geometry的名称
    print("\n=== 所有geometry名称 ===")
    for name in list(scene.geometry.keys())[:20]:
        print(f"  {name}")
    if len(scene.geometry) > 20:
        print(f"  ... 共 {len(scene.geometry)} 个")
    
    # 6. 输出完整的父子关系树到JSON
    result = {
        "total_nodes": len(scene.graph.nodes),
        "nodes_with_geometry": len(list(scene.graph.nodes_geometry)),
        "assembly_nodes": assembly_nodes,
        "children_of": {k: list(v) for k, v in children_of.items()},
        "geometry_names": list(scene.geometry.keys())
    }
    
    output_path = Path(glb_path).with_suffix('.hierarchy.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n层级结构已保存到: {output_path}")

if __name__ == "__main__":
    # 分析产品总图
    glb_path = "output/03.05.20.0005E-CW3T-VIO35挖机压实轮VIO35连接器/glb_files/product_total.glb"
    analyze_glb_hierarchy(glb_path)

