# -*- coding: utf-8 -*-
"""
检查GLB文件中的mesh名称
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent))

try:
    import trimesh
    
    # 检查一个GLB文件
    glb_path = "output/fa592fac-0516-4d18-bf85-e18a12ef72e2/glb_files/product_total.glb"
    
    print(f"📦 加载GLB文件: {glb_path}")
    scene = trimesh.load(glb_path)
    
    if isinstance(scene, trimesh.Scene):
        print(f"\n✅ 这是一个场景，包含 {len(list(scene.graph.nodes_geometry))} 个节点")
        
        print(f"\n📋 前20个节点的名称:")
        for i, node_name in enumerate(list(scene.graph.nodes_geometry)[:20], 1):
            transform, geometry_name = scene.graph[node_name]
            print(f"   {i}. node_name: {node_name}")
            print(f"      geometry_name: {geometry_name}")
            print()
    else:
        print(f"\n✅ 这是一个单独的mesh")
        print(f"   mesh名称: {scene.metadata.get('name', 'N/A')}")

except ImportError:
    print("❌ trimesh未安装，尝试使用Blender...")
    
    # 使用Blender检查
    import subprocess
    import tempfile
    import json
    
    glb_path = "output/fa592fac-0516-4d18-bf85-e18a12ef72e2/glb_files/product_total.glb"
    
    script = f"""
import bpy
import json

# 清除默认场景
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# 导入GLB
bpy.ops.import_scene.gltf(filepath="{glb_path}")

# 获取所有mesh对象
meshes = []
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH':
        meshes.append({{
            "name": obj.name,
            "vertices": len(obj.data.vertices)
        }})

print("MESH_LIST_START")
print(json.dumps(meshes[:20], indent=2))
print("MESH_LIST_END")
"""
    
    script_path = tempfile.mktemp(suffix=".py")
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script)
    
    try:
        result = subprocess.run(
            ["blender", "--background", "--python", script_path],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        output = result.stdout
        start_idx = output.find("MESH_LIST_START")
        end_idx = output.find("MESH_LIST_END")
        
        if start_idx >= 0 and end_idx >= 0:
            json_str = output[start_idx + len("MESH_LIST_START"):end_idx].strip()
            meshes = json.loads(json_str)
            
            print(f"\n✅ 找到 {len(meshes)} 个mesh对象（前20个）:")
            for i, mesh in enumerate(meshes, 1):
                print(f"   {i}. {mesh['name']} ({mesh['vertices']} 顶点)")
        else:
            print("❌ 无法解析Blender输出")
            print(output)
    
    finally:
        import os
        if os.path.exists(script_path):
            os.remove(script_path)

