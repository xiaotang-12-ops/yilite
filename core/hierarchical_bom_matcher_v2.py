# -*- coding: utf-8 -*-
"""
分层级的BOM-3D匹配器 V2
处理组件级别和产品级别的分开匹配
"""

import json
import re
from typing import Dict, List, Optional
from pathlib import Path
from processors.file_processor import ModelProcessor
from processors.step_to_glb_converter import StepToGlbConverter
from core.bom_3d_matcher import match_bom_to_3d  # ✅ 使用完整版的匹配函数
from core.step_hierarchy_parser import parse_step_hierarchy, collect_leaf_parts

from utils.logger import print_step, print_substep, print_info, print_success, print_error, print_warning
from utils.time_utils import build_debug_output_dir


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
        file_hierarchy: Dict = None,
        ai_provider: str = "openrouter",
        ai_model: Optional[str] = None,
        ai_fallback_model: Optional[str] = None,
        ai_api_key: Optional[str] = None
    ) -> Dict:
        """
        分层级处理STEP文件和BOM匹配

        Args:
            step_dir: STEP文件目录
            bom_data: 完整的BOM数据
            component_plans: 组件规划列表（来自Agent 1）
            output_dir: GLB输出目录
            file_hierarchy: 文件层级结构（包含组件图的实际序号）
            ai_provider: AI提供方（openrouter/deepseek/doubao）
            ai_model: AI模型名称
            ai_fallback_model: AI兜底模型名称（可选）
            ai_api_key: AI API密钥

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
        task_id = glb_output.parent.name or step_path.parent.name or "unknown_task"

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
                    ai_matcher = AIBOMMatcher(
                        task_id=task_id,
                        provider=ai_provider,
                        model_name=ai_model,
                        fallback_model_name=ai_fallback_model,
                        api_key=ai_api_key
                    )
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
        hierarchy_output = glb_output.parent / "step_assembly_hierarchy.json"
        hierarchy_data = None
        
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

                # 解析并保存 STEP 装配层级
                try:
                    hierarchy_data = parse_step_hierarchy(str(product_step))
                    hierarchy_output.parent.mkdir(parents=True, exist_ok=True)
                    with open(hierarchy_output, "w", encoding="utf-8") as f:
                        json.dump(hierarchy_data, f, ensure_ascii=False, indent=2)
                    print_success(f"装配层级已生成: {hierarchy_output.name}", indent=1)
                except Exception as e:
                    print_warning(f"装配层级解析失败: {e}", indent=1)
                
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

                # ========== 优化后的匹配策略 v2.0.33 ==========
                # 优先级：层级匹配(100%准确) → 代码匹配 → AI匹配(兜底)

                total_bom = len(product_bom)
                total_parts = len(parts_list)

                # ✅ 步骤1：层级匹配优先（100%准确，基于STEP文件的真实父子关系）
                assembly_to_mesh = {}
                hierarchy_matched_nodes = set()  # 记录层级匹配已覆盖的node_names
                hierarchy_matched_bom_codes = set()  # 记录层级匹配已覆盖的bom_codes

                if hierarchy_data:
                    try:
                        print_info("🏗️ 步骤1：层级匹配（优先，100%准确）", indent=1)
                        assembly_to_mesh = self._build_assembly_mesh_mapping(
                            hierarchy_data.get("hierarchy", {}),
                            product_bom,
                            parts_list,  # 直接使用parts_list，无需等待cleaned_parts
                            nauo_edges=hierarchy_data.get("nauo_edges", []),
                            task_name=task_id,
                        )
                        if assembly_to_mesh:
                            # 收集已被层级匹配覆盖的node_names和bom_codes
                            for bom_code, node_list in assembly_to_mesh.items():
                                hierarchy_matched_bom_codes.add(bom_code)
                                hierarchy_matched_nodes.update(node_list)
                            print_success(f"  层级匹配成功: {len(assembly_to_mesh)} 个装配体, 覆盖 {len(hierarchy_matched_nodes)} 个零件", indent=1)
                        else:
                            print_info("  层级匹配无结果（可能没有子装配体）", indent=1)
                    except Exception as e:
                        print_warning(f"层级匹配失败: {e}", indent=1)

                # ✅ 步骤2：代码匹配（处理剩余零件，排除已被层级匹配覆盖的）
                print_info("📝 步骤2：代码匹配（处理剩余零件）", indent=1)

                # 过滤掉已被层级匹配覆盖的零件
                remaining_parts = [p for p in parts_list if p.get("node_name") not in hierarchy_matched_nodes]
                # 过滤掉已被层级匹配覆盖的BOM
                remaining_bom = [b for b in product_bom if b.get("code") not in hierarchy_matched_bom_codes]

                print_info(f"  剩余零件: {len(remaining_parts)}/{total_parts}, 剩余BOM: {len(remaining_bom)}/{total_bom}", indent=1)

                code_matching_result = match_bom_to_3d(remaining_bom, remaining_parts)

                code_bom_to_mesh = code_matching_result.get("bom_to_mesh_mapping", {})
                code_summary = code_matching_result.get("summary", {})
                unmatched_parts = code_matching_result.get("unmatched_parts", [])
                cleaned_parts = code_matching_result.get("cleaned_parts", [])

                code_bom_matched = code_summary.get('bom_matched_count', 0)
                print_info(f"  代码匹配成功: {code_bom_matched} 个BOM", indent=1)

                # ✅ 步骤3：AI匹配（处理仍未匹配的零件，兜底）
                print_info(f"🤖 步骤3：AI匹配（兜底，处理仍未匹配的零件）", indent=1)
                ai_bom_to_mesh = {}
                ai_bom_matched_count = 0

                if unmatched_parts:
                    import sys
                    sys.stdout.flush()

                    # 计算未匹配的BOM（排除已被层级匹配和代码匹配覆盖的）
                    matched_bom_codes = hierarchy_matched_bom_codes | set(code_bom_to_mesh.keys())
                    unmatched_bom = [bom for bom in product_bom if bom.get('code') not in matched_bom_codes]

                    print_info(f"  待AI匹配: {len(unmatched_parts)} 个零件, {len(unmatched_bom)} 个BOM", indent=1)

                    if unmatched_bom:  # 只有还有未匹配的BOM才调用AI
                        from core.ai_matcher import AIBOMMatcher
                        ai_matcher = AIBOMMatcher(
                            task_id=task_id,
                            provider=ai_provider,
                            model_name=ai_model,
                            fallback_model_name=ai_fallback_model,
                            api_key=ai_api_key
                        )
                        ai_results = ai_matcher.match_unmatched_parts(unmatched_parts, unmatched_bom)

                        # 将AI匹配结果应用到cleaned_parts（更新bom_code）
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

                        # 计算AI新增匹配的BOM数量
                        ai_bom_matched_count = len(ai_bom_to_mesh)
                        print_info(f"  AI匹配成功: {ai_bom_matched_count} 个BOM", indent=1)
                    else:
                        print_info("  无需AI匹配（所有BOM已被层级/代码匹配覆盖）", indent=1)
                else:
                    print_info("  无需AI匹配（所有零件已匹配）", indent=1)

                # ✅ 步骤4：合并匹配结果（层级优先）
                # 合并顺序：层级匹配 → 代码匹配 → AI匹配
                final_bom_to_mesh = {**assembly_to_mesh, **code_bom_to_mesh, **ai_bom_to_mesh}
                total_bom_matched = len(final_bom_to_mesh)
                final_bom_rate = total_bom_matched / total_bom if total_bom else 0

                # 计算最终的3D零件匹配数
                final_parts_matched = sum(len(meshes) for meshes in final_bom_to_mesh.values())
                final_parts_rate = final_parts_matched / total_parts if total_parts else 0

                # 打印匹配汇总
                print_success(f"✅ 匹配完成 - 层级:{len(assembly_to_mesh)} + 代码:{code_bom_matched} + AI:{ai_bom_matched_count} = 总计:{total_bom_matched}/{total_bom}", indent=1)
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
                    "hierarchy_matched": len(assembly_to_mesh),  # ✅ 新增：层级匹配数量
                    "code_matched": code_bom_matched,
                    "ai_matched": ai_bom_matched_count,
                    "matching_rate": final_bom_rate,  # ✅ 兼容旧代码
                    "assembly_to_mesh": assembly_to_mesh,
                    "step_assembly_hierarchy": str(hierarchy_output) if hierarchy_output.exists() else None
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
            print_info(f"开始生成 GLB 清单，共 {len(glb_files)} 个 GLB 文件...")
            for key, glb_path in glb_files.items():
                print_info(f"  处理 {key}: {glb_path}", indent=1)
                inv = self.model_processor.generate_glb_inventory(
                    glb_path=glb_path,
                    output_path=None
                )
                if inv.get("success"):
                    print_info(f"    ✅ 节点数: {inv.get('nodes_total', 0)}, 几何体数: {inv.get('geometry_total', 0)}", indent=1)
                else:
                    print_warning(f"    ⚠️ 生成失败: {inv.get('error', '未知错误')}", indent=1)
                inventory[key] = inv

            inventory_path = Path(output_dir).parent / "step3_glb_inventory.json"
            print_info(f"保存到: {inventory_path}")
            with open(inventory_path, "w", encoding="utf-8") as f:
                json.dump({
                    "glb_files": inventory
                }, f, ensure_ascii=False, indent=2)
            print_success(f"GLB 清单已生成: {inventory_path.name}")
        except Exception as e:
            import traceback
            print_warning(f"生成 GLB 清单失败: {e}")
            print_warning(f"详细堆栈: {traceback.format_exc()}")
        
        return {
            "success": True,
            "component_level_mappings": component_level_mappings,
            "product_level_mapping": product_level_mapping,
            "glb_files": glb_files
        }

    # ---------- 装配层级辅助 ----------
    def _build_assembly_mesh_mapping(
        self,
        hierarchy: Dict,
        product_bom: List[Dict],
        cleaned_parts: List[Dict],
        nauo_edges: Optional[List[Dict]] = None,
        task_name: Optional[str] = None,
    ) -> Dict[str, List[str]]:
        """
        将子装配体（BOM项）映射到其所有叶子零件的 node_name 列表。

        ✅ v2.0.47 修复（面向未来的“父级上下文”层级匹配）：
        - 根因：仅凭“零件名/几何名”做全局匹配，会在同名件（如“防滑条”）场景下
          发生“串父级拿错NAUO” + “重复件只拿到1个实例”。
        - 新策略：优先使用 STEP 的 NAUO 父子边（nauo_edges）来确定“哪个父装配体下面有哪些 NAUO”，
          再结合 GLB parts_info 中真实 node_name 集合，将同一 NAUO 展开到 NAUOxxx、NAUOxxx_1 等重复实例。

        兼容策略：如果未提供 nauo_edges，则回退到旧的名称匹配逻辑（尽力而为）。
        """
        if not hierarchy or not product_bom or not cleaned_parts:
            return {}

        # 统一调试日志：记录 product_code 与装配层级键的匹配过程
        hierarchy_keys = list(hierarchy.keys())
        debug_log: List[Dict] = []
        debug_dir: Optional[Path] = None
        try:
            debug_dir = Path(build_debug_output_dir(task_name))
            debug_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            debug_dir = None

        def _format_record(detail: Dict) -> Dict:
            """统一输出字段，贴近 step2_bom_correction_log 的阅读习惯。"""
            product_code_orig = detail.get("product_code_orig", "")
            product_code_text = detail.get("product_code_text", product_code_orig)
            product_code_name = detail.get("product_code_name", "")
            decision = detail.get("decision")
            product_code_final = ""
            if decision == "keep":
                product_code_final = product_code_orig
            elif decision == "correct_to_text_pc":
                product_code_final = product_code_text
            elif decision == "correct_to_name_pc":
                product_code_final = product_code_name or product_code_orig

            assembly_key = detail.get("assembly_key_selected", "") or ""
            return {
                "seq": detail.get("seq"),
                "code": detail.get("bom_code"),
                "name": detail.get("bom_name"),
                "product_code_orig": product_code_orig,
                "product_code_text": product_code_text,
                "product_code_name": product_code_name,
                "product_code_final": product_code_final,
                "decision": decision,
                "reasons": detail.get("reasons", []),
                "assembly_key_selected": assembly_key,
                "code_hits": detail.get("candidates_by_code", []),
                "name_hits": detail.get("candidates_by_name", []),
                "mapped_nodes": detail.get("mapped_nodes", 0),
                "stage": detail.get("stage"),
            }

        def _write_debug_log():
            if not debug_dir:
                return
            try:
                summary = {
                    "total_bom": len(product_bom),
                    "mapped": sum(1 for r in debug_log if r.get("decision") == "mapped"),
                    "skipped": sum(1 for r in debug_log if r.get("decision") != "mapped"),
                    "has_nauo_edges": bool(nauo_edges),
                }
                log_path = debug_dir / "product_code_correction_log.json"
                with open(log_path, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "_comment": [
                                "产品级层级匹配纠正日志：记录 product_code(原值/OCR) 与 PDF 文本层值、名称交叉校验后的决策。字段含义对齐 step2_bom_correction_log：",
                                "  product_code_orig  -> 原值（OCR/大模型）",
                                "  product_code_text  -> PDF 文本层提取值（无则等于原值）",
                                "  product_code_name  -> 基于 name 在层级键名命中的推导值",
                                "  product_code_final -> 最终采用的值",
                                "  decision           -> keep(用原值) / correct_to_text_pc(用文本层值) / correct_to_name_pc(用名称命中层级键) / no_safe_pc(无层级匹配，跳过)",
                                "  reasons            -> 决策原因列表（如 use_text_pc, name_not_in_selected, skip_ambiguous_name 等）",
                                "  code_hits          -> 按 code（原值或文本层）命中的层级键列表",
                                "  name_hits          -> 按 BOM 名称命中的层级键列表（独立于 code，用于兜底或校验）"
                            ],
                            "summary": summary,
                            "records": [_format_record(d) for d in debug_log],
                        },
                        f,
                        ensure_ascii=False,
                        indent=2,
                    )
                print_info(f"产品级匹配日志已写入: {log_path}", indent=1)
            except Exception as e:
                print_warning(f"写产品级匹配日志失败: {e}", indent=1)

        def _select_assembly_key_with_guard(bom_item: Dict, stage: str) -> (Optional[str], Dict):
            """按 product_code + name 选择装配层级键，异常时放弃以避免串件；支持文本层回退。"""
            product_code_orig = str(bom_item.get("product_code") or "").strip()
            product_code_text = str(bom_item.get("product_code_text") or product_code_orig).strip()
            bom_name = str(bom_item.get("name") or "").strip()
            bom_code = str(bom_item.get("code") or "").strip()

            norm_product_code = self._normalize_token(product_code_orig)
            norm_product_code_text = self._normalize_token(product_code_text)
            bom_name_norm = self._normalize_token(bom_name)

            def _match_by_code(code_val: str) -> (Optional[str], List[str], bool):
                norm_code = self._normalize_token(code_val)
                candidates: List[str] = []
                if norm_code and len(norm_code) >= 8:
                    candidates = [k for k in hierarchy_keys if norm_code in self._normalize_token(k)]
                if not candidates:
                    code_token = self._extract_code_token(code_val)
                    if code_token:
                        candidates = [k for k in hierarchy_keys if code_token in self._normalize_token(k)]
                filtered = list(candidates)
                if bom_name_norm and filtered:
                    name_filtered = [c for c in filtered if bom_name_norm in self._normalize_token(c)]
                    if name_filtered:
                        filtered = name_filtered
                selected = max(filtered, key=len) if filtered else None
                name_in = bool(selected and bom_name_norm and bom_name_norm in self._normalize_token(selected))
                return selected, candidates, name_in

            reasons: List[str] = []
            # 尝试原始 code
            assembly_name, code_hits, name_in_selected = _match_by_code(product_code_orig)
            used_code = "orig"

            # 若原始 code 未命中或名称不符，尝试文本层 code（若与原值不同）
            if (not assembly_name or (bom_name_norm and not name_in_selected)) and product_code_text and product_code_text != product_code_orig:
                assembly_name, code_hits, name_in_selected = _match_by_code(product_code_text)
                used_code = "text"
                if assembly_name:
                    reasons.append("use_text_pc")

            # 名称候选（独立于 code）
            candidates_by_name: List[str] = []
            if bom_name_norm:
                candidates_by_name = [k for k in hierarchy_keys if bom_name_norm in self._normalize_token(k)]

            if assembly_name:
                reasons.append("code_match")
                if bom_name_norm and not name_in_selected:
                    reasons.append("name_not_in_selected")
                    if len(candidates_by_name) == 1:
                        assembly_name = candidates_by_name[0]
                        name_in_selected = True
                        used_code = "name"
                        reasons.append("name_override_unique")
                    elif len(candidates_by_name) == 0:
                        assembly_name = None
                        reasons.append("skip_no_name_match")
                    else:
                        assembly_name = None
                        reasons.append("skip_ambiguous_name")
            else:
                reasons.append("no_code_candidate")
                if len(candidates_by_name) == 1:
                    assembly_name = candidates_by_name[0]
                    name_in_selected = True
                    used_code = "name"
                    reasons.append("fallback_name_unique")

            decision = "no_safe_pc"
            product_code_name = ""
            if assembly_name:
                if used_code == "orig":
                    decision = "keep"
                elif used_code == "text":
                    decision = "correct_to_text_pc"
                else:
                    decision = "correct_to_name_pc"
                    product_code_name = assembly_name

            detail = {
                "stage": stage,
                "seq": bom_item.get("seq"),
                "bom_code": bom_code,
                "product_code_orig": product_code_orig,
                "product_code_text": product_code_text,
                "product_code_name": product_code_name,
                "bom_name": bom_name,
                "assembly_key_selected": assembly_name,
                "candidates_by_code": code_hits,
                "candidates_by_name": candidates_by_name,
                "name_in_selected": name_in_selected,
                "decision": decision,
                "reasons": reasons or ["noop"],
            }
            return assembly_name, detail

        # ---------- 优先：基于 NAUO 边（父级上下文）构建映射 ----------
        assembly_map: Dict[str, List[str]] = {}
        if nauo_edges:
            from collections import defaultdict

            # GLB 实例节点索引：base(NAUOxxx) -> [NAUOxxx, NAUOxxx_1, ...]
            nodes_by_base: Dict[str, List[str]] = defaultdict(list)
            node_names_set = set()
            for part in cleaned_parts:
                node = str(part.get("node_name") or "").strip()
                if not node:
                    continue
                node_names_set.add(node)
                base = node.split("_", 1)[0]
                nodes_by_base[base].append(node)

            # parent_name(装配体名) -> leaf node_name 列表
            # 只收集“叶子零件边”（child_name 不是装配体）来避免把中间装配体节点当作可高亮零件。
            parent_to_leaf_nodes: Dict[str, List[str]] = defaultdict(list)
            for edge in nauo_edges:
                try:
                    parent_name = str(edge.get("parent_name") or "").strip()
                    child_name = str(edge.get("child_name") or "").strip()
                    base_nauo = str(edge.get("nauo_name") or "").strip()
                except Exception:
                    continue

                if not parent_name or not child_name or not base_nauo:
                    continue

                # child_name 出现在 hierarchy key 中，说明它还是装配体（非叶子）
                if child_name in hierarchy:
                    continue

                # 将一个 STEP NAUO 展开到 GLB 的真实节点名（含 _1/_2 后缀）
                candidates = nodes_by_base.get(base_nauo, [])
                if not candidates and base_nauo in node_names_set:
                    candidates = [base_nauo]

                if not candidates:
                    continue

                parent_to_leaf_nodes[parent_name].extend(candidates)

            # descendant 装配体缓存：root -> {root及其所有子装配体}
            descendant_cache: Dict[str, set] = {}

            def _collect_descendant_assemblies(root_name: str) -> set:
                if root_name in descendant_cache:
                    return descendant_cache[root_name]

                visited = set()
                stack = [root_name]
                while stack:
                    current = stack.pop()
                    if current in visited:
                        continue
                    visited.add(current)
                    for child in hierarchy.get(current, []):
                        if child in hierarchy:
                            stack.append(child)
                descendant_cache[root_name] = visited
                return visited
            for bom in product_bom:
                bom_code = str(bom.get("code", "") or "").strip()
                if not bom_code:
                    continue

                assembly_name, detail = _select_assembly_key_with_guard(bom, stage="nauo")
                if not assembly_name:
                    debug_log.append(detail)
                    continue

                descendant_assemblies = _collect_descendant_assemblies(assembly_name)
                node_names = set()
                for asm_name in descendant_assemblies:
                    node_names.update(parent_to_leaf_nodes.get(asm_name, []))

                if node_names:
                    assembly_map[bom_code] = sorted(node_names)
                    detail["mapped_nodes"] = len(node_names)
                else:
                    detail["decision"] = "skipped"
                    detail["reasons"].append("no_leaf_nodes")
                debug_log.append(detail)

        # ---------- 回退：旧的“名称匹配”逻辑（尽力而为） ----------
        if assembly_map:
            _write_debug_log()
            return assembly_map

        # NAUO 未命中则回退名称匹配，日志重新开始避免重复记录
        if nauo_edges:
            debug_log = []

        # 建立几何名 -> node_name 的快速索引（含标准化）
        # 注意：bom_to_mesh 实际存储的是 node_name，不是 mesh_id
        from collections import defaultdict

        geom_to_nodes: Dict[str, List[str]] = defaultdict(list)
        norm_geom_to_nodes: Dict[str, List[str]] = defaultdict(list)

        for part in cleaned_parts:
            node_name = part.get("node_name")  # 使用 node_name
            if not node_name:
                continue

            names = [
                part.get("fixed_name") or "",
                part.get("geometry_name") or "",
                part.get("node_name") or "",
            ]
            for name in names:
                if not name:
                    continue
                geom_to_nodes[name].append(node_name)
                norm = self._normalize_token(name)
                if norm:
                    norm_geom_to_nodes[norm].append(node_name)

        assembly_map: Dict[str, List[str]] = {}

        for bom in product_bom:
            # 优先使用 product_code（因为层级key是产品代号+名称格式）
            product_code = bom.get("product_code", "")
            bom_code = bom.get("code", "")

            if not bom_code:
                continue

            assembly_name, detail = _select_assembly_key_with_guard(bom, stage="name_fallback")
            if not assembly_name:
                debug_log.append(detail)
                continue

            # 收集该子装配体的所有叶子零件对应的 node_name
            leaves = collect_leaf_parts(hierarchy, assembly_name)
            node_names: List[str] = []

            for leaf in leaves:
                matched_any = False

                # 方法1：直接匹配（可能有多个 node_name）
                if leaf in geom_to_nodes:
                    node_names.extend([n for n in geom_to_nodes[leaf] if n])
                    matched_any = True

                # 方法2：规范化匹配
                norm_leaf = self._normalize_token(leaf)
                if norm_leaf in norm_geom_to_nodes:
                    node_names.extend([n for n in norm_geom_to_nodes[norm_leaf] if n])
                    matched_any = True

                # 方法3：前缀匹配（处理 _1, _2 后缀）
                # 说明：即使“直接匹配”命中，也不能跳过此步骤，否则会只拿到一个实例，丢失重复件。
                for geom_name, nodes in geom_to_nodes.items():
                    base_geom = geom_name.rsplit("_", 1)[0] if "_" in geom_name else geom_name
                    if leaf == base_geom or leaf == geom_name:
                        node_names.extend([n for n in nodes if n])
                        matched_any = True

                # 方法4：代码片段匹配
                if not matched_any:
                    leaf_code = self._extract_code_token(leaf)
                    if leaf_code:
                        for norm_name, nodes in norm_geom_to_nodes.items():
                            if leaf_code in norm_name:
                                node_names.extend([n for n in nodes if n])
                            break

            if node_names:
                # 使用 bom_code 作为 key（与 ai_bom_to_mesh 格式一致）
                assembly_map[bom_code] = sorted(set(node_names))
                detail["mapped_nodes"] = len(assembly_map[bom_code])
            else:
                detail["decision"] = "skipped"
                detail["reasons"].append("no_leaf_nodes")
            debug_log.append(detail)

        _write_debug_log()
        return assembly_map

    def _normalize_token(self, text: str) -> str:
        """轻量级规范化：去除空白和常见分隔符，转小写。"""
        if not text:
            return ""
        return re.sub(r"[\s_\-]+", "", str(text)).lower()

    def _extract_code_token(self, text: str) -> str:
        """提取类似 E-CW3T-02 或 XX.XX.XXXX 的代码片段。"""
        if not text:
            return ""
        # 产品代码
        match = re.search(r"[A-Z]-[A-Z0-9]+-\d+(?:-\d+)?", str(text), re.IGNORECASE)
        if match:
            return match.group(0).lower()
        # BOM 代号格式 01.09.2549
        match = re.search(r"\d{2}\.\d{2}\.\d{4}", str(text))
        if match:
            return match.group(0).lower()
        return ""
    
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
