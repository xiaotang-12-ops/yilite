# -*- coding: utf-8 -*-

"""

DeepSeek装配专家模型调用模块

专业的机械装配与焊接工艺专家

"""



import os

import json

from typing import Dict, List, Optional, Any

from openai import OpenAI

from prompts.assembly_expert_prompts import build_assembly_expert_prompt, build_user_input





class AssemblyExpertModel:

    """DeepSeek装配专家模型封装类"""

    

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):

        """

        初始化DeepSeek装配专家模型



        Args:

            api_key: DeepSeek API Key，如果不提供则从环境变量获取

            model_name: 模型名称（可选，默认从config.py读取）

        """

        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")

        if not self.api_key:

            raise ValueError("请设置DEEPSEEK_API_KEY环境变量或传入api_key参数")



        self.client = OpenAI(

            api_key=self.api_key,

            base_url="https://api.deepseek.com"

        )



        # ✅ Bug修复：从config.py读取模型名称

        if model_name:

            self.model_name = model_name

        else:

            try:

                from config import MODEL_CONFIG

                self.model_name = MODEL_CONFIG["deepseek"]

            except ImportError:

                self.model_name = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")



    @staticmethod

    def _parse_json_from_content(content: str) -> Dict[str, Any]:

        """从模型响应中提取JSON数据"""

        if not content or not content.strip():

            raise ValueError('DeepSeek返回内容为空')



        cleaned = content.strip()

        json_start = cleaned.find('{')

        json_end = cleaned.rfind('}')



        if json_start == -1 or json_end == -1 or json_end <= json_start:

            raise ValueError('DeepSeek返回内容不包含有效JSON')



        json_str = cleaned[json_start:json_end + 1]

        return json.loads(json_str)



    

    def generate_assembly_specification(

        self,

        vision_analysis_results: List[Dict],

        model_analysis_results: Optional[Dict] = None,

        focus_type: str = "general",

        special_requirements: str = "无特殊要求"

    ) -> Dict:

        """

        生成装配工艺规程

        

        Args:

            vision_analysis_results: 视觉模型分析结果列表

            model_analysis_results: 3D模型分析结果

            focus_type: 专业重点类型 ("general", "welding", "precision", "heavy")

            special_requirements: 特殊要求描述

            

        Returns:

            装配规程生成结果

        """

        # 构建专家提示词

        system_prompt = build_assembly_expert_prompt(focus_type)

        

        # 整理输入数据

        input_data = {

            "vision_analysis": vision_analysis_results,

            "model_analysis": model_analysis_results,

            "focus_type": focus_type

        }

        

        # 构建用户输入

        user_input = build_user_input(

            input_data=json.dumps(input_data, ensure_ascii=False, indent=2),

            special_requirements=special_requirements

        )

        

        try:

            # 调用DeepSeek API

            response = self.client.chat.completions.create(

                model=self.model_name,

                messages=[

                    {"role": "system", "content": system_prompt},

                    {"role": "user", "content": user_input}

                ],

                stream=False,

                temperature=0.1,  # 降低随机性，提高一致性

                max_tokens=8000

            )

            

            raw_content = response.choices[0].message.content or ""

            usage = getattr(response, 'usage', None)

            token_usage = {

                "prompt_tokens": getattr(usage, 'prompt_tokens', None),

                "completion_tokens": getattr(usage, 'completion_tokens', None),

                "total_tokens": getattr(usage, 'total_tokens', None)

            }



            try:

                parsed_result = self._parse_json_from_content(raw_content)

            except (ValueError, json.JSONDecodeError) as e:

                error_message = f"DeepSeek返回结果解析失败: {e}"

                return {

                    "success": False,

                    "error": error_message,

                    "raw_response": raw_content,

                    "token_usage": token_usage

                }



            return {

                "success": True,

                "result": parsed_result,

                "raw_response": raw_content,

                "token_usage": token_usage

            }



        except Exception as e:

            return {

                "success": False,

                "error": str(e),

                "result": None

            }

    

    def optimize_assembly_sequence(

        self,

        current_sequence: List[Dict],

        constraints: Optional[Dict] = None

    ) -> Dict:

        """

        优化装配顺序

        

        Args:

            current_sequence: 当前装配顺序

            constraints: 约束条件

            

        Returns:

            优化后的装配顺序

        """

        optimization_prompt = """作为装配工艺专家，请优化以下装配顺序：



当前装配顺序：

{current_sequence}



约束条件：

{constraints}



请从以下角度进行优化：

1. 装配可达性和操作便利性

2. 工装夹具的使用效率

3. 质量控制的检验时机

4. 生产效率和节拍要求

5. 安全风险的控制



输出优化后的装配顺序，并说明优化理由。"""

        

        try:

            response = self.client.chat.completions.create(

                model=self.model_name,

                messages=[

                    {

                        "role": "system", 

                        "content": build_assembly_expert_prompt("general")

                    },

                    {

                        "role": "user", 

                        "content": optimization_prompt.format(

                            current_sequence=json.dumps(current_sequence, ensure_ascii=False, indent=2),

                            constraints=json.dumps(constraints or {}, ensure_ascii=False, indent=2)

                        )

                    }

                ],

                stream=False,

                temperature=0.1

            )

            

            return {

                "success": True,

                "optimized_sequence": response.choices[0].message.content,

                "token_usage": {

                    "prompt_tokens": response.usage.prompt_tokens,

                    "completion_tokens": response.usage.completion_tokens,

                    "total_tokens": response.usage.total_tokens

                }

            }

            

        except Exception as e:

            return {

                "success": False,

                "error": str(e)

            }

    

    def generate_quality_checklist(

        self,

        assembly_spec: Dict,

        quality_level: str = "standard"

    ) -> Dict:

        """

        生成质量检查清单

        

        Args:

            assembly_spec: 装配规程

            quality_level: 质量等级 ("basic", "standard", "high", "critical")

            

        Returns:

            质量检查清单

        """

        quality_prompt = """基于以下装配规程，生成详细的质量检查清单：



装配规程：

{assembly_spec}



质量等级：{quality_level}



请生成包含以下内容的质量检查清单：

1. 过程检验点和检验方法

2. 关键尺寸和公差要求

3. 焊接质量检验标准

4. 外观质量要求

5. 功能性能测试项目

6. 最终验收标准



输出格式为结构化的检查清单。"""

        

        try:

            response = self.client.chat.completions.create(

                model=self.model_name,

                messages=[

                    {

                        "role": "system", 

                        "content": build_assembly_expert_prompt("general")

                    },

                    {

                        "role": "user", 

                        "content": quality_prompt.format(

                            assembly_spec=json.dumps(assembly_spec, ensure_ascii=False, indent=2),

                            quality_level=quality_level

                        )

                    }

                ],

                stream=False,

                temperature=0.1

            )

            

            return {

                "success": True,

                "quality_checklist": response.choices[0].message.content,

                "token_usage": {

                    "prompt_tokens": response.usage.prompt_tokens,

                    "completion_tokens": response.usage.completion_tokens,

                    "total_tokens": response.usage.total_tokens

                }

            }

            

        except Exception as e:

            return {

                "success": False,

                "error": str(e)

            }





# 便捷函数

def generate_assembly_manual(

    vision_results: List[Dict],

    model_results: Optional[Dict] = None,

    focus_type: str = "general",

    api_key: Optional[str] = None

) -> Dict:

    """

    生成装配手册的便捷函数

    

    Args:

        vision_results: 视觉分析结果

        model_results: 3D模型分析结果

        focus_type: 专业重点类型

        api_key: API密钥

        

    Returns:

        装配手册生成结果

    """

    expert = AssemblyExpertModel(api_key)

    return expert.generate_assembly_specification(

        vision_analysis_results=vision_results,

        model_analysis_results=model_results,

        focus_type=focus_type

    )

