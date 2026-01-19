# -*- coding: utf-8 -*-
"""
Agent 5: 

"""

from typing import Dict, List
from agents.base_gemini_agent import BaseGeminiAgent
from prompts.agent_5_welding import build_welding_prompt


class WeldingAgent(BaseGeminiAgent):
    """"""
    
    def __init__(self, api_key: str = None, model_name: str = None, provider: str = "openrouter"):
        super().__init__(
            agent_name="Agent5_",
            api_key=api_key,
            temperature=0.1,
            model_name=model_name,
            provider=provider
        )
    
    def process(
        self,
        all_images: List[str],
        assembly_steps: List[Dict]
    ) -> Dict:
        """
        新逻辑：为每个装配步骤添加焊接要点（如果该步骤涉及焊接）

        Args:
            all_images: PDF图纸列表
            assembly_steps: Agent 3或Agent 4生成的装配步骤

        Returns:
            {
                "success": bool,
                "enhanced_steps": [...]  # 增强后的装配步骤（包含焊接信息）
            }
        """
        print(f"\n{'='*80}")
        print(f" Agent 5: 焊接工艺专家 - 为装配步骤添加焊接要点")
        print(f"{'='*80}")
        print(f" 📷 图纸数量: {len(all_images)}")
        print(f" 📋 装配步骤数量: {len(assembly_steps)}")

        # 构建prompt
        system_prompt, user_query = build_welding_prompt(assembly_steps)

        # 调用Gemini
        result = self.call_gemini(
            system_prompt=system_prompt,
            user_query=user_query,
            images=all_images
        )

        if result["success"]:
            parsed = result["result"]

            # 获取增强后的步骤
            enhanced_steps = parsed.get("enhanced_steps", [])

            # 统计焊接步骤数量
            welding_steps_count = sum(
                1 for step in enhanced_steps
                if step.get("welding", {}).get("required", False)
            )

            # ✅ 计算覆盖率
            coverage_rate = (welding_steps_count / len(enhanced_steps) * 100) if len(enhanced_steps) > 0 else 0

            # ✅ 统计焊接点数量
            total_welding_points = 0
            for step in enhanced_steps:
                welding_info = step.get("welding", {})
                if welding_info.get("required", False):
                    welding_points = welding_info.get("welding_points", [])
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
        else:
            print(f"\n ❌ 焊接分析失败: {result.get('error')}")
            return {
                "success": False,
                "error": result.get("error"),
                "enhanced_steps": assembly_steps,  # 返回原始步骤
                "total_steps": len(assembly_steps),
                "welding_steps_count": 0
            }

