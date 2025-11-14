# -*- coding: utf-8 -*-
"""
Agent 4:

"""

import re
from typing import Dict, List
from agents.base_gemini_agent import BaseGeminiAgent
from prompts.agent_4_product_assembly import build_product_assembly_prompt


class ProductAssemblyAgent(BaseGeminiAgent):
    """"""

    def __init__(self, api_key: str = None):
        super().__init__(
            agent_name="Agent4_",
            api_key=api_key,
            temperature=0.1
        )

    @staticmethod
    def normalize_bom_name(name: str) -> str:
        """
        标准化BOM名称：去除末尾的数量后缀

        例如：
        - "连接板 1" -> "连接板"
        - "方形板-机加 4" -> "方形板-机加"
        - "矩形管 1" -> "矩形管"

        Args:
            name: 原始BOM名称

        Returns:
            标准化后的名称
        """
        if not name:
            return ""
        # 去除末尾的"空格+数字"（数字是数量，不是名称的一部分）
        return re.sub(r'\s+\d+$', '', name).strip()
    
    def process(
        self,
        product_plan: Dict,
        product_images: List[str],
        components_list: List[Dict],
        product_bom: List[Dict] = None,  # ✅ 新增：产品级BOM
        component_bom_items: List[Dict] = None,  # ✅ 新增：子组件的BOM项
        part_bom_items: List[Dict] = None,  # ✅ 新增：零件的BOM项
        bom_to_mesh_mapping: Dict = None,  # ✅ 新增：BOM-3D映射（兼容旧代码）
        bom_mapping_table: List[Dict] = None,  # ✅ 新增：BOM映射宽表
        check_coverage: bool = True,  # ✅ 新增：是否检查BOM覆盖率
        min_coverage: float = 0.80,  # ✅ 新增：最低覆盖率要求（产品级80%即可，因为有很多标准件）
        max_retries: int = 2  # ✅ 新增：最大重试次数
    ) -> Dict:
        """
        生成产品总装步骤（带BOM覆盖率检查和重试机制）

        Args:
            product_plan: Agent 1的规划结果
            product_images: 产品总图图片
            components_list: 组件列表
            product_bom: 产品级BOM列表（从产品总图提取的零件）
            bom_to_mesh_mapping: BOM代号到mesh_id的映射（兼容旧代码）
            bom_mapping_table: BOM映射宽表（包含seq→code→mesh_id的完整链条）
            check_coverage: 是否检查BOM覆盖率
            min_coverage: 最低覆盖率要求（默认80%，产品级允许较低因为有很多标准件）
            max_retries: 最大重试次数（默认2次）

        Returns:
            {
                "success": bool,
                "product_name": str,
                "assembly_steps": [...]  # 装配步骤
            }
        """
        product_name = product_plan.get("product_name", "")
        total_bom_count = len(product_bom) if product_bom else 0

        print(f"\n{'='*80}")
        print(f" Agent 4: 产品总装步骤生成 - {product_name}")
        print(f"{'='*80}")
        print(f" 图片数: {len(product_images)}")
        print(f" 组件数: {len(components_list)}")
        if product_bom:
            print(f" 产品级BOM: {total_bom_count}")

        # 尝试生成（带重试）
        for attempt in range(max_retries + 1):
            if attempt > 0:
                print(f"\n{'='*60}")
                print(f"🔄 BOM覆盖率不足，开始第{attempt}次重试...")
                print(f"{'='*60}")

            # 构建提示词
            system_prompt, user_query = build_product_assembly_prompt(
                product_plan=product_plan,
                components_list=components_list,
                product_bom=product_bom or [],
                component_bom_items=component_bom_items or [],  # ✅ 新增：子组件BOM
                part_bom_items=part_bom_items or []  # ✅ 新增：零件BOM
            )

            # 如果是重试，添加反馈信息
            if attempt > 0 and check_coverage and product_bom:
                feedback = f"""

⚠️ 重要提醒：上一次生成的步骤产品级BOM覆盖率只有{coverage_rate:.1%}，未达到{min_coverage:.0%}的要求。

未覆盖的产品级BOM项（前20个）：
{uncovered_bom_list}

请重新生成装配步骤，尽量提高BOM覆盖率。重点关注组件连接时需要的紧固件（螺栓、螺母、垫圈等）。
                """
                user_query = user_query + feedback

            # 调用AI生成步骤（使用重试机制）
            result = self.call_gemini_with_retry(
                system_prompt=system_prompt,
                user_query=user_query,
                images=product_images,
                max_retries=2  # JSON解析失败时重试2次（避免过多API调用）
            )

            if not result["success"]:
                print(f"\n❌ 生成失败: {result.get('error')}")
                continue

            parsed = result["result"]
            assembly_steps = parsed.get("assembly_steps", [])

            # ✅ 使用BOM映射宽表添加mesh_id
            if bom_mapping_table:
                assembly_steps = self._add_mesh_ids_from_table(assembly_steps, bom_mapping_table)
            elif bom_to_mesh_mapping:
                assembly_steps = self._add_mesh_ids(assembly_steps, bom_to_mesh_mapping)

            print(f"\n✅ 生成结果:")
            print(f"   - 步骤数: {len(assembly_steps)}")

            # ✅ 验证3d_highlight字段
            missing_highlight_steps = []
            for step in assembly_steps:
                if "3d_highlight" not in step or not step["3d_highlight"]:
                    missing_highlight_steps.append(step.get("step_number", "?"))

            if missing_highlight_steps:
                print(f"   ⚠️  以下步骤缺少3d_highlight字段: {missing_highlight_steps}")
            else:
                print(f"   ✅ 所有步骤都包含3d_highlight字段")

            # ✅ 自动生成3d_highlight（如果AI没生成）
            assembly_steps = self._auto_generate_3d_highlight(assembly_steps)

            # 检查产品级BOM覆盖率
            if check_coverage and product_bom and total_bom_count > 0:
                covered_bom_seqs = set()
                for step in assembly_steps:
                    # 检查fasteners字段
                    for fastener in step.get("fasteners", []):
                        bom_seq = fastener.get("bom_seq")
                        if bom_seq:
                            covered_bom_seqs.add(str(bom_seq))
                    # 检查components字段
                    for comp in step.get("components", []):
                        bom_seq = comp.get("bom_seq")
                        if bom_seq:
                            covered_bom_seqs.add(str(bom_seq))

                covered_count = len(covered_bom_seqs)
                coverage_rate = covered_count / total_bom_count

                print(f"\n  📋 产品级BOM覆盖率: {covered_count}/{total_bom_count} ({coverage_rate:.1%})")

                if coverage_rate >= min_coverage:
                    print(f"  ✅ BOM覆盖率达标")
                    return {
                        "success": True,
                        "product_name": product_name,
                        "assembly_steps": assembly_steps,
                        "raw_result": parsed
                    }
                else:
                    # 找出未覆盖的BOM
                    all_bom_seqs = {str(i+1) for i in range(total_bom_count)}
                    uncovered_seqs = all_bom_seqs - covered_bom_seqs
                    # 只显示前20个未覆盖的BOM
                    uncovered_list = sorted(uncovered_seqs, key=int)[:20]
                    uncovered_bom_list = "\n".join([
                        f"  - BOM序号{seq}: {product_bom[int(seq)-1].get('name', 'N/A')}"
                        for seq in uncovered_list
                    ])

                    print(f"  ⚠️ 有 {len(uncovered_seqs)} 个产品级BOM未覆盖")

                    if attempt < max_retries:
                        print(uncovered_bom_list)
                        continue
                    else:
                        print(f"\n  ❌ 重试{max_retries}次后，BOM覆盖率仍未达标")
                        print(uncovered_bom_list)
                        return {
                            "success": True,  # 仍然返回成功，但覆盖率不足
                            "product_name": product_name,
                            "assembly_steps": assembly_steps,
                            "raw_result": parsed,
                            "coverage_warning": f"产品级BOM覆盖率{coverage_rate:.1%}未达标"
                        }
            else:
                # 不检查覆盖率，直接返回
                return {
                    "success": True,
                    "product_name": product_name,
                    "assembly_steps": assembly_steps,
                    "raw_result": parsed
                }

        # 所有尝试都失败
        return {
            "success": False,
            "error": "所有尝试都失败",
            "product_name": product_name,
            "assembly_steps": []
        }

    def _add_mesh_ids_from_table(
        self,
        assembly_steps: List[Dict],
        bom_mapping_table: List[Dict]
    ) -> List[Dict]:
        """
        ✅ 使用BOM映射宽表添加node_name（直接使用node_name，不再使用mesh_id）

        Args:
            assembly_steps: 装配步骤列表
            bom_mapping_table: BOM映射宽表

        Returns:
            添加了node_name的装配步骤
        """
        # 构建code到node_names的映射（主要）
        code_to_nodes = {}
        code_to_seq = {}

        # 构建seq到node_names的映射（备用）
        seq_to_nodes = {}
        seq_to_code = {}

        # ✅ 统计总的node_name数量
        total_node_names = 0

        for item in bom_mapping_table:
            seq = str(item.get("seq", ""))
            code = item.get("code", "")
            node_names = item.get("node_names", [])

            # 通过code映射（主要方式）
            if code and node_names:
                code_to_nodes[code] = node_names
                code_to_seq[code] = seq
                total_node_names += len(node_names)

            # 通过seq映射（备用方式）
            if seq and node_names:
                seq_to_nodes[seq] = node_names
                seq_to_code[seq] = code

        # ✅ 打印日志，强调node_name来源
        print(f"\n{'='*80}")
        print(f"📍 从BOM映射表中加载node_name数据:")
        print(f"   - BOM映射表项数: {len(bom_mapping_table)}")
        print(f"   - 可用的BOM代号: {len(code_to_nodes)}")
        print(f"   - 可用的BOM序号: {len(seq_to_nodes)}")
        print(f"   - 总node_name数量: {total_node_names}")
        print(f"{'='*80}\n")

        # 遍历步骤，添加node_name
        total_added_nodes = 0  # ✅ 统计添加的node_name数量

        for step_idx, step in enumerate(assembly_steps, 1):
            step_added_nodes = 0  # 当前步骤添加的node_name数量

            # 处理主要组件（components）
            components = step.get("components", [])
            for comp in components:
                bom_code = comp.get("bom_code", "")
                bom_seq = str(comp.get("bom_seq", ""))

                # 优先通过bom_code查找
                if bom_code and bom_code in code_to_nodes:
                    comp["node_name"] = code_to_nodes[bom_code]
                    step_added_nodes += len(code_to_nodes[bom_code])
                    if bom_code in code_to_seq:
                        comp["bom_seq"] = code_to_seq[bom_code]
                # 备用：通过bom_seq查找
                elif bom_seq and bom_seq in seq_to_nodes:
                    comp["node_name"] = seq_to_nodes[bom_seq]
                    step_added_nodes += len(seq_to_nodes[bom_seq])
                    if "bom_code" not in comp or not comp["bom_code"]:
                        comp["bom_code"] = seq_to_code[bom_seq]

            # 处理紧固件（fasteners）
            fasteners = step.get("fasteners", [])
            for fastener in fasteners:
                bom_code = fastener.get("bom_code", "")
                bom_seq = str(fastener.get("bom_seq", ""))

                # 优先通过bom_code查找
                if bom_code and bom_code in code_to_nodes:
                    fastener["node_name"] = code_to_nodes[bom_code]
                    step_added_nodes += len(code_to_nodes[bom_code])
                    if bom_code in code_to_seq:
                        fastener["bom_seq"] = code_to_seq[bom_code]
                # 备用：通过bom_seq查找
                elif bom_seq and bom_seq in seq_to_nodes:
                    fastener["node_name"] = seq_to_nodes[bom_seq]
                    step_added_nodes += len(seq_to_nodes[bom_seq])
                    if "bom_code" not in fastener or not fastener["bom_code"]:
                        fastener["bom_code"] = seq_to_code[bom_seq]

            # ✅ 打印每个步骤添加的node_name数量
            if step_added_nodes > 0:
                print(f"   步骤{step_idx}: 从BOM映射表添加了 {step_added_nodes} 个node_name")

            total_added_nodes += step_added_nodes

        # ✅ 打印总结
        print(f"\n✅ 总共从BOM映射表添加了 {total_added_nodes} 个node_name到装配步骤中\n")

        return assembly_steps

    def _auto_generate_3d_highlight(self, assembly_steps: List[Dict]) -> List[Dict]:
        """
        验证和修正3d_highlight字段（强制验证所有步骤）

        规则：
        - 步骤1：3d_highlight = 所有子组件的所有node_name
        - 步骤2-N：3d_highlight = 当前步骤的零件的所有node_name

        Args:
            assembly_steps: 装配步骤列表

        Returns:
            验证和修正后的装配步骤
        """
        print(f"\n  🎨 验证和修正产品装配的3D高亮字段...")

        # ✅ 第一步：检测并删除重复的组件安装步骤
        print(f"\n  🔍 检测重复的组件安装步骤...")

        # 收集步骤1中的所有组件的bom_code和bom_name
        component_codes_in_step1 = set()
        component_names_in_step1 = set()

        if len(assembly_steps) > 0:
            step1 = assembly_steps[0]
            for comp in step1.get("components", []):
                bom_code = comp.get("bom_code", "")
                bom_name = comp.get("bom_name", "")
                if bom_code:
                    component_codes_in_step1.add(bom_code)
                if bom_name:
                    component_names_in_step1.add(bom_name)

            if component_codes_in_step1 or component_names_in_step1:
                print(f"   📋 步骤1包含{len(component_codes_in_step1)}个子组件（通过bom_code识别）")

        # 检测步骤2-N中是否有重复的组件
        steps_to_remove = []
        for i in range(1, len(assembly_steps)):
            step = assembly_steps[i]
            step_number = step.get('step_number', i+1)
            components = step.get("components", [])

            if not components:
                continue

            # 检查这些components是否在步骤1中已经出现过
            components_to_remove = []
            for j, comp in enumerate(components):
                bom_code = comp.get("bom_code", "")
                bom_name = comp.get("bom_name", "")

                # 如果bom_code或bom_name在步骤1中已经出现过，标记删除
                if (bom_code and bom_code in component_codes_in_step1) or \
                   (bom_name and bom_name in component_names_in_step1):
                    print(f"   ⚠️  步骤{step_number}的components中包含了步骤1中已经放置的组件: {bom_code or bom_name} - {bom_name}")
                    components_to_remove.append(j)

            # 删除重复的components
            for j in reversed(components_to_remove):
                del components[j]

            # 如果删除后components和fasteners都为空，标记删除整个步骤
            if not components and not step.get("fasteners"):
                print(f"   ❌ 步骤{step_number}的components和fasteners都为空，将删除整个步骤")
                steps_to_remove.append(i)
            elif components_to_remove:
                print(f"   ✅ 步骤{step_number}删除了{len(components_to_remove)}个重复的组件，保留fasteners")

        # 删除标记的步骤
        if steps_to_remove:
            print(f"\n   🗑️  删除{len(steps_to_remove)}个重复的组件安装步骤")
            for i in reversed(steps_to_remove):
                del assembly_steps[i]

            # 重新编号所有步骤
            print(f"   🔢 重新编号所有步骤...")
            for i, step in enumerate(assembly_steps, 1):
                step["step_number"] = i
                step["step_id"] = f"product_step_{i}"

            print(f"   ✅ 删除后剩余{len(assembly_steps)}个步骤")
        else:
            print(f"   ✅ 未发现重复的组件安装步骤")

        # ✅ 第二步：验证和修正3d_highlight字段
        print(f"\n  🎨 验证和修正3D高亮字段...")

        for i, step in enumerate(assembly_steps):
            step_number = step.get('step_number', i+1)

            # 自动生成正确的3d_highlight
            correct_highlight_nodes = []

            # 收集当前步骤的所有node_name
            # 1. 从components中收集
            for comp in step.get("components", []):
                node_names = comp.get("node_name", [])
                if isinstance(node_names, list):
                    correct_highlight_nodes.extend(node_names)
                elif node_names:
                    correct_highlight_nodes.append(node_names)

            # 2. 从fasteners中收集
            for fastener in step.get("fasteners", []):
                node_names = fastener.get("node_name", [])
                if isinstance(node_names, list):
                    correct_highlight_nodes.extend(node_names)
                elif node_names:
                    correct_highlight_nodes.append(node_names)

            # 去重
            correct_highlight_nodes = list(dict.fromkeys(correct_highlight_nodes))

            # 检查AI生成的3d_highlight是否正确
            ai_highlight = step.get("3d_highlight", [])

            # 比较AI生成的和正确的3d_highlight（使用集合比较，忽略顺序）
            if set(ai_highlight) != set(correct_highlight_nodes):
                # 不一致，需要修正
                print(f"   ⚠️  步骤{step_number}的3d_highlight不正确，已自动修正")
                print(f"      - AI生成的({len(ai_highlight)}个): {ai_highlight[:5]}{'...' if len(ai_highlight) > 5 else ''}")
                print(f"      - 正确的({len(correct_highlight_nodes)}个): {correct_highlight_nodes[:5]}{'...' if len(correct_highlight_nodes) > 5 else ''}")
                step["3d_highlight"] = correct_highlight_nodes
            else:
                # 一致，无需修正
                if ai_highlight:
                    print(f"   ✅ 步骤{step_number}的3d_highlight正确({len(ai_highlight)}个node_name)")
                else:
                    print(f"   ✅ 步骤{step_number}自动生成3d_highlight({len(correct_highlight_nodes)}个node_name)")
                    step["3d_highlight"] = correct_highlight_nodes

        return assembly_steps

    def _add_mesh_ids(
        self,
        assembly_steps: List[Dict],
        bom_to_mesh_mapping: Dict
    ) -> List[Dict]:
        """
        旧方法：使用BOM代号添加mesh_id（兼容旧代码）

        Args:
            assembly_steps: 装配步骤列表
            bom_to_mesh_mapping: BOM代号到mesh_id的映射表

        Returns:
            添加了mesh_id的装配步骤
        """
        for step in assembly_steps:
            # 处理主要组件（components）
            components = step.get("components", [])
            for comp in components:
                bom_code = comp.get("bom_code", "")
                if bom_code in bom_to_mesh_mapping:
                    comp["mesh_id"] = bom_to_mesh_mapping[bom_code]

            # 处理紧固件（fasteners）
            fasteners = step.get("fasteners", [])
            for fastener in fasteners:
                bom_code = fastener.get("bom_code", "")
                if bom_code in bom_to_mesh_mapping:
                    fastener["mesh_id"] = bom_to_mesh_mapping[bom_code]

        return assembly_steps

