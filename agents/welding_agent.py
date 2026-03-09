# -*- coding: utf-8 -*-
"""
Agent 5: 焊接工艺增强
"""

from copy import deepcopy
from typing import Any, Dict, List, Optional
from agents.base_gemini_agent import BaseGeminiAgent
from prompts.agent_5_welding import build_welding_prompt

WELDING_REQUEST_TIMEOUT_SECONDS = 1800
WELDING_SDK_MAX_RETRIES = 0
WELDING_TEXT_LIMIT = 240


def _to_text(value: Any, max_len: int = WELDING_TEXT_LIMIT) -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
    if len(text) > max_len:
        return text[:max_len]
    return text


def _to_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except Exception:
        return None


class WeldingAgent(BaseGeminiAgent):
    """焊接智能体（精简输入+增量输出，避免大 JSON 往返）。"""

    def __init__(
        self,
        api_key: str = None,
        model_name: str = None,
        fallback_model_name: str = None,
        provider: str = "openrouter"
    ):
        super().__init__(
            agent_name="Agent5_",
            api_key=api_key,
            temperature=0.1,
            model_name=model_name,
            fallback_model_name=fallback_model_name,
            provider=provider,
            request_timeout_seconds=WELDING_REQUEST_TIMEOUT_SECONDS,
            sdk_max_retries=WELDING_SDK_MAX_RETRIES,
        )

    def _build_compact_steps(self, assembly_steps: List[Dict]) -> List[Dict[str, Any]]:
        compact_steps: List[Dict[str, Any]] = []
        for index, step in enumerate(assembly_steps, start=1):
            if not isinstance(step, dict):
                continue
            step_id = _to_text(step.get("step_id") or f"step_{index}", 64)
            description = step.get("description") or step.get("operation") or ""
            compact_steps.append(
                {
                    "step_id": step_id,
                    "step_number": step.get("step_number", index),
                    "title": _to_text(step.get("title"), 80),
                    "description": _to_text(description, 280),
                    "quality_check": _to_text(step.get("quality_check"), 120),
                }
            )
        return compact_steps

    def _normalize_welding_data(self, annotation: Dict[str, Any]) -> Dict[str, Any]:
        raw_welding = annotation.get("welding")
        welding: Dict[str, Any] = raw_welding if isinstance(raw_welding, dict) else {}

        # 兼容模型把字段扁平输出到 annotation 顶层
        for key in (
            "welding_type",
            "welding_method",
            "weld_size",
            "welding_position",
            "quality_requirements",
            "safety_notes",
            "welding_points",
        ):
            if key not in welding and annotation.get(key) is not None:
                welding[key] = annotation.get(key)

        cleaned: Dict[str, Any] = {}
        for key, value in welding.items():
            if isinstance(value, list):
                compact_list = [_to_text(item, 120) for item in value if _to_text(item, 120)]
                if compact_list:
                    cleaned[key] = compact_list
            else:
                text = _to_text(value, 180)
                if text:
                    cleaned[key] = text

        cleaned["required"] = True
        return cleaned

    def _merge_welding_annotations(
        self, assembly_steps: List[Dict], annotations: List[Dict[str, Any]]
    ) -> List[Dict]:
        enhanced_steps = deepcopy(assembly_steps)
        by_step_id: Dict[str, Dict[str, Any]] = {}
        by_step_number: Dict[int, Dict[str, Any]] = {}

        for item in annotations:
            if not isinstance(item, dict):
                continue
            step_id = _to_text(item.get("step_id"), 64)
            step_number = _to_int(item.get("step_number"))
            if step_id:
                by_step_id[step_id] = item
            if step_number is not None:
                by_step_number[step_number] = item

        for index, step in enumerate(enhanced_steps, start=1):
            if not isinstance(step, dict):
                continue

            step_id = _to_text(step.get("step_id"), 64)
            step_number = _to_int(step.get("step_number")) or index
            annotation = by_step_id.get(step_id) or by_step_number.get(step_number)
            if not annotation:
                continue

            required = bool(annotation.get("required", False))
            if required:
                step["welding"] = self._normalize_welding_data(annotation)
            else:
                step.pop("welding", None)

        return enhanced_steps

    def process(
        self,
        all_images: List[str],
        assembly_steps: List[Dict]
    ) -> Dict:
        """
        为装配步骤添加焊接要点（如果该步骤涉及焊接）。
        输入/输出都采用增量结构，减少 token 与响应体体积。
        """
        print(f"\n{'='*80}")
        print(" Agent 5: 焊接工艺专家 - 为装配步骤添加焊接要点")
        print(f"{'='*80}")
        print(f" 📷 图纸数量: {len(all_images)}")
        print(f" 📋 装配步骤数量: {len(assembly_steps)}")

        compact_steps = self._build_compact_steps(assembly_steps)
        print(f" 🧾 发送精简步骤字段: {len(compact_steps)} 条")

        system_prompt, user_query = build_welding_prompt(compact_steps)
        result = self.call_gemini(
            system_prompt=system_prompt,
            user_query=user_query,
            images=all_images
        )

        if not result["success"]:
            print(f"\n ❌ 焊接分析失败: {result.get('error')}")
            return {
                "success": False,
                "error": result.get("error"),
                "enhanced_steps": assembly_steps,
                "total_steps": len(assembly_steps),
                "welding_steps_count": 0
            }

        parsed = result["result"]
        annotations: List[Dict[str, Any]] = []
        enhanced_steps: Optional[List[Dict]] = None

        # 兼容旧格式：模型直接返回 enhanced_steps
        if isinstance(parsed, list):
            enhanced_steps = parsed
        elif isinstance(parsed, dict):
            legacy_steps = parsed.get("enhanced_steps")
            if isinstance(legacy_steps, list):
                enhanced_steps = legacy_steps
            candidate_annotations = parsed.get("welding_annotations")
            if isinstance(candidate_annotations, list):
                annotations = [item for item in candidate_annotations if isinstance(item, dict)]

        # 新格式：只返回按步骤增量标注，本地合并回原步骤
        if enhanced_steps is None:
            if not annotations:
                error = f"焊接输出结构异常，未找到 welding_annotations，实际为: {type(parsed).__name__}"
                print(f"\n ❌ 焊接分析失败: {error}")
                return {
                    "success": False,
                    "error": error,
                    "enhanced_steps": assembly_steps,
                    "total_steps": len(assembly_steps),
                    "welding_steps_count": 0
                }
            enhanced_steps = self._merge_welding_annotations(assembly_steps, annotations)

        welding_steps_count = sum(
            1 for step in enhanced_steps
            if isinstance(step, dict) and step.get("welding", {}).get("required", False)
        )
        coverage_rate = (welding_steps_count / len(enhanced_steps) * 100) if enhanced_steps else 0

        total_welding_points = 0
        for step in enhanced_steps:
            if not isinstance(step, dict):
                continue
            welding_info = step.get("welding", {})
            if welding_info.get("required", False):
                welding_points = welding_info.get("welding_points", [])
                if isinstance(welding_points, list):
                    total_welding_points += len(welding_points)

        print(f"\n ✅ 焊接分析完成:")
        print(f"   - 总步骤数: {len(enhanced_steps)}")
        print(f"   - 涉及焊接的步骤: {welding_steps_count}")
        print(f"   - 焊接覆盖率: {coverage_rate:.1f}%")
        if total_welding_points > 0:
            print(f"   - 总焊接点数: {total_welding_points}")

        return {
            "success": True,
            "enhanced_steps": enhanced_steps,
            "total_steps": len(enhanced_steps),
            "welding_steps_count": welding_steps_count,
            "coverage_rate": coverage_rate,
            "total_welding_points": total_welding_points,
            "raw_result": parsed
        }

