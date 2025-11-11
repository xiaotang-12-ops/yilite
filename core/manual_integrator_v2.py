# -*- coding: utf-8 -*-
"""
 V2.0
AgentJSON
"""

import json
from typing import Dict, List
from pathlib import Path


class ManualIntegratorV2:
    """ V2.0"""

    def __init__(self, product_name: str = ""):
        """
        Args:
            product_name: 产品名称（用户输入）
        """
        self.product_name = product_name  # ✅ 保存产品名称
    
    def integrate(
        self,
        planning_result: Dict,
        component_assembly_results: List[Dict],
        product_assembly_result: Dict,
        welding_result: Dict = None,
        safety_faq_result: Dict = None,
        bom_to_mesh_mapping: Dict = None,
        component_to_glb_mapping: Dict = None,
        component_level_mappings: Dict = None,  # ✅ 新增：组件级别映射（包含BOM映射表）
        image_hierarchy: Dict = None,  # ✅ 新增：图片层级结构
        task_id: str = None  # ✅ 新增：任务ID（用于生成API路径）
    ) -> Dict:
        """
        Agent
        
        Args:
            planning_result: Agent 1
            component_assembly_results: Agent 3
            product_assembly_result: Agent 4
            welding_result: Agent 5
            safety_faq_result: Agent 6FAQ
            bom_to_mesh_mapping: BOMmesh_id
            component_to_glb_mapping: GLB
            
        Returns:
            JSON
        """
        print(f"\n{'='*80}")
        print(f"  V2.0 - ")
        print(f"{'='*80}")
        
        #
        manual = {
            "metadata": self._build_metadata(planning_result),
            "component_assembly": self._build_component_assembly(
                component_assembly_results,
                component_to_glb_mapping,
                image_hierarchy,
                task_id
            ),
            "product_assembly": self._build_product_assembly(
                product_assembly_result,
                image_hierarchy,
                task_id
            ),
            "welding_requirements": self._build_welding(welding_result, component_assembly_results, product_assembly_result),
            "safety_and_faq": self._build_safety_faq(safety_faq_result, component_assembly_results, product_assembly_result),
            "3d_resources": self._build_3d_resources(
                bom_to_mesh_mapping,
                component_to_glb_mapping,
                component_level_mappings  # ✅ 传递组件级别映射
            )
        }
        
        print(f"\n :")
        print(f"   - : {len(manual['component_assembly'])} ")
        print(f"   - : {len(manual['product_assembly']['steps'])} ")
        print(f"   - : {len(manual['welding_requirements'])} ")
        print(f"   - : {len(manual['safety_and_faq']['safety_warnings'])} ")
        print(f"   - FAQ: {len(manual['safety_and_faq']['faq_items'])} ")
        
        return manual
    
    def _build_metadata(self, planning_result: Dict) -> Dict:
        """"""
        product_plan = planning_result.get("product_assembly_plan", {})
        component_plans = planning_result.get("component_assembly_plan", [])

        # ✅ 优先使用用户输入的产品名称，如果没有则使用AI生成的
        product_name = self.product_name or product_plan.get("product_name", "")

        return {
            "product_name": product_name,
            "total_components": len(component_plans),
            "base_component": {
                "code": product_plan.get("base_component_code", ""),
                "name": product_plan.get("base_component_name", "")
            },
            "generated_at": self._get_timestamp()
        }
    
    def _build_component_assembly(
        self,
        component_results: List[Dict],
        component_to_glb_mapping: Dict = None,
        image_hierarchy: Dict = None,
        task_id: str = None
    ) -> List[Dict]:
        """
        组件装配章节构建（增强版：添加PDF图纸路径）

        Args:
            component_results: 组件装配结果
            component_to_glb_mapping: GLB文件映射
            image_hierarchy: 图片层级结构
            task_id: 任务ID

        Returns:
            组件装配章节列表（按assembly_order排序）
        """
        chapters = []

        # ✅ 按assembly_order排序（Agent1规划的装配顺序）
        sorted_results = sorted(
            component_results,
            key=lambda x: x.get("assembly_order", 999)  # 没有order的放最后
        )

        for result in sorted_results:
            if not result.get("success"):
                continue

            component_code = result.get("component_code", "")
            component_name = result.get("component_name", "")
            assembly_order = result.get("assembly_order", "")
            drawing_index = result.get("drawing_index", "")  # ✅ 获取实际的图纸序号

            # GLB文件
            glb_file = None
            if component_to_glb_mapping and component_code in component_to_glb_mapping:
                glb_file = component_to_glb_mapping[component_code]

            # ✅ 获取组件的PDF图片路径（使用drawing_index而不是assembly_order）
            # 原因：PDF图片目录按文件名序号组织（组件图1.pdf -> pdf_images/1/）
            # 而GLB文件也按drawing_index命名（component_1.glb）
            # 必须保持一致，否则PDF和GLB会对不上
            component_images = []
            if image_hierarchy:
                # 优先使用drawing_index，如果没有则使用assembly_order作为后备
                index_to_use = drawing_index if drawing_index else assembly_order
                if index_to_use:
                    component_images = image_hierarchy.get('component_images', {}).get(str(index_to_use), [])

            # ✅ 为每个步骤添加图纸路径
            steps = result.get("assembly_steps", [])
            enhanced_steps = self._add_drawings_to_steps(steps, component_images, task_id)

            chapter = {
                "chapter_type": "component_assembly",
                "component_code": component_code,
                "component_name": component_name,
                "glb_file": glb_file,
                "drawing_index": drawing_index,  # ✅ 添加drawing_index字段
                "assembly_order": assembly_order,  # ✅ 保留assembly_order字段
                "steps": enhanced_steps,  # ✅ 使用增强后的步骤
                "3d_display_mode": "part_level_explosion"
            }

            chapters.append(chapter)

        return chapters
    
    def _build_product_assembly(
        self,
        product_result: Dict,
        image_hierarchy: Dict = None,
        task_id: str = None
    ) -> Dict:
        """
        产品总装章节构建（增强版：添加PDF图纸路径）

        Args:
            product_result: 产品装配结果
            image_hierarchy: 图片层级结构
            task_id: 任务ID

        Returns:
            产品总装章节
        """
        # ✅ 获取产品总图的PDF图片路径
        product_images = []
        if image_hierarchy:
            product_images = image_hierarchy.get('product_images', [])

        # ✅ 为每个步骤添加图纸路径
        steps = product_result.get("assembly_steps", [])
        enhanced_steps = self._add_drawings_to_steps(steps, product_images, task_id)

        return {
            "chapter_type": "product_assembly",
            "product_name": product_result.get("product_name", ""),
            "glb_file": "product_total.glb",
            "steps": enhanced_steps,  # ✅ 使用增强后的步骤
            "3d_display_mode": "component_level_explosion"
        }
    
    def _build_welding(
        self,
        welding_result: Dict = None,
        component_assembly_results: List[Dict] = None,
        product_assembly_result: Dict = None
    ) -> List[Dict]:
        """
        构建焊接要求列表

        策略：
        1. 优先使用welding_result（如果有）
        2. 否则从组件装配和产品装配步骤中提取焊接信息

        Args:
            welding_result: 焊接Agent的结果
            component_results: 组件装配结果列表
            product_result: 产品装配结果

        Returns:
            焊接要求列表
        """
        welding_list = []

        # 方法1: 从welding_result提取
        if welding_result and welding_result.get("success"):
            welding_list.extend(welding_result.get("welding_requirements", []))

        # 方法2: 从组件装配步骤中提取
        if component_assembly_results:
            for comp_result in component_assembly_results:
                if not comp_result.get("success"):
                    continue

                steps = comp_result.get("assembly_steps", [])
                for step in steps:
                    welding_info = step.get("welding")
                    if welding_info:
                        welding_list.append({
                            "step_number": step.get("step_number"),
                            "component": comp_result.get("component_name", ""),
                            "welding_info": welding_info
                        })

        # 方法3: 从产品装配步骤中提取
        if product_assembly_result and product_assembly_result.get("success"):
            steps = product_assembly_result.get("assembly_steps", [])
            for step in steps:
                welding_info = step.get("welding")
                if welding_info:
                    welding_list.append({
                        "step_number": step.get("step_number"),
                        "component": "产品总装",
                        "welding_info": welding_info
                    })

        return welding_list
    
    def _build_safety_faq(
        self,
        safety_faq_result: Dict = None,
        component_assembly_results: List[Dict] = None,
        product_assembly_result: Dict = None
    ) -> Dict:
        """
        构建安全警告和FAQ

        策略：
        1. 优先使用safety_faq_result（如果有）
        2. 否则从组件装配和产品装配步骤中提取安全警告

        Args:
            safety_faq_result: 安全FAQ Agent的结果
            component_results: 组件装配结果列表
            product_result: 产品装配结果

        Returns:
            包含safety_warnings和faq_items的字典
        """
        safety_warnings = []
        faq_items = []

        # 方法1: 从safety_faq_result提取
        if safety_faq_result and safety_faq_result.get("success"):
            safety_warnings.extend(safety_faq_result.get("safety_warnings", []))
            faq_items.extend(safety_faq_result.get("faq_items", []))

        # 方法2: 从组件装配步骤中提取安全警告
        if component_assembly_results:
            for comp_result in component_assembly_results:
                if not comp_result.get("success"):
                    continue

                steps = comp_result.get("assembly_steps", [])
                for step in steps:
                    step_warnings = step.get("safety_warnings", [])
                    if step_warnings:
                        for warning in step_warnings:
                            safety_warnings.append({
                                "step_number": step.get("step_number"),
                                "component": comp_result.get("component_name", ""),
                                "warning": warning
                            })

        # 方法3: 从产品装配步骤中提取安全警告
        if product_assembly_result and product_assembly_result.get("success"):
            steps = product_assembly_result.get("assembly_steps", [])
            for step in steps:
                step_warnings = step.get("safety_warnings", [])
                if step_warnings:
                    for warning in step_warnings:
                        safety_warnings.append({
                            "step_number": step.get("step_number"),
                            "component": "产品总装",
                            "warning": warning
                        })

        return {
            "safety_warnings": safety_warnings,
            "faq_items": faq_items
        }
    
    def _build_3d_resources(
        self,
        bom_to_mesh_mapping: Dict = None,
        component_to_glb_mapping: Dict = None,
        component_level_mappings: Dict = None
    ) -> Dict:
        """
        3D资源构建

        Args:
            bom_to_mesh_mapping: BOM到mesh_id的映射
            component_to_glb_mapping: 组件到GLB文件的映射
            component_level_mappings: 组件级别映射（包含BOM映射表）

        Returns:
            3D资源字典
        """
        return {
            "bom_to_mesh": bom_to_mesh_mapping or {},
            "component_to_glb": component_to_glb_mapping or {},
            "component_level_mappings": component_level_mappings or {},  # ✅ 添加组件级别映射
            "product_glb": "product_total.glb"
        }
    
    def _add_drawings_to_steps(
        self,
        steps: List[Dict],
        image_paths: List[str],
        task_id: str = None
    ) -> List[Dict]:
        """
        为每个步骤添加PDF图纸路径

        策略：
        1. 如果只有1张图纸，所有步骤共享这张图纸
        2. 如果有多张图纸，平均分配给各个步骤
        3. 如果图纸数量>=步骤数量，每个步骤至少1张图纸

        Args:
            steps: 装配步骤列表
            image_paths: PDF图片路径列表（本地文件路径）
            task_id: 任务ID（用于转换为API路径）

        Returns:
            增强后的步骤列表（包含drawings字段）
        """
        if not steps or not image_paths:
            return steps

        enhanced_steps = []

        # 转换本地路径为API路径
        api_image_paths = [self._convert_to_api_path(path, task_id) for path in image_paths]

        for i, step in enumerate(steps):
            step_copy = step.copy()

            # ✅ 修改策略：所有步骤都显示所有图纸（用户可以在前端查看所有图纸）
            step_copy["drawings"] = api_image_paths

            enhanced_steps.append(step_copy)

        return enhanced_steps

    def _convert_to_api_path(self, local_path: str, task_id: str = None) -> str:
        """
        将本地文件路径转换为API路径

        例如：
        输入: "pipeline_output\\pdf_images\\page_001.png"
        输出: "/api/manual/{task_id}/pdf_images/page_001.png"

        Args:
            local_path: 本地文件路径
            task_id: 任务ID

        Returns:
            API路径
        """
        # 提取pdf_images之后的路径部分
        path_obj = Path(local_path)
        parts = path_obj.parts

        # 找到pdf_images的位置
        try:
            pdf_images_idx = parts.index('pdf_images')
            # 获取pdf_images之后的所有部分
            relative_parts = parts[pdf_images_idx:]
            # 拼接为API路径
            relative_path = '/'.join(relative_parts)

            if task_id:
                return f"/api/manual/{task_id}/{relative_path}"
            else:
                return f"/api/manual/{{task_id}}/{relative_path}"
        except ValueError:
            # 如果路径中没有pdf_images，直接返回文件名
            if task_id:
                return f"/api/manual/{task_id}/pdf_images/{path_obj.name}"
            else:
                return f"/api/manual/{{task_id}}/pdf_images/{path_obj.name}"

    def _get_timestamp(self) -> str:
        """"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def save_to_file(self, manual: Dict, output_path: str):
        """
        
        
        Args:
            manual: 
            output_path: 
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(manual, f, ensure_ascii=False, indent=2)
        
        print(f"\n : {output_path}")

