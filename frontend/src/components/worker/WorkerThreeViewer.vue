<template>
  <div class="worker-three-viewer">
    <div class="viewer-header">
      <h4>3D模型查看器</h4>
      <div class="viewer-controls">
        <el-button-group size="small">
          <el-button @click="resetView">重置视角</el-button>
          <el-button @click="toggleWireframe">{{ wireframe ? '实体' : '线框' }}</el-button>
          <el-button @click="toggleFullscreen">{{ fullscreen ? '退出全屏' : '全屏' }}</el-button>
        </el-button-group>
      </div>
    </div>

    <div 
      ref="viewerContainer" 
      class="viewer-container"
      :class="{ fullscreen: fullscreen }"
    >
      <div ref="threeContainer" class="three-container"></div>
      
      <!-- 加载状态 -->
      <div v-if="loading" class="loading-overlay">
        <el-icon class="loading-icon"><loading /></el-icon>
        <p>正在加载3D模型...</p>
      </div>
      
      <!-- 错误状态 -->
      <div v-if="error" class="error-overlay">
        <el-icon class="error-icon"><warning /></el-icon>
        <p>{{ error }}</p>
        <el-button @click="retryLoad">重新加载</el-button>
      </div>
      
      <!-- 控制面板 -->
      <div class="control-panel">
        <div class="panel-section">
          <h5>视图控制</h5>
          <div class="control-buttons">
            <el-button size="small" @click="setView('front')">前视图</el-button>
            <el-button size="small" @click="setView('back')">后视图</el-button>
            <el-button size="small" @click="setView('left')">左视图</el-button>
            <el-button size="small" @click="setView('right')">右视图</el-button>
            <el-button size="small" @click="setView('top')">俯视图</el-button>
            <el-button size="small" @click="setView('bottom')">仰视图</el-button>
          </div>
        </div>
        
        <div class="panel-section">
          <h5>显示选项</h5>
          <div class="display-options">
            <el-checkbox v-model="showAxes" @change="toggleAxes">显示坐标轴</el-checkbox>
            <el-checkbox v-model="showGrid" @change="toggleGrid">显示网格</el-checkbox>
            <el-checkbox v-model="showBoundingBox" @change="toggleBoundingBox">显示边界框</el-checkbox>
          </div>
        </div>
        
        <div class="panel-section">
          <h5>零件高亮</h5>
          <div class="part-list">
            <div 
              v-for="part in parts" 
              :key="part.id"
              class="part-item"
              :class="{ highlighted: part.highlighted }"
              @click="togglePartHighlight(part)"
            >
              <div class="part-color" :style="{ backgroundColor: part.color }"></div>
              <span class="part-name">{{ part.name }}</span>
              <el-icon v-if="part.highlighted" class="highlight-icon"><check /></el-icon>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 操作说明 -->
    <div class="operation-tips">
      <h5>操作说明</h5>
      <div class="tips-grid">
        <div class="tip-item">
          <el-icon><operation /></el-icon>
          <span>左键拖拽：旋转视角</span>
        </div>
        <div class="tip-item">
          <el-icon><operation /></el-icon>
          <span>右键拖拽：平移视图</span>
        </div>
        <div class="tip-item">
          <el-icon><operation /></el-icon>
          <span>滚轮：缩放模型</span>
        </div>
        <div class="tip-item">
          <el-icon><position /></el-icon>
          <span>双击：聚焦零件</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, defineProps, defineEmits, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading, Warning, Check, Operation, Position } from '@element-plus/icons-vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls'
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader'
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader'

// Props
const props = defineProps({
  modelUrl: {
    type: String,
    required: true
  },
  parts: {
    type: Array,
    default: () => []
  }
})

// 事件定义
const emit = defineEmits(['part-selected', 'view-changed'])

// 响应式数据
const viewerContainer = ref(null)
const threeContainer = ref(null)
const loading = ref(true)
const error = ref('')
const fullscreen = ref(false)
const wireframe = ref(false)
const showAxes = ref(true)
const showGrid = ref(true)
const showBoundingBox = ref(false)

// Three.js 相关变量
let scene, camera, renderer, controls
let model, axesHelper, gridHelper, boundingBoxHelper
const parts = ref([
  { id: 1, name: '底座', color: '#ff6b6b', highlighted: false },
  { id: 2, name: '支架', color: '#4ecdc4', highlighted: false },
  { id: 3, name: '连接件', color: '#45b7d1', highlighted: false },
  { id: 4, name: '固定螺栓', color: '#96ceb4', highlighted: false }
])

// 生命周期
onMounted(async () => {
  await nextTick()
  initThreeJS()
  loadModel()
  
  // 监听窗口大小变化
  window.addEventListener('resize', onWindowResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', onWindowResize)
  
  // 清理Three.js资源
  if (renderer) {
    renderer.dispose()
  }
  if (controls) {
    controls.dispose()
  }
})

// 方法
const initThreeJS = () => {
  if (!threeContainer.value) return
  
  // 创建场景
  scene = new THREE.Scene()
  scene.background = new THREE.Color(0xf5f5f5)
  
  // 创建相机
  const container = threeContainer.value
  const width = container.clientWidth
  const height = container.clientHeight
  
  camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000)
  camera.position.set(5, 5, 5)
  
  // 创建渲染器
  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setSize(width, height)
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  
  container.appendChild(renderer.domElement)
  
  // 创建控制器
  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.05
  
  // 添加光源
  const ambientLight = new THREE.AmbientLight(0x404040, 0.6)
  scene.add(ambientLight)
  
  const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8)
  directionalLight.position.set(10, 10, 5)
  directionalLight.castShadow = true
  scene.add(directionalLight)
  
  // 添加辅助元素
  addHelpers()
  
  // 开始渲染循环
  animate()
}

const addHelpers = () => {
  // 坐标轴
  axesHelper = new THREE.AxesHelper(5)
  scene.add(axesHelper)
  
  // 网格
  gridHelper = new THREE.GridHelper(10, 10)
  scene.add(gridHelper)
}

const loadModel = async () => {
  try {
    loading.value = true
    error.value = ''
    
    const loader = getLoaderByExtension(props.modelUrl)
    const extension = props.modelUrl.split('.').pop()?.toLowerCase()

    let loadedObject: any

    if (extension === 'glb' || extension === 'gltf') {
      // GLB/GLTF文件加载
      const gltf = await new Promise<any>((resolve, reject) => {
        (loader as GLTFLoader).load(
          props.modelUrl,
          resolve,
          (progress) => {
            console.log('Loading progress:', progress)
          },
          reject
        )
      })
      loadedObject = gltf.scene
    } else {
      // STL/OBJ文件加载
      const geometry = await new Promise<THREE.BufferGeometry>((resolve, reject) => {
        loader.load(
          props.modelUrl,
          resolve,
          (progress) => {
            console.log('Loading progress:', progress)
          },
          reject
        )
      })

      // 创建材质
      const material = new THREE.MeshLambertMaterial({
        color: 0x606060,
        wireframe: wireframe.value
      })

      // 创建模型
      loadedObject = new THREE.Mesh(geometry, material)
      loadedObject.castShadow = true
      loadedObject.receiveShadow = true
    }

    model = loadedObject
    
    // 居中模型
    const box = new THREE.Box3().setFromObject(model)
    const center = box.getCenter(new THREE.Vector3())
    model.position.sub(center)
    
    scene.add(model)
    
    // 调整相机位置
    const size = box.getSize(new THREE.Vector3())
    const maxDim = Math.max(size.x, size.y, size.z)
    camera.position.set(maxDim, maxDim, maxDim)
    controls.target.copy(center)
    controls.update()
    
    loading.value = false
    
  } catch (err) {
    console.error('Model loading error:', err)
    error.value = '模型加载失败，请检查文件格式或网络连接'
    loading.value = false
  }
}

const getLoaderByExtension = (url: string) => {
  const extension = url.split('.').pop()?.toLowerCase()

  switch (extension) {
    case 'stl':
      return new STLLoader()
    case 'obj':
      return new OBJLoader()
    case 'glb':
    case 'gltf':
      return new GLTFLoader()
    default:
      throw new Error(`不支持的文件格式: ${extension}`)
  }
}

const animate = () => {
  requestAnimationFrame(animate)
  
  if (controls) {
    controls.update()
  }
  
  if (renderer && scene && camera) {
    renderer.render(scene, camera)
  }
}

const onWindowResize = () => {
  if (!threeContainer.value || !camera || !renderer) return
  
  const container = threeContainer.value
  const width = container.clientWidth
  const height = container.clientHeight
  
  camera.aspect = width / height
  camera.updateProjectionMatrix()
  
  renderer.setSize(width, height)
}

const resetView = () => {
  if (!model || !camera || !controls) return
  
  const box = new THREE.Box3().setFromObject(model)
  const size = box.getSize(new THREE.Vector3())
  const center = box.getCenter(new THREE.Vector3())
  const maxDim = Math.max(size.x, size.y, size.z)
  
  camera.position.set(maxDim, maxDim, maxDim)
  controls.target.copy(center)
  controls.update()
  
  emit('view-changed', 'reset')
}

const setView = (viewType) => {
  if (!model || !camera || !controls) return
  
  const box = new THREE.Box3().setFromObject(model)
  const center = box.getCenter(new THREE.Vector3())
  const size = box.getSize(new THREE.Vector3())
  const distance = Math.max(size.x, size.y, size.z) * 2
  
  switch (viewType) {
    case 'front':
      camera.position.set(center.x, center.y, center.z + distance)
      break
    case 'back':
      camera.position.set(center.x, center.y, center.z - distance)
      break
    case 'left':
      camera.position.set(center.x - distance, center.y, center.z)
      break
    case 'right':
      camera.position.set(center.x + distance, center.y, center.z)
      break
    case 'top':
      camera.position.set(center.x, center.y + distance, center.z)
      break
    case 'bottom':
      camera.position.set(center.x, center.y - distance, center.z)
      break
  }
  
  controls.target.copy(center)
  controls.update()
  
  emit('view-changed', viewType)
}

const toggleWireframe = () => {
  wireframe.value = !wireframe.value
  
  if (model && model.material) {
    model.material.wireframe = wireframe.value
  }
}

const toggleFullscreen = () => {
  fullscreen.value = !fullscreen.value
  
  nextTick(() => {
    onWindowResize()
  })
}

const toggleAxes = () => {
  if (axesHelper) {
    axesHelper.visible = showAxes.value
  }
}

const toggleGrid = () => {
  if (gridHelper) {
    gridHelper.visible = showGrid.value
  }
}

const toggleBoundingBox = () => {
  if (!model) return
  
  if (showBoundingBox.value) {
    const box = new THREE.Box3().setFromObject(model)
    boundingBoxHelper = new THREE.Box3Helper(box, 0xff0000)
    scene.add(boundingBoxHelper)
  } else {
    if (boundingBoxHelper) {
      scene.remove(boundingBoxHelper)
      boundingBoxHelper = null
    }
  }
}

const togglePartHighlight = (part) => {
  part.highlighted = !part.highlighted
  emit('part-selected', part)
  
  // 这里可以添加实际的零件高亮逻辑
  ElMessage.info(`${part.highlighted ? '高亮' : '取消高亮'}: ${part.name}`)
}

const retryLoad = () => {
  loadModel()
}
</script>

<style scoped>
.worker-three-viewer {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.viewer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  border-bottom: 1px solid #e4e7ed;
  background: #f5f7fa;
}

.viewer-header h4 {
  margin: 0;
  color: #606266;
}

.viewer-container {
  flex: 1;
  position: relative;
  display: flex;
}

.viewer-container.fullscreen {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 9999;
  background: #fff;
}

.three-container {
  flex: 1;
  position: relative;
}

.loading-overlay, .error-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  background: rgba(255, 255, 255, 0.9);
  z-index: 10;
}

.loading-icon {
  font-size: 48px;
  color: #409eff;
  animation: spin 1s linear infinite;
  margin-bottom: 15px;
}

.error-icon {
  font-size: 48px;
  color: #f56c6c;
  margin-bottom: 15px;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.control-panel {
  width: 250px;
  padding: 15px;
  background: #f9f9f9;
  border-left: 1px solid #e4e7ed;
  overflow-y: auto;
}

.panel-section {
  margin-bottom: 20px;
}

.panel-section h5 {
  margin: 0 0 10px 0;
  color: #606266;
  font-size: 14px;
  font-weight: 600;
}

.control-buttons {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 5px;
}

.display-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.part-list {
  max-height: 200px;
  overflow-y: auto;
}

.part-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.part-item:hover {
  background: #e6f7ff;
}

.part-item.highlighted {
  background: #f6ffed;
  border: 1px solid #b7eb8f;
}

.part-color {
  width: 16px;
  height: 16px;
  border-radius: 2px;
  border: 1px solid #d9d9d9;
}

.part-name {
  flex: 1;
  font-size: 14px;
  color: #606266;
}

.highlight-icon {
  color: #52c41a;
}

.operation-tips {
  padding: 15px;
  border-top: 1px solid #e4e7ed;
  background: #f5f7fa;
}

.operation-tips h5 {
  margin: 0 0 10px 0;
  color: #606266;
  font-size: 14px;
  font-weight: 600;
}

.tips-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.tip-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #909399;
}

.tip-item .el-icon {
  color: #c0c4cc;
}
</style>
