# -*- coding: utf-8 -*-
"""
文件处理模块
处理PDF和3D模型文件
"""

import os
import json
import tempfile
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import fitz  # PyMuPDF
from PIL import Image


class PDFProcessor:
    """PDF文件处理器"""
    
    def __init__(self, dpi: int = 300):
        """
        初始化PDF处理器
        
        Args:
            dpi: 图片渲染DPI，推荐300-400
        """
        self.dpi = dpi
    
    def pdf_to_images(self, pdf_path: str, output_dir: Optional[str] = None) -> List[str]:
        """
        将PDF转换为高分辨率图片
        
        Args:
            pdf_path: PDF文件路径
            output_dir: 输出目录，如果不指定则使用临时目录
            
        Returns:
            生成的图片文件路径列表
        """
        if output_dir is None:
            output_dir = tempfile.mkdtemp()
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 打开PDF文件
        pdf_document = fitz.open(pdf_path)
        image_paths = []
        
        try:
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                
                # 设置渲染参数
                mat = fitz.Matrix(self.dpi / 72, self.dpi / 72)  # 缩放矩阵
                pix = page.get_pixmap(matrix=mat)
                
                # 保存图片
                image_path = output_dir / f"page_{page_num + 1:03d}.png"
                pix.save(str(image_path))
                image_paths.append(str(image_path))
                
                print(f"已转换第 {page_num + 1}/{len(pdf_document)} 页")
        
        finally:
            pdf_document.close()
        
        return image_paths
    
    def extract_text_content(self, pdf_path: str) -> List[Dict]:
        """
        提取PDF文本内容
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            每页的文本内容列表
        """
        pdf_document = fitz.open(pdf_path)
        text_content = []
        
        try:
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                text = page.get_text()
                
                text_content.append({
                    "page_number": page_num + 1,
                    "text": text,
                    "char_count": len(text)
                })
        
        finally:
            pdf_document.close()
        
        return text_content


class ModelProcessor:
    """3D模型文件处理器"""

    def __init__(self, blender_path: Optional[str] = None):
        """
        初始化3D模型处理器

        Args:
            blender_path: Blender可执行文件路径（保留兼容性，但优先使用trimesh）
        """
        self.blender_path = blender_path or os.getenv("BLENDER_EXE", "blender")

        # 导入trimesh用于GLB转换
        try:
            import trimesh
            self.trimesh = trimesh
            self.use_trimesh = True
        except ImportError:
            self.trimesh = None
            self.use_trimesh = False
    
    def step_to_glb(
        self,
        step_path: str,
        output_path: str,
        scale_factor: float = 1.0
    ) -> Dict:
        """
        将STEP/STL文件转换为GLB格式

        Args:
            step_path: STEP/STL文件路径
            output_path: 输出GLB文件路径
            scale_factor: 缩放因子

        Returns:
            转换结果信息
        """
        if self.use_trimesh:
            return self._convert_with_trimesh(step_path, output_path, scale_factor)
        else:
            return self._convert_with_blender(step_path, output_path, scale_factor)

    def _convert_with_trimesh(self, input_path: str, output_path: str, scale_factor: float = 1.0) -> Dict:
        """
        使用trimesh进行转换（保留装配层级）

        重要：不合并场景，保留所有零件的独立性，以便：
        1. 爆炸图动画
        2. 零件高亮显示
        3. BOM匹配
        """
        try:
            print(f"   🔄 开始加载STEP文件: {os.path.basename(input_path)}")

            # 检查文件扩展名
            file_ext = os.path.splitext(input_path)[1].lower()

            # 如果是STEP文件，检查cascadio是否可用
            if file_ext in ['.step', '.stp']:
                try:
                    import cascadio
                    print(f"   ✅ 检测到cascadio库，支持STEP文件")
                except ImportError:
                    print(f"   ⚠️  cascadio库未安装，STEP文件支持受限")
                    return {
                        "success": False,
                        "error": "STEP文件需要cascadio库支持，但该库未正确安装。建议：1) 重新构建Docker镜像 2) 或将STEP文件转换为STL格式后上传",
                        "message": "缺少STEP文件支持库"
                    }

            # 加载模型文件（force='scene'保留装配结构）
            # ✅ 添加错误处理：STEP文件格式问题
            try:
                mesh = self.trimesh.load(input_path, force='scene')
            except Exception as load_error:
                # STEP文件格式错误的特殊处理
                error_str = str(load_error)
                print(f"   ⚠️  STEP文件加载错误: {error_str}")

                # 尝试使用不同的加载方式
                print(f"   🔄 尝试使用备用加载方式...")
                try:
                    # 尝试不强制为scene
                    mesh = self.trimesh.load(input_path)
                    print(f"   ✅ 备用加载方式成功")
                except Exception as retry_error:
                    print(f"   ❌ 备用加载方式也失败: {str(retry_error)}")

                    # 如果是JSON解析错误，可能是trimesh的STEP解析器问题
                    if "unexpected" in error_str or "{" in error_str or "}" in error_str:
                        raise Exception(f"STEP文件解析失败。这可能是因为：\n1. STEP文件格式不被trimesh/cascadio支持\n2. 文件包含特殊字符或非标准格式\n3. 建议：使用CAD软件将STEP转换为STL格式后再上传")
                    else:
                        raise load_error

            if mesh.is_empty:
                return {
                    "success": False,
                    "error": f"文件 {input_path} 不包含任何几何体",
                    "message": "转换失败"
                }

            # 处理场景或单个网格
            if isinstance(mesh, self.trimesh.Scene):
                # 保留场景结构，不合并
                scene = mesh
                part_count = len(list(scene.graph.nodes_geometry))
                print(f"   📦 检测到装配体，包含 {part_count} 个零件")
            else:
                # 如果是单个网格，创建场景
                scene = self.trimesh.Scene(mesh)
                print(f"   📦 单个网格，创建场景")

            # 应用缩放
            if scale_factor != 1.0:
                scene.apply_scale(scale_factor)
                print(f"   📏 应用缩放因子: {scale_factor}")

            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # 导出GLB（保留场景层级）
            glb_data = scene.export(file_type='glb')

            # 写入文件
            with open(output_path, 'wb') as f:
                f.write(glb_data)

            # 提取零件信息
            parts_info = []
            part_count = 0

            if isinstance(scene, self.trimesh.Scene):
                for node_name in scene.graph.nodes_geometry:
                    # scene.graph[node_name] 返回 (transform_matrix, geometry_name)
                    # 但有时geometry_name可能是对象而不是字符串
                    try:
                        transform, geometry_name = scene.graph[node_name]
                        # 确保geometry_name是字符串
                        if not isinstance(geometry_name, str):
                            geometry_name = str(geometry_name)
                    except (ValueError, TypeError) as e:
                        # 如果解包失败，使用默认值
                        geometry_name = f"geometry_{len(parts_info)}"

                    parts_info.append({
                        "node_name": str(node_name),  # 确保是字符串
                        "geometry_name": geometry_name
                    })
                part_count = len(parts_info)
                print(f"   📊 提取零件信息: {part_count} 个零件")
            else:
                # 单个网格也算1个零件
                part_count = 1
                parts_info.append({
                    "node_name": "single_mesh",
                    "geometry_name": "mesh_0"
                })
                print(f"   📊 单个网格，计为1个零件")

            return {
                "success": True,
                "output_path": output_path,
                "message": "转换成功",
                "method": "trimesh",
                "log": f"使用trimesh成功转换 {input_path} -> {output_path}",
                # "scene": scene,  # ❌ 不能序列化Scene对象！会导致WebSocket错误
                "parts_count": part_count,
                "parts_info": parts_info  # 零件信息列表
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "trimesh转换失败"
            }

    def generate_explosion_data(
        self,
        glb_path: str,
        assembly_spec: Dict,
        output_dir: str
    ) -> Dict:
        """
        生成爆炸动画数据

        Args:
            glb_path: GLB文件路径
            assembly_spec: 装配规程JSON
            output_dir: 输出目录

        Returns:
            包含manifest.json路径和爆炸数据的字典
        """
        try:
            import numpy as np

            # 加载GLB文件
            scene = self.trimesh.load(glb_path)

            if not isinstance(scene, self.trimesh.Scene):
                # 单个网格，无法分解
                return {
                    "success": False,
                    "error": "模型是单个网格，无法生成爆炸动画",
                    "message": "需要包含多个零件的装配体"
                }

            # ✅ 获取所有节点（遍历所有几何体，确保不遗漏任何零件）
            # 修复：当产品STEP包含组件时，组件内的零件可能在子节点中
            # 需要遍历所有节点，而不仅仅是nodes_geometry
            node_names = []

            print(f"      🔍 开始遍历场景图节点...")
            print(f"      📊 scene.graph.nodes总数: {len(list(scene.graph.nodes))}")
            print(f"      📊 scene.graph.nodes_geometry总数: {len(list(scene.graph.nodes_geometry))}")
            print(f"      📊 scene.geometry总数: {len(scene.geometry)}")

            # ✅ 关键修复：遍历所有节点，检查每个节点是否关联了几何体
            # 这样可以捕获子装配体内的零件
            for node in scene.graph.nodes:
                try:
                    # 尝试获取节点的几何体
                    transform, geometry_name = scene.graph[node]

                    # 如果节点关联了几何体，且几何体存在于scene.geometry中
                    if geometry_name and geometry_name in scene.geometry:
                        if node not in node_names:
                            node_names.append(node)
                            # 调试：打印前10个节点
                            if len(node_names) <= 10:
                                print(f"      ✅ 节点{len(node_names)}: {node} -> {geometry_name}")
                except:
                    # 节点没有关联几何体，跳过
                    pass

            print(f"      ✅ 找到 {len(node_names)} 个零件节点（包含所有子装配体内的零件）")

            if len(node_names) < 2:
                return {
                    "success": False,
                    "error": "模型零件数量不足",
                    "message": f"只有{len(node_names)}个零件，无法生成爆炸动画"
                }

            # 计算装配体中心
            bounds = scene.bounds
            center = (bounds[0] + bounds[1]) / 2

            # ✅ 计算装配体的特征尺寸（用于爆炸距离的基准）
            assembly_size = np.linalg.norm(bounds[1] - bounds[0])

            # 🔍 调试日志：打印装配体尺寸信息
            print(f"      📏 装配体边界框: min={bounds[0]}, max={bounds[1]}")
            print(f"      📏 装配体特征尺寸: {assembly_size:.6f} 米")
            print(f"      📏 装配体中心: {center}")

            # ✅ 爆炸系数：控制整体爆炸程度
            # 修复：STEP文件单位通常是毫米，转换为米后数值很小
            # 需要使用更大的爆炸系数（50-100倍）才能在前端显示明显的爆炸效果
            explosion_factor = 100.0  # 从1.5改为100，确保爆炸距离足够大
            print(f"      🎯 爆炸系数: {explosion_factor}")
            print(f"      🎯 基础爆炸距离: {assembly_size * explosion_factor:.6f} 米 ({assembly_size * explosion_factor * 1000:.2f} 毫米)")
            print(f"      🎯 最小爆炸距离: {assembly_size * 0.3:.6f} 米")

            # 生成爆炸向量
            explosion_vectors = {}
            node_map = {}

            for i, node_name in enumerate(node_names):
                try:
                    # ✅ 关键修复：正确计算零件在世界坐标系中的位置
                    # 问题根源：STEP文件中的几何体可能已经包含了位置信息（不在原点）
                    # 需要将几何体的局部坐标通过变换矩阵转换到世界坐标

                    # 获取节点的世界变换矩阵（从world到node的累积变换）
                    world_transform_tuple = scene.graph.get(frame_to=node_name, frame_from='world')
                    if world_transform_tuple and len(world_transform_tuple) == 2:
                        world_transform = world_transform_tuple[0]  # 第一个元素是4x4变换矩阵
                        geometry_name = world_transform_tuple[1]    # 第二个元素是几何体名称
                    else:
                        # 降级方案：使用局部变换
                        world_transform, geometry_name = scene.graph[node_name]

                    # 获取几何体
                    geometry = scene.geometry[geometry_name]

                    # ✅ 使用几何体的质心（centroid）作为零件中心
                    # 注意：几何体的centroid已经在其局部坐标系中，可能不在原点
                    part_center_local = geometry.centroid

                    # ✅ 应用世界变换矩阵：world_pos = transform @ local_pos
                    # 使用齐次坐标进行变换
                    if world_transform is not None:
                        # 将3D点转换为齐次坐标 [x, y, z, 1]
                        part_center_homogeneous = np.append(part_center_local, 1.0)
                        # 应用4x4变换矩阵
                        part_center_world_homogeneous = world_transform @ part_center_homogeneous
                        # 转换回3D坐标
                        part_center = part_center_world_homogeneous[:3]
                    else:
                        part_center = part_center_local

                    # 计算爆炸方向（从装配体中心指向零件中心）
                    direction = part_center - center
                    distance_to_center = np.linalg.norm(direction)

                    # ✅ 降低阈值，因为使用边界框后，重叠的情况会减少
                    if distance_to_center > 0.0001:  # 从0.001降低到0.0001
                        direction = direction / distance_to_center
                    else:
                        # 如果零件仍然在中心，使用均匀分布的方向
                        # 使用球面均匀分布算法
                        theta = (i * 2.399963) % (2 * np.pi)  # 黄金角
                        phi = np.arccos(1 - 2 * (i + 0.5) / len(node_names))
                        direction = np.array([
                            np.sin(phi) * np.cos(theta),
                            np.sin(phi) * np.sin(theta),
                            np.cos(phi)
                        ])
                        distance_to_center = assembly_size * 0.1  # 给中心零件一个默认距离

                    # ✅ 爆炸距离策略：统一使用固定爆炸距离
                    # 原因：产品STEP文件中的组件可能作为子装配体存在，导致零件聚集
                    # 使用固定距离可以确保所有零件都能明显散开
                    explosion_distance = assembly_size * explosion_factor

                    # 调试日志（每10个零件打印一次，避免日志过多）
                    if i % 10 == 0:
                        print(f"      零件{i}: part_center={part_center}, distance_to_center={distance_to_center:.6f}, explosion_distance={explosion_distance:.6f}")

                    explosion_vectors[node_name] = {
                        "direction": direction.tolist(),
                        "distance": float(explosion_distance),
                        "original_position": part_center.tolist()
                    }

                    # 创建节点映射
                    node_map[f"part_{i:03d}"] = node_name

                except Exception as e:
                    print(f"      ⚠️  处理节点 {node_name} 时出错: {e}")
                    continue

            # 生成manifest.json
            manifest = self._generate_manifest(
                glb_path=glb_path,
                node_map=node_map,
                explosion_vectors=explosion_vectors,
                assembly_spec=assembly_spec
            )

            # 保存manifest.json
            manifest_path = os.path.join(output_dir, "manifest.json")
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)

            return {
                "success": True,
                "manifest_path": manifest_path,
                "manifest": manifest,
                "node_count": len(node_names),
                "message": f"成功生成{len(node_names)}个零件的爆炸动画数据"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "生成爆炸数据失败"
            }

    def _generate_manifest(
        self,
        glb_path: str,
        node_map: Dict,
        explosion_vectors: Dict,
        assembly_spec: Dict
    ) -> Dict:
        """
        生成manifest.json文件

        Args:
            glb_path: GLB文件路径
            node_map: 零件ID到节点名称的映射
            explosion_vectors: 爆炸向量数据
            assembly_spec: 装配规程

        Returns:
            manifest字典
        """
        # 提取装配步骤
        assembly_steps = []
        if "assembly_plan" in assembly_spec and "sequence" in assembly_spec["assembly_plan"]:
            for i, step in enumerate(assembly_spec["assembly_plan"]["sequence"]):
                # 尝试匹配零件
                involved_parts = []
                step_desc = step.get("description", "").lower()

                # 简单的零件匹配逻辑（可以根据实际情况优化）
                for part_id, node_name in node_map.items():
                    # 如果步骤描述中包含零件相关信息
                    if any(keyword in step_desc for keyword in ["安装", "装配", "固定", "连接"]):
                        involved_parts.append(part_id)

                assembly_steps.append({
                    "step_number": i + 1,
                    "description": step.get("description", ""),
                    "parts": involved_parts[:2] if involved_parts else [list(node_map.keys())[i % len(node_map)]],
                    "tools": step.get("tools", []),
                    "warnings": step.get("warnings", []),
                    "duration": step.get("duration", "5分钟")
                })

        # 生成颜色映射
        colors = {}
        color_palette = [
            "#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A",
            "#98D8C8", "#F7DC6F", "#BB8FCE", "#85C1E2"
        ]

        for i, part_id in enumerate(node_map.keys()):
            colors[part_id] = color_palette[i % len(color_palette)]

        # 构建manifest
        manifest = {
            "version": "1.0",
            "model": os.path.basename(glb_path),
            "node_map": node_map,
            "explosion_vectors": explosion_vectors,
            "steps": assembly_steps,
            "colors": colors,
            "metadata": {
                "total_parts": len(node_map),
                "total_steps": len(assembly_steps),
                "generated_at": datetime.now().isoformat()
            }
        }

        return manifest

    def _convert_with_blender(self, step_path: str, output_path: str, scale_factor: float = 1.0) -> Dict:
        """使用Blender进行转换（备用方法）"""
        # 原来的Blender转换代码保持不变
        blender_script = f"""
import bpy
import bmesh

# 清除默认场景
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# 导入STEP/STL文件
try:
    if "{step_path}".lower().endswith('.step') or "{step_path}".lower().endswith('.stp'):
        # 导入STEP文件需要CAD Sketcher插件或其他STEP导入插件
        # 这里使用通用的导入方法
        bpy.ops.import_scene.obj(filepath="{step_path}")
        print("STEP文件导入成功")
    else:
        # STL文件
        bpy.ops.import_mesh.stl(filepath="{step_path}")
        print("STL文件导入成功")
except Exception as e:
    print(f"文件导入失败: {{e}}")
    exit(1)

# 选择所有导入的对象
bpy.ops.object.select_all(action='SELECT')

# 缩放模型
if {scale_factor} != 1.0:
    bpy.ops.transform.resize(value=({scale_factor}, {scale_factor}, {scale_factor}))

# 应用变换
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# 导出GLB
bpy.ops.export_scene.gltf(
    filepath="{output_path}",
    export_format='GLB',
    export_selected=True,
    export_apply=True,
    export_materials='EXPORT',
    export_colors=True,
    export_cameras=False,
    export_lights=False
)

print("GLB导出成功")
"""

        # 保存脚本到临时文件
        script_path = tempfile.mktemp(suffix=".py")
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(blender_script)

        try:
            # 执行Blender命令
            cmd = [
                self.blender_path,
                "--background",
                "--python", script_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )

            if result.returncode == 0:
                return {
                    "success": True,
                    "output_path": output_path,
                    "message": "转换成功",
                    "method": "blender",
                    "log": result.stdout
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr,
                    "message": "转换失败"
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "转换超时",
                "message": "转换过程超过5分钟"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "转换过程出错"
            }

        finally:
            # 清理临时脚本文件
            if os.path.exists(script_path):
                os.remove(script_path)
    
    def analyze_model_structure(self, glb_path: str) -> Dict:
        """
        分析GLB模型结构
        
        Args:
            glb_path: GLB文件路径
            
        Returns:
            模型结构分析结果
        """
        # 创建Blender分析脚本
        analysis_script = f"""
import bpy
import json

# 清除默认场景
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# 导入GLB文件
bpy.ops.import_scene.gltf(filepath="{glb_path}")

# 分析模型结构
analysis_result = {{
    "objects": [],
    "materials": [],
    "total_vertices": 0,
    "total_faces": 0,
    "bounding_box": {{}}
}}

# 分析对象
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH':
        mesh_data = {{
            "name": obj.name,
            "vertices": len(obj.data.vertices),
            "faces": len(obj.data.polygons),
            "location": list(obj.location),
            "dimensions": list(obj.dimensions)
        }}
        analysis_result["objects"].append(mesh_data)
        analysis_result["total_vertices"] += mesh_data["vertices"]
        analysis_result["total_faces"] += mesh_data["faces"]

# 分析材质
for material in bpy.data.materials:
    mat_data = {{
        "name": material.name,
        "use_nodes": material.use_nodes
    }}
    analysis_result["materials"].append(mat_data)

# 计算整体包围盒
if bpy.context.scene.objects:
    bpy.ops.object.select_all(action='SELECT')
    bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
    
    # 获取包围盒
    bbox_corners = [obj.matrix_world @ mathutils.Vector(corner) for obj in bpy.context.selected_objects for corner in obj.bound_box]
    if bbox_corners:
        min_x = min(corner.x for corner in bbox_corners)
        max_x = max(corner.x for corner in bbox_corners)
        min_y = min(corner.y for corner in bbox_corners)
        max_y = max(corner.y for corner in bbox_corners)
        min_z = min(corner.z for corner in bbox_corners)
        max_z = max(corner.z for corner in bbox_corners)
        
        analysis_result["bounding_box"] = {{
            "min": [min_x, min_y, min_z],
            "max": [max_x, max_y, max_z],
            "size": [max_x - min_x, max_y - min_y, max_z - min_z]
        }}

# 输出结果
print("ANALYSIS_RESULT_START")
print(json.dumps(analysis_result, indent=2))
print("ANALYSIS_RESULT_END")
"""
        
        script_path = tempfile.mktemp(suffix=".py")
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(analysis_script)
        
        try:
            cmd = [
                self.blender_path,
                "--background",
                "--python", script_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            
            if result.returncode == 0:
                # 提取分析结果
                output = result.stdout
                start_marker = "ANALYSIS_RESULT_START"
                end_marker = "ANALYSIS_RESULT_END"
                
                start_idx = output.find(start_marker)
                end_idx = output.find(end_marker)
                
                if start_idx >= 0 and end_idx >= 0:
                    json_str = output[start_idx + len(start_marker):end_idx].strip()
                    try:
                        analysis_data = json.loads(json_str)
                        return {
                            "success": True,
                            "analysis": analysis_data
                        }
                    except json.JSONDecodeError:
                        pass
                
                return {
                    "success": False,
                    "error": "无法解析分析结果",
                    "raw_output": output
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
        
        finally:
            if os.path.exists(script_path):
                os.remove(script_path)


# 便捷函数
def process_pdf_file(pdf_path: str, output_dir: Optional[str] = None) -> Tuple[List[str], List[Dict]]:
    """
    处理PDF文件的便捷函数
    
    Args:
        pdf_path: PDF文件路径
        output_dir: 输出目录
        
    Returns:
        (图片路径列表, 文本内容列表)
    """
    processor = PDFProcessor()
    images = processor.pdf_to_images(pdf_path, output_dir)
    texts = processor.extract_text_content(pdf_path)
    return images, texts


def process_3d_model(model_path: str, output_path: str) -> Dict:
    """
    处理3D模型文件的便捷函数
    
    Args:
        model_path: 模型文件路径
        output_path: 输出GLB路径
        
    Returns:
        处理结果
    """
    processor = ModelProcessor()
    return processor.step_to_glb(model_path, output_path)
