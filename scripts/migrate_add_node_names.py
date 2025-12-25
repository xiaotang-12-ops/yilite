# -*- coding: utf-8 -*-
"""
迁移脚本：为现有的 assembly_manual.json 补充 node_name

问题背景：
- bom_to_mesh 映射是正确的（所有零件都有 node_name）
- 但步骤数据中的 components 缺少 node_name（导致前端3D高亮失效）

修复逻辑：
1. 读取 assembly_manual.json
2. 从 3d_resources.bom_to_mesh 获取映射
3. 遍历所有步骤，为 components/fasteners/parts_used 注入 node_name
4. 保存修复后的文件
"""

import json
import sys
from pathlib import Path


def migrate_manual(manual_path: str, dry_run: bool = False) -> dict:
    """
    迁移单个手册文件
    
    Args:
        manual_path: assembly_manual.json 的路径
        dry_run: 是否只检查不修改
        
    Returns:
        统计信息
    """
    manual_path = Path(manual_path)
    if not manual_path.exists():
        print(f"❌ 文件不存在: {manual_path}")
        return {"success": False, "error": "file_not_found"}
    
    # 读取文件
    with open(manual_path, "r", encoding="utf-8") as f:
        manual = json.load(f)
    
    # 获取 bom_to_mesh 映射
    bom_to_mesh = manual.get("3d_resources", {}).get("bom_to_mesh", {})
    if not bom_to_mesh:
        print(f"⚠️  没有 bom_to_mesh 映射: {manual_path}")
        return {"success": False, "error": "no_bom_to_mesh"}
    
    print(f"📊 bom_to_mesh 中有 {len(bom_to_mesh)} 个映射")
    
    # 统计
    stats = {
        "total_steps": 0,
        "components_fixed": 0,
        "fasteners_fixed": 0,
        "parts_used_fixed": 0,
        "already_has_node_name": 0,
        "no_mapping_found": 0,
    }
    
    def inject_node_name(item: dict, item_type: str) -> bool:
        """为单个零件注入 node_name"""
        # 已经有 node_name 的跳过
        if item.get("node_name"):
            stats["already_has_node_name"] += 1
            return False
        
        # 尝试通过 component_code 或 bom_code 查找
        code = item.get("bom_code") or item.get("component_code")
        if not code:
            # 尝试从步骤级别获取 component_code
            return False
        
        node_names = bom_to_mesh.get(code, [])
        if node_names:
            item["node_name"] = node_names
            if not item.get("bom_code"):
                item["bom_code"] = code
            return True
        else:
            stats["no_mapping_found"] += 1
            return False
    
    def process_step(step: dict):
        """处理单个步骤"""
        stats["total_steps"] += 1
        component_code = step.get("component_code", "")

        # 处理 components
        for comp in step.get("components", []):
            # 已经有 node_name 的跳过
            if comp.get("node_name"):
                stats["already_has_node_name"] += 1
                continue

            # 优先用 comp 自己的 bom_code，否则用步骤的 component_code
            code = comp.get("bom_code") or component_code
            if code:
                node_names = bom_to_mesh.get(code, [])
                if node_names:
                    comp["node_name"] = node_names
                    comp["bom_code"] = code
                    stats["components_fixed"] += 1
                else:
                    stats["no_mapping_found"] += 1

        # 处理 fasteners
        for fastener in step.get("fasteners", []):
            if inject_node_name(fastener, "fastener"):
                stats["fasteners_fixed"] += 1

        # 处理 parts_used
        for part in step.get("parts_used", []):
            if inject_node_name(part, "part"):
                stats["parts_used_fixed"] += 1
    
    # 处理产品装配步骤
    product_steps = manual.get("product_assembly", {}).get("steps", [])
    print(f"📦 处理产品装配步骤: {len(product_steps)} 个")
    for step in product_steps:
        process_step(step)
    
    # 处理组件装配步骤
    component_chapters = manual.get("component_assembly", [])
    print(f"📦 处理组件装配章节: {len(component_chapters)} 个")
    for chapter in component_chapters:
        for step in chapter.get("steps", []):
            process_step(step)
    
    # 打印统计
    print(f"\n📊 统计结果:")
    print(f"   - 总步骤数: {stats['total_steps']}")
    print(f"   - 修复的 components: {stats['components_fixed']}")
    print(f"   - 修复的 fasteners: {stats['fasteners_fixed']}")
    print(f"   - 修复的 parts_used: {stats['parts_used_fixed']}")
    print(f"   - 已有 node_name: {stats['already_has_node_name']}")
    print(f"   - 未找到映射: {stats['no_mapping_found']}")
    
    total_fixed = stats["components_fixed"] + stats["fasteners_fixed"] + stats["parts_used_fixed"]
    
    if dry_run:
        print(f"\n🔍 DRY RUN 模式，不保存文件")
    elif total_fixed > 0:
        # 备份原文件
        backup_path = manual_path.with_suffix(".json.bak")
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(manual, f, ensure_ascii=False, indent=2)
        print(f"💾 已备份原文件: {backup_path.name}")
        
        # 保存修复后的文件
        with open(manual_path, "w", encoding="utf-8") as f:
            json.dump(manual, f, ensure_ascii=False, indent=2)
        print(f"✅ 已保存修复后的文件: {manual_path.name}")
    else:
        print(f"\n✅ 无需修复，所有零件已有 node_name 或无映射")
    
    stats["success"] = True
    stats["total_fixed"] = total_fixed
    return stats


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python migrate_add_node_names.py <manual_path> [--dry-run]")
        print("示例: python migrate_add_node_names.py output/xxx/assembly_manual.json")
        sys.exit(1)
    
    manual_path = sys.argv[1]
    dry_run = "--dry-run" in sys.argv
    
    print(f"🔧 迁移脚本：为 assembly_manual.json 补充 node_name")
    print(f"📂 文件: {manual_path}")
    print(f"{'🔍 DRY RUN 模式' if dry_run else '💾 正式执行模式'}\n")
    
    migrate_manual(manual_path, dry_run)


if __name__ == "__main__":
    main()

