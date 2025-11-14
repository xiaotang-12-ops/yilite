<template>
  <div class="worker-manual-viewer">
    <!-- 顶部进度条 -->
    <div class="top-bar">
      <div class="product-info">
        <h1>{{ productName }}</h1>
        <el-tag type="info" size="large">装配说明书</el-tag>
      </div>

      <div class="progress-section">
        <div class="progress-info">
          <span class="current-step">步骤 {{ currentStepIndex + 1 }}</span>
          <span class="total-steps">/ {{ totalSteps }}</span>
          <span class="step-title">{{ currentStepData?.title }}</span>
        </div>
        <el-progress
          :percentage="progressPercentage"
          :stroke-width="10"
          :color="progressColor"
        />
      </div>

      <div class="top-actions">
        <el-button-group size="large">
          <el-button :icon="ArrowLeft" :disabled="currentStepIndex === 0" @click="previousStep">
            上一步
          </el-button>
          <el-button type="primary" :icon="ArrowRight" :disabled="currentStepIndex === totalSteps - 1" @click="nextStep">
            下一步
          </el-button>
        </el-button-group>

        <!-- 管理员登录/管理按钮 -->
        <div class="admin-section">
          <el-button
            v-if="!isAdmin"
            type="warning"
            size="large"
            @click="showLoginDialog = true"
          >
            <el-icon><Lock /></el-icon>
            管理员登录
          </el-button>

          <div v-else class="admin-actions">
            <el-tag type="success" size="large">管理员模式</el-tag>
            <el-button type="primary" size="large" @click="showEditDialog = true">
              <el-icon><Edit /></el-icon>
              编辑内容
            </el-button>
            <el-button size="large" @click="logout">退出</el-button>
          </div>
        </div>


      </div>
    </div>

    <!-- 主工作区 -->
    <div class="main-workspace" v-if="manualData">
      <!-- 左侧：图纸参考（全屏显示） -->
      <div class="left-sidebar">
        <div class="drawing-section-full">
          <div class="section-title">
            📐 图纸参考
            <span v-if="drawingImages.length > 1" class="page-indicator">
              共{{ drawingImages.length }}张
            </span>
          </div>
          <el-scrollbar class="drawings-container">
            <div class="drawings-list">
              <div
                v-for="(drawingUrl, index) in drawingImages"
                :key="index"
                class="drawing-item"
                :class="{ 'zoomed': zoomedDrawingIndex === index }"
                @click="toggleDrawingZoom(index)"
              >
                <img
                  :src="drawingUrl"
                  :alt="`工程图纸 ${index + 1}`"
                  class="drawing-image"
                  @dragstart.prevent
                />
              </div>
              <div v-if="drawingImages.length === 0" class="drawing-placeholder">
                <el-icon :size="64" color="#ccc"><Picture /></el-icon>
                <p>暂无图纸</p>
              </div>
            </div>
          </el-scrollbar>
        </div>
      </div>

      <!-- 中间：3D模型 -->
      <div class="center-viewer">
        <div class="model-container" ref="modelContainer">
          <!-- Three.js 渲染区域 -->
        </div>

        <!-- 3D控制 -->
        <div class="model-controls">
          <div class="controls-row">
            <el-button-group>
              <el-button :icon="Refresh" @click="resetCamera">重置视角</el-button>
              <el-button
                :icon="View"
                :type="isExploded ? 'primary' : ''"
                @click="toggleExplode"
              >
                {{ isExploded ? '收起' : '爆炸' }}视图
              </el-button>
              <el-button
                :icon="Grid"
                :type="isWireframe ? 'primary' : ''"
                @click="toggleWireframe"
              >
                线框模式
              </el-button>
            </el-button-group>
          </div>

          <!-- 爆炸比例滑块 -->
          <div v-if="isExploded" class="explode-slider">
            <span class="slider-label">爆炸程度:</span>
            <el-slider
              v-model="explodeScale"
              :min="0"
              :max="50"
              :step="1"
              style="width: 300px; margin: 0 12px;"
            />
            <span class="slider-value">{{ explodeScale }}%</span>
          </div>
        </div>
      </div>

      <!-- 右侧：当前步骤详情 -->
      <div class="right-sidebar">
        <el-scrollbar height="100%">

          <!-- 当前步骤 -->
          <div class="step-detail-card" v-if="currentStepData">
            <div class="step-header">
              <div class="step-badge">{{ currentStepIndex + 1 }}</div>
              <h2>{{ currentStepData.title }}</h2>
            </div>

            <div class="step-content">
              <!-- 描述 -->
              <div class="description-section">
                <p class="description-text">{{ currentStepData.operation || currentStepData.description }}</p>
              </div>

              <!-- 操作步骤 -->
              <div class="operations-section" v-if="currentStepData.operation_steps">
                <h3>📝 操作步骤</h3>
                <ol class="operation-list">
                  <li v-for="(op, index) in currentStepData.operation_steps" :key="index">
                    {{ op }}
                  </li>
                </ol>
              </div>

              <!-- 所需工具 -->
              <div class="tools-section" v-if="currentStepData.tools_required && currentStepData.tools_required.length">
                <h3>🔧 所需工具</h3>
                <div class="tools-tags">
                  <el-tag
                    v-for="tool in currentStepData.tools_required"
                    :key="tool"
                    type="info"
                    size="large"
                    effect="plain"
                  >
                    {{ tool }}
                  </el-tag>
                </div>
              </div>

              <!-- 关键点 -->
              <div class="keypoints-section" v-if="currentStepData.key_points && currentStepData.key_points.length">
                <h3>💡 关键点</h3>
                <ul class="keypoints-list">
                  <li v-for="(point, index) in currentStepData.key_points" :key="index">
                    {{ point }}
                  </li>
                </ul>
              </div>

              <!-- ✅ 移除：安全警告已在下方"安全"标签页中统一显示 -->

              <!-- 质检要求 -->
              <div class="operations-section" v-if="currentStepData.quality_check">
                <h3>✅ 质检要求</h3>
                <p>{{ currentStepData.quality_check }}</p>
              </div>

              <!-- 预计时间 -->
              <div class="time-section">
                <el-icon><Clock /></el-icon>
                <span>预计时间: {{ currentStepData.estimated_time_minutes }} 分钟</span>
              </div>
            </div>
          </div>

          <!-- 快速参考标签页 -->
          <div class="quick-reference-tabs">
            <el-tabs v-model="activeTab" type="border-card">
              <el-tab-pane label="焊接" name="welding">
                <div class="tab-content-scroll">


                  <div
                    v-for="(req, index) in currentStepWeldingRequirements"
                    :key="index"
                    class="ref-item"
                  >
                    <div class="ref-header">
                      <strong>步骤{{ req.step_number }} - {{ req.component }}</strong>
                      <el-tag type="warning" size="small" v-if="req.welding_info?.required">
                        需要焊接
                      </el-tag>
                    </div>
                    <p v-if="req.welding_info?.welding_position">📍 {{ req.welding_info.welding_position }}</p>
                    <el-text type="info" size="small" v-if="req.welding_info">
                      {{ req.welding_info.welding_type || req.welding_info.welding_method }} - {{ req.welding_info.weld_size }}
                    </el-text>
                  </div>
                  <el-empty v-if="!currentStepWeldingRequirements.length" description="当前步骤无焊接要求" />
                </div>
              </el-tab-pane>

              <el-tab-pane label="质检" name="quality">
                <div class="tab-content-scroll">
                  <div v-if="currentStepQualityCheck && currentStepQualityCheck.quality_check" class="ref-item">
                    <div class="ref-header">
                      <strong>步骤{{ currentStepQualityCheck.step_number }} - {{ currentStepQualityCheck.component }}</strong>
                    </div>
                    <p>{{ currentStepQualityCheck.quality_check }}</p>
                  </div>
                  <el-empty v-else description="当前步骤无质检要求" />
                </div>
              </el-tab-pane>

              <el-tab-pane label="安全" name="safety">
                <div class="tab-content-scroll">
                  <el-alert
                    v-for="(warning, index) in currentStepSafetyWarnings"
                    :key="index"
                    :title="`步骤${warning.step_number} - ${warning.component}`"
                    type="warning"
                    :description="warning.warning"
                    show-icon
                    :closable="false"
                    style="margin-bottom: 8px"
                  />
                  <el-empty v-if="!currentStepSafetyWarnings.length" description="当前步骤无安全警告" />
                </div>
              </el-tab-pane>

              <el-tab-pane label="FAQ" name="faq">
                <div class="tab-content-scroll">
                  <div
                    v-for="(faq, index) in (manualData.safety_and_faq?.faq_items || manualData.faq_items || []).slice(0, 2)"
                    :key="index"
                    class="ref-item"
                  >
                    <div class="ref-header">
                      <strong>Q: {{ faq.question }}</strong>
                    </div>
                    <p>A: {{ faq.answer?.substring(0, 80) }}...</p>
                  </div>
                  <el-empty v-if="!(manualData.safety_and_faq?.faq_items || manualData.faq_items || []).length" description="暂无常见问题" />
                </div>
              </el-tab-pane>
            </el-tabs>
          </div>
        </el-scrollbar>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-else class="loading-screen">
      <el-icon class="is-loading" :size="64">
        <Loading />
      </el-icon>
      <p>加载装配说明书中...</p>
    </div>

    <!-- 管理员登录Dialog -->
    <el-dialog
      v-model="showLoginDialog"
      title="管理员登录"
      width="400px"
      :close-on-click-modal="false"
    >
      <el-form :model="loginForm" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="loginForm.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            @keyup.enter="handleLogin"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showLoginDialog = false">取消</el-button>
        <el-button type="primary" @click="handleLogin">登录</el-button>
      </template>
    </el-dialog>

    <!-- 内容编辑Dialog -->
    <el-dialog
      v-model="showEditDialog"
      :title="`编辑步骤${currentStepData?.step_number} - ${currentStepData?.action}`"
      width="800px"
      :close-on-click-modal="false"
    >
      <el-tabs v-model="editActiveTab">
        <!-- 焊接注意事项 -->
        <el-tab-pane label="焊接注意事项" name="welding">
          <div class="edit-section">
            <el-alert
              title="提示"
              type="info"
              :closable="false"
              style="margin-bottom: 12px"
            >
              当前步骤的焊接要求（步骤{{ currentStepData?.step_number }}）
            </el-alert>

            <el-button
              type="primary"
              size="small"
              @click="addWeldingRequirement"
              :disabled="editData.welding_requirements.length >= 1"
              style="margin-bottom: 12px"
            >
              <el-icon><Plus /></el-icon>
              添加焊接要求
            </el-button>
            <el-text v-if="editData.welding_requirements.length >= 1" type="info" size="small" style="margin-left: 8px;">
              每个步骤只能有一个焊接要求，如需修改请先删除现有要求
            </el-text>

            <div
              v-for="(req, index) in editData.welding_requirements"
              :key="index"
              class="welding-edit-card"
            >
              <el-card shadow="hover">
                <template #header>
                  <div class="card-header">
                    <span>焊接要求 #{{ index + 1 }}</span>
                    <el-button
                      type="danger"
                      size="small"
                      @click="removeWeldingRequirement(index)"
                    >
                      删除
                    </el-button>
                  </div>
                </template>

                <el-form label-width="120px">
                  <el-form-item label="步骤号">
                    <el-input-number
                      v-model="req.step_number"
                      :min="1"
                      placeholder="步骤号"
                      disabled
                    />
                    <el-text type="info" size="small" style="margin-left: 8px;">
                      步骤号由当前步骤自动确定
                    </el-text>
                  </el-form-item>

                  <el-form-item label="组件名称">
                    <el-input
                      v-model="req.component"
                      placeholder="例如：固定座组件"
                    />
                    <el-text type="warning" size="small" style="margin-left: 8px;">
                      <el-icon><Warning /></el-icon>
                      修改组件名称会同步更新到当前步骤和安全警告模块
                    </el-text>
                  </el-form-item>

                  <el-divider content-position="left">焊接信息</el-divider>

                  <el-form-item label="是否需要焊接">
                    <el-switch v-model="req.welding_info.required" />
                  </el-form-item>

                  <el-form-item label="焊接类型">
                    <el-input
                      v-model="req.welding_info.welding_type"
                      placeholder="例如：角焊（定位焊）"
                    />
                  </el-form-item>

                  <el-form-item label="焊缝尺寸">
                    <el-input
                      v-model="req.welding_info.weld_size"
                      placeholder="例如：点焊，焊点长度约10mm"
                    />
                  </el-form-item>

                  <el-form-item label="焊接位置">
                    <el-input
                      v-model="req.welding_info.welding_position"
                      type="textarea"
                      :rows="2"
                      placeholder="例如：加强板（③）与卷圆板（①）的连接处"
                    />
                  </el-form-item>
                </el-form>
              </el-card>
            </div>

            <el-empty v-if="!editData.welding_requirements.length" description="暂无焊接要求" />
          </div>
        </el-tab-pane>

        <!-- 安全警告 -->
        <el-tab-pane label="安全警告" name="safety">
          <div class="edit-section">
            <el-alert
              title="提示"
              type="info"
              :closable="false"
              style="margin-bottom: 12px"
            >
              当前步骤的安全警告（步骤{{ currentStepData?.step_number }}）
            </el-alert>

            <el-button
              type="primary"
              size="small"
              @click="addSafetyWarning"
              style="margin-bottom: 12px"
            >
              <el-icon><Plus /></el-icon>
              添加安全警告
            </el-button>

            <div
              v-for="(warning, index) in editData.safety_warnings"
              :key="index"
              class="safety-edit-card"
            >
              <el-card shadow="hover">
                <template #header>
                  <div class="card-header">
                    <span>安全警告 #{{ index + 1 }}</span>
                    <el-button
                      type="danger"
                      size="small"
                      @click="removeSafetyWarning(index)"
                    >
                      删除
                    </el-button>
                  </div>
                </template>

                <el-form label-width="100px">
                  <el-form-item label="步骤号">
                    <el-input-number
                      v-model="warning.step_number"
                      :min="1"
                      placeholder="步骤号"
                      disabled
                    />
                    <el-text type="info" size="small" style="margin-left: 8px;">
                      步骤号由当前步骤自动确定
                    </el-text>
                  </el-form-item>

                  <el-form-item label="组件名称">
                    <el-input
                      v-model="warning.component"
                      placeholder="例如：固定座组件"
                      disabled
                      style="background-color: #f5f7fa;"
                    />
                    <el-text type="info" size="small" style="margin-left: 8px;">
                      组件名称由焊接模块自动同步，不可单独修改
                    </el-text>
                  </el-form-item>

                  <el-form-item label="警告内容">
                    <el-input
                      v-model="warning.warning"
                      type="textarea"
                      :rows="3"
                      placeholder="例如：卷圆板属于重物，必须使用行车或叉车进行吊运"
                    />
                  </el-form-item>
                </el-form>
              </el-card>
            </div>

            <el-empty v-if="!editData.safety_warnings.length" description="暂无安全警告" />
          </div>
        </el-tab-pane>

        <!-- 质检要求 -->
        <el-tab-pane label="质检要求" name="quality">
          <div class="edit-section">
            <el-alert
              title="提示"
              type="info"
              :closable="false"
              style="margin-bottom: 12px"
            >
              当前步骤的质检要求（步骤{{ currentStepData?.step_number }}）
            </el-alert>

            <el-form label-width="100px">
              <el-form-item label="质检要求">
                <el-input
                  v-model="editData.quality_check"
                  type="textarea"
                  :rows="6"
                  placeholder="例如：检查焊点牢固性，确保无裂纹、气孔等缺陷"
                />
              </el-form-item>
            </el-form>
          </div>
        </el-tab-pane>

        <!-- FAQ -->
        <el-tab-pane label="常见问题" name="faq">
          <div class="edit-section">
            <el-button
              type="primary"
              size="small"
              @click="addFaqItem"
              style="margin-bottom: 12px"
            >
              <el-icon><Plus /></el-icon>
              添加FAQ
            </el-button>
            <div
              v-for="(faq, index) in editData.faq_items"
              :key="index"
              class="edit-item"
            >
              <el-input
                v-model="faq.question"
                placeholder="问题"
                style="margin-bottom: 8px"
              />
              <el-input
                v-model="faq.answer"
                type="textarea"
                :rows="2"
                placeholder="答案"
              />
              <el-button
                type="danger"
                size="small"
                @click="removeFaqItem(index)"
                style="margin-top: 8px"
              >
                删除
              </el-button>
            </div>
            <el-empty v-if="!editData.faq_items.length" description="暂无常见问题" />
          </div>
        </el-tab-pane>
      </el-tabs>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="saveManualData" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Loading, ArrowLeft, ArrowRight, Picture, Box,
  Refresh, View, Grid, Clock, Lock, Edit, Plus, Warning
} from '@element-plus/icons-vue'
import axios from 'axios'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls'

// ============ 辅助函数 ============



// ============ 类型定义 ============

// 焊接要求编辑类型
interface WeldingRequirementEdit {
  step_id: string
  step_number: number
  component: string
  welding_info: {
    required: boolean
    welding_type: string
    weld_size: string
    welding_position: string
  }
}

// 安全警告编辑类型
interface SafetyWarningEdit {
  step_number: number
  component: string
  warning: string
}

// ✅ 接收路由参数 taskId
const props = defineProps<{
  taskId: string
}>()

const manualData = ref<any>(null)
const currentStepIndex = ref(0)
const activeTab = ref('welding')
const modelContainer = ref<HTMLElement | null>(null)

// 管理员相关
const isAdmin = ref(false)
const showLoginDialog = ref(false)
const showEditDialog = ref(false)
const editActiveTab = ref('welding')
const saving = ref(false)

const loginForm = ref({
  username: '',
  password: ''
})

// 编辑数据（使用新的类型定义）
const editData = ref({
  welding_requirements: [] as WeldingRequirementEdit[],
  safety_warnings: [] as SafetyWarningEdit[],
  quality_check: '' as string,
  faq_items: [] as Array<{ question: string; answer: string }>
})

// 🔧 记录编辑前的原始步骤号（用于保存时精确删除）
const originalStepNumber = ref<number>(0)

// Three.js 相关
let scene: THREE.Scene | null = null
let camera: THREE.PerspectiveCamera | null = null
let renderer: THREE.WebGLRenderer | null = null
let controls: OrbitControls | null = null
let model: THREE.Group | null = null
let gridHelper: THREE.GridHelper | null = null

// 保存每个mesh的原始位置、材质和爆炸方向
let meshOriginalPositions: Map<string, THREE.Vector3> = new Map()
let meshOriginalMaterials: Map<string, THREE.Material> = new Map()
let meshExplodeDirections: Map<string, THREE.Vector3> = new Map()

// ✅ 使用世界坐标系存储，以避免层级导致的局部位置重合问题
let meshWorldOriginalPositions: Map<string, THREE.Vector3> = new Map()
let meshWorldExplodeDirections: Map<string, THREE.Vector3> = new Map()


const isExploded = ref(false)
const isWireframe = ref(false)
const explodeScale = ref(25) // 爆炸比例（0-50，默认25）

// 图纸缩放相关
const zoomedDrawingIndex = ref<number | null>(null)

// 获取当前步骤的图纸列表
const drawingImages = computed(() => {
  if (!currentStepData.value) {
    console.log('⚠️ 当前步骤数据为空')
    return []
  }

  const stepData = currentStepData.value

  // 1. 优先从当前步骤中获取图纸
  const stepDrawings = stepData.drawings ||
                       stepData.pdf_images ||
                       stepData.technical_drawings ||
                       stepData.drawing_images ||
                       []

  if (Array.isArray(stepDrawings) && stepDrawings.length > 0) {
    console.log(`✅ 步骤${currentStepIndex.value + 1}有${stepDrawings.length}张图纸`)
    return stepDrawings
  }

  // 2. 如果步骤中没有图纸，尝试从全局获取
  if (manualData.value) {
    // 从3d_resources中获取
    const resources3d = manualData.value['3d_resources']
    if (resources3d?.pdf_images && Array.isArray(resources3d.pdf_images)) {
      console.log('✅ 从3d_resources.pdf_images找到', resources3d.pdf_images.length, '张图纸（全局）')
      return resources3d.pdf_images
    }

    // 从product_assembly中获取
    const productAssembly = manualData.value.product_assembly
    if (productAssembly?.pdf_images && Array.isArray(productAssembly.pdf_images)) {
      console.log('✅ 从product_assembly.pdf_images找到', productAssembly.pdf_images.length, '张图纸（全局）')
      return productAssembly.pdf_images
    }
  }

  // 3. ⚠️ 临时方案：如果都没有，使用默认路径
  // TODO: 等后端在每个步骤中添加图纸字段后，这段代码会自动失效
  console.warn(`⚠️ 步骤${currentStepIndex.value + 1}未找到图纸数据，使用默认路径（临时方案）`)
  const taskId = props.taskId
  return [
    `/api/manual/${taskId}/pdf_images/page_001.png`,
    `/api/manual/${taskId}/pdf_images/page_002.png`
  ]
})

const productName = computed(() => {
  if (!manualData.value) return '加载中...'
  return manualData.value?.product_overview?.product_name || '装配说明书'
})

// ✅ 构建完整的步骤列表：组件装配 + 产品装配
const allSteps = computed(() => {
  const steps = []

  // 1. 添加组件装配步骤（按assembly_order排序）
  const componentAssembly = manualData.value?.component_assembly || []
  console.log('🔍 [allSteps] 组件装配数量:', componentAssembly.length)

  for (const component of componentAssembly) {
    const componentSteps = component.steps || []
    console.log(`🔍 [allSteps] 组件 "${component.component_name}" 的步骤数量:`, componentSteps.length)

    for (const step of componentSteps) {
      const stepData = {
        ...step,
        chapter_type: 'component_assembly',
        component_code: component.component_code,
        component_name: component.component_name,
        glb_file: component.glb_file
      }
      console.log(`🔍 [allSteps] 添加步骤 ${step.step_number}:`, {
        action: step.action,
        component_name: component.component_name,
        fields: Object.keys(step)
      })
      steps.push(stepData)
    }
  }

  // 2. 添加产品装配步骤
  const productSteps = manualData.value?.product_assembly?.steps || []
  console.log('🔍 [allSteps] 产品装配步骤数量:', productSteps.length)

  for (const step of productSteps) {
    const stepData = {
      ...step,
      chapter_type: 'product_assembly',
      glb_file: 'product_total.glb'
    }
    console.log(`🔍 [allSteps] 添加产品装配步骤 ${step.step_number}:`, {
      action: step.action,
      fields: Object.keys(step)
    })
    steps.push(stepData)
  }

  console.log('🔍 [allSteps] 总步骤数量:', steps.length)
  console.log('🔍 [allSteps] 所有步骤:', steps.map(s => ({
    step_number: s.step_number,
    action: s.action,
    component_name: s.component_name,
    chapter_type: s.chapter_type
  })))

  return steps
})

const totalSteps = computed(() => {
  return allSteps.value.length
})

const currentStepData = computed(() => {
  const stepData = allSteps.value[currentStepIndex.value]

  // 调试：查看步骤数据中是否有图纸字段
  if (stepData) {
    console.log(`📋 步骤${currentStepIndex.value + 1}的数据:`, stepData)
    console.log(`🎨 步骤${currentStepIndex.value + 1}的字段:`, Object.keys(stepData))
  }

  return stepData
})

const currentStepParts = computed(() => {
  // ✅ 兼容两种数据结构：parts_used 或 fasteners
  return currentStepData.value?.parts_used || currentStepData.value?.fasteners || []
})

// ✅ 根据当前步骤的零件自动生成3D高亮mesh列表
const currentStepHighlightMeshes = computed(() => {
  const highlightMeshes: string[] = []
  const allParts: any[] = []

  // ✅ 收集所有需要高亮的零件（主要组件 + 紧固件 + parts_used）
  // 1. 产品装配步骤：components + fasteners
  if (currentStepData.value?.components) {
    // 过滤掉空值
    allParts.push(...currentStepData.value.components.filter((c: any) => c))
  }
  if (currentStepData.value?.fasteners) {
    // 过滤掉空值
    allParts.push(...currentStepData.value.fasteners.filter((f: any) => f))
  }

  // 2. 组件装配步骤：parts_used
  if (currentStepData.value?.parts_used) {
    // 过滤掉空值
    allParts.push(...currentStepData.value.parts_used.filter((p: any) => p))
  }

  // ✅ 3. 从描述中提取BOM序号（备用方案：只有当allParts为空时才使用）
  // 这样可以避免用户修改description时影响3D高亮
  const description: string = (currentStepData.value as any)?.description || ''
  if (allParts.length === 0 && description) {
    console.log('  ⚠️  parts_used为空，尝试从description中提取BOM序号（备用方案）')
    // 圆圈数字到普通数字的映射
    const circleToNumber: { [key: string]: string } = {
      '①': '1', '②': '2', '③': '3', '④': '4', '⑤': '5',
      '⑥': '6', '⑦': '7', '⑧': '8', '⑨': '9', '⑩': '10'
    }

    // 匹配模式：普通数字+号 或 圆圈数字+号
    // 例如："4号"、"4、5号"、"⑨号"、"⑥号"
    const bomSeqPattern = /([①②③④⑤⑥⑦⑧⑨⑩\d]+)[、，号]/g
    const matches = description.matchAll(bomSeqPattern)
    const extractedSeqs = new Set<string>()

    for (const match of matches) {
      let seq = match[1]
      // 如果是圆圈数字，转换为普通数字
      if (circleToNumber[seq]) {
        seq = circleToNumber[seq]
      }
      extractedSeqs.add(seq)
    }

    if (extractedSeqs.size > 0) {
      console.log(`  📝 从描述中提取到BOM序号:`, Array.from(extractedSeqs))

      // 从BOM映射表中查找这些序号对应的node_name
      const componentCode = (currentStepData.value as any)?.component_code
      console.log(`  🔑 当前组件代码:`, componentCode)

      const resources3d = (manualData.value as any)?.['3d_resources']
      console.log(`  📦 3D资源:`, resources3d ? '存在' : '不存在')

      const componentMappings = resources3d?.component_level_mappings
      console.log(`  📦 组件级别映射:`, componentMappings ? Object.keys(componentMappings) : '不存在')

      const bomMappingTable = componentMappings?.[componentCode]?.bom_mapping_table
      console.log(`  📋 BOM映射表:`, bomMappingTable ? `存在(${bomMappingTable.length}项)` : '不存在')

      if (bomMappingTable) {
        console.log(`  📋 BOM映射表中的所有seq:`, bomMappingTable.map((item: any) => `${item.seq}(${typeof item.seq})`))

        extractedSeqs.forEach(seq => {
          console.log(`  🔍 查找seq="${seq}"(${typeof seq})`)
          const bomItem = bomMappingTable.find((item: any) => item.seq === seq)

          if (bomItem) {
            console.log(`  ✅ 找到BOM项:`, bomItem)
            if (bomItem.node_names && bomItem.node_names.length > 0) {
              allParts.push({
                bom_code: bomItem.code,
                bom_seq: seq,
                node_name: bomItem.node_names,
                from_description: true
              })
              console.log(`  📝 描述中的${seq}号 → ${bomItem.code} → ${bomItem.node_names.length}个node`)
            } else {
              console.warn(`  ⚠️  ${seq}号BOM项没有node_names字段或为空数组`)
            }
          } else {
            console.warn(`  ❌ 未找到seq="${seq}"的BOM项`)
          }
        })
      } else {
        console.warn(`  ⚠️  无法获取BOM映射表，componentCode=${componentCode}`)
      }
    }
  }

  // ✅ 优先使用零件中的node_name字段（直接使用GLB中的node名称）
  allParts.forEach((part: any) => {
    if (part.node_name) {
      // node_name可能是数组或单个值
      if (Array.isArray(part.node_name)) {
        highlightMeshes.push(...part.node_name)
        const source = part.from_description ? '(从描述提取)' : '(直接指定)'
        console.log(`  ✅ ${part.bom_code || part.code} → ${part.node_name.length} 个node ${source}:`, part.node_name)
      } else {
        highlightMeshes.push(part.node_name)
        const source = part.from_description ? '(从描述提取)' : '(直接指定)'
        console.log(`  ✅ ${part.bom_code || part.code} → 1 个node ${source}:`, part.node_name)
      }
    } else if (part.mesh_id) {
      // 兼容旧数据：如果有mesh_id，也支持
      if (Array.isArray(part.mesh_id)) {
        highlightMeshes.push(...part.mesh_id)
        console.log(`  ⚠️  ${part.bom_code || part.code} → ${part.mesh_id.length} 个mesh (旧格式):`, part.mesh_id)
      } else {
        highlightMeshes.push(part.mesh_id)
        console.log(`  ⚠️  ${part.bom_code || part.code} → 1 个mesh (旧格式):`, part.mesh_id)
      }
    } else {
      console.warn(`  ❌ ${part.bom_code || part.code} 没有node_name或mesh_id`)
    }
  })

  console.log(`🎯 步骤${currentStepIndex.value + 1}需要高亮的零件:`, allParts.map(p => p.bom_code || p.code))
  console.log(`🎯 步骤${currentStepIndex.value + 1}需要高亮的mesh (${highlightMeshes.length}个):`, highlightMeshes)
  return highlightMeshes
})

// ✅ 判断当前是否是产品总装章节
const isProductAssembly = computed(() => {
  return currentStepData.value?.chapter_type === 'product_assembly'
})

// ✅ 计算已装配的零件（绿色）
const assembledMeshes = computed(() => {
  const assembled: string[] = []

  console.log(`🔍 [计算已装配零件] 当前步骤索引: ${currentStepIndex.value}`)

  // ✅ 产品总装：所有组件的零件都是绿色
  if (isProductAssembly.value) {
    console.log('  📦 [产品总装] 收集所有子组件的零件')

    // ✅ 修复：从product_assembly的步骤1的components中收集子组件的正确node_name
    // 原因：product_total.glb中的子组件node_name（NAUO38-NAUO84）与component_assembly中的node_name（NAUO1-NAUO36）不同
    const productSteps = manualData.value?.product_assembly?.steps || []
    const step1 = productSteps.find((s: any) => s.step_number === 1)

    if (step1 && step1.components) {
      console.log('  ✅ [从步骤1收集子组件] 步骤1标题:', step1.title)
      let subcomponentNodeCount = 0

      step1.components.forEach((comp: any) => {
        if (comp.node_name) {
          const nodes = Array.isArray(comp.node_name) ? comp.node_name : [comp.node_name]
          assembled.push(...nodes)
          subcomponentNodeCount += nodes.length
          console.log(`    - ${comp.bom_name}: ${nodes.length}个node_name`)
        }
      })

      console.log(`  ✅ [子组件总计] 收集了${subcomponentNodeCount}个子组件node_name`)
    } else {
      console.warn('  ⚠️ [警告] 未找到product_assembly的步骤1，无法收集子组件node_name')
    }

    // ✅ 加上前面步骤的紧固件（产品级别的零件）
    const componentAssembly = manualData.value?.component_assembly || []
    const componentStepsCount = componentAssembly.reduce((sum: number, chapter: any) => sum + chapter.steps.length, 0)

    let fastenersNodeCount = 0
    for (let i = componentStepsCount; i < currentStepIndex.value; i++) {
      const step = allSteps.value[i]
      if (step?.fasteners) {
        step.fasteners.forEach((fastener: any) => {
          if (fastener.node_name) {
            const nodes = Array.isArray(fastener.node_name) ? fastener.node_name : [fastener.node_name]
            assembled.push(...nodes)
            fastenersNodeCount += nodes.length
          }
        })
      }
    }

    if (fastenersNodeCount > 0) {
      console.log(`  ✅ [产品级零件] 收集了${fastenersNodeCount}个之前步骤的紧固件node_name`)
    }
  } else {
    // ✅ 组件装配：只累积当前组件内前面步骤的零件
    console.log('  🔧 [组件装配] 只累积当前组件内的前面步骤')

    // 只累积索引 < currentStepIndex 的步骤
    for (let i = 0; i < currentStepIndex.value; i++) {
      const step = allSteps.value[i]

      // ✅ 关键：只累积当前组件的步骤
      if (step?.component_code === currentStepData.value?.component_code) {
        if (step.parts_used) {
          step.parts_used.forEach((part: any) => {
            if (part.node_name) {
              if (Array.isArray(part.node_name)) {
                assembled.push(...part.node_name)
                console.log(`    🟢 [步骤${i+1}] 添加零件 ${part.bom_code}: ${part.node_name.join(', ')}`)
              } else {
                assembled.push(part.node_name)
                console.log(`    🟢 [步骤${i+1}] 添加零件 ${part.bom_code}: ${part.node_name}`)
              }
            }
          })
        }
      }
    }
  }

  console.log(`🟢 已装配零件总数: ${assembled.length}个`, assembled)
  return assembled
})

// 图纸点击放大功能
const toggleDrawingZoom = (index: number) => {
  if (zoomedDrawingIndex.value === index) {
    zoomedDrawingIndex.value = null
  } else {
    zoomedDrawingIndex.value = index
  }
}

// ✅ 过滤当前步骤的焊接信息（只从步骤内嵌字段读取）
const currentStepWeldingRequirements = computed(() => {
  const currentStep = currentStepData.value
  if (!currentStep?.welding?.required) return []

  // 将步骤内嵌的 welding 字段转换为数组格式（保持UI兼容性）
  return [{
    step_id: currentStep.step_id,
    step_number: currentStep.step_number,
    component: currentStep.component_name || '',
    welding_info: currentStep.welding
  }]
})

// ✅ 过滤当前步骤的安全警告（只从步骤内嵌字段读取）
const currentStepSafetyWarnings = computed(() => {
  const currentStep = currentStepData.value
  if (!currentStep) return []

  // 从步骤内嵌字段读取（字符串数组），转换为对象数组（用于显示）
  const warnings = currentStep.safety_warnings || []
  return warnings.map((warning: string) => ({
    step_number: currentStep.step_number,
    component: currentStep.component_name || '',
    warning: warning
  }))
})

// ✅ 从所有步骤中提取质检要求
const qualityCheckpoints = computed(() => {
  const checkpoints: any[] = []

  // 从组件装配步骤中提取
  const componentAssembly = manualData.value?.component_assembly || []
  for (const component of componentAssembly) {
    const steps = component.steps || []
    for (const step of steps) {
      if (step.quality_check) {
        checkpoints.push({
          step_number: step.step_number,
          component: component.component_name,
          quality_check: step.quality_check
        })
      }
    }
  }

  // 从产品装配步骤中提取
  const productSteps = manualData.value?.product_assembly?.steps || []
  for (const step of productSteps) {
    if (step.quality_check) {
      checkpoints.push({
        step_number: step.step_number,
        component: '产品总装',
        quality_check: step.quality_check
      })
    }
  }

  return checkpoints
})

// ✅ 当前步骤的质检要求
const currentStepQualityCheck = computed(() => {
  const currentStep = currentStepData.value
  if (!currentStep) return null

  return {
    step_number: currentStep.step_number,
    component: currentStep.component_name || '产品总装',
    quality_check: currentStep.quality_check || ''
  }
})

const progressPercentage = computed(() => {
  if (totalSteps.value === 0) return 0
  return ((currentStepIndex.value + 1) / totalSteps.value) * 100
})

const progressColor = computed(() => {
  const percentage = progressPercentage.value
  if (percentage < 30) return '#409eff'
  if (percentage < 70) return '#e6a23c'
  return '#67c23a'
})

// ✅ 初始化3D查看器和模型
const init3DViewerAndModel = async () => {
  console.log('🚀 开始初始化3D查看器和模型...')
  await new Promise(resolve => setTimeout(resolve, 100)) // 等待DOM更新
  console.log('⏰ DOM更新等待完成')
  init3DViewer()
  console.log('⏰ 3D查看器初始化完成，开始加载模型...')
  await load3DModel()
  console.log('🎉 3D查看器和模型初始化全部完成')

  // ✅ 延迟后重新调整渲染器尺寸，确保容器已完全渲染
  await new Promise(resolve => setTimeout(resolve, 200))
  if (modelContainer.value && renderer && camera) {
    const width = modelContainer.value.clientWidth
    const height = modelContainer.value.clientHeight
    console.log('🔄 重新调整渲染器尺寸:', { width, height })
    camera.aspect = width / height
    camera.updateProjectionMatrix()
    renderer.setSize(width, height)
  }
}

// ============ 管理员功能 ============

// 管理员登录
const handleLogin = () => {
  const { username, password } = loginForm.value

  // 硬编码验证
  if (username === 'admin' && password === 'admin123') {
    isAdmin.value = true
    sessionStorage.setItem('isAdmin', 'true')
    showLoginDialog.value = false
    ElMessage.success('登录成功！')
    loginForm.value = { username: '', password: '' }
  } else {
    ElMessage.error('用户名或密码错误')
  }
}

// 退出登录
const logout = () => {
  isAdmin.value = false
  sessionStorage.removeItem('isAdmin')
  ElMessage.success('已退出管理员模式')
}

// 打开编辑Dialog时初始化数据（只加载当前步骤的数据）
// 🔧 修复：记住原始 step_id，用于保存时精确删除
watch(showEditDialog, (newVal) => {
  if (newVal && manualData.value && currentStepData.value) {
    const currentStep = currentStepData.value
    const currentStepId = currentStep.step_id
    const currentStepNumber = currentStep.step_number
    const currentComponentName = currentStep.component_name

    // 🔧 记住原始步骤号（兼容性）
    originalStepNumber.value = currentStepNumber

    // 从步骤内嵌字段加载焊接数据
    if (currentStep.welding && currentStep.welding.required) {
      editData.value.welding_requirements = [{
        step_id: currentStepId,
        step_number: currentStepNumber,
        component: currentComponentName || '',
        welding_info: JSON.parse(JSON.stringify(currentStep.welding))
      }]
    } else {
      editData.value.welding_requirements = []
    }

    // 从步骤内嵌字段加载安全警告
    editData.value.safety_warnings = (currentStep.safety_warnings || []).map((warning: string) => ({
      step_number: currentStepNumber,
      component: currentComponentName,
      warning: warning
    }))

    // 加载当前步骤的质检要求
    editData.value.quality_check = currentStep.quality_check || ''

    // FAQ是全局的，不按步骤过滤
    const safetyAndFaq = manualData.value.safety_and_faq || {}
    editData.value.faq_items = JSON.parse(JSON.stringify(safetyAndFaq.faq_items || []))

    console.log('📝 [编辑数据初始化完成]')
    console.log('  - 原始步骤号:', originalStepNumber.value)
    console.log('  - 当前组件名称:', currentComponentName)
    console.log('  - 当前步骤焊接要求数量:', editData.value.welding_requirements.length)
    console.log('  - 当前步骤安全警告数量:', editData.value.safety_warnings.length)
    console.log('  - 当前步骤质检要求:', editData.value.quality_check)
  }
})

// ✅ 监听焊接模块的组件名称变化，自动同步到安全警告模块
watch(
  () => editData.value.welding_requirements.length > 0
    ? editData.value.welding_requirements[0].component
    : null,
  (newComponentName) => {
    if (newComponentName && editData.value.safety_warnings.length > 0) {
      // 同步到所有安全警告
      editData.value.safety_warnings.forEach(warning => {
        warning.component = newComponentName
      })
      console.log('🔄 [组件名称同步] 焊接模块 → 安全警告模块:', newComponentName)
    }
  }
)

// 添加/删除焊接要求
const addWeldingRequirement = () => {
  const currentStep = currentStepData.value
  const stepId = currentStep?.step_id || ''
  const stepNumber = currentStep?.step_number || 1
  const componentName = currentStep?.component_name || ''

  console.log('➕ [添加焊接要求]', { stepId, stepNumber, componentName })

  editData.value.welding_requirements.push({
    step_id: stepId,  // ⭐ 使用 step_id
    step_number: stepNumber,  // 保留（兼容性）
    component: componentName,  // 保留（兼容性）
    welding_info: {
      required: true,
      welding_type: '',
      weld_size: '',
      welding_position: ''
    }
  })
}

const removeWeldingRequirement = (index: number) => {
  editData.value.welding_requirements.splice(index, 1)
}

// 添加/删除安全警告
const addSafetyWarning = () => {
  const currentStep = currentStepData.value
  const stepNumber = currentStep?.step_number || 1
  const componentName = currentStep?.component_name || ''

  console.log('➕ [添加安全警告]', { stepNumber, componentName })

  editData.value.safety_warnings.push({
    step_number: stepNumber,
    component: componentName,  // 🔥 修复：使用 component_name 而不是 action
    warning: ''
  })
}

const removeSafetyWarning = (index: number) => {
  editData.value.safety_warnings.splice(index, 1)
}

// 添加/删除FAQ
const addFaqItem = () => {
  editData.value.faq_items.push({ question: '', answer: '' })
}

const removeFaqItem = (index: number) => {
  editData.value.faq_items.splice(index, 1)
}

// 保存修改（只更新当前步骤的数据）
// 🔧 修复：基于原始数据快照进行精确替换，避免数据丢失和重复
const saveManualData = async () => {
  try {
    saving.value = true

    const currentStep = currentStepData.value
    if (!currentStep) {
      ElMessage.error('当前步骤数据不存在')
      return
    }

    const currentStepNumber = currentStep.step_number

    // 更新manualData
    const updatedData = { ...manualData.value }

    // ========== 更新焊接要求（只保存到步骤内嵌字段） ==========
    const currentStepId = currentStep.step_id || ''

    // 获取用户修改后的组件名称（如果有修改）
    const updatedComponentName = editData.value.welding_requirements.length > 0
      ? editData.value.welding_requirements[0].component
      : currentStep.component_name || ''

    console.log('💾 [保存组件名称]')
    console.log('  - 当前步骤ID:', currentStepId)
    console.log('  - 原组件名称:', currentStep.component_name)
    console.log('  - 新组件名称:', updatedComponentName)
    console.log('  - 焊接要求数量:', editData.value.welding_requirements.length)

    // 过滤有效的焊接数据
    const validWeldingReqs = editData.value.welding_requirements
      .filter(r => r.welding_info && (r.welding_info.welding_type || r.welding_info.weld_size || r.welding_info.welding_position))

    // 更新步骤内嵌的 welding 字段和 component_name
    let stepUpdated = false

    // 更新组件装配步骤
    if (updatedData.component_assembly) {
      for (const component of updatedData.component_assembly) {
        if (component.steps) {
          for (const step of component.steps) {
            if (step.step_id === currentStepId) {
              console.log('  ✅ 找到匹配的步骤，准备更新...')
              console.log('  - 更新前 component.component_name:', component.component_name)

              // 更新焊接数据
              if (validWeldingReqs.length > 0) {
                step.welding = validWeldingReqs[0].welding_info
              } else {
                delete step.welding
              }

              // ✅ 更新组件级别的 component_name（前端显示用的是这个）
              component.component_name = updatedComponentName

              console.log('  - 更新后 component.component_name:', component.component_name)
              stepUpdated = true
              break
            }
          }
        }
        if (stepUpdated) break
      }
    }

    // 更新产品装配步骤
    if (!stepUpdated && updatedData.product_assembly?.steps) {
      for (const step of updatedData.product_assembly.steps) {
        if (step.step_id === currentStepId) {
          // 更新焊接数据
          if (validWeldingReqs.length > 0) {
            step.welding = validWeldingReqs[0].welding_info
          } else {
            delete step.welding
          }
          // 更新组件名称（如果用户修改了）
          step.component_name = updatedComponentName
          stepUpdated = true
          break
        }
      }
    }

    // ========== 更新安全警告（只保存到步骤内嵌字段） ==========
    // 获取用户修改后的组件名称（如果有修改）
    const updatedComponentNameFromSafety = editData.value.safety_warnings.length > 0
      ? editData.value.safety_warnings[0].component
      : updatedComponentName

    // 过滤有效的安全警告
    const validSafetyWarnings = editData.value.safety_warnings
      .filter(w => w.warning && w.warning.trim())
      .map(w => w.warning)

    // 更新步骤内嵌的 safety_warnings 字段和 component_name
    stepUpdated = false

    // 更新组件装配步骤
    if (updatedData.component_assembly) {
      for (const component of updatedData.component_assembly) {
        if (component.steps) {
          for (const step of component.steps) {
            if (step.step_id === currentStepId) {
              step.safety_warnings = validSafetyWarnings
              // ✅ 更新组件级别的 component_name（前端显示用的是这个）
              component.component_name = updatedComponentNameFromSafety
              stepUpdated = true
              break
            }
          }
        }
        if (stepUpdated) break
      }
    }

    // 更新产品装配步骤
    if (!stepUpdated && updatedData.product_assembly?.steps) {
      for (const step of updatedData.product_assembly.steps) {
        if (step.step_id === currentStepId) {
          step.safety_warnings = validSafetyWarnings
          // 更新组件名称（优先使用安全警告中的组件名称）
          step.component_name = updatedComponentNameFromSafety
          stepUpdated = true
          break
        }
      }
    }

    // ========== 更新质检要求 ==========
    // 使用 step_id 精确匹配当前步骤
    stepUpdated = false

    // 更新组件装配步骤中的质检要求
    if (updatedData.component_assembly) {
      for (const component of updatedData.component_assembly) {
        if (component.steps) {
          for (const step of component.steps) {
            if (step.step_id === currentStepId) {
              step.quality_check = editData.value.quality_check
              stepUpdated = true
              break
            }
          }
        }
        if (stepUpdated) break
      }
    }

    // 更新产品装配步骤中的质检要求
    if (!stepUpdated && updatedData.product_assembly?.steps) {
      for (const step of updatedData.product_assembly.steps) {
        if (step.step_id === currentStepId) {
          step.quality_check = editData.value.quality_check
          stepUpdated = true
          break
        }
      }
    }

    // ========== 更新FAQ（全局） ==========
    if (!updatedData.safety_and_faq) {
      updatedData.safety_and_faq = {}
    }
    updatedData.safety_and_faq.faq_items = editData.value.faq_items.filter(
      f => f.question.trim() && f.answer.trim()
    )

    // 调用后端API保存
    const response = await axios.put(`/api/manual/${props.taskId}`, updatedData)

    if (response.data.success) {
      // 更新本地数据
      manualData.value = updatedData

      // 更新localStorage缓存
      localStorage.setItem('current_manual', JSON.stringify(updatedData))

      ElMessage.success(`保存成功！版本号: ${response.data.version}`)
      showEditDialog.value = false

      console.log('✅ [保存成功]')
      console.log('  - 新版本号:', response.data.version)
      console.log('  - 数据已同步到localStorage')
    }
  } catch (error: any) {
    console.error('❌ [保存失败]:', error)
    ElMessage.error('保存失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    saving.value = false
  }
}


// ✅ 优先从 localStorage 加载，如果没有再从 API 加载
const loadLocalJSON = async () => {
  if (!props.taskId) {
    ElMessage.error('任务ID不存在')
    return
  }

  try {
    // 1. 先尝试从 localStorage 加载
    const currentManual = localStorage.getItem('current_manual')
    if (currentManual) {
      const cached = JSON.parse(currentManual)

      // 发送HEAD请求检查版本号
      try {
        const response = await axios.head(`/api/manual/${props.taskId}/version`)
        const serverVersion = response.headers['x-manual-version']

        console.log(`📌 缓存版本: ${cached.version}, 服务器版本: ${serverVersion}`)

        if (cached.version === serverVersion) {
          // 版本一致,使用缓存
          manualData.value = cached
          console.log('✅ 从缓存加载说明书成功 (版本一致):', manualData.value)
          console.log('📋 manualData的所有字段:', Object.keys(manualData.value))

          ElMessage.success('装配说明书加载成功！')

          // ✅ 数据加载完成后初始化3D
          await init3DViewerAndModel()
          return
        } else {
          console.log('⚠️ 版本不一致，重新从API加载')
        }
      } catch (error) {
        console.warn('版本检查失败,使用缓存数据', error)
        manualData.value = cached
        console.log('✅ 从缓存加载说明书成功 (版本检查失败):', manualData.value)
        ElMessage.success('装配说明书加载成功！')
        await init3DViewerAndModel()
        return
      }
    }

    // 2. 版本不一致或无缓存，从后端 API 获取
    const response = await axios.get(`/api/manual/${props.taskId}`)
    manualData.value = response.data

    // 保存到 localStorage
    localStorage.setItem('current_manual', JSON.stringify(manualData.value))

    console.log('✅ 从API加载说明书成功:', manualData.value)
    console.log('📋 manualData的所有字段:', Object.keys(manualData.value))

    ElMessage.success('装配说明书加载成功！')

    // ✅ 数据加载完成后初始化3D
    await init3DViewerAndModel()
  } catch (error: any) {
    console.error('❌ 加载失败:', error)
    ElMessage.error('加载失败: ' + (error.response?.data?.detail || error.message || '未知错误'))
  }
}

const previousStep = () => {
  if (currentStepIndex.value > 0) {
    currentStepIndex.value--
  }
}

const nextStep = () => {
  if (currentStepIndex.value < totalSteps.value - 1) {
    currentStepIndex.value++
  }
}

const goToStep = (index: number) => {
  currentStepIndex.value = index
}

const getImportanceType = (importance: string) => {
  const map: any = { '关键': 'danger', '重要': 'warning', '一般': 'info' }
  return map[importance] || 'info'
}

const getSeverityType = (severity: string) => {
  const map: any = { '高': 'error', '中': 'warning', '低': 'info' }
  return map[severity] || 'warning'
}

const init3DViewer = () => {
  console.log('🎬 开始初始化3D查看器...')

  if (!modelContainer.value) {
    console.error('❌ modelContainer 不存在')
    return
  }

  const container = modelContainer.value
  const width = container.clientWidth
  const height = container.clientHeight

  console.log('📐 容器尺寸:', { width, height })

  if (width === 0 || height === 0) {
    console.error('❌ 容器尺寸为0，无法初始化3D')
    return
  }

  // 创建场景
  scene = new THREE.Scene()
  scene.background = new THREE.Color(0xf0f2f5)
  console.log('✅ 场景创建成功')

  // 创建相机
  camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 10000)
  camera.position.set(500, 500, 500)

  // 创建渲染器
  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setSize(width, height)
  renderer.setPixelRatio(window.devicePixelRatio)
  container.appendChild(renderer.domElement)
  console.log('✅ 渲染器创建成功，已添加到DOM')

  // 添加光源（增强亮度）
  const ambientLight = new THREE.AmbientLight(0xffffff, 1.2)  // 环境光增强到1.2
  scene.add(ambientLight)

  const directionalLight1 = new THREE.DirectionalLight(0xffffff, 1.0)  // 主光源
  directionalLight1.position.set(100, 100, 50)
  scene.add(directionalLight1)

  const directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.6)  // 补光
  directionalLight2.position.set(-100, 50, -50)
  scene.add(directionalLight2)

  const directionalLight3 = new THREE.DirectionalLight(0xffffff, 0.4)  // 顶部补光
  directionalLight3.position.set(0, 200, 0)
  scene.add(directionalLight3)

  // 添加控制器
  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.05

  // 添加底部地面网格（初始位置，会在模型加载后调整）
  const gridSize = 5000  // 大网格
  gridHelper = new THREE.GridHelper(gridSize, 50, 0x888888, 0xcccccc)
  gridHelper.position.y = -1000  // 临时位置
  scene.add(gridHelper)

  // 动画循环
  const animate = () => {
    requestAnimationFrame(animate)
    if (controls) controls.update()
    if (renderer && scene && camera) {
      renderer.render(scene, camera)
    }
  }
  animate()
  console.log('🎬 动画循环已启动')

  // ✅ 调试：暴露到window对象
  ;(window as any).__three_debug__ = { scene, camera, renderer, controls }

  // 窗口大小调整
  const handleResize = () => {
    if (!container || !camera || !renderer) return
    const width = container.clientWidth
    const height = container.clientHeight
    camera.aspect = width / height
    camera.updateProjectionMatrix()
    renderer.setSize(width, height)
  }
  window.addEventListener('resize', handleResize)
}

const load3DModel = async () => {
  console.log('🎨 开始加载3D模型...')

  if (!scene) {
    console.error('❌ scene 不存在，无法加载模型')
    return
  }

  if (!manualData.value) {
    console.error('❌ manualData 不存在，无法获取GLB路径')
    return
  }

  try {
    const loader = new GLTFLoader()

    // ✅ 获取当前步骤对应的GLB文件
    const currentStep = allSteps.value[currentStepIndex.value]
    const glbFile = currentStep?.glb_file || 'product_total.glb'

    // ✅ 构建完整的GLB文件路径（使用相对路径，支持远程访问）
    const glbPath = `/api/manual/${props.taskId}/glb/${glbFile}`
    console.log('📦 加载3D模型:', glbPath)
    console.log('📋 当前步骤:', currentStepIndex.value + 1, '/', allSteps.value.length)
    console.log('📋 GLB文件:', glbFile)

    const gltf = await loader.loadAsync(glbPath)
    console.log('✅ GLB文件加载成功:', gltf)

    model = gltf.scene

    // 先不保存位置，等模型居中后再保存
    let meshCount = 0
    const meshNames: string[] = []
    model.traverse((child: any) => {
      if (child.isMesh) {
        meshCount++
        meshNames.push(child.name)

        // 创建新的高对比度材质（天蓝色，清晰锐利）
        const brightMaterial = new THREE.MeshStandardMaterial({
          color: 0x4A90E2,        // 天蓝色
          metalness: 0.5,
          roughness: 0.4,
          side: THREE.DoubleSide  // 双面渲染
        })

        child.material = brightMaterial
        meshOriginalMaterials.set(child.name, brightMaterial.clone())
      }
    })

    console.log('🔍 模型中的mesh数量:', meshCount)
    console.log('🔍 前20个mesh名称:', meshNames.slice(0, 20))

    // 计算模型边界并居中
    const box = new THREE.Box3().setFromObject(model)
    const center = box.getCenter(new THREE.Vector3())
    const size = box.getSize(new THREE.Vector3())

    console.log('📏 模型尺寸:', {
      size: { x: size.x, y: size.y, z: size.z },
      center: { x: center.x, y: center.y, z: center.z }
    })

    // ✅ 如果模型太小（单位可能是米，但实际是毫米建模），放大倍数
    const maxDimOriginal = Math.max(size.x, size.y, size.z)
    let scaleFactor = 1

    // 根据模型尺寸自动计算放大倍数，目标是让模型达到1500-2000单位（根据图纸1830mm）
    if (maxDimOriginal < 10) {
      scaleFactor = 1000000  // 如果小于10，放大100万倍（模型单位可能是米）
    } else if (maxDimOriginal < 100) {
      scaleFactor = 10000   // 如果小于100，放大1万倍
    } else if (maxDimOriginal < 1000) {
      scaleFactor = 1000    // 如果小于1000，放大1000倍
    }

    if (scaleFactor > 1) {
      console.warn(`⚠️ 模型太小（${maxDimOriginal.toFixed(6)}），放大${scaleFactor}倍`)
      model.scale.set(scaleFactor, scaleFactor, scaleFactor)
      // 重新计算边界
      box.setFromObject(model)
      box.getCenter(center)
      box.getSize(size)
      console.log('📏 放大后的模型尺寸:', {
        size: { x: size.x, y: size.y, z: size.z },
        center: { x: center.x, y: center.y, z: center.z },
        scaleFactor
      })
    }

    // 移动模型到中心
    model.position.sub(center)

    // ✅ 模型居中后，保存每个mesh的世界坐标位置和爆炸方向（世界坐标系）
    const worldCenter = new THREE.Vector3(0, 0, 0) // 已经居中到(0,0,0)
    let nearCenterCount = 0
    const samplePositions: any[] = []

    model.traverse((child: any) => {
      if (child.isMesh) {
        // 保存本地坐标位置（兼容旧逻辑）
        const localPos = child.position.clone()
        meshOriginalPositions.set(child.name, localPos)

        // ✅ 计算世界坐标位置
        const worldPos = new THREE.Vector3()
        child.getWorldPosition(worldPos)
        meshWorldOriginalPositions.set(child.uuid, worldPos.clone())

        // 计算并保存爆炸方向（从中心指向零件，纯径向，使用世界坐标）
        const directionWorld = worldPos.clone().sub(worldCenter)
        const distance = directionWorld.length()

        // 收集前10个零件的位置信息用于调试
        if (samplePositions.length < 10) {
          samplePositions.push({
            name: child.name,
            localPos: `(${localPos.x.toFixed(3)}, ${localPos.y.toFixed(3)}, ${localPos.z.toFixed(3)})`,
            worldPos: `(${worldPos.x.toFixed(3)}, ${worldPos.y.toFixed(3)}, ${worldPos.z.toFixed(3)})`,
            distance: distance.toFixed(6),
            parentName: child.parent?.name || 'unknown'
          })
        }

        if (distance < 1e-6) {
          // 如果零件非常接近中心点，使用均匀随机方向避免重叠
          const theta = Math.random() * Math.PI * 2
          const phi = Math.random() * Math.PI
          directionWorld.set(
            Math.sin(phi) * Math.cos(theta),
            Math.cos(phi),
            Math.sin(phi) * Math.sin(theta)
          )
          nearCenterCount++
        } else {
          directionWorld.normalize()
        }

        meshExplodeDirections.set(child.name, directionWorld.clone()) // 兼容旧逻辑（按名称）
        meshWorldExplodeDirections.set(child.uuid, directionWorld)
      }
    })
    console.log('✅ 已保存', meshWorldOriginalPositions.size, '个mesh的世界位置和爆炸方向')
    console.log('📍 前10个零件的位置信息:', samplePositions)
    if (nearCenterCount > 0) {
      console.log(`⚠️ ${nearCenterCount} 个零件非常接近中心，使用随机方向`)
    }

    // 调整相机位置以适应模型
    const maxDim = Math.max(size.x, size.y, size.z)
    console.log('📏 最大尺寸:', maxDim)

    const fov = camera!.fov * (Math.PI / 180)
    let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2))
    cameraZ *= 2.5 // 增加距离，确保能看到

    console.log('📷 计算的相机距离:', cameraZ)

    // ✅ 如果计算出的距离太小（模型单位可能是毫米），使用固定距离
    if (cameraZ < 10) {
      console.warn('⚠️ 相机距离太小，使用固定距离')
      cameraZ = Math.max(maxDim * 3, 1000) // 至少1000单位
    }

    console.log('📷 最终相机距离:', cameraZ)

    camera!.position.set(cameraZ * 0.7, cameraZ * 0.5, cameraZ * 0.7)
    camera!.lookAt(0, 0, 0)

    if (controls) {
      controls.target.set(0, 0, 0)
      controls.update()
    }

    console.log('📷 相机位置:', camera!.position)
    console.log('🎯 控制器目标:', controls?.target)

    scene.add(model)
    console.log('✅ 3D模型已添加到场景')
    console.log('📊 模型信息:', {
      meshCount: meshOriginalPositions.size,
      boundingBox: size,
      center,
      cameraPosition: camera!.position,
      modelPosition: model.position
    })

    // ✅ 调整网格位置，紧贴模型底部
    if (gridHelper) {
      const modelBox = new THREE.Box3().setFromObject(model)
      const modelMin = modelBox.min
      gridHelper.position.y = modelMin.y  // 网格Y坐标 = 模型最低点Y坐标
      console.log('✅ 网格已调整到模型底部，Y =', modelMin.y)
    }

    // ✅ 调试：暴露model到window对象
    ;(window as any).__three_debug__.model = model

    ElMessage.success('3D模型加载成功！')

    // 高亮当前步骤的零件
    highlightStepParts()
  } catch (error: any) {
    console.error('❌ 3D模型加载失败:', error)
    ElMessage.error('3D模型加载失败: ' + (error.message || '未知错误'))
  }
}

// 切换GLB模型
const switchGLBModel = async (glbFile: string) => {
  console.log('🔄 开始切换GLB模型:', glbFile)

  if (!scene) {
    console.error('❌ scene 不存在，无法切换模型')
    return
  }

  try {
    // 1. 清除旧模型
    if (model) {
      console.log('🗑️ 清除旧模型')
      scene.remove(model)
      model.traverse((child: any) => {
        if (child.isMesh) {
          child.geometry?.dispose()
          child.material?.dispose()
        }
      })
    }

    // 2. 清空材质缓存
    meshOriginalMaterials.clear()
    meshOriginalPositions.clear()
    // ✅ 清空世界坐标缓存
    meshWorldOriginalPositions.clear()
    meshWorldExplodeDirections.clear()

    // 3. 加载新模型
    const loader = new GLTFLoader()
    const glbPath = `/api/manual/${props.taskId}/glb/${glbFile}`
    console.log('📦 加载新模型:', glbPath)

    const gltf = await loader.loadAsync(glbPath)
    console.log('✅ 新模型加载成功')

    model = gltf.scene

    // 4. 初始化材质
    let meshCount = 0
    model.traverse((child: any) => {
      if (child.isMesh) {
        meshCount++
        const brightMaterial = new THREE.MeshStandardMaterial({
          color: 0x4A90E2,
          metalness: 0.5,
          roughness: 0.4,
          side: THREE.DoubleSide
        })
        child.material = brightMaterial
        meshOriginalMaterials.set(child.name, brightMaterial.clone())
        meshOriginalPositions.set(child.name, child.position.clone())
      }
    })

    console.log('🔍 新模型mesh数量:', meshCount)

    // 5. 居中和缩放
    const box = new THREE.Box3().setFromObject(model)
    const center = box.getCenter(new THREE.Vector3())
    const size = box.getSize(new THREE.Vector3())

    const maxDimOriginal = Math.max(size.x, size.y, size.z)
    let scaleFactor = 1

    if (maxDimOriginal < 10) {
      scaleFactor = 1000000
    } else if (maxDimOriginal < 100) {
      scaleFactor = 10000
    } else if (maxDimOriginal < 1000) {
      scaleFactor = 1000
    }

    if (scaleFactor > 1) {
      console.log(`⚠️ 模型太小（${maxDimOriginal.toFixed(6)}），放大${scaleFactor}倍`)
      model.scale.set(scaleFactor, scaleFactor, scaleFactor)
      box.setFromObject(model)
      box.getCenter(center)
      box.getSize(size)
    }

    model.position.set(-center.x, -center.y, -center.z)

    // ✅ 6. 模型居中后，保存每个mesh的世界坐标位置和爆炸方向（世界坐标系）
    const worldCenter = new THREE.Vector3(0, 0, 0) // 已经居中到(0,0,0)
    let nearCenterCount = 0
    const samplePositions: any[] = []

    model.traverse((child: any) => {
      if (child.isMesh) {
        // ✅ 计算世界坐标位置
        const worldPos = new THREE.Vector3()
        child.getWorldPosition(worldPos)
        meshWorldOriginalPositions.set(child.uuid, worldPos.clone())

        // 计算并保存爆炸方向（从中心指向零件，纯径向，使用世界坐标）
        const directionWorld = worldPos.clone().sub(worldCenter)
        const distance = directionWorld.length()

        // 收集前10个零件的位置信息用于调试
        if (samplePositions.length < 10) {
          samplePositions.push({
            name: child.name,
            worldPos: `(${worldPos.x.toFixed(3)}, ${worldPos.y.toFixed(3)}, ${worldPos.z.toFixed(3)})`,
            distance: distance.toFixed(6),
            parentName: child.parent?.name || 'unknown'
          })
        }

        if (distance < 1e-6) {
          // 如果零件非常接近中心点，使用均匀随机方向避免重叠
          const theta = Math.random() * Math.PI * 2
          const phi = Math.random() * Math.PI
          directionWorld.set(
            Math.sin(phi) * Math.cos(theta),
            Math.cos(phi),
            Math.sin(phi) * Math.sin(theta)
          )
          nearCenterCount++
        } else {
          directionWorld.normalize()
        }

        meshExplodeDirections.set(child.name, directionWorld.clone()) // 兼容旧逻辑（按名称）
        meshWorldExplodeDirections.set(child.uuid, directionWorld)
      }
    })
    console.log('✅ 已保存', meshWorldOriginalPositions.size, '个mesh的世界位置和爆炸方向')
    console.log('📍 前10个零件的位置信息:', samplePositions)
    if (nearCenterCount > 0) {
      console.log(`⚠️ ${nearCenterCount} 个零件非常接近中心，使用随机方向`)
    }

    // 7. 调整相机
    const maxDim = Math.max(size.x, size.y, size.z)
    let cameraZ = maxDim * 2.5

    if (cameraZ < 100) {
      cameraZ = Math.max(maxDim * 3, 1000)
    }

    camera!.position.set(cameraZ * 0.7, cameraZ * 0.5, cameraZ * 0.7)
    camera!.lookAt(0, 0, 0)

    if (controls) {
      controls.target.set(0, 0, 0)
      controls.update()
    }

    // 8. 添加到场景
    scene.add(model)
    console.log('✅ 新模型已添加到场景')

    // 9. 调整网格
    if (gridHelper) {
      const modelBox = new THREE.Box3().setFromObject(model)
      gridHelper.position.y = modelBox.min.y
    }

    // 10. 重置爆炸状态
    isExploded.value = false

    ElMessage.success(`已切换到${glbFile}`)
  } catch (error: any) {
    console.error('❌ 切换模型失败:', error)
    ElMessage.error('切换模型失败: ' + (error.message || '未知错误'))
  }
}

// 高亮当前步骤的零件（三色方案：黄色=正在装配，绿色=已装配，灰色=未装配）
const highlightStepParts = () => {
  if (!model || !currentStepData.value) {
    console.log('⚠️ 无法高亮：model或currentStepData不存在')
    return
  }

  // ✅ 获取当前步骤要装配的零件（黄色）
  const currentNodes: string[] = currentStepData.value['3d_highlight'] || currentStepHighlightMeshes.value

  // 添加日志，帮助调试
  if (currentStepData.value['3d_highlight']) {
    console.log('✅ 使用3d_highlight字段:', currentStepData.value['3d_highlight'])
  } else {
    console.log('⚠️ 3d_highlight字段不存在，回退到currentStepHighlightMeshes')
  }

  console.log('🟡 步骤', currentStepIndex.value + 1, '正在装配的零件:', currentNodes)

  // ✅ 获取已装配的零件（绿色）
  const assembledNodes: string[] = assembledMeshes.value
  console.log('🟢 已装配的零件:', assembledNodes)

  // ✅ 兼容旧数据：如果是mesh_xxx格式，转换为NAUOxxx
  const normalizeNodeName = (nodeName: string): string => {
    if (nodeName.startsWith('mesh_')) {
      const number = nodeName.replace('mesh_', '')
      const numericValue = parseInt(number, 10)
      return `NAUO${numericValue}`
    }
    return nodeName
  }

  const normalizedCurrentNodes = currentNodes.map(normalizeNodeName)
  const normalizedAssembledNodes = assembledNodes.map(normalizeNodeName)

  // 统计
  let currentCount = 0
  let assembledCount = 0
  let unassembledCount = 0

  // 遍历模型，设置三种颜色
  model.traverse((child: any) => {
    if (child.isMesh) {
      const nodeName = child.name

      if (normalizedCurrentNodes.includes(nodeName)) {
        // 🟡 正在装配：黄色高亮
        child.material = new THREE.MeshStandardMaterial({
          color: 0xffff00,        // 亮黄色
          emissive: 0xffaa00,     // 橙黄色发光
          emissiveIntensity: 0.8,
          metalness: 0.3,
          roughness: 0.4,
          transparent: false,
          opacity: 1.0
        })
        currentCount++
      } else if (normalizedAssembledNodes.includes(nodeName)) {
        // 🟢 已装配：绿色
        child.material = new THREE.MeshStandardMaterial({
          color: 0x4CAF50,        // 绿色
          emissive: 0x2E7D32,     // 深绿色发光
          emissiveIntensity: 0.3,
          metalness: 0.4,
          roughness: 0.5,
          transparent: false,
          opacity: 1.0
        })
        assembledCount++
      } else {
        // ⚪ 未装配：浅灰色半透明
        const originalMaterial = meshOriginalMaterials.get(nodeName)
        if (originalMaterial) {
          child.material = originalMaterial.clone()
        } else {
          child.material = new THREE.MeshStandardMaterial({
            color: 0xCCCCCC,      // 浅灰色
            metalness: 0.3,
            roughness: 0.6
          })
        }
        child.material.transparent = true
        child.material.opacity = 0.3
        unassembledCount++
      }
    }
  })

  console.log(`✅ 三色渲染完成: 🟡正在装配=${currentCount}, 🟢已装配=${assembledCount}, ⚪未装配=${unassembledCount}`)
}

// 应用爆炸效果（按装配步骤层级爆炸）
const applyExplode = () => {
  if (!model) return

  // ✅ 使用allSteps（包含组件装配+产品装配）
  const steps = allSteps.value

  console.log('🔧 applyExplode 被调用', {
    hasModel: !!model,
    hasManualData: !!manualData.value,
    stepsCount: steps.length,
    isExploded: isExploded.value,
    explodeScale: explodeScale.value
  })

  let processedCount = 0
  let sampleMesh: any = null

  // 以模型当前包围盒尺寸为基准计算爆炸距离（世界坐标）
  const box = new THREE.Box3().setFromObject(model)
  const size = new THREE.Vector3()
  box.getSize(size)
  const maxDim = Math.max(size.x, size.y, size.z)
  const explodeDistanceBase = maxDim * (explodeScale.value / 100)

  model.traverse((child: any) => {
    if (child.isMesh) {
      const key = child.uuid
      const originalWorldPos = meshWorldOriginalPositions.get(key)
      const explodeDirectionWorld = meshWorldExplodeDirections.get(key)

      if (originalWorldPos && explodeDirectionWorld) {
        if (isExploded.value && explodeScale.value > 0) {
          // 使用保存的世界坐标方向（已归一化）
          const direction = explodeDirectionWorld.clone()

          // 径向爆炸：从中心向外，使用与模型尺寸相关的距离
          const explodeDistance = explodeDistanceBase

          // 计算新的世界坐标位置
          const newWorldPos = originalWorldPos.clone().add(direction.multiplyScalar(explodeDistance))

          // 转回子节点的局部坐标
          const newLocalPos = child.parent.worldToLocal(newWorldPos.clone())
          child.position.copy(newLocalPos)
          child.updateMatrix()
          processedCount++

          if (!sampleMesh) {
            sampleMesh = {
              name: child.name,
              explodeDistance,
              originalPos: originalWorldPos.clone(),
              newPos: newWorldPos.clone(),
              direction: explodeDirectionWorld.clone()
            }
          }
        } else {
          // 恢复到原始世界坐标对应的局部位置
          const restoreLocal = child.parent.worldToLocal(originalWorldPos.clone())
          child.position.copy(restoreLocal)
          child.updateMatrix()
          processedCount++
        }
      }
    }
  })

  if (processedCount > 0) {
    console.log(`🔄 爆炸视图更新: ${isExploded.value ? '展开' : '收起'}, 比例=${explodeScale.value}%, 处理了${processedCount}个零件, 基准距离=${explodeDistanceBase.toFixed(3)}`)
    if (sampleMesh) {
      const dirLen = Math.sqrt(
        sampleMesh.direction.x ** 2 +
        sampleMesh.direction.y ** 2 +
        sampleMesh.direction.z ** 2
      )
      console.log('📍 示例零件 (世界坐标径向爆炸):', {
        name: sampleMesh.name,
        原始世界位置: `(${sampleMesh.originalPos.x.toFixed(3)}, ${sampleMesh.originalPos.y.toFixed(3)}, ${sampleMesh.originalPos.z.toFixed(3)})`,
        新世界位置: `(${sampleMesh.newPos.x.toFixed(3)}, ${sampleMesh.newPos.y.toFixed(3)}, ${sampleMesh.newPos.z.toFixed(3)})`,
        方向: `(${sampleMesh.direction.x.toFixed(3)}, ${sampleMesh.direction.y.toFixed(3)}, ${sampleMesh.direction.z.toFixed(3)})`,
        方向长度: dirLen.toFixed(3),
        爆炸距离: sampleMesh.explodeDistance.toFixed(3)
      })
    }
  }
}

// 爆炸视图开关
const toggleExplode = () => {
  if (!model) return
  isExploded.value = !isExploded.value
  applyExplode()
}

// 监听爆炸比例变化
watch(explodeScale, () => {
  if (isExploded.value) {
    applyExplode()
  }
})

// 线框模式
const toggleWireframe = () => {
  if (!model) return

  isWireframe.value = !isWireframe.value

  model.traverse((child: any) => {
    if (child.isMesh) {
      if (child.material) {
        child.material.wireframe = isWireframe.value
      }
    }
  })
}

// 重置相机
const resetCamera = () => {
  if (!camera || !controls || !model) return

  const box = new THREE.Box3().setFromObject(model)
  const center = box.getCenter(new THREE.Vector3())
  const size = box.getSize(new THREE.Vector3())

  const maxDim = Math.max(size.x, size.y, size.z)
  const fov = camera.fov * (Math.PI / 180)
  let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2))
  cameraZ *= 1.5

  camera.position.set(cameraZ, cameraZ, cameraZ)
  camera.lookAt(0, 0, 0)
  controls.target.set(0, 0, 0)
  controls.update()
}



// 监听步骤变化，更新高亮和GLB模型
watch(currentStepIndex, async (newIndex, oldIndex) => {
  const newStep = allSteps.value[newIndex]
  const oldStep = allSteps.value[oldIndex]

  // 检查是否需要切换GLB文件
  const newGlbFile = newStep?.glb_file
  const oldGlbFile = oldStep?.glb_file

  console.log(`📋 步骤切换: ${oldIndex + 1} → ${newIndex + 1}`)
  console.log(`📦 GLB文件: ${oldGlbFile || '无'} → ${newGlbFile || '无'}`)

  // ✅ 修复：只要新步骤有GLB文件，且与旧步骤不同，就切换
  // 不再要求oldGlbFile必须存在（解决首次加载和步骤缺失glb_file的问题）
  if (newGlbFile && newGlbFile !== oldGlbFile) {
    console.log(`🔄 切换GLB模型: ${oldGlbFile || '无'} → ${newGlbFile}`)
    await switchGLBModel(newGlbFile)
  } else if (!newGlbFile) {
    console.warn(`⚠️ 步骤${newIndex + 1}缺少glb_file字段，无法加载3D模型`)
  } else {
    console.log(`✅ GLB文件未变化，无需切换`)
  }

  highlightStepParts()

  // 如果当前是爆炸状态，重新应用爆炸
  if (isExploded.value) {
    isExploded.value = false
    toggleExplode()
  }
})

onMounted(() => {
  // 检查sessionStorage中的登录状态
  const adminStatus = sessionStorage.getItem('isAdmin')
  if (adminStatus === 'true') {
    isAdmin.value = true
  }

  // ✅ 只需要加载数据，3D初始化会在数据加载完成后自动执行
  loadLocalJSON()
})

onUnmounted(() => {
  if (renderer) {
    renderer.dispose()
  }
  if (controls) {
    controls.dispose()
  }
})
</script>

<style scoped lang="scss">
.worker-manual-viewer {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f0f2f5;
  overflow: hidden;
}

.top-bar {
  height: 100px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 16px 24px;
  display: flex;
  align-items: center;
  gap: 24px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);

  .product-info {
    min-width: 250px;

    h1 {
      margin: 0 0 8px 0;
      font-size: 24px;
      font-weight: 700;
    }
  }

  .progress-section {
    flex: 1;

    .progress-info {
      display: flex;
      align-items: baseline;
      gap: 8px;
      margin-bottom: 8px;

      .current-step {
        font-size: 32px;
        font-weight: 700;
      }

      .total-steps {
        font-size: 20px;
        opacity: 0.8;
      }

      .step-title {
        font-size: 16px;
        margin-left: 16px;
        opacity: 0.9;
      }
    }
  }

  .top-actions {
    display: flex;
    gap: 12px;
    align-items: center;
  }

  .admin-section {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .admin-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }
}

.main-workspace {
  flex: 1;
  display: grid;
  grid-template-columns: 300px 1fr 400px;
  gap: 16px;
  padding: 16px;
  overflow: hidden;
}

.left-sidebar, .right-sidebar {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.left-sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;

  .section-title {
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 12px;
    color: #333;
    display: flex;
    align-items: center;
    justify-content: space-between;

    .page-indicator {
      font-size: 14px;
      color: #666;
      font-weight: normal;
    }
  }

  .drawing-section-full {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;

    .drawings-container {
      flex: 1;
      height: 100%;
    }

    .drawings-list {
      display: flex;
      flex-direction: column;
      gap: 16px;
      padding: 8px;
    }

    .drawing-item {
      background: #fafafa;
      border: 2px solid #e5e7eb;
      border-radius: 8px;
      overflow: hidden;
      cursor: pointer;
      transition: all 0.3s ease;

      &:hover {
        border-color: #3b82f6;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
      }

      &.zoomed {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        z-index: 9999;
        border-radius: 0;
        border: none;
        background: rgba(0, 0, 0, 0.95);
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 20px;

        .drawing-image {
          max-width: 95vw;
          max-height: 95vh;
          width: auto;
          height: auto;
        }
      }

      .drawing-image {
        width: 100%;
        height: auto;
        display: block;
        background: white;
        user-select: none;
        -webkit-user-drag: none;
      }
    }

    .drawing-placeholder {
      width: 100%;
      height: 300px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 12px;
      background: #fafafa;
      border: 2px dashed #e5e7eb;
      border-radius: 8px;

      p {
        margin: 0;
        color: #999;
      }
    }
  }

  .drawing-section-old {
    flex: 1;

    .drawing-viewer {
      height: 100%;
      background: #fafafa;
      border: 2px solid #e5e7eb;
      border-radius: 8px;
      overflow: hidden;
      position: relative;
      transition: all 0.3s ease;
      user-select: none;

      &.zoomed {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        z-index: 9999;
        border-radius: 0;
        background: rgba(0, 0, 0, 0.95);
        overflow: hidden;
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .drawing-image {
        width: 100%;
        height: 100%;
        object-fit: contain;
        background: white;
        transition: transform 0.2s ease;
        transform-origin: center center;
        user-select: none;
        -webkit-user-drag: none;
      }

      .drawing-placeholder {
        width: 100%;
        height: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 12px;

        p {
          margin: 0;
          color: #999;
        }
      }

      .drawing-nav-buttons {
        position: absolute;
        bottom: 16px;
        left: 50%;
        transform: translateX(-50%);
        display: flex;
        gap: 12px;
        z-index: 10;

        :deep(.el-button) {
          background: rgba(255, 255, 255, 0.9);
          backdrop-filter: blur(4px);

          &:hover:not(:disabled) {
            background: white;
          }
        }
      }
    }
  }

  .parts-section {
    .parts-list {
      display: flex;
      flex-direction: column;
      gap: 8px;

      .part-card {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px;
        background: #f9fafb;
        border-radius: 8px;
        border: 1px solid #e5e7eb;

        .part-icon {
          font-size: 32px;
        }

        .part-details {
          flex: 1;

          .part-name {
            font-weight: 600;
            margin-bottom: 4px;
          }

          .part-code {
            font-size: 12px;
            color: #666;
            margin-bottom: 4px;
          }
        }
      }

      .empty-hint {
        text-align: center;
        padding: 24px;
        color: #999;
      }
    }
  }
}

.center-viewer {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  display: flex;
  flex-direction: column;

  .model-container {
    flex: 1;
    position: relative;
    overflow: hidden;
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);

    canvas {
      display: block;
      width: 100%;
      height: 100%;
    }
  }

  .model-controls {
    padding: 16px;
    border-top: 1px solid #e5e7eb;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;

    .controls-row {
      display: flex;
      justify-content: center;
    }

    .explode-slider {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 16px;
      background: #f5f7fa;
      border-radius: 8px;

      .slider-label {
        font-size: 14px;
        color: #666;
        white-space: nowrap;
      }

      .slider-value {
        font-size: 14px;
        font-weight: 600;
        color: #7c3aed;
        min-width: 45px;
        text-align: right;
      }
    }
  }
}

.right-sidebar {
  padding: 16px;

  .step-detail-card {
    margin-bottom: 16px;

    .step-header {
      display: flex;
      align-items: center;
      gap: 16px;
      margin-bottom: 20px;

      .step-badge {
        width: 48px;
        height: 48px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        font-weight: 700;
        flex-shrink: 0;
      }

      h2 {
        margin: 0;
        font-size: 20px;
        color: #333;
      }
    }

    .step-content {
      h3 {
        font-size: 16px;
        margin: 16px 0 12px 0;
        color: #333;
      }

      .description-text {
        font-size: 15px;
        line-height: 1.8;
        color: #555;
        margin-bottom: 16px;
      }

      .operation-list {
        padding-left: 20px;
        margin: 0;

        li {
          margin-bottom: 8px;
          line-height: 1.6;
        }
      }

      .tools-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }

      .keypoints-list {
        padding-left: 20px;
        margin: 0;

        li {
          margin-bottom: 8px;
          line-height: 1.6;
          color: #555;
        }
      }

      .time-section {
        margin-top: 16px;
        padding-top: 16px;
        border-top: 1px solid #e5e7eb;
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 14px;
        color: #666;
      }
    }
  }

  .quick-reference-tabs {
    .tab-content-scroll {
      max-height: 300px;
      overflow-y: auto;

      .ref-item {
        padding: 12px;
        margin-bottom: 12px;
        background: #f9fafb;
        border-radius: 8px;

        .ref-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
        }

        p {
          margin: 4px 0;
          font-size: 14px;
          color: #555;
        }
      }
    }
  }
}

// 编辑Dialog样式
.edit-section {
  max-height: 500px;
  overflow-y: auto;
  padding: 12px;

  .edit-item {
    margin-bottom: 16px;
    padding: 12px;
    background: #f9fafb;
    border-radius: 8px;
    border: 1px solid #e5e7eb;
  }

  .welding-edit-card,
  .safety-edit-card {
    margin-bottom: 16px;

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-weight: 600;
    }

    :deep(.el-card__body) {
      padding: 16px;
    }

    :deep(.el-divider) {
      margin: 12px 0;
    }

    :deep(.el-form-item) {
      margin-bottom: 12px;
    }
  }
}

.loading-screen {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 24px;

  p {
    font-size: 18px;
    color: #666;
  }
}
</style>

