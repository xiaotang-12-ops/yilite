<template>
  <div class="simple-glb-test">
    <div class="container">
      <h1>简单GLB测试</h1>
      
      <!-- 文件选择 -->
      <div class="controls">
        <el-select v-model="selectedFile" placeholder="选择GLB文件" @change="loadModel">
          <el-option label="产品测试.glb" value="http://localhost:8000/output/processor_test/product_test.glb" />
          <el-option label="组件图1.glb" value="http://localhost:8000/output/processor_test/component1.glb" />
          <el-option label="trimesh产品测试.glb" value="http://localhost:8000/output/trimesh_test/product_test.glb" />
          <el-option label="trimesh组件图1.glb" value="http://localhost:8000/output/trimesh_test/component1.glb" />
        </el-select>
        
        <el-button @click="resetView">重置视角</el-button>
        <el-button @click="toggleWireframe">{{ wireframe ? '实体' : '线框' }}</el-button>
      </div>
      
      <!-- 3D容器 -->
      <div ref="threeContainer" class="three-container"></div>
      
      <!-- 状态信息 -->
      <div class="status">
        <p>状态: {{ status }}</p>
        <p v-if="selectedFile">文件: {{ selectedFile }}</p>
        <p v-if="modelInfo">模型信息: {{ modelInfo }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader'

// 响应式数据
const threeContainer = ref<HTMLElement>()
const selectedFile = ref('')
const status = ref('就绪')
const modelInfo = ref('')
const wireframe = ref(false)

// Three.js 变量
let scene: THREE.Scene
let camera: THREE.PerspectiveCamera
let renderer: THREE.WebGLRenderer
let controls: OrbitControls
let currentModel: THREE.Object3D | null = null
let animationId: number

// 初始化Three.js
const initThree = () => {
  if (!threeContainer.value) return
  
  // 场景
  scene = new THREE.Scene()
  scene.background = new THREE.Color(0xf0f0f0)
  
  // 相机
  const container = threeContainer.value
  camera = new THREE.PerspectiveCamera(
    75,
    container.clientWidth / container.clientHeight,
    0.1,
    1000
  )
  camera.position.set(5, 5, 5)
  
  // 渲染器
  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setSize(container.clientWidth, container.clientHeight)
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  
  container.appendChild(renderer.domElement)
  
  // 控制器
  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.05
  
  // 光照
  const ambientLight = new THREE.AmbientLight(0x404040, 0.6)
  scene.add(ambientLight)
  
  const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8)
  directionalLight.position.set(10, 10, 5)
  directionalLight.castShadow = true
  scene.add(directionalLight)
  
  // 网格
  const gridHelper = new THREE.GridHelper(10, 10)
  scene.add(gridHelper)
  
  // 坐标轴
  const axesHelper = new THREE.AxesHelper(5)
  scene.add(axesHelper)
  
  // 开始渲染
  animate()
  
  status.value = 'Three.js初始化完成'
}

// 渲染循环
const animate = () => {
  animationId = requestAnimationFrame(animate)
  controls.update()
  renderer.render(scene, camera)
}

// 加载模型
const loadModel = async () => {
  if (!selectedFile.value) return
  
  status.value = '加载中...'
  
  try {
    // 清除之前的模型
    if (currentModel) {
      scene.remove(currentModel)
    }
    
    const loader = new GLTFLoader()
    
    const gltf = await new Promise<any>((resolve, reject) => {
      loader.load(
        selectedFile.value,
        resolve,
        (progress) => {
          const percent = Math.round((progress.loaded / progress.total) * 100)
          status.value = `加载中... ${percent}%`
        },
        reject
      )
    })
    
    currentModel = gltf.scene
    scene.add(currentModel)
    
    // 自动调整相机
    const box = new THREE.Box3().setFromObject(currentModel)
    const center = box.getCenter(new THREE.Vector3())
    const size = box.getSize(new THREE.Vector3())
    
    const maxDim = Math.max(size.x, size.y, size.z)
    camera.position.set(center.x + maxDim, center.y + maxDim, center.z + maxDim)
    controls.target.copy(center)
    controls.update()
    
    // 更新模型信息
    let vertexCount = 0
    let faceCount = 0
    currentModel.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        const geometry = child.geometry
        if (geometry.attributes.position) {
          vertexCount += geometry.attributes.position.count
        }
        if (geometry.index) {
          faceCount += geometry.index.count / 3
        }
      }
    })
    
    modelInfo.value = `顶点: ${vertexCount}, 面: ${Math.round(faceCount)}`
    status.value = '加载完成'
    
  } catch (error) {
    console.error('模型加载失败:', error)
    status.value = `加载失败: ${error}`
  }
}

// 重置视角
const resetView = () => {
  if (currentModel) {
    const box = new THREE.Box3().setFromObject(currentModel)
    const center = box.getCenter(new THREE.Vector3())
    const size = box.getSize(new THREE.Vector3())
    const maxDim = Math.max(size.x, size.y, size.z)
    
    camera.position.set(center.x + maxDim, center.y + maxDim, center.z + maxDim)
    controls.target.copy(center)
    controls.update()
  }
}

// 切换线框模式
const toggleWireframe = () => {
  wireframe.value = !wireframe.value
  
  if (currentModel) {
    currentModel.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        if (Array.isArray(child.material)) {
          child.material.forEach(mat => {
            mat.wireframe = wireframe.value
          })
        } else {
          child.material.wireframe = wireframe.value
        }
      }
    })
  }
}

// 窗口大小调整
const onWindowResize = () => {
  if (!threeContainer.value || !camera || !renderer) return
  
  const container = threeContainer.value
  camera.aspect = container.clientWidth / container.clientHeight
  camera.updateProjectionMatrix()
  renderer.setSize(container.clientWidth, container.clientHeight)
}

// 生命周期
onMounted(async () => {
  await nextTick()
  initThree()
  window.addEventListener('resize', onWindowResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', onWindowResize)
  
  if (animationId) {
    cancelAnimationFrame(animationId)
  }
  
  if (renderer) {
    renderer.dispose()
  }
  
  if (controls) {
    controls.dispose()
  }
})
</script>

<style lang="scss" scoped>
.simple-glb-test {
  min-height: 100vh;
  background: var(--el-bg-color-page);
  padding: 20px;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
}

h1 {
  text-align: center;
  margin-bottom: 30px;
  color: var(--el-text-color-primary);
}

.controls {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
  align-items: center;
  
  .el-select {
    width: 300px;
  }
}

.three-container {
  width: 100%;
  height: 600px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  overflow: hidden;
  background: #f5f5f5;
}

.status {
  margin-top: 20px;
  padding: 16px;
  background: var(--el-bg-color);
  border-radius: 8px;
  
  p {
    margin: 4px 0;
    color: var(--el-text-color-regular);
  }
}
</style>
