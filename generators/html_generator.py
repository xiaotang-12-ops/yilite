# -*- coding: utf-8 -*-
"""
HTML装配说明书生成器
生成工人友好的交互式装配说明书
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional
from jinja2 import Template


class HTMLManualGenerator:
    """HTML装配说明书生成器"""
    
    def __init__(self):
        """初始化生成器"""
        self.template_dir = Path(__file__).parent / "templates"
        self.template_dir.mkdir(exist_ok=True)
    
    def generate_manual(
        self,
        assembly_spec: Dict,
        glb_files: List[str],
        output_dir: str,
        template_name: str = "assembly_manual.html"
    ) -> Dict:
        """
        生成HTML装配说明书
        
        Args:
            assembly_spec: 装配规程数据
            glb_files: GLB模型文件列表
            output_dir: 输出目录
            template_name: 模板文件名
            
        Returns:
            生成结果
        """
        try:
            output_path = Path(output_dir)
            
            # 确保模板存在
            template_path = self._ensure_template_exists(template_name)
            
            # 读取模板
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            template = Template(template_content)
            
            # 准备模板数据
            template_data = self._prepare_template_data(assembly_spec, glb_files)
            
            # 渲染HTML
            html_content = template.render(**template_data)
            
            # 保存HTML文件
            html_file = output_path / "assembly_manual.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # 复制静态资源
            self._copy_static_resources(output_path)
            
            # 生成配套的JSON数据文件
            data_file = output_path / "assembly_data.json"
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, ensure_ascii=False, indent=2)
            
            return {
                "success": True,
                "html_file": str(html_file),
                "data_file": str(data_file),
                "message": "HTML装配说明书生成成功"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "HTML生成失败"
            }
    
    def _prepare_template_data(self, assembly_spec: Dict, glb_files: List[str]) -> Dict:
        """准备模板数据"""
        
        # 从装配规程中提取数据
        spec_result = assembly_spec.get("result", {})
        
        # 产品信息
        product_info = spec_result.get("product_info", {
            "name": "装配产品",
            "drawing_no": "未知",
            "material_grade": "未知"
        })
        
        # BOM汇总
        bom_summary = spec_result.get("bom_summary", {
            "total_parts": 0,
            "main_materials": [],
            "critical_parts": []
        })
        
        # 装配步骤
        assembly_sequence = spec_result.get("assembly_sequence", [])
        
        # 焊接要求
        welding_requirements = spec_result.get("welding_requirements", [])
        
        # 质量控制
        quality_control = spec_result.get("quality_control", {})
        
        # 最终检验
        final_inspection = spec_result.get("final_inspection", {})
        
        # 处理装配步骤，添加序号和格式化
        processed_steps = []
        for i, step in enumerate(assembly_sequence):
            processed_step = {
                "step_number": i + 1,
                "title": step.get("title", f"步骤 {i + 1}"),
                "description": step.get("description", ""),
                "parts_involved": step.get("parts_involved", []),
                "tools_required": step.get("tools_required", []),
                "key_points": step.get("key_points", []),
                "quality_check": step.get("quality_check", []),
                "safety_notes": step.get("safety_notes", []),
                "estimated_time": step.get("estimated_time", "未知")
            }
            processed_steps.append(processed_step)
        
        # 准备3D模型数据
        models_data = []
        for glb_file in glb_files:
            models_data.append({
                "filename": glb_file,
                "path": f"models/{glb_file}",
                "name": os.path.splitext(glb_file)[0]
            })
        
        return {
            "product_info": product_info,
            "bom_summary": bom_summary,
            "assembly_steps": processed_steps,
            "welding_requirements": welding_requirements,
            "quality_control": quality_control,
            "final_inspection": final_inspection,
            "models": models_data,
            "total_steps": len(processed_steps),
            "generation_info": {
                "generator": "智能装配说明书生成系统",
                "version": "1.0.0"
            }
        }
    
    def _ensure_template_exists(self, template_name: str) -> Path:
        """确保模板文件存在"""
        template_path = self.template_dir / template_name
        
        if not template_path.exists():
            # 创建默认模板
            self._create_default_template(template_path)
        
        return template_path
    
    def _create_default_template(self, template_path: Path):
        """创建默认HTML模板"""
        default_template = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ product_info.name }} - 装配说明书</title>
    <link rel="stylesheet" href="static/style.css">
    <script type="importmap">
    {
        "imports": {
            "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
            "three/examples/jsm/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"
        }
    }
    </script>
</head>
<body>
    <header class="manual-header">
        <div class="container">
            <h1>{{ product_info.name }}</h1>
            <div class="product-meta">
                <span class="drawing-no">图号: {{ product_info.drawing_no }}</span>
                <span class="material">主材: {{ product_info.material_grade }}</span>
            </div>
        </div>
    </header>

    <nav class="step-navigation">
        <div class="container">
            <div class="nav-buttons">
                <button id="prevBtn" class="nav-btn" disabled>上一步</button>
                <span id="stepCounter" class="step-counter">1 / {{ total_steps }}</span>
                <button id="nextBtn" class="nav-btn">下一步</button>
            </div>
            <div class="progress-bar">
                <div id="progressFill" class="progress-fill"></div>
            </div>
        </div>
    </nav>

    <main class="manual-content">
        <div class="container">
            <div class="content-grid">
                <!-- 3D模型显示区域 -->
                <section class="model-viewer">
                    <div id="threejs-container" class="viewer-container">
                        <div id="loading-indicator" class="loading">
                            <div class="spinner"></div>
                            <p>正在加载3D模型...</p>
                        </div>
                    </div>
                    <div class="viewer-controls">
                        <button id="resetView" class="control-btn">重置视角</button>
                        <button id="explodeToggle" class="control-btn">爆炸视图</button>
                        <input type="range" id="explodeSlider" min="0" max="1" step="0.01" value="0" class="explode-slider">
                    </div>
                </section>

                <!-- 装配步骤区域 -->
                <section class="assembly-steps">
                    {% for step in assembly_steps %}
                    <div class="step-card" id="step-{{ step.step_number }}" {% if loop.first %}style="display: block;"{% else %}style="display: none;"{% endif %}>
                        <div class="step-header">
                            <h2>步骤 {{ step.step_number }}: {{ step.title }}</h2>
                            <span class="time-estimate">⏱️ {{ step.estimated_time }}分钟</span>
                        </div>
                        
                        <div class="step-content">
                            <div class="description">
                                <h3>操作说明</h3>
                                <p>{{ step.description }}</p>
                            </div>
                            
                            {% if step.parts_involved %}
                            <div class="parts-list">
                                <h3>涉及零件</h3>
                                <ul>
                                    {% for part in step.parts_involved %}
                                    <li class="part-item">{{ part }}</li>
                                    {% endfor %}
                                </ul>
                            </div>
                            {% endif %}
                            
                            {% if step.tools_required %}
                            <div class="tools-list">
                                <h3>所需工具</h3>
                                <ul>
                                    {% for tool in step.tools_required %}
                                    <li class="tool-item">🔧 {{ tool }}</li>
                                    {% endfor %}
                                </ul>
                            </div>
                            {% endif %}
                            
                            {% if step.key_points %}
                            <div class="key-points">
                                <h3>关键要点</h3>
                                <ul>
                                    {% for point in step.key_points %}
                                    <li class="key-point">💡 {{ point }}</li>
                                    {% endfor %}
                                </ul>
                            </div>
                            {% endif %}
                            
                            {% if step.safety_notes %}
                            <div class="safety-notes">
                                <h3>安全注意</h3>
                                <ul>
                                    {% for note in step.safety_notes %}
                                    <li class="safety-note">⚠️ {{ note }}</li>
                                    {% endfor %}
                                </ul>
                            </div>
                            {% endif %}
                            
                            {% if step.quality_check %}
                            <div class="quality-check">
                                <h3>质量检查</h3>
                                <ul>
                                    {% for check in step.quality_check %}
                                    <li class="quality-item">✓ {{ check }}</li>
                                    {% endfor %}
                                </ul>
                            </div>
                            {% endif %}
                        </div>
                    </div>
                    {% endfor %}
                </section>
            </div>
        </div>
    </main>

    <footer class="manual-footer">
        <div class="container">
            <p>{{ generation_info.generator }} v{{ generation_info.version }}</p>
        </div>
    </footer>

    <script type="module" src="static/app.js"></script>
</body>
</html>'''
        
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(default_template)
    
    def _copy_static_resources(self, output_dir: Path):
        """复制静态资源文件"""
        static_dir = output_dir / "static"
        static_dir.mkdir(exist_ok=True)
        
        # 创建CSS文件
        self._create_css_file(static_dir / "style.css")
        
        # 创建JavaScript文件
        self._create_js_file(static_dir / "app.js")
    
    def _create_css_file(self, css_path: Path):
        """创建CSS样式文件"""
        css_content = '''/* 装配说明书样式 */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Microsoft YaHei', Arial, sans-serif;
    line-height: 1.6;
    color: #333;
    background-color: #f5f5f5;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;
}

/* 头部样式 */
.manual-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 20px 0;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.manual-header h1 {
    font-size: 2.5em;
    margin-bottom: 10px;
}

.product-meta {
    display: flex;
    gap: 30px;
    font-size: 1.1em;
    opacity: 0.9;
}

/* 导航样式 */
.step-navigation {
    background: white;
    padding: 15px 0;
    border-bottom: 1px solid #ddd;
    position: sticky;
    top: 0;
    z-index: 100;
}

.nav-buttons {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 20px;
    margin-bottom: 15px;
}

.nav-btn {
    background: #667eea;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 5px;
    cursor: pointer;
    font-size: 16px;
    transition: background 0.3s;
}

.nav-btn:hover:not(:disabled) {
    background: #5a6fd8;
}

.nav-btn:disabled {
    background: #ccc;
    cursor: not-allowed;
}

.step-counter {
    font-size: 18px;
    font-weight: bold;
    color: #667eea;
}

.progress-bar {
    width: 100%;
    height: 6px;
    background: #e0e0e0;
    border-radius: 3px;
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #667eea, #764ba2);
    transition: width 0.3s ease;
    width: 0%;
}

/* 主内容样式 */
.manual-content {
    padding: 30px 0;
}

.content-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 30px;
    align-items: start;
}

/* 3D模型查看器 */
.model-viewer {
    background: white;
    border-radius: 10px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    overflow: hidden;
}

.viewer-container {
    height: 500px;
    position: relative;
    background: #f8f9fa;
}

.loading {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    text-align: center;
}

.spinner {
    width: 40px;
    height: 40px;
    border: 4px solid #f3f3f3;
    border-top: 4px solid #667eea;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto 10px;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

.viewer-controls {
    padding: 15px;
    background: #f8f9fa;
    border-top: 1px solid #e9ecef;
    display: flex;
    gap: 10px;
    align-items: center;
}

.control-btn {
    background: #6c757d;
    color: white;
    border: none;
    padding: 8px 15px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
}

.control-btn:hover {
    background: #5a6268;
}

.explode-slider {
    flex: 1;
    margin-left: 10px;
}

/* 装配步骤样式 */
.assembly-steps {
    background: white;
    border-radius: 10px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    overflow: hidden;
}

.step-card {
    padding: 25px;
}

.step-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    padding-bottom: 15px;
    border-bottom: 2px solid #667eea;
}

.step-header h2 {
    color: #667eea;
    font-size: 1.5em;
}

.time-estimate {
    background: #e3f2fd;
    color: #1976d2;
    padding: 5px 10px;
    border-radius: 15px;
    font-size: 14px;
}

.step-content > div {
    margin-bottom: 20px;
}

.step-content h3 {
    color: #333;
    margin-bottom: 10px;
    font-size: 1.1em;
    border-left: 4px solid #667eea;
    padding-left: 10px;
}

.step-content ul {
    list-style: none;
    padding-left: 0;
}

.step-content li {
    padding: 8px 0;
    border-bottom: 1px solid #f0f0f0;
}

.part-item {
    background: #f8f9fa;
    padding: 8px 12px;
    margin: 5px 0;
    border-radius: 4px;
    border-left: 3px solid #28a745;
}

.tool-item {
    background: #fff3cd;
    padding: 8px 12px;
    margin: 5px 0;
    border-radius: 4px;
    border-left: 3px solid #ffc107;
}

.key-point {
    background: #d1ecf1;
    padding: 8px 12px;
    margin: 5px 0;
    border-radius: 4px;
    border-left: 3px solid #17a2b8;
}

.safety-note {
    background: #f8d7da;
    padding: 8px 12px;
    margin: 5px 0;
    border-radius: 4px;
    border-left: 3px solid #dc3545;
}

.quality-item {
    background: #d4edda;
    padding: 8px 12px;
    margin: 5px 0;
    border-radius: 4px;
    border-left: 3px solid #28a745;
}

/* 底部样式 */
.manual-footer {
    background: #333;
    color: white;
    text-align: center;
    padding: 20px 0;
    margin-top: 50px;
}

/* 响应式设计 */
@media (max-width: 768px) {
    .content-grid {
        grid-template-columns: 1fr;
    }
    
    .nav-buttons {
        flex-direction: column;
        gap: 10px;
    }
    
    .product-meta {
        flex-direction: column;
        gap: 10px;
    }
    
    .step-header {
        flex-direction: column;
        align-items: flex-start;
        gap: 10px;
    }
}'''
        
        with open(css_path, 'w', encoding='utf-8') as f:
            f.write(css_content)

    def _create_js_file(self, js_path: Path):
        """创建JavaScript交互文件"""
        js_content = '''// 装配说明书交互脚本
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

class AssemblyManualApp {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = parseInt(document.getElementById('stepCounter').textContent.split(' / ')[1]);
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.models = [];
        this.explodeAmount = 0;

        this.init();
    }

    init() {
        this.setupNavigation();
        this.setup3DViewer();
        this.loadModels();
        this.updateProgress();
    }

    setupNavigation() {
        const prevBtn = document.getElementById('prevBtn');
        const nextBtn = document.getElementById('nextBtn');

        prevBtn.addEventListener('click', () => this.previousStep());
        nextBtn.addEventListener('click', () => this.nextStep());

        // 键盘导航
        document.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowLeft') this.previousStep();
            if (e.key === 'ArrowRight') this.nextStep();
        });
    }

    setup3DViewer() {
        const container = document.getElementById('threejs-container');
        const width = container.clientWidth;
        const height = container.clientHeight;

        // 创建场景
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0xf0f0f0);

        // 创建相机
        this.camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
        this.camera.position.set(5, 5, 5);

        // 创建渲染器
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(width, height);
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;

        container.appendChild(this.renderer.domElement);

        // 创建控制器
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;

        // 添加光照
        this.setupLighting();

        // 设置控制按钮
        this.setupViewerControls();

        // 开始渲染循环
        this.animate();

        // 响应窗口大小变化
        window.addEventListener('resize', () => this.onWindowResize());
    }

    setupLighting() {
        // 环境光
        const ambientLight = new THREE.AmbientLight(0x404040, 0.6);
        this.scene.add(ambientLight);

        // 主光源
        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(10, 10, 5);
        directionalLight.castShadow = true;
        directionalLight.shadow.mapSize.width = 2048;
        directionalLight.shadow.mapSize.height = 2048;
        this.scene.add(directionalLight);

        // 补充光源
        const fillLight = new THREE.DirectionalLight(0xffffff, 0.3);
        fillLight.position.set(-10, -10, -5);
        this.scene.add(fillLight);
    }

    setupViewerControls() {
        const resetBtn = document.getElementById('resetView');
        const explodeToggle = document.getElementById('explodeToggle');
        const explodeSlider = document.getElementById('explodeSlider');

        resetBtn.addEventListener('click', () => this.resetView());
        explodeToggle.addEventListener('click', () => this.toggleExplode());
        explodeSlider.addEventListener('input', (e) => {
            this.explodeAmount = parseFloat(e.target.value);
            this.updateExplode();
        });
    }

    async loadModels() {
        const loader = new GLTFLoader();
        const loadingIndicator = document.getElementById('loading-indicator');

        try {
            // 这里应该从assembly_data.json加载模型列表
            const response = await fetch('assembly_data.json');
            const data = await response.json();

            for (const modelInfo of data.models) {
                try {
                    const gltf = await loader.loadAsync(modelInfo.path);
                    const model = gltf.scene;

                    // 设置模型属性
                    model.userData = {
                        name: modelInfo.name,
                        originalPosition: model.position.clone()
                    };

                    // 启用阴影
                    model.traverse((child) => {
                        if (child.isMesh) {
                            child.castShadow = true;
                            child.receiveShadow = true;
                        }
                    });

                    this.scene.add(model);
                    this.models.push(model);

                } catch (error) {
                    console.warn(`加载模型失败: ${modelInfo.path}`, error);
                }
            }

            // 调整相机位置以适应模型
            this.fitCameraToModels();

        } catch (error) {
            console.error('加载模型数据失败:', error);
        } finally {
            loadingIndicator.style.display = 'none';
        }
    }

    fitCameraToModels() {
        if (this.models.length === 0) return;

        const box = new THREE.Box3();
        this.models.forEach(model => {
            box.expandByObject(model);
        });

        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);

        const distance = maxDim * 2;
        this.camera.position.set(distance, distance, distance);
        this.camera.lookAt(center);
        this.controls.target.copy(center);
        this.controls.update();
    }

    resetView() {
        this.fitCameraToModels();
        this.explodeAmount = 0;
        document.getElementById('explodeSlider').value = 0;
        this.updateExplode();
    }

    toggleExplode() {
        const slider = document.getElementById('explodeSlider');
        if (this.explodeAmount === 0) {
            slider.value = 1;
            this.explodeAmount = 1;
        } else {
            slider.value = 0;
            this.explodeAmount = 0;
        }
        this.updateExplode();
    }

    updateExplode() {
        this.models.forEach((model, index) => {
            const originalPos = model.userData.originalPosition;
            const explodeVector = new THREE.Vector3(
                (index % 3 - 1) * 2,
                Math.floor(index / 3) * 2,
                (index % 2) * 2
            );

            model.position.copy(originalPos).add(
                explodeVector.multiplyScalar(this.explodeAmount * 3)
            );
        });
    }

    previousStep() {
        if (this.currentStep > 1) {
            this.currentStep--;
            this.updateStep();
        }
    }

    nextStep() {
        if (this.currentStep < this.totalSteps) {
            this.currentStep++;
            this.updateStep();
        }
    }

    updateStep() {
        // 隐藏所有步骤
        document.querySelectorAll('.step-card').forEach(card => {
            card.style.display = 'none';
        });

        // 显示当前步骤
        const currentCard = document.getElementById(`step-${this.currentStep}`);
        if (currentCard) {
            currentCard.style.display = 'block';
        }

        // 更新导航按钮状态
        document.getElementById('prevBtn').disabled = this.currentStep === 1;
        document.getElementById('nextBtn').disabled = this.currentStep === this.totalSteps;

        // 更新步骤计数器
        document.getElementById('stepCounter').textContent = `${this.currentStep} / ${this.totalSteps}`;

        // 更新进度条
        this.updateProgress();

        // 高亮相关零件（如果有的话）
        this.highlightRelevantParts();
    }

    updateProgress() {
        const progress = (this.currentStep / this.totalSteps) * 100;
        document.getElementById('progressFill').style.width = `${progress}%`;
    }

    highlightRelevantParts() {
        // 重置所有模型的材质
        this.models.forEach(model => {
            model.traverse(child => {
                if (child.isMesh && child.material) {
                    child.material.emissive.setHex(0x000000);
                }
            });
        });

        // 这里可以根据当前步骤高亮相关零件
        // 需要根据实际的装配数据来实现
    }

    animate() {
        requestAnimationFrame(() => this.animate());

        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    }

    onWindowResize() {
        const container = document.getElementById('threejs-container');
        const width = container.clientWidth;
        const height = container.clientHeight;

        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    new AssemblyManualApp();
});'''

        with open(js_path, 'w', encoding='utf-8') as f:
            f.write(js_content)
