<template>
  <div class="processing-visualization-new">
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
      <div class="progress-text">{{ progressText }}</div>
    </div>

    <!-- 阶段卡片 -->
    <div class="stages-container">
      <!-- 阶段1: PDF解析 - 提取BOM表 -->
      <div class="stage-card" :class="getStageClass('pdf_bom')">
        <div class="stage-header">
          <div class="stage-icon">
            <el-icon v-if="isStageComplete('pdf_bom')"><CircleCheck /></el-icon>
            <el-icon v-else-if="isStageActive('pdf_bom')" class="rotating"><Loading /></el-icon>
            <el-icon v-else><Clock /></el-icon>
          </div>
          <div class="stage-title">
            <h4>阶段1: PDF解析 - 提取BOM表</h4>
            <p>这是所有后续步骤的基础</p>
          </div>
        </div>
        <div class="stage-content" v-if="stageData.pdf_bom">
          <div class="stage-item" v-if="stageData.pdf_bom.text_extraction">
            <el-icon><Reading /></el-icon>
            <span>文本提取: {{ stageData.pdf_bom.text_extraction.bom_candidates || 0 }}个BOM项</span>
          </div>
          <div class="stage-item" v-if="stageData.pdf_bom.vision_analysis">
            <el-icon><View /></el-icon>
            <span class="agent-highlight">🤖 Qwen-VL视觉智能体: {{ stageData.pdf_bom.vision_analysis.assembly_relations || 0 }}个装配关系</span>
          </div>
          <div class="stage-item" v-if="stageData.pdf_bom.bom_generation">
            <el-icon><List /></el-icon>
            <span>BOM生成: {{ stageData.pdf_bom.bom_generation.total_items || 0 }}项零件清单</span>
          </div>
        </div>
      </div>

      <!-- 阶段2: 并行处理 -->
      <div class="stage-card" :class="getStageClass('parallel')">
        <div class="stage-header">
          <div class="stage-icon">
            <el-icon v-if="isStageComplete('parallel')"><CircleCheck /></el-icon>
            <el-icon v-else-if="isStageActive('parallel')" class="rotating"><Loading /></el-icon>
            <el-icon v-else><Clock /></el-icon>
          </div>
          <div class="stage-title">
            <h4>阶段2: 并行处理 - 基于BOM数据</h4>
            <p>PDF深度分析和STEP零件提取同时进行</p>
          </div>
        </div>
        <div class="stage-content" v-if="stageData.pdf_deep || stageData.step_extract">
          <div class="stage-item" v-if="stageData.pdf_deep">
            <el-icon><Document /></el-icon>
            <span class="agent-highlight">🤖 Qwen-VL装配智能体: {{ stageData.pdf_deep.assembly_steps || 0 }}个装配步骤</span>
          </div>
          <div class="stage-item" v-if="stageData.step_extract">
            <el-icon><Box /></el-icon>
            <span>STEP零件提取: {{ stageData.step_extract.unique_parts || 0 }}个唯一零件，{{ stageData.step_extract.total_instances || 0 }}个实例</span>
          </div>
        </div>
      </div>

      <!-- 阶段3: BOM-STEP智能匹配 -->
      <div class="stage-card" :class="getStageClass('matching')">
        <div class="stage-header">
          <div class="stage-icon">
            <el-icon v-if="isStageComplete('matching')"><CircleCheck /></el-icon>
            <el-icon v-else-if="isStageActive('matching')" class="rotating"><Loading /></el-icon>
            <el-icon v-else><Clock /></el-icon>
          </div>
          <div class="stage-title">
            <h4>阶段3: BOM-STEP智能匹配</h4>
            <p>建立3D模型与BOM表的精准对应关系</p>
          </div>
        </div>
        <div class="stage-content" v-if="stageData.matching">
          <div class="stage-item" v-if="stageData.matching.rule_matching">
            <el-icon><Operation /></el-icon>
            <span>规则匹配: {{ stageData.matching.rule_matching.matched || 0 }}/{{ stageData.matching.rule_matching.total_bom || 0 }} ({{ stageData.matching.rule_matching.match_rate || 0 }}%)</span>
          </div>
          <div class="stage-item" v-if="stageData.matching.ai_matching">
            <el-icon><MagicStick /></el-icon>
            <span class="agent-highlight">🤖 DeepSeek推理智能体: 新增{{ stageData.matching.ai_matching.new_matches || 0 }}个匹配，拆解{{ stageData.matching.ai_matching.components || 0 }}个组件</span>
          </div>
          <div class="stage-item" v-if="stageData.matching.mapping">
            <el-icon><Finished /></el-icon>
            <span class="final-result">最终匹配率: {{ stageData.matching.mapping.final_match_rate || 0 }}%</span>
          </div>
        </div>
      </div>

      <!-- 阶段4: 生成装配说明书 -->
      <div class="stage-card" :class="getStageClass('generate')">
        <div class="stage-header">
          <div class="stage-icon">
            <el-icon v-if="isStageComplete('generate')"><CircleCheck /></el-icon>
            <el-icon v-else-if="isStageActive('generate')" class="rotating"><Loading /></el-icon>
            <el-icon v-else><Clock /></el-icon>
          </div>
          <div class="stage-title">
            <h4>阶段4: 生成装配说明书</h4>
            <p>生成交互式HTML装配说明书</p>
          </div>
        </div>
        <div class="stage-content" v-if="stageData.generate">
          <div class="stage-item">
            <el-icon><Setting /></el-icon>
            <span class="agent-highlight">🤖 DeepSeek装配专家: 生成装配规程和3D动画</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 实时日志 -->
    <div class="processing-logs">
      <div class="logs-header">
        <el-icon><Document /></el-icon>
        <span>实时日志</span>
        <el-tag v-if="logs.length > 0" size="small" type="info">{{ logs.length }} 条</el-tag>
      </div>
      <div class="logs-content" ref="logsContent">
        <div 
          v-for="(log, index) in logs" 
          :key="index" 
          :class="['log-item', log.level]"
        >
          <span class="log-time">{{ log.time }}</span>
          <span class="log-message" v-html="formatLogMessage(log.message)"></span>
        </div>
        <div v-if="logs.length === 0" class="logs-empty">
          <el-icon><Document /></el-icon>
          <span>等待处理日志...</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import {
  Document, List, Upload, Setting, View, Operation, Tools,
  Reading, Link, Connection, Box, MagicStick, Finished,
  CircleCheck, Loading, Clock, CircleClose, Warning, InfoFilled
} from '@element-plus/icons-vue'

// Props
const props = defineProps({
  stage: {
    type: String,
    default: 'pdf_bom'
  },
  progress: {
    type: Number,
    default: 0
  },
  data: {
    type: Object,
    default: () => ({})
  }
})

// Emits
const emit = defineEmits(['stage-complete'])

// 响应式数据
const overallProgress = ref(0)
const progressText = ref('准备开始...')
const progressStatus = ref('')
const currentStage = ref('pdf_bom')
const completedStages = ref<string[]>([])
const stageData = ref<any>({})
const logs = ref<any[]>([])
const logsContent = ref<HTMLElement>()

// 阶段状态判断
const isStageComplete = (stage: string) => {
  return completedStages.value.includes(stage)
}

const isStageActive = (stage: string) => {
  return currentStage.value === stage && !isStageComplete(stage)
}

const getStageClass = (stage: string) => {
  if (isStageComplete(stage)) return 'completed'
  if (isStageActive(stage)) return 'active'
  return 'pending'
}

// 格式化日志消息（高亮智能体）
const formatLogMessage = (message: string) => {
  return message
    .replace(/Qwen-VL|Qwen3-VL/g, '<span class="agent-name">🤖 $&</span>')
    .replace(/DeepSeek/g, '<span class="agent-name">🤖 $&</span>')
    .replace(/智能体|Agent/g, '<span class="agent-name">$&</span>')
}

// 添加日志
const addLog = (message: string, level: string = 'info') => {
  logs.value.push({
    time: new Date().toLocaleTimeString(),
    message,
    level
  })
  
  // 保持日志数量
  if (logs.value.length > 50) {
    logs.value.shift()
  }
  
  // 自动滚动到底部
  nextTick(() => {
    if (logsContent.value) {
      logsContent.value.scrollTop = logsContent.value.scrollHeight
    }
  })
}

// 监听props变化
watch(() => props.progress, (newProgress) => {
  overallProgress.value = newProgress
})

watch(() => props.stage, (newStage) => {
  currentStage.value = newStage
  
  // 标记之前的阶段为完成
  const stageOrder = ['pdf_bom', 'parallel', 'matching', 'generate']
  const currentIndex = stageOrder.indexOf(newStage)
  if (currentIndex > 0) {
    completedStages.value = stageOrder.slice(0, currentIndex)
  }
})

watch(() => props.data, (newData) => {
  stageData.value = { ...stageData.value, ...newData }
  
  // 更新进度文本
  if (newData.message) {
    progressText.value = newData.message
  }
}, { deep: true })

// 暴露方法给父组件
defineExpose({
  addLog
})
</script>

<style scoped lang="scss">
.processing-visualization-new {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.overall-progress {
  margin-bottom: 32px;
  
  .progress-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    
    h3 {
      margin: 0;
      font-size: 24px;
      color: var(--el-text-color-primary);
    }
    
    .progress-percentage {
      font-size: 32px;
      font-weight: bold;
      color: var(--el-color-primary);
    }
  }
  
  .progress-text {
    margin-top: 12px;
    text-align: center;
    color: var(--el-text-color-secondary);
    font-size: 14px;
  }
}

.stages-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 32px;
}

.stage-card {
  border: 2px solid var(--el-border-color);
  border-radius: 12px;
  padding: 20px;
  background: var(--el-bg-color);
  transition: all 0.3s;
  
  &.completed {
    border-color: var(--el-color-success);
    background: var(--el-color-success-light-9);
    
    .stage-icon {
      color: var(--el-color-success);
    }
  }
  
  &.active {
    border-color: var(--el-color-primary);
    background: var(--el-color-primary-light-9);
    box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
    
    .stage-icon {
      color: var(--el-color-primary);
    }
  }
  
  &.pending {
    opacity: 0.6;
    
    .stage-icon {
      color: var(--el-text-color-secondary);
    }
  }
}

.stage-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
  
  .stage-icon {
    font-size: 32px;
    
    .rotating {
      animation: rotate 1s linear infinite;
    }
  }
  
  .stage-title {
    flex: 1;
    
    h4 {
      margin: 0 0 4px 0;
      font-size: 18px;
      color: var(--el-text-color-primary);
    }
    
    p {
      margin: 0;
      font-size: 13px;
      color: var(--el-text-color-secondary);
    }
  }
}

.stage-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-left: 48px;
}

.stage-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--el-text-color-regular);
  
  .el-icon {
    font-size: 16px;
    color: var(--el-color-primary);
  }
  
  .agent-highlight {
    font-weight: 600;
    color: var(--el-color-primary);
    background: linear-gradient(90deg, #409eff, #67c23a);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  
  .final-result {
    font-weight: bold;
    font-size: 16px;
    color: var(--el-color-success);
  }
}

.processing-logs {
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  overflow: hidden;
  
  .logs-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 16px;
    background: var(--el-fill-color-light);
    border-bottom: 1px solid var(--el-border-color);
    
    span {
      flex: 1;
      font-weight: 600;
    }
  }
  
  .logs-content {
    max-height: 300px;
    overflow-y: auto;
    padding: 12px;
    background: var(--el-bg-color);
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 13px;
  }
  
  .log-item {
    display: flex;
    gap: 12px;
    padding: 6px 0;
    border-bottom: 1px solid var(--el-border-color-lighter);
    
    &:last-child {
      border-bottom: none;
    }
    
    .log-time {
      color: var(--el-text-color-secondary);
      flex-shrink: 0;
    }
    
    .log-message {
      flex: 1;
      word-break: break-word;
      
      :deep(.agent-name) {
        font-weight: bold;
        color: var(--el-color-primary);
      }
    }
    
    &.success {
      color: var(--el-color-success);
    }
    
    &.error {
      color: var(--el-color-error);
    }
    
    &.warning {
      color: var(--el-color-warning);
    }
  }
  
  .logs-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px;
    color: var(--el-text-color-secondary);
    
    .el-icon {
      font-size: 48px;
      margin-bottom: 12px;
      opacity: 0.3;
    }
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
</style>

