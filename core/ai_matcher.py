"""
AI智能匹配器
用于处理代码匹配失败的零件
"""

import json
import re
from typing import List, Dict, Optional
from openai import OpenAI
import sys
import os
from utils.time_utils import beijing_now, build_debug_output_dir

DOUBAO_BASE_URL = (
    os.getenv("DOUBAO_BASE_URL")
    or os.getenv("ARK_BASE_URL")
    or "http://111.230.37.43:3000/v1"
)
DOUBAO_MAX_TOKENS = 64000

PROVIDER_BASE_URLS = {
    "openrouter": "https://openrouter.ai/api/v1",
    "deepseek": "https://api.deepseek.com",
    "doubao": DOUBAO_BASE_URL,
}
PROVIDER_API_KEY_ENVS = {
    "openrouter": "OPENROUTER_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "doubao": "ARK_API_KEY",
}
PROVIDER_MODEL_ENVS = {
    "openrouter": "OPENROUTER_MODEL",
    "deepseek": "DEEPSEEK_MODEL",
    "doubao": "ARK_MODEL",
}
PROVIDER_DEFAULT_MODELS = {
    "openrouter": "google/gemini-2.5-flash-preview-09-2025",
    "deepseek": "deepseek-chat",
    "doubao": "doubao-seed-1-8-251228",
}

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入提示词
from prompts.agent_2_bom_3d_matching import (
    build_ai_matching_prompt,
    AI_MATCHING_SYSTEM_PROMPT
)


class AIBOMMatcher:
    """AI智能BOM匹配器"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        task_id: Optional[str] = None,
        provider: str = "openrouter",
        model_name: Optional[str] = None
    ):
        self.provider = provider
        api_key_env = PROVIDER_API_KEY_ENVS.get(provider, "OPENROUTER_API_KEY")
        model_env = PROVIDER_MODEL_ENVS.get(provider, "OPENROUTER_MODEL")
        base_url = PROVIDER_BASE_URLS.get(provider, PROVIDER_BASE_URLS["openrouter"])

        self.api_key = api_key or os.getenv(api_key_env)
        if not self.api_key:
            raise ValueError(f"需要设置{api_key_env}环境变量或传入api_key参数")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=base_url
        )
        self.model = model_name or os.getenv(model_env) or PROVIDER_DEFAULT_MODELS.get(provider, PROVIDER_DEFAULT_MODELS["openrouter"])
        # 记录任务ID用于调试文件命名
        self.task_id = task_id or os.getenv("TASK_ID", "unknown_task")
        # 批处理参数（未匹配零件超过阈值时分批，以防响应截断）
        self.batch_threshold = 200  # 超过这个数量的未匹配3D零件就分批
        self.batch_size = 100       # 单批上限
        self.min_batch_size = 20    # 截断重试时的最小批大小（避免无限拆分）
    
    def match_unmatched_parts(
        self,
        unmatched_parts: List[Dict],
        bom_data: List[Dict]
    ) -> List[Dict]:
        """
        用AI一次性匹配所有未匹配的零件

        Args:
            unmatched_parts: 未匹配的零件列表
            bom_data: BOM表数据

        Returns:
            AI匹配结果列表
        """
        print(f"\n   🤖 AI员工开始工作...")
        print(f"      📊 他看到了 {len(unmatched_parts)} 个未匹配的3D零件")
        print(f"      📋 他参考了 {len(bom_data)} 个BOM项")
        print(f"      🎯 他准备用智能算法进行匹配...")
        import sys
        sys.stdout.flush()

        # 统一的调试文件标识与输出目录
        now = beijing_now()
        ts_str = now.strftime("%Y%m%d_%H%M%S")
        debug_dir = build_debug_output_dir(self.task_id, now=now)
        safe_task = re.sub(r"[^A-Za-z0-9._-]+", "_", str(self.task_id)) or "unknown_task"

        # 根据数量决定是否分批，以避免大响应被截断
        if len(unmatched_parts) > self.batch_threshold:
            print(f"      📦 未匹配零件超过 {self.batch_threshold} 个，按批次处理（单批 {self.batch_size} 个）...")
            sys.stdout.flush()
            all_results = self._match_in_batches(unmatched_parts, bom_data, safe_task, ts_str, debug_dir)
        else:
            all_results = self._match_all_at_once(
                unmatched_parts,
                bom_data,
                safe_task,
                ts_str,
                debug_dir,
                allow_split=True,
            )

        # 统计AI匹配结果
        matched_count = sum(1 for r in all_results if r.get('matched_bom_code'))
        unmatched_count = len(all_results) - matched_count
        match_rate = (matched_count / len(all_results) * 100) if all_results else 0

        # 置信度统计
        high_confidence_count = sum(1 for r in all_results if r.get('confidence', 0) >= 0.85)
        medium_confidence_count = sum(1 for r in all_results if 0.6 <= r.get('confidence', 0) < 0.85)
        low_confidence_count = sum(1 for r in all_results if 0 < r.get('confidence', 0) < 0.6)

        print(f"\n" + "="*80)
        print(f"🤖 AI匹配结果统计")
        print(f"="*80)
        print(f"📊 总零件数: {len(all_results)}")
        print(f"✅ 成功匹配: {matched_count} ({match_rate:.1f}%)")
        print(f"❌ 未匹配: {unmatched_count}")
        print(f"\n📈 置信度分布:")
        print(f"   🟢 高置信度 (≥0.85): {high_confidence_count}")
        print(f"   🟡 中置信度 (0.6-0.85): {medium_confidence_count}")
        print(f"   🔴 低置信度 (<0.6): {low_confidence_count}")

        if match_rate >= 95:
            print(f"\n🎉 AI匹配率达到 {match_rate:.1f}%，表现优秀！")
        elif match_rate >= 80:
            print(f"\n👍 AI匹配率 {match_rate:.1f}%，表现良好")
        else:
            print(f"\n⚠️  AI匹配率 {match_rate:.1f}%，需要优化提示词")
        print(f"="*80)

        import sys
        sys.stdout.flush()

        return all_results
    
    def _match_all_at_once(
        self,
        parts: List[Dict],
        bom_data: List[Dict],
        safe_task: str,
        ts_str: str,
        debug_dir: str,
        batch_label: Optional[str] = None,
        allow_split: bool = False
    ) -> List[Dict]:
        """
        匹配一批零件；可在检测到截断时按需拆分

        Args:
            parts: 未匹配的3D零件列表
            bom_data: 未匹配的BOM列表（已经在调用方计算好了）
            safe_task: 任务名（用于调试文件）
            ts_str: 时间戳（用于调试文件）
            debug_dir: 调试文件目录
            batch_label: 批次标识，用于调试文件命名
            allow_split: 截断时是否继续拆分当前批
        """

        print(f"      📝 他正在准备分析资料... (批次: {batch_label or '全量'}, 数量: {len(parts)})")
        import sys
        sys.stdout.flush()

        # ✅ bom_data已经是未匹配的BOM了，不需要再次计算
        unmatched_bom = bom_data

        print(f"      📊 他发现还有 {len(unmatched_bom)} 个BOM未匹配")
        sys.stdout.flush()

        # 使用提示词文件构建prompt
        system_prompt, user_query = build_ai_matching_prompt(parts, unmatched_bom)

        print(f"      🤖 他开始调用 {self.provider}/{self.model} 进行深度分析...")
        print(f"      ⏱️  请稍候，模型正在分析...")
        sys.stdout.flush()

        # 调用AI（带重试机制）
        max_retries = 3
        retry_delay = 5  # 秒

        try:
            import time
            start_time = time.time()

            last_error = None
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        print(f"      🔄 第 {attempt + 1} 次重试...")
                        time.sleep(retry_delay)

                    request_payload = {
                        "model": self.model,  # 使用配置模型
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_query}
                        ],
                        "temperature": 0.4,  # ✅ 提高到0.4，使用COT推理，追求100%匹配率
                        "stream": False,
                        "timeout": 120  # ✅ 增加超时时间到120秒
                    }
                    if self.provider == "doubao":
                        request_payload["extra_body"] = {
                            "thinking": {"type": "enabled"},
                            "reasoning_effort": "medium",
                            "max_completion_tokens": DOUBAO_MAX_TOKENS
                        }
                        request_payload["timeout"] = 1800

                    response = self.client.chat.completions.create(**request_payload)
                    break  # 成功则跳出重试循环
                except Exception as retry_error:
                    last_error = retry_error
                    print(f"      ⚠️  请求失败 (尝试 {attempt + 1}/{max_retries}): {retry_error}")
                    if attempt == max_retries - 1:
                        raise last_error  # 最后一次重试也失败，抛出异常

            elapsed = time.time() - start_time
            choice = response.choices[0]
            result_text = choice.message.content
            finish_reason = getattr(choice, "finish_reason", None)

            print(f"      📊 AI大脑返回了分析结果 ({len(result_text)} 字符, 耗时: {elapsed:.1f}秒, finish_reason={finish_reason})")
            import sys
            sys.stdout.flush()

            # 调试：保存AI原始响应
            os.makedirs(debug_dir, exist_ok=True)
            debug_file = os.path.join(debug_dir, f"ai_matching_response_{safe_task}_{ts_str}.txt")
            if batch_label:
                debug_file = debug_file.replace(".txt", f"_part{batch_label}.txt")
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(result_text)
            print(f"      💾 AI响应已保存到: {debug_file}")

            # 解析JSON
            ai_results = self._parse_response(result_text)

            truncated = False
            if finish_reason and finish_reason != "stop":
                truncated = True
            if not ai_results:
                truncated = True
            elif len(ai_results) < len(parts) and finish_reason and finish_reason != "stop":
                truncated = True

            if truncated and allow_split and len(parts) > self.min_batch_size:
                print(f"      ⚠️  检测到响应可能被截断，拆分本批继续处理（批次: {batch_label or '全量'}）")
                mid = len(parts) // 2 or 1
                left = parts[:mid]
                right = parts[mid:]
                left_results = self._match_all_at_once(
                    left, bom_data, safe_task, ts_str, debug_dir, f"{batch_label or '1'}-a", allow_split=True
                )
                right_results = self._match_all_at_once(
                    right, bom_data, safe_task, ts_str, debug_dir, f"{batch_label or '1'}-b", allow_split=True
                )
                return left_results + right_results

            if not ai_results:
                print(f"   ⚠️  JSON解析失败，返回空结果")
                return self._create_empty_results(parts)

            return self._map_ai_results(parts, ai_results)

        except Exception as e:
            print(f"   ❌ AI匹配失败: {e}")
            import traceback
            traceback.print_exc()

            # ✅ 保存失败信息到调试文件
            try:
                batch_suffix = f"_part{batch_label}" if batch_label else ""
                os.makedirs(debug_dir, exist_ok=True)
                error_file = os.path.join(debug_dir, f"ai_matching_ERROR_{safe_task}_{ts_str}{batch_suffix}.txt")
                with open(error_file, "w", encoding="utf-8") as f:
                    f.write(f"=== AI匹配失败 ===\n")
                    f.write(f"时间: {ts_str}\n")
                    f.write(f"批次: {batch_label or '全量'}\n")
                    f.write(f"零件数: {len(parts)}\n")
                    f.write(f"BOM数: {len(bom_data)}\n")
                    f.write(f"\n=== 错误信息 ===\n")
                    f.write(f"{type(e).__name__}: {e}\n")
                    f.write(f"\n=== 堆栈跟踪 ===\n")
                    f.write(traceback.format_exc())
                    f.write(f"\n=== 零件列表 ===\n")
                    for p in parts[:10]:  # 只记录前10个
                        f.write(f"  - {p.get('node_name', 'N/A')}: {p.get('geometry_name', 'N/A')[:50]}\n")
                    if len(parts) > 10:
                        f.write(f"  ... 还有 {len(parts) - 10} 个零件\n")
                print(f"   📝 错误信息已保存到: {error_file}")
            except Exception as save_error:
                print(f"   ⚠️  保存错误信息失败: {save_error}")

            return self._create_empty_results(parts)

    def _match_in_batches(
        self,
        parts: List[Dict],
        bom_data: List[Dict],
        safe_task: str,
        ts_str: str,
        debug_dir: str,
    ) -> List[Dict]:
        """分批处理未匹配零件，防止单次响应过长被截断"""
        results: List[Dict] = []
        batch_no = 0
        total_parts = len(parts)
        for start in range(0, total_parts, self.batch_size):
            batch_no += 1
            end = min(start + self.batch_size, total_parts)
            batch_parts = parts[start:end]
            print(f"\n   📦 正在处理批次 {batch_no}: {len(batch_parts)} 个零件（范围 {start+1}-{end}/{total_parts}）")
            batch_results = self._match_all_at_once(
                batch_parts,
                bom_data,
                safe_task,
                ts_str,
                debug_dir,
                batch_label=str(batch_no),
                allow_split=True
            )
            results.extend(batch_results)
        return results

    def _map_ai_results(self, parts: List[Dict], ai_results: List[Dict]) -> List[Dict]:
        """
        将AI结果映射回原始零件

        AI返回格式：{"node_name": "...", "geometry_name": "...", "bom_code": "...", "confidence": 0.85, "reasoning": "..."}
        """
        results = []
        for part in parts:
            ai_result = None
            part_node_name = part.get('node_name', '')
            part_geometry = part.get('geometry_name', '')

            for ar in ai_results:
                # 优先通过node_name匹配
                if ar.get('node_name') == part_node_name:
                    ai_result = ar
                    break
                # 备用：通过geometry_name匹配
                elif ar.get('geometry_name') == part_geometry:
                    ai_result = ar
                    break

            if ai_result:
                results.append({
                    'geometry_name': part.get('geometry_name'),
                    'node_name': part.get('node_name'),
                    'matched_bom_code': ai_result.get('bom_code'),  # AI返回的是bom_code
                    'confidence': ai_result.get('confidence', 0.0),
                    'reason': ai_result.get('reasoning', '')  # AI返回的是reasoning
                })
            else:
                # 如果没找到对应结果，返回空匹配
                results.append({
                    'geometry_name': part.get('geometry_name'),
                    'node_name': part.get('node_name'),
                    'matched_bom_code': None,
                    'confidence': 0.0,
                    'reason': 'AI未返回匹配结果'
                })

        return results

    def _create_empty_results(self, parts: List[Dict]) -> List[Dict]:
        """创建空的匹配结果"""
        return [
            {
                "geometry_name": p.get('geometry_name'),
                "node_name": p.get('node_name'),
                "matched_bom_code": None,
                "confidence": 0.0,
                "reason": "AI匹配失败"
            }
            for p in parts
        ]
    
    def _build_prompt(self, parts: List[Dict], bom_data: List[Dict]) -> str:
        """构建AI匹配的prompt"""
        
        # 限制BOM表大小（只发送前100项）
        bom_sample = bom_data[:100] if len(bom_data) > 100 else bom_data
        
        prompt = f"""你是一个BOM-3D零件匹配专家。你的任务是将3D模型中的零件名称与BOM表中的项目进行匹配。

## 背景
- 3D零件名称可能有编码问题（乱码），但你可以通过产品代号、规格、关键词等线索进行匹配
- BOM表包含：代号（code）、产品代号（product_code）、名称（name）等信息
- 匹配依据：产品代号（优先）、规格（如M16、φ40等）、零件类型（螺栓、垫圈、方形板等）

## BOM表（{len(bom_data)}项，显示前{len(bom_sample)}项）
```json
{json.dumps(bom_sample, ensure_ascii=False, indent=2)[:2000]}
...
```

## 未匹配的3D零件（{len(parts)}个）
```json
{json.dumps([{'fixed_name': p['fixed_name'], 'geometry_name': p['geometry_name']} for p in parts], ensure_ascii=False, indent=2)}
```

## 匹配规则
1. **优先匹配产品代号**：如果3D零件名称中包含产品代号（如T-SPV1830-EURO-09），优先匹配
2. **规格匹配**：对于标准件（螺栓、垫圈等），通过规格（M16、φ40等）匹配
3. **关键词匹配**：通过零件类型关键词（方形板、垫圈、螺栓等）辅助匹配
4. **无法匹配**：如果BOM表中确实没有对应项，返回null

## 输出格式
返回JSON数组，每个元素包含：
- geometry_name: 3D零件的原始名称（必须与输入完全一致）
- bom_code: 匹配到的BOM代号（如"01.09.2556"），如果无法匹配则为null
- confidence: 匹配置信度（0-1）
- reasoning: 匹配理由（简短说明）

请只返回JSON数组，不要其他解释。

示例输出：
[
  {
    "geometry_name": "T-SPV1830-EURO-09-Q235",
    "bom_code": "01.09.2556",
    "confidence": 0.95,
    "reasoning": "产品代号完全匹配"
  },
  {
    "geometry_name": "M16x60-GB/T5782-2000",
    "bom_code": "02.03.0088",
    "confidence": 0.85,
    "reasoning": "规格M16匹配"
  }
]
"""
        return prompt
    
    def _parse_response(self, response_text: str) -> List[Dict]:
        """解析AI响应（参考dual_channel_parser的成熟方案）"""

        # 移除markdown代码块标记（参考dual_channel_parser）
        content = response_text.strip()

        if content.startswith('```json'):
            content = content[7:]  # 移除 ```json

        if content.startswith('```'):
            content = content[3:]  # 移除 ```

        if content.endswith('```'):
            content = content[:-3]  # 移除结尾的 ```

        content = content.strip()

        # 查找JSON的开始和结束
        json_start = content.find('{')
        json_end = content.rfind('}') + 1

        if json_start >= 0 and json_end > json_start:
            json_str = content[json_start:json_end]

            # ✅ 自动修复常见的JSON格式错误
            # 1. 移除数组/对象最后一个元素后的逗号（如 },\n] 或 },\n}）
            json_str = re.sub(r',(\s*[\]}])', r'\1', json_str)

            # 2. 移除控制字符
            json_str = ''.join(char for char in json_str if ord(char) >= 32 or char in '\n\r\t')

            # 尝试解析JSON
            try:
                parsed_result = json.loads(json_str)
                print(f"      ✅ JSON解析成功")

                # 如果返回的是对象，提取ai_matched_pairs字段
                if isinstance(parsed_result, dict):
                    if 'ai_matched_pairs' in parsed_result:
                        return parsed_result['ai_matched_pairs']
                    else:
                        print(f"      ⚠️  JSON格式错误：缺少'ai_matched_pairs'字段")
                        return []
                # 如果直接返回数组
                elif isinstance(parsed_result, list):
                    return parsed_result
                else:
                    print(f"      ⚠️  JSON格式错误：期望对象或数组，得到 {type(parsed_result)}")
                    return []

            except json.JSONDecodeError as e:
                error_msg = f"JSON解析失败: line {e.lineno} column {e.colno} (char {e.pos})"
                print(f"      ⚠️  {error_msg}")
                return []
            except Exception as e:
                print(f"      ⚠️  解析错误: {e}")
                return []
        else:
            print(f"      ⚠️  未找到有效的JSON数据")
            return []
    
    def apply_ai_matches(
        self,
        cleaned_parts: List[Dict],
        ai_matches: List[Dict],
        min_confidence: float = 0.8
    ) -> List[Dict]:
        """
        将AI匹配结果应用到零件列表
        
        Args:
            cleaned_parts: 清洗后的零件列表
            ai_matches: AI匹配结果
            min_confidence: 最小置信度阈值
            
        Returns:
            更新后的零件列表
        """
        print(f"\n🔧 应用AI匹配结果...")
        
        # 创建geometry_name到AI匹配的映射
        ai_match_map = {
            m['geometry_name']: m
            for m in ai_matches
            if m.get('matched_bom_code') and m.get('confidence', 0) >= min_confidence
        }
        
        # 应用AI匹配
        updated_count = 0
        for part in cleaned_parts:
            # 只更新未匹配的零件
            if not part.get('bom_code'):
                geometry_name = part['geometry_name']
                if geometry_name in ai_match_map:
                    ai_match = ai_match_map[geometry_name]
                    part['bom_code'] = ai_match['matched_bom_code']
                    part['match_method'] = f"AI匹配(置信度{ai_match['confidence']:.2f})"
                    part['confidence'] = ai_match['confidence']
                    part['ai_reason'] = ai_match.get('reason', '')
                    updated_count += 1
        
        print(f"   更新了 {updated_count} 个零件的匹配结果")
        
        return cleaned_parts
