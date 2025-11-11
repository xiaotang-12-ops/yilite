<template>
  <div class="ai-processing-section">
    <div class="processing-header">
      <h3>AI智能解析</h3>
      <p>正在使用双通道架构解析您的工程图纸</p>
    </div>

    <!-- 处理状态卡片 -->
    <div class="status-cards">
      <!-- 文本通道 -->
      <div class="status-card" :class="{ active: currentStage >= 1, completed: currentStage > 1 }">
        <div class="card-icon">
          <el-icon v-if="currentStage > 1" class="success-icon"><check /></el-icon>
          <el-icon v-else-if="currentStage === 1" class="loading-icon"><loading /></el-icon>
          <el-icon v-else class="pending-icon"><document /></el-icon>
        </div>
        <div class="card-content">
          <h4>文本通道解析</h4>
          <p>提取BOM表、技术要求、尺寸标注</p>
          <div v-if="textChannelResult" class="result-summary">
            <span>BOM项目: {{ textChannelResult.bomCount }}</span>
            <span>技术要求: {{ textChannelResult.techReqCount }}</span>
          </div>
        </div>
      </div>

      <!-- 视觉通道 -->
      <div class="status-card" :class="{ active: currentStage >= 2, completed: currentStage > 2 }">
        <div class="card-icon">
          <el-icon v-if="currentStage > 2" class="success-icon"><check /></el-icon>
          <el-icon v-else-if="currentStage === 2" class="loading-icon"><loading /></el-icon>
          <el-icon v-else class="pending-icon"><view /></el-icon>
        </div>
        <div class="card-content">
          <h4>视觉通道解析</h4>
          <p>识别图形、符号、尺寸、装配关系</p>
          <div v-if="visionChannelResult" class="result-summary">
            <span>视觉元素: {{ visionChannelResult.elementCount }}</span>
            <span>尺寸信息: {{ visionChannelResult.dimensionCount }}</span>
          </div>
        </div>
      </div>

      <!-- 融合推理 -->
      <div class="status-card" :class="{ active: currentStage >= 3, completed: currentStage > 3 }">
        <div class="card-icon">
          <el-icon v-if="currentStage > 3" class="success-icon"><check /></el-icon>
          <el-icon v-else-if="currentStage === 3" class="loading-icon"><loading /></el-icon>
          <el-icon v-else class="pending-icon"><operation /></el-icon>
        </div>
        <div class="card-content">
          <h4>DeepSeek融合推理</h4>
          <p>智能融合双通道数据，生成装配规范</p>
          <div v-if="fusionResult" class="result-summary">
            <span>装配步骤: {{ fusionResult.stepCount }}</span>
            <span>质检要点: {{ fusionResult.qcCount }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 详细进度 -->
    <div class="detailed-progress">
      <h4>处理详情</h4>
      <div class="progress-timeline">
        <div 
          v-for="(log, index) in processLogs" 
          :key="index"
          class="timeline-item"
          :class="{ active: log.status === 'processing', completed: log.status === 'completed', error: log.status === 'error' }"
        >
          <div class="timeline-dot"></div>
          <div class="timeline-content">
            <div class="timeline-time">{{ log.timestamp }}</div>
            <div class="timeline-title">{{ log.title }}</div>
            <div class="timeline-desc">{{ log.description }}</div>
            <div v-if="log.progress" class="timeline-progress">
              <el-progress 
                :percentage="log.progress" 
                :status="log.status === 'error' ? 'exception' : ''"
                :stroke-width="6"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 错误信息 -->
    <div v-if="errorMessage" class="error-section">
      <el-alert
        :title="errorMessage"
        type="error"
        :closable="false"
        show-icon
      />
      <div class="error-actions">
        <el-button type="primary" @click="retryProcessing">重试</el-button>
        <el-button @click="skipToManualReview">跳过到人工复核</el-button>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="processing-actions">
      <el-button 
        v-if="currentStage === 0"
        type="primary" 
        size="large"
        @click="startProcessing"
        :disabled="!taskId"
      >
        开始AI解析
      </el-button>
      
      <el-button 
        v-if="currentStage > 0 && currentStage < 4"
        size="large"
        @click="cancelProcessing"
        :disabled="cancelling"
      >
        {{ cancelling ? '取消中...' : '取消处理' }}
      </el-button>
      
      <el-button 
        v-if="currentStage === 4"
        type="success" 
        size="large"
        @click="proceedToReview"
      >
        进入人工复核
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, defineProps, defineEmits } from 'vue'
import { ElMessage } from 'element-plus'
import { Check, Loading, Document, View, Operation } from '@element-plus/icons-vue'

// Props
const props = defineProps({
  taskId: {
    type: String,
    required: true
  }
})

// 事件定义
const emit = defineEmits(['processing-complete', 'processing-error'])

// 响应式数据
const currentStage = ref(0) // 0: 未开始, 1: 文本通道, 2: 视觉通道, 3: 融合推理, 4: 完成
const textChannelResult = ref(null)
const visionChannelResult = ref(null)
const fusionResult = ref(null)
const errorMessage = ref('')
const cancelling = ref(false)
const processLogs = ref([])
const pollingTimer = ref(null)

// 方法
const startProcessing = async () => {
  try {
    currentStage.value = 1
    addLog('开始AI解析', '启动双通道解析流程', 'processing')
    
    // 调用后端API开始处理
    const response = await fetch(`/api/tasks/${props.taskId}/process`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })
    
    if (!response.ok) {
      throw new Error('启动AI解析失败')
    }
    
    // 开始轮询状态
    startPolling()
    
  } catch (error) {
    errorMessage.value = error.message
    addLog('启动失败', error.message, 'error')
  }
}

const startPolling = () => {
  pollingTimer.value = setInterval(async () => {
    try {
      const response = await fetch(`/api/tasks/${props.taskId}/status`)
      const data = await response.json()
      
      updateProcessingStatus(data)
      
    } catch (error) {
      console.error('轮询状态失败:', error)
    }
  }, 2000) // 每2秒轮询一次
}

const updateProcessingStatus = (data) => {
  const { stage, status, progress, result, error } = data
  
  if (error) {
    errorMessage.value = error
    addLog('处理错误', error, 'error')
    stopPolling()
    return
  }
  
  // 更新当前阶段
  if (stage === 'text_channel') {
    currentStage.value = 1
    if (status === 'completed') {
      textChannelResult.value = result
      addLog('文本通道完成', `提取到 ${result.bomCount} 个BOM项目`, 'completed')
      currentStage.value = 2
    } else {
      addLog('文本通道处理中', '正在解析PDF文档...', 'processing', progress)
    }
  } else if (stage === 'vision_channel') {
    currentStage.value = 2
    if (status === 'completed') {
      visionChannelResult.value = result
      addLog('视觉通道完成', `识别到 ${result.elementCount} 个视觉元素`, 'completed')
      currentStage.value = 3
    } else {
      addLog('视觉通道处理中', '正在分析工程图纸...', 'processing', progress)
    }
  } else if (stage === 'fusion') {
    currentStage.value = 3
    if (status === 'completed') {
      fusionResult.value = result
      addLog('融合推理完成', `生成 ${result.stepCount} 个装配步骤`, 'completed')
      currentStage.value = 4
      stopPolling()
      
      // 发送完成事件
      emit('processing-complete', {
        textChannel: textChannelResult.value,
        visionChannel: visionChannelResult.value,
        fusion: fusionResult.value
      })
    } else {
      addLog('融合推理中', '正在智能分析和整合数据...', 'processing', progress)
    }
  }
}

const addLog = (title, description, status, progress = null) => {
  const timestamp = new Date().toLocaleTimeString()
  processLogs.value.push({
    timestamp,
    title,
    description,
    status,
    progress
  })
}

const stopPolling = () => {
  if (pollingTimer.value) {
    clearInterval(pollingTimer.value)
    pollingTimer.value = null
  }
}

const cancelProcessing = async () => {
  try {
    cancelling.value = true
    
    const response = await fetch(`/api/tasks/${props.taskId}/cancel`, {
      method: 'POST'
    })
    
    if (response.ok) {
      stopPolling()
      currentStage.value = 0
      addLog('处理已取消', '用户主动取消了AI解析', 'error')
      ElMessage.info('AI解析已取消')
    }
    
  } catch (error) {
    ElMessage.error('取消失败: ' + error.message)
  } finally {
    cancelling.value = false
  }
}

const retryProcessing = () => {
  errorMessage.value = ''
  processLogs.value = []
  currentStage.value = 0
  startProcessing()
}

const skipToManualReview = () => {
  emit('processing-error', { 
    message: '跳过AI解析，进入人工复核模式',
    skipToManual: true 
  })
}

const proceedToReview = () => {
  emit('processing-complete', {
    textChannel: textChannelResult.value,
    visionChannel: visionChannelResult.value,
    fusion: fusionResult.value
  })
}

// 生命周期
onMounted(() => {
  // 如果有taskId，检查是否已经在处理中
  if (props.taskId) {
    // 可以在这里检查任务状态
  }
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.ai-processing-section {
  padding: 20px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.processing-header {
  text-align: center;
  margin-bottom: 30px;
}

.processing-header h3 {
  color: #303133;
  margin-bottom: 8px;
}

.processing-header p {
  color: #909399;
  margin: 0;
}

.status-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.status-card {
  display: flex;
  align-items: center;
  padding: 20px;
  border: 2px solid #e4e7ed;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.status-card.active {
  border-color: #409eff;
  background: #f0f9ff;
}

.status-card.completed {
  border-color: #67c23a;
  background: #f0f9ff;
}

.card-icon {
  margin-right: 15px;
  font-size: 24px;
}

.success-icon {
  color: #67c23a;
}

.loading-icon {
  color: #409eff;
  animation: spin 1s linear infinite;
}

.pending-icon {
  color: #c0c4cc;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.card-content h4 {
  margin: 0 0 5px 0;
  color: #303133;
}

.card-content p {
  margin: 0 0 10px 0;
  color: #606266;
  font-size: 14px;
}

.result-summary {
  display: flex;
  gap: 15px;
}

.result-summary span {
  font-size: 12px;
  color: #909399;
  background: #f5f7fa;
  padding: 2px 8px;
  border-radius: 4px;
}

.detailed-progress {
  margin-bottom: 30px;
}

.detailed-progress h4 {
  margin-bottom: 15px;
  color: #606266;
}

.progress-timeline {
  position: relative;
  padding-left: 30px;
}

.progress-timeline::before {
  content: '';
  position: absolute;
  left: 10px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #e4e7ed;
}

.timeline-item {
  position: relative;
  margin-bottom: 20px;
}

.timeline-dot {
  position: absolute;
  left: -25px;
  top: 5px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #c0c4cc;
  border: 2px solid #fff;
}

.timeline-item.active .timeline-dot {
  background: #409eff;
}

.timeline-item.completed .timeline-dot {
  background: #67c23a;
}

.timeline-item.error .timeline-dot {
  background: #f56c6c;
}

.timeline-content {
  padding-left: 10px;
}

.timeline-time {
  font-size: 12px;
  color: #c0c4cc;
  margin-bottom: 2px;
}

.timeline-title {
  font-weight: 500;
  color: #303133;
  margin-bottom: 2px;
}

.timeline-desc {
  font-size: 14px;
  color: #606266;
  margin-bottom: 8px;
}

.timeline-progress {
  width: 200px;
}

.error-section {
  margin-bottom: 20px;
}

.error-actions {
  margin-top: 15px;
  text-align: center;
}

.error-actions .el-button {
  margin: 0 10px;
}

.processing-actions {
  text-align: center;
}

.processing-actions .el-button {
  margin: 0 10px;
}
</style>
