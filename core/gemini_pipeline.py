# -*- coding: utf-8 -*-
"""
Gemini 6-Agent工作流（生产级）
基于Gemini 2.5 Flash的装配说明书自动生成系统

架构说明：
- 支路1（PDF处理）：文件分类 → BOM提取 → Agent 1视觉规划
- 支路2（3D处理）：STEP转GLB → Agent 2 BOM-3D匹配
- 主线路：Agent 3组件装配 → Agent 4产品总装 → Agent 5焊接 → Agent 6安全FAQ → 整合输出

复用的Core组件：
- file_classifier.py - 文件分类
- hierarchical_bom_matcher_v2.py - 分层级BOM-3D匹配
- manual_integrator_v2.py - 手册整合
"""

import os
import json
import time
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# 添加项目根目录到路径
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Windows平台设置UTF-8编码（支持emoji显示）
if sys.platform == 'win32':
    import io
    # 强制设置stdout和stderr为UTF-8编码
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# 复用Core组件
from core.file_classifier import FileClassifier
from core.hierarchical_bom_matcher_v2 import HierarchicalBOMMatcher
from core.manual_integrator_v2 import ManualIntegratorV2
from core.simple_planner import SimplePlanner

# 6个Gemini Agent
from agents.component_assembly_agent import ComponentAssemblyAgent
from agents.product_assembly_agent import ProductAssemblyAgent
from agents.welding_agent import WeldingAgent
from agents.safety_faq_agent import SafetyFAQAgent

# 日志工具
from utils.logger import (
    print_step, print_substep, print_info,
    print_success, print_error, print_warning
)
from utils.time_utils import beijing_now


class GeminiAssemblyPipeline:
    """基于Gemini 2.5 Flash的6-Agent装配说明书生成工作流"""

    def __init__(self, api_key: str, output_dir: str = "pipeline_output", product_name: str = "", model_name: str = None):
        """
        初始化工作流

        Args:
            api_key: OpenRouter API密钥
            output_dir: 输出目录
            product_name: 产品名称（用户输入）
            model_name: AI模型名称（可选，如果不提供则从环境变量读取）
        """
        self.api_key = api_key
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.product_name = product_name  # ✅ 保存产品名称
        self.model_name = model_name or os.getenv("OPENROUTER_MODEL") or "google/gemini-2.0-flash-exp:free"

        # 设置API密钥和模型名称到环境变量
        os.environ["OPENROUTER_API_KEY"] = api_key
        os.environ["OPENROUTER_MODEL"] = self.model_name

        print(f"🤖 Pipeline 初始化 - 使用模型: {self.model_name}")

        # 初始化复用的Core组件
        self.file_classifier = FileClassifier()
        self.bom_matcher = HierarchicalBOMMatcher()
        self.integrator = ManualIntegratorV2(product_name=product_name)  # ✅ 传入产品名称

        # 初始化Agent - 传入model_name确保使用正确的模型
        self.component_agent = ComponentAssemblyAgent()
        self.product_agent = ProductAssemblyAgent()
        self.welding_agent = WeldingAgent()
        self.safety_agent = SafetyFAQAgent()
        self.simple_planner = SimplePlanner()
        self.is_product_mode = False  # 判定当前任务是否按产品总图流程

        # 初始化Gemini视觉模型（用于BOM提取）
        from models.gemini_model import GeminiVisionModel
        self.gemini_model = GeminiVisionModel(api_key=api_key, model_name=self.model_name)

        # 工作流状态
        self.start_time = None
        self.current_step = 0
        self.total_steps = 8
        
    def log_agent_call(self, agent_name: str, action: str, status: str = "running"):
        """记录Agent调用日志（生动的AI员工工作描述）"""
        timestamp = beijing_now().strftime("%H:%M:%S")

        if status == "running":
            print_info(f"[{timestamp}] 👷 {agent_name}AI员工加入工作，他开始{action}...")
            import sys
            sys.stdout.flush()  # 强制刷新输出
        elif status == "success":
            print_success(f"[{timestamp}] ✅ {agent_name}AI员工完成了工作，他{action}", indent=1)
            import sys
            sys.stdout.flush()
        elif status == "error":
            print_error(f"[{timestamp}] ❌ {agent_name}AI员工遇到了问题，{action}失败了", indent=1)
            import sys
            sys.stdout.flush()
    
    def run(self, pdf_dir: str, step_dir: str) -> Dict:
        """
        运行完整的工作流

        Args:
            pdf_dir: PDF文件目录
            step_dir: STEP文件目录

        Returns:
            工作流结果字典
        """
        self.start_time = time.time()

        print_step("🚀 Gemini 6-Agent装配说明书生成工作流启动")
        print_info(f"📁 输出目录: {self.output_dir}")
        print_info(f"📋 总步骤数: {self.total_steps}")
        print_info("")

        try:
            # ========== 支路1: PDF处理 ==========
            # 步骤1: 文件分类 + PDF转图片
            self.current_step = 1
            file_hierarchy, image_hierarchy = self._step1_classify_and_convert(pdf_dir, step_dir)

            # 步骤2: 从PDF提取BOM数据
            self.current_step = 2
            bom_data = self._step2_extract_bom_from_pdfs(file_hierarchy)

            # 判定模式：组件或产品（单PDF/STEP场景互斥）
            self.is_product_mode = self._determine_mode(file_hierarchy, bom_data)
            mode_label = "产品模式" if self.is_product_mode else "组件模式"
            print_info(f"🧭 判定结果: {mode_label}", indent=1)
            import sys; sys.stdout.flush()

            # 步骤3: SimplePlanner - 按BOM序号规划
            self.current_step = 3
            planning_result = self._step3_vision_planning(image_hierarchy, bom_data, file_hierarchy)
            
            # ========== 支路2: 3D处理 ==========
            # 步骤4: Agent 2 - BOM-3D匹配
            self.current_step = 4
            matching_result = self._step4_bom_3d_matching(
                step_dir, bom_data, planning_result, file_hierarchy
            )
            
            # ========== 主线路: Agent 3-6 ==========
            # 步骤5: Agent 3 - 组件装配（可复用，产品模式下跳过）
            component_results = []
            if self.is_product_mode:
                print_info("⏭️ 产品模式下跳过组件装配（Step5）", indent=1)
                import sys; sys.stdout.flush()
            else:
                self.current_step = 5
                component_results = self._step5_component_assembly(
                    file_hierarchy, image_hierarchy, planning_result, matching_result
                )
            
            # 步骤6: Agent 4 - 产品总装（仅产品模式）
            if self.is_product_mode:
                self.current_step = 6
                product_result = self._step6_product_assembly(
                    file_hierarchy, image_hierarchy, planning_result, matching_result
                )
            else:
                product_result = {}

            # 步骤7: Agent 5 & 6 - 焊接和安全（增强装配步骤）
            self.current_step = 7
            enhanced_component_results, enhanced_product_result = self._step7_welding_and_safety(
                file_hierarchy, image_hierarchy, component_results, product_result
            )

            # 步骤8: 整合最终手册
            self.current_step = 8
            final_manual = self._step8_integrate_manual(
                planning_result, enhanced_component_results, enhanced_product_result,
                matching_result, image_hierarchy  # ✅ 传入图片层级结构
            )
            
            # 计算总耗时
            elapsed_time = time.time() - self.start_time
            
            print_step("🎉 工作流完成")
            print_success(f"⏱️  总耗时: {elapsed_time:.1f}秒")
            print_success(f"📄 输出文件: {self.output_dir / 'assembly_manual.json'}")
            return {
                "success": True,
                "output_file": str(self.output_dir / "assembly_manual.json"),
                "elapsed_time": elapsed_time,
                "manual": final_manual
            }

        except Exception as e:
            print_error(f"工作流失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }

    def _determine_mode(self, file_hierarchy: Dict, bom_data: List[Dict]) -> bool:
        """
        判定当前任务是否走产品模式（True）或组件模式（False）
        规则：
        1) PDF 文件名（stem）前缀 01 → 组件模式
        2) PDF 文件名（stem）前缀 03/06/07/08 → 产品模式
        3) 其他情况默认组件模式
        """
        pdf_names = []

        product_pdf = (file_hierarchy.get("product") or {}).get("pdf")
        if product_pdf:
            pdf_names.append(Path(product_pdf).stem)

        for comp in file_hierarchy.get("components", []):
            pdf_path = comp.get("pdf")
            if pdf_path:
                pdf_names.append(Path(pdf_path).stem)
            else:
                name = comp.get("name", "")
                if name:
                    pdf_names.append(str(name))

        product_prefixes = {"03", "06", "07", "08"}
        component_prefixes = {"01"}

        found_product_prefix = False
        found_component_prefix = False

        for name in pdf_names:
            match = re.match(r"(\d{2})", name)
            if not match:
                continue
            prefix = match.group(1)
            if prefix in product_prefixes:
                found_product_prefix = True
            elif prefix in component_prefixes:
                found_component_prefix = True

        if found_product_prefix:
            return True
        if found_component_prefix:
            return False

        # 默认组件模式
        return False

    def _get_product_pdf(self, file_hierarchy: Dict) -> Optional[str]:
        """
        获取产品总图PDF路径，若未识别产品但需要产品模式，则回退到首个组件PDF
        """
        product_pdf = (file_hierarchy.get("product") or {}).get("pdf")
        if product_pdf:
            return product_pdf
        components = file_hierarchy.get("components", [])
        if components:
            return components[0].get("pdf")
        return None
    
    def _step1_classify_and_convert(self, pdf_dir: str, step_dir: str = None) -> tuple:
        """步骤1: 文件分类 + PDF转图片"""
        print_substep(f"[{self.current_step}/{self.total_steps}] 📂 文件管理员")

        self.log_agent_call("文件管理", "查看文件夹里有哪些图纸", "running")

        pdf_path = Path(pdf_dir)
        # ✅ Bug修复：同时扫描大写和小写的PDF文件
        pdf_files = [str(f) for f in pdf_path.glob("*.pdf")] + [str(f) for f in pdf_path.glob("*.PDF")]

        print_info(f"📄 他发现了 {len(pdf_files)} 个PDF图纸", indent=1)
        import sys
        sys.stdout.flush()

        self.log_agent_call("文件管理", "分辨哪些是产品总图，哪些是组件图", "running")

        # 获取STEP文件列表
        step_files = []
        if step_dir:
            step_path = Path(step_dir)
            step_files = [str(f) for f in step_path.glob("*.STEP")] + [str(f) for f in step_path.glob("*.step")] + [str(f) for f in step_path.glob("*.stp")]

        file_hierarchy = self.file_classifier.classify_files(pdf_files, step_files)

        product_name = Path(file_hierarchy['product']['pdf']).name if file_hierarchy['product'] else 'N/A'
        print_success(f"📋 他找到了产品总图: {product_name}", indent=1)
        print_success(f"🔧 他找到了 {len(file_hierarchy['components'])} 个组件图:", indent=1)

        for comp in file_hierarchy['components']:
            print_info(f"   • {comp['name']} (代号: {comp['bom_code']})", indent=2)

        sys.stdout.flush()

        # PDF转图片
        self.log_agent_call("文件管理", "把PDF转换成图片（AI需要看图片）", "running")

        images_dir = self.output_dir / "pdf_images"
        image_hierarchy = self.file_classifier.convert_pdfs_to_images(
            file_hierarchy=file_hierarchy,
            output_base_dir=str(images_dir),
            dpi=200  # 降低DPI加快速度
        )

        total_images = len(image_hierarchy.get("product_images", []))
        for comp_images in image_hierarchy.get("component_images", {}).values():
            total_images += len(comp_images)

        print_success(f"🖼️  他转换了 {total_images} 张图片", indent=1)
        sys.stdout.flush()

        self.log_agent_call("文件管理", "整理好了所有图纸和图片", "success")

        # 保存结果
        with open(self.output_dir / "step1_file_hierarchy.json", "w", encoding="utf-8") as f:
            json.dump(file_hierarchy, f, ensure_ascii=False, indent=2)

        with open(self.output_dir / "step1_image_hierarchy.json", "w", encoding="utf-8") as f:
            json.dump(image_hierarchy, f, ensure_ascii=False, indent=2)

        return file_hierarchy, image_hierarchy
    
    def _step2_extract_bom_from_pdfs(self, file_hierarchy: Dict) -> List[Dict]:
        """步骤2: 从PDF提取BOM数据（使用Gemini Vision API）"""
        print_substep(f"[{self.current_step}/{self.total_steps}] 📊 BOM数据分析员")

        self.log_agent_call("BOM分析", "从图纸中读取零件清单", "running")

        all_bom_items = []

        # 收集所有PDF文件
        all_pdfs = []
        if file_hierarchy['product']:
            all_pdfs.append(file_hierarchy['product']['pdf'])
        for comp in file_hierarchy['components']:
            all_pdfs.append(comp['pdf'])

        print_info(f"📄 他准备从 {len(all_pdfs)} 个图纸中提取零件信息", indent=1)
        import sys
        sys.stdout.flush()

        # 统计每个PDF的BOM数量
        pdf_bom_counts = {}

        # 从每个PDF提取BOM（使用Gemini Vision API）
        for pdf_path in all_pdfs:
            pdf_name = Path(pdf_path).name
            print_info(f"   📖 正在阅读: {pdf_name}", indent=1)
            sys.stdout.flush()

            try:
                # 使用Gemini Vision API提取BOM
                bom_items = self._extract_bom_with_vision(pdf_path, pdf_name)

                if bom_items:
                    all_bom_items.extend(bom_items)
                    pdf_bom_counts[pdf_name] = len(bom_items)
                    print_success(f"      提取到 {len(bom_items)} 个零件", indent=1)
                else:
                    pdf_bom_counts[pdf_name] = 0
                    print_warning(f"      未提取到零件", indent=1)

                sys.stdout.flush()

            except Exception as e:
                print_warning(f"   ⚠️  {pdf_name} 读取失败: {e}", indent=1)
                pdf_bom_counts[pdf_name] = 0
                sys.stdout.flush()

        # 显示详细统计
        print_success(f"📦 他整理出了 {len(all_bom_items)} 个零件的信息", indent=1)
        print_info(f"   详细统计:", indent=1)
        for pdf_name, count in pdf_bom_counts.items():
            print_info(f"      • {pdf_name}: {count} 个零件", indent=1)
        sys.stdout.flush()

        # ✅ 检查seq连续性
        self._check_seq_continuity(all_bom_items)

        self.log_agent_call("BOM分析", "生成了完整的零件清单", "success")

        # 保存结果
        with open(self.output_dir / "step2_bom_data.json", "w", encoding="utf-8") as f:
            json.dump(all_bom_items, f, ensure_ascii=False, indent=2)

        return all_bom_items

    def _check_seq_continuity(self, bom_items: List[Dict]) -> None:
        """检查BOM序号是否连续，警告缺失的序号"""
        if not bom_items:
            return

        # 提取所有seq并转换为整数
        seqs = set()
        for item in bom_items:
            seq_str = item.get("seq", "")
            try:
                seq_int = int(seq_str)
                seqs.add(seq_int)
            except (ValueError, TypeError):
                pass

        if not seqs:
            return

        max_seq = max(seqs)
        min_seq = min(seqs)

        # 检查缺失的序号
        expected_seqs = set(range(min_seq, max_seq + 1))
        missing_seqs = sorted(expected_seqs - seqs)

        if missing_seqs:
            print_warning(f"   ⚠️  检测到BOM序号不连续！缺失的序号: {missing_seqs}", indent=1)
            print_warning(f"   ⚠️  这可能导致匹配不完整，建议检查原始PDF", indent=1)
            sys.stdout.flush()
        else:
            print_success(f"   ✅ BOM序号连续性检查通过 (seq {min_seq}-{max_seq})", indent=1)
            sys.stdout.flush()

    def _extract_bom_with_vision(self, pdf_path: str, pdf_name: str) -> List[Dict]:
        """使用Gemini Vision API从PDF中提取BOM表"""
        import fitz
        import base64
        import io
        from PIL import Image

        # 将PDF转换为图片
        doc = fitz.open(pdf_path)
        images = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x缩放
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # 转换为base64
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            images.append(img_base64)

        doc.close()

        # 构建Gemini Vision API请求（增强版提示词）
        prompt = f"""你是一个BOM表提取专家。请从这个工程图纸中提取BOM表（零件清单）。

# 如何识别BOM表
1. 必须有"代号"列，格式为XX.XX.XXXX（至少3段，如01.09.1140）
2. 必须有"序号"列（数字1, 2, 3...）
3. 必须有"名称"列（零件名称）
4. 不要提取"工艺路线"表（只有2段如08.02）

# 输出格式
返回一个有效的JSON数组。不要markdown，不要解释，不要代码块。

示例：
[{{"seq":"1","code":"01.09.1140","product_code":"S-AB1830(72IN)-MP1140-01","name":"刷辊组件-漆后","quantity":1,"weight":76.42}}]

# 字段映射
- seq: 序号（字符串，如"1", "2", "3"）
- code: 代号（字符串，XX.XX.XXXX格式，至少3段）
- product_code: 产品代号/规格（字符串，如果没有则为空字符串""）
- name: 名称（字符串，如果没有则为空字符串""）
- quantity: 数量（整数）
- weight: 总重（浮点数，优先使用总重，否则使用单重）

# ⚠️ 重要规则（必须遵守）
1. **必须提取所有行**：不要遗漏任何一行BOM数据，每一行都很重要
2. **仔细检查表格边界**：BOM表可能跨越多行或多列，确保完整提取
3. **注意表格分隔**：如果表格有分隔线或空行，继续检查下方是否还有数据
4. 按seq序号排序（1, 2, 3...）
5. 如果没有找到BOM表，返回[]
6. 只返回有效的JSON，不要其他文本

来源PDF: {pdf_name}"""

        all_bom_items = []

        for i, img_base64 in enumerate(images):
            print_info(f"      正在分析第 {i+1}/{len(images)} 页...", indent=1)

            try:
                # 调用Gemini Vision API
                from openai import OpenAI
                client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=self.api_key
                )

                completion = client.chat.completions.create(
                    extra_headers={
                        "HTTP-Referer": "https://mecagent.com",
                        "X-Title": "MecAgent BOM Extraction"
                    },
                    model=self.model_name,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/png;base64,{img_base64}"}
                                }
                            ]
                        }
                    ],
                    temperature=0.0,
                    max_tokens=4096
                )

                response = {"content": completion.choices[0].message.content}

                # 解析响应
                content = response.get("content", "").strip()

                # 尝试提取JSON数组
                import json
                import re

                # 方法1: 直接解析
                try:
                    bom_items = json.loads(content)
                    if isinstance(bom_items, list):
                        # ✅ 添加source_pdf字段
                        for item in bom_items:
                            item["source_pdf"] = pdf_name
                        all_bom_items.extend(bom_items)
                        print_info(f"         找到 {len(bom_items)} 个零件", indent=1)
                        continue
                except:
                    pass

                # 方法2: 提取JSON数组
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    try:
                        bom_items = json.loads(json_match.group(0))
                        if isinstance(bom_items, list):
                            # ✅ 添加source_pdf字段
                            for item in bom_items:
                                item["source_pdf"] = pdf_name
                            all_bom_items.extend(bom_items)
                            print_info(f"         找到 {len(bom_items)} 个零件", indent=1)
                            continue
                    except:
                        pass

                print_info(f"         未找到BOM表", indent=1)

            except Exception as e:
                print_warning(f"      第 {i+1} 页分析失败: {e}", indent=1)
                continue

        return all_bom_items



    def _step3_vision_planning(self, image_hierarchy: Dict, bom_data: List[Dict], file_hierarchy: Dict) -> Dict:
        """步骤3: SimplePlanner - 按BOM序号规划（替代Agent1）"""
        print_substep(f"[{self.current_step}/{self.total_steps}] 🔍 装配规划师（SimplePlanner）")

        self.log_agent_call("装配规划", "按BOM序号自动生成装配规划", "running")

        import sys
        component_plans = []

        # 组件级规划
        components = file_hierarchy.get("components", [])
        for comp in components:
            comp_name = comp.get("name") or Path(comp.get("pdf", "")).stem
            comp_index = comp.get("index", len(component_plans) + 1)
            comp_pdf_stem = Path(comp.get("pdf", comp_name)).stem

            comp_bom = [item for item in bom_data if str(item.get("source_pdf", "")).startswith(comp_pdf_stem)]
            if not comp_bom:
                print_warning(f"⚠️  组件 {comp_name} 未找到BOM数据，跳过规划", indent=1)
                continue

            try:
                plan = self.simple_planner.generate_component_plan(comp_pdf_stem, comp_bom, drawing_index=comp_index)
                component_plans.append(plan.__dict__)
                print_success(f"🎯 组件规划完成: {comp_name} (序号={comp_index})", indent=1)
            except Exception as e:
                print_warning(f"⚠️ 组件 {comp_name} 规划失败: {e}", indent=1)

        # 产品级规划（仅产品模式）
        product_plan = {}
        product_pdf = self._get_product_pdf(file_hierarchy) if self.is_product_mode else None
        if self.is_product_mode and product_pdf:
            product_stem = Path(product_pdf).stem
            product_bom = [item for item in bom_data if str(item.get("source_pdf", "")).startswith(product_stem)]
            if product_bom:
                try:
                    product_plan = self.simple_planner.generate_product_plan(product_stem, product_bom)
                    print_success(f"📦 产品规划完成: {product_stem}", indent=1)
                except Exception as e:
                    print_warning(f"⚠️ 产品规划失败: {e}", indent=1)
            else:
                print_warning("⚠️ 产品总图未找到BOM数据，跳过产品规划", indent=1)
        elif self.is_product_mode and not product_pdf:
            # ✅ 产品模式下找不到产品PDF，直接终止程序
            error_msg = "❌ 产品模式下找不到产品总图，程序终止"
            print_warning(error_msg, indent=1)

            # 在失败文件第一行标注生成失败
            final_output_path = self.output_dir / f"{self.task_id}_装配说明书.md"
            with open(final_output_path, 'w', encoding='utf-8') as f:
                f.write("# ❌ 此文件生成失败\n\n")
                f.write(f"**失败原因**: 产品模式下找不到产品总图PDF文件\n\n")
                f.write(f"**解决方法**: 请确保产品总图PDF文件存在于正确路径\n")

            raise FileNotFoundError(error_msg)

        planning_result = {
            "success": True,
            "component_assembly_plan": component_plans,
            "product_assembly_plan": product_plan,
            "metadata": {
                "generated_by": "SimplePlanner",
                "generation_time": beijing_now().isoformat(),
            "components_planned": len(component_plans),
            "product_planned": bool(product_plan),
        }
        }

        # ❌ 删除step3文件保存逻辑（不再需要，因为基准件=BOM序号1）
        # with open(self.output_dir / "step3_planning_result.json", "w", encoding="utf-8") as f:
        #     json.dump(planning_result, f, ensure_ascii=False, indent=2)

        self.log_agent_call("装配规划", "完成了装配规划方案", "success")
        sys.stdout.flush()
        return planning_result

    def _step4_bom_3d_matching(
        self, step_dir: str, bom_data: List[Dict], planning_result: Dict, file_hierarchy: Dict
    ) -> Dict:
        """步骤4: Agent 2 - BOM-3D匹配"""
        print_substep(f"[{self.current_step}/{self.total_steps}] 🎨 3D模型工程师")

        self.log_agent_call("3D模型", "将STEP文件转换成网页能看的GLB格式", "running")

        component_plans = planning_result.get("component_assembly_plan", [])

        import sys
        sys.stdout.flush()

        self.log_agent_call("3D模型", "把零件清单和3D模型对应起来", "running")

        matching_result = self.bom_matcher.process_hierarchical_matching(
            step_dir=step_dir,
            bom_data=bom_data,
            component_plans=component_plans,
            output_dir=str(self.output_dir / "glb_files"),
            file_hierarchy=file_hierarchy  # ✅ 传入文件层级结构
        )

        if matching_result["success"]:
            comp_count = len(matching_result.get("component_level_mappings", {}))
            print_success(f"🔧 他处理了 {comp_count} 个组件的3D模型", indent=1)

            if matching_result.get("product_level_mapping"):
                print_success("📦 他完成了产品总装的3D模型", indent=1)

            sys.stdout.flush()
            self.log_agent_call("3D模型", "生成了所有3D模型和零件的对应关系", "success")
        else:
            self.log_agent_call("3D模型", "3D模型处理", "error")

        # 保存结果
        with open(self.output_dir / "step4_matching_result.json", "w", encoding="utf-8") as f:
            json.dump(matching_result, f, ensure_ascii=False, indent=2)

        return matching_result

    def _step5_component_assembly(
        self, file_hierarchy: Dict, image_hierarchy: Dict, planning_result: Dict, matching_result: Dict
    ) -> List[Dict]:
        """步骤5: Agent 3 - 组件装配"""
        print_substep(f"[{self.current_step}/{self.total_steps}] 🔨 组件装配工程师")

        component_plans = planning_result.get("component_assembly_plan", [])
        component_level_mappings = matching_result.get("component_level_mappings", {})

        # ✅ 读取BOM数据
        bom_data = []
        bom_file = self.output_dir / "step2_bom_data.json"
        if bom_file.exists():
            import json
            with open(bom_file, 'r', encoding='utf-8') as f:
                bom_data = json.load(f)

        component_results = []

        import sys

        for i, comp_plan in enumerate(component_plans, 1):
            comp_code = comp_plan.get("component_code", "")
            comp_name = comp_plan.get("component_name", "")
            comp_order = comp_plan.get("assembly_order", 0)

            # ✅ 获取实际的组件图序号（从matching_result中获取）
            drawing_index = comp_order  # 默认值
            if comp_code in component_level_mappings:
                drawing_index = component_level_mappings[comp_code].get("drawing_index", comp_order)

            self.log_agent_call(
                f"组件装配工 #{i}",
                f"编写【{comp_name}】的装配步骤 (图纸序号={drawing_index})",
                "running"
            )
            sys.stdout.flush()

            # ✅ 使用实际的组件图序号获取图纸
            component_images = image_hierarchy.get('component_images', {}).get(str(drawing_index), [])

            if not component_images:
                print_warning(f"未找到组件图{drawing_index}的图片", indent=1)
                # ✅ 标记为跳过状态，确保前端卡片能收到完成信号
                self.log_agent_call(
                    f"组件装配工 #{i}",
                    f"跳过了工作，因为缺少组件图片",
                    "skipped"
                )
                sys.stdout.flush()

                # ✅ 添加一个跳过的结果
                component_results.append({
                    "success": False,
                    "skipped": True,
                    "component_code": comp_code,
                    "component_name": comp_name,
                    "assembly_order": comp_order,
                    "drawing_index": drawing_index,
                    "reason": "缺少组件图片"
                })
                continue

            # ✅ 使用实际的组件图序号获取BOM列表
            # 从file_hierarchy中找到对应的组件图名称
            comp_pdf_name = None
            for comp in file_hierarchy.get("components", []):
                if comp.get("index") == drawing_index:
                    comp_pdf_name = comp.get("name", "")
                    break

            if not comp_pdf_name:
                comp_pdf_name = f"组件图{drawing_index}"

            component_bom = [
                item for item in bom_data
                if item.get("source_pdf", "").startswith(comp_pdf_name)
            ]

            # ✅ 获取组件的BOM-3D映射（宽表和旧格式都获取）
            bom_to_mesh = None
            bom_mapping_table = None

            if comp_code in component_level_mappings:
                bom_to_mesh = component_level_mappings[comp_code].get("bom_to_mesh", {})
                bom_mapping_table = component_level_mappings[comp_code].get("bom_mapping_table", None)

            # 调用Agent 3
            print_info(f"   📖 他正在研究【{comp_name}】的图纸", indent=1)
            print_info(f"   📋 组件BOM: {len(component_bom)} 个零件", indent=1)
            sys.stdout.flush()

            result = self.component_agent.process(
                component_plan=comp_plan,
                component_images=component_images,
                parts_list=component_bom,  # ✅ 传入组件的BOM列表
                bom_to_mesh_mapping=bom_to_mesh,  # 兼容旧代码
                bom_mapping_table=bom_mapping_table  # ✅ 新增：传入BOM映射宽表
            )

            if result["success"]:
                step_count = len(result.get("assembly_steps", []))
                print_success(f"   ✅ 生成了 {step_count} 个装配步骤", indent=1)
                sys.stdout.flush()
                self.log_agent_call(f"组件装配工 #{i}", f"完成了【{comp_name}】的装配说明", "success")
            else:
                self.log_agent_call(f"组件装配工 #{i}", "装配步骤编写", "error")

            # ✅ 添加组件代号、装配顺序和图纸序号到结果中（供后续步骤使用）
            result["component_code"] = comp_code
            result["component_name"] = comp_name
            result["assembly_order"] = comp_order
            result["drawing_index"] = drawing_index  # ✅ 新增：保存实际的组件图序号

            component_results.append(result)

        # ✅ 输出步骤总结
        total_components = len(component_plans)
        successful_components = sum(1 for r in component_results if r.get("success", False))
        skipped_components = sum(1 for r in component_results if r.get("skipped", False))

        print_info(f"\n📊 组件装配工程师工作总结:", indent=1)
        print_info(f"   总组件数: {total_components}", indent=1)
        print_info(f"   成功处理: {successful_components}", indent=1)
        print_info(f"   跳过: {skipped_components}", indent=1)
        sys.stdout.flush()

        # 保存结果
        with open(self.output_dir / "step5_component_results.json", "w", encoding="utf-8") as f:
            json.dump(component_results, f, ensure_ascii=False, indent=2)

        return component_results

    def _step6_product_assembly(
        self, file_hierarchy: Dict, image_hierarchy: Dict, planning_result: Dict, matching_result: Dict
    ) -> Dict:
        """步骤6: Agent 4 - 产品总装"""
        print_substep(f"[{self.current_step}/{self.total_steps}] 🏗️ 产品总装工程师")

        self.log_agent_call("产品总装", "规划如何把组件组装成最终产品", "running")

        # ✅ 使用图片而不是PDF
        product_images = image_hierarchy.get('product_images', [])

        # 若无产品图片，尝试回退到首个组件图片（单图场景）
        if not product_images:
            first_comp_images = []
            comp_images_map = image_hierarchy.get('component_images', {})
            if comp_images_map:
                first_comp_images = comp_images_map.get(next(iter(comp_images_map.keys())), [])
            if first_comp_images:
                product_images = first_comp_images
                print_warning("⚠️  没有产品总图图片，回退使用组件图作为产品图", indent=1)
            else:
                print_warning("⚠️  没有找到产品总图图片", indent=1)
                return {"success": False, "error": "No product images"}

        # ✅ 读取产品级BOM数据
        bom_data = []
        bom_file = self.output_dir / "step2_bom_data.json"
        if bom_file.exists():
            import json
            with open(bom_file, 'r', encoding='utf-8') as f:
                bom_data = json.load(f)

        # ✅ 筛选产品级BOM（从产品总图提取的零件）
        # ✅ 修改：不排除组件，组件的零件也要参与匹配
        product_pdf_stem = ""
        if file_hierarchy and file_hierarchy.get("product", {}).get("pdf"):
            product_pdf_stem = Path(file_hierarchy["product"]["pdf"]).stem

        product_bom_all = [
            item for item in bom_data
            if product_pdf_stem and str(item.get("source_pdf", "")).startswith(product_pdf_stem)
        ]

        # ✅ 新策略：包含所有BOM项（组件+零件）
        # 原因：产品总装步骤需要高亮组件内的零件，所以组件的零件也要参与匹配
        product_bom = product_bom_all

        # ✅ 获取产品级BOM-3D映射（宽表和旧格式都获取）
        product_bom_to_mesh = matching_result.get("product_level_mapping", {}).get("bom_to_mesh", {})
        product_bom_mapping_table = matching_result.get("product_level_mapping", {}).get("bom_mapping_table", None)

        import sys
        print_info(f"📋 他正在研究产品总图", indent=1)
        print_info(f"📋 产品级BOM: {len(product_bom)} 个零件", indent=1)
        sys.stdout.flush()

        result = self.product_agent.process(
            product_plan=planning_result.get("product_assembly_plan", {}),
            product_images=product_images,
            components_list=planning_result.get("component_assembly_plan", []),
            product_bom=product_bom,  # ✅ 传入产品级BOM
            bom_to_mesh_mapping=product_bom_to_mesh,  # 兼容旧代码
            bom_mapping_table=product_bom_mapping_table  # ✅ 新增：传入BOM映射宽表
        )

        if result["success"]:
            step_count = len(result.get("assembly_steps", []))
            print_success(f"✅ 生成了 {step_count} 个总装步骤", indent=1)
            sys.stdout.flush()
            self.log_agent_call("产品总装", "完成了产品总装说明", "success")
        else:
            self.log_agent_call("产品总装", "总装步骤编写", "error")

        # 保存结果
        with open(self.output_dir / "step6_product_result.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return result

    def _step7_welding_and_safety(
        self, file_hierarchy: Dict, image_hierarchy: Dict, component_results: List[Dict], product_result: Dict
    ) -> tuple:
        """
        步骤7: Agent 5 & 6 - 焊接和安全

        新逻辑：
        1. Agent 5接收装配步骤+图片，为每个步骤添加焊接要点
        2. Agent 6接收增强后的步骤，为每个步骤添加安全警告
        3. 返回增强后的组件和产品装配步骤
        """
        print_substep(f"[{self.current_step}/{self.total_steps}] ⚡ 焊接工程师 & 🛡️ 安全专员")

        # ✅ 使用图片而不是PDF
        all_images = []
        all_images.extend(image_hierarchy.get('product_images', []))
        for comp_images in image_hierarchy.get('component_images', {}).values():
            all_images.extend(comp_images)

        import sys
        sys.stdout.flush()

        # ========== Agent 5: 焊接工程师 ==========
        self.log_agent_call("焊接工程师", "为每个装配步骤添加焊接要点", "running")

        # 处理组件装配步骤
        enhanced_component_results = []
        for comp_result in component_results:
            if not comp_result.get("success"):
                enhanced_component_results.append(comp_result)
                continue

            assembly_steps = comp_result.get("assembly_steps", [])

            # ✅ 使用assembly_order来获取组件图片
            assembly_order = comp_result.get("assembly_order", "")
            component_images = image_hierarchy.get('component_images', {}).get(str(assembly_order), [])

            welding_result = self.welding_agent.process(
                all_images=component_images,
                assembly_steps=assembly_steps
            )

            # 将焊接要点嵌入到步骤中
            if welding_result.get("success"):
                enhanced_steps = welding_result.get("enhanced_steps", assembly_steps)
                comp_result["assembly_steps"] = enhanced_steps

            enhanced_component_results.append(comp_result)

        # 处理产品装配步骤
        enhanced_product_result = product_result.copy()
        if product_result.get("success"):
            product_steps = product_result.get("assembly_steps", [])
            product_images = image_hierarchy.get('product_images', [])

            welding_result = self.welding_agent.process(
                all_images=product_images,
                assembly_steps=product_steps
            )

            if welding_result.get("success"):
                enhanced_steps = welding_result.get("enhanced_steps", product_steps)
                enhanced_product_result["assembly_steps"] = enhanced_steps

        print_success(f"⚡ 焊接要点已嵌入到装配步骤中", indent=1)
        sys.stdout.flush()
        self.log_agent_call("焊接工程师", "完成焊接要点标注", "success")

        # ========== Agent 6: 安全专员 ==========
        self.log_agent_call("安全专员", "为每个装配步骤添加安全警告", "running")

        # 处理组件装配步骤
        final_component_results = []
        for comp_result in enhanced_component_results:
            if not comp_result.get("success"):
                final_component_results.append(comp_result)
                continue

            assembly_steps = comp_result.get("assembly_steps", [])

            safety_result = self.safety_agent.process(
                assembly_steps=assembly_steps
            )

            # 将安全警告嵌入到步骤中
            if safety_result.get("success"):
                enhanced_steps = safety_result.get("enhanced_steps", assembly_steps)
                comp_result["assembly_steps"] = enhanced_steps

            final_component_results.append(comp_result)

        # 处理产品装配步骤
        final_product_result = enhanced_product_result.copy()
        if enhanced_product_result.get("success"):
            product_steps = enhanced_product_result.get("assembly_steps", [])

            safety_result = self.safety_agent.process(
                assembly_steps=product_steps
            )

            if safety_result.get("success"):
                enhanced_steps = safety_result.get("enhanced_steps", product_steps)
                final_product_result["assembly_steps"] = enhanced_steps

        print_success(f"🛡️ 安全警告已嵌入到装配步骤中", indent=1)
        sys.stdout.flush()
        self.log_agent_call("安全专员", "完成安全警告标注", "success")

        # ✅ 保存增强后的结果（合并成一个文件，避免生成空文件）
        enhanced_result = {
            "type": "product" if self.is_product_mode else "component",
            "component_results": final_component_results,  # 组件模式时有数据，产品模式时为[]
            "product_result": final_product_result  # 产品模式时有数据，组件模式时为{}
        }

        with open(self.output_dir / "step7_enhanced_result.json", "w", encoding="utf-8") as f:
            json.dump(enhanced_result, f, ensure_ascii=False, indent=2)

        return final_component_results, final_product_result

    def _step8_integrate_manual(
        self,
        planning_result: Dict,
        component_results: List[Dict],
        product_result: Dict,
        matching_result: Dict,
        image_hierarchy: Dict  # ✅ 新增参数
    ) -> Dict:
        """
        步骤8: 整合最终手册

        注意：component_results和product_result已经包含了焊接和安全信息
        """
        print_substep(f"[{self.current_step}/{self.total_steps}] 📚 手册编辑员")

        self.log_agent_call("手册编辑", "把所有工程师的成果整合成一本完整的说明书", "running")

        import sys
        sys.stdout.flush()

        # ✅ 构建组件到GLB的映射（使用drawing_index而不是assembly_order）
        component_to_glb_mapping = {}
        component_level_mappings = matching_result.get("component_level_mappings", {})
        glb_files = matching_result.get("glb_files", {})

        # 从component_level_mappings构建映射，使用drawing_index
        for comp_code, mapping in component_level_mappings.items():
            # 从mapping中获取drawing_index
            drawing_index = mapping.get("drawing_index")

            if not drawing_index:
                # 如果没有drawing_index，尝试从component_results中获取
                for comp_result in component_results:
                    if comp_result.get("component_code") == comp_code:
                        drawing_index = comp_result.get("drawing_index")
                        break

            if drawing_index:
                # ✅ 使用实际的组件图序号构建GLB文件名
                glb_filename = f"component_{drawing_index}.glb"
                component_to_glb_mapping[comp_code] = glb_filename

        # 如果上面没有生成映射，且 glb_files 有组件 GLB，则兜底映射到唯一组件
        if not component_to_glb_mapping and glb_files:
            # 取第一个组件GLB
            for key, path in glb_files.items():
                if key.startswith("component"):
                    component_to_glb_mapping["default_component"] = Path(path).name
                    break

        print_info("📝 他正在整理所有内容...", indent=1)
        sys.stdout.flush()

        # ✅ 使用输出目录名作为task_id
        task_id = self.output_dir.name

        final_manual = self.integrator.integrate(
            planning_result=planning_result,
            component_assembly_results=component_results,
            product_assembly_result=product_result,
            welding_result={},  # 焊接信息已经在步骤中了
            safety_faq_result={},  # 安全信息已经在步骤中了
            component_to_glb_mapping=component_to_glb_mapping,
            component_level_mappings=component_level_mappings,  # ✅ 传入组件级别映射（包含BOM映射表）
            bom_to_mesh_mapping=matching_result.get("product_level_mapping", {}).get("bom_to_mesh", {}),
            image_hierarchy=image_hierarchy,  # ✅ 传入图片层级结构
            task_id=task_id  # ✅ 使用输出目录名作为task_id
        )

        print_success("📖 装配说明书编辑完成", indent=1)
        sys.stdout.flush()
        self.log_agent_call("手册编辑", "生成了最终的装配说明书", "success")

        # 保存最终手册
        output_file = self.output_dir / "assembly_manual.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(final_manual, f, ensure_ascii=False, indent=2)

        print_success(f"💾 保存到: {output_file}", indent=1)
        sys.stdout.flush()

        return final_manual


# ========== 测试入口 ==========
def test_gemini_pipeline():
    """测试Gemini 6-Agent工作流"""

    # 配置
    api_key = "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"
    pdf_dir = "测试-pdf"
    step_dir = "step-stl文件"
    output_dir = "pipeline_output"

    # 创建工作流实例
    pipeline = GeminiAssemblyPipeline(
        api_key=api_key,
        output_dir=output_dir
    )

    # 运行工作流
    result = pipeline.run(
        pdf_dir=pdf_dir,
        step_dir=step_dir
    )

    # 输出结果
    if result["success"]:
        print("\n" + "=" * 80)
        print("工作流执行成功！")
        print("=" * 80)
        print(f"输出文件: {result['output_file']}")
        print(f"总耗时: {result['elapsed_time']:.1f}秒")
    else:
        print("\n" + "=" * 80)
        print("工作流执行失败！")
        print("=" * 80)
        print(f"错误: {result.get('error')}")


if __name__ == "__main__":
    test_gemini_pipeline()


