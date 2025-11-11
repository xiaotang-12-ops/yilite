#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
融合推理专家 - DeepSeek模型按照设计文档要求进行融合推理
"""

import os
import json
from typing import Dict, List, Any, Optional
from openai import OpenAI


class FusionExpertModel:
    """融合推理专家模型 - 严格按照设计文档实现"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY is required")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com"
        )
        
        # 设计文档中的系统提示词
        self.system_prompt = """你是"机械装配与工艺规划汇总器"。

输入是一份来自"视觉通道/文本通道"的候选事实 JSON（已包含 BOM 行、技术要求、尺寸/孔距、焊接/形位符号、视图和表格的证据定位）。

你的任务：

1. 实体归并与冲突调解：同一字段存在多候选时，按来源权重（BOM 表>技术要求文本>视觉识别）与一致性选择"主事实"，其余保留在 alternatives。
2. 构建部件层级与连接关系：输出 parts[]、connections[]（焊/螺/过盈/定位）。
3. 生成装配计划：assembly_plan.sequence[] 给出可执行工艺动作（定位/点焊/全焊/矫形/打磨/喷涂/紧固）与检验点。
4. 质检计划与风险：qc_plan 写明关键尺寸/焊缝抽检与方法；risks 标出热变形/喷涂遮蔽等。
5. 溯源与置信度：每条结论必须包含 evidence{page_id, region或row_id} 与 confidence(0~1)。
6. 严禁臆造：缺失数据写入 unknowns 与 questions_to_ask；不得自造标准/扭矩/膜厚。
7. 严格遵守输出 Schema，先输出 JSON，随后用不超过 10 行中文给出要点摘要。

来源权重建议：BOM表 0.9 > 技术要求 0.8 > 视觉图像 0.7；多来源一致+0.1；跨视图互证+0.05；异常降权（乱码、单位异常、几何冲突）。"""
    
    def fuse_candidate_facts(self, candidate_facts: Dict[str, Any]) -> Dict[str, Any]:
        """
        融合候选事实，生成装配规范JSON
        
        Args:
            candidate_facts: 双通道解析的候选事实JSON
            
        Returns:
            装配规范JSON
        """
        print("🧠 DeepSeek融合推理中...")
        
        try:
            # 构建用户查询
            user_query = f"""请对以下候选事实JSON进行融合推理，输出装配规范JSON：

{json.dumps(candidate_facts, ensure_ascii=False, indent=2)}

请严格按照装配规范JSON Schema输出，包含：
- doc_meta: 文档元信息
- extracted: 提取的原始信息
- parts: 零件信息
- connections: 连接关系
- assembly_plan: 装配计划
- qc_plan: 质检计划
- risks: 风险分析
- unknowns: 未知信息
- questions_to_ask: 需要确认的问题
- traceability: 溯源信息

请先输出完整的JSON，然后用不超过10行中文总结要点。"""
            
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_query}
                ],
                temperature=0.1,
                max_tokens=8000,
                stream=False
            )
            
            content = response.choices[0].message.content
            
            # 解析JSON部分
            assembly_spec = self._extract_json_from_response(content)
            
            if assembly_spec:
                print("✅ 融合推理完成")
                return {
                    "success": True,
                    "assembly_spec": assembly_spec,
                    "summary": self._extract_summary_from_response(content),
                    "raw_response": content
                }
            else:
                print("❌ 融合推理失败：无法解析JSON")
                return {
                    "success": False,
                    "error": "无法解析装配规范JSON",
                    "raw_response": content
                }
                
        except Exception as e:
            print(f"❌ 融合推理异常: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """从响应中提取JSON部分"""
        try:
            # 查找JSON代码块
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "{" in response and "}" in response:
                # 查找第一个完整的JSON对象
                start = response.find("{")
                brace_count = 0
                end = start
                
                for i in range(start, len(response)):
                    if response[i] == "{":
                        brace_count += 1
                    elif response[i] == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            end = i + 1
                            break
                
                json_str = response[start:end]
            else:
                return None
            
            return json.loads(json_str)
            
        except Exception as e:
            print(f"⚠️ JSON解析失败: {e}")
            return None
    
    def _extract_summary_from_response(self, response: str) -> str:
        """从响应中提取总结部分"""
        try:
            # 查找JSON后的总结
            if "```" in response:
                last_code_block = response.rfind("```")
                summary_start = response.find("\n", last_code_block) + 1
                summary = response[summary_start:].strip()
            else:
                # 如果没有代码块，查找JSON后的内容
                json_end = response.rfind("}")
                if json_end > 0:
                    summary = response[json_end + 1:].strip()
                else:
                    summary = "无总结"
            
            return summary[:500]  # 限制长度
            
        except Exception:
            return "总结提取失败"
    
    def validate_assembly_spec(self, assembly_spec: Dict[str, Any]) -> Dict[str, Any]:
        """验证装配规范JSON的完整性"""
        required_fields = [
            "doc_meta", "extracted", "parts", "connections", 
            "assembly_plan", "qc_plan", "risks", "unknowns", 
            "questions_to_ask", "traceability"
        ]
        
        validation_result = {
            "valid": True,
            "missing_fields": [],
            "warnings": []
        }
        
        # 检查必需字段
        for field in required_fields:
            if field not in assembly_spec:
                validation_result["missing_fields"].append(field)
                validation_result["valid"] = False
        
        # 检查关键内容
        if "parts" in assembly_spec and len(assembly_spec["parts"]) == 0:
            validation_result["warnings"].append("零件列表为空")
        
        if "assembly_plan" in assembly_spec:
            plan = assembly_spec["assembly_plan"]
            if "sequence" not in plan or len(plan["sequence"]) == 0:
                validation_result["warnings"].append("装配步骤为空")
        
        return validation_result
    
    def generate_assembly_spec_template(self) -> Dict[str, Any]:
        """生成装配规范JSON模板"""
        return {
            "doc_meta": {
                "drawing_no": "unknown",
                "rev": "unknown", 
                "pages": []
            },
            "extracted": {
                "tech_requirements": [],
                "bom_table": []
            },
            "parts": [],
            "connections": [],
            "assembly_plan": {
                "sequence": [],
                "fixtures": [],
                "safety_notes": []
            },
            "qc_plan": {
                "kpcs": [],
                "ndt": []
            },
            "risks": [],
            "unknowns": [],
            "questions_to_ask": [],
            "traceability": []
        }
