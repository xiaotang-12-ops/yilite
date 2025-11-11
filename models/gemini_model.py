# -*- coding: utf-8 -*-
"""
Gemini 2.5 Flash 视觉模型封装
通过OpenRouter API调用
"""

import os
import json
import base64
from typing import Dict, List, Optional, Union
from openai import OpenAI


class GeminiVisionModel:
    """Gemini 2.5 Flash 视觉模型封装类"""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        """
        初始化Gemini模型

        Args:
            api_key: OpenRouter API Key
            model_name: 模型名称（可选，默认从config.py读取）
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("请设置OPENROUTER_API_KEY环境变量或传入api_key参数")

        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key
        )

        # ✅ Bug修复：从config.py读取模型名称
        if model_name:
            self.model_name = model_name
        else:
            try:
                from config import MODEL_CONFIG
                self.model_name = MODEL_CONFIG["gemini"]
            except ImportError:
                self.model_name = os.getenv("GEMINI_MODEL", "google/gemini-2.5-flash-preview-09-2025")
    
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
            return f"data:image/png;base64,{encoded_string}"
    
    def analyze_engineering_drawing(
        self,
        image_path: Union[str, List[str]],
        system_prompt: str,
        user_query: str
    ) -> Dict:
        """
        分析工程图纸
        
        Args:
            image_path: 图片文件路径（单张）或图片路径列表（多张）
            system_prompt: 系统提示词
            user_query: 用户查询
            
        Returns:
            解析结果字典
        """
        # 准备图片数据（支持单张或多张）
        image_paths = [image_path] if isinstance(image_path, str) else image_path
        
        # 构建用户消息内容（多张图片）
        user_content = []
        
        # 添加文本查询（放在最前面）
        user_content.append({
            "type": "text",
            "text": user_query
        })
        
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
                extra_headers={
                    "HTTP-Referer": "https://mecagent.com",
                    "X-Title": "MecAgent Assembly Planning"
                },
                model=self.model_name,
                messages=messages,
                temperature=0.1  # 降低温度，提高确定性
            )
            
            # 获取响应
            response_content = completion.choices[0].message.content
            
            # 尝试解析JSON结果
            try:
                # 提取JSON部分
                json_start = response_content.find('{')
                json_end = response_content.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response_content[json_start:json_end]
                    parsed_result = json.loads(json_str)
                else:
                    parsed_result = {"raw_content": response_content}
            except json.JSONDecodeError as e:
                # JSON解析失败，尝试修复
                print(f"⚠️ JSON解析失败: {e}")
                
                # 尝试提取```json代码块
                if "```json" in response_content:
                    json_start = response_content.find("```json") + 7
                    json_end = response_content.find("```", json_start)
                    if json_end > json_start:
                        json_str = response_content[json_start:json_end].strip()
                        try:
                            parsed_result = json.loads(json_str)
                        except:
                            parsed_result = {"raw_content": response_content, "parse_error": str(e)}
                    else:
                        parsed_result = {"raw_content": response_content, "parse_error": str(e)}
                else:
                    parsed_result = {"raw_content": response_content, "parse_error": str(e)}
            
            # 保存输出结果到临时文件
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = "debug_output"
            os.makedirs(output_dir, exist_ok=True)
            
            output_file = os.path.join(output_dir, f"gemini_output_{timestamp}.json")
            result_data = {
                "success": True,
                "model": self.model_name,
                "timestamp": timestamp,
                "image_count": len(image_paths),
                "result": parsed_result,
                "raw_response": response_content
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            
            print(f"💾 Gemini输出已保存: {output_file}")
            
            return {
                "success": True,
                "result": parsed_result,
                "raw_response": response_content
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "result": None
            }

