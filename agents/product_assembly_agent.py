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

    def __init__(self, api_key: str = None, model_name: str = None, provider: str = "openrouter"):
        super().__init__(
            agent_name="Agent4_",
            api_key=api_key,
            temperature=0.1,
            model_name=model_name,
            provider=provider
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
        last_coverage_rate = None
        last_uncovered_bom_list = ""

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
                product_bom=product_bom or []
            )

            # 如果是重试，添加反馈信息
            if attempt > 0 and check_coverage and product_bom:
                if last_coverage_rate is not None:
                    list_text = last_uncovered_bom_list or "（未生成明细）"
                    feedback = f"""

⚠️ 重要提醒：上一次生成的步骤产品级BOM覆盖率只有{last_coverage_rate:.1%}，未达到{min_coverage:.0%}的要求。

未覆盖的产品级BOM项（前20个）：
{list_text}

请重新生成装配步骤，尽量提高BOM覆盖率。重点关注组件连接时需要的紧固件（螺栓、螺母、垫圈等）。
                    """
                else:
                    feedback = """

⚠️ 重要提醒：上一次生成未能计算产品级BOM覆盖率，请尽量覆盖所有BOM项。

请重新生成装配步骤，尽量提高BOM覆盖率。重点关注组件连接时需要的紧固件（螺栓、螺母、垫圈等）。
                    """
                user_query = user_query + feedback

            # 调用AI生成步骤（使用重试机制）
            result = self.call_gemini_with_retry(
                system_prompt=system_prompt,
                user_query=user_query,
                images=product_images,
                max_retries=3  # JSON解析失败时重试3次
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

                    last_coverage_rate = coverage_rate
                    last_uncovered_bom_list = uncovered_bom_list

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

        for item in bom_mapping_table:
            seq = str(item.get("seq", ""))
            code = item.get("code", "")
            node_names = item.get("node_names", [])

            # 通过code映射（主要方式）
            if code and node_names:
                code_to_nodes[code] = node_names
                code_to_seq[code] = seq

            # 通过seq映射（备用方式）
            if seq and node_names:
                seq_to_nodes[seq] = node_names
                seq_to_code[seq] = code

        # 遍历步骤，添加node_name
        for step in assembly_steps:
            # 处理主要组件（components）
            components = step.get("components", [])
            for comp in components:
                bom_code = comp.get("bom_code", "")
                bom_seq = str(comp.get("bom_seq", ""))

                # 优先通过bom_code查找
                if bom_code and bom_code in code_to_nodes:
                    comp["node_name"] = code_to_nodes[bom_code]
                    if bom_code in code_to_seq:
                        comp["bom_seq"] = code_to_seq[bom_code]
                # 备用：通过bom_seq查找
                elif bom_seq and bom_seq in seq_to_nodes:
                    comp["node_name"] = seq_to_nodes[bom_seq]
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
                    if bom_code in code_to_seq:
                        fastener["bom_seq"] = code_to_seq[bom_code]
                # 备用：通过bom_seq查找
                elif bom_seq and bom_seq in seq_to_nodes:
                    fastener["node_name"] = seq_to_nodes[bom_seq]
                    if "bom_code" not in fastener or not fastener["bom_code"]:
                        fastener["bom_code"] = seq_to_code[bom_seq]

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

