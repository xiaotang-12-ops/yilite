#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
提取STEP文件中的零件列表
"""

import re
from pathlib import Path
import sys

def extract_parts_from_step(step_file_path):
    """从STEP文件中提取零件列表"""
    with open(step_file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # 提取所有PRODUCT定义
    # STEP文件格式: #123 = PRODUCT('零件名称', ...);
    products = re.findall(r"#\d+\s*=\s*PRODUCT\s*\('([^']+)'", content)
    
    # 去重并排序
    unique_products = sorted(set(products))
    
    return unique_products

if __name__ == "__main__":
    # 组件图2的STEP文件
    step_file = Path('output/dfb95cdb-923e-49c9-910d-a716de3bf8be/step_files/组件图2.STEP')
    
    if not step_file.exists():
        print(f"错误: 文件不存在 {step_file}")
        sys.exit(1)
    
    parts = extract_parts_from_step(step_file)
    
    print(f"# 组件图2 STEP文件零件列表\n")
    print(f"**文件路径**: `{step_file}`")
    print(f"**零件总数**: {len(parts)}\n")
    print(f"## 零件清单\n")
    
    for i, part in enumerate(parts, 1):
        print(f"{i}. {part}")

