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
from utils.newapi_compat import (
    NEWAPI_BASE_URL,
    DEFAULT_NEWAPI_MODEL,
    DEFAULT_NEWAPI_MAX_COMPLETION_TOKENS,
    extract_completion_tokens_cap,
    is_newapi_provider,
    normalize_provider,
)

PROVIDER_CONFIG = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "model_env": "OPENROUTER_MODEL",
        "default_model": "google/gemini-2.5-flash-preview-09-2025",
    },
    "newapi": {
        "base_url": NEWAPI_BASE_URL,
        "api_key_env": "ARK_API_KEY",
        "model_env": "ARK_MODEL",
        "default_model": DEFAULT_NEWAPI_MODEL,
    },
    "doubao": {  # legacy alias
        "base_url": NEWAPI_BASE_URL,
        "api_key_env": "ARK_API_KEY",
        "model_env": "ARK_MODEL",
        "default_model": DEFAULT_NEWAPI_MODEL,
    }
}


class GeminiVisionModel:
    """视觉模型封装类（OpenRouter / NewAPI均可用）"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        fallback_model_name: Optional[str] = None,
        provider: str = "openrouter",
        base_url: Optional[str] = None
    ):
        """
        初始化Gemini模型

        Args:
            api_key: API Key
            model_name: 模型名称（可选，默认从config.py读取）
            provider: 提供方（openrouter/newapi）
            base_url: 自定义Base URL（可选）
        """
        self.provider = normalize_provider(provider)
        provider_config = PROVIDER_CONFIG.get(self.provider, PROVIDER_CONFIG["openrouter"])
        self._model_env = provider_config["model_env"]
        self._default_model = provider_config["default_model"]

        self.api_key = api_key or os.getenv(provider_config["api_key_env"])
        if not self.api_key:
            raise ValueError(f"请设置{provider_config['api_key_env']}环境变量或传入api_key参数")

        self.client = OpenAI(
            base_url=base_url or provider_config["base_url"],
            api_key=self.api_key
        )

        # ✅ Bug修复：从config.py读取模型名称
        if model_name:
            self.model_name = model_name
        else:
            if provider == "openrouter":
                try:
                    from config import MODEL_CONFIG
                    self.model_name = MODEL_CONFIG["gemini"]
                except ImportError:
                    self.model_name = os.getenv("GEMINI_MODEL", self._default_model)
            else:
                self.model_name = os.getenv(self._model_env) or self._default_model
        self.fallback_model_name = (fallback_model_name or "").strip() or None
    
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
            candidate_models = [self.model_name]
            if self.fallback_model_name and self.fallback_model_name != self.model_name:
                candidate_models.append(self.fallback_model_name)

            completion = None
            last_error = None
            for model_index, current_model in enumerate(candidate_models):
                request_payload = {
                    "model": current_model,
                    "messages": messages,
                    "temperature": 0.1
                }
                if self.provider == "openrouter":
                    request_payload["extra_headers"] = {
                        "HTTP-Referer": "https://mecagent.com",
                        "X-Title": "MecAgent Assembly Planning"
                    }
                newapi_max_completion_tokens = DEFAULT_NEWAPI_MAX_COMPLETION_TOKENS
                if is_newapi_provider(self.provider):
                    request_payload["extra_body"] = {
                        "max_completion_tokens": newapi_max_completion_tokens
                    }
                try:
                    completion = self.client.chat.completions.create(**request_payload)
                    if model_index > 0:
                        print(f"⚠️ 主模型 {self.model_name} 失败，已切换兜底模型 {current_model}")
                    break
                except Exception as request_error:
                    last_error = request_error
                    if not is_newapi_provider(self.provider):
                        continue

                    cap = extract_completion_tokens_cap(request_error)
                    if cap and cap > 0 and newapi_max_completion_tokens > cap:
                        request_payload["extra_body"] = {
                            "max_completion_tokens": cap
                        }
                        try:
                            completion = self.client.chat.completions.create(**request_payload)
                            if model_index > 0:
                                print(f"⚠️ 主模型 {self.model_name} 失败，已切换兜底模型 {current_model}")
                            break
                        except Exception as second_error:
                            last_error = second_error
                    continue

            if completion is None:
                raise last_error or RuntimeError("视觉模型调用失败：所有候选模型均不可用")
            
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
            
            # 保存输出结果到临时文件（按任务名归档到子目录）
            from utils.time_utils import beijing_now, build_debug_output_dir
            now = beijing_now()
            timestamp = now.strftime("%Y%m%d_%H%M%S")
            output_dir = build_debug_output_dir(os.getenv("TASK_ID"), now=now)
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

