# -*- coding: utf-8 -*-
"""
文件处理模块
处理PDF和3D模型文件
"""

import os
import json
import re
import tempfile
import subprocess
import signal
from multiprocessing import Process, Queue
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import fitz  # PyMuPDF
from PIL import Image
from utils.time_utils import beijing_now


def _terminate_process(process: Process) -> None:
    if not process.is_alive():
        return
    process.terminate()
    process.join(timeout=5)
    if not process.is_alive():
        return
    if process.pid:
        try:
            os.kill(process.pid, getattr(signal, "SIGKILL", signal.SIGTERM))
        except Exception:
            pass
    process.join(timeout=2)


def _step_has_very_long_lines(step_path: str) -> Tuple[bool, Dict[str, int]]:
    """
    预检 STEP 文本特征：超长参数行通常会让 cascadio/trimesh 的三角化复杂度爆炸。
    仅用于决定是否优先走 OCP 兜底，不改变正常模型的默认链路。
    """
    threshold = 20000
    hit_count = 1
    try:
        threshold = int(os.getenv("STEP_LONG_LINE_THRESHOLD", str(threshold)))
    except Exception:
        pass
    try:
        hit_count = int(os.getenv("STEP_LONG_LINE_HIT_COUNT", str(hit_count)))
    except Exception:
        pass

    max_len = 0
    hits = 0
    try:
        with open(step_path, "rb") as f:
            for line in f:
                length = len(line)
                if length > max_len:
                    max_len = length
                if length >= threshold:
                    hits += 1
                    if hits >= hit_count:
                        return True, {"max_len": max_len, "hits": hits, "threshold": threshold}
    except Exception:
        return False, {"max_len": 0, "hits": 0, "threshold": threshold}

    return False, {"max_len": max_len, "hits": hits, "threshold": threshold}


def _trimesh_step_to_glb_worker(in_path: str, out_path: str, scale: float, queue: Queue) -> None:
    """
    顶层 worker（Windows spawn 兼容）：用于把 trimesh.load 放到子进程里做硬超时。
    """
    try:
        import os
        import trimesh

        print(f"   🔄 开始加载STEP文件: {os.path.basename(in_path)}")

        file_ext = os.path.splitext(in_path)[1].lower()
        if file_ext in [".step", ".stp"]:
            try:
                import cascadio  # noqa: F401

                print(f"   ✅ 检测到cascadio库，支持STEP文件")
            except ImportError:
                print(f"   ⚠️  cascadio库未安装，STEP文件支持受限")
                queue.put(
                    {
                        "success": False,
                        "error": "STEP文件需要cascadio库支持，但该库未正确安装。建议：1) 重新构建Docker镜像 2) 或将STEP文件转换为STL格式后上传",
                        "message": "缺少STEP文件支持库",
                    }
                )
                return

        try:
            mesh = trimesh.load(in_path, force="scene")
        except Exception as load_error:
            error_str = str(load_error)
            print(f"   ⚠️  STEP文件加载错误: {error_str}")
            print(f"   🔄 尝试使用备用加载方式...")
            try:
                mesh = trimesh.load(in_path)
                print(f"   ✅ 备用加载方式成功")
            except Exception as retry_error:
                print(f"   ❌ 备用加载方式也失败: {str(retry_error)}")
                if "unexpected" in error_str or "{" in error_str or "}" in error_str:
                    queue.put(
                        {
                            "success": False,
                            "error": "STEP文件解析失败。这可能是因为：1. STEP文件格式不被trimesh/cascadio支持 2. 文件包含特殊字符或非标准格式 3. 建议：使用CAD软件将STEP转换为STL格式后再上传",
                            "message": "trimesh转换失败",
                        }
                    )
                else:
                    queue.put(
                        {
                            "success": False,
                            "error": error_str,
                            "message": "trimesh转换失败",
                        }
                    )
                return

        if mesh.is_empty:
            queue.put(
                {
                    "success": False,
                    "error": f"文件 {in_path} 不包含任何几何体",
                    "message": "转换失败",
                }
            )
            return

        if isinstance(mesh, trimesh.Scene):
            scene = mesh
            part_count = len(list(scene.graph.nodes_geometry))
            print(f"   📦 检测到装配体，包含 {part_count} 个零件")
        else:
            scene = trimesh.Scene(mesh)
            print(f"   📦 单个网格，创建场景")

        if scale != 1.0:
            scene.apply_scale(scale)
            print(f"   📏 应用缩放因子: {scale}")

        def _decode_name(name: str) -> str:
            if not name:
                return name
            if re.search(r"[\u4e00-\u9fff]", str(name)):
                return str(name)
            try:
                raw_bytes = str(name).encode("latin1", errors="ignore")
            except Exception:
                return str(name)
            for enc in ("gbk", "gb18030"):
                try:
                    decoded = raw_bytes.decode(enc)
                    if decoded:
                        return decoded
                except Exception:
                    continue
            return str(name)

        if isinstance(scene, trimesh.Scene):
            new_geometry = {}
            name_map = {}
            for old_name, geom in scene.geometry.items():
                fixed_name = _decode_name(old_name)
                if fixed_name in new_geometry and new_geometry[fixed_name] is not geom:
                    fixed_name = f"{fixed_name}_{len(new_geometry)}"
                new_geometry[fixed_name] = geom
                name_map[old_name] = fixed_name
            scene.geometry = new_geometry

            for node in list(scene.graph.nodes_geometry):
                try:
                    transform, geom_name = scene.graph[node]
                    fixed_geom_name = name_map.get(geom_name, _decode_name(geom_name))
                    scene.graph.update(
                        frame_from=None,
                        frame_to=node,
                        matrix=transform,
                        geometry=fixed_geom_name,
                    )
                except Exception:
                    continue

            with_geom = [n for n in scene.graph.nodes if scene.graph[n][1] is not None]
            if scene.geometry and len(with_geom) / len(scene.geometry) < 0.95:
                raise ValueError(f"节点与geometry绑定缺失：with_geom={len(with_geom)}, geometry={len(scene.geometry)}")
        else:
            mesh_name = _decode_name(getattr(scene, "metadata", {}).get("name", "mesh_0"))
            scene.metadata["name"] = mesh_name

        # 自动简化：仅在超大节点数模型触发（不影响常规模型）
        simplification_report = None
        try:
            from processors.glb_simplifier import auto_simplify_scene

            scene_simplified, simplification_report = auto_simplify_scene(scene)
            if simplification_report and simplification_report.get("applied"):
                before_n = simplification_report.get("nodes_geometry_before")
                after_n = simplification_report.get("nodes_geometry_after")
                print(f"   🧹 自动简化已应用: nodes_geometry {before_n} -> {after_n}")
                scene = scene_simplified
        except Exception as simplify_err:
            print(f"   ⚠️  自动简化失败，继续使用原模型: {simplify_err}")

        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        glb_data = scene.export(file_type="glb")
        with open(out_path, "wb") as f:
            f.write(glb_data)

        parts_info = []
        if isinstance(scene, trimesh.Scene):
            for node_name in scene.graph.nodes_geometry:
                try:
                    _, geometry_name = scene.graph[node_name]
                    if not isinstance(geometry_name, str):
                        geometry_name = str(geometry_name)
                except Exception:
                    geometry_name = f"geometry_{len(parts_info)}"
                parts_info.append({"node_name": str(node_name), "geometry_name": geometry_name})
            part_count = len(parts_info)
            print(f"   📊 提取零件信息: {part_count} 个零件")
        else:
            part_count = 1
            parts_info.append({"node_name": "single_mesh", "geometry_name": "mesh_0"})
            print(f"   📊 单个网格，计为1个零件")

        queue.put(
            {
                "success": True,
                "output_path": out_path,
                "message": "转换成功",
                "method": "trimesh",
                "log": f"使用trimesh成功转换 {in_path} -> {out_path}",
                "parts_count": part_count,
                "parts_info": parts_info,
                "simplification": simplification_report,
            }
        )
    except Exception as e:
        queue.put({"success": False, "error": str(e), "message": "trimesh转换失败"})


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
        scale_factor: float = 1.0,
        timeout_seconds: int = 120
    ) -> Dict:
        """
        将STEP/STL文件转换为GLB格式

        Args:
            step_path: STEP/STL文件路径
            output_path: 输出GLB文件路径
            scale_factor: 缩放因子
            timeout_seconds: 子进程硬超时

        Returns:
            转换结果信息
        """
        file_ext = os.path.splitext(step_path)[1].lower()
        is_step = file_ext in [".step", ".stp"]

        # ✅ 对“高风险 STEP”优先走 OCP 兜底（避免先等 trimesh 硬超时）
        prefer_ocp_first = False
        if is_step:
            prefer_ocp_first = os.getenv("STEP_TO_GLB_PREFER_OCP", "").strip().lower() in (
                "1",
                "true",
                "yes",
                "y",
                "on",
            )
            if not prefer_ocp_first:
                risky, info = _step_has_very_long_lines(step_path)
                if risky:
                    prefer_ocp_first = True
                    print(f"   ⚠️  STEP 预检命中超长行，优先走 OCP：{info}")

        if not self.use_trimesh:
            return self._convert_with_blender(step_path, output_path, scale_factor)

        ocp_attempted = False
        if prefer_ocp_first:
            ocp_attempted = True
            ocp_result = self._convert_with_ocp(step_path, output_path, scale_factor)
            if ocp_result.get("success"):
                return ocp_result

        result = self._convert_with_trimesh(
            step_path,
            output_path,
            scale_factor,
            timeout_seconds=timeout_seconds,
        )
        if result.get("success"):
            return result

        # ✅ 兜底：trimesh 超时/失败时，尝试 OCP 转换
        if is_step and not ocp_attempted:
            ocp_result = self._convert_with_ocp(step_path, output_path, scale_factor)
            if ocp_result.get("success"):
                ocp_result["fallback_from"] = {
                    "method": "trimesh",
                    "error": result.get("error"),
                    "message": result.get("message"),
                }
                return ocp_result

        return result

    def _convert_with_ocp(self, input_path: str, output_path: str, scale_factor: float = 1.0) -> Dict:
        """
        OCP(OpenCASCADE) 兜底转换：用于处理 trimesh/cascadio 卡死/失败的 STEP 文件。
        """
        try:
            from processors.ocp_step_to_glb import convert_step_to_glb_with_ocp

            return convert_step_to_glb_with_ocp(
                step_path=input_path,
                output_path=output_path,
                scale_factor=scale_factor,
            )
        except Exception as e:
            return {
                "success": False,
                "error": f"OCP 兜底转换不可用: {e}",
                "message": "ocp转换失败",
            }

    def _convert_with_trimesh(self, input_path: str, output_path: str, scale_factor: float = 1.0, timeout_seconds: int = 120) -> Dict:
        """
        使用trimesh进行转换（保留装配层级），并在独立进程中设置硬超时。
        """
        result_queue: Queue = Queue()
        process: Process = Process(
            target=_trimesh_step_to_glb_worker,
            args=(input_path, output_path, scale_factor, result_queue),
        )
        process.start()
        process.join(timeout_seconds)

        if process.is_alive():
            _terminate_process(process)
            return {
                "success": False,
                "error": f"STEP->GLB 转换超时（{timeout_seconds}s）",
                "message": "trimesh转换超时"
            }

        if result_queue.empty():
            return {
                "success": False,
                "error": "转换进程未返回结果",
                "message": "trimesh转换失败"
            }

        return result_queue.get()

    def generate_glb_inventory(
        self,
        glb_path: str,
        output_path: Optional[str] = None
    ) -> Dict:
        """
        生成 GLB 节点/几何清单，便于调试缺件问题。

        Args:
            glb_path: GLB 文件路径
            output_path: 如提供则写入文件，否则仅返回字典

        Returns:
            {
                "glb": "...",
                "nodes_total": int,
                "geometry_total": int,
                "nodes_with_geometry": int,
                "nodes_without_geometry": [...],
                "geometry_unused": [...],
                "node_to_geometry": [{"node": "...", "geometry": "..."}]
            }
        """
        try:
            scene = self.trimesh.load(glb_path, force='scene')
            if not isinstance(scene, self.trimesh.Scene):
                return {
                    "success": False,
                    "error": "GLB 不是 Scene，无法生成清单"
                }

            nodes = list(scene.graph.nodes)
            node_to_geom = []
            nodes_without = []
            used_geom = set()

            for node in nodes:
                try:
                    transform, geom_name = scene.graph[node]
                except Exception:
                    nodes_without.append(str(node))
                    continue
                if geom_name:
                    node_to_geom.append({"node": str(node), "geometry": str(geom_name)})
                    used_geom.add(str(geom_name))
                else:
                    nodes_without.append(str(node))

            all_geom = set(str(k) for k in scene.geometry.keys())
            unused_geom = sorted(all_geom - used_geom)

            # ✅ 按 NAUO 编号从小到大排序（NAUO1, NAUO2, ..., NAUO10, NAUO11, ...）
            def _extract_nauo_num(item):
                """提取 NAUO 编号用于排序"""
                node_name = item.get("node", "")
                if node_name.startswith("NAUO"):
                    try:
                        return int(node_name[4:])  # 提取 NAUO 后面的数字
                    except ValueError:
                        return float('inf')  # 无法解析的放最后
                return float('inf')  # 非 NAUO 节点放最后

            node_to_geom_sorted = sorted(node_to_geom, key=_extract_nauo_num)

            result = {
                "success": True,
                "glb": os.path.basename(glb_path),
                "nodes_total": len(nodes),
                "geometry_total": len(scene.geometry),
                "nodes_with_geometry": len(node_to_geom_sorted),
                "nodes_without_geometry": nodes_without,
                "geometry_unused": unused_geom,
                "node_to_geometry": node_to_geom_sorted
            }

            if output_path:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)

            return result
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
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
                "generated_at": beijing_now().isoformat()
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
