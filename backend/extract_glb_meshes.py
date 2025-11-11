#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
提取GLB文件中的mesh名称
"""

import json
import struct
from pathlib import Path
import sys

# 设置输出编码为UTF-8
sys.stdout.reconfigure(encoding='utf-8')

def extract_meshes_from_glb(glb_file_path):
    """从GLB文件中提取mesh名称"""
    with open(glb_file_path, 'rb') as f:
        # 读取GLB文件头
        magic = f.read(4)
        if magic != b'glTF':
            print(f"错误: 不是有效的GLB文件")
            return []
        
        version = struct.unpack('<I', f.read(4))[0]
        length = struct.unpack('<I', f.read(4))[0]
        
        # 读取JSON chunk
        chunk_length = struct.unpack('<I', f.read(4))[0]
        chunk_type = struct.unpack('<I', f.read(4))[0]
        
        if chunk_type != 0x4E4F534A:  # JSON
            print(f"错误: 第一个chunk不是JSON")
            return []
        
        json_data = f.read(chunk_length).decode('utf-8')
        gltf = json.loads(json_data)
        
        # 提取mesh名称
        meshes = []
        if 'nodes' in gltf:
            for node in gltf['nodes']:
                if 'name' in node:
                    meshes.append(node['name'])
        
        return meshes

if __name__ == "__main__":
    # 组件2的GLB文件
    glb_file = Path('output/dfb95cdb-923e-49c9-910d-a716de3bf8be/glb_files/component_01_09_2550.glb')
    
    if not glb_file.exists():
        print(f"错误: 文件不存在 {glb_file}")
        sys.exit(1)
    
    meshes = extract_meshes_from_glb(glb_file)
    
    print(f"# 组件2 GLB文件中的Mesh列表\n")
    print(f"**文件路径**: `{glb_file}`")
    print(f"**Mesh总数**: {len(meshes)}\n")
    print(f"## Mesh名称列表\n")
    
    for i, mesh in enumerate(meshes, 1):
        print(f"{i}. `{mesh}`")
    
    print(f"\n---\n")
    print(f"## 与BOM代号的对比\n")
    print(f"**BOM零件代号**:")
    bom_codes = [
        "01.01.01.11513",
        "01.01.01.11511",
        "01.01.01.11512",
        "01.01.01.11514",
        "01.01.01.11515",
        "01.01.01.11516",
        "01.01.04.0592",
        "01.02.02.0490",
        "01.01.02.1221",
        "01.01.02.0337"
    ]
    
    for code in bom_codes:
        # 检查是否有mesh名称包含这个代号
        matched = [m for m in meshes if code in m or code.replace('.', '') in m]
        if matched:
            print(f"- `{code}` → ✅ 匹配到: {matched}")
        else:
            print(f"- `{code}` → ❌ 未匹配")

