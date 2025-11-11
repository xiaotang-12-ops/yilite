# -*- coding: utf-8 -*-
"""
Agent 6: FAQ
FAQ
"""

from typing import Dict, List
from agents.base_gemini_agent import BaseGeminiAgent
from prompts.agent_6_safety_faq import build_safety_faq_prompt


class SafetyFAQAgent(BaseGeminiAgent):
    """FAQ"""
    
    def __init__(self, api_key: str = None):
        super().__init__(
            agent_name="Agent6_FAQ",
            api_key=api_key,
            temperature=0.2  # 
        )
    
    def process(
        self,
        assembly_steps: List[Dict]
    ) -> Dict:
        """
        新逻辑：为每个装配步骤添加安全警告和FAQ（如果该步骤有安全风险）

        Args:
            assembly_steps: Agent 5增强后的装配步骤（已包含焊接信息）

        Returns:
            {
                "success": bool,
                "enhanced_steps": [...],  # 增强后的装配步骤（包含安全警告）
                "faq_items": [...]        # 全局FAQ列表
            }
        """
        print(f"\n{'='*80}")
        print(f"  Agent 6: 安全专家 - 为装配步骤添加安全警告和FAQ")
        print(f"{'='*80}")
        print(f" 📋 装配步骤数量: {len(assembly_steps)}")

        # 构建prompt
        system_prompt, user_query = build_safety_faq_prompt(
            assembly_steps=assembly_steps
        )

        # 调用Gemini
        result = self.call_gemini(
            system_prompt=system_prompt,
            user_query=user_query,
            images=None
        )

        if result["success"]:
            parsed = result["result"]

            # 获取增强后的步骤和FAQ
            enhanced_steps = parsed.get("enhanced_steps", [])
            faq_items = parsed.get("faq_items", [])

            # 统计有安全警告的步骤数量
            safety_steps_count = sum(
                1 for step in enhanced_steps
                if step.get("safety_warnings") and len(step.get("safety_warnings", [])) > 0
            )

            # ✅ 计算覆盖率
            coverage_rate = (safety_steps_count / len(enhanced_steps) * 100) if len(enhanced_steps) > 0 else 0

            # ✅ 统计安全警告总数
            total_warnings = 0
            for step in enhanced_steps:
                warnings = step.get("safety_warnings", [])
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
        else:
            print(f"\n ❌ 安全分析失败: {result.get('error')}")
            return {
                "success": False,
                "error": result.get("error"),
                "enhanced_steps": assembly_steps,  # 返回原始步骤
                "faq_items": [],
                "total_steps": len(assembly_steps),
                "safety_steps_count": 0
            }

