<template>
  <div class="home-page">
    <!-- 3D网格背景 -->
    <div ref="gridBackground" class="grid-background"></div>
    
    <!-- 3D模型背景 -->
    <div ref="threeBackground" class="three-background"></div>
    
    <!-- 主要内容 -->
    <div class="content-overlay">
      <!-- 左侧主标题区域 -->
      <div class="main-title-section">
        <h1 class="main-title">
          <div class="title-line">易力特1</div>
          <div class="title-line">AI智能装配平台</div>
        </h1>
        
        <div class="feature-list">
          <div class="feature-item">
            <span class="feature-arrow">></span>
            <span>上传图纸和3D模型</span>
          </div>
          <div class="feature-item">
            <span class="feature-arrow">></span>
            <span>AI自动识别分析</span>
          </div>
          <div class="feature-item">
            <span class="feature-arrow">></span>
            <span>生成精确装配方案</span>
          </div>
        </div>
        
        <div class="action-buttons">
          <el-button
            type="primary"
            size="large"
            @click="router.push('/generator')"
            class="start-btn"
          >
            开始工作
          </el-button>
        </div>
      </div>
      
      <!-- 右侧Agent状态区域 -->
      <div class="agent-status-section">
        <div class="agent-grid">
          <div
            v-for="agent in agentList"
            :key="agent.id"
            class="agent-item"
            :class="{ active: agent.status === 'online' }"
          >
            <div class="agent-icon">{{ agent.icon }}</div>
            <div class="agent-name">{{ agent.name }}</div>
            <div class="agent-role">AI员工</div>
            <div class="agent-indicator" :class="agent.status"></div>
          </div>
        </div>
      </div>
      
      <!-- 底部能力/流程提示 -->
      <div class="stats-section">
        <div class="stat-item">
          <div class="stat-value">6</div>
          <div class="stat-label">个AI员工协作</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">8</div>
          <div class="stat-label">个步骤全流程</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">多模态</div>
          <div class="stat-label">视觉智能体</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">3D</div>
          <div class="stat-label">组件实时显示</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useDark } from '@vueuse/core'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'

// 响应式数据
const router = useRouter()
const gridBackground = ref<HTMLElement>()
const threeBackground = ref<HTMLElement>()
const isDarkMode = useDark() // 使用全局主题状态

// 3D模型数组
const models: any[] = []

// 6个AI智能体信息
const agentList = [
  {
    id: 1,
    name: '视觉规划',
    icon: '👁️',
    status: 'online'
  },
  {
    id: 2,
    name: 'BOM匹配',
    icon: '🔗',
    status: 'online'
  },
  {
    id: 3,
    name: '组件装配',
    icon: '🔧',
    status: 'online'
  },
  {
    id: 4,
    name: '产品总装',
    icon: '🏗️',
    status: 'online'
  },
  {
    id: 5,
    name: '焊接工艺',
    icon: '⚡',
    status: 'online'
  },
  {
    id: 6,
    name: '安全FAQ',
    icon: '🛡️',
    status: 'online'
  }
]

// Three.js 相关变量
let scene: THREE.Scene
let camera: THREE.PerspectiveCamera
let renderer: THREE.WebGLRenderer
let model: THREE.Group
let animationId: number

// 网格背景变量
let gridScene: THREE.Scene
let gridCamera: THREE.PerspectiveCamera
let gridRenderer: THREE.WebGLRenderer
let gridMesh: THREE.Mesh
let gridMaterial: THREE.MeshBasicMaterial

// 初始化3D网格背景
const initGridBackground = () => {
  if (!gridBackground.value) return

  // 创建场景
  gridScene = new THREE.Scene()
  
  // 创建相机
  gridCamera = new THREE.PerspectiveCamera(
    75,
    window.innerWidth / window.innerHeight,
    0.1,
    1000
  )
  gridCamera.position.set(0, 5, 10)
  gridCamera.lookAt(0, 0, 0)

  // 创建渲染器
  gridRenderer = new THREE.WebGLRenderer({ 
    antialias: true, 
    alpha: true 
  })
  gridRenderer.setSize(window.innerWidth, window.innerHeight)
  gridRenderer.setClearColor(isDarkMode.value ? 0x0a0a0a : 0xf5f5f5, 1)
  gridBackground.value.appendChild(gridRenderer.domElement)

  // 创建网格
  const gridSize = 50
  const gridDivisions = 50
  const gridHelper = new THREE.GridHelper(gridSize, gridDivisions, 0x00ffff, 0x004466)
  gridScene.add(gridHelper)

  // 添加线条效果
  const geometry = new THREE.PlaneGeometry(100, 100, 50, 50)
  gridMaterial = new THREE.MeshBasicMaterial({
    color: isDarkMode.value ? 0x00ffff : 0x0066cc,
    wireframe: true,
    transparent: true,
    opacity: isDarkMode.value ? 0.12 : 0.15
  })
  gridMesh = new THREE.Mesh(geometry, gridMaterial)
  gridMesh.rotation.x = -Math.PI / 2
  gridScene.add(gridMesh)

  // 开始渲染循环
  animateGrid()
}

// 网格动画
const animateGrid = () => {
  animationId = requestAnimationFrame(animateGrid)
  
  // 旋转网格
  if (gridMesh) {
    gridMesh.rotation.z += 0.002
  }
  
  // 相机运动
  const time = Date.now() * 0.0005
  gridCamera.position.x = Math.cos(time) * 15
  gridCamera.position.z = Math.sin(time) * 15
  gridCamera.lookAt(0, 0, 0)
  
  gridRenderer.render(gridScene, gridCamera)
}

// 初始化3D模型背景
const init3DBackground = () => {
  if (!threeBackground.value) return

  // 创建场景
  scene = new THREE.Scene()
  
  // 创建相机
  camera = new THREE.PerspectiveCamera(
    75,
    window.innerWidth / window.innerHeight,
    0.1,
    1000
  )
  camera.position.set(15, 15, 15)

  // 创建渲染器
  renderer = new THREE.WebGLRenderer({ 
    antialias: true, 
    alpha: true 
  })
  renderer.setSize(window.innerWidth, window.innerHeight)
  renderer.setClearColor(0x000000, 0)
  threeBackground.value.appendChild(renderer.domElement)

  // 添加光源
  const ambientLight = new THREE.AmbientLight(0x404040, 0.4)
  scene.add(ambientLight)

  const directionalLight = new THREE.DirectionalLight(0xff6600, 1)
  directionalLight.position.set(10, 10, 5)
  scene.add(directionalLight)

  // 先创建备用几何体，确保有3D内容显示
  createFallbackGeometry()

  // 然后尝试加载GLB模型
  loadBackgroundModel()

  // 开始渲染循环
  animate3D()
}

// 加载背景3D模型
const loadBackgroundModel = () => {
  const loader = new GLTFLoader()

  console.log('开始加载3D模型...')

  loader.load(
    '/产品测试.glb',
    (gltf) => {
      console.log('3D模型加载成功:', gltf)

      // 创建多个模型实例
      for (let i = 0; i < 3; i++) {
        const modelClone = gltf.scene.clone()

        // 设置不同的位置和大小 - 分散到屏幕各个角落
        const positions = [
          { x: -26, y: 12, z: -12, scale: 8 },  // 左上更远
          { x: 22, y: -4, z: -14, scale: 6 },   // 右下
          { x: 18, y: 18, z: -22, scale: 7 }    // 右上更远
        ]

        const pos = positions[i]
        const box = new THREE.Box3().setFromObject(modelClone)
        const size = box.getSize(new THREE.Vector3())
        const maxDim = Math.max(size.x, size.y, size.z)
        const scale = pos.scale / maxDim

        modelClone.scale.set(scale, scale, scale)
        modelClone.position.set(pos.x, pos.y, pos.z)

        // 设置不同的材质颜色 - 更亮的颜色
        const colors = [0xff8800, 0x00ddff, 0xff4488]
        const opacities = [0.4, 0.3, 0.35]

        modelClone.traverse((child) => {
          if (child instanceof THREE.Mesh) {
            ;(child as THREE.Mesh).material = new THREE.MeshPhongMaterial({
              color: colors[i],
              transparent: true,
              opacity: opacities[i],
              emissive: colors[i],
              emissiveIntensity: 0.2
            })
          }
        })

        scene.add(modelClone)
        console.log(`模型 ${i + 1} 添加到场景`)

        // 存储GLB模型到数组中
        models.push({
          mesh: modelClone,
          originalPosition: { x: pos.x, y: pos.y, z: pos.z },
          rotationSpeed: {
            x: (Math.random() - 0.5) * 0.015,
            y: (Math.random() - 0.5) * 0.015,
            z: (Math.random() - 0.5) * 0.015
          },
          floatSpeed: Math.random() * 0.003 + 0.0015,
          floatAmplitude: Math.random() * 3.0 + 1.0
        })

        // 保存第一个模型用于动画
        if (i === 0) {
          model = modelClone
        }
      }
    },
    (progress) => {
      console.log('加载进度:', (progress.loaded / progress.total * 100) + '%')
    },
    (error) => {
      console.error('Error loading background model:', error)
      // 如果加载失败，创建几何体作为替代
      createFallbackGeometry()
    }
  )
}

// 创建备用几何体
const createFallbackGeometry = () => {
  console.log('创建备用几何体...')

  // 创建多个几何体填充背景
  const geometries = [
    new THREE.BoxGeometry(4, 4, 4),
    new THREE.SphereGeometry(3, 32, 32),
    new THREE.ConeGeometry(2.5, 5, 8),
    new THREE.TorusGeometry(2.5, 0.8, 16, 100),
    new THREE.OctahedronGeometry(3),
    new THREE.DodecahedronGeometry(2.5)
  ]

  const colors = [0xff8800, 0x00ddff, 0xff4488, 0x88ff00, 0x8844ff, 0xff8844]

  for (let i = 0; i < 6; i++) {
    const material = new THREE.MeshPhongMaterial({
      color: colors[i],
      transparent: true,
      opacity: 0.4,
      emissive: colors[i],
      emissiveIntensity: 0.2,
      shininess: 100
    })

    const mesh = new THREE.Mesh(geometries[i], material)

    // 设置位置 - 分散到屏幕各个角落
    const positions = [
      { x: -24, y: 14, z: -12 },  // 左上更远
      { x: 26, y: 16, z: -14 },   // 右上最远
      { x: -18, y: -6, z: -10 },  // 左下
      { x: 28, y: -4, z: -13 },   // 右下最右
      { x: 0, y: 18, z: -22 },    // 中上远
      { x: 16, y: 4, z: -24 }     // 右中远
    ]

    mesh.position.set(positions[i].x, positions[i].y, positions[i].z)

    // 添加随机旋转
    mesh.rotation.x = Math.random() * Math.PI
    mesh.rotation.y = Math.random() * Math.PI
    mesh.rotation.z = Math.random() * Math.PI

    scene.add(mesh)
    console.log(`几何体 ${i + 1} 添加到场景`)

    // 存储所有模型到数组中
    models.push({
      mesh: mesh,
      originalPosition: { ...positions[i] },
      rotationSpeed: {
        x: (Math.random() - 0.5) * 0.02,
        y: (Math.random() - 0.5) * 0.02,
        z: (Math.random() - 0.5) * 0.02
      },
      floatSpeed: Math.random() * 0.004 + 0.0015,
      floatAmplitude: Math.random() * 3.5 + 1.0
    })
  }
}

// 3D模型动画
const animate3D = () => {
  animationId = requestAnimationFrame(animate3D)

  const time = Date.now() * 0.001

  // 为每个模型添加不规则运动
  models.forEach((modelData, index) => {
    const { mesh, originalPosition, rotationSpeed, floatSpeed, floatAmplitude } = modelData

    // 不规则旋转
    mesh.rotation.x += rotationSpeed.x
    mesh.rotation.y += rotationSpeed.y
    mesh.rotation.z += rotationSpeed.z

    // 不规则浮动
    const floatOffset = Math.sin(time * floatSpeed + index) * floatAmplitude
    mesh.position.y = originalPosition.y + floatOffset

    // 轻微的左右摆动
    const swayOffset = Math.cos(time * floatSpeed * 0.7 + index * 2) * 0.8
    mesh.position.x = originalPosition.x + swayOffset
  })

  renderer.render(scene, camera)
}

// 窗口大小调整
const handleResize = () => {
  if (gridCamera && gridRenderer) {
    gridCamera.aspect = window.innerWidth / window.innerHeight
    gridCamera.updateProjectionMatrix()
    gridRenderer.setSize(window.innerWidth, window.innerHeight)
  }

  if (camera && renderer) {
    camera.aspect = window.innerWidth / window.innerHeight
    camera.updateProjectionMatrix()
    renderer.setSize(window.innerWidth, window.innerHeight)
  }
}

// 更新主题
const updateTheme = () => {
  // 1) CSS变量（DOM层样式）
  if (isDarkMode.value) {
    document.documentElement.style.setProperty('--bg-color', '#0a0a0a')
    document.documentElement.style.setProperty('--text-color', '#ffffff')
    document.documentElement.style.setProperty('--text-secondary', 'rgba(255,255,255,0.65)')
    document.documentElement.style.setProperty('--grid-color', '#00ffff')
    document.documentElement.style.setProperty('--accent-color', '#00ffff')
    document.documentElement.style.setProperty('--card-bg', 'rgba(0,255,255,0.15)')
    document.documentElement.style.setProperty('--active-card-bg', 'rgba(0,255,255,0.25)')
    document.documentElement.style.setProperty('--card-border', 'rgba(0,255,255,0.4)')
  } else {
    document.documentElement.style.setProperty('--bg-color', '#f5f5f5')
    document.documentElement.style.setProperty('--text-color', '#1f2937')
    document.documentElement.style.setProperty('--text-secondary', 'rgba(0,0,0,0.55)')
    document.documentElement.style.setProperty('--grid-color', '#0066cc')
    document.documentElement.style.setProperty('--accent-color', '#0066cc')
    document.documentElement.style.setProperty('--card-bg', 'rgba(0,102,204,0.10)')
    document.documentElement.style.setProperty('--active-card-bg', 'rgba(0,102,204,0.20)')
    document.documentElement.style.setProperty('--card-border', 'rgba(0,102,204,0.35)')
  }

  // 2) Three.js 背景与网格颜色同步
  if (gridRenderer) {
    gridRenderer.setClearColor(isDarkMode.value ? 0x0a0a0a : 0xf5f5f5, 1)
  }
  if (gridMesh && gridMaterial) {
    gridMaterial.color.set(isDarkMode.value ? 0x00ffff : 0x0066cc)
    gridMaterial.opacity = isDarkMode.value ? 0.12 : 0.15
    gridMaterial.needsUpdate = true
  }
  // 3) 根节点主题标记（便于外层样式做差异化）
  document.documentElement.setAttribute('data-theme', isDarkMode.value ? 'dark' : 'light')
}

// 监听主题变化
watch(isDarkMode, () => {
  updateTheme()
}, { immediate: true })

// 生命周期
onMounted(() => {
  initGridBackground()
  init3DBackground()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (animationId) {
    cancelAnimationFrame(animationId)
  }
  window.removeEventListener('resize', handleResize)
})
</script>

<style lang="scss" scoped>
.home-page {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: var(--bg-color, #000);
  color: var(--text-color, white);
  transition: all 0.3s ease;
}

.grid-background {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1;

  canvas {
    width: 100% !important;
    height: 100% !important;
  }
}

.three-background {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 2;

  canvas {
    width: 100% !important;
    height: 100% !important;
  }
}

.content-overlay {
  position: relative;
  z-index: 10;
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  padding: 10px 80px 40px 80px; /* 顶部进一步收紧 */
  color: var(--text-color);
  overflow: hidden;
}

.main-title-section {
  /* 取消占满剩余空间，避免把统计组件顶到最底部 */
  flex: 0;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  max-width: 700px;
  margin-top: 10px;
}



.main-title {
  font-size: 6rem;
  font-weight: 900;
  line-height: 0.9;
  margin-bottom: 20px; /* 收紧与下方的间距 */
  text-transform: uppercase;

  .title-line {
    display: block;
    background: linear-gradient(45deg, var(--text-color), var(--accent-color));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    text-shadow: 0 0 30px rgba(0, 255, 255, 0.3);
  }
}

.feature-list {
  margin-bottom: 20px; /* 收紧与按钮的间距 */

  .feature-item {
    display: flex;
    align-items: center;
    gap: 15px;
    margin-bottom: 18px;
    font-size: 20px;
    color: var(--text-secondary);

    .feature-arrow {
      color: var(--accent-color);
      font-weight: bold;
      font-size: 24px;
    }
  }
}

.action-buttons {
  .start-btn {
    background: transparent;
    border: 3px solid var(--text-color);
    color: var(--text-color);
    padding: 20px 40px;
    font-size: 18px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 2px;
    transition: all 0.3s ease;

    &:hover {
      background: var(--text-color);
      color: var(--bg-color);
      box-shadow: 0 0 25px rgba(0, 0, 0, 0.15);
      transform: translateY(-2px);
    }
  }
}

.agent-status-section {
  position: absolute;
  top: 60px;
  right: 80px;

  .agent-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 18px;

    .agent-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 10px;
      padding: 20px 15px;
      background: var(--card-bg);
      border: 2px solid var(--card-border);
      border-radius: 12px;
      transition: all 0.3s ease;
      min-width: 120px;

      &.active {
        background: var(--active-card-bg);
        border-color: var(--accent-color);
        box-shadow: 0 0 20px color-mix(in srgb, var(--accent-color), transparent 60%);
      }

      .agent-icon {
        font-size: 28px;
      }

      .agent-name {
        font-size: 14px;
        text-align: center;
        color: var(--text-color);
        line-height: 1.2;
        font-weight: 500;
      }

      .agent-role {
        font-size: 11px;
        color: var(--accent-color);
        text-align: center;
        font-weight: 600;
      }

      .agent-indicator {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #666;

        &.online {
          background: var(--accent-color);
          box-shadow: 0 0 12px var(--accent-color);
        }
      }
    }
  }
}

.stats-section {
  display: flex;
  justify-content: flex-start;
  gap: 100px;

  .stat-item {
    text-align: left;

    .stat-value {
      font-size: 3.5rem;
      font-weight: 900;
      color: var(--text-color);
      line-height: 1;
      margin-bottom: 10px;
    }

    .stat-label {
      font-size: 16px;
      color: var(--text-secondary);
      text-transform: none;
      letter-spacing: 1px;
      font-weight: 500;
    }
  }
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

// 响应式设计
@media (max-width: 1400px) {
  .content-overlay {
    padding: 25px 40px;
  }

  .main-title {
    font-size: 3.8rem;
    margin-bottom: 30px;
  }

  .feature-list {
    margin-bottom: 30px;
  }

  .stats-section {
    gap: 50px;

    .stat-item .stat-value {
      font-size: 2.2rem;
    }
  }
}

@media (max-width: 1200px) {
  .content-overlay {
    padding: 20px 35px;
  }

  .main-title {
    font-size: 3.2rem;
    margin-bottom: 25px;
  }

  .stats-section {
    gap: 40px;

    .stat-item .stat-value {
      font-size: 2rem;
    }
  }

  .agent-status-section {
    top: 25px;
    right: 35px;

    .agent-grid {
      gap: 10px;

      .agent-item {
        padding: 10px 6px;
        min-width: 70px;
      }
    }
  }
}

@media (max-width: 768px) {
  .content-overlay {
    padding: 15px 25px;
    height: 100vh;
  }

  .main-title {
    font-size: 2.5rem;
    margin-bottom: 20px;
  }

  .feature-list {
    margin-bottom: 20px;

    .feature-item {
      font-size: 14px;
      margin-bottom: 8px;
    }
  }

  .agent-status-section {
    position: static;
    margin: 20px 0;

    .agent-grid {
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;

      .agent-item {
        padding: 8px 4px;
        min-width: 60px;

        .agent-icon {
          font-size: 16px;
        }

        .agent-name {
          font-size: 10px;
        }

        .agent-role {
          font-size: 8px;
        }
      }
    }
  }

  .stats-section {
    flex-wrap: wrap;
    gap: 20px;
    padding-bottom: 10px;

    .stat-item {
      .stat-value {
        font-size: 1.8rem;
      }

      .stat-label {
        font-size: 10px;
      }
    }
  }
}
</style>
