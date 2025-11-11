# -*- coding: utf-8 -*-
"""
Agent 3:

"""

import re
from typing import Dict, List
from agents.base_gemini_agent import BaseGeminiAgent
from prompts.agent_3_component_assembly import build_component_assembly_prompt


class ComponentAssemblyAgent(BaseGeminiAgent):
    """"""

    def __init__(self, api_key: str = None):
        super().__init__(
            agent_name="Agent3_",
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
        component_plan: Dict,
        component_images: List[str],
        parts_list: List[Dict],
        bom_to_mesh_mapping: Dict = None,
        bom_mapping_table: List[Dict] = None,  # ✅ 新增：BOM映射宽表
        check_coverage: bool = True,  # ✅ 新增：是否检查BOM覆盖率
        min_coverage: float = 0.95,  # ✅ 新增：最低覆盖率要求（95%）
        max_retries: int = 2  # ✅ 新增：最大重试次数
    ) -> Dict:
        """
        生成组件装配步骤（带BOM覆盖率检查和重试机制）

        Args:
            component_plan: Agent 1的规划结果
            component_images: 组件图片
            parts_list: 组件内零件清单
            bom_to_mesh_mapping: BOM代号到mesh_id的映射（兼容旧代码）
            bom_mapping_table: BOM映射宽表（包含seq→code→mesh_id的完整链条）
            check_coverage: 是否检查BOM覆盖率
            min_coverage: 最低覆盖率要求（默认95%）
            max_retries: 最大重试次数（默认2次）

        Returns:
            {
                "success": bool,
                "component_code": str,
                "component_name": str,
                "assembly_steps": [...]
            }
        """
        component_name = component_plan.get("component_name", "")
        total_bom_count = len(parts_list)

        print(f"\n{'='*80}")
        print(f" Agent 3: 组件装配步骤生成 - {component_name}")
        print(f"{'='*80}")
        print(f" 图片数: {len(component_images)}")
        print(f" 零件数: {total_bom_count}")

        # 尝试生成（带重试）
        for attempt in range(max_retries + 1):
            if attempt > 0:
                print(f"\n{'='*60}")
                print(f"🔄 BOM覆盖率不足，开始第{attempt}次重试...")
                print(f"{'='*60}")

            # 构建提示词
            system_prompt, user_query = build_component_assembly_prompt(
                component_plan=component_plan,
                parts_list=parts_list
            )

            # 如果是重试，添加反馈信息
            if attempt > 0 and check_coverage:
                feedback = f"""

⚠️ 重要提醒：上一次生成的步骤BOM覆盖率只有{coverage_rate:.1%}，未达到{min_coverage:.0%}的要求。

未覆盖的BOM项：
{uncovered_bom_list}

请重新生成装配步骤，确保100%覆盖所有BOM项。每个BOM项都必须在某个步骤的parts_used中出现。
                """
                user_query = user_query + feedback

            # 调用AI生成步骤（使用重试机制）
            result = self.call_gemini_with_retry(
                system_prompt=system_prompt,
                user_query=user_query,
                images=component_images,
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

            # 检查BOM覆盖率
            if check_coverage:
                covered_bom_seqs = set()
                for step in assembly_steps:
                    for part in step.get("parts_used", []):
                        bom_seq = part.get("bom_seq")
                        if bom_seq:
                            covered_bom_seqs.add(str(bom_seq))

                covered_count = len(covered_bom_seqs)
                coverage_rate = covered_count / total_bom_count if total_bom_count > 0 else 0

                print(f"\n  📋 BOM覆盖率: {covered_count}/{total_bom_count} ({coverage_rate:.1%})")

                if coverage_rate >= min_coverage:
                    print(f"  ✅ BOM覆盖率达标")
                    return {
                        "success": True,
                        "component_code": component_plan.get("component_code"),
                        "component_name": component_name,
                        "assembly_steps": assembly_steps,
                        "raw_result": parsed
                    }
                else:
                    # 找出未覆盖的BOM
                    all_bom_seqs = {str(i+1) for i in range(total_bom_count)}
                    uncovered_seqs = all_bom_seqs - covered_bom_seqs
                    uncovered_bom_list = "\n".join([
                        f"  - BOM序号{seq}: {parts_list[int(seq)-1].get('name', 'N/A')}"
                        for seq in sorted(uncovered_seqs, key=int)
                    ])

                    print(f"  ⚠️ 有 {len(uncovered_seqs)} 个BOM未覆盖")

                    if attempt < max_retries:
                        print(uncovered_bom_list)
                        continue
                    else:
                        print(f"\n  ❌ 重试{max_retries}次后，BOM覆盖率仍未达标")
                        print(uncovered_bom_list)
                        return {
                            "success": True,  # 仍然返回成功，但覆盖率不足
                            "component_code": component_plan.get("component_code"),
                            "component_name": component_name,
                            "assembly_steps": assembly_steps,
                            "raw_result": parsed,
                            "coverage_warning": f"BOM覆盖率{coverage_rate:.1%}未达标"
                        }
            else:
                # 不检查覆盖率，直接返回
                return {
                    "success": True,
                    "component_code": component_plan.get("component_code"),
                    "component_name": component_name,
                    "assembly_steps": assembly_steps,
                    "raw_result": parsed
                }

        # 所有尝试都失败
        return {
            "success": False,
            "error": "所有尝试都失败",
            "component_code": component_plan.get("component_code"),
            "component_name": component_name,
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
        code_to_name = {}

        # 构建seq到node_names的映射（备用）
        seq_to_nodes = {}
        seq_to_code = {}
        seq_to_name = {}

        for item in bom_mapping_table:
            seq = str(item.get("seq", ""))
            code = item.get("code", "")
            node_names = item.get("node_names", [])
            name = item.get("name", "")

            # 通过code映射（主要方式，因为Gemini生成的bom_code是准确的）
            if code and node_names:
                code_to_nodes[code] = node_names
                code_to_seq[code] = seq
                code_to_name[code] = name

            # 通过seq映射（备用方式）
            if seq and node_names:
                seq_to_nodes[seq] = node_names
                seq_to_code[seq] = code
                seq_to_name[seq] = name

        # 遍历步骤，添加node_name
        for step in assembly_steps:
            parts_used = step.get("parts_used", [])
            for part in parts_used:
                bom_code = part.get("bom_code", "")
                bom_seq = str(part.get("bom_seq", ""))

                # ✅ 优先通过bom_code查找（因为Gemini识别的code是准确的）
                if bom_code and bom_code in code_to_nodes:
                    part["node_name"] = code_to_nodes[bom_code]
                    # 同时更新bom_seq（修正AI可能看错的图纸标号）
                    if bom_code in code_to_seq:
                        part["bom_seq"] = code_to_seq[bom_code]
                    # 验证bom_name
                    ai_name = self.normalize_bom_name(part.get("bom_name", ""))
                    actual_name = self.normalize_bom_name(code_to_name.get(bom_code, ""))
                    if ai_name != actual_name:
                        print(f"   ⚠️  BOM代号{bom_code}的名称不匹配: AI生成='{part.get('bom_name')}', 实际='{code_to_name.get(bom_code)}'")

                # ✅ 备用：通过bom_seq查找（如果code不存在或未匹配）
                elif bom_seq and bom_seq in seq_to_nodes:
                    part["node_name"] = seq_to_nodes[bom_seq]
                    # 填充bom_code字段
                    if "bom_code" not in part or not part["bom_code"]:
                        part["bom_code"] = seq_to_code[bom_seq]
                    # 验证bom_name
                    ai_name = self.normalize_bom_name(part.get("bom_name", ""))
                    actual_name = self.normalize_bom_name(seq_to_name.get(bom_seq, ""))
                    if ai_name != actual_name:
                        print(f"   ⚠️  BOM序号{bom_seq}的名称不匹配: AI生成='{part.get('bom_name')}', 实际='{seq_to_name.get(bom_seq)}'")

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
            bom_to_mesh_mapping: BOM代号到mesh_id的映射

        Returns:
            添加了mesh_id的装配步骤
        """
        for step in assembly_steps:
            parts_used = step.get("parts_used", [])
            for part in parts_used:
                bom_code = part.get("bom_code", "")
                if bom_code in bom_to_mesh_mapping:
                    part["mesh_id"] = bom_to_mesh_mapping[bom_code]

        return assembly_steps

