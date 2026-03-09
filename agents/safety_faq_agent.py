# -*- coding: utf-8 -*-
"""
Agent 6: 安全警告增强
"""

from copy import deepcopy
from typing import Any, Dict, List, Optional
from agents.base_gemini_agent import BaseGeminiAgent
from prompts.agent_6_safety_faq import build_safety_faq_prompt

SAFETY_REQUEST_TIMEOUT_SECONDS = 1200
SAFETY_SDK_MAX_RETRIES = 0
SAFETY_TEXT_LIMIT = 240


def _to_text(value: Any, max_len: int = SAFETY_TEXT_LIMIT) -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
    if len(text) > max_len:
        return text[:max_len]
    return text


def _to_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except Exception:
        return None


class SafetyFAQAgent(BaseGeminiAgent):
    """安全智能体（精简输入+增量输出，减少 token 消耗）。"""

    def __init__(
        self,
        api_key: str = None,
        model_name: str = None,
        fallback_model_name: str = None,
        provider: str = "openrouter"
    ):
        super().__init__(
            agent_name="Agent6_FAQ",
            api_key=api_key,
            temperature=0.15,
            model_name=model_name,
            fallback_model_name=fallback_model_name,
            provider=provider,
            request_timeout_seconds=SAFETY_REQUEST_TIMEOUT_SECONDS,
            sdk_max_retries=SAFETY_SDK_MAX_RETRIES,
        )

    def _build_compact_steps(self, assembly_steps: List[Dict]) -> List[Dict[str, Any]]:
        compact_steps: List[Dict[str, Any]] = []
        for index, step in enumerate(assembly_steps, start=1):
            if not isinstance(step, dict):
                continue
            welding = step.get("welding") if isinstance(step.get("welding"), dict) else {}
            welding_hint = " / ".join(
                [value for value in [_to_text(welding.get("welding_type"), 40), _to_text(welding.get("welding_position"), 80)] if value]
            )
            compact_steps.append(
                {
                    "step_id": _to_text(step.get("step_id") or f"step_{index}", 64),
                    "step_number": step.get("step_number", index),
                    "title": _to_text(step.get("title"), 80),
                    "description": _to_text(step.get("description") or step.get("operation"), 280),
                    "quality_check": _to_text(step.get("quality_check"), 120),
                    "has_welding": bool(welding.get("required", False)),
                    "welding_hint": welding_hint,
                }
            )
        return compact_steps

    def _normalize_faq_items(self, faq_items: Any) -> List[Dict[str, str]]:
        if not isinstance(faq_items, list):
            return []
        normalized: List[Dict[str, str]] = []
        for item in faq_items:
            if not isinstance(item, dict):
                continue
            question = _to_text(item.get("question"), 120)
            answer = _to_text(item.get("answer"), 260)
            if question and answer:
                normalized.append({"question": question, "answer": answer})
            if len(normalized) >= 6:
                break
        return normalized

    def _merge_safety_annotations(
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

            raw_warnings = annotation.get("safety_warnings")
            if raw_warnings is None:
                raw_warnings = annotation.get("warnings")
            warnings = []
            if isinstance(raw_warnings, list):
                warnings = [_to_text(item, 120) for item in raw_warnings if _to_text(item, 120)]

            warnings = warnings[:2]
            if warnings:
                step["safety_warnings"] = warnings
            else:
                step.pop("safety_warnings", None)

        return enhanced_steps

    def process(
        self,
        assembly_steps: List[Dict]
    ) -> Dict:
        """
        为每个装配步骤补充安全警告（按步骤增量返回，本地合并）。
        """
        print(f"\n{'='*80}")
        print("  Agent 6: 安全专家 - 为装配步骤添加安全警告和FAQ")
        print(f"{'='*80}")
        print(f" 📋 装配步骤数量: {len(assembly_steps)}")

        compact_steps = self._build_compact_steps(assembly_steps)
        print(f" 🧾 发送精简步骤字段: {len(compact_steps)} 条")

        system_prompt, user_query = build_safety_faq_prompt(
            assembly_steps=compact_steps
        )

        result = self.call_gemini(
            system_prompt=system_prompt,
            user_query=user_query,
            images=None
        )

        if not result["success"]:
            print(f"\n ❌ 安全分析失败: {result.get('error')}")
            return {
                "success": False,
                "error": result.get("error"),
                "enhanced_steps": assembly_steps,
                "faq_items": [],
                "total_steps": len(assembly_steps),
                "safety_steps_count": 0
            }

        parsed = result["result"]
        enhanced_steps: Optional[List[Dict]] = None
        annotations: List[Dict[str, Any]] = []
        faq_items: List[Dict[str, str]] = []

        # 兼容旧格式
        if isinstance(parsed, list):
            enhanced_steps = parsed
        elif isinstance(parsed, dict):
            legacy_steps = parsed.get("enhanced_steps")
            if isinstance(legacy_steps, list):
                enhanced_steps = legacy_steps
            candidate_annotations = parsed.get("safety_annotations")
            if isinstance(candidate_annotations, list):
                annotations = [item for item in candidate_annotations if isinstance(item, dict)]
            faq_items = self._normalize_faq_items(parsed.get("faq_items", []))

        if enhanced_steps is None:
            if not annotations:
                return {
                    "success": False,
                    "error": "安全分析结果结构异常",
                    "enhanced_steps": assembly_steps,
                    "faq_items": [],
                    "total_steps": len(assembly_steps),
                    "safety_steps_count": 0
                }
            enhanced_steps = self._merge_safety_annotations(assembly_steps, annotations)

        safety_steps_count = sum(
            1 for step in enhanced_steps
            if isinstance(step, dict) and isinstance(step.get("safety_warnings"), list) and len(step.get("safety_warnings")) > 0
        )
        coverage_rate = (safety_steps_count / len(enhanced_steps) * 100) if enhanced_steps else 0

        total_warnings = 0
        for step in enhanced_steps:
            if not isinstance(step, dict):
                continue
            warnings = step.get("safety_warnings", [])
            if isinstance(warnings, list):
                total_warnings += len(warnings)

        print(f"\n ✅ 安全分析完成:")
        print(f"   - 总步骤数: {len(enhanced_steps)}")
        print(f"   - 有安全警告的步骤: {safety_steps_count}")
        print(f"   - 安全覆盖率: {coverage_rate:.1f}%")
        if total_warnings > 0:
            print(f"   - 总安全警告数: {total_warnings}")
        print(f"   - FAQ条目: {len(faq_items)}")

        return {
            "success": True,
            "enhanced_steps": enhanced_steps,
            "faq_items": faq_items,
            "total_steps": len(enhanced_steps),
            "safety_steps_count": safety_steps_count,
            "coverage_rate": coverage_rate,
            "total_warnings": total_warnings,
            "raw_result": parsed
        }

