<template>
  <div class="processing-steps">
    <!-- 总体进度 -->
    <div class="overall-progress">
      <div class="progress-header">
        <h3>🤖 智能装配说明书生成中...</h3>
        <div class="progress-percentage">{{ overallProgress }}%</div>
      </div>
      <el-progress 
        :percentage="overallProgress" 
        :status="progressStatus"
        :stroke-width="24"
        :show-text="false"
      />
      <div class="progress-text">{{ currentMessage }}</div>
    </div>

    <!-- 步骤列表 -->
    <div class="steps-container">
      <el-timeline>
        <el-timeline-item
          v-for="(step, index) in steps"
          :key="index"
          :type="getStepType(step)"
          :icon="getStepIcon(step)"
          :color="getStepColor(step)"
          :size="step.status === 'active' ? 'large' : 'normal'"
        >
          <div class="step-content">
            <div class="step-header">
              <span class="step-title">{{ step.title }}</span>
              <el-tag v-if="step.status === 'complete'" type="success" size="small">完成</el-tag>
              <el-tag v-else-if="step.status === 'active'" type="primary" size="small">进行中</el-tag>
              <el-tag v-else type="info" size="small">等待中</el-tag>
            </div>
            
            <!-- 关键数据 -->
            <div class="step-data" v-if="step.data && step.status !== 'pending'">
              <div v-for="(value, key) in step.data" :key="key" class="data-item">
                <el-icon><DataLine /></el-icon>
                <span>{{ key }}: <strong>{{ value }}</strong></span>
              </div>
            </div>
            
            <!-- 子步骤 -->
            <div class="sub-steps" v-if="step.subSteps && step.subSteps.length > 0">
              <div v-for="(subStep, subIndex) in step.subSteps" :key="subIndex" class="sub-step">
                <el-icon v-if="subStep.status === 'complete'"><CircleCheck /></el-icon>
                <el-icon v-else-if="subStep.status === 'active'" class="rotating"><Loading /></el-icon>
                <el-icon v-else><Clock /></el-icon>
                <span>{{ subStep.title }}</span>
                <span v-if="subStep.data" class="sub-step-data">{{ subStep.data }}</span>
              </div>
            </div>
          </div>
        </el-timeline-item>
      </el-timeline>
    </div>

    <!-- 实时日志 -->
    <div class="logs-container">
      <div class="logs-header">
        <h4>📋 实时日志</h4>
        <el-button size="small" @click="clearLogs">清空</el-button>
      </div>
      <div class="logs-content" ref="logsContent">
        <div
          v-for="(log, index) in logs"
          :key="index"
          :class="['log-item', `log-${log.level}`]"
        >
          <span class="log-time">{{ formatTime(log.timestamp) }}</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { CircleCheck, Loading, Clock, DataLine, SuccessFilled, WarnTriangleFilled } from '@element-plus/icons-vue'

interface SubStep {
  title: string
  status: 'pending' | 'active' | 'complete'
  data?: string
}

interface Step {
  id: string
  title: string
  status: 'pending' | 'active' | 'complete' | 'error'
  data?: Record<string, any>
  subSteps?: SubStep[]
}

interface Log {
  timestamp: number
  level: 'info' | 'success' | 'warning' | 'error'
  message: string
}

const props = defineProps<{
  progress: number
  message: string
  stage: string
}>()

const steps = ref<Step[]>([
  {
    id: 'pdf_text',
    title: '步骤1: PDF文本提取 - pypdf解析BOM',
    status: 'pending',
    data: {},
    subSteps: []
  },
  {
    id: 'step_glb',
    title: '步骤2: STEP→GLB转换 - 解析零件',
    status: 'pending',
    data: {},
    subSteps: []
  },
  {
    id: 'vision',
    title: '步骤3: Qwen-VL视觉分析 - 结合BOM上下文',
    status: 'pending',
    data: {},
    subSteps: []
  },
  {
    id: 'matching',
    title: '步骤4: DeepSeek智能匹配 - BOM↔GLB零件对应',
    status: 'pending',
    data: {},
    subSteps: []
  },
  {
    id: 'explosion',
    title: '步骤5: 生成爆炸动画数据',
    status: 'pending',
    data: {},
    subSteps: []
  },
  {
    id: 'html',
    title: '步骤6: 生成HTML装配说明书',
    status: 'pending',
    data: {},
    subSteps: []
  }
])

const logs = ref<Log[]>([])
const logsContent = ref<HTMLElement>()

const overallProgress = computed(() => props.progress)
const currentMessage = computed(() => props.message)
const progressStatus = computed(() => {
  if (overallProgress.value === 100) return 'success'
  if (overallProgress.value > 0) return undefined
  return undefined
})

// 添加日志
const addLog = (message: string, level: 'info' | 'success' | 'warning' | 'error' = 'info') => {
  logs.value.push({
    timestamp: Date.now(),
    level,
    message
  })
  
  // 自动滚动到底部
  nextTick(() => {
    if (logsContent.value) {
      logsContent.value.scrollTop = logsContent.value.scrollHeight
    }
  })
}

// 更新步骤状态
const updateStep = (stepId: string, status: Step['status'], data?: Record<string, any>) => {
  const step = steps.value.find(s => s.id === stepId)
  if (step) {
    step.status = status
    if (data) {
      step.data = { ...step.data, ...data }
    }
  }
}

// 清空日志
const clearLogs = () => {
  logs.value = []
}

// 格式化时间
const formatTime = (timestamp: number) => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour12: false })
}

// 获取步骤类型
const getStepType = (step: Step) => {
  if (step.status === 'complete') return 'success'
  if (step.status === 'error') return 'danger'
  if (step.status === 'active') return 'primary'
  return 'info'
}

// 获取步骤图标
const getStepIcon = (step: Step) => {
  if (step.status === 'complete') return SuccessFilled
  if (step.status === 'error') return WarnTriangleFilled
  if (step.status === 'active') return Loading
  return Clock
}

// 获取步骤颜色
const getStepColor = (step: Step) => {
  if (step.status === 'complete') return '#67c23a'
  if (step.status === 'error') return '#f56c6c'
  if (step.status === 'active') return '#409eff'
  return '#909399'
}

// 监听阶段变化
watch(() => props.stage, (newStage) => {
  // 根据阶段更新步骤状态
  // 这里需要根据实际的阶段名称来映射
})

// 暴露方法给父组件
defineExpose({
  addLog,
  updateStep
})
</script>

<style scoped lang="scss">
.processing-steps {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
}

.overall-progress {
  background: white;
  padding: 24px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);

  .progress-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;

    h3 {
      margin: 0;
      font-size: 18px;
      color: #303133;
    }

    .progress-percentage {
      font-size: 24px;
      font-weight: bold;
      color: #409eff;
    }
  }

  .progress-text {
    margin-top: 12px;
    color: #606266;
    font-size: 14px;
  }
}

.steps-container {
  background: white;
  padding: 24px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.step-content {
  .step-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;

    .step-title {
      font-size: 16px;
      font-weight: 600;
      color: #303133;
    }
  }

  .step-data {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-top: 12px;
    padding: 12px;
    background: #f5f7fa;
    border-radius: 4px;

    .data-item {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 14px;
      color: #606266;

      strong {
        color: #409eff;
        font-weight: 600;
      }
    }
  }

  .sub-steps {
    margin-top: 12px;
    padding-left: 24px;

    .sub-step {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 0;
      font-size: 14px;
      color: #606266;

      .sub-step-data {
        margin-left: auto;
        color: #409eff;
        font-weight: 600;
      }
    }
  }
}

.logs-container {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  overflow: hidden;

  .logs-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 24px;
    border-bottom: 1px solid #ebeef5;

    h4 {
      margin: 0;
      font-size: 16px;
      color: #303133;
    }
  }

  .logs-content {
    max-height: 300px;
    overflow-y: auto;
    padding: 16px 24px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 13px;

    .log-item {
      display: flex;
      gap: 12px;
      padding: 6px 0;
      border-bottom: 1px solid #f5f7fa;

      &:last-child {
        border-bottom: none;
      }

      .log-time {
        color: #909399;
        flex-shrink: 0;
      }

      .log-message {
        flex: 1;
      }

      &.log-info {
        color: #606266;
      }

      &.log-success {
        color: #67c23a;
      }

      &.log-warning {
        color: #e6a23c;
      }

      &.log-error {
        color: #f56c6c;
      }
    }
  }
}

.rotating {
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>

