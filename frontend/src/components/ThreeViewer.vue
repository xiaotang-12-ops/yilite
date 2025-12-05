<template>
  <div class="three-viewer" ref="containerRef">
    <!-- 3D渲染容器 -->
    <div ref="rendererRef" class="renderer-container"></div>
    
    <!-- 控制面板 -->
    <div class="control-panel" :class="{ collapsed: panelCollapsed }">
      <div class="panel-header">
        <h3>3D控制台</h3>
        <el-button 
          :icon="panelCollapsed ? 'Expand' : 'Fold'" 
          text 
          @click="panelCollapsed = !panelCollapsed"
        />
      </div>
      
      <div class="panel-content" v-show="!panelCollapsed">
        <!-- 视图控制 -->
        <div class="control-group">
          <label>视图模式</label>
          <el-radio-group v-model="viewMode" @change="changeViewMode">
            <el-radio-button value="normal">正常</el-radio-button>
            <el-radio-button value="exploded">爆炸</el-radio-button>
            <el-radio-button value="wireframe">线框</el-radio-button>
          </el-radio-group>
        </div>
        
        <!-- 爆炸程度控制 -->
        <div class="control-group" v-show="viewMode === 'exploded'">
          <label>爆炸程度</label>
          <el-slider 
            v-model="explodeLevel" 
            :min="0" 
            :max="100" 
            @input="updateExplode"
            show-input
          />
        </div>
        
        <!-- 动画控制 -->
        <div class="control-group">
          <label>动画</label>
          <div class="animation-controls">
            <el-button 
              :type="isAnimating ? 'danger' : 'primary'" 
              @click="toggleAnimation"
              :icon="isAnimating ? 'VideoPause' : 'VideoPlay'"
            >
              {{ isAnimating ? '暂停' : '播放' }}
            </el-button>
            <el-button @click="resetView" icon="Refresh">重置</el-button>
          </div>
        </div>
        
        <!-- 零件列表 -->
        <div class="control-group">
          <label>零件列表</label>
          <div class="parts-list">
            <div 
              v-for="part in parts" 
              :key="part.id"
              class="part-item"
              :class="{ active: selectedPart === part.id }"
              @click="selectPart(part.id)"
            >
              <div class="part-color" :style="{ background: part.color }"></div>
              <span class="part-name">{{ part.name }}</span>
              <el-switch 
                v-model="part.visible" 
                @change="togglePartVisibility(part.id)"
                size="small"
              />
            </div>
          </div>
        </div>
        
        <!-- 环境设置 -->
        <div class="control-group">
          <label>环境设置</label>
          <div class="env-controls">
            <div class="env-item">
              <span>背景</span>
              <el-color-picker v-model="backgroundColor" @change="updateBackground" />
            </div>
            <div class="env-item">
              <span>光照强度</span>
              <el-slider 
                v-model="lightIntensity" 
                :min="0" 
                :max="2" 
                :step="0.1"
                @input="updateLighting"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 性能监控 -->
    <div class="performance-monitor" v-show="showPerformance">
      <div class="fps-counter">FPS: {{ fps }}</div>
      <div class="poly-counter">多边形: {{ polyCount }}</div>
    </div>
    
    <!-- 加载状态 -->
    <div class="loading-overlay" v-show="loading">
      <div class="loading-content">
        <el-icon class="loading-icon"><Loading /></el-icon>
        <p>正在加载3D模型...</p>
        <el-progress :percentage="loadingProgress" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { gsap } from 'gsap'
import { useMediaQuery } from '@vueuse/core'

interface Part {
  id: string
  name: string
  color: string
  visible: boolean
  mesh?: THREE.Mesh
  originalPosition?: THREE.Vector3
}

interface Props {
  modelUrl?: string
  autoRotate?: boolean
  showGrid?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  autoRotate: true,
  showGrid: true
})

// 响应式数据
const containerRef = ref<HTMLElement>()
const rendererRef = ref<HTMLElement>()
const panelCollapsed = ref(false)
const viewMode = ref('normal')
const explodeLevel = ref(0)
const isAnimating = ref(false)
const selectedPart = ref<string>('')
const backgroundColor = ref('#1a1a2e')
const lightIntensity = ref(1)
const showPerformance = ref(false)
const fps = ref(0)
const polyCount = ref(0)
const loading = ref(false)
const loadingProgress = ref(0)
const isMobile = useMediaQuery('(max-width: 1024px)')

const parts = ref<Part[]>([
  { id: 'part1', name: '主体框架', color: '#409eff', visible: true },
  { id: 'part2', name: '连接件', color: '#67c23a', visible: true },
  { id: 'part3', name: '紧固件', color: '#e6a23c', visible: true }
])

// Three.js 核心对象
let scene: THREE.Scene
let camera: THREE.PerspectiveCamera
let renderer: THREE.WebGLRenderer
let controls: OrbitControls
let animationId: number
let loadedModel: THREE.Group

// 初始化3D场景
const initThreeJS = () => {
  if (!rendererRef.value) return
  
  // 场景
  scene = new THREE.Scene()
  scene.background = new THREE.Color(backgroundColor.value)
  
  // 相机
  camera = new THREE.PerspectiveCamera(
    75,
    rendererRef.value.clientWidth / rendererRef.value.clientHeight,
    0.1,
    1000
  )
  camera.position.set(5, 5, 5)
  
  // 渲染器
  renderer = new THREE.WebGLRenderer({ 
    antialias: !isMobile.value,
    alpha: true,
    powerPreference: 'high-performance'
  })
  renderer.setSize(rendererRef.value.clientWidth, rendererRef.value.clientHeight)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, isMobile.value ? 1.5 : 2))
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1
  
  rendererRef.value.appendChild(renderer.domElement)
  
  // 控制器
  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.05
  controls.autoRotate = props.autoRotate && !isMobile.value
  controls.autoRotateSpeed = 2
  
  // 光照
  setupLighting()
  
  // 网格
  if (props.showGrid) {
    const gridHelper = new THREE.GridHelper(10, 10, 0x444444, 0x222222)
    scene.add(gridHelper)
  }
  
  // 开始渲染循环
  animate()
}

// 设置光照
const setupLighting = () => {
  // 环境光
  const ambientLight = new THREE.AmbientLight(0x404040, 0.6)
  scene.add(ambientLight)
  
  // 主光源
  const directionalLight = new THREE.DirectionalLight(0xffffff, lightIntensity.value)
  directionalLight.position.set(10, 10, 5)
  directionalLight.castShadow = true
  directionalLight.shadow.mapSize.width = 2048
  directionalLight.shadow.mapSize.height = 2048
  scene.add(directionalLight)
  
  // 补光
  const fillLight = new THREE.DirectionalLight(0x4080ff, 0.3)
  fillLight.position.set(-5, 5, -5)
  scene.add(fillLight)
}

// 渲染循环
const animate = () => {
  animationId = requestAnimationFrame(animate)
  
  controls.update()
  renderer.render(scene, camera)
  
  // 性能监控
  updatePerformanceStats()
}

// 加载3D模型
const loadModel = async (url: string) => {
  loading.value = true
  loadingProgress.value = 0
  
  const loader = new GLTFLoader()
  
  try {
    const gltf = await new Promise<any>((resolve, reject) => {
      loader.load(
        url,
        resolve,
        (progress) => {
          loadingProgress.value = Math.round((progress.loaded / progress.total) * 100)
        },
        reject
      )
    })
    
    loadedModel = gltf.scene
    scene.add(loadedModel)
    
    // 自动调整相机位置
    const box = new THREE.Box3().setFromObject(loadedModel)
    const center = box.getCenter(new THREE.Vector3())
    const size = box.getSize(new THREE.Vector3())
    
    const maxDim = Math.max(size.x, size.y, size.z)
    const fov = camera.fov * (Math.PI / 180)
    let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2))
    
    camera.position.set(center.x, center.y, center.z + cameraZ * 1.5)
    controls.target.copy(center)
    
    loading.value = false
    
  } catch (error) {
    console.error('模型加载失败:', error)
    loading.value = false
    ElMessage.error('模型加载失败')
  }
}

// 控制方法
const changeViewMode = (mode: string) => {
  // 实现视图模式切换逻辑
}

const updateExplode = (level: number) => {
  // 实现爆炸视图逻辑
}

const toggleAnimation = () => {
  isAnimating.value = !isAnimating.value
  controls.autoRotate = isAnimating.value
}

const resetView = () => {
  // 重置相机位置和模型状态
}

const selectPart = (partId: string) => {
  selectedPart.value = partId
  // 高亮选中的零件
}

const togglePartVisibility = (partId: string) => {
  // 切换零件可见性
}

const updateBackground = (color: string) => {
  scene.background = new THREE.Color(color)
}

const updateLighting = (intensity: number) => {
  // 更新光照强度
}

const updatePerformanceStats = () => {
  // 更新性能统计
}

// 响应式处理
const handleResize = () => {
  if (!rendererRef.value) return
  
  const width = rendererRef.value.clientWidth
  const height = rendererRef.value.clientHeight
  
  camera.aspect = width / height
  camera.updateProjectionMatrix()
  renderer.setSize(width, height)
}

// 生命周期
onMounted(() => {
  initThreeJS()
  window.addEventListener('resize', handleResize)
  
  if (props.modelUrl) {
    loadModel(props.modelUrl)
  }

  if (isMobile.value) {
    panelCollapsed.value = true
  }
})

onUnmounted(() => {
  if (animationId) {
    cancelAnimationFrame(animationId)
  }
  window.removeEventListener('resize', handleResize)
  
  if (renderer) {
    renderer.dispose()
  }
})

// 监听模型URL变化
watch(() => props.modelUrl, (newUrl) => {
  if (newUrl) {
    loadModel(newUrl)
  }
})

watch(isMobile, (val) => {
  panelCollapsed.value = val ? true : panelCollapsed.value
  if (controls) {
    controls.autoRotate = props.autoRotate && !val
  }
  if (renderer) {
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, val ? 1.5 : 2))
  }
})
</script>

<style lang="scss" scoped>
.three-viewer {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  border-radius: 12px;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
}

.renderer-container {
  width: 100%;
  height: 100%;
}

.control-panel {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 300px;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.3s ease;
  
  &.collapsed {
    width: 120px;
    
    .panel-content {
      display: none;
    }
  }
  
  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    
    h3 {
      margin: 0;
      color: white;
      font-size: 16px;
    }
  }
  
  .panel-content {
    padding: 16px;
    max-height: 500px;
    overflow-y: auto;
  }
  
  .control-group {
    margin-bottom: 20px;
    
    label {
      display: block;
      color: #ccc;
      font-size: 14px;
      margin-bottom: 8px;
    }
  }
  
  .parts-list {
    .part-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px;
      border-radius: 6px;
      cursor: pointer;
      transition: background 0.2s;
      
      &:hover {
        background: rgba(255, 255, 255, 0.1);
      }
      
      &.active {
        background: rgba(64, 158, 255, 0.3);
      }
      
      .part-color {
        width: 12px;
        height: 12px;
        border-radius: 50%;
      }
      
      .part-name {
        flex: 1;
        color: white;
        font-size: 12px;
      }
    }
  }
  
  .env-controls {
    .env-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
      
      span {
        color: #ccc;
        font-size: 12px;
      }
    }
  }
}

.performance-monitor {
  position: absolute;
  top: 20px;
  left: 20px;
  background: rgba(0, 0, 0, 0.7);
  padding: 8px 12px;
  border-radius: 6px;
  color: #00ff00;
  font-family: monospace;
  font-size: 12px;
  
  div {
    margin-bottom: 4px;
    
    &:last-child {
      margin-bottom: 0;
    }
  }
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  
  .loading-content {
    text-align: center;
    color: white;
    
    .loading-icon {
      font-size: 48px;
      margin-bottom: 16px;
      animation: spin 1s linear infinite;
    }
    
    p {
      margin: 16px 0;
      font-size: 16px;
    }
  }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@media (max-width: 1024px) {
  .renderer-container {
    min-height: 55vh;
  }

  .control-panel {
    width: 90%;
    left: 50%;
    transform: translateX(-50%);
    top: auto;
    bottom: 16px;

    &.collapsed {
      width: 72px;
      .panel-header {
        justify-content: center;
      }
    }
  }

  .panel-content {
    max-height: 320px;
  }
}
</style>
