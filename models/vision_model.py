# -*- coding: utf-8 -*-
"""
Qwen3-VL视觉模型调用模块
基于阿里云DashScope API
"""

import os
import json
import base64
import ssl
import certifi
from typing import Dict, List, Optional, Union
from openai import OpenAI
from prompts.agent_1_vision_prompts import build_vision_prompt, build_user_query

# 禁用SSL验证警告
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Qwen3VLModel:
    """Qwen3-VL视觉模型封装类"""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        """
        初始化Qwen3-VL模型

        Args:
            api_key: DashScope API Key，如果不提供则从环境变量获取
            model_name: 模型名称（可选，默认从config.py读取）
        """
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("请设置DASHSCOPE_API_KEY环境变量或传入api_key参数")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )

        # ✅ Bug修复：从config.py读取模型名称
        if model_name:
            self.model_name = model_name
        else:
            try:
                from config import MODEL_CONFIG
                self.model_name = MODEL_CONFIG["qwen"]
            except ImportError:
                self.model_name = os.getenv("QWEN_MODEL", "qwen-vl-plus")
    
    def encode_image_to_base64(self, image_path: str) -> str:
        """
        将图片文件编码为base64格式
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            base64编码的图片数据URL
        """
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            return f"data:image/jpeg;base64,{encoded_string}"
    
    def analyze_engineering_drawing(
        self,
        image_path: Union[str, List[str]],
        focus_areas: Optional[List[str]] = None,
        drawing_type: str = "装配图",
        enable_thinking: bool = True,
        custom_system_prompt: Optional[str] = None,
        custom_user_query: Optional[str] = None
    ) -> Dict:
        """
        分析工程图纸

        Args:
            image_path: 图片文件路径（单张）或图片路径列表（多张）
            focus_areas: 重点关注领域，可选值：['welding', 'assembly', 'quality']
            drawing_type: 图纸类型描述
            enable_thinking: 是否启用思考过程
            custom_system_prompt: 自定义系统提示词，如果提供则覆盖默认提示词
            custom_user_query: 自定义用户查询，如果提供则覆盖默认查询

        Returns:
            解析结果字典
        """
        # 构建提示词
        if custom_system_prompt:
            system_prompt = custom_system_prompt
        else:
            system_prompt = build_vision_prompt(focus_areas)

        if custom_user_query:
            user_query = custom_user_query
        else:
            user_query = build_user_query(
                drawing_type=drawing_type,
                focus_description="BOM表格、技术要求和装配工艺"
            )

        # 准备图片数据（支持单张或多张）
        image_paths = [image_path] if isinstance(image_path, str) else image_path

        # 构建用户消息内容（多张图片）
        user_content = []

        # 添加所有图片
        for img_path in image_paths:
            if img_path.startswith('http'):
                image_url = img_path
            else:
                image_url = self.encode_image_to_base64(img_path)

            user_content.append({
                "type": "image_url",
                "image_url": {"url": image_url}
            })

        # 添加文本查询
        user_content.append({
            "type": "text",
            "text": user_query
        })

        # 构建消息
        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_content
            }
        ]
        
        try:
            # 调用API
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                stream=True,
                extra_body={
                    'enable_thinking': enable_thinking,
                    "thinking_budget": 1000
                }
            )
            
            # 处理流式响应
            reasoning_content = ""
            answer_content = ""
            is_answering = False
            
            for chunk in completion:
                if not chunk.choices:
                    continue
                    
                delta = chunk.choices[0].delta
                
                # 收集思考过程
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    reasoning_content += delta.reasoning_content
                else:
                    # 收集回复内容
                    if delta.content and not is_answering:
                        is_answering = True
                    if delta.content:
                        answer_content += delta.content
            
            # 尝试解析JSON结果
            try:
                # 提取JSON部分
                json_start = answer_content.find('{')
                json_end = answer_content.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = answer_content[json_start:json_end]
                    parsed_result = json.loads(json_str)
                else:
                    parsed_result = {"raw_content": answer_content}
            except json.JSONDecodeError as e:
                # JSON解析失败，尝试修复
                print(f"⚠️ JSON解析失败: {e}")
                print(f"⚠️ 错误位置: line {e.lineno} column {e.colno}")

                # 尝试提取```json代码块
                if "```json" in answer_content:
                    json_start = answer_content.find("```json") + 7
                    json_end = answer_content.find("```", json_start)
                    if json_end > json_start:
                        json_str = answer_content[json_start:json_end].strip()
                        try:
                            parsed_result = json.loads(json_str)
                        except:
                            parsed_result = {"raw_content": answer_content, "parse_error": str(e)}
                    else:
                        parsed_result = {"raw_content": answer_content, "parse_error": str(e)}
                else:
                    parsed_result = {"raw_content": answer_content, "parse_error": str(e)}
            
            # 保存输出结果到临时文件
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = "debug_output"
            os.makedirs(output_dir, exist_ok=True)

            output_file = os.path.join(output_dir, f"vision_output_{timestamp}.json")
            result_data = {
                "success": True,
                "model": self.model_name,
                "timestamp": timestamp,
                "image_path": image_path,
                "reasoning": reasoning_content,
                "result": parsed_result,
                "raw_response": answer_content
            }

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)

            print(f"💾 视觉模型输出已保存: {output_file}")

            return {
                "success": True,
                "reasoning": reasoning_content,
                "result": parsed_result,
                "raw_response": answer_content
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "result": None
            }
    
    def batch_analyze_pdf_pages(
        self, 
        pdf_images: List[str], 
        focus_areas: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        批量分析PDF页面图片
        
        Args:
            pdf_images: PDF页面图片路径列表
            focus_areas: 重点关注领域
            
        Returns:
            每页的分析结果列表
        """
        results = []
        
        for i, image_path in enumerate(pdf_images):
            print(f"正在分析第 {i+1}/{len(pdf_images)} 页...")
            
            result = self.analyze_engineering_drawing(
                image_path=image_path,
                focus_areas=focus_areas,
                drawing_type=f"工程图第{i+1}页"
            )
            
            result["page_number"] = i + 1
            result["image_path"] = image_path
            results.append(result)
        
        return results


# 便捷函数
def analyze_single_drawing(
    image_path: str, 
    api_key: Optional[str] = None,
    focus_areas: Optional[List[str]] = None
) -> Dict:
    """
    分析单张工程图纸的便捷函数
    
    Args:
        image_path: 图片路径
        api_key: API密钥
        focus_areas: 重点关注领域
        
    Returns:
        分析结果
    """
    model = Qwen3VLModel(api_key)
    return model.analyze_engineering_drawing(image_path, focus_areas)


def analyze_pdf_drawings(
    pdf_images: List[str], 
    api_key: Optional[str] = None,
    focus_areas: Optional[List[str]] = None
) -> List[Dict]:
    """
    批量分析PDF工程图纸的便捷函数
    
    Args:
        pdf_images: PDF页面图片列表
        api_key: API密钥
        focus_areas: 重点关注领域
        
    Returns:
        分析结果列表
    """
    model = Qwen3VLModel(api_key)
    return model.batch_analyze_pdf_pages(pdf_images, focus_areas)
