<template>
  <div class="generator-page">
    <div class="container">
      <!-- 步骤内容 -->
      <div class="step-content">
        <!-- 步骤1: 文件上传 -->
        <div v-show="currentStep === 0" class="step-panel">
          <div class="upload-section">
            <div class="upload-grid">
              <!-- PDF上传 -->
              <div class="upload-card">
                <h3>
                  <el-icon><Document /></el-icon>
                  工程图纸 (PDF)
                </h3>
                <el-upload
                  ref="pdfUploadRef"
                  class="upload-dragger"
                  drag
                  :auto-upload="false"
                  :multiple="false"
                  :limit="1"
                  accept=".pdf"
                  :on-change="handlePdfChange"
                  :on-exceed="handlePdfExceed"
                  :file-list="pdfFiles"
                >
                  <el-icon class="upload-icon"><UploadFilled /></el-icon>
                  <div class="upload-text">
                    <p>拖拽PDF文件到此处，或<em>点击上传</em></p>
                    <p class="upload-hint">仅支持1个PDF文件，单个文件不超过50MB</p>
                  </div>
                </el-upload>
                
                <!-- PDF文件列表 -->
                <div class="file-list" v-if="pdfFiles.length">
                  <h4>已选择的PDF文件:</h4>
                  <div class="file-item" v-for="file in pdfFiles" :key="file.uid">
                    <el-icon><Document /></el-icon>
                    <span class="file-name">{{ file.name }}</span>
                    <span class="file-size">{{ formatFileSize(file.size) }}</span>
                    <el-button 
                      type="danger" 
                      text 
                      @click="removePdfFile(file)"
                      :icon="Delete"
                    />
                  </div>
                </div>
              </div>

              <!-- 3D模型上传 -->
              <div class="upload-card">
                <h3>
                  <el-icon><Box /></el-icon>
                  3D模型 (STEP格式)
                </h3>
                <el-upload
                  ref="modelUploadRef"
                  class="upload-dragger"
                  drag
                  :auto-upload="false"
                  :multiple="false"
                  :limit="1"
                  accept=".step,.stp"
                  :on-change="handleModelChange"
                  :on-exceed="handleModelExceed"
                  :file-list="modelFiles"
                >
                  <el-icon class="upload-icon"><Box /></el-icon>
                  <div class="upload-text">
                    <p>拖拽STEP模型文件到此处，或<em>点击上传</em></p>
                    <p class="upload-hint">仅支持1个STEP文件 (.step, .stp)，单个文件不超过100MB</p>
                  </div>
                </el-upload>
                
                <!-- 模型文件列表 -->
                <div class="file-list" v-if="modelFiles.length">
                  <h4>已选择的模型文件:</h4>
                  <div class="file-item" v-for="file in modelFiles" :key="file.uid">
                    <el-icon><Box /></el-icon>
                    <span class="file-name">{{ file.name }}</span>
                    <span class="file-size">{{ formatFileSize(file.size) }}</span>
                    <el-button 
                      type="danger" 
                      text 
                      @click="removeModelFile(file)"
                      :icon="Delete"
                    />
                  </div>
                </div>
              </div>
            </div>

            <!-- 文件验证提示 -->
            <div class="validation-section" v-if="pdfFiles.length > 0 || modelFiles.length > 0">
              <h3>
                <el-icon><Warning /></el-icon>
                文件验证
              </h3>
            <div class="validation-content">
              <div class="validation-tips">
                <p><strong>📋 上传要求：</strong></p>
                <ul>
                    <li>当前仅支持<strong>1个PDF</strong>和<strong>1个STEP</strong>，task_id 将以PDF文件名（去后缀）生成</li>
                    <li>请确保上传的文件中包含所需的<strong>组件图</strong>和<strong>整体产品图</strong></li>
                    <li>确保所有图纸都包含<strong>BOM表格</strong>和<strong>技术要求</strong></li>
                  </ul>
                </div>

                <!-- 文件对应性验证结果 -->
                <div class="validation-result" v-if="validationResult">
                  <div v-if="validationResult.isValid" class="validation-success">
                    <el-icon><CircleCheck /></el-icon>
                    <span>文件验证通过！所有PDF和STEP文件都有对应关系</span>
                  </div>
                  <div v-else class="validation-errors">
                    <el-icon><CircleClose /></el-icon>
                    <span>发现文件对应问题：</span>
                    <ul>
                      <li v-for="error in validationResult.errors" :key="error">{{ error }}</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>

            <!-- 项目配置 -->

            <!-- 操作按钮 -->
            <div class="step-actions">
              <el-button 
                type="primary" 
                size="large"
                @click="startGeneration"
                :disabled="!canStartGeneration"
                :loading="isGenerating"
              >
                <el-icon><Right /></el-icon>
                开始生成
              </el-button>
            </div>
          </div>
        </div>

        <!-- 步骤2-4: 处理中 -->
        <div v-show="currentStep >= 1 && currentStep <= 4" class="step-panel">
          <!-- ✅ 全屏日志显示 -->
          <div class="fullscreen-logs-container">
            <!-- 日志头部 -->
            <div class="logs-header-large">
              <h2>📋 多智能体协作可视面板 </h2>
              <div class="header-actions">
                <el-button
                  v-if="isGenerating || taskId"
                  type="danger"
                  text
                  :icon="CircleClose"
                  :loading="isAborting"
                  :disabled="isAborting || !taskId"
                  @click="abortProcessing"
                >
                  强制中断/清理
                </el-button>
                <el-button text @click="clearLogs" :icon="Delete">清空日志</el-button>
              </div>
            </div>

            <!-- 日志内容区域 - 大字体 -->
            <div class="logs-content-large" ref="logsContainer">
              <div
                v-for="log in processingLogs"
                :key="log.id"
                class="log-item-large"
                :class="log.type"
              >
                <span class="log-time-large">{{ log.time }}</span>
                <span class="log-message-large">{{ log.message }}</span>
              </div>
              <div v-if="processingLogs.length === 0" class="empty-logs-large">
                <el-icon size="48"><Document /></el-icon>
                <p>等待任务开始...</p>
              </div>
            </div>

            <!-- ✅ 生成完成后的操作按钮 -->
            <div v-if="!isGenerating && taskId && processingStatus === 'success'" class="completion-actions-large">
              <el-button
                type="primary"
                size="large"
                @click="viewManual"
                :icon="View"
              >
                📖 查看装配说明书
              </el-button>
              <el-button
                size="large"
                @click="resetGenerator"
              >
                🔄 重新生成
              </el-button>
            </div>
          </div>
        </div>

        <!-- 步骤5: 完成 -->
        <div v-show="currentStep === 5" class="step-panel">
          <div class="result-section">
            <div class="result-header">
              <el-icon class="success-icon" size="64"><CircleCheck /></el-icon>
              <h2>装配说明书生成完成！</h2>
              <p>您的智能装配说明书已成功生成，可以预览和下载。</p>
            </div>
            
            <div class="result-actions">
              <el-button 
                type="primary" 
                size="large"
                @click="previewResult"
              >
                <el-icon><View /></el-icon>
                预览说明书
              </el-button>
              
              <el-button 
                size="large"
                @click="downloadResult"
              >
                <el-icon><Download /></el-icon>
                下载文件
              </el-button>
              
              <el-button 
                size="large"
                @click="shareResult"
              >
                <el-icon><Share /></el-icon>
                分享链接
              </el-button>
            </div>
            
            <!-- 结果统计 -->
            <div class="result-stats">
              <div class="stat-item">
                <div class="stat-number">{{ resultStats.pdfPages }}</div>
                <div class="stat-label">PDF页数</div>
              </div>
              <div class="stat-item">
                <div class="stat-number">{{ resultStats.bomItems }}</div>
                <div class="stat-label">BOM项目</div>
              </div>
              <div class="stat-item">
                <div class="stat-number">{{ resultStats.assemblySteps }}</div>
                <div class="stat-label">装配步骤</div>
              </div>
              <div class="stat-item">
                <div class="stat-number">{{ resultStats.processingTime }}</div>
                <div class="stat-label">处理时间(秒)</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- 同名冲突/任务占用弹窗 -->
  <el-dialog
    v-model="conflictDialogVisible"
    :title="conflictDialogTitle"
    width="520px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
  >
    <p style="margin-bottom: 12px;">{{ conflictDialogMessage }}</p>
    <ul class="conflict-list">
        <li v-if="conflictDialog.projectName">任务名称：{{ conflictDialog.projectName }}</li>
        <li v-if="conflictDialog.isProcessing">当前状态：生成中（建议等待或生成第二套）</li>
        <li v-else-if="conflictDialog.manualExists">当前状态：已生成手册</li>
        <li v-if="conflictDialog.createdAt">创建时间：{{ formatConflictTime(conflictDialog.createdAt) }}</li>
        <li v-if="conflictDialog.updatedAt">最后更新：{{ formatConflictTime(conflictDialog.updatedAt) }}</li>
        <li v-if="conflictDialog.manualMtime">手册更新时间：{{ formatConflictTime(conflictDialog.manualMtime) }}</li>
        <li v-if="conflictDialog.suggested">建议下一套名称：{{ conflictDialog.suggested }}</li>
    </ul>
    <template #footer>
      <div v-if="!isBusyConflict" class="conflict-footer">
        <el-button @click="handleConflictChoice('cancel')">取消</el-button>
          <el-button
            type="default"
            @click="handleConflictChoice('duplicate')"
          >
            生成下一套
          </el-button>
        <el-button
          type="primary"
          @click="handleConflictChoice('overwrite')"
        >
          覆盖并备份
        </el-button>
      </div>
      <div v-else class="conflict-footer">
        <el-button type="primary" @click="handleConflictChoice('cancel')">知道了</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onUnmounted, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { UploadFile, UploadFiles } from 'element-plus'
import {
  Document, UploadFilled, Right, CircleCheck,
  Download, View, Delete, Share, Box, Warning,
  CircleClose, Folder, Hide
} from '@element-plus/icons-vue'
import ProcessingSteps from '../components/ProcessingSteps.vue'
import axios from 'axios'

// 响应式数据
const currentStep = ref(0)
const isGenerating = ref(false)
const isAborting = ref(false)
const showLogs = ref(false)

const pdfFiles = ref<UploadFiles>([])
const modelFiles = ref<UploadFiles>([])

const config = reactive({
  projectName: ''
})

// 文件验证相关
const validationResult = ref(null)

// Agent协作相关
// 6个AI智能体（根据 docs/AGENT_ARCHITECTURE.md）
// ✅ 基于实际日志的 8 个 AI 员工
const agents = ref([
  {
    id: 'file-manager',
    name: '📂 文件管理员',
    icon: '📂',
    currentTask: '等待启动...',
    status: 'idle',
    progress: 0,
    results: []
  },
  {
    id: 'bom-analyst',
    name: '📊 BOM数据分析员',
    icon: '📊',
    currentTask: '等待启动...',
    status: 'idle',
    progress: 0,
    results: []
  },
  {
    id: 'assembly-planner',
    name: '🔍 装配规划师',
    icon: '🔍',
    currentTask: '等待启动...',
    status: 'idle',
    progress: 0,
    results: []
  },
  {
    id: '3d-engineer',
    name: '🎨 3D模型工程师',
    icon: '🎨',
    currentTask: '等待启动...',
    status: 'idle',
    progress: 0,
    results: []
  },
  {
    id: 'component-engineer',
    name: '🔨 组件装配工程师',
    icon: '🔨',
    currentTask: '等待启动...',
    status: 'idle',
    progress: 0,
    results: []
  },
  {
    id: 'product-engineer',
    name: '🏗️ 产品总装工程师',
    icon: '🏗️',
    currentTask: '等待启动...',
    status: 'idle',
    progress: 0,
    results: []
  },
  {
    id: 'welding-engineer',
    name: '⚡ 焊接工程师',
    icon: '⚡',
    currentTask: '等待启动...',
    status: 'idle',
    progress: 0,
    results: []
  },
  {
    id: 'safety-officer',
    name: '🛡️ 安全专员',
    icon: '🛡️',
    currentTask: '等待启动...',
    status: 'idle',
    progress: 0,
    results: []
  }
])

// ✅ 清空日志
const clearLogs = () => {
  processingLogs.value = []
}

// ✅ 添加日志
const addLog = (message: string, type: 'info' | 'success' | 'warning' | 'error' = 'info') => {
  const now = new Date()
  const time = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`

  processingLogs.value.push({
    id: Date.now(),
    time,
    message,
    type
  })

  // ✅ 根据日志内容更新 Agent 状态
  updateAgentStatus(message)

  // 自动滚动到底部
  nextTick(() => {
    if (logsContainer.value) {
      logsContainer.value.scrollTop = logsContainer.value.scrollHeight
    }
  })
}

// ✅ 根据日志内容更新 Agent 状态
const updateAgentStatus = (message: string) => {
  // Agent 关键词映射（基于实际后端日志）
  const agentKeywords = {
    'file-manager': ['文件管理', '图纸', 'PDF', '转换成图片', '整理好了所有图纸'],
    'bom-analyst': ['BOM分析', 'BOM数据分析', '零件清单', '提取到', '个零件'],
    'assembly-planner': ['装配规划', '装配顺序', 'Agent 1', '识别出了', '个组件'],
    '3d-engineer': ['3D模型', 'BOM-3D匹配', 'STEP', 'GLB', '匹配率', '代码匹配', 'AI匹配'],
    'component-engineer': ['组件装配工', 'Agent 3', '组件级别', '编写', '装配步骤'],
    'product-engineer': ['产品总装', 'Agent 4', '产品级别', '总装步骤', 'BOM覆盖率'],
    'welding-engineer': ['焊接工程师', 'Agent 5', '焊接要点', '焊接分析'],
    'safety-officer': ['安全专员', 'Agent 6', '安全警告', '安全FAQ']
  }

  // 检查哪个 Agent 正在工作
  for (const [agentId, keywords] of Object.entries(agentKeywords)) {
    const agent = agents.value.find(a => a.id === agentId)
    if (!agent) continue

    // 检查是否包含关键词
    const isWorking = keywords.some(keyword => message.includes(keyword))

    if (isWorking) {
      // 检查是否是完成消息
      if (message.includes('成功') || message.includes('完成') || message.includes('✅')) {
        agent.status = 'completed'
        agent.progress = 100
        agent.currentTask = '已完成'

        // 提取成果信息（支持多个结果）
        if (agentId === 'file-manager') {
          // 文件管理员：提取PDF和图片数量
          const pdfMatch = message.match(/(\d+)\s*个PDF/)
          const imgMatch = message.match(/(\d+)\s*张图片/)
          if (pdfMatch) agent.results.push(`📄 ${pdfMatch[1]} 个PDF图纸`)
          if (imgMatch) agent.results.push(`🖼️ ${imgMatch[1]} 张图片`)
        } else if (agentId === 'bom-analyst') {
          // BOM分析员：提取零件数量
          const match = message.match(/(\d+)\s*个零件/)
          if (match) agent.results.push(`📦 ${match[1]} 个零件`)
        } else if (agentId === 'assembly-planner') {
          // 装配规划师：提取组件数量
          const match = message.match(/(\d+)\s*个组件/)
          if (match) agent.results.push(`🎯 ${match[1]} 个组件`)
        } else if (agentId === '3d-engineer') {
          // 3D工程师：提取匹配率
          const totalMatch = message.match(/总匹配率:\s*BOM\s*(\d+)\/(\d+)\s*\((\d+\.?\d*)%\)/)
          const codeMatch = message.match(/代码:\s*(\d+)/)
          const aiMatch = message.match(/AI:\s*(\d+)/)
          if (totalMatch) {
            agent.results.push(`📊 总匹配率: ${totalMatch[3]}% (${totalMatch[1]}/${totalMatch[2]})`)
          }
          if (codeMatch) agent.results.push(`🔧 代码匹配: ${codeMatch[1]} 项`)
          if (aiMatch) agent.results.push(`🤖 AI匹配: ${aiMatch[1]} 项`)
        } else if (agentId === 'component-engineer') {
          // 组件装配工程师：提取组件数量
          const match = message.match(/(\d+)\s*个组件/)
          if (match) agent.results.push(`🔨 ${match[1]} 个组件`)
        } else if (agentId === 'product-engineer') {
          // 产品总装工程师：提取步骤数和覆盖率
          const stepsMatch = message.match(/(\d+)\s*个总装步骤/)
          const coverageMatch = message.match(/BOM覆盖率:\s*(\d+)\/(\d+)\s*\((\d+\.?\d*)%\)/)
          if (stepsMatch) agent.results.push(`📋 ${stepsMatch[1]} 个总装步骤`)
          if (coverageMatch) {
            agent.results.push(`✅ BOM覆盖率: ${coverageMatch[3]}% (${coverageMatch[1]}/${coverageMatch[2]})`)
          }
        } else if (agentId === 'welding-engineer') {
          // 焊接工程师：提取焊接步骤数
          const match = message.match(/涉及焊接的步骤:\s*(\d+)/)
          if (match) agent.results.push(`⚡ ${match[1]} 个焊接步骤`)
        } else if (agentId === 'safety-officer') {
          // 安全专员
          agent.results.push('🛡️ 安全检查完成')
        }
      } else {
        // 正在工作
        agent.status = 'working'

        // 提取任务描述（去除emoji和特殊字符）
        const cleanMessage = message.replace(/[🔄📊📦📏✅❌⚠️👷🤖🎯📝⏱️💾]/g, '').trim()
        agent.currentTask = cleanMessage.substring(0, 60) + (cleanMessage.length > 60 ? '...' : '')

        // 尝试提取进度
        const progressMatch = message.match(/(\d+)%/)
        if (progressMatch) {
          agent.progress = parseInt(progressMatch[1])
        } else {
          // 根据不同阶段设置默认进度
          if (message.includes('开始') || message.includes('启动')) {
            agent.progress = 10
          } else if (message.includes('处理中') || message.includes('分析')) {
            agent.progress = 50
          } else {
            agent.progress = 70
          }
        }
      }
    }
  }
}

// ✅ 日志容器引用
const logsContainer = ref(null)

// ✅ 查看说明书（带重试逻辑）
const viewManual = async () => {
  if (!taskId.value) {
    ElMessage.error('任务ID不存在，无法查看说明书')
    return
  }

  const loading = ElMessage({
    message: '正在加载说明书...',
    type: 'info',
    duration: 0
  })

  try {
    // ✅ 重试逻辑：最多尝试3次，每次间隔1秒
    let retryCount = 0
    const maxRetries = 3
    let manualData = null

    while (retryCount < maxRetries) {
      try {
        console.log(`尝试获取说明书 (${retryCount + 1}/${maxRetries})...`)
        const response = await axios.get(`/api/manual/${taskId.value}`)
        manualData = response.data
        break // 成功获取，跳出循环
      } catch (error: any) {
        retryCount++
        if (retryCount < maxRetries) {
          console.log(`获取失败，${1}秒后重试...`)
          await new Promise(resolve => setTimeout(resolve, 1000))
        } else {
          throw error // 最后一次尝试失败，抛出错误
        }
      }
    }

    if (!manualData) {
      throw new Error('无法获取说明书数据')
    }

    loading.close()

    // 2. 保存到 localStorage 的历史记录
    const historyKey = 'assembly_manual_history'
    let history = []

    try {
      const stored = localStorage.getItem(historyKey)
      if (stored) {
        history = JSON.parse(stored)
      }
    } catch (e) {
      console.warn('读取历史记录失败:', e)
    }

    // 3. 添加当前记录到历史
    const historyItem = {
      taskId: taskId.value,
      productName: manualData.metadata?.product_name || manualData.product_name || '未命名产品',
      timestamp: new Date().toISOString(),
      data: manualData
    }

    // 检查是否已存在
    const existingIndex = history.findIndex((item: any) => item.taskId === taskId.value)
    if (existingIndex >= 0) {
      // 更新现有记录
      history[existingIndex] = historyItem
    } else {
      // 添加新记录（最多保存 10 条）
      history.unshift(historyItem)
      if (history.length > 10) {
        history = history.slice(0, 10)
      }
    }

    // 4. 保存到 localStorage
    localStorage.setItem(historyKey, JSON.stringify(history))

    // 5. 设置当前查看的说明书
    localStorage.setItem('current_manual', JSON.stringify(manualData))

    // 6. 跳转到查看页面
    ElMessage.success('说明书加载成功！')
    router.push(`/manual/${taskId.value}`)
  } catch (error: any) {
    loading.close()
    console.error('获取说明书失败:', error)

    const errorMsg = error.response?.data?.detail || error.message || '未知错误'
    ElMessage.error({
      message: `获取说明书失败: ${errorMsg}`,
      duration: 5000,
      showClose: true
    })

    // ✅ 显示详细错误信息
    console.error('详细错误信息:', {
      taskId: taskId.value,
      status: error.response?.status,
      statusText: error.response?.statusText,
      data: error.response?.data
    })
  }
}

// ✅ 重新生成
const resetGenerator = () => {
  // 重置所有状态
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
  currentStep.value = 0
  pdfFiles.value = []
  modelFiles.value = []
  taskId.value = ''
  processingProgress.value = 0
  processingStatus.value = undefined
  processingText.value = ''
  processingLogs.value = []
  isGenerating.value = false

  // 重置所有 Agent 状态
  agents.value.forEach(agent => {
    agent.status = 'idle'
    agent.currentTask = '等待启动...'
    agent.progress = 0
    agent.results = []
  })

  ElMessage.info('已重置，可以重新上传文件')
}

// 手动中断当前任务，清理连接并删除后端残留，便于重新上传
const abortProcessing = async () => {
  if (isAborting.value) return

  // 没有任务ID时直接重置前端状态
  if (!taskId.value) {
    resetGenerator()
    ElMessage.info('已中断当前流程，可重新上传文件')
    return
  }

  const confirmed = await ElMessageBox.confirm(
    '确认要强制中断当前生成任务吗？可能已有的中间结果会被清理，需要重新上传后再生成。',
    '确认中断',
    { type: 'warning', confirmButtonText: '立即中断', cancelButtonText: '取消' }
  ).catch(() => false)
  if (!confirmed) return

  isAborting.value = true
  try {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
    // 请求后端删除任务目录/内存记录，后端若仍在处理会返回非 200；仍然继续清理前端状态
    try {
      await axios.delete(`/api/manual/${encodeURIComponent(taskId.value)}`)
      addLog('⏹ 已请求后端清理当前任务', 'warning')
    } catch (error: any) {
      const detail = error?.response?.data?.detail || error?.message || '未知原因'
      addLog(`⏹ 中断请求未完全成功：${detail}`, 'warning')
    }
    localStorage.removeItem(RECOVERY_TASK_KEY)
    resetGenerator()
    processingStatus.value = 'exception'
    processingText.value = '已手动中断'
    ElMessage.info('已手动中断，您可以重新上传文件重新生成')
  } finally {
    isAborting.value = false
  }
}

const agentDialogs = ref([])
const typingAgent = ref(null)
const dialogContainer = ref(null)

const processingProgress = ref(0)
const processingStatus = ref<'success' | 'exception' | undefined>()
const processingText = ref('')

// 新增：可视化处理相关数据
const currentProcessingStage = ref('pdf_bom') // pdf_bom, parallel, matching, generate
const processingData = ref({})
const processingStepsRef = ref()
const taskId = ref('')
const generatedManualUrl = ref('')

// 同名冲突弹窗数据
const conflictDialogVisible = ref(false)
const conflictDialog = reactive<{
  code?: string
  taskId: string
  projectName?: string
  isProcessing: boolean
  manualExists: boolean
  createdAt?: string
  updatedAt?: string
  manualMtime?: string
  suggested?: string
  message?: string
}>({
  code: '',
  taskId: '',
  projectName: '',
  isProcessing: false,
  manualExists: false,
  createdAt: '',
  updatedAt: '',
  manualMtime: '',
  suggested: '',
  message: ''
})

const isBusyConflict = computed(() => conflictDialog.code === 'TASK_BUSY')
const conflictDialogTitle = computed(() => (isBusyConflict.value ? '当前任务运行中' : '任务已存在'))
const conflictDialogMessage = computed(() => {
  if (conflictDialog.message) {
    return conflictDialog.message
  }
  return isBusyConflict.value ? '当前有任务正在运行，请等待完成后再试。' : '检测到同名任务，请选择操作：'
})

const resetToUploadStep = (keepFiles: boolean = true) => {
  currentStep.value = 0
  processingStatus.value = undefined
  processingText.value = ''
  processingProgress.value = 0
  isGenerating.value = false
  processingLogs.value = []
  taskId.value = ''
  agents.value.forEach(agent => {
    agent.status = 'idle'
    agent.currentTask = '等待启动...'
    agent.progress = 0
    agent.results = []
  })
  if (!keepFiles) {
    pdfFiles.value = []
    modelFiles.value = []
  }
}

const processingLogs = ref<Array<{
  id: number
  time: string
  message: string
  type: 'info' | 'success' | 'warning' | 'error'
}>>([])

const resultStats = reactive({
  pdfPages: 0,
  bomItems: 0,
  assemblySteps: 0,
  processingTime: 0
})

// 处理步骤配置
const processingSteps = [
  {
    title: 'AI视觉解析中...',
    description: 'Qwen3-VL模型正在分析您的工程图纸，识别BOM表格、技术要求和尺寸标注'
  },
  {
    title: '专家工艺生成中...',
    description: 'DeepSeek专家模型正在基于解析结果生成专业的装配工艺规程'
  },
  {
    title: '3D模型处理中...',
    description: 'Blender正在自动转换和优化您的3D模型，生成Web友好的格式'
  },
  {
    title: '装配说明书生成中...',
    description: '正在整合所有信息，生成最终的交互式装配说明书'
  }
]

// 计算属性
const canStartGeneration = computed(() => {
  return pdfFiles.value.length === 1 &&
         modelFiles.value.length === 1 &&
         (!validationResult.value || validationResult.value.isValid)
})

// 将项目名称与 PDF 文件名保持一致
const syncProjectNameFromPdf = () => {
  if (!pdfFiles.value.length) return
  const pdfName = pdfFiles.value[0].name.replace(/\.pdf$/i, '')
  config.projectName = pdfName
}

// 方法
const handlePdfChange = (file: UploadFile, fileList: UploadFiles) => {
  if (fileList.length > 1) {
    ElMessage.warning('仅支持上传1个PDF文件，已保留最近选择的文件')
    pdfFiles.value = [fileList[fileList.length - 1]]
  } else {
    pdfFiles.value = fileList
  }
  syncProjectNameFromPdf()
  validateFileCorrespondence()
}

const handlePdfExceed = () => {
  ElMessage.warning('一次只能上传1个PDF文件')
}

const handleModelChange = (file: UploadFile, fileList: UploadFiles) => {
  if (fileList.length > 1) {
    ElMessage.warning('仅支持上传1个STEP文件，已保留最近选择的文件')
    modelFiles.value = [fileList[fileList.length - 1]]
  } else {
    modelFiles.value = fileList
  }
  validateFileCorrespondence()
}

const handleModelExceed = () => {
  ElMessage.warning('一次只能上传1个STEP文件')
}

// 文件对应性验证
const validateFileCorrespondence = () => {
  if (pdfFiles.value.length === 0 && modelFiles.value.length === 0) {
    validationResult.value = null
    return
  }

  const errors = []

  // 限制数量
  if (pdfFiles.value.length !== 1) {
    errors.push(`需要上传1个PDF文件（当前${pdfFiles.value.length}个）`)
  }
  if (modelFiles.value.length !== 1) {
    errors.push(`需要上传1个STEP文件（当前${modelFiles.value.length}个）`)
  }

  // 检查文件名对应
  validationResult.value = {
    isValid: errors.length === 0,
    errors: errors
  }
}

const removePdfFile = (file: UploadFile) => {
  const index = pdfFiles.value.indexOf(file)
  if (index > -1) {
    pdfFiles.value.splice(index, 1)
  }
  if (pdfFiles.value.length === 0) {
    config.projectName = ''
  } else {
    syncProjectNameFromPdf()
  }
}

const removeModelFile = (file: UploadFile) => {
  const index = modelFiles.value.indexOf(file)
  if (index > -1) {
    modelFiles.value.splice(index, 1)
  }
}

const formatFileSize = (size: number) => {
  if (size < 1024) return size + ' B'
  if (size < 1024 * 1024) return (size / 1024).toFixed(1) + ' KB'
  return (size / (1024 * 1024)).toFixed(1) + ' MB'
}

const startGeneration = async () => {
  // 验证文件
  if (pdfFiles.value.length !== 1 || modelFiles.value.length !== 1) {
    ElMessage.warning('请上传1个PDF和1个STEP文件')
    return
  }

  // 若未填项目名，自动取PDF去后缀
  if (!config.projectName.trim() && pdfFiles.value.length === 1) {
    config.projectName = pdfFiles.value[0].name.replace(/\.pdf$/i, '')
  }

  // 验证文件对应关系
  if (validationResult.value && !validationResult.value.isValid) {
    ElMessage.error('请先解决文件对应性问题')
    return
  }

  isGenerating.value = true
  currentStep.value = 1
  processingStatus.value = undefined
  processingProgress.value = 0
  processingText.value = '准备上传文件...'

  // 清空之前的日志和对话
  processingLogs.value = []
  agentDialogs.value = []

  // 初始化Agent状态
  agents.value.forEach(agent => {
    agent.status = 'idle'
    agent.progress = 0
    agent.currentTask = '等待启动...'
  })

  try {
    // 1. 上传文件
    currentStep.value = 2
    processingStepsRef.value?.addLog('📤 开始上传文件...', 'info')
    await uploadFiles()
    processingStepsRef.value?.addLog('✅ 文件上传完成', 'success')

    // 2. 启动并行处理（会自动建立WebSocket连接）
    currentStep.value = 3
    processingText.value = '启动并行处理流水线...'
    processingStepsRef.value?.addLog('🚀 启动生产级并行处理流水线', 'info')

    await startGenerationTask('prompt')

    // WebSocket会处理后续的进度更新和完成通知
    // 不需要在这里设置完成状态

  } catch (error: any) {
    console.error('生成失败:', error)
    const status = error?.status || error?.response?.status
    const data = error?.data || error?.response?.data
    const detail = data?.detail || error?.detail || error?.message || error?.response?.data?.detail

    // 409 冲突：展示自定义弹窗，三选项
    const conflict = data?.code ? data : data?.detail
    if (status === 409 && conflict?.code) {
      openConflictDialog(conflict)
      isGenerating.value = false
      return
    }

    processingStatus.value = 'exception'
    processingText.value = '生成失败'
    addLog(`❌ 生成失败: ${detail}`, 'error')
    isGenerating.value = false

    // 关闭 SSE
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
  }
}

// 上传文件到后端
const uploadFiles = async () => {
  const formData = new FormData()

  // 添加PDF文件
  pdfFiles.value.forEach(file => {
    if (file.raw) {
      formData.append('pdf_files', file.raw)
    }
  })

  // 添加3D模型文件
  modelFiles.value.forEach(file => {
    if (file.raw) {
      formData.append('model_files', file.raw)
    }
  })

  const response = await axios.post('/api/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })

  if (!response.data.success) {
    throw new Error('文件上传失败')
  }

  return response.data.data
}

// EventSource 连接（SSE）
let eventSource: EventSource | null = null
const RECOVERY_TASK_KEY = 'generator_current_task'

// 开始生成任务 - 使用 SSE 实时更新
const formatConflictTime = (value?: string) => {
  if (!value) return ''
  const d = new Date(value)
  return isNaN(d.getTime()) ? value : d.toLocaleString()
}

const openConflictDialog = (conflict: any) => {
  conflictDialog.code = conflict.code || ''
  conflictDialog.taskId = conflict.task_id || ''
  conflictDialog.projectName = conflict.project_name || ''
  conflictDialog.isProcessing = Boolean(conflict.is_processing)
  conflictDialog.manualExists = Boolean(conflict.manual_exists)
  conflictDialog.createdAt = conflict.created_at
  conflictDialog.updatedAt = conflict.updated_at
  conflictDialog.manualMtime = conflict.manual_mtime
  conflictDialog.suggested = conflict.suggested_duplicate_id || ''
  conflictDialog.message = conflict.message || '检测到同名任务，请选择操作：'
  conflictDialogVisible.value = true
}

const handleConflictChoice = async (action: 'overwrite' | 'duplicate' | 'cancel') => {
  conflictDialogVisible.value = false
  if (action === 'cancel') {
    resetToUploadStep(true)
    return
  }
  try {
    isGenerating.value = true
    await startGenerationTask(action)
  } catch (e) {
    // startGeneration 已有错误处理，这里不重复提示
  }
}

const startGenerationTask = async (conflictStrategy: 'prompt' | 'overwrite' | 'duplicate' = 'prompt') => {
  try {
    const response = await axios.post('/api/generate', {
      config: {
        projectName: config.projectName
      },
      pdf_files: pdfFiles.value.map(f => f.name),
      model_files: modelFiles.value.map(f => f.name),
      conflict_strategy: conflictStrategy
    })

    if (!response.data.success) {
      throw new Error('生成失败: ' + (response.data.detail || '未知错误'))
    }

    const newTaskId = response.data.task_id
    taskId.value = newTaskId
    // 若后端生成了新的 task_id（duplicate 场景），保持项目名与 task_id 对齐
    if (config.projectName !== newTaskId) {
      config.projectName = newTaskId
    }
    localStorage.setItem(RECOVERY_TASK_KEY, newTaskId)

    // 建立 SSE 连接
    connectEventSource(newTaskId)

    return newTaskId
  } catch (error: any) {
    const detail = error.response?.data?.detail || error.message || '未知错误'
    const status = error.response?.status
    const data = error.response?.data
    // 抛出结构化错误，供上层区分是否为同名任务冲突
    if (status === 409 && data?.code) {
      openConflictDialog(data)
      throw {
        message: detail,
        detail,
        status,
        data
      }
    }
    throw {
      message: detail,
      detail,
      status,
      data
    }
  }
}

// 连接 EventSource (SSE)
const connectEventSource = (taskId: string) => {
  const sseUrl = `http://localhost:8008/api/stream/${taskId}`
  eventSource = new EventSource(sseUrl)

  eventSource.onopen = () => {
    console.log('✅ SSE 连接已建立')
    addLog('✅ 实时日志连接成功', 'success')
  }

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      handleSSEMessage(data)
    } catch (error) {
      console.error('解析 SSE 消息失败:', error)
    }
  }

  eventSource.onerror = (error) => {
    console.error('❌ SSE 错误:', error)
    eventSource?.close()
    eventSource = null
  }
}

// 处理 SSE 消息
const handleSSEMessage = (data: any) => {
  console.log('收到 SSE 消息:', data)

  switch (data.type) {
    case 'connected':
      // 连接成功
      addLog(`📡 ${data.message}`, 'info')
      break

    case 'log':
      // ✅ 实时日志消息
      addLog(data.message, 'info')
      break

    case 'progress':
      // 进度更新
      processingProgress.value = data.progress
      if (data.status === 'processing') {
        processingStatus.value = undefined
        processingText.value = '正在处理中...'
      }
      break

    case 'status_change':
      // 状态变化
      if (data.status === 'processing') {
        addLog('🚀 任务开始处理...', 'info')
      } else if (data.status === 'completed') {
        addLog('✅ 任务处理完成', 'success')
      } else if (data.status === 'failed') {
        addLog('❌ 任务处理失败', 'error')
      }
      break

    case 'complete':
      // 任务完成
      eventSource?.close()
      eventSource = null

      if (data.status === 'completed') {
        processingProgress.value = 100
        processingStatus.value = 'success'
        processingText.value = '生成完成！'
        currentStep.value = 4

        addLog('✅ 装配说明书生成完成！', 'success')

        // ✅ 不自动跳转，只显示成功消息
        ElMessage.success({
          message: '装配说明书生成完成！',
          duration: 3000
        })
        localStorage.removeItem(RECOVERY_TASK_KEY)
      } else {
        processingStatus.value = 'exception'
        processingText.value = data.error || '生成失败'
        addLog(`❌ ${data.error}`, 'error')
        localStorage.removeItem(RECOVERY_TASK_KEY)
      }

      isGenerating.value = false
      break

    case 'error':
      // 错误消息
      processingStatus.value = 'exception'
      processingText.value = data.message || '发生错误'
      addLog(`❌ ${data.message}`, 'error')
      eventSource?.close()
      eventSource = null
      isGenerating.value = false
      localStorage.removeItem(RECOVERY_TASK_KEY)
      break
  }
}

// 删除复杂的监控逻辑，现在是同步处理

// 更新处理数据用于可视化
const updateProcessingData = (stage: string, taskData: any) => {
  console.log('更新处理数据:', stage, taskData)

  const data = { ...processingData.value }

  // 处理并行进度数据
  if (taskData.parallel_progress) {
    data.parallel_progress = taskData.parallel_progress
  }

  // 处理阶段数据
  if (taskData.stage_data) {
    data.stage_data = taskData.stage_data
  }

  switch (stage) {
    case 'pdf_bom':
      // 阶段1: PDF解析 - 提取BOM表
      data.pdf_bom = {
        ...data.pdf_bom,
        ...taskData
      }
      break
    case 'parallel':
      // 阶段2: 并行处理
      data.pdf_deep = taskData.pdf_deep
      data.step_extract = taskData.step_extract
      break
    case 'matching':
      // 阶段3: BOM-STEP匹配
      data.matching = {
        ...data.matching,
        ...taskData
      }
      break
    case 'generate':
      // 阶段4: 生成说明书
      data.generate = {
        ...data.generate,
        ...taskData
      }
      break
    case 'pdf':
      data.files = taskData.pdf_analysis || []
      break
    case 'model':
      data.models = taskData.model_conversion || []
      break
    case 'ai':
      data.aiProgress = taskData.ai_progress || { vision: 0, expert: 0 }
      data.visionResults = taskData.vision_results || []
      data.expertInsights = taskData.expert_insights || []
      break
  }

  if (taskData.logs) {
    data.logs = taskData.logs
  }

  processingData.value = data
}

// 根据日志内容更新步骤状态
const updateStepByLog = (message: string, level: string) => {
  const msg = message.toLowerCase()

  // ✅ 修复: 如果是错误日志，立即停止流程并显示错误
  if (level === 'error') {
    processingStatus.value = 'exception'
    processingText.value = '处理失败'
    isGenerating.value = false

    // 显示错误对话框
    ElMessageBox.alert(message, '处理失败', {
      type: 'error',
      confirmButtonText: '确定'
    })

    return  // 不再继续更新步骤
  }

  // 步骤1: PDF文本提取
  if (msg.includes('开始pdf文本提取')) {
    processingStepsRef.value?.updateStep('pdf_text', 'active')
  } else if (msg.includes('pdf文本提取完成')) {
    const match = message.match(/(\d+)个BOM项/)
    const data = match ? {
      'BOM项数': match[1],
      '详细信息': message
    } : {}
    processingStepsRef.value?.updateStep('pdf_text', 'complete', data)
  }

  // 步骤2: STEP→GLB转换
  else if (msg.includes('开始step→glb转换')) {
    processingStepsRef.value?.updateStep('step_glb', 'active')
  } else if (msg.includes('step→glb转换完成')) {
    const fileMatch = message.match(/(\d+)个文件/)
    const partMatch = message.match(/共(\d+)个零件/)
    const data: Record<string, any> = {}
    if (fileMatch) data['文件数'] = fileMatch[1]
    if (partMatch) data['零件总数'] = partMatch[1]
    data['详细信息'] = message
    processingStepsRef.value?.updateStep('step_glb', 'complete', data)
  }

  // 步骤3: Qwen-VL视觉分析
  else if (msg.includes('qwen-vl视觉智能体启动')) {
    processingStepsRef.value?.updateStep('vision', 'active')
  } else if (msg.includes('qwen-vl视觉分析完成') || msg.includes('qwen-vl返回数据解析成功')) {
    const relationMatch = message.match(/(\d+)个装配关系/)
    const reqMatch = message.match(/(\d+)个技术要求/)
    const data: Record<string, any> = {}
    if (relationMatch) data['装配关系'] = relationMatch[1]
    if (reqMatch) data['技术要求'] = reqMatch[1]
    if (Object.keys(data).length > 0) {
      data['详细信息'] = message
      processingStepsRef.value?.updateStep('vision', 'complete', data)
    }
  }

  // 步骤4: DeepSeek智能匹配
  else if (msg.includes('deepseek开始匹配') || msg.includes('调用deepseek专家模型')) {
    processingStepsRef.value?.updateStep('matching', 'active')
  } else if (msg.includes('deepseek匹配完成')) {
    const partMatch = message.match(/(\d+)个零件/)
    const stepMatch = message.match(/(\d+)个装配步骤/)
    const rateMatch = message.match(/匹配率([\d.]+)%/)
    const matchedMatch = message.match(/\((\d+)\/(\d+)\)/)

    const data: Record<string, any> = {}
    if (partMatch) data['零件数'] = partMatch[1]
    if (stepMatch) data['装配步骤'] = stepMatch[1]
    if (rateMatch) data['匹配率'] = rateMatch[1] + '%'
    if (matchedMatch) data['匹配情况'] = `${matchedMatch[1]}/${matchedMatch[2]}`
    data['详细信息'] = message
    processingStepsRef.value?.updateStep('matching', 'complete', data)
  }

  // 步骤5: 生成爆炸动画
  else if (msg.includes('生成glb爆炸动画')) {
    processingStepsRef.value?.updateStep('explosion', 'active')
  } else if (msg.includes('成功生成') && msg.includes('爆炸动画')) {
    const match = message.match(/(\d+)个零件/)
    const data = match ? {
      '零件数': match[1],
      '详细信息': message
    } : {}
    processingStepsRef.value?.updateStep('explosion', 'complete', data)
  }

  // 步骤6: 生成HTML说明书
  else if (msg.includes('生成html装配说明书')) {
    processingStepsRef.value?.updateStep('html', 'active')
  } else if (msg.includes('处理完成')) {
    processingStepsRef.value?.updateStep('html', 'complete', {
      '详细信息': message
    })
  }
}

// 处理阶段完成回调
const handleStageComplete = (stage: string) => {
  processingStepsRef.value?.addLog(`${stage}阶段处理完成`, 'success')
}

const previewResult = () => {
  if (generatedManualUrl.value) {
    window.open(generatedManualUrl.value, '_blank')
  } else {
    ElMessage.warning('说明书还未生成完成')
  }
  router.push('/viewer/demo')
}

const downloadResult = () => {
  ElMessage.info('下载功能开发中...')
}

const shareResult = () => {
  ElMessage.info('分享功能开发中...')
}

// Agent对话处理方法
const parseAndAddAgentDialog = (message: string, level: string) => {
  const agentDialog = parseAgentLog(message, level)
  if (agentDialog) {
    addAgentDialog(agentDialog)
  }
}

const parseAgentLog = (message: string, level: string) => {
  // 解析后端Agent日志格式
  const agentStartMatch = message.match(/👷 (.+?)AI员工加入工作，他开始(.+?)\.\.\./)
  if (agentStartMatch) {
    const agentName = mapAgentName(agentStartMatch[1])
    updateAgentStatus(agentName, 'working', `正在${agentStartMatch[2]}...`)

    return {
      id: generateDialogId(),
      agent: agentName,
      agentIcon: getAgentIcon(agentName),
      message: `我开始${agentStartMatch[2]}...`,
      timestamp: new Date().toLocaleTimeString(),
      type: 'working',
      status: 'typing'
    }
  }

  const agentSuccessMatch = message.match(/✅ (.+?)AI员工完成了工作，他(.+)/)
  if (agentSuccessMatch) {
    const agentName = mapAgentName(agentSuccessMatch[1])
    updateAgentStatus(agentName, 'completed', '任务完成')

    return {
      id: generateDialogId(),
      agent: agentName,
      agentIcon: getAgentIcon(agentName),
      message: `我已经完成了${agentSuccessMatch[2]}！`,
      timestamp: new Date().toLocaleTimeString(),
      type: 'reporting',
      status: 'complete'
    }
  }

  // 解析其他类型的Agent消息
  if (message.includes('Qwen-VL') || message.includes('视觉智能体')) {
    return {
      id: generateDialogId(),
      agent: 'Qwen-VL视觉智能体',
      agentIcon: '👁️',
      message: message,
      timestamp: new Date().toLocaleTimeString(),
      type: 'working',
      status: 'complete'
    }
  }

  if (message.includes('DeepSeek') || message.includes('推理智能体')) {
    return {
      id: generateDialogId(),
      agent: 'DeepSeek推理智能体',
      agentIcon: '🧠',
      message: message,
      timestamp: new Date().toLocaleTimeString(),
      type: 'thinking',
      status: 'complete'
    }
  }

  return null
}

const mapAgentName = (rawName: string) => {
  const nameMap = {
    '文件管理': '文件管理员',
    'Qwen-VL': 'Qwen-VL视觉智能体',
    'DeepSeek': 'DeepSeek推理智能体',
    'BOM提取': 'BOM提取专家',
    '装配专家': '装配工艺专家'
  }
  return nameMap[rawName] || rawName
}

const getAgentIcon = (agentName: string) => {
  const iconMap = {
    '文件管理员': '📁',
    'Qwen-VL视觉智能体': '👁️',
    'DeepSeek推理智能体': '🧠',
    'BOM提取专家': '📋',
    '装配工艺专家': '🔧'
  }
  return iconMap[agentName] || '🤖'
}

const generateDialogId = () => {
  return Date.now() + Math.random().toString(36).substr(2, 9)
}

const addAgentDialog = (dialog: any) => {
  agentDialogs.value.push(dialog)

  // 自动滚动到底部
  nextTick(() => {
    if (dialogContainer.value) {
      dialogContainer.value.scrollTop = dialogContainer.value.scrollHeight
    }
  })
}

// ✅ 旧的 updateAgentStatus 已删除，使用新版本（在 addLog 函数附近）

// 路由
const router = useRouter()

// 组件卸载时清理 SSE
onUnmounted(() => {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
})

// 刷新恢复：若存在未完成任务ID，则查询状态并重连
const restoreTaskFromCache = async () => {
  const cachedId = localStorage.getItem(RECOVERY_TASK_KEY)
  if (!cachedId) return

  try {
    const resp = await axios.get(`/api/status/${cachedId}`)
    const status = resp.data.status
    taskId.value = cachedId

    if (status === 'processing') {
      ElMessage.info('检测到未完成的生成任务，已自动恢复连接')
      connectEventSource(cachedId)
      isGenerating.value = true
      processingStatus.value = undefined
      processingText.value = '正在处理中...'
    } else if (status === 'completed') {
      ElMessage.success('上次任务已完成，可以到查看器查看')
      localStorage.removeItem(RECOVERY_TASK_KEY)
    } else if (status === 'failed') {
      ElMessage.warning('上次任务已失败，可重新上传生成')
      localStorage.removeItem(RECOVERY_TASK_KEY)
    }
  } catch (e) {
    // 无法恢复则清理缓存
    localStorage.removeItem(RECOVERY_TASK_KEY)
  }
}

onMounted(() => {
  restoreTaskFromCache()
})
</script>

<style lang="scss" scoped>
.generator-page {
  min-height: 100vh;
  padding: 40px 0;
  
  .container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 24px;
  }
}

// ✅ 上传指南样式已删除

.step-content {
  .step-panel {
    min-height: 500px;
  }
}

.upload-section {
  .upload-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 32px;
    margin-bottom: 40px;
    
    .upload-card {
      background: var(--el-bg-color);
      border-radius: 16px;
      padding: 24px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
      
      h3 {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 20px;
        color: var(--el-text-color-primary);
      }
      
      .upload-dragger {
        width: 100%;
        
        :deep(.el-upload-dragger) {
          width: 100%;
          height: 200px;
          border: 2px dashed var(--el-border-color);
          border-radius: 12px;
          background: var(--el-fill-color-lighter);
          transition: all 0.3s ease;
          
          &:hover {
            border-color: var(--el-color-primary);
            background: var(--el-color-primary-light-9);
          }
        }
        
        .upload-icon {
          font-size: 48px;
          color: var(--el-color-primary);
          margin-bottom: 16px;
        }
        
        .upload-text {
          p {
            margin: 8px 0;
            
            &.upload-hint {
              font-size: 12px;
              color: var(--el-text-color-secondary);
            }
          }
          
          em {
            color: var(--el-color-primary);
            font-style: normal;
          }
        }
      }
      
      .file-list {
        margin-top: 20px;
        
        h4 {
          margin-bottom: 12px;
          color: var(--el-text-color-primary);
        }
        
        .file-item {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 12px;
          background: var(--el-fill-color-light);
          border-radius: 8px;
          margin-bottom: 8px;
          
          .file-name {
            flex: 1;
            font-size: 14px;
          }
          
          .file-size {
            font-size: 12px;
            color: var(--el-text-color-secondary);
          }
        }
      }
    }
  }
  
  .config-section {
    background: var(--el-bg-color);
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 40px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);

    h3 {
      margin-bottom: 20px;
      color: var(--el-text-color-primary);
    }

    .config-item {
      label {
        display: block;
        margin-bottom: 12px;
        font-weight: 500;
        color: var(--el-text-color-primary);
        font-size: 16px;
      }
    }
  }
  
  .step-actions {
    text-align: center;
  }
}

.processing-section {
  display: flex;
  align-items: center;
  gap: 60px;
  
  .processing-visual {
    flex-shrink: 0;
    
    .processing-animation {
      width: 300px;
      height: 300px;
      background: radial-gradient(circle, rgba(64, 158, 255, 0.1), transparent);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
    }
  }
  
  .processing-info {
    flex: 1;
    
    h3 {
      font-size: 1.8rem;
      margin-bottom: 16px;
      color: var(--el-text-color-primary);
    }
    
    p {
      font-size: 1.1rem;
      color: var(--el-text-color-secondary);
      line-height: 1.6;
      margin-bottom: 32px;
    }
    
    .progress-section {
      margin-bottom: 32px;
      
      .progress-text {
        margin-top: 12px;
        text-align: center;
        color: var(--el-text-color-secondary);
      }
    }
    
    .log-section {
      h4 {
        margin-bottom: 12px;
        color: var(--el-text-color-primary);
      }
      
      .log-container {
        max-height: 200px;
        overflow-y: auto;
        background: var(--el-fill-color-darker);
        border-radius: 8px;
        padding: 12px;
        
        .log-item {
          display: flex;
          gap: 12px;
          margin-bottom: 8px;
          font-family: monospace;
          font-size: 12px;
          
          .log-time {
            color: var(--el-text-color-secondary);
            flex-shrink: 0;
          }
          
          .log-message {
            flex: 1;
          }
          
          &.info { color: var(--el-color-info); }
          &.success { color: var(--el-color-success); }
          &.warning { color: var(--el-color-warning); }
          &.error { color: var(--el-color-danger); }
        }
      }
    }
  }
}

.result-section {
  text-align: center;
  
  .result-header {
    margin-bottom: 40px;
    
    .success-icon {
      color: var(--el-color-success);
      margin-bottom: 20px;
    }
    
    h2 {
      font-size: 2rem;
      margin-bottom: 16px;
      color: var(--el-text-color-primary);
    }
    
    p {
      font-size: 1.1rem;
      color: var(--el-text-color-secondary);
    }
  }
  
  .result-actions {
    display: flex;
    justify-content: center;
    gap: 16px;
    margin-bottom: 60px;
  }
  
  .result-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 32px;
    
    .stat-item {
      .stat-number {
        font-size: 2.5rem;
        font-weight: 700;
        color: var(--el-color-primary);
        margin-bottom: 8px;
      }
      
      .stat-label {
        color: var(--el-text-color-secondary);
      }
    }
  }
}

// 文件验证样式
.validation-section {
  background: var(--el-bg-color);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 40px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);

  h3 {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 16px;
    color: var(--el-color-warning);
  }

  .validation-tips {
    ul {
      margin: 8px 0;
      padding-left: 20px;

      li {
        margin: 4px 0;
        color: var(--el-text-color-regular);
      }
    }
  }

  .validation-success {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px;
    background: var(--el-color-success-light-9);
    border: 1px solid var(--el-color-success-light-7);
    border-radius: 8px;
    color: var(--el-color-success);
    margin-top: 16px;
  }

  .validation-errors {
    padding: 12px;
    background: var(--el-color-danger-light-9);
    border: 1px solid var(--el-color-danger-light-7);
    border-radius: 8px;
    color: var(--el-color-danger);
    margin-top: 16px;

    ul {
      margin: 8px 0 0 0;
      padding-left: 20px;
    }
  }
}

// Agent协作样式
.agent-collaboration-section {
  background: var(--el-bg-color);
  border-radius: 16px;
  padding: 32px;
  margin-bottom: 32px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);

  h3 {
    font-size: 1.5rem;
    margin-bottom: 8px;
    background: linear-gradient(135deg, #409eff, #67c23a);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  > p {
    color: var(--el-text-color-secondary);
    margin-bottom: 32px;
  }
}

.agent-status-panel {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  margin-bottom: 32px;

  .agent-card {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
    padding: 24px;
    background: var(--el-fill-color-lighter);
    border: 2px solid var(--el-border-color-light);
    border-radius: 16px;
    transition: all 0.3s ease;
    min-height: 140px;

    &.active {
      border-color: var(--el-color-primary);
      background: var(--el-color-primary-light-9);
      box-shadow: 0 0 20px rgba(64, 158, 255, 0.3);
    }

    &.completed {
      border-color: var(--el-color-success);
      background: var(--el-color-success-light-9);
    }

    .agent-avatar {
      position: relative;
      align-self: center;

      .avatar-icon {
        width: 64px;
        height: 64px;
        border-radius: 50%;
        background: var(--el-color-primary-light-8);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 32px;
      }

      .status-indicator {
        position: absolute;
        bottom: 2px;
        right: 2px;
        width: 16px;
        height: 16px;
        border-radius: 50%;
        border: 3px solid var(--el-bg-color);

        &.idle { background: var(--el-color-info); }
        &.working {
          background: var(--el-color-primary);
          animation: pulse 2s infinite;
        }
        &.completed { background: var(--el-color-success); }
      }
    }

    .agent-info {
      flex: 1;
      width: 100%;

      h4 {
        margin: 0 0 8px 0;
        font-size: 16px;
        font-weight: 600;
        color: var(--el-text-color-primary);
      }

      p {
        margin: 0;
        font-size: 13px;
        color: var(--el-text-color-secondary);
        line-height: 1.5;
      }
    }
  }
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.2); opacity: 0.7; }
}

// ✅ 全屏日志显示样式
.fullscreen-logs-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 300px);
  min-height: 600px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-light);
  border-radius: 12px;
  overflow: hidden;

  .logs-header-large {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px 32px;
    background: linear-gradient(135deg, var(--el-color-primary-light-9), var(--el-fill-color-light));
    border-bottom: 2px solid var(--el-border-color-light);

    h2 {
      margin: 0;
      font-size: 24px;
      font-weight: 600;
      color: var(--el-text-color-primary);
    }

    .header-actions {
      display: flex;
      gap: 12px;
    }
  }

  .logs-content-large {
    flex: 1;
    overflow-y: auto;
    padding: 24px 32px;
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    background: #1e1e1e;
    color: #d4d4d4;

    .log-item-large {
      padding: 12px 16px;
      margin-bottom: 8px;
      border-radius: 8px;
      display: flex;
      gap: 16px;
      transition: all 0.2s;
      font-size: 16px;
      line-height: 1.6;
      background: rgba(255, 255, 255, 0.03);

      &:hover {
        background: rgba(255, 255, 255, 0.08);
        transform: translateX(4px);
      }

      .log-time-large {
        color: #858585;
        flex-shrink: 0;
        width: 100px;
        font-size: 14px;
        font-weight: 500;
      }

      .log-message-large {
        flex: 1;
        color: #d4d4d4;
        word-break: break-word;
      }

      &.info {
        border-left: 4px solid #3b82f6;
        .log-message-large { color: #60a5fa; }
      }

      &.success {
        border-left: 4px solid #10b981;
        .log-message-large { color: #34d399; font-weight: 500; }
      }

      &.warning {
        border-left: 4px solid #f59e0b;
        .log-message-large { color: #fbbf24; }
      }

      &.error {
        border-left: 4px solid #ef4444;
        background: rgba(239, 68, 68, 0.1);
        .log-message-large { color: #f87171; font-weight: 600; }
      }
    }

    .empty-logs-large {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100%;
      gap: 16px;
      color: #6b7280;

      .el-icon {
        color: #4b5563;
      }

      p {
        font-size: 18px;
        margin: 0;
      }
    }

    // 滚动条样式
    &::-webkit-scrollbar {
      width: 12px;
    }

    &::-webkit-scrollbar-track {
      background: #2d2d2d;
      border-radius: 6px;
    }

    &::-webkit-scrollbar-thumb {
      background: #4b5563;
      border-radius: 6px;

      &:hover {
        background: #6b7280;
      }
    }
  }

  .completion-actions-large {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 24px;
    padding: 24px 32px;
    background: linear-gradient(135deg, var(--el-color-success-light-9), var(--el-fill-color-light));
    border-top: 2px solid var(--el-color-success-light-5);

    .el-button {
      min-width: 220px;
      font-size: 18px;
      padding: 18px 36px;
      font-weight: 600;
    }
  }
}

@keyframes glow {
  0%, 100% {
    box-shadow: 0 0 20px rgba(64, 158, 255, 0.3);
  }
  50% {
    box-shadow: 0 0 40px rgba(64, 158, 255, 0.6);
  }
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.dialog-stream {
  .dialog-header {
    display: flex;
    justify-content: between;
    align-items: center;
    margin-bottom: 16px;

    h4 {
      margin: 0;
      color: var(--el-text-color-primary);
    }
  }

  .dialog-container {
    max-height: 400px;
    overflow-y: auto;
    padding: 16px;
    background: var(--el-fill-color-darker);
    border-radius: 12px;

    .dialog-message {
      margin-bottom: 16px;
      padding: 12px 16px;
      border-radius: 12px;
      background: var(--el-bg-color);
      border-left: 4px solid var(--el-color-primary);

      &.qwenvl {
        border-left-color: #ff6b6b;
        background: linear-gradient(135deg, rgba(255, 107, 107, 0.1), transparent);
      }

      &.deepseek {
        border-left-color: #4ecdc4;
        background: linear-gradient(135deg, rgba(78, 205, 196, 0.1), transparent);
      }

      &.filemanager {
        border-left-color: #45b7d1;
        background: linear-gradient(135deg, rgba(69, 183, 209, 0.1), transparent);
      }

      &.typing {
        animation: typing-glow 2s infinite;
      }

      .message-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;

        .agent-name {
          font-weight: 600;
          color: var(--el-color-primary);
        }

        .timestamp {
          font-size: 12px;
          color: var(--el-text-color-secondary);
        }
      }

      .message-content {
        color: var(--el-text-color-primary);
        line-height: 1.5;

        .agent-highlight {
          color: var(--el-color-primary);
          font-weight: 600;
        }

        .number-highlight {
          color: var(--el-color-success);
          font-weight: 600;
        }

        .percentage-highlight {
          color: var(--el-color-warning);
          font-weight: 600;
        }

        .typing-text {
          color: var(--el-text-color-secondary);
        }

        .typing-cursor {
          color: var(--el-color-primary);
          animation: blink 1s infinite;
        }
      }

      .message-progress {
        margin-top: 8px;
      }
    }
  }
}

@keyframes typing-glow {
  0%, 100% { box-shadow: 0 0 5px rgba(64, 158, 255, 0.3); }
  50% { box-shadow: 0 0 20px rgba(64, 158, 255, 0.6); }
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

// 响应式设计
@media (max-width: 1024px) {
  .generator-page {
    padding: 24px 0;
  }

  .container {
    padding: 0 16px;
  }

  .fullscreen-logs-container {
    height: 70vh;
    min-height: 420px;
  }

  .result-actions {
    flex-wrap: wrap;
    gap: 12px;
  }
}

@media (max-width: 768px) {
  .upload-grid {
    grid-template-columns: 1fr !important;
  }

  .processing-section {
    flex-direction: column;
    gap: 40px;
    text-align: center;
  }

  .result-actions {
    flex-direction: column;
    align-items: center;
  }

  .agent-status-panel {
    grid-template-columns: 1fr;
  }

  .dialog-container {
    max-height: 300px;
  }
}

.conflict-list {
  padding-left: 18px;
  margin: 8px 0 0;
  color: var(--el-text-color-primary);
  line-height: 1.6;
}

.conflict-list li + li {
  margin-top: 4px;
}

.conflict-footer {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  flex-wrap: nowrap;
}

.conflict-footer .el-button {
  white-space: nowrap;
}
</style>
