# -*- coding: utf-8 -*-
"""
重新运行BOM-3D匹配（使用已有的BOM和GLB数据）
"""

import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from core.hierarchical_bom_matcher_v2 import HierarchicalBOMMatcher

# 使用已有的任务数据
task_id = "fa592fac-0516-4d18-bf85-e18a12ef72e2"
output_dir = Path("output") / task_id

print("="*80)
print("  🔄 重新运行BOM-3D匹配")
print("="*80)

# 1. 加载文件层级
hierarchy_file = output_dir / "step1_file_hierarchy.json"
with open(hierarchy_file, 'r', encoding='utf-8') as f:
    file_hierarchy = json.load(f)

# 2. 加载BOM数据
bom_file = output_dir / "step2_bom_data.json"
with open(bom_file, 'r', encoding='utf-8') as f:
    all_bom_data = json.load(f)

print(f"\n📋 加载数据:")
print(f"   - BOM数据: {len(all_bom_data)} 条")
print(f"   - 组件数: {len(file_hierarchy.get('components', []))}")

# 3. 准备匹配数据
component_bom_list = []
component_glb_list = []

# 组件级数据
for i, comp in enumerate(file_hierarchy.get('components', []), 1):
    comp_code = comp.get('code', f'component_{i}')
    
    # 获取该组件的BOM
    comp_bom = [item for item in all_bom_data if item.get('source_pdf') == f'component_{i}']
    if comp_bom:
        component_bom_list.append({
            'component_code': comp_code,
            'bom_data': comp_bom
        })
    
    # 获取该组件的GLB
    glb_path = output_dir / "glb_files" / f"component_{i}.glb"
    if glb_path.exists():
        component_glb_list.append({
            'component_code': comp_code,
            'glb_file': str(glb_path)
        })

# 产品级数据
product_bom = [item for item in all_bom_data if item.get('source_pdf') == 'product']
product_glb = output_dir / "glb_files" / "product_total.glb"

print(f"\n📊 匹配数据:")
print(f"   - 组件BOM组: {len(component_bom_list)}")
print(f"   - 组件GLB: {len(component_glb_list)}")
print(f"   - 产品BOM: {len(product_bom)} 条")
print(f"   - 产品GLB: {'存在' if product_glb.exists() else '不存在'}")

# 4. 执行匹配
print(f"\n🎯 开始BOM-3D匹配...")
matcher = HierarchicalBOMMatcher()

matching_result = matcher.match(
    component_bom_list=component_bom_list,
    component_glb_list=component_glb_list,
    product_bom=product_bom,
    product_glb=str(product_glb) if product_glb.exists() else None
)

# 5. 保存结果
output_file = output_dir / "step4_matching_result_NEW.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(matching_result, f, ensure_ascii=False, indent=2)

print(f"\n✅ 匹配结果已保存: {output_file}")

# 6. 显示结果
product_mapping = matching_result.get('product_level_mapping', {})
print(f"\n" + "="*80)
print(f"  📊 匹配结果")
print(f"="*80)
print(f"\n产品级匹配:")
print(f"   - 总BOM数: {product_mapping.get('total_bom_count', 0)}")
print(f"   - 匹配成功: {product_mapping.get('bom_matched_count', 0)}")
print(f"   - 匹配率: {product_mapping.get('matching_rate', 0)*100:.1f}%")
print(f"   - 代号匹配: {product_mapping.get('code_matched', 0)}")
print(f"   - AI匹配: {product_mapping.get('ai_matched', 0)}")

bom_to_mesh = product_mapping.get('bom_to_mesh', {})
print(f"\n   - BOM-Mesh映射: {len(bom_to_mesh)} 个BOM代号")
print(f"\n   前10个映射:")
for i, (bom_code, meshes) in enumerate(list(bom_to_mesh.items())[:10], 1):
    print(f"      {i}. {bom_code} → {len(meshes)} 个mesh")

print(f"\n" + "="*80)
print(f"  ✅ 完成")
print(f"="*80)

