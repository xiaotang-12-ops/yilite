<template>
  <div class="assembly-manual-viewer">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <h2>{{ manualTitle }}</h2>
        <el-tag type="info">{{ currentStep }}/{{ totalSteps }} 步骤</el-tag>
      </div>
      <div class="toolbar-right">
        <el-button-group>
          <el-button :icon="View" @click="resetCamera">重置视角</el-button>
          <el-button :icon="Refresh" @click="toggleExplosion">
            {{ isExploded ? '收起' : '爆炸' }}视图
          </el-button>
          <el-button :icon="Download" @click="exportPDF">导出PDF</el-button>
        </el-button-group>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 左侧：3D查看器 -->
      <div class="viewer-container">
        <div ref="threeContainer" class="three-container"></div>
        
        <!-- 3D控制面板 -->
        <div class="viewer-controls">
          <el-slider
            v-model="explosionProgress"
            :min="0"
            :max="100"
            :disabled="!isExploded"
            @input="updateExplosion"
          />
          <span class="control-label">爆炸程度</span>
        </div>

        <!-- 零件信息卡片 -->
        <transition name="fade">
          <div v-if="selectedPart" class="part-info-card">
            <h3>{{ selectedPart.name }}</h3>
            <p>{{ selectedPart.description }}</p>
            <el-tag v-for="tag in selectedPart.tags" :key="tag" size="small">
              {{ tag }}
            </el-tag>
          </div>
        </transition>
      </div>

      <!-- 右侧：装配步骤 -->
      <div class="steps-container">
        <el-scrollbar height="100%">
          <div class="steps-list">
            <div
              v-for="(step, index) in assemblySteps"
              :key="index"
              :class="['step-card', { active: currentStep === index + 1 }]"
              @click="goToStep(index + 1)"
            >
              <div class="step-header">
                <div class="step-number">{{ index + 1 }}</div>
                <h3>{{ step.title }}</h3>
              </div>
              
              <div class="step-content">
                <p class="step-description">{{ step.description }}</p>
                
                <!-- 涉及零件 -->
                <div v-if="step.parts && step.parts.length" class="step-parts">
                  <h4>涉及零件：</h4>
                  <div class="parts-list">
                    <el-tag
                      v-for="part in step.parts"
                      :key="part"
                      :color="getPartColor(part)"
                      class="part-tag"
                      @click.stop="highlightPart(part)"
                    >
                      {{ part }}
                    </el-tag>
                  </div>
                </div>

                <!-- 所需工具 -->
                <div v-if="step.tools && step.tools.length" class="step-tools">
                  <h4>所需工具：</h4>
                  <div class="tools-list">
                    <el-tag v-for="tool in step.tools" :key="tool" type="info" size="small">
                      {{ tool }}
                    </el-tag>
                  </div>
                </div>

                <!-- 注意事项 -->
                <div v-if="step.warnings && step.warnings.length" class="step-warnings">
                  <el-alert
                    v-for="(warning, wIndex) in step.warnings"
                    :key="wIndex"
                    :title="warning"
                    type="warning"
                    :closable="false"
                  />
                </div>

                <!-- 2D图纸参考 -->
                <div v-if="step.drawing" class="step-drawing">
                  <el-image
                    :src="step.drawing"
                    :preview-src-list="[step.drawing]"
                    fit="contain"
                  >
                    <template #placeholder>
                      <div class="image-placeholder">加载中...</div>
                    </template>
                  </el-image>
                </div>
              </div>

              <div class="step-footer">
                <el-icon><Clock /></el-icon>
                <span>预计时间: {{ step.duration || '5分钟' }}</span>
              </div>
            </div>
          </div>
        </el-scrollbar>

        <!-- 步骤导航 -->
        <div class="steps-navigation">
          <el-button
            :disabled="currentStep === 1"
            @click="previousStep"
          >
            <el-icon><ArrowLeft /></el-icon>
            上一步
          </el-button>
          <el-button
            type="primary"
            :disabled="currentStep === totalSteps"
            @click="nextStep"
          >
            下一步
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  View, Refresh, Download, Clock, ArrowLeft, ArrowRight
} from '@element-plus/icons-vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader'

// Props
interface Props {
  glbUrl: string
  manifestUrl: string
  assemblySpec: any
}

const props = defineProps<Props>()

// 响应式数据
const threeContainer = ref<HTMLDivElement>()
const currentStep = ref(1)
const isExploded = ref(false)
const explosionProgress = ref(0)
const selectedPart = ref<any>(null)

// Three.js对象
let scene: THREE.Scene
let camera: THREE.PerspectiveCamera
let renderer: THREE.WebGLRenderer
let controls: OrbitControls
let model: THREE.Group
let manifest: any = null
let partMeshes: Map<string, THREE.Object3D> = new Map()
let originalPositions: Map<string, THREE.Vector3> = new Map()

// 计算属性
const manualTitle = computed(() => {
  return props.assemblySpec?.doc_meta?.title || '装配说明书'
})

const totalSteps = computed(() => {
  return assemblySteps.value.length
})

const assemblySteps = computed(() => {
  if (!manifest || !manifest.steps) return []
  return manifest.steps
})

// 初始化Three.js场景
const initThreeScene = () => {
  if (!threeContainer.value) return

  const container = threeContainer.value
  const width = container.clientWidth
  const height = container.clientHeight

  // 创建场景
  scene = new THREE.Scene()
  scene.background = new THREE.Color(0xf5f5f5)

  // 创建相机
  camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000)
  camera.position.set(5, 5, 5)
  camera.lookAt(0, 0, 0)

  // 创建渲染器
  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setSize(width, height)
  renderer.setPixelRatio(window.devicePixelRatio)
  renderer.shadowMap.enabled = true
  container.appendChild(renderer.domElement)

  // 添加控制器
  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.05

  // 添加光源
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.6)
  scene.add(ambientLight)

  const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8)
  directionalLight.position.set(10, 10, 5)
  directionalLight.castShadow = true
  scene.add(directionalLight)

  // 添加网格辅助线
  const gridHelper = new THREE.GridHelper(10, 10)
  scene.add(gridHelper)

  // 开始动画循环
  animate()
}

// 动画循环
const animate = () => {
  requestAnimationFrame(animate)
  controls.update()
  renderer.render(scene, camera)
}

// 加载GLB模型
const loadModel = async () => {
  const loader = new GLTFLoader()
  
  try {
    const gltf = await loader.loadAsync(props.glbUrl)
    model = gltf.scene
    
    // 遍历模型，收集所有网格
    model.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        child.castShadow = true
        child.receiveShadow = true
        
        // 保存原始位置
        originalPositions.set(child.uuid, child.position.clone())
        
        // 添加到零件映射
        if (child.name) {
          partMeshes.set(child.name, child)
        }
      }
    })
    
    // 居中模型
    const box = new THREE.Box3().setFromObject(model)
    const center = box.getCenter(new THREE.Vector3())
    model.position.sub(center)
    
    scene.add(model)
    
    ElMessage.success('模型加载成功')
  } catch (error) {
    console.error('模型加载失败:', error)
    ElMessage.error('模型加载失败')
  }
}

// 加载manifest
const loadManifest = async () => {
  try {
    const response = await fetch(props.manifestUrl)
    manifest = await response.json()
    console.log('Manifest加载成功:', manifest)
  } catch (error) {
    console.error('Manifest加载失败:', error)
    ElMessage.error('配置文件加载失败')
  }
}

// 切换爆炸视图
const toggleExplosion = () => {
  isExploded.value = !isExploded.value
  if (isExploded.value) {
    explosionProgress.value = 100
    updateExplosion(100)
  } else {
    explosionProgress.value = 0
    updateExplosion(0)
  }
}

// 更新爆炸效果
const updateExplosion = (progress: number) => {
  if (!model || !manifest || !manifest.explosion_vectors) return

  const factor = progress / 100

  model.traverse((child) => {
    if (child instanceof THREE.Mesh && child.name) {
      const explosionData = manifest.explosion_vectors[child.name]
      if (explosionData) {
        const originalPos = originalPositions.get(child.uuid)
        if (originalPos) {
          const direction = new THREE.Vector3(
            explosionData.direction[0],
            explosionData.direction[1],
            explosionData.direction[2]
          )
          const distance = explosionData.distance * factor
          child.position.copy(originalPos).add(direction.multiplyScalar(distance))
        }
      }
    }
  })
}

// 高亮零件
const highlightPart = (partId: string) => {
  if (!manifest || !manifest.node_map) return

  const nodeName = manifest.node_map[partId]
  const mesh = partMeshes.get(nodeName)

  if (mesh && mesh instanceof THREE.Mesh) {
    // 重置所有零件材质
    partMeshes.forEach((m) => {
      if (m instanceof THREE.Mesh && m.material) {
        (m.material as THREE.MeshStandardMaterial).emissive.setHex(0x000000)
      }
    })

    // 高亮选中零件
    if (mesh.material) {
      (mesh.material as THREE.MeshStandardMaterial).emissive.setHex(0xff6b6b)
    }

    // 相机聚焦到零件
    const box = new THREE.Box3().setFromObject(mesh)
    const center = box.getCenter(new THREE.Vector3())
    controls.target.copy(center)

    selectedPart.value = {
      name: partId,
      description: `零件 ${partId}`,
      tags: ['装配零件']
    }
  }
}

// 获取零件颜色
const getPartColor = (partId: string) => {
  if (!manifest || !manifest.colors) return '#409EFF'
  return manifest.colors[partId] || '#409EFF'
}

// 重置相机
const resetCamera = () => {
  camera.position.set(5, 5, 5)
  camera.lookAt(0, 0, 0)
  controls.target.set(0, 0, 0)
  selectedPart.value = null
}

// 步骤导航
const goToStep = (step: number) => {
  currentStep.value = step

  // 高亮当前步骤涉及的零件
  const stepData = assemblySteps.value[step - 1]
  if (stepData && stepData.parts && stepData.parts.length > 0) {
    highlightPart(stepData.parts[0])
  }
}

const previousStep = () => {
  if (currentStep.value > 1) {
    goToStep(currentStep.value - 1)
  }
}

const nextStep = () => {
  if (currentStep.value < totalSteps.value) {
    goToStep(currentStep.value + 1)
  }
}

// 导出PDF
const exportPDF = () => {
  ElMessage.info('PDF导出功能开发中...')
}

// 窗口大小调整
const handleResize = () => {
  if (!threeContainer.value) return

  const width = threeContainer.value.clientWidth
  const height = threeContainer.value.clientHeight

  camera.aspect = width / height
  camera.updateProjectionMatrix()
  renderer.setSize(width, height)
}

// 生命周期
onMounted(async () => {
  initThreeScene()
  await loadManifest()
  await loadModel()

  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)

  // 清理Three.js资源
  if (renderer) {
    renderer.dispose()
  }
  if (controls) {
    controls.dispose()
  }
})

// 监听步骤变化
watch(currentStep, (newStep) => {
  console.log('当前步骤:', newStep)
})
</script>

<style scoped lang="scss">
.assembly-manual-viewer {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: white;
  border-bottom: 1px solid #e0e0e0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);

  .toolbar-left {
    display: flex;
    align-items: center;
    gap: 16px;

    h2 {
      margin: 0;
      font-size: 20px;
      font-weight: 600;
    }
  }
}

.main-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.viewer-container {
  flex: 1;
  position: relative;
  background: #fafafa;
}

.three-container {
  width: 100%;
  height: 100%;
}

.viewer-controls {
  position: absolute;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  background: white;
  padding: 16px 24px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 300px;

  .control-label {
    font-size: 14px;
    color: #666;
    white-space: nowrap;
  }
}

.part-info-card {
  position: absolute;
  top: 24px;
  right: 24px;
  background: white;
  padding: 16px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  max-width: 300px;

  h3 {
    margin: 0 0 8px 0;
    font-size: 16px;
  }

  p {
    margin: 0 0 12px 0;
    color: #666;
    font-size: 14px;
  }
}

.steps-container {
  width: 400px;
  background: white;
  border-left: 1px solid #e0e0e0;
  display: flex;
  flex-direction: column;
}

.steps-list {
  padding: 16px;
}

.step-card {
  background: white;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
  cursor: pointer;
  transition: all 0.3s;

  &:hover {
    border-color: #409EFF;
    box-shadow: 0 2px 8px rgba(64, 158, 255, 0.2);
  }

  &.active {
    border-color: #409EFF;
    background: #f0f7ff;
  }
}

.step-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;

  .step-number {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: #409EFF;
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
  }

  h3 {
    margin: 0;
    font-size: 16px;
  }
}

.step-description {
  color: #666;
  font-size: 14px;
  line-height: 1.6;
  margin-bottom: 12px;
}

.step-parts,
.step-tools,
.step-warnings {
  margin-bottom: 12px;

  h4 {
    font-size: 13px;
    color: #999;
    margin: 0 0 8px 0;
  }
}

.parts-list,
.tools-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.part-tag {
  cursor: pointer;
  transition: transform 0.2s;

  &:hover {
    transform: scale(1.05);
  }
}

.step-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #999;
  font-size: 13px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}

.steps-navigation {
  padding: 16px;
  border-top: 1px solid #e0e0e0;
  display: flex;
  gap: 12px;

  .el-button {
    flex: 1;
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

