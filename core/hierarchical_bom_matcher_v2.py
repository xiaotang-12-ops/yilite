# -*- coding: utf-8 -*-
"""
分层级的BOM-3D匹配器 V2
处理组件级别和产品级别的分开匹配
"""

from typing import Dict, List
from pathlib import Path
from processors.file_processor import ModelProcessor
from processors.step_to_glb_converter import StepToGlbConverter
from core.bom_3d_matcher import match_bom_to_3d  # ✅ 使用完整版的匹配函数

from utils.logger import print_step, print_substep, print_info, print_success, print_error, print_warning


class HierarchicalBOMMatcher:
    """分层级的BOM-3D匹配器"""
    
    def __init__(self):
        """初始化匹配器"""
        self.model_processor = ModelProcessor()
        self.step_converter = StepToGlbConverter(self.model_processor)
    
    def process_hierarchical_matching(
        self,
        step_dir: str,
        bom_data: List[Dict],
        component_plans: List[Dict],
        output_dir: str,
        file_hierarchy: Dict = None
    ) -> Dict:
        """
        分层级处理STEP文件和BOM匹配

        Args:
            step_dir: STEP文件目录
            bom_data: 完整的BOM数据
            component_plans: 组件规划列表（来自Agent 1）
            output_dir: GLB输出目录
            file_hierarchy: 文件层级结构（包含组件图的实际序号）

        Returns:
            {
                "component_level_mappings": {...},  # 组件级别的映射
                "product_level_mapping": {...},     # 产品级别的映射
                "glb_files": {...}                  # 所有GLB文件路径
            }
        """
        print_step("分层级BOM-3D匹配")

        step_path = Path(step_dir)
        glb_output = Path(output_dir)
        glb_output.mkdir(parents=True, exist_ok=True)

        print_info(f"STEP文件目录: {step_dir}")
        print_info(f"GLB输出目录: {output_dir}")
        print_info(f"组件数量: {len(component_plans)}")

        # ✅ 新策略：直接使用 file_hierarchy 中的文件序号（index）
        # 不再依赖 AI 识别的 drawing_number，避免 PDF 标注和文件序号不一致的问题
        print_info("📂 使用文件系统中的实际文件序号进行映射")

        # 结果容器
        component_level_mappings = {}
        product_level_mapping = {}
        glb_files = {}

        # ========== 1. 处理组件级别 ==========
        print_substep("步骤1：处理组件级别的STEP文件")

        # ✅ 遍历 file_hierarchy 中的组件（按文件实际存在的顺序）
        components_from_files = file_hierarchy.get("components", []) if file_hierarchy else []

        if not components_from_files:
            print_warning("file_hierarchy 中没有组件信息，回退到使用 component_plans", indent=1)
            # 回退方案：使用 component_plans 的 assembly_order
            components_from_files = [
                {
                    "index": plan.get("assembly_order", i + 1),
                    "name": f"组件图{plan.get('assembly_order', i + 1)}",
                    "component_code": plan.get("component_code", ""),
                    "component_name": plan.get("component_name", "")
                }
                for i, plan in enumerate(component_plans)
            ]

        for comp_file_info in components_from_files:
            file_index = comp_file_info.get("index")  # 文件序号（组件图X 中的 X）
            file_name = comp_file_info.get("name", f"组件图{file_index}")
            step_path_from_hierarchy = comp_file_info.get("step")

            # 查找对应的 AI 规划（通过 assembly_order 匹配）
            comp_plan = None
            for plan in component_plans:
                # 尝试通过 assembly_order 匹配
                if plan.get("assembly_order") == file_index:
                    comp_plan = plan
                    break

            if not comp_plan:
                # 如果找不到匹配的规划，跳过
                print_warning(f"未找到组件图{file_index}对应的AI规划，跳过", indent=1)
                continue

            comp_code = comp_plan.get("component_code", "")
            comp_name = comp_plan.get("component_name", "")
            comp_order = comp_plan.get("assembly_order", 0)

            print_info(f"\n处理组件: {comp_name} (文件序号={file_index}, 装配顺序={comp_order})")

            # ✅ 优先使用 file_hierarchy 中记录的真实 STEP 路径
            step_file = None
            if step_path_from_hierarchy:
                candidate = Path(step_path_from_hierarchy)
                if candidate.exists():
                    step_file = candidate

            # 若未找到，再按历史命名回退
            if not step_file:
                possible_names = [
                    f"组件图{file_index}.STEP",
                    f"组件图{file_index}.step",
                    f"组件{file_index}.STEP",
                    f"组件{file_index}.step",
                    f"组件图{file_index}.stp",
                    f"组件{file_index}.stp"
                ]

                for name in possible_names:
                    candidate = step_path / name
                    if candidate.exists():
                        step_file = candidate
                        break

                if not step_file:
                    print_warning(f"组件图{file_index}的STEP文件不存在（尝试了: {', '.join(possible_names)}）", indent=1)
                    continue

            print_info(f"STEP文件: {step_file.name}", indent=1)

            # ✅ 使用文件序号命名GLB文件
            glb_file = glb_output / f"component_{file_index}.glb"
            print_info(f"开始转换STEP -> GLB: {glb_file.name}", indent=1)

            import sys
            sys.stdout.flush()

            convert_result = self.step_converter.convert(
                step_path=str(step_file),
                output_path=str(glb_file),
                scale_factor=0.001  # mm -> m
            )

            sys.stdout.flush()
            
            if not convert_result["success"]:
                print_error(f"GLB转换失败: {convert_result.get('error')}", indent=1)
                continue
            
            parts_list = convert_result.get("parts_info", [])
            print_success(f"GLB转换成功: {len(parts_list)} 个零件", indent=1)

            # 获取组件的BOM数据（只包含组件内部的零件）
            component_bom = self._get_component_bom(bom_data, comp_plan, file_index, file_name=comp_name)
            print_info(f"组件BOM: {len(component_bom)} 个零件", indent=1)

            # BOM-3D匹配（双匹配策略：代码匹配 + AI跟进匹配）
            if parts_list and component_bom:
                # 步骤1：代码匹配
                code_matching_result = match_bom_to_3d(component_bom, parts_list)

                code_bom_to_mesh = code_matching_result.get("bom_to_mesh_mapping", {})
                code_summary = code_matching_result.get("summary", {})
                unmatched_parts = code_matching_result.get("unmatched_parts", [])

                code_bom_matched = code_summary.get('bom_matched_count', 0)
                total_bom = code_summary.get('total_bom_count', 0)
                total_parts = code_summary.get('total_3d_parts', 0)

                # ✅ AI匹配所有零件
                print_info(f"🤖 AI匹配员工开始工作，分析 {len(component_bom)} 个BOM和 {len(parts_list)} 个3D零件", indent=1)
                ai_bom_to_mesh = {}
                ai_bom_matched_count = 0

                if unmatched_parts:
                    import sys
                    sys.stdout.flush()

                    # ✅ 计算未匹配的BOM（排除已经被代码匹配的BOM）
                    matched_bom_codes = set(code_bom_to_mesh.keys())
                    unmatched_bom = [bom for bom in component_bom if bom.get('code') not in matched_bom_codes]

                    from core.ai_matcher import AIBOMMatcher
                    ai_matcher = AIBOMMatcher()
                    ai_results = ai_matcher.match_unmatched_parts(unmatched_parts, unmatched_bom)

                    # ✅ 将AI匹配结果应用到cleaned_parts（更新bom_code）
                    cleaned_parts = code_matching_result.get("cleaned_parts", [])
                    for ai_result in ai_results:
                        bom_code = ai_result.get("matched_bom_code")
                        node_name = ai_result.get("node_name")

                        if bom_code and node_name:
                            # 找到对应的零件并更新bom_code
                            for part in cleaned_parts:
                                if part.get("node_name") == node_name and not part.get("bom_code"):
                                    part["bom_code"] = bom_code
                                    part["match_method"] = "AI匹配"
                                    part["confidence"] = ai_result.get("confidence", 0.0)
                                    break

                            # 同时更新ai_bom_to_mesh映射（用于统计）
                            if bom_code not in ai_bom_to_mesh:
                                ai_bom_to_mesh[bom_code] = []
                            ai_bom_to_mesh[bom_code].append(node_name)

                    # 计算AI新增匹配的BOM数量（不在代码匹配中的）
                    ai_bom_matched_count = len([k for k in ai_bom_to_mesh.keys() if k not in code_bom_to_mesh])

                # ✅ 合并匹配结果
                final_bom_to_mesh = {**code_bom_to_mesh, **ai_bom_to_mesh}
                total_bom_matched = len(final_bom_to_mesh)
                final_bom_rate = total_bom_matched / total_bom if total_bom else 0

                # 计算最终的3D零件匹配数
                final_parts_matched = sum(len(meshes) for meshes in final_bom_to_mesh.values())
                final_parts_rate = final_parts_matched / total_parts if total_parts else 0

                print_success(f"✅ AI匹配完成:", indent=1)
                print_info(f"  📋 BOM匹配率: {total_bom_matched}/{total_bom} ({final_bom_rate*100:.1f}%)", indent=1)
                print_info(f"  🎨 3D零件覆盖率: {final_parts_matched}/{total_parts} ({final_parts_rate*100:.1f}%)", indent=1)

                # ✅ 列出未匹配的BOM
                if total_bom_matched < total_bom:
                    unmatched_bom_codes = [bom.get('code') for bom in component_bom if bom.get('code') not in final_bom_to_mesh]
                    print_warning(f"  ⚠️  未匹配的BOM ({len(unmatched_bom_codes)}个): {', '.join(unmatched_bom_codes[:5])}", indent=1)

                import sys
                sys.stdout.flush()

                # ✅ 重新生成BOM映射宽表（使用更新后的cleaned_parts）
                from core.bom_3d_matcher import BOM3DMatcher
                matcher = BOM3DMatcher()
                bom_mapping_table = matcher.generate_bom_mapping_table(component_bom, cleaned_parts)

                # ✅ 生成组件的爆炸视图数据
                print_info(f"生成组件{file_index}爆炸视图数据...", indent=1)
                explosion_result = self.model_processor.generate_explosion_data(
                    glb_path=str(glb_file),
                    assembly_spec={},  # 组件级别暂时不需要装配规程
                    output_dir=str(glb_output)
                )

                if explosion_result["success"]:
                    # 重命名manifest.json为manifest_component_{file_index}.json
                    import shutil
                    from pathlib import Path as PathLib  # ✅ 使用别名避免与顶部导入冲突
                    manifest_path = PathLib(explosion_result["manifest_path"])
                    component_manifest_path = manifest_path.parent / f"manifest_component_{file_index}.json"
                    shutil.move(str(manifest_path), str(component_manifest_path))
                    print_success(f"爆炸视图数据生成成功: {explosion_result['node_count']} 个零件", indent=1)
                else:
                    print_warning(f"爆炸视图数据生成失败: {explosion_result.get('error')}", indent=1)

                # 保存组件级别的映射
                component_level_mappings[comp_code] = {
                    "component_name": comp_name,
                    "glb_file": str(glb_file),
                    "drawing_index": file_index,  # ✅ 使用文件序号
                    "assembly_order": comp_order,  # ✅ 保留装配顺序信息
                    "bom_to_mesh": final_bom_to_mesh,
                    "bom_mapping_table": bom_mapping_table,  # ✅ 新增：保存BOM映射宽表
                    "total_bom_count": total_bom,
                    "bom_matched_count": total_bom_matched,
                    "bom_matching_rate": final_bom_rate,  # ✅ BOM匹配率
                    "total_3d_parts": total_parts,
                    "matched_3d_count": final_parts_matched,  # ✅ 匹配的3D零件数
                    "parts_matching_rate": final_parts_rate,  # ✅ 3D零件匹配率
                    "code_matched": code_bom_matched,
                    "ai_matched": ai_bom_matched_count,
                    "matching_rate": final_bom_rate  # ✅ 兼容旧代码
                }

                # ✅ 使用组件代号作为 key，若缺失则使用 component_X
                glb_key = comp_code or f"component_{file_index}"
                glb_files[glb_key] = str(glb_file)
            else:
                if not parts_list:
                    print_warning("没有提取到零件信息", indent=1)
                if not component_bom:
                    print_warning("没有组件BOM数据", indent=1)
                # 即便未匹配成功，也记录 GLB，便于前端加载
                glb_key = comp_code or f"component_{file_index}"
                glb_files[glb_key] = str(glb_file)
        
        print_success(f"组件级别处理完成: {len(component_level_mappings)} 个组件")
        
        # ========== 2. 处理产品级别 ==========
        print_substep("步骤2：处理产品级别的STEP文件")
        
        # 查找产品总图的STEP文件（优先使用 file_hierarchy 中的真实文件名）
        product_step = None
        product_info = file_hierarchy.get("product") if isinstance(file_hierarchy, dict) else None
        if isinstance(product_info, dict) and product_info.get("step"):
            candidate = Path(product_info["step"])
            if candidate.exists():
                product_step = candidate

        # 回退：尝试多种可能的产品STEP文件名
        if not product_step:
            possible_product_names = [
                "产品测试.STEP",
                "产品总图.STEP",
                "产品主图.STEP",
                "产品测试.step",
                "产品总图.step",
                "产品主图.step",
                "产品测试.stp",
                "产品总图.stp",
                "产品主图.stp",
            ]
            for name in possible_product_names:
                candidate = step_path / name
                if candidate.exists():
                    product_step = candidate
                    break

        if product_step and product_step.exists():
            print_info(f"处理产品总图: {product_step.name}")
            
            # 转换为GLB
            product_glb = glb_output / "product_total.glb"
            convert_result = self.step_converter.convert(
                step_path=str(product_step),
                output_path=str(product_glb),
                scale_factor=0.001
            )
            
            if convert_result["success"]:
                parts_list = convert_result.get("parts_info", [])
                print_success(f"GLB转换成功: {len(parts_list)} 个零件", indent=1)

                # ✅ 生成产品总图的爆炸视图数据
                print_info("生成产品总图爆炸视图数据...", indent=1)
                explosion_result = self.model_processor.generate_explosion_data(
                    glb_path=str(product_glb),
                    assembly_spec={},  # 产品级别暂时不需要装配规程
                    output_dir=str(glb_output)
                )

                if explosion_result["success"]:
                    # 重命名manifest.json为manifest_product.json
                    import shutil
                    from pathlib import Path as PathLib  # ✅ 避免与顶部导入冲突
                    manifest_path = PathLib(explosion_result["manifest_path"])
                    product_manifest_path = manifest_path.parent / "manifest_product.json"
                    shutil.move(str(manifest_path), str(product_manifest_path))
                    print_success(f"爆炸视图数据生成成功: {explosion_result['node_count']} 个零件", indent=1)
                else:
                    print_warning(f"爆炸视图数据生成失败: {explosion_result.get('error')}", indent=1)

                # ✅ 产品级别的BOM数据（从产品总图PDF提取的零件）
                # ✅ 修改：不排除组件，组件的零件也要参与匹配
                product_pdf_stem = ""
                if isinstance(product_info, dict) and product_info.get("pdf"):
                    product_pdf_stem = Path(product_info["pdf"]).stem

                product_bom_all = [
                    item for item in bom_data
                    if product_pdf_stem and str(item.get("source_pdf", "")).startswith(product_pdf_stem)
                ]

                # ✅ 新策略：包含所有BOM项（组件+零件）
                # 原因：产品总装步骤需要高亮组件内的零件，所以组件的零件也要参与匹配
                product_bom = product_bom_all

                print(f"  产品BOM: {len(product_bom)} 个项（包含组件和零件）", flush=True)
                
                # BOM-3D匹配（双匹配策略：代码匹配 + AI跟进匹配）
                # 步骤1：代码匹配
                code_matching_result = match_bom_to_3d(product_bom, parts_list)

                code_bom_to_mesh = code_matching_result.get("bom_to_mesh_mapping", {})
                code_summary = code_matching_result.get("summary", {})
                unmatched_parts = code_matching_result.get("unmatched_parts", [])

                code_bom_matched = code_summary.get('bom_matched_count', 0)
                total_bom = code_summary.get('total_bom_count', 0)
                total_parts = code_summary.get('total_3d_parts', 0)

                # ✅ AI匹配所有零件
                print_info(f"🤖 AI匹配员工开始工作，分析 {len(product_bom)} 个BOM和 {len(parts_list)} 个3D零件", indent=1)
                ai_bom_to_mesh = {}
                ai_bom_matched_count = 0

                if unmatched_parts:
                    import sys
                    sys.stdout.flush()

                    # ✅ 计算未匹配的BOM（排除已经被代码匹配的BOM）
                    matched_bom_codes = set(code_bom_to_mesh.keys())
                    unmatched_bom = [bom for bom in product_bom if bom.get('code') not in matched_bom_codes]

                    from core.ai_matcher import AIBOMMatcher
                    ai_matcher = AIBOMMatcher()
                    ai_results = ai_matcher.match_unmatched_parts(unmatched_parts, unmatched_bom)

                    # ✅ 将AI匹配结果应用到cleaned_parts（更新bom_code）
                    cleaned_parts = code_matching_result.get("cleaned_parts", [])
                    for ai_result in ai_results:
                        bom_code = ai_result.get("matched_bom_code")
                        node_name = ai_result.get("node_name")

                        if bom_code and node_name:
                            # 找到对应的零件并更新bom_code
                            for part in cleaned_parts:
                                if part.get("node_name") == node_name and not part.get("bom_code"):
                                    part["bom_code"] = bom_code
                                    part["match_method"] = "AI匹配"
                                    part["confidence"] = ai_result.get("confidence", 0.0)
                                    break

                            # 同时更新ai_bom_to_mesh映射（用于统计）
                            if bom_code not in ai_bom_to_mesh:
                                ai_bom_to_mesh[bom_code] = []
                            ai_bom_to_mesh[bom_code].append(node_name)

                    # 计算AI新增匹配的BOM数量（不在代码匹配中的）
                    ai_bom_matched_count = len([k for k in ai_bom_to_mesh.keys() if k not in code_bom_to_mesh])

                # ✅ 合并匹配结果
                final_bom_to_mesh = {**code_bom_to_mesh, **ai_bom_to_mesh}
                total_bom_matched = len(final_bom_to_mesh)
                final_bom_rate = total_bom_matched / total_bom if total_bom else 0

                # 计算最终的3D零件匹配数
                final_parts_matched = sum(len(meshes) for meshes in final_bom_to_mesh.values())
                final_parts_rate = final_parts_matched / total_parts if total_parts else 0

                print_success(f"✅ AI匹配完成:", indent=1)
                print_info(f"  📋 BOM匹配率: {total_bom_matched}/{total_bom} ({final_bom_rate*100:.1f}%)", indent=1)
                print_info(f"  🎨 3D零件覆盖率: {final_parts_matched}/{total_parts} ({final_parts_rate*100:.1f}%)", indent=1)

                # ✅ 列出未匹配的BOM
                if total_bom_matched < total_bom:
                    unmatched_bom_codes = [bom.get('code') for bom in product_bom if bom.get('code') not in final_bom_to_mesh]
                    print_warning(f"  ⚠️  未匹配的BOM ({len(unmatched_bom_codes)}个): {', '.join(unmatched_bom_codes[:5])}", indent=1)

                import sys
                sys.stdout.flush()

                # ✅ 重新生成BOM映射宽表（使用更新后的cleaned_parts）
                from core.bom_3d_matcher import BOM3DMatcher
                matcher = BOM3DMatcher()
                product_bom_mapping_table = matcher.generate_bom_mapping_table(product_bom, cleaned_parts)

                product_level_mapping = {
                    "glb_file": str(product_glb),
                    "bom_to_mesh": final_bom_to_mesh,
                    "bom_mapping_table": product_bom_mapping_table,  # ✅ 新增：保存BOM映射宽表
                    "total_bom_count": total_bom,
                    "bom_matched_count": total_bom_matched,
                    "bom_matching_rate": final_bom_rate,  # ✅ BOM匹配率
                    "total_3d_parts": total_parts,
                    "matched_3d_count": final_parts_matched,  # ✅ 匹配的3D零件数
                    "parts_matching_rate": final_parts_rate,  # ✅ 3D零件匹配率
                    "code_matched": code_bom_matched,
                    "ai_matched": ai_bom_matched_count,
                    "matching_rate": final_bom_rate  # ✅ 兼容旧代码
                }

                glb_files["product_total"] = str(product_glb)
            else:
                print_error(f"GLB转换失败: {convert_result.get('error')}", indent=1)
        else:
            print_warning("未找到产品总图的STEP文件")
        
        # ========== 3. 汇总结果 ==========
        print_substep("分层级匹配汇总")
        print_info(f"组件级别: {len(component_level_mappings)} 个组件")
        for comp_code, mapping in component_level_mappings.items():
            print_info(f"  {comp_code}: BOM {mapping['bom_matched_count']}/{mapping['total_bom_count']} ({mapping['matching_rate']*100:.1f}%)", indent=1)

        if product_level_mapping:
            print_info(f"产品级别: BOM {product_level_mapping['bom_matched_count']}/{product_level_mapping['total_bom_count']} ({product_level_mapping['matching_rate']*100:.1f}%)")

        # ========== 4. 生成 GLB 清单（step3_glb_inventory.json，用于调试） ==========
        try:
            inventory = {}
            for key, glb_path in glb_files.items():
                inv = self.model_processor.generate_glb_inventory(
                    glb_path=glb_path,
                    output_path=None
                )
                inventory[key] = inv
            inventory_path = Path(output_dir).parent / "step3_glb_inventory.json"
            with open(inventory_path, "w", encoding="utf-8") as f:
                json.dump({
                    "glb_files": inventory
                }, f, ensure_ascii=False, indent=2)
            print_success(f"GLB 清单已生成: {inventory_path.name}")
        except Exception as e:
            print_warning(f"生成 GLB 清单失败: {e}")
        
        return {
            "success": True,
            "component_level_mappings": component_level_mappings,
            "product_level_mapping": product_level_mapping,
            "glb_files": glb_files
        }
    
    def _get_component_bom(self, bom_data: List[Dict], comp_plan: Dict, drawing_index: int = None, file_name: str = "") -> List[Dict]:
        """
        获取组件的BOM数据（只包含组件内部的零件）

        根据source_pdf字段来区分：
        - 组件图1.pdf -> 组件1的BOM
        - 组件图2.pdf -> 组件2的BOM
        - 组件图3.pdf -> 组件3的BOM

        Args:
            bom_data: 完整的BOM数据
            comp_plan: 组件规划（包含assembly_order）
            drawing_index: 实际的图纸序号（优先使用）

        Returns:
            组件的BOM数据列表
        """
        # ✅ 优先使用drawing_index，如果没有则使用assembly_order
        if drawing_index is None:
            drawing_index = comp_plan.get("assembly_order", 0)

        comp_name = comp_plan.get("component_name", "") or file_name or comp_plan.get("component_code", "")

        # 根据source_pdf过滤BOM数据（支持多种命名方式）
        component_bom = []

        # 可能的文件名格式（不区分大小写）
        base_name = comp_name or f"组件图{drawing_index}"
        possible_names = {
            f"组件图{drawing_index}.pdf",
            f"组件图{drawing_index}.PDF",
            f"组件{drawing_index}.pdf",
            f"组件{drawing_index}.PDF",
            f"{base_name}.pdf",
            f"{base_name}.PDF"
        }

        # ✅ 调试日志：打印查找信息
        print_info(f"🔍 查找组件{drawing_index}({comp_name})的BOM数据", indent=1)
        print_info(f"   可能的文件名: {', '.join(sorted(possible_names))}", indent=1)

        # 统计所有source_pdf
        all_source_pdfs = set()
        for bom_item in bom_data:
            source_pdf = bom_item.get("source_pdf", "")
            all_source_pdfs.add(source_pdf)
            # 不区分大小写匹配
            if source_pdf in possible_names:
                component_bom.append(bom_item)

        print_info(f"   BOM数据中的所有source_pdf: {', '.join(sorted(all_source_pdfs))}", indent=1)
        print_info(f"   匹配到的BOM数量: {len(component_bom)}", indent=1)

        return component_bom

