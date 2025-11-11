# -*- coding: utf-8 -*-
"""

 vs 
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple
import fitz  # PyMuPDF


class FileClassifier:
    """"""
    
    def __init__(self):
        """初始化文件分类器"""
        # 产品总图的匹配模式：包含"产品"、"总图"、"总装"等关键词
        self.product_pattern = re.compile(r'(产品|总图|总装|product|total)', re.IGNORECASE)
        # 组件图的匹配模式："组件图1"、"组件1"、"component_1"等
        self.component_pattern = re.compile(r'(组件图?|component)[_\s]?(\d+)', re.IGNORECASE)
    
    def classify_files(
        self,
        pdf_files: List[str],
        step_files: List[str] = None
    ) -> Dict:
        """
        文件分类 - 基于文件名匹配PDF和STEP文件

        Args:
            pdf_files: PDF文件列表
            step_files: STEP文件列表

        Returns:
            {
                "product": {
                    "pdf": "产品总图.pdf",
                    "step": "产品总图.step",
                    "product_code": ""
                },
                "components": [
                    {
                        "index": 1,
                        "name": "组件图1",
                        "bom_code": "",
                        "pdf": "组件图1.pdf",
                        "step": "组件图1.step"
                    }
                ]
            }
        """
        result = {
            "product": None,
            "components": []
        }

        # 创建STEP文件名映射表（不含扩展名）
        step_name_map = {}
        if step_files:
            for step_file in step_files:
                step_name = Path(step_file).stem
                step_name_map[step_name] = step_file

        # 处理PDF文件
        for pdf_file in pdf_files:
            pdf_name = Path(pdf_file).stem  # 不含扩展名的文件名

            # 查找对应的STEP文件
            corresponding_step = step_name_map.get(pdf_name)

            # 判断是否为产品总图
            if self.product_pattern.search(pdf_name):
                result["product"] = {
                    "pdf": pdf_file,
                    "step": corresponding_step,
                    "product_code": self._extract_product_code(pdf_name)
                }
            else:
                # 其他都视为组件图
                component_info = self._parse_component_filename(pdf_name)
                # ✅ 从文件名中提取实际的序号（如"组件图1" -> 1, "组件图2" -> 2）
                component_number = self._extract_component_number(pdf_name)
                component_info["index"] = component_number if component_number else len(result["components"]) + 1
                component_info["name"] = pdf_name  # 使用文件名作为组件名
                component_info["pdf"] = pdf_file
                component_info["step"] = corresponding_step
                result["components"].append(component_info)

        # 处理没有对应PDF的STEP文件
        used_step_files = set()
        if result["product"] and result["product"]["step"]:
            used_step_files.add(result["product"]["step"])
        for comp in result["components"]:
            if comp["step"]:
                used_step_files.add(comp["step"])

        # 将剩余的STEP文件也作为组件处理
        if step_files:
            for step_file in step_files:
                if step_file not in used_step_files:
                    step_name = Path(step_file).stem
                    # 如果是产品总图但没有对应PDF
                    if self.product_pattern.search(step_name):
                        if not result["product"]:
                            result["product"] = {
                                "pdf": None,
                                "step": step_file,
                                "product_code": self._extract_product_code(step_name)
                            }
                    else:
                        # 作为组件处理
                        component_info = self._parse_component_filename(step_name)
                        # ✅ 从文件名中提取实际的序号
                        component_number = self._extract_component_number(step_name)
                        component_info["index"] = component_number if component_number else len(result["components"]) + 1
                        component_info["name"] = step_name
                        component_info["pdf"] = None
                        component_info["step"] = step_file
                        result["components"].append(component_info)

        # 按索引排序
        result["components"].sort(key=lambda x: x["index"])

        return result
    
    def _extract_product_code(self, filename: str) -> str:
        """
        
        
        Args:
            filename: 
            
        Returns:
            
        """
        #  "T-SPV1830-EURO" 
        pattern = re.compile(r'[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+', re.IGNORECASE)
        match = pattern.search(filename)
        if match:
            return match.group(0)
        return ""
    
    def _extract_component_number(self, filename: str) -> int:
        """
        从文件名中提取组件序号

        Args:
            filename: 文件名（如"组件图1", "组件图2", "component_3"）

        Returns:
            组件序号（如1, 2, 3），如果提取失败返回None
        """
        # 匹配"组件图1"、"组件1"、"component_1"等模式
        match = self.component_pattern.search(filename)
        if match:
            return int(match.group(2))
        return None

    def _parse_component_filename(self, filename: str) -> Dict:
        """


        Args:
            filename: 1__01.09.2549

        Returns:
            {
                "name": "",
                "bom_code": "01.09.2549"
            }
        """
        #
        parts = filename.split('_')

        result = {
            "name": "",
            "bom_code": ""
        }

        #
        if len(parts) >= 2:
            result["name"] = parts[1]

        # BOM01.09.xxxx
        bom_pattern = re.compile(r'\d{2}\.\d{2}\.\d+')
        for part in parts:
            match = bom_pattern.search(part)
            if match:
                result["bom_code"] = match.group(0)
                break

        return result
    
    def convert_pdfs_to_images(
        self,
        file_hierarchy: Dict,
        output_base_dir: str,
        dpi: int = 300
    ) -> Dict:
        """
        PDF
        
        Args:
            file_hierarchy: classify_files
            output_base_dir: 
            dpi: DPI
            
        Returns:
            {
                "product_images": ["/page_001.png", ...],
                "component_images": {
                    1: ["1/page_001.png", ...],
                    2: ["2/page_001.png", ...],
                    ...
                }
            }
        """
        result = {
            "product_images": [],
            "component_images": {}
        }
        
        output_base = Path(output_base_dir)
        output_base.mkdir(parents=True, exist_ok=True)
        
        # 
        if file_hierarchy["product"] and file_hierarchy["product"]["pdf"]:
            product_pdf = file_hierarchy["product"]["pdf"]
            product_dir = output_base / ""
            product_dir.mkdir(exist_ok=True)
            
            print(f"\n : {Path(product_pdf).name}")
            images = self._pdf_to_images(product_pdf, str(product_dir), dpi)
            result["product_images"] = images
            print(f"     {len(images)} ")
        
        # 
        for component in file_hierarchy["components"]:
            if component["pdf"]:
                comp_index = component["index"]
                comp_pdf = component["pdf"]
                comp_dir = output_base / f"{comp_index}"
                comp_dir.mkdir(exist_ok=True)
                
                print(f"\n {comp_index}: {Path(comp_pdf).name}")
                images = self._pdf_to_images(comp_pdf, str(comp_dir), dpi)
                # ✅ 使用字符串key，保持与JSON序列化后的一致性
                result["component_images"][str(comp_index)] = images
                print(f"     {len(images)} ")
        
        return result
    
    def _pdf_to_images(
        self,
        pdf_path: str,
        output_dir: str,
        dpi: int = 300
    ) -> List[str]:
        """
        PDF转图片（统一输出目录结构）

        Args:
            pdf_path: PDF文件路径
            output_dir: 输出根目录
            dpi: DPI分辨率

        Returns:
            图片路径列表
        """
        # ✅ Bug修复：统一输出目录结构为 output_dir/{pdf_name}/page_001.png
        pdf_name = Path(pdf_path).stem
        image_dir = Path(output_dir) / pdf_name
        image_dir.mkdir(parents=True, exist_ok=True)

        try:
            pdf_document = fitz.open(pdf_path)
        except Exception as e:
            raise ValueError(f"无法打开PDF文件 {pdf_path}: {str(e)}")

        image_paths = []

        try:
            for page_num in range(len(pdf_document)):
                try:
                    page = pdf_document[page_num]

                    # 设置渲染参数
                    mat = fitz.Matrix(dpi / 72, dpi / 72)
                    pix = page.get_pixmap(matrix=mat)

                    # 保存图片到统一目录结构
                    image_path = image_dir / f"page_{page_num + 1:03d}.png"
                    pix.save(str(image_path))
                    image_paths.append(str(image_path))
                except Exception as e:
                    print(f"⚠️ PDF {pdf_name} 第{page_num+1}页转换失败: {str(e)}")
                    continue

        finally:
            pdf_document.close()

        return image_paths

