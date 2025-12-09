#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分析STEP文件中的NAUO定义和装配层级
NAUO = NEXT_ASSEMBLY_USAGE_OCCURRENCE
"""

import re
from pathlib import Path

def analyze_step_file(step_path):
    """分析STEP文件中的装配层级"""
    print(f"=== 分析 {step_path.name} ===\n")
    
    content = step_path.read_bytes()
    
    # 尝试不同编码
    text = None
    for enc in ['utf-8', 'gb18030', 'gbk', 'latin1']:
        try:
            text = content.decode(enc)
            print(f"编码: {enc}")
            break
        except:
            continue
    
    if not text:
        print("无法解码文件")
        return
    
    # 1. 查找PRODUCT定义 - 这是零件/组件的名称定义
    # 格式: #ID = PRODUCT('名称', ...)
    product_pattern = r"#(\d+)\s*=\s*PRODUCT\s*\(\s*'([^']*)'"
    products = re.findall(product_pattern, text)
    
    product_by_id = {id: name for id, name in products}
    print(f"\n=== PRODUCT定义 ({len(products)}个) ===")
    for id, name in products[:30]:
        print(f"  #{id} = {name}")
    if len(products) > 30:
        print(f"  ... 共 {len(products)} 个")
    
    # 2. 查找PRODUCT_DEFINITION - 关联到PRODUCT
    # 格式: #ID = PRODUCT_DEFINITION(..., #PRODUCT_ID, ...)
    pd_pattern = r"#(\d+)\s*=\s*PRODUCT_DEFINITION\s*\([^)]*#(\d+)"
    pds = re.findall(pd_pattern, text)
    
    # 3. 查找NEXT_ASSEMBLY_USAGE_OCCURRENCE (NAUO) - 定义装配关系
    # 格式: #ID = NEXT_ASSEMBLY_USAGE_OCCURRENCE('名称', '描述', #父PD, #子PD, ...)
    nauo_pattern = r"#(\d+)\s*=\s*NEXT_ASSEMBLY_USAGE_OCCURRENCE\s*\(\s*'([^']*)'[^#]*#(\d+)[^#]*#(\d+)"
    nauos = re.findall(nauo_pattern, text)
    
    print(f"\n=== NAUO装配关系 ({len(nauos)}个) ===")
    for id, name, parent_pd, child_pd in nauos[:30]:
        # 尝试找到对应的PRODUCT名称
        parent_name = product_by_id.get(parent_pd, f"PD#{parent_pd}")
        child_name = product_by_id.get(child_pd, f"PD#{child_pd}")
        print(f"  NAUO#{id} '{name}': {parent_name} -> {child_name}")
    if len(nauos) > 30:
        print(f"  ... 共 {len(nauos)} 个")
    
    # 4. 找出所有的"顶层"组件（在BOM中列出的）
    print("\n=== 寻找组件名称模式 ===")
    assembly_names = set()
    for id, name in products:
        # 匹配组件代号模式，如 E-CW3T-01, E-CW3T-02
        if re.match(r'E-CW3T-\d+[-$]?', name):
            assembly_names.add(name)
            print(f"  找到组件: {name} (#{id})")
    
    return products, nauos

if __name__ == "__main__":
    # 找到产品总图的STEP文件
    step_dir = Path("output/03.05.20.0005E-CW3T-VIO35挖机压实轮VIO35连接器/step_files")
    step_files = list(step_dir.glob("*.STEP")) + list(step_dir.glob("*.step"))
    
    for sf in step_files:
        analyze_step_file(sf)
        print("\n" + "="*60 + "\n")

