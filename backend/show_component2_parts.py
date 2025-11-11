#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
显示组件2的零件列表
"""

import json
from pathlib import Path
import sys

# 设置输出编码为UTF-8
sys.stdout.reconfigure(encoding='utf-8')

# 读取assembly_manual.json
manual_file = Path('output/dfb95cdb-923e-49c9-910d-a716de3bf8be/assembly_manual.json')

with open(manual_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 获取组件2的信息
comp_assembly = data.get('component_assembly', [])

if len(comp_assembly) >= 2:
    comp2 = comp_assembly[1]  # 第2个组件（索引1）
    
    print('# 组件2零件列表')
    print()
    print(f'**组件名称**: {comp2.get("component_name")}')
    print(f'**组件代号**: {comp2.get("component_code")}')
    print(f'**GLB文件**: {comp2.get("glb_file")}')
    print()
    
    # 从装配步骤中提取零件列表
    steps = comp2.get('steps', [])
    comp2_parts_dict = {}

    for step in steps:
        parts_used = step.get('parts_used', [])
        for part in parts_used:
            bom_code = part.get('bom_code')
            if bom_code not in comp2_parts_dict:
                comp2_parts_dict[bom_code] = part

    comp2_parts = list(comp2_parts_dict.values())
    
    print(f'## BOM表中的零件（{len(comp2_parts)}个）')
    print()
    for i, part in enumerate(comp2_parts, 1):
        print(f'{i}. **{part.get("bom_code")}** - {part.get("bom_name")} (数量: {part.get("quantity")})')
    
    # 获取bom_to_mesh映射
    bom_to_mesh = data.get('3d_resources', {}).get('bom_to_mesh', {})
    
    print()
    print(f'## BOM到Mesh的映射')
    print()
    
    mapped_count = 0
    for part in comp2_parts:
        bom_code = part.get('bom_code')
        if bom_code in bom_to_mesh:
            meshes = bom_to_mesh[bom_code]
            print(f'- **{bom_code}**: `{meshes}`')
            mapped_count += 1
        else:
            print(f'- **{bom_code}**: ❌ 未映射')
    
    print()
    if len(comp2_parts) > 0:
        print(f'**映射覆盖率**: {mapped_count}/{len(comp2_parts)} = {mapped_count/len(comp2_parts)*100:.1f}%')
    else:
        print(f'**映射覆盖率**: 0/0 = N/A')
    print()
    print(f'## 装配步骤（{len(steps)}步）')
    print()
    
    # 统计步骤中使用的零件
    used_bom_codes = set()
    
    for step in steps:
        step_num = step.get('step_number')
        title = step.get('title', '')
        parts_used = step.get('parts_used', [])
        
        print(f'### 步骤{step_num}: {title}')
        print()
        if parts_used:
            for part in parts_used:
                bom_code = part.get('bom_code')
                used_bom_codes.add(bom_code)
                print(f'- `{bom_code}` - {part.get("bom_name")} (数量: {part.get("quantity")})')
        else:
            print('- （无零件）')
        print()
    
    # 检查BOM覆盖率
    print('## BOM覆盖率检查')
    print()
    
    all_bom_codes = set(p.get('bom_code') for p in comp2_parts)
    missing_codes = all_bom_codes - used_bom_codes
    
    print(f'**BOM表零件总数**: {len(all_bom_codes)}')
    print(f'**步骤中使用的零件数**: {len(used_bom_codes)}')
    if len(all_bom_codes) > 0:
        print(f'**覆盖率**: {len(used_bom_codes)}/{len(all_bom_codes)} = {len(used_bom_codes)/len(all_bom_codes)*100:.1f}%')
    else:
        print(f'**覆盖率**: 0/0 = N/A')
    print()
    
    if missing_codes:
        print('### ❌ 遗漏的零件:')
        print()
        for code in sorted(missing_codes):
            # 找到零件名称
            part_name = next((p.get('bom_name') for p in comp2_parts if p.get('bom_code') == code), '未知')
            print(f'- `{code}` - {part_name}')
    else:
        print('### ✅ 所有BOM零件都已包含在装配步骤中')
    
else:
    print('错误: 找不到组件2')

