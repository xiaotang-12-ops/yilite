# -*- coding: utf-8 -*-
"""
Gemini Agent 
Gemini 2.5 FlashAgent
"""

import os
import json
import base64
import time
from typing import Dict, List, Optional, Union
from openai import OpenAI
import datetime
from utils.time_utils import beijing_now, build_debug_output_dir

DOUBAO_BASE_URL = (
    os.getenv("DOUBAO_BASE_URL")
    or os.getenv("ARK_BASE_URL")
    or "http://111.230.37.43:3000/v1"
)
DOUBAO_MAX_TOKENS = 64000

PROVIDER_CONFIG = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "model_env": "OPENROUTER_MODEL",
        "default_model": "google/gemini-2.5-flash-preview-09-2025",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "api_key_env": "DEEPSEEK_API_KEY",
        "model_env": "DEEPSEEK_MODEL",
        "default_model": "deepseek-chat",
    },
    "doubao": {
        "base_url": DOUBAO_BASE_URL,
        "api_key_env": "ARK_API_KEY",
        "model_env": "ARK_MODEL",
        "default_model": "doubao-seed-1-8-251228",
    },
}


class BaseGeminiAgent:
    """Gemini 2.5 Flash Agent"""
    
    def __init__(
        self,
        agent_name: str,
        api_key: Optional[str] = None,
        temperature: float = 0.1,
        model_name: Optional[str] = None,
        provider: str = "openrouter"
    ):
        """
        Gemini Agent

        Args:
            agent_name: Agent
            api_key: OpenRouter API Key
            temperature: 0-1
            model_name: 模型名称（可选，默认从环境变量OPENROUTER_MODEL读取）
        """
        self.agent_name = agent_name
        self.temperature = temperature

        self.provider = provider
        provider_config = PROVIDER_CONFIG.get(provider, PROVIDER_CONFIG["openrouter"])
        self._model_env = provider_config["model_env"]
        self._default_model = provider_config["default_model"]

        self.api_key = api_key or os.getenv(provider_config["api_key_env"])
        if not self.api_key:
            raise ValueError(f"{provider_config['api_key_env']} is required")

        self.client = OpenAI(
            base_url=provider_config["base_url"],
            api_key=self.api_key
        )

        # 保存传入的model_name（如果有的话），否则每次调用时从环境变量读取
        self._model_name_override = model_name

    @property
    def model_name(self) -> str:
        """动态获取模型名称，优先使用传入的值，其次使用环境变量，最后使用默认值"""
        return self._model_name_override or os.getenv(self._model_env) or self._default_model
    
    def encode_image_to_base64(self, image_path: str) -> str:
        """
        base64

        Args:
            image_path: 

        Returns:
            base64URL
        """
        try:
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('ascii')
                # 
                if image_path.lower().endswith('.png'):
                    return f"data:image/png;base64,{encoded_string}"
                elif image_path.lower().endswith(('.jpg', '.jpeg')):
                    return f"data:image/jpeg;base64,{encoded_string}"
                else:
                    return f"data:image/png;base64,{encoded_string}"
        except Exception as e:
            print(f"  : {image_path}")
            print(f"   : {str(e)}")
            raise
    
    def call_gemini_with_retry(
        self,
        system_prompt: str,
        user_query: str,
        images: Optional[Union[str, List[str]]] = None,
        max_retries: int = 3
    ) -> Dict:
        """
        带重试机制的Gemini调用

        Args:
            system_prompt: 系统提示词
            user_query: 用户查询
            images: 图片路径
            max_retries: 最大重试次数（默认3次）

        Returns:
            {
                "success": bool,
                "result": dict,
                "raw_response": str
            }
        """
        for attempt in range(max_retries):
            print(f"\n{'='*60}")
            if attempt > 0:
                print(f"🔄 第{attempt + 1}次尝试（共{max_retries}次）")
            print(f"{'='*60}")

            result = self.call_gemini(system_prompt, user_query, images)

            if result["success"]:
                # 检查JSON是否有效
                parsed = result["result"]
                if parsed and not parsed.get("parse_error") and not parsed.get("raw_content"):
                    print(f"✅ 调用成功，JSON解析正常")
                    return result
                else:
                    print(f"⚠️ JSON解析失败，准备重试...")
                    if attempt < max_retries - 1:
                        print(f"⏳ 等待2秒后重试...")
                        time.sleep(2)
            else:
                print(f"⚠️ API调用失败: {result.get('error')}")
                if attempt < max_retries - 1:
                    print(f"⏳ 等待2秒后重试...")
                    time.sleep(2)

        # 所有重试都失败
        print(f"\n❌ 重试{max_retries}次后仍然失败")
        return {
            "success": False,
            "error": f"重试{max_retries}次后仍然失败",
            "result": None
        }

    def call_gemini(
        self,
        system_prompt: str,
        user_query: str,
        images: Optional[Union[str, List[str]]] = None
    ) -> Dict:
        """
        Gemini 2.5 Flash
        
        Args:
            system_prompt: 
            user_query: 
            images: 
            
        Returns:
            {
                "success": bool,
                "result": dict,  # JSON
                "raw_response": str  # 
            }
        """
        # 
        image_paths = []
        if images:
            if isinstance(images, str):
                image_paths = [images]
            else:
                image_paths = images
        
        # 
        user_content = []
        
        # 
        user_content.append({
            "type": "text",
            "text": user_query
        })
        
        # 
        for img_path in image_paths:
            if img_path.startswith('http'):
                image_url = img_path
            else:
                image_url = self.encode_image_to_base64(img_path)
            
            user_content.append({
                "type": "image_url",
                "image_url": {"url": image_url}
            })
        
        # 
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
            print(f"\n[{self.agent_name}] Calling AI Model")
            print(f"   Model: {self.model_name}")
            print(f"   Images: {len(image_paths)}")
            print(f"   Temperature: {self.temperature}")

            # API
            request_payload = {
                "model": self.model_name,
                "messages": messages,
                "temperature": self.temperature
            }
            if self.provider == "openrouter":
                request_payload["extra_headers"] = {
                    "HTTP-Referer": "https://mecagent.com",
                    "X-Title": "MecAgent"
                }
            if self.provider == "doubao":
                request_payload["extra_body"] = {
                    "max_completion_tokens": DOUBAO_MAX_TOKENS
                }

            completion = self.client.chat.completions.create(**request_payload)
            
            #
            response_content = completion.choices[0].message.content

            print(f"[{self.agent_name}] Success")

            # ✅ 先保存原始响应，再解析JSON
            try:
                parsed_result = self._parse_json_response(response_content)
            except Exception as parse_error:
                # 即使解析失败，也保存原始响应用于调试
                self._save_debug_output(
                    system_prompt=system_prompt,
                    user_query=user_query,
                    image_count=len(image_paths),
                    response=response_content,
                    parsed={"parse_error": str(parse_error)}
                )
                raise parse_error

            #
            self._save_debug_output(
                system_prompt=system_prompt,
                user_query=user_query,
                image_count=len(image_paths),
                response=response_content,
                parsed=parsed_result
            )

            return {
                "success": True,
                "result": parsed_result,
                "raw_response": response_content
            }

        except Exception as e:
            print(f"[{self.agent_name}] Failed: {str(e)}")
            print(f"\n⚠️ 提示：检查 debug_output 目录查看原始响应")
            return {
                "success": False,
                "error": str(e),
                "result": None
            }
    
    def _parse_json_response(self, response_content: str) -> Dict:
        """
        JSON
        
        Args:
            response_content: 
            
        Returns:
            JSON
        """
        try:
            # 
            json_start = response_content.find('{')
            json_end = response_content.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_content[json_start:json_end]
                return json.loads(json_str)
            else:
                return {"raw_content": response_content}
        except json.JSONDecodeError as e:
            # JSON```json
            if "```json" in response_content:
                json_start = response_content.find("```json") + 7
                json_end = response_content.find("```", json_start)
                if json_end > json_start:
                    json_str = response_content[json_start:json_end].strip()
                    try:
                        return json.loads(json_str)
                    except:
                        return {"raw_content": response_content, "parse_error": str(e)}
                else:
                    return {"raw_content": response_content, "parse_error": str(e)}
            else:
                return {"raw_content": response_content, "parse_error": str(e)}
    
    def _save_debug_output(
        self,
        system_prompt: str,
        user_query: str,
        image_count: int,
        response: str,
        parsed: Dict
    ):
        """
        
        
        Args:
            system_prompt: 
            user_query: 
            image_count: 
            response: 
            parsed: 
        """
        now = beijing_now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        # 任务名优先使用环境变量 TASK_ID，否则用 agent 名称
        debug_dir = build_debug_output_dir(os.getenv("TASK_ID") or self.agent_name, now=now)
        os.makedirs(debug_dir, exist_ok=True)

        result_data = {
            "agent_name": self.agent_name,
            "model": self.model_name,
            "timestamp": timestamp,
            "image_count": image_count,
            "temperature": self.temperature,
            "system_prompt": system_prompt,
            "user_query": user_query,
            "raw_response": response,
            "parsed_result": parsed
        }

        safe_name = self.agent_name.replace(" ", "_").replace("/", "_")
        output_file = os.path.join(debug_dir, f"{safe_name}__{timestamp}.json")

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)

        print(f" [{self.agent_name}] : {output_file}")
    
    def process(self, **kwargs) -> Dict:
        """
        
        
        Args:
            **kwargs: 
            
        Returns:
            
        """
        raise NotImplementedError("process")

