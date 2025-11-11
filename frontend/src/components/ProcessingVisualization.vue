<template>
  <div class="processing-visualization">
    <div class="processing-header">
      <h3>🤖 智能装配说明书生成中...</h3>
      <p>多智能体协同工作，分析工程图纸和3D模型</p>
    </div>

    <!-- 总体进度 -->
    <div class="overall-progress">
      <el-progress
        :percentage="overallProgress"
        :status="progressStatus"
        :stroke-width="20"
        :show-text="true"
      />
      <div class="progress-text">{{ progressText }}</div>
    </div>

    <!-- 阶段卡片式展示 -->
    <div class="stages-container">`
    <div class="detailed-steps">
      <!-- 阶段1: PDF解析提取BOM（必须先完成） -->
      <div v-if="stage === 'pdf_bom'" class="sequential-stage">
        <div class="stage-header">
          <div class="stage-icon">
            <el-icon><Document /></el-icon>
          </div>
          <div class="stage-info">
            <h3>阶段1: PDF解析 - 提取BOM表</h3>
            <p>这是所有后续步骤的基础，必须先完成</p>
          </div>
        </div>

        <div class="stage-tasks">
          <!-- 文本提取 -->
          <div class="task-item" :class="{ active: stageData.pdf_bom?.current_task === 'text_extraction' }">
            <div class="task-header">
              <el-icon><Reading /></el-icon>
              <span>文本提取 (pypdf)</span>
              <el-tag v-if="stageData.pdf_bom?.text_extraction_done" type="success" size="small">完成</el-tag>
            </div>
            <div class="task-details" v-if="stageData.pdf_bom?.text_extraction">
              <p>{{ stageData.pdf_bom.text_extraction.message || '提取BOM表格数据...' }}</p>
              <div class="task-stats">
                <span>BOM候选项: {{ stageData.pdf_bom.text_extraction.bom_candidates || 0 }}</span>
              </div>
            </div>
          </div>

          <!-- 视觉分析 -->
          <div class="task-item" :class="{ active: stageData.pdf_bom?.current_task === 'vision_analysis' }">
            <div class="task-header">
              <el-icon><View /></el-icon>
              <span>视觉分析 (Qwen-VL)</span>
              <el-tag v-if="stageData.pdf_bom?.vision_analysis_done" type="success" size="small">完成</el-tag>
            </div>
            <div class="task-details" v-if="stageData.pdf_bom?.vision_analysis">
              <p>{{ stageData.pdf_bom.vision_analysis.message || '分析图纸结构和装配关系...' }}</p>
              <div class="task-stats">
                <span>装配关系: {{ stageData.pdf_bom.vision_analysis.assembly_relations || 0 }}</span>
                <span>技术要求: {{ stageData.pdf_bom.vision_analysis.requirements || 0 }}</span>
              </div>
            </div>
          </div>

          <!-- BOM生成 -->
          <div class="task-item" :class="{ active: stageData.pdf_bom?.current_task === 'bom_generation' }">
            <div class="task-header">
              <el-icon><List /></el-icon>
              <span>生成BOM表</span>
              <el-tag v-if="stageData.pdf_bom?.bom_generation_done" type="success" size="small">完成</el-tag>
            </div>
            <div class="task-details" v-if="stageData.pdf_bom?.bom_generation">
              <p>{{ stageData.pdf_bom.bom_generation.message || '合并文本和视觉结果...' }}</p>
              <div class="task-stats">
                <span>最终BOM项目: {{ stageData.pdf_bom.bom_generation.total_items || 0 }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 阶段2: 并行处理（基于BOM） -->
      <div v-if="stage === 'parallel'" class="sequential-stage">
        <div class="stage-header">
          <div class="stage-icon">
            <el-icon><Connection /></el-icon>
          </div>
          <div class="stage-info">
            <h3>阶段2: 并行处理 - 基于BOM数据</h3>
            <p>PDF深度分析和STEP零件提取同时进行</p>
          </div>
        </div>

        <div class="parallel-tasks">
          <!-- PDF深度分析 -->
          <div class="task-card">
            <div class="task-header">
              <el-icon><Document /></el-icon>
              <span>PDF深度分析</span>
              <span class="task-progress">{{ parallelProgress.pdf_deep || 0 }}%</span>
            </div>
            <el-progress :percentage="parallelProgress.pdf_deep || 0" size="small" />
            <div class="task-details" v-if="stageData.pdf_deep">
              <p>{{ stageData.pdf_deep.message || '分析装配关系和技术要求...' }}</p>
              <div class="task-stats">
                <span>装配步骤: {{ stageData.pdf_deep.assembly_steps || 0 }}</span>
                <span>紧固件: {{ stageData.pdf_deep.fasteners || 0 }}</span>
              </div>
            </div>
          </div>

          <!-- STEP零件提取 -->
          <div class="task-card">
            <div class="task-header">
              <el-icon><Box /></el-icon>
              <span>STEP零件提取</span>
              <span class="task-progress">{{ parallelProgress.step_extract || 0 }}%</span>
            </div>
            <el-progress :percentage="parallelProgress.step_extract || 0" size="small" />
            <div class="task-details" v-if="stageData.step_extract">
              <p>{{ stageData.step_extract.message || '提取零件几何名称和实例数...' }}</p>
              <div class="task-stats">
                <span>唯一零件: {{ stageData.step_extract.unique_parts || 0 }}</span>
                <span>总实例: {{ stageData.step_extract.total_instances || 0 }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 阶段3: BOM-STEP智能匹配 -->
      <div v-if="stage === 'matching'" class="sequential-stage">
        <div class="stage-header">
          <div class="stage-icon">
            <el-icon><Link /></el-icon>
          </div>
          <div class="stage-info">
            <h3>阶段3: BOM-STEP智能匹配</h3>
            <p>建立3D模型与BOM表的精准对应关系</p>
          </div>
        </div>

        <div class="stage-tasks">
          <!-- 规则匹配 -->
          <div class="task-item" :class="{ active: stageData.matching?.current_task === 'rule_matching' }">
            <div class="task-header">
              <el-icon><Operation /></el-icon>
              <span>规则匹配</span>
              <el-tag v-if="stageData.matching?.rule_matching_done" type="success" size="small">完成</el-tag>
            </div>
            <div class="task-details" v-if="stageData.matching?.rule_matching">
              <p>{{ stageData.matching.rule_matching.message || '基于代号和规格进行匹配...' }}</p>
              <div class="task-stats">
                <span>已匹配: {{ stageData.matching.rule_matching.matched || 0 }}/{{ stageData.matching.rule_matching.total_bom || 0 }}</span>
                <span>匹配率: {{ stageData.matching.rule_matching.match_rate || 0 }}%</span>
              </div>
            </div>
          </div>

          <!-- DeepSeek推理 -->
          <div class="task-item" :class="{ active: stageData.matching?.current_task === 'ai_matching' }">
            <div class="task-header">
              <el-icon><MagicStick /></el-icon>
              <span>DeepSeek推理匹配</span>
              <el-tag v-if="stageData.matching?.ai_matching_done" type="success" size="small">完成</el-tag>
            </div>
            <div class="task-details" v-if="stageData.matching?.ai_matching">
              <p>{{ stageData.matching.ai_matching.message || '修复编码问题，组件拆解...' }}</p>
              <div class="task-stats">
                <span>新匹配: {{ stageData.matching.ai_matching.new_matches || 0 }}</span>
                <span>组件拆解: {{ stageData.matching.ai_matching.components || 0 }}</span>
              </div>
            </div>
          </div>

          <!-- 生成映射 -->
          <div class="task-item" :class="{ active: stageData.matching?.current_task === 'mapping' }">
            <div class="task-header">
              <el-icon><Finished /></el-icon>
              <span>生成BOM-3D映射</span>
              <el-tag v-if="stageData.matching?.mapping_done" type="success" size="small">完成</el-tag>
            </div>
            <div class="task-details" v-if="stageData.matching?.mapping">
              <p>{{ stageData.matching.mapping.message || '建立完整的对应关系...' }}</p>
              <div class="task-stats">
                <span>总匹配率: {{ stageData.matching.mapping.final_match_rate || 0 }}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- PDF解析可视化 -->
      <div v-if="stage === 'pdf'" class="step-detail">
        <div class="step-header">
          <el-icon><Document /></el-icon>
          <span>PDF解析进度</span>
        </div>
        <div class="pdf-analysis">
          <div v-for="(file, index) in pdfAnalysis" :key="index" class="file-item">
            <div class="file-name">{{ file.name }}</div>
            <el-progress :percentage="file.progress" size="small" />
            <div class="analysis-details">
              <div v-if="file.bomItems > 0" class="detail-item">
                <el-icon><List /></el-icon>
                <span>BOM项目: {{ file.bomItems }}</span>
              </div>
              <div v-if="file.dimensions > 0" class="detail-item">
                <el-icon><Tools /></el-icon>
                <span>尺寸标注: {{ file.dimensions }}</span>
              </div>
              <div v-if="file.notes > 0" class="detail-item">
                <el-icon><Document /></el-icon>
                <span>技术要求: {{ file.notes }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 3D模型处理可视化 -->
      <div v-if="stage === 'model'" class="step-detail">
        <div class="step-header">
          <el-icon><Upload /></el-icon>
          <span>3D模型转换</span>
        </div>
        <div class="model-conversion">
          <div v-for="(model, index) in modelConversion" :key="index" class="model-item">
            <div class="model-info">
              <div class="model-name">{{ model.name }}</div>
              <div class="model-format">{{ model.format }} → GLB</div>
            </div>
            <el-progress :percentage="model.progress" size="small" />
            <div class="conversion-stats">
              <span v-if="model.vertices">顶点: {{ model.vertices.toLocaleString() }}</span>
              <span v-if="model.faces">面: {{ model.faces.toLocaleString() }}</span>
              <span v-if="model.size">大小: {{ formatFileSize(model.size) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- AI分析可视化 -->
      <div v-if="stage === 'ai'" class="step-detail">
        <div class="step-header">
          <el-icon><Setting /></el-icon>
          <span>AI智能分析</span>
        </div>
        <div class="ai-analysis">
          <div class="analysis-item">
            <div class="analysis-title">
              <el-icon><View /></el-icon>
              <span>视觉分析 (Qwen3-VL)</span>
            </div>
            <el-progress :percentage="aiProgress.vision" size="small" />
            <div class="analysis-results">
              <div v-for="result in visionResults" :key="result.type" class="result-item">
                <span class="result-type">{{ result.type }}</span>
                <span class="result-count">{{ result.count }}</span>
              </div>
            </div>
          </div>

          <div class="analysis-item">
            <div class="analysis-title">
              <el-icon><Setting /></el-icon>
              <span>专家分析 (DeepSeek)</span>
            </div>
            <el-progress :percentage="aiProgress.expert" size="small" />
            <div class="expert-insights">
              <div v-for="insight in expertInsights" :key="insight.category" class="insight-item">
                <el-tag :type="insight.type" size="small">{{ insight.category }}</el-tag>
                <span>{{ insight.description }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 生成阶段可视化 -->
      <div v-if="stage === 'generate'" class="step-detail">
        <div class="step-header">
          <el-icon><Setting /></el-icon>
          <span>说明书生成</span>
        </div>
        <div class="generation-progress">
          <div class="gen-item">
            <span>装配步骤生成</span>
            <el-progress :percentage="generationProgress.steps" size="small" />
          </div>
          <div class="gen-item">
            <span>3D交互界面</span>
            <el-progress :percentage="generationProgress.interface" size="small" />
          </div>
          <div class="gen-item">
            <span>HTML文档生成</span>
            <el-progress :percentage="generationProgress.html" size="small" />
          </div>
        </div>
      </div>
    </div>

    <!-- 实时日志 - 增强版 -->
    <div class="processing-logs">
      <div class="logs-header">
        <el-icon><Document /></el-icon>
        <span>处理日志</span>
        <el-tag v-if="logs.length > 0" size="small" type="info">{{ logs.length }} 条</el-tag>
      </div>
      <div class="logs-content">
        <div
          v-for="(log, index) in logs"
          :key="index"
          :class="['log-item', log.level || log.type]"
        >
          <span class="log-time">{{ log.time }}</span>
          <el-icon v-if="log.level === 'success'" class="log-icon"><CircleCheck /></el-icon>
          <el-icon v-else-if="log.level === 'error'" class="log-icon"><CircleClose /></el-icon>
          <el-icon v-else-if="log.level === 'warning'" class="log-icon"><Warning /></el-icon>
          <el-icon v-else class="log-icon"><InfoFilled /></el-icon>
          <span class="log-message">{{ log.message }}</span>
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
import { ref, computed, defineProps, defineEmits, watch } from 'vue'
import {
  Document, List, Upload, Setting, View, Operation, Tools,
  Reading, Link, Connection, Box, MagicStick, Finished
} from '@element-plus/icons-vue'

// Props
const props = defineProps({
  stage: {
    type: String,
    default: 'pdf' // pdf, model, ai, generate
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

// 并行处理进度（阶段2）
const parallelProgress = ref({ pdf_deep: 0, step_extract: 0 })
const stageData = ref<any>({})

const pdfAnalysis = ref<any[]>([])
const modelConversion = ref<any[]>([])
const aiProgress = ref({ vision: 0, expert: 0 })
const visionResults = ref<any[]>([])
const expertInsights = ref<any[]>([])
const generationProgress = ref({ steps: 0, interface: 0, html: 0 })
const logs = ref<any[]>([])

// 计算属性
const currentStage = computed(() => {
  const stages = {
    pdf_bom: {
      title: '阶段1: PDF解析 - 提取BOM表',
      description: '这是所有后续步骤的基础，必须先完成'
    },
    parallel: {
      title: '阶段2: 并行处理 - 基于BOM数据',
      description: 'PDF深度分析和STEP零件提取同时进行'
    },
    matching: {
      title: '阶段3: BOM-STEP智能匹配',
      description: '建立3D模型与BOM表的精准对应关系'
    },
    generate: {
      title: '阶段4: 生成装配说明书',
      description: '正在生成交互式装配说明书，整合所有分析结果'
    }
  }
  return stages[props.stage] || stages.pdf_bom
})

// 方法
const addLog = (message: string, type: string = 'info') => {
  logs.value.push({
    time: new Date().toLocaleTimeString(),
    message,
    type
  })
  
  // 保持日志数量在合理范围
  if (logs.value.length > 50) {
    logs.value.shift()
  }
}

const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const updateProgress = (stage: string, progress: number, data: any = {}) => {
  overallProgress.value = progress

  switch (stage) {
    case 'pdf_bom':
      stageData.value.pdf_bom = data
      progressText.value = `正在提取BOM表... ${progress}%`
      break
    case 'parallel':
      // 并行处理阶段
      if (data.parallel_progress) {
        parallelProgress.value = data.parallel_progress
      }
      stageData.value = { ...stageData.value, ...data }
      progressText.value = `并行处理中... ${progress}%`
      break
    case 'matching':
      stageData.value.matching = data
      progressText.value = `BOM-STEP匹配中... ${progress}%`
      break
    case 'generate':
      generationProgress.value = data.generationProgress || { steps: 0, interface: 0, html: 0 }
      progressText.value = `生成说明书... ${progress}%`
      break
  }

  if (progress >= 100) {
    progressStatus.value = 'success'
    emit('stage-complete', stage)
  }
}

// 监听props变化
watch(() => props.progress, (newProgress) => {
  updateProgress(props.stage, newProgress, props.data)
})

watch(() => props.data, (newData) => {
  // 处理并行进度数据
  if (newData.parallel_progress) {
    // 提取进度数字
    const progressData: any = {}
    Object.keys(newData.parallel_progress).forEach(key => {
      const item = newData.parallel_progress[key]
      progressData[key] = typeof item === 'number' ? item : (item.progress || 0)
    })
    parallelProgress.value = progressData
  }

  // 处理阶段数据
  if (newData.stage_data) {
    stageData.value = newData.stage_data
  }

  if (newData.logs) {
    newData.logs.forEach((log: any) => addLog(log.message, log.type))
  }
}, { deep: true })

// 暴露方法给父组件
defineExpose({
  addLog,
  updateProgress
})
</script>

<style lang="scss" scoped>
.processing-visualization {
  padding: 20px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.parallel-processing {
  margin-bottom: 30px;
}

.parallel-header {
  text-align: center;
  margin-bottom: 20px;

  h3 {
    margin: 0 0 8px 0;
    color: #409eff;
    font-size: 18px;
  }

  p {
    margin: 0;
    color: #666;
    font-size: 14px;
  }
}

.parallel-tasks {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.task-card {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 16px;
  transition: all 0.3s ease;

  &:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }
}

.task-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;

  .el-icon {
    margin-right: 8px;
    color: #409eff;
  }

  span:first-of-type {
    font-weight: 500;
    color: #333;
  }

  .task-progress {
    font-weight: bold;
    color: #409eff;
  }
}

.task-details {
  margin-top: 12px;

  p {
    margin: 0 0 8px 0;
    font-size: 13px;
    color: #666;
  }
}

.task-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;

  span {
    font-size: 12px;
    color: #888;
    background: #fff;
    padding: 2px 6px;
    border-radius: 4px;
    border: 1px solid #e9ecef;
  }
}

.processing-header {
  text-align: center;
  margin-bottom: 30px;
  
  h3 {
    color: #303133;
    margin-bottom: 8px;
  }
  
  p {
    color: #909399;
    margin: 0;
  }
}

.overall-progress {
  margin-bottom: 30px;
  
  .progress-text {
    text-align: center;
    margin-top: 10px;
    color: #606266;
    font-weight: 500;
  }
}

.detailed-steps {
  margin-bottom: 30px;
}

.step-detail {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
}

.step-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 15px;
  font-weight: 600;
  color: #303133;
}

.file-item, .model-item {
  margin-bottom: 15px;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 6px;
}

.file-name, .model-name {
  font-weight: 500;
  margin-bottom: 5px;
}

.analysis-details, .conversion-stats {
  display: flex;
  gap: 15px;
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}

.detail-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.analysis-item {
  margin-bottom: 20px;
}

.analysis-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  font-weight: 500;
}

.result-item, .insight-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 5px;
  font-size: 13px;
}

.gen-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.processing-logs {
  border-top: 1px solid #e4e7ed;
  padding-top: 20px;
}

.logs-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 15px;
  font-weight: 600;
  color: #303133;
}

.logs-content {
  max-height: 200px;
  overflow-y: auto;
  background: #f5f7fa;
  border-radius: 6px;
  padding: 10px;
}

.log-item {
  display: flex;
  gap: 10px;
  margin-bottom: 5px;
  font-size: 12px;
  
  &.info { color: #606266; }
  &.success { color: #67c23a; }
  &.warning { color: #e6a23c; }
  &.error { color: #f56c6c; }
}

.log-time {
  color: #909399;
  min-width: 80px;
}
</style>
