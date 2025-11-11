#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
使用trimesh提取GLB文件的完整信息
"""

import trimesh
from pathlib import Path
import sys
import json

# 设置输出编码为UTF-8
sys.stdout.reconfigure(encoding='utf-8')

def extract_full_info_from_glb(glb_file_path):
    """从GLB文件中提取完整信息"""
    
    # 加载GLB文件
    scene = trimesh.load(str(glb_file_path))
    
    print(f"# 组件2 GLB文件完整信息\n")
    print(f"**文件路径**: `{glb_file_path}`\n")
    print(f"**文件类型**: {type(scene)}\n")
    
    # 检查是Scene还是单个Mesh
    if isinstance(scene, trimesh.Scene):
        print(f"## Scene信息\n")
        print(f"**几何体数量**: {len(scene.geometry)}\n")
        
        print(f"## 场景图 (Scene Graph)\n")
        print(f"**节点总数**: {len(scene.graph.nodes)}\n")
        print(f"**节点列表**:")
        for node in scene.graph.nodes:
            print(f"- `{node}`")
        
        print(f"\n## 几何体详细信息\n")
        
        for i, (name, geom) in enumerate(scene.geometry.items(), 1):
            print(f"### {i}. 几何体: `{name}`\n")
            print(f"- **类型**: {type(geom).__name__}")
            print(f"- **顶点数**: {len(geom.vertices) if hasattr(geom, 'vertices') else 'N/A'}")
            print(f"- **面数**: {len(geom.faces) if hasattr(geom, 'faces') else 'N/A'}")
            
            # 检查是否有metadata
            if hasattr(geom, 'metadata'):
                print(f"- **Metadata**: {geom.metadata}")
            
            # 检查visual信息
            if hasattr(geom, 'visual'):
                print(f"- **Visual**: {type(geom.visual).__name__}")
                if hasattr(geom.visual, 'material'):
                    print(f"  - Material: {geom.visual.material}")
            
            print()
        
        # 提取场景图的变换信息
        print(f"## 场景图变换信息\n")
        
        for node in scene.graph.nodes:
            # 获取该节点的几何体
            geom_name = scene.graph.get(node)
            if geom_name:
                print(f"### 节点: `{node}`")
                print(f"- **关联几何体**: `{geom_name}`")
                
                # 获取变换矩阵
                transform, geom_key = scene.graph.get(node)
                if transform is not None:
                    print(f"- **变换矩阵**: 存在")
                print()
        
        # 检查是否有额外的属性
        print(f"## Scene额外属性\n")
        print(f"- **camera**: {scene.camera if hasattr(scene, 'camera') else 'None'}")
        print(f"- **lights**: {len(scene.lights) if hasattr(scene, 'lights') else 0}")
        
        # 尝试访问原始GLTF数据
        if hasattr(scene, 'metadata'):
            print(f"\n## Scene Metadata\n")
            print(f"```json")
            print(json.dumps(scene.metadata, indent=2, ensure_ascii=False))
            print(f"```")
        
    else:
        print(f"## 单个Mesh信息\n")
        print(f"- **顶点数**: {len(scene.vertices)}")
        print(f"- **面数**: {len(scene.faces)}")
        if hasattr(scene, 'metadata'):
            print(f"- **Metadata**: {scene.metadata}")

if __name__ == "__main__":
    # 组件2的GLB文件
    glb_file = Path('output/dfb95cdb-923e-49c9-910d-a716de3bf8be/glb_files/component_01_09_2550.glb')
    
    if not glb_file.exists():
        print(f"错误: 文件不存在 {glb_file}")
        sys.exit(1)
    
    try:
        extract_full_info_from_glb(glb_file)
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

