#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试组件2步骤15的BOM映射问题
"""

import json
import os
import sys

def find_latest_task():
    """找到最新的任务目录"""
    output_dir = "output"
    if not os.path.exists(output_dir):
        print("❌ output目录不存在")
        return None
    
    # 获取所有任务目录，按修改时间排序
    task_dirs = []
    for name in os.listdir(output_dir):
        path = os.path.join(output_dir, name)
        if os.path.isdir(path):
            # 检查是否有assembly_manual.json
            manual_path = os.path.join(path, "assembly_manual.json")
            if os.path.exists(manual_path):
                mtime = os.path.getmtime(manual_path)
                task_dirs.append((name, mtime))
    
    if not task_dirs:
        print("❌ 没有找到任何任务")
        return None
    
    # 按时间排序，返回最新的
    task_dirs.sort(key=lambda x: x[1], reverse=True)
    return task_dirs[0][0]

def debug_component2_step15(task_id):
    """调试组件2步骤15"""
    print(f"\n{'='*80}")
    print(f"🔍 调试任务: {task_id}")
    print(f"{'='*80}\n")
    
    # 1. 读取assembly_manual.json
    manual_path = f"output/{task_id}/assembly_manual.json"
    if not os.path.exists(manual_path):
        print(f"❌ 文件不存在: {manual_path}")
        return
    
    with open(manual_path, 'r', encoding='utf-8') as f:
        manual = json.load(f)
    
    # 2. 找到组件2
    component_assembly = manual.get('component_assembly', [])
    if len(component_assembly) < 2:
        print(f"❌ 组件数量不足，只有{len(component_assembly)}个组件")
        return
    
    comp2 = component_assembly[1]  # 第二个组件
    comp2_code = comp2.get('component_code')
    comp2_name = comp2.get('component_name')
    
    print(f"📦 组件2: {comp2_code} - {comp2_name}")
    print()
    
    # 3. 读取BOM数据
    bom_path = f"output/{task_id}/step2_bom_data.json"
    with open(bom_path, 'r', encoding='utf-8') as f:
        bom_data = json.load(f)
    
    # 找到组件2的BOM
    comp2_bom = [item for item in bom_data if item.get('parent_code') == comp2_code]
    
    print(f"📋 组件2的BOM表 ({len(comp2_bom)}个零件):")
    print()
    print(f"{'序号':<6} {'BOM代号':<20} {'名称':<30}")
    print("-" * 80)
    for item in comp2_bom:
        seq = item.get('seq', '')
        code = item.get('code', '')
        name = item.get('name', '')
        print(f"{seq:<6} {code:<20} {name:<30}")
    print()
    
    # 4. 读取匹配结果
    matching_path = f"output/{task_id}/step4_matching_result.json"
    with open(matching_path, 'r', encoding='utf-8') as f:
        matching = json.load(f)
    
    # 找到组件2的bom_to_mesh映射
    comp2_mapping = None
    for comp_map in matching.get('component_level_mappings', []):
        if comp_map.get('component_code') == comp2_code:
            comp2_mapping = comp_map.get('bom_to_mesh', {})
            break
    
    if not comp2_mapping:
        print("❌ 没有找到组件2的bom_to_mesh映射")
        return
    
    print(f"🔗 组件2的BOM-Mesh映射 ({len(comp2_mapping)}个):")
    print()
    
    # 创建一个反向映射：mesh_id -> bom_code
    mesh_to_bom = {}
    for bom_code, mesh_ids in comp2_mapping.items():
        for mesh_id in mesh_ids:
            mesh_to_bom[mesh_id] = bom_code
    
    # 5. 找到步骤15
    steps = comp2.get('steps', [])
    step15 = None
    for step in steps:
        if step.get('step_number') == 15:
            step15 = step
            break
    
    if not step15:
        print(f"❌ 没有找到步骤15，总共有{len(steps)}个步骤")
        return
    
    print(f"📝 步骤15: {step15.get('title')}")
    print()
    
    parts_used = step15.get('parts_used', [])
    print(f"🔧 步骤15使用的零件 ({len(parts_used)}个):")
    print()
    
    for i, part in enumerate(parts_used, 1):
        bom_code = part.get('bom_code', '')
        bom_name = part.get('bom_name', '')
        mesh_ids = part.get('mesh_id', [])
        
        print(f"{i}. BOM代号: {bom_code}")
        print(f"   名称: {bom_name}")
        print(f"   mesh_id: {mesh_ids}")
        
        # 查找这个BOM在BOM表中的序号
        bom_item = next((item for item in comp2_bom if item.get('code') == bom_code), None)
        if bom_item:
            print(f"   ✅ BOM表序号: {bom_item.get('seq')}")
        else:
            print(f"   ❌ 在BOM表中找不到")
        print()
    
    # 6. 分析问题
    print(f"\n{'='*80}")
    print(f"🔍 问题分析")
    print(f"{'='*80}\n")
    
    print("根据你的描述：")
    print("- 步骤15文字说的是'组件9和10'")
    print("- 但3D高亮的是'组件3和1'")
    print()
    
    print("可能的原因：")
    print("1. AI生成步骤时，看图纸上的序号是9和10")
    print("2. 但AI填写的bom_code字段不是序号9和10对应的BOM代号")
    print("3. 而是填写了序号3和1对应的BOM代号")
    print()
    
    print("让我们验证一下：")
    print()
    
    # 找到序号9和10的BOM
    seq9 = next((item for item in comp2_bom if item.get('seq') == '9'), None)
    seq10 = next((item for item in comp2_bom if item.get('seq') == '10'), None)
    
    if seq9:
        print(f"序号9: {seq9.get('code')} - {seq9.get('name')}")
        if seq9.get('code') in comp2_mapping:
            print(f"  → mesh: {comp2_mapping[seq9.get('code')]}")
    
    if seq10:
        print(f"序号10: {seq10.get('code')} - {seq10.get('name')}")
        if seq10.get('code') in comp2_mapping:
            print(f"  → mesh: {comp2_mapping[seq10.get('code')]}")
    
    print()
    
    # 找到序号3和1的BOM
    seq3 = next((item for item in comp2_bom if item.get('seq') == '3'), None)
    seq1 = next((item for item in comp2_bom if item.get('seq') == '1'), None)
    
    if seq3:
        print(f"序号3: {seq3.get('code')} - {seq3.get('name')}")
        if seq3.get('code') in comp2_mapping:
            print(f"  → mesh: {comp2_mapping[seq3.get('code')]}")
    
    if seq1:
        print(f"序号1: {seq1.get('code')} - {seq1.get('name')}")
        if seq1.get('code') in comp2_mapping:
            print(f"  → mesh: {comp2_mapping[seq1.get('code')]}")
    
    print()
    print("✅ 如果步骤15中的bom_code是序号3和1的代号，那就证实了问题所在！")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        task_id = sys.argv[1]
    else:
        task_id = find_latest_task()
        if not task_id:
            sys.exit(1)
        print(f"📌 使用最新任务: {task_id}\n")
    
    debug_component2_step15(task_id)

