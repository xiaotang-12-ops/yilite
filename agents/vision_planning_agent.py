# -*- coding: utf-8 -*-
"""
Agent 1: 

"""

from typing import Dict, List
from agents.base_gemini_agent import BaseGeminiAgent
from prompts.agent_1_vision_planning import build_simple_assembly_planning_prompt


class VisionPlanningAgent(BaseGeminiAgent):
    """"""
    
    def __init__(self, api_key: str = None):
        super().__init__(
            agent_name="Agent1_",
            api_key=api_key,
            temperature=0.1
        )
    
    def process(
        self,
        all_images: List[str],
        bom_data: List[Dict],
        expected_component_count: int = None
    ) -> Dict:
        """


        Args:
            all_images: PDF
            bom_data: BOM
            expected_component_count: 期望的组件数量（从文件系统识别出的组件图数量）

        Returns:
            {
                "success": bool,
                "component_assembly_plan": [...],  #
                "product_assembly_plan": {...}     #
            }
        """
        print(f"\n{'='*80}")
        print(f" Agent 1:  - ")
        print(f"{'='*80}")
        print(f" : {len(all_images)}")
        print(f" BOM: {len(bom_data)}")
        if expected_component_count:
            print(f" : {expected_component_count}")

        #
        system_prompt, user_query = build_simple_assembly_planning_prompt(bom_data, expected_component_count)

        # Gemini
        result = self.call_gemini(
            system_prompt=system_prompt,
            user_query=user_query,
            images=all_images
        )
        
        if result["success"]:
            parsed = result["result"]
            
            # 
            component_plan = parsed.get("component_assembly_plan", [])
            product_plan = parsed.get("product_assembly_plan", {})
            
            print(f"\n :")
            print(f"   - : {len(component_plan)}")
            print(f"   - : {product_plan.get('base_component_name', 'N/A')}")
            
            return {
                "success": True,
                "component_assembly_plan": component_plan,
                "product_assembly_plan": product_plan,
                "raw_result": parsed
            }
        else:
            print(f"\n : {result.get('error')}")
            return {
                "success": False,
                "error": result.get("error"),
                "component_assembly_plan": [],
                "product_assembly_plan": {}
            }

