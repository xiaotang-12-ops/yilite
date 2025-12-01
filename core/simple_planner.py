"""SimplePlanner: 用代码替代 Agent1 规划，按 BOM 序号排序。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from utils.time_utils import beijing_now


@dataclass
class ComponentPlan:
    component_code: str
    component_name: str
    assembly_order: int
    drawing_number: str
    base_part_code: str
    base_part_name: str
    base_part_seq: str
    base_part_material: str
    base_part_quantity: int
    assembly_steps: List[Dict]


class SimplePlanner:
    """
    简化装配规划器

    规则：
    - 基准件 = BOM 序号最小的零件（seq 最小）
    - 装配顺序 = BOM 序号从小到大
    - 产品基准组件 = BOM 序号最小的组焊件/组件
    """

    def __init__(self):
        pass

    def _sort_bom(self, bom_data: List[Dict]) -> List[Dict]:
        def _seq(item):
            try:
                return int(item.get("seq", 9999))
            except Exception:
                return 9999

        return sorted(bom_data, key=_seq)

    def generate_component_plan(
        self, pdf_stem: str, bom_data: List[Dict], drawing_index: Optional[int] = None
    ) -> ComponentPlan:
        if not bom_data:
            raise ValueError(f"BOM数据为空: {pdf_stem}")

        sorted_bom = self._sort_bom(bom_data)
        base_part = sorted_bom[0]

        return ComponentPlan(
            component_code=pdf_stem,
            component_name=pdf_stem,
            assembly_order=drawing_index or 1,
            drawing_number=str(drawing_index or 1),
            base_part_code=base_part.get("code", ""),
            base_part_name=base_part.get("name", ""),
            base_part_seq=str(base_part.get("seq", "1")),
            base_part_material=base_part.get("material", ""),
            base_part_quantity=int(base_part.get("quantity", 1) or 1),
            assembly_steps=[],
        )

    def generate_product_plan(self, pdf_stem: str, bom_data: List[Dict]) -> Dict:
        sorted_bom = self._sort_bom(bom_data)
        sub_assemblies = [item for item in sorted_bom if self._is_sub_assembly(item)]
        if not sub_assemblies:
            # 兜底：没有子装配时，仍然生成一个包含所有BOM的简单计划
            # 基准件使用BOM序号最小的零件
            base_part = sorted_bom[0] if sorted_bom else {}
            return {
                "product_name": pdf_stem,
                "base_component_code": base_part.get("code", ""),
                "base_component_name": base_part.get("name", ""),
                "base_component_seq": str(base_part.get("seq", "1")),
                "base_component_drawing_number": base_part.get("drawing_number", ""),
                "assembly_sequence": [],
                "component_assembly_plan": [],
                "generated_by": "SimplePlanner",
                "generation_time": beijing_now().isoformat(),
            }

        base_component = sub_assemblies[0]

        component_plans = []
        for i, comp in enumerate(sub_assemblies, 1):
            component_plans.append(
                {
                    "component_code": comp.get("code", ""),
                    "component_name": comp.get("name", ""),
                    "assembly_order": i,
                    "drawing_number": str(i),
                    "bom_seq": str(comp.get("seq", "")),
                }
            )

        return {
            "product_name": pdf_stem,
            "base_component_code": base_component.get("code", ""),
            "base_component_name": base_component.get("name", ""),
            "base_component_seq": str(base_component.get("seq", "1")),
            "base_component_drawing_number": base_component.get("drawing_number", ""),
            "assembly_sequence": [],
            "component_assembly_plan": component_plans,
            "generated_by": "SimplePlanner",
            "generation_time": beijing_now().isoformat(),
        }

    def _is_sub_assembly(self, bom_item: Dict) -> bool:
        material = (bom_item.get("material") or "").lower()
        name = (bom_item.get("name") or "").lower()
        keywords = ["组焊件", "组件", "assembly", "assy", "weldment"]
        return any(kw in material or kw in name for kw in keywords)
