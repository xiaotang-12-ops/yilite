#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
解析GLB几何体名称，提取BOM代号
"""

import trimesh
from pathlib import Path
import sys
import re

# 设置输出编码为UTF-8
sys.stdout.reconfigure(encoding='utf-8')

def parse_geometry_names(glb_file_path):
    """解析GLB几何体名称"""
    
    # 加载GLB文件
    scene = trimesh.load(str(glb_file_path))
    
    print(f"# 组件2 GLB几何体名称解析\n")
    print(f"**文件路径**: `{glb_file_path}`\n")
    
    if isinstance(scene, trimesh.Scene):
        print(f"## 几何体名称列表（{len(scene.geometry)}个）\n")
        
        # 提取所有几何体名称
        geometry_names = list(scene.geometry.keys())
        
        # 尝试从名称中提取BOM代号
        # BOM代号格式: XX.XX.XX.XXXXX (如 01.01.01.11513)
        bom_pattern = r'\d{2}\.\d{2}\.\d{2}\.\d{4,5}'
        
        parsed_data = []
        
        for i, name in enumerate(geometry_names, 1):
            print(f"### {i}. `{name}`\n")
            
            # 尝试提取BOM代号
            bom_match = re.search(bom_pattern, name)
            if bom_match:
                bom_code = bom_match.group(0)
                print(f"- **BOM代号**: `{bom_code}`")
                
                # 尝试提取零件名称（BOM代号后面的部分）
                # 格式通常是: T-SPV250-Z602-02-01-Q355B方形板-机加
                # 或者: ZT-φ5-φ7-35-Q235轴套
                parts = name.split('-')
                if len(parts) >= 3:
                    # 最后一部分通常是材料+零件名
                    last_part = parts[-1]
                    print(f"- **零件描述**: `{last_part}`")
                
                parsed_data.append({
                    'geometry_name': name,
                    'bom_code': bom_code,
                    'description': last_part if len(parts) >= 3 else ''
                })
            else:
                print(f"- **BOM代号**: ❌ 未找到")
                parsed_data.append({
                    'geometry_name': name,
                    'bom_code': None,
                    'description': ''
                })
            
            print()
        
        # 统计
        print(f"## 统计信息\n")
        
        bom_found = [d for d in parsed_data if d['bom_code']]
        print(f"- **几何体总数**: {len(geometry_names)}")
        print(f"- **包含BOM代号的几何体**: {len(bom_found)}")
        print(f"- **覆盖率**: {len(bom_found)}/{len(geometry_names)} = {len(bom_found)/len(geometry_names)*100:.1f}%")
        
        # 提取所有唯一的BOM代号
        unique_bom_codes = set(d['bom_code'] for d in parsed_data if d['bom_code'])
        print(f"\n## 唯一BOM代号列表（{len(unique_bom_codes)}个）\n")
        
        for bom_code in sorted(unique_bom_codes):
            # 找到所有使用这个BOM代号的几何体
            geoms = [d['geometry_name'] for d in parsed_data if d['bom_code'] == bom_code]
            print(f"- `{bom_code}` → {len(geoms)}个几何体")
            for geom in geoms:
                print(f"  - `{geom}`")
        
        # 与BOM表对比
        print(f"\n## 与BOM表对比\n")
        
        bom_table = [
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
        
        print(f"**BOM表零件**: {len(bom_table)}个")
        print(f"**GLB中的BOM代号**: {len(unique_bom_codes)}个\n")
        
        for bom_code in bom_table:
            if bom_code in unique_bom_codes:
                geoms = [d['geometry_name'] for d in parsed_data if d['bom_code'] == bom_code]
                print(f"- `{bom_code}` → ✅ 找到 ({len(geoms)}个几何体)")
            else:
                print(f"- `{bom_code}` → ❌ 未找到")

if __name__ == "__main__":
    # 组件2的GLB文件
    glb_file = Path('output/dfb95cdb-923e-49c9-910d-a716de3bf8be/glb_files/component_01_09_2550.glb')
    
    if not glb_file.exists():
        print(f"错误: 文件不存在 {glb_file}")
        sys.exit(1)
    
    try:
        parse_geometry_names(glb_file)
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

