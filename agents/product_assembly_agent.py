# -*- coding: utf-8 -*-
"""
Agent 4:

"""

import re
from typing import Dict, List, Optional
from agents.base_gemini_agent import BaseGeminiAgent
from prompts.agent_4_product_assembly import build_product_assembly_prompt


class ProductAssemblyAgent(BaseGeminiAgent):
    """"""

    def __init__(
        self,
        api_key: str = None,
        model_name: str = None,
        fallback_model_name: str = None,
        provider: str = "openrouter"
    ):
        super().__init__(
            agent_name="Agent4_",
            api_key=api_key,
            temperature=0.1,
            model_name=model_name,
            fallback_model_name=fallback_model_name,
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
        min_coverage: float = 0.70,  # ✅ 低于70%才阻断，70%以上继续生成并提示
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
            min_coverage: 最低覆盖率要求（默认70%，低于该值才阻断）
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
        target_coverage = max(min_coverage, 0.95)  # 目标覆盖率（低于该值会继续重试优化）
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

⚠️ 重要提醒：上一次生成的“有效覆盖率（有node_name才算覆盖）”只有{last_coverage_rate:.1%}，未达到{target_coverage:.0%}的目标。

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

            # ✅ 数量对齐：以匹配结果为准，避免模型在描述中“猜数量”
            if bom_mapping_table:
                assembly_steps, correction_stats = self._align_step_quantities(assembly_steps, bom_mapping_table)
                corrected = correction_stats.get("item_corrections", 0)
                if corrected:
                    print(
                        "   ⚠️ 数量已自动对齐："
                        f"修正 {corrected} 个条目（步骤 {correction_stats.get('step_corrections', 0)} 个）"
                    )

            print(f"\n✅ 生成结果:")
            print(f"   - 步骤数: {len(assembly_steps)}")

            # 检查产品级BOM覆盖率
            if check_coverage and product_bom and total_bom_count > 0:
                covered_bom_seqs = set()
                covered_bom_with_nodes = set()
                for step in assembly_steps:
                    # 检查fasteners字段
                    for fastener in step.get("fasteners", []):
                        bom_seq = str(fastener.get("bom_seq") or "").strip()
                        if bom_seq:
                            covered_bom_seqs.add(bom_seq)
                            if self._has_valid_node_names(fastener.get("node_name")):
                                covered_bom_with_nodes.add(bom_seq)
                    # 检查components字段
                    for comp in step.get("components", []):
                        bom_seq = str(comp.get("bom_seq") or "").strip()
                        if bom_seq:
                            covered_bom_seqs.add(bom_seq)
                            if self._has_valid_node_names(comp.get("node_name")):
                                covered_bom_with_nodes.add(bom_seq)

                covered_count_seq = len(covered_bom_seqs)
                covered_count_nodes = len(covered_bom_with_nodes)
                coverage_rate_seq = covered_count_seq / total_bom_count
                coverage_rate_nodes = covered_count_nodes / total_bom_count
                effective_coverage = min(coverage_rate_seq, coverage_rate_nodes)

                print(
                    f"\n  📋 产品级BOM覆盖率(按序号): {covered_count_seq}/{total_bom_count} ({coverage_rate_seq:.1%})"
                )
                print(
                    f"  📋 产品级BOM覆盖率(有节点): {covered_count_nodes}/{total_bom_count} ({coverage_rate_nodes:.1%})"
                )
                print(f"  📋 有效覆盖率(取较低值): {effective_coverage:.1%}")

                if effective_coverage >= target_coverage:
                    print(f"  ✅ BOM覆盖率达标")
                    return {
                        "success": True,
                        "product_name": product_name,
                        "assembly_steps": assembly_steps,
                        "raw_result": parsed
                    }
                else:
                    # 找出未覆盖或缺少node_name的BOM（按有节点口径）
                    all_bom_seqs = {str(i+1) for i in range(total_bom_count)}
                    uncovered_seqs = all_bom_seqs - covered_bom_with_nodes
                    # 只显示前20个未覆盖的BOM
                    uncovered_list = sorted(uncovered_seqs, key=int)[:20]
                    missing_node_but_present = sorted(
                        covered_bom_seqs - covered_bom_with_nodes,
                        key=int
                    )[:20]
                    uncovered_bom_list = "\n".join([
                        f"  - BOM序号{seq}: {product_bom[int(seq)-1].get('name', 'N/A')}"
                        for seq in uncovered_list
                    ])
                    if missing_node_but_present:
                        uncovered_bom_list += "\n\n仅有序号但缺少node_name的BOM（前20个）：\n"
                        uncovered_bom_list += "\n".join([
                            f"  - BOM序号{seq}: {product_bom[int(seq)-1].get('name', 'N/A')}"
                            for seq in missing_node_but_present
                        ])

                    last_coverage_rate = effective_coverage
                    last_uncovered_bom_list = uncovered_bom_list

                    print(f"  ⚠️ 有 {len(uncovered_seqs)} 个产品级BOM未有效覆盖（按有节点口径）")

                    if attempt < max_retries:
                        print(uncovered_bom_list)
                        continue
                    else:
                        print(f"\n  ⚠️ 重试{max_retries}次后，有效覆盖率仍未达到目标{target_coverage:.0%}")
                        print(uncovered_bom_list)
                        if effective_coverage < min_coverage:
                            return {
                                "success": False,
                                "error": f"有效覆盖率{effective_coverage:.1%}低于阻断阈值{min_coverage:.0%}",
                                "product_name": product_name,
                                "assembly_steps": assembly_steps,
                                "raw_result": parsed,
                                "coverage_warning": f"有效覆盖率{effective_coverage:.1%}低于{min_coverage:.0%}"
                            }

                        # >=70% 时继续产出，但带明确警告
                        return {
                            "success": True,
                            "product_name": product_name,
                            "assembly_steps": assembly_steps,
                            "raw_result": parsed,
                            "coverage_warning": (
                                f"有效覆盖率{effective_coverage:.1%}未达目标{target_coverage:.0%}，"
                                f"但高于阻断阈值{min_coverage:.0%}，已继续生成"
                            )
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

    @staticmethod
    def _safe_int(value, default: Optional[int] = 0) -> Optional[int]:
        """安全整数转换，失败时返回默认值。"""
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _has_valid_node_names(node_name) -> bool:
        """判断条目是否携带有效 node_name（空数组/空字符串都算无效）。"""
        if isinstance(node_name, list):
            return any(str(node).strip() for node in node_name if node is not None)
        return bool(str(node_name or "").strip())

    def _build_quantity_reference(self, bom_mapping_table: List[Dict]) -> Dict[str, Dict]:
        """
        构建数量权威映射：
        - seq -> {bom_qty, node_count}
        - code_unique -> {bom_qty, node_count}（仅 code 唯一时可回退）
        """
        by_seq: Dict[str, Dict] = {}
        code_candidates: Dict[str, List[Dict]] = {}

        for item in bom_mapping_table or []:
            seq = str(item.get("seq", "")).strip()
            code = str(item.get("code", "")).strip()
            bom_qty = self._safe_int(item.get("quantity"), 0) or 0
            node_count = len(item.get("node_names", []) or [])

            ref = {
                "seq": seq,
                "code": code,
                "bom_qty": bom_qty,
                "node_count": node_count,
            }

            if seq:
                by_seq[seq] = ref
            if code:
                code_candidates.setdefault(code, []).append(ref)

        # code 可能不唯一，仅保留唯一 code 作为回退查询
        by_code_unique = {
            code: refs[0]
            for code, refs in code_candidates.items()
            if len(refs) == 1
        }

        return {
            "by_seq": by_seq,
            "by_code_unique": by_code_unique,
        }

    def _resolve_target_quantity(
        self,
        item: Dict,
        qty_ref: Dict[str, Dict],
        prefer_node_count: bool,
    ) -> Optional[int]:
        """解析条目的目标数量。"""
        bom_seq = str(item.get("bom_seq", "")).strip()
        bom_code = str(item.get("bom_code", "")).strip()

        ref = None
        if bom_seq and bom_seq in qty_ref["by_seq"]:
            ref = qty_ref["by_seq"][bom_seq]
        elif bom_code and bom_code in qty_ref["by_code_unique"]:
            ref = qty_ref["by_code_unique"][bom_code]

        if not ref:
            return None

        bom_qty = ref.get("bom_qty", 0)
        node_count = ref.get("node_count", 0)

        # 数量以 BOM 为权威值，避免“匹配漏了 -> 步骤数量被悄悄改小”。
        # node_count 仅作为 BOM 数量缺失时的兜底。
        if bom_qty > 0:
            return bom_qty
        if node_count > 0:
            return node_count
        return None

    def _sync_description_quantity(self, description: str, target_qty: int) -> str:
        """同步描述中的数量词，避免字段与文案口径不一致。"""
        if not description:
            return description

        text = description
        patterns = [
            r"(取)\d+(个|件)",
            r"(安装)\d+(个|件)",
            r"(共安装)\d+(个|件)",
            r"(共)\d+(个|件)",
            r"(为)\d+(个)",
        ]

        for pattern in patterns:
            new_text = re.sub(
                pattern,
                lambda m: f"{m.group(1)}{target_qty}{m.group(2)}",
                text,
                count=1,
            )
            if new_text != text:
                return new_text

        return text

    def _align_step_quantities(
        self,
        assembly_steps: List[Dict],
        bom_mapping_table: List[Dict],
    ) -> tuple[List[Dict], Dict[str, int]]:
        """
        对齐步骤数量，避免模型输出数量与匹配结果不一致。
        """
        qty_ref = self._build_quantity_reference(bom_mapping_table)

        item_corrections = 0
        step_corrections = 0

        for step in assembly_steps:
            step_changed = False
            primary_target_qty = None

            for field, prefer_node_count in (("components", False), ("fasteners", True)):
                for item in step.get(field, []) or []:
                    target_qty = self._resolve_target_quantity(item, qty_ref, prefer_node_count=prefer_node_count)
                    if target_qty is None:
                        continue

                    current_qty = self._safe_int(item.get("quantity"), None)
                    if current_qty != target_qty:
                        item["quantity"] = target_qty
                        item_corrections += 1
                        step_changed = True
                        if primary_target_qty is None:
                            primary_target_qty = target_qty

            if step_changed:
                step_corrections += 1
                if primary_target_qty is not None:
                    step["description"] = self._sync_description_quantity(
                        step.get("description", ""),
                        primary_target_qty,
                    )

        return assembly_steps, {
            "item_corrections": item_corrections,
            "step_corrections": step_corrections,
        }

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

