#!/usr/bin/env python3

# -*- coding: utf-8 -*-

"""

双通道解析器 - 严格按照总设计思路实现

PDF → 视觉通道 + 文本通道 → 候选事实JSON

"""



import os

import json

import tempfile

from pathlib import Path

from typing import Dict, List, Any, Optional



import fitz  # PyMuPDF

from pypdf import PdfReader

from models.vision_model import Qwen3VLModel
from utils.time_utils import beijing_strftime





class DualChannelParser:

    """双通道PDF解析器"""



    def __init__(self, progress_reporter=None):

        self.vision_model = Qwen3VLModel()

        self.progress_reporter = progress_reporter



    def _report_progress(self, stage: str, progress: int, message: str, data: Dict = None):

        """报告进度"""

        if self.progress_reporter:

            self.progress_reporter.report_progress(stage, progress, message, data)



    def _log(self, message: str, level: str = "info"):

        """记录日志"""

        print(f"[{level.upper()}] {message}")

        if self.progress_reporter:

            self.progress_reporter.log(message, level)



    def parse_multi_pdfs(self, pdf_paths: List[str]) -> Dict[str, Any]:
        """
        解析多个PDF文件，合并BOM后进行视觉分析

        Args:
            pdf_paths: PDF文件路径列表

        Returns:
            候选事实JSON
        """
        import os
        import re
        from pypdf import PdfReader

        print(f"🔍 开始多PDF双通道解析: {len(pdf_paths)} 个文件")

        # 步骤1：从所有PDF提取BOM（文本通道）
        print("\n" + "="*80)
        print("步骤1: 文本通道解析 - 从所有PDF提取BOM表")
        print("="*80)

        all_bom_items = []

        for i, pdf_path in enumerate(pdf_paths, 1):
            print(f"\n📄 处理第 {i}/{len(pdf_paths)} 个PDF: {os.path.basename(pdf_path)}")

            # 使用pypdf提取BOM
            bom_items = self._extract_bom_from_pdf(pdf_path)

            if bom_items:
                # 添加来源信息
                for item in bom_items:
                    item["source_pdf"] = os.path.basename(pdf_path)

                all_bom_items.extend(bom_items)
                print(f"   ✅ 提取到 {len(bom_items)} 个BOM项")
            else:
                print(f"   ⚠️  未提取到BOM项")

        print(f"\n✅ 文本通道完成，共提取 {len(all_bom_items)} 个BOM项")

        # 步骤2：合并所有PDF页面，进行视觉分析
        print("\n" + "="*80)
        print("步骤2: 视觉通道解析 - 装配专家分析（传入所有BOM上下文）")
        print("="*80)

        # 合并所有PDF的页面到临时目录
        temp_dir = tempfile.mkdtemp()
        print(f"📁 创建临时目录: {temp_dir}")

        all_image_paths = []
        total_pages = 0

        for pdf_path in pdf_paths:
            doc = fitz.open(pdf_path)
            total_pages += len(doc)

            for page_num in range(len(doc)):
                page = doc[page_num]

                # 高分辨率渲染
                mat = fitz.Matrix(3, 3)  # 3倍缩放
                pix = page.get_pixmap(matrix=mat)

                img_path = f"{temp_dir}/pdf{len(all_image_paths) + 1}_page{page_num + 1}.png"
                pix.save(img_path)
                all_image_paths.append(img_path)

            doc.close()

        print(f"📄 总页数: {total_pages}，已转换为 {len(all_image_paths)} 张图片")
        print(f"📊 BOM上下文: {len(all_bom_items)} 个零件")

        # 调用视觉模型分析所有图片
        vision_results = self._vision_channel_parse_images(
            image_paths=all_image_paths,
            bom_items=all_bom_items
        )

        # 清理临时文件
        import shutil
        shutil.rmtree(temp_dir)
        print("🗑️  已清理临时文件")

        # 合并结果
        result = {
            "bom_candidates": all_bom_items,
            "vision_channel": vision_results,
            "pdf_count": len(pdf_paths),
            "total_pages": total_pages
        }

        print("\n✅ 双通道解析完成")

        return result

    def _extract_bom_from_pdf(self, pdf_path: str) -> List[Dict]:
        """从单个PDF提取BOM表"""
        try:
            from pypdf import PdfReader
            import re

            reader = PdfReader(pdf_path)
            all_text = ""
            for page in reader.pages:
                all_text += page.extract_text() + "\n"

            bom_items = []
            seen_codes = set()
            lines = all_text.split('\n')

            for line in lines:
                if not line.strip() or '序号' in line or '物料代码' in line:
                    continue

                parts = line.split()
                if len(parts) < 4:
                    continue

                # 第一个应该是序号
                try:
                    seq = int(parts[0])
                    if not (1 <= seq <= 200):
                        continue
                except:
                    continue

                # 查找BOM代号
                code = None
                code_idx = -1
                for i, part in enumerate(parts[1:], 1):
                    if re.match(r'^\d{2}\.\d{2}\.', part):
                        code = part
                        code_idx = i
                        break

                if not code or code in seen_codes:
                    continue
                seen_codes.add(code)

                # 提取产品代号
                product_code = ""
                if code_idx + 1 < len(parts):
                    next_part = parts[code_idx + 1]
                    if any(c in next_part for c in ['-', '*', 'φ', 'Φ', 'M', 'T-']):
                        product_code = next_part

                # 提取名称
                name_start_idx = code_idx + 2 if product_code else code_idx + 1
                name_parts = []
                for i in range(name_start_idx, len(parts) - 2):
                    name_parts.append(parts[i])
                name = ' '.join(name_parts) if name_parts else "未知"

                # 提取数量
                try:
                    qty = int(parts[-2])
                    weight = float(parts[-1])
                except:
                    try:
                        qty = int(parts[-3])
                        weight = float(parts[-1])
                    except:
                        continue

                bom_items.append({
                    "seq": str(seq),
                    "code": code,
                    "product_code": product_code,
                    "name": name,
                    "specification": "",
                    "quantity": qty,
                    "weight": weight,
                    "material": ""
                })

            return bom_items
        except Exception as e:
            print(f"   ❌ BOM提取失败: {e}")
            return []

    def parse_pdf(self, pdf_path: str) -> Dict[str, Any]:

        """

        双通道解析PDF，输出候选事实JSON



        流程：先文本解析BOM → 再把BOM传给视觉模型（顺序执行）



        Args:

            pdf_path: PDF文件路径（单个PDF）或PDF文件路径列表（多个PDF）



        Returns:

            候选事实JSON，符合设计文档格式

        """

        # 支持单个PDF或多个PDF
        if isinstance(pdf_path, list):
            return self.parse_multi_pdfs(pdf_path)

        print(f"🔍 开始双通道解析: {pdf_path}")



        # 1. 基础信息提取

        doc = fitz.open(pdf_path)

        pages_info = []



        for page_num in range(len(doc)):

            page = doc[page_num]

            rect = page.rect

            pages_info.append({

                "page_id": page_num + 1,

                "width_px": int(rect.width * 4),  # 假设300DPI

                "height_px": int(rect.height * 4)

            })



        # 2. 文本通道解析（先执行）

        print("\n" + "="*80)

        print("步骤1: 文本通道解析 - 提取BOM表")

        print("="*80)

        text_channel_results = self._text_channel_parse(pdf_path, doc)

        bom_items = text_channel_results.get("bom_items", [])

        print(f"✅ 文本通道完成，提取到 {len(bom_items)} 个BOM项目")



        # 3. 视觉通道解析（后执行，传入BOM数据）

        print("\n" + "="*80)

        print("步骤2: 视觉通道解析 - 装配专家分析（传入BOM上下文）")

        print("="*80)

        vision_channel_results = self._vision_channel_parse(pdf_path, doc, bom_items)

        print(f"✅ 视觉通道完成")



        # 4. 合并为候选事实JSON

        print("\n" + "="*80)

        print("步骤3: 合并双通道结果")

        print("="*80)

        candidate_facts = self._merge_channels(

            pages_info,

            text_channel_results,

            vision_channel_results

        )



        doc.close()



        print(f"\n✅ 双通道解析完成，候选事实数量: {len(candidate_facts.get('bom_candidates', []))}")

        return candidate_facts

    

    def _text_channel_parse(self, pdf_path: str, doc) -> Dict[str, Any]:

        """文本通道：使用pypdf提取文本 + BOM解析（完全参考参考项目）"""

        print("📄 文本通道解析中...")

        print(f"[DEBUG] 文本通道 - PDF路径: {pdf_path}")



        # 报告进度：文本提取开始

        self._report_progress("pdf_bom", 10, "正在提取BOM表...", {

            "current_task": "text_extraction",

            "text_extraction": {

                "message": "pypdf文本提取中...",

                "bom_candidates": 0

            }

        })

        self._log("📄 开始PDF文本提取", "info")



        results = {

            "text_content": [],

            "bom_items": [],

            "tech_requirements": []

        }



        # 使用pypdf提取文本（参考参考项目的方法）

        try:

            reader = PdfReader(pdf_path)

        except Exception as e:

            print(f"❌ pypdf读取失败: {e}")

            return results



        # 提取所有页面文本

        text_chunks = []

        for page in reader.pages:

            page_text = page.extract_text() or ""

            if page_text:

                text_chunks.append(page_text)



        combined_text = "\n".join(text_chunks)



        # 使用参考项目的方法提取BOM项目

        bom_items = self._extract_bom_from_text(combined_text)

        results["bom_items"] = bom_items

        print(f"📦 提取到 {len(bom_items)} 个BOM项目")



        # 提取技术要求

        for page_num, text in enumerate(text_chunks):

            tech_lines = self._extract_tech_requirements(text, page_num + 1)

            results["tech_requirements"].extend(tech_lines)



        print(f"✅ 文本通道完成 - BOM: {len(results['bom_items'])}, 技术要求: {len(results['tech_requirements'])}")



        # 报告进度：文本提取完成

        self._report_progress("pdf_bom", 30, "文本提取完成", {

            "current_task": "vision_analysis",

            "text_extraction": {

                "message": "文本提取完成",

                "bom_candidates": len(bom_items)

            },

            "text_extraction_done": True

        })

        self._log(f"✅ PDF文本提取完成: {len(bom_items)}个BOM项", "success")



        return results

    

    def _vision_channel_parse_images(self, image_paths: List[str], bom_items: List[Dict]) -> Dict[str, Any]:
        """
        视觉通道：使用已有的图片路径进行装配分析

        Args:
            image_paths: 图片路径列表
            bom_items: BOM数据

        Returns:
            视觉分析结果
        """
        print("👁️ 视觉通道解析中（装配专家CoT推理模式）...")
        print(f"📊 BOM上下文: {len(bom_items)} 个零件")
        print(f"📄 图片数量: {len(image_paths)} 张")

        # 调用装配专家模型
        from prompts.agent_1_vision_prompts import build_assembly_expert_prompt

        system_prompt, user_prompt = build_assembly_expert_prompt(
            bom_context=bom_items,
            enable_cot=True
        )

        print(f"\n🤖 调用装配专家模型（CoT推理模式）")
        print(f"   📄 图纸: {len(image_paths)} 页")
        print(f"   📦 BOM: {len(bom_items)} 个零件")

        # 调用Qwen-VL
        self._log(f"🤖 Qwen-VL视觉智能体启动，分析{len(image_paths)}页图纸...", "info")

        import json

        # 准备消息（多图格式）
        content = []

        # 添加所有图片
        for img_path in image_paths:
            if img_path.startswith('http'):
                image_url = img_path
            else:
                image_url = self.vision_model.encode_image_to_base64(img_path)

            content.append({
                "type": "image_url",
                "image_url": {"url": image_url}
            })

        # 添加用户提示词
        content.append({
            "type": "text",
            "text": user_prompt
        })

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ]

        # 调用API
        print(f"   🔄 正在调用 qwen-vl-plus...")

        response = self.vision_model.client.chat.completions.create(
            model="qwen-vl-plus",
            messages=messages,
            temperature=0.1,
            max_tokens=8000,
            stream=True
        )

        # 收集响应
        answer_content = ""
        for chunk in response:
            if chunk.choices[0].delta.content:
                answer_content += chunk.choices[0].delta.content
                print(".", end="", flush=True)

        print()  # 换行

        # 解析JSON
        try:
            if "```json" in answer_content:
                json_start = answer_content.find("```json") + 7
                json_end = answer_content.find("```", json_start)
                json_str = answer_content[json_start:json_end].strip()
            else:
                json_start = answer_content.find('{')
                json_end = answer_content.rfind('}') + 1
                json_str = answer_content[json_start:json_end]

            result = json.loads(json_str)
            print(f"   ✅ JSON解析成功")

            return result

        except Exception as e:
            print(f"   ⚠️  JSON解析失败: {e}")
            return {}

    def _vision_channel_parse(self, pdf_path: str, doc, bom_items: List[Dict]) -> Dict[str, Any]:

        """

        视觉通道：多图一次性送入Qwen-VL进行装配分析



        Args:

            pdf_path: PDF文件路径

            doc: PyMuPDF文档对象

            bom_items: 文本通道提取的BOM数据

        """

        print("👁️ 视觉通道解析中（装配专家CoT推理模式）...")

        print(f"📊 BOM上下文: {len(bom_items)} 个零件")



        results = {

            "assembly_analysis": {}  # 完整的装配分析结果

        }



        # 转换所有PDF页面为图片

        temp_dir = tempfile.mkdtemp()

        print(f"📁 创建临时目录: {temp_dir}")

        print(f"📄 PDF总页数: {len(doc)}")



        image_paths = []

        for page_num in range(len(doc)):

            page = doc[page_num]

            print(f"🖼️  转换第 {page_num + 1} 页为图片...")



            # 高分辨率渲染

            mat = fitz.Matrix(3, 3)  # 3倍缩放，约225DPI

            pix = page.get_pixmap(matrix=mat)

            img_path = f"{temp_dir}/page_{page_num + 1}.png"

            pix.save(img_path)

            image_paths.append(img_path)

            print(f"   ✅ 已保存: {img_path}, 尺寸: {pix.width}x{pix.height}")



        # 报告进度：视觉分析开始

        self._report_progress("pdf_bom", 50, "🤖 Qwen-VL视觉智能体分析中...", {

            "current_task": "vision_analysis",

            "vision_analysis": {

                "message": "🤖 Qwen-VL分析图纸结构...",

                "assembly_relations": 0,

                "requirements": 0

            }

        })

        self._log(f"🤖 Qwen-VL视觉智能体启动，分析{len(image_paths)}页图纸...", "info")



        # 一次性调用视觉模型分析所有图片（传入BOM上下文）

        try:

            print(f"\n🤖 调用装配专家模型（CoT推理模式）")

            print(f"   📄 图纸: {len(image_paths)} 页")

            print(f"   📦 BOM: {len(bom_items)} 个零件")



            vision_result = self._call_assembly_expert_model(image_paths, bom_items)



            if vision_result and vision_result.get("success"):

                data = vision_result.get("result", {})



                # ✅ 新的数据结构：直接返回完整的装配分析结果

                results["assembly_analysis"] = data



                print(f"\n✅ 装配专家分析完成")

                print(f"   📋 产品总览: {data.get('product_overview', {}).get('product_name', '未知')}")

                print(f"   🔗 图号映射: {len(data.get('drawing_number_to_bom', []))} 项")

                print(f"   📍 空间关系: {len(data.get('spatial_relationships', []))} 项")

                print(f"   🔧 装配连接: {len(data.get('assembly_connections', []))} 项")

                print(f"   📏 关键尺寸: {len(data.get('critical_dimensions', []))} 项")

                print(f"   💡 装配线索: {len(data.get('assembly_sequence_hints', []))} 条")

                print(f"   🔥 焊接信息: {len(data.get('welding_info', []))} 项")



                # 报告进度：视觉分析完成

                self._report_progress("pdf_bom", 70, "视觉分析完成", {

                    "current_task": "bom_generation",

                    "vision_analysis": {

                        "message": "视觉分析完成",

                        "assembly_connections": len(data.get('assembly_connections', [])),

                        "critical_dimensions": len(data.get('critical_dimensions', []))

                    },

                    "vision_analysis_done": True

                })

                self._log(f"✅ Qwen-VL视觉分析完成: {len(data.get('assembly_connections', []))}个装配连接, {len(data.get('critical_dimensions', []))}个关键尺寸", "success")

            else:

                error_msg = vision_result.get("error", "未知错误") if vision_result else "未返回结果"

                print(f"❌ 装配专家分析失败: {error_msg}")

                self._log(f"⚠️ Qwen-VL视觉分析失败: {error_msg}", "error")

                raise RuntimeError(error_msg)



        except Exception as e:

            error_msg = f"视觉通道解析失败: {e}"

            print(f"⚠️ {error_msg}")

            import traceback

            traceback.print_exc()

            self._log(f"⚠️ {error_msg}", "error")

            raise

        finally:

            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

            print(f"🗑️  已清理临时文件")



        return results

    

    def _call_assembly_expert_model(self, image_paths: List[str], bom_items: List[Dict]) -> Dict[str, Any]:

        """

        调用装配专家模型（多图输入 + BOM上下文）- 带重试机制



        Args:

            image_paths: 所有图片路径列表

            bom_items: BOM表数据



        Returns:

            装配专家分析结果

        """

        from prompts.agent_1_vision_prompts import build_vision_prompt



        # ✅ 添加重试机制

        max_retries = 3

        last_error = None



        for attempt in range(max_retries):

            try:

                self._log(f"🤖 Qwen-VL视觉智能体启动（尝试 {attempt+1}/{max_retries}），分析{len(image_paths)}页图纸...", "info")



                # 构建系统提示词（装配专家CoT模式）

                system_prompt = build_vision_prompt(focus_areas=['assembly'])



                # 简化BOM数据，只保留关键字段

                simplified_bom = []

                for item in bom_items:

                    simplified_bom.append({

                        "seq": item.get("seq", ""),

                        "code": item.get("code", ""),

                        "name": item.get("name", ""),

                        "qty": item.get("qty", 0),

                        "weight": item.get("weight", 0)

                    })



                # 构建用户查询（使用新的视觉分析模板）
                from prompts.agent_1_vision_prompts import ASSEMBLY_USER_QUERY_TEMPLATE

                # 只提取主要结构件（BOM代号以"01."开头）
                main_parts = [item for item in simplified_bom if item.get("code", "").startswith("01.")]

                user_query = f"""我提供了这个产品的所有工程图纸（{len(image_paths)}页）和BOM表数据。

**BOM表中的主要结构件（共{len(main_parts)}个）：**

```json
{json.dumps(main_parts[:15], ensure_ascii=False, indent=2)}
```

{ASSEMBLY_USER_QUERY_TEMPLATE}

"""



                # 构建多图消息内容

                content = []



                # 添加所有图片

                for img_path in image_paths:

                    # 编码图片为base64

                    image_url = self.vision_model.encode_image_to_base64(img_path)

                    content.append({

                        "type": "image_url",

                        "image_url": {"url": image_url}

                    })



                # 添加文本查询（包含BOM）

                content.append({

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

                        "content": content

                    }

                ]



                # 调用API（使用qwen-vl-plus）

                print(f"🔄 正在调用 {self.vision_model.model_name}...")

                completion = self.vision_model.client.chat.completions.create(

                    model=self.vision_model.model_name,

                    messages=messages,

                    stream=True,

                    # ⚠️ 不限制max_tokens，让模型完整输出所有零件的装配指导
                    # max_tokens=4000,  # 之前限制导致JSON被截断

                    extra_body={

                        'enable_thinking': False,  # 装配分析不需要思考过程

                    }

                )



                # 处理流式响应

                answer_content = ""



                for chunk in completion:

                    if not chunk.choices:

                        continue



                    delta = chunk.choices[0].delta

                    if delta.content:

                        answer_content += delta.content

                        print(".", end="", flush=True)  # 显示进度



                print()  # 换行



                # 解析JSON结果（增强容错）

                # 移除markdown代码块标记

                content = answer_content.strip()

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



                    # 尝试解析JSON

                    try:

                        parsed_result = json.loads(json_str)

                        print(f"✅ JSON解析成功")

                        self._log(f"✅ Qwen-VL视觉分析完成（第{attempt+1}次尝试成功）", "success")

                    except json.JSONDecodeError as e:

                        # ✅ 修复: JSON解析失败时，抛出异常触发重试

                        error_msg = f"JSON解析失败: line {e.lineno} column {e.colno} (char {e.pos})"

                        print(f"[DEBUG] {error_msg}")

                        self._log(f"⚠️ {error_msg}（尝试 {attempt+1}/{max_retries}）", "warning")

                        raise json.JSONDecodeError(error_msg, json_str, e.pos)

                else:

                    # ✅ 修复: 未找到JSON时，抛出异常触发重试

                    error_msg = "未找到有效的JSON数据"

                    self._log(f"⚠️ {error_msg}（尝试 {attempt+1}/{max_retries}）", "warning")

                    raise ValueError(error_msg)



                # 保存输出结果到临时文件（按任务名归档到子目录）
                from utils.time_utils import beijing_now, build_debug_output_dir

                now = beijing_now()
                timestamp = now.strftime("%Y%m%d_%H%M%S")

                output_dir = build_debug_output_dir(os.getenv("TASK_ID"), now=now)

                os.makedirs(output_dir, exist_ok=True)

                output_file = os.path.join(output_dir, f"assembly_expert_output_{timestamp}.json")

                result_data = {

                    "success": True,

                    "model": self.vision_model.model_name,

                    "timestamp": timestamp,

                    "image_count": len(image_paths),

                    "attempt": attempt + 1,

                    "result": parsed_result,

                    "raw_response": answer_content

                }



                with open(output_file, 'w', encoding='utf-8') as f:

                    json.dump(result_data, f, ensure_ascii=False, indent=2)



                print(f"💾 装配专家输出已保存: {output_file}")



                # ✅ 成功解析，返回结果

                return {

                    "success": True,

                    "result": parsed_result,

                    "raw_response": answer_content

                }



            except (json.JSONDecodeError, ValueError) as e:

                # ✅ JSON解析失败，记录错误并重试

                last_error = e

                if attempt < max_retries - 1:

                    # 还有重试机会，等待后重试

                    import time

                    time.sleep(2)

                    continue

                else:

                    # 最后一次失败，抛出异常

                    error_msg = f"Qwen-VL调用失败（已重试{max_retries}次）: {str(e)}"

                    self._log(f"❌ {error_msg}", "error")

                    raise Exception(error_msg)



            except Exception as e:

                # ✅ 其他异常，记录错误并重试

                last_error = e

                print(f"❌ 调用装配专家模型异常: {e}")

                import traceback

                traceback.print_exc()



                if attempt < max_retries - 1:

                    # 还有重试机会，等待后重试

                    import time

                    time.sleep(2)

                    continue

                else:

                    # 最后一次失败，抛出异常

                    error_msg = f"Qwen-VL调用失败（已重试{max_retries}次）: {str(e)}"

                    self._log(f"❌ {error_msg}", "error")

                    raise Exception(error_msg)



        # ✅ 理论上不会到这里，但为了安全起见

        raise Exception(f"Qwen-VL调用失败: {str(last_error)}")



    def _call_vision_model_with_design_prompt(self, img_path: str, page_id: int, width: int, height: int) -> Dict[str, Any]:

        """使用设计文档中的系统提示词调用视觉模型"""

        

        # 设计文档中的系统提示词

        system_prompt = """你是"工程图视觉解析智能体"。你的职责是：从输入的工程图页面图像中，精准抽取用于装配/工艺规划的候选事实，并输出结构化 JSON。



你只做视觉与版面理解：区域定位、文字/OCR、尺寸和符号识别、BOM 表解析、编号气泡与零件对应、视图类型判定。不要做装配顺序或工艺推理。



必须遵守：

1. 可追溯：每个结论提供 evidence（page_id、region[x,y,w,h] 或 table_row）。

2. 不臆造：看不清或不确定的值用 "unknown"，并在 confidence 降低。

3. 规范输出：严格按"候选事实 JSON 契约"输出，不要输出多余文本。

4. 鲁棒 OCR：修正常见 OCR 错误，保留原文于 raw 字段。

5. 符号优先：优先识别焊接符号、形位公差、粗糙度、倒角、板厚、孔径/孔距等工程要素。



输出：仅输出候选事实 JSON，禁止其它内容。"""

        

        user_query = f"""请分析这张工程图纸（页面{page_id}，尺寸{width}x{height}），按照候选事实JSON格式输出结果。



重点识别：

1. 页面区域（标题栏、技术要求、BOM表、主视图、等轴测、局部视图）

2. BOM表格内容

3. 几何尺寸和符号

4. 编号气泡与零件对应

5. 技术要求文本



请严格按照JSON格式输出，不要添加任何解释文字。"""

        

        try:

            print(f"[DEBUG] 开始调用vision_model.analyze_engineering_drawing...")

            result = self.vision_model.analyze_engineering_drawing(

                image_path=img_path,

                focus_areas=['assembly', 'welding'],

                drawing_type='装配图',

                custom_system_prompt=system_prompt,

                custom_user_query=user_query

            )

            print(f"[DEBUG] vision_model返回: success={result.get('success')}")



            if result['success']:

                print(f"[DEBUG] 解析视觉模型结果...")

                # 尝试解析JSON结果

                if isinstance(result['result'], str):

                    parsed = json.loads(result['result'])

                    print(f"[DEBUG] JSON解析成功，keys: {parsed.keys() if isinstance(parsed, dict) else 'not dict'}")

                    return parsed

                else:

                    print(f"[DEBUG] 结果已是dict类型")

                    return result['result']

            else:

                print(f"❌ 视觉模型调用失败: {result.get('error')}")

                return {}



        except Exception as e:

            print(f"❌ 视觉模型解析异常: {e}")

            import traceback

            traceback.print_exc()

            return {}

    

    def _extract_bom_from_text(self, raw_text: str) -> List[Dict[str, Any]]:

        """

        从文本中提取BOM项目（参考参考项目的方法）



        BOM行格式通常为：

        序号 代号 名称 [材料/规格] 数量 [重量]

        例如: 53 01.09.2556 T-SPV1830-EURO-09-Q235 方形板-机加-镀锌 1 3.65

        """

        items = []



        for raw_line in raw_text.splitlines():

            line = raw_line.strip()

            if not line:

                continue



            tokens = line.split()



            # 至少需要4个token: 序号 代号 名称 数量

            if len(tokens) < 4:

                continue



            # 第一个token必须是数字（序号）

            if not tokens[0].isdigit():

                continue



            # 第二个token应该是代号（包含字母或特殊字符）

            code = tokens[1]

            if not self._looks_like_part_code(code):

                continue



            # 解析序号

            try:

                index = int(tokens[0])

            except ValueError:

                continue



            # 查找最后的数量（整数）

            qty_info = self._find_last_int(tokens)

            # 查找最后的重量（浮点数）

            weight_info = self._find_last_float(tokens)



            # 确定名称的结束位置

            desc_end = len(tokens)

            if qty_info:

                desc_end = min(desc_end, qty_info[1])

            elif weight_info:

                desc_end = min(desc_end, weight_info[1])



            # 提取名称（从第3个token到desc_end）

            name_tokens = tokens[2:desc_end]

            if not name_tokens:

                name_tokens = tokens[1:desc_end]



            item = {

                "seq": str(index),

                "code": code,

                "name": " ".join(name_tokens),

                "qty": qty_info[0] if qty_info else "unknown",

                "weight": weight_info[0] if weight_info else None,

                "raw": line,

                "source": "text_extraction",

                "confidence": 0.85

            }

            items.append(item)



        return items



    def _looks_like_part_code(self, token: str) -> bool:

        """判断token是否像零件代号"""

        # 包含字母

        if any(ch.isalpha() for ch in token):

            return True

        # 包含特殊字符

        return any(ch in "-_.*/" for ch in token)



    def _find_last_int(self, tokens: List[str]) -> Optional[tuple]:

        """从后往前查找最后一个整数"""

        for idx in range(len(tokens) - 1, -1, -1):

            token = tokens[idx]

            if token.isdigit():

                try:

                    return int(token), idx

                except ValueError:

                    continue

        return None



    def _find_last_float(self, tokens: List[str]) -> Optional[tuple]:

        """从后往前查找最后一个浮点数"""

        for idx in range(len(tokens) - 1, -1, -1):

            token = tokens[idx]

            try:

                if any(ch.isdigit() for ch in token):

                    return float(token), idx

            except ValueError:

                continue

        return None



    def _extract_tech_requirements(self, text: str, page_id: int) -> List[Dict[str, Any]]:

        """从文本中提取技术要求"""

        tech_requirements = []

        

        # 简单规则匹配技术要求

        lines = text.split('\n')

        for i, line in enumerate(lines):

            line = line.strip()

            

            # 匹配技术要求关键词

            if any(keyword in line for keyword in [

                '技术要求', '未注', '公差', '焊接', '喷涂', '热处理', 

                '表面', '精度', '材料', '标准'

            ]):

                if len(line) > 10:  # 过滤太短的行

                    tech_requirements.append({

                        "text": line,

                        "source": "text_channel",

                        "evidence": {

                            "page_id": page_id,

                            "line_number": i + 1

                        },

                        "confidence": 0.8

                    })

        

        return tech_requirements

    



    def _merge_channels(self, pages_info: List[Dict], text_results: Dict, vision_results: Dict) -> Dict[str, Any]:

        """合并双通道结果为候选事实JSON"""



        candidate_facts = {

            "pages": pages_info,

            "regions": vision_results.get("regions", []),

            "bom_candidates": [],

            "feature_candidates": vision_results.get("feature_candidates", []),

            "note_candidates": [],

            "part_bubble_candidates": vision_results.get("part_bubble_candidates", []),

            "units_notes": [{"scope": "page", "unit": "mm", "confidence": 0.95}],

            "warnings": [],

            "vision_channel": vision_results.get("assembly_analysis", {})  # 添加视觉通道的装配分析结果

        }



        # 合并BOM候选（从文本提取）

        for item in text_results.get("bom_items", []):

            candidate_facts["bom_candidates"].append(item)



        # 合并技术要求

        for tech_req in text_results.get("tech_requirements", []):

            candidate_facts["note_candidates"].append(tech_req)



        return candidate_facts

