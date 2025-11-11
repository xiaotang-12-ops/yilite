<template>
  <div class="quality-check-section">
    <div class="check-header">
      <h3>质量检查</h3>
      <p>对装配规范进行最终质量检查，确保符合生产要求</p>
    </div>

    <!-- 检查概览 -->
    <div class="check-overview">
      <div class="overview-card" :class="{ passed: overallScore >= 80, warning: overallScore >= 60 && overallScore < 80, failed: overallScore < 60 }">
        <div class="score-display">
          <div class="score-number">{{ overallScore }}</div>
          <div class="score-label">综合评分</div>
        </div>
        <div class="score-status">
          <el-icon v-if="overallScore >= 80" class="success-icon"><circle-check /></el-icon>
          <el-icon v-else-if="overallScore >= 60" class="warning-icon"><warning /></el-icon>
          <el-icon v-else class="error-icon"><circle-close /></el-icon>
          <span>{{ getScoreStatus(overallScore) }}</span>
        </div>
      </div>

      <div class="check-stats">
        <div class="stat-item">
          <div class="stat-value">{{ passedChecks }}</div>
          <div class="stat-label">通过项</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">{{ warningChecks }}</div>
          <div class="stat-label">警告项</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">{{ failedChecks }}</div>
          <div class="stat-label">失败项</div>
        </div>
      </div>
    </div>

    <!-- 检查项目 -->
    <div class="check-categories">
      <el-collapse v-model="activeCategories">
        <!-- 完整性检查 -->
        <el-collapse-item name="completeness">
          <template #title>
            <div class="category-title">
              <el-icon :class="getCategoryIconClass('completeness')">
                <component :is="getCategoryIcon('completeness')" />
              </el-icon>
              <span>完整性检查</span>
              <el-tag :type="getCategoryTagType('completeness')" size="small">
                {{ getCategoryStatus('completeness') }}
              </el-tag>
            </div>
          </template>
          
          <div class="check-items">
            <div v-for="item in completenessChecks" :key="item.id" class="check-item">
              <div class="item-header">
                <el-checkbox v-model="item.checked" @change="updateItemStatus(item)">
                  {{ item.title }}
                </el-checkbox>
                <el-tag :type="getItemTagType(item.status)" size="small">
                  {{ item.status }}
                </el-tag>
              </div>
              <div class="item-description">{{ item.description }}</div>
              <div v-if="item.issues.length > 0" class="item-issues">
                <h5>发现的问题：</h5>
                <ul>
                  <li v-for="issue in item.issues" :key="issue">{{ issue }}</li>
                </ul>
              </div>
              <div v-if="item.suggestions.length > 0" class="item-suggestions">
                <h5>改进建议：</h5>
                <ul>
                  <li v-for="suggestion in item.suggestions" :key="suggestion">{{ suggestion }}</li>
                </ul>
              </div>
            </div>
          </div>
        </el-collapse-item>

        <!-- 准确性检查 -->
        <el-collapse-item name="accuracy">
          <template #title>
            <div class="category-title">
              <el-icon :class="getCategoryIconClass('accuracy')">
                <component :is="getCategoryIcon('accuracy')" />
              </el-icon>
              <span>准确性检查</span>
              <el-tag :type="getCategoryTagType('accuracy')" size="small">
                {{ getCategoryStatus('accuracy') }}
              </el-tag>
            </div>
          </template>
          
          <div class="check-items">
            <div v-for="item in accuracyChecks" :key="item.id" class="check-item">
              <div class="item-header">
                <el-checkbox v-model="item.checked" @change="updateItemStatus(item)">
                  {{ item.title }}
                </el-checkbox>
                <el-tag :type="getItemTagType(item.status)" size="small">
                  {{ item.status }}
                </el-tag>
              </div>
              <div class="item-description">{{ item.description }}</div>
              <div v-if="item.confidence" class="item-confidence">
                <span>置信度: </span>
                <el-progress 
                  :percentage="item.confidence * 100" 
                  :stroke-width="6"
                  :show-text="false"
                  :color="getConfidenceColor(item.confidence)"
                />
                <span>{{ (item.confidence * 100).toFixed(0) }}%</span>
              </div>
            </div>
          </div>
        </el-collapse-item>

        <!-- 可行性检查 -->
        <el-collapse-item name="feasibility">
          <template #title>
            <div class="category-title">
              <el-icon :class="getCategoryIconClass('feasibility')">
                <component :is="getCategoryIcon('feasibility')" />
              </el-icon>
              <span>可行性检查</span>
              <el-tag :type="getCategoryTagType('feasibility')" size="small">
                {{ getCategoryStatus('feasibility') }}
              </el-tag>
            </div>
          </template>
          
          <div class="check-items">
            <div v-for="item in feasibilityChecks" :key="item.id" class="check-item">
              <div class="item-header">
                <el-checkbox v-model="item.checked" @change="updateItemStatus(item)">
                  {{ item.title }}
                </el-checkbox>
                <el-tag :type="getItemTagType(item.status)" size="small">
                  {{ item.status }}
                </el-tag>
              </div>
              <div class="item-description">{{ item.description }}</div>
              <div v-if="item.riskLevel" class="item-risk">
                <span>风险等级: </span>
                <el-tag :type="getRiskTagType(item.riskLevel)" size="small">
                  {{ getRiskText(item.riskLevel) }}
                </el-tag>
              </div>
            </div>
          </div>
        </el-collapse-item>

        <!-- 安全性检查 -->
        <el-collapse-item name="safety">
          <template #title>
            <div class="category-title">
              <el-icon :class="getCategoryIconClass('safety')">
                <component :is="getCategoryIcon('safety')" />
              </el-icon>
              <span>安全性检查</span>
              <el-tag :type="getCategoryTagType('safety')" size="small">
                {{ getCategoryStatus('safety') }}
              </el-tag>
            </div>
          </template>
          
          <div class="check-items">
            <div v-for="item in safetyChecks" :key="item.id" class="check-item">
              <div class="item-header">
                <el-checkbox v-model="item.checked" @change="updateItemStatus(item)">
                  {{ item.title }}
                </el-checkbox>
                <el-tag :type="getItemTagType(item.status)" size="small">
                  {{ item.status }}
                </el-tag>
              </div>
              <div class="item-description">{{ item.description }}</div>
              <div v-if="item.safetyLevel" class="item-safety">
                <span>安全等级: </span>
                <el-tag :type="getSafetyTagType(item.safetyLevel)" size="small">
                  {{ getSafetyText(item.safetyLevel) }}
                </el-tag>
              </div>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </div>

    <!-- 检查报告 -->
    <div class="check-report">
      <h4>质量检查报告</h4>
      <div class="report-content">
        <el-input
          v-model="checkReport"
          type="textarea"
          :rows="6"
          placeholder="请输入质量检查报告和建议..."
        />
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="check-actions">
      <el-button 
        size="large"
        @click="generateReport"
        :loading="generatingReport"
      >
        {{ generatingReport ? '生成中...' : '生成检查报告' }}
      </el-button>
      
      <el-button 
        type="warning" 
        size="large"
        @click="rejectQuality"
        :disabled="overallScore >= 80"
      >
        质量不合格，退回修改
      </el-button>
      
      <el-button 
        type="success" 
        size="large"
        @click="approveQuality"
        :disabled="overallScore < 60"
      >
        质量检查通过
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, defineProps, defineEmits, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  CircleCheck, Warning, CircleClose,
  Document, Location, Tools, Lock
} from '@element-plus/icons-vue'

// Props
const props = defineProps({
  assemblySpec: {
    type: Object,
    required: true
  }
})

// 事件定义
const emit = defineEmits(['quality-approved', 'quality-rejected'])

// 响应式数据
const activeCategories = ref(['completeness', 'accuracy', 'feasibility', 'safety'])
const checkReport = ref('')
const generatingReport = ref(false)

// 检查项目数据
const completenessChecks = ref([
  {
    id: 'bom_complete',
    title: 'BOM表完整性',
    description: '检查BOM表是否包含所有必要的零件信息',
    checked: false,
    status: '待检查',
    issues: [],
    suggestions: []
  },
  {
    id: 'steps_complete',
    title: '装配步骤完整性',
    description: '检查装配步骤是否覆盖所有零件的装配过程',
    checked: false,
    status: '待检查',
    issues: [],
    suggestions: []
  },
  {
    id: 'tech_req_complete',
    title: '技术要求完整性',
    description: '检查技术要求是否涵盖关键的质量标准',
    checked: false,
    status: '待检查',
    issues: [],
    suggestions: []
  }
])

const accuracyChecks = ref([
  {
    id: 'dimension_accuracy',
    title: '尺寸信息准确性',
    description: '验证尺寸标注与图纸的一致性',
    checked: false,
    status: '待检查',
    confidence: 0.85
  },
  {
    id: 'material_accuracy',
    title: '材料信息准确性',
    description: '确认材料规格与设计要求匹配',
    checked: false,
    status: '待检查',
    confidence: 0.92
  },
  {
    id: 'process_accuracy',
    title: '工艺流程准确性',
    description: '验证装配工艺的合理性和可操作性',
    checked: false,
    status: '待检查',
    confidence: 0.78
  }
])

const feasibilityChecks = ref([
  {
    id: 'time_feasible',
    title: '时间估算合理性',
    description: '评估装配时间估算是否符合实际情况',
    checked: false,
    status: '待检查',
    riskLevel: 'medium'
  },
  {
    id: 'tool_availability',
    title: '工具设备可用性',
    description: '确认所需工具和设备在生产现场可获得',
    checked: false,
    status: '待检查',
    riskLevel: 'low'
  },
  {
    id: 'skill_requirement',
    title: '技能要求合理性',
    description: '评估对工人技能水平的要求是否合理',
    checked: false,
    status: '待检查',
    riskLevel: 'medium'
  }
])

const safetyChecks = ref([
  {
    id: 'safety_warnings',
    title: '安全警告完整性',
    description: '检查是否包含所有必要的安全注意事项',
    checked: false,
    status: '待检查',
    safetyLevel: 'high'
  },
  {
    id: 'hazard_identification',
    title: '危险源识别',
    description: '确认已识别并标注所有潜在危险源',
    checked: false,
    status: '待检查',
    safetyLevel: 'critical'
  },
  {
    id: 'ppe_requirements',
    title: '防护用品要求',
    description: '明确各步骤所需的个人防护用品',
    checked: false,
    status: '待检查',
    safetyLevel: 'medium'
  }
])

// 计算属性
const allChecks = computed(() => [
  ...completenessChecks.value,
  ...accuracyChecks.value,
  ...feasibilityChecks.value,
  ...safetyChecks.value
])

const passedChecks = computed(() => 
  allChecks.value.filter(item => item.status === '通过').length
)

const warningChecks = computed(() => 
  allChecks.value.filter(item => item.status === '警告').length
)

const failedChecks = computed(() => 
  allChecks.value.filter(item => item.status === '失败').length
)

const overallScore = computed(() => {
  const totalChecks = allChecks.value.length
  if (totalChecks === 0) return 0
  
  const passedWeight = passedChecks.value * 100
  const warningWeight = warningChecks.value * 70
  const failedWeight = failedChecks.value * 0
  
  return Math.round((passedWeight + warningWeight + failedWeight) / totalChecks)
})

// 监听装配规范变化，自动执行检查
watch(() => props.assemblySpec, (newSpec) => {
  if (newSpec) {
    performAutomaticChecks()
  }
}, { immediate: true })

// 方法
const performAutomaticChecks = () => {
  // 自动检查完整性
  checkCompleteness()
  // 自动检查准确性
  checkAccuracy()
  // 自动检查可行性
  checkFeasibility()
  // 自动检查安全性
  checkSafety()
}

const checkCompleteness = () => {
  const spec = props.assemblySpec
  
  // 检查BOM完整性
  const bomCheck = completenessChecks.value.find(c => c.id === 'bom_complete')
  if (spec.parts && spec.parts.length > 0) {
    bomCheck.status = '通过'
    bomCheck.checked = true
  } else {
    bomCheck.status = '失败'
    bomCheck.issues = ['BOM表为空或缺失']
  }
  
  // 检查装配步骤完整性
  const stepsCheck = completenessChecks.value.find(c => c.id === 'steps_complete')
  if (spec.assembly_plan && spec.assembly_plan.sequence && spec.assembly_plan.sequence.length > 0) {
    stepsCheck.status = '通过'
    stepsCheck.checked = true
  } else {
    stepsCheck.status = '失败'
    stepsCheck.issues = ['装配步骤缺失或不完整']
  }
  
  // 检查技术要求完整性
  const techCheck = completenessChecks.value.find(c => c.id === 'tech_req_complete')
  if (spec.technical_requirements && spec.technical_requirements.length > 0) {
    techCheck.status = '通过'
    techCheck.checked = true
  } else {
    techCheck.status = '警告'
    techCheck.issues = ['技术要求信息较少']
    techCheck.suggestions = ['建议补充更多技术要求细节']
  }
}

const checkAccuracy = () => {
  // 基于置信度自动判断准确性
  accuracyChecks.value.forEach(check => {
    if (check.confidence >= 0.8) {
      check.status = '通过'
      check.checked = true
    } else if (check.confidence >= 0.6) {
      check.status = '警告'
    } else {
      check.status = '失败'
    }
  })
}

const checkFeasibility = () => {
  // 基于风险等级判断可行性
  feasibilityChecks.value.forEach(check => {
    if (check.riskLevel === 'low') {
      check.status = '通过'
      check.checked = true
    } else if (check.riskLevel === 'medium') {
      check.status = '警告'
    } else {
      check.status = '失败'
    }
  })
}

const checkSafety = () => {
  // 基于安全等级判断安全性
  safetyChecks.value.forEach(check => {
    if (check.safetyLevel === 'critical') {
      check.status = '失败' // 关键安全项需要人工确认
    } else if (check.safetyLevel === 'high') {
      check.status = '警告'
    } else {
      check.status = '通过'
      check.checked = true
    }
  })
}

const updateItemStatus = (item) => {
  if (item.checked) {
    item.status = '通过'
  } else {
    item.status = '待检查'
  }
}

const getCategoryStatus = (category) => {
  let checks = []
  switch (category) {
    case 'completeness': checks = completenessChecks.value; break
    case 'accuracy': checks = accuracyChecks.value; break
    case 'feasibility': checks = feasibilityChecks.value; break
    case 'safety': checks = safetyChecks.value; break
  }
  
  const passed = checks.filter(c => c.status === '通过').length
  const total = checks.length
  
  if (passed === total) return '全部通过'
  if (passed > total / 2) return '部分通过'
  return '需要检查'
}

const getCategoryTagType = (category) => {
  const status = getCategoryStatus(category)
  if (status === '全部通过') return 'success'
  if (status === '部分通过') return 'warning'
  return 'danger'
}

const getCategoryIcon = (category) => {
  switch (category) {
    case 'completeness': return Document
    case 'accuracy': return Location
    case 'feasibility': return Tools
    case 'safety': return Lock
    default: return Document
  }
}

const getCategoryIconClass = (category) => {
  const type = getCategoryTagType(category)
  return {
    'success-icon': type === 'success',
    'warning-icon': type === 'warning',
    'error-icon': type === 'danger'
  }
}

const getItemTagType = (status) => {
  switch (status) {
    case '通过': return 'success'
    case '警告': return 'warning'
    case '失败': return 'danger'
    default: return 'info'
  }
}

const getScoreStatus = (score) => {
  if (score >= 80) return '质量优秀'
  if (score >= 60) return '质量合格'
  return '质量不合格'
}

const getConfidenceColor = (confidence) => {
  if (confidence >= 0.8) return '#67c23a'
  if (confidence >= 0.6) return '#e6a23c'
  return '#f56c6c'
}

const getRiskTagType = (level) => {
  switch (level) {
    case 'low': return 'success'
    case 'medium': return 'warning'
    case 'high': return 'danger'
    default: return 'info'
  }
}

const getRiskText = (level) => {
  switch (level) {
    case 'low': return '低风险'
    case 'medium': return '中风险'
    case 'high': return '高风险'
    default: return '未知'
  }
}

const getSafetyTagType = (level) => {
  switch (level) {
    case 'low': return 'success'
    case 'medium': return 'warning'
    case 'high': return 'danger'
    case 'critical': return 'danger'
    default: return 'info'
  }
}

const getSafetyText = (level) => {
  switch (level) {
    case 'low': return '低风险'
    case 'medium': return '中等风险'
    case 'high': return '高风险'
    case 'critical': return '关键风险'
    default: return '未知'
  }
}

const generateReport = async () => {
  generatingReport.value = true
  
  try {
    // 模拟生成报告
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    const report = `
质量检查报告
=============

检查时间: ${new Date().toLocaleString()}
综合评分: ${overallScore.value}分

检查结果:
- 通过项目: ${passedChecks.value}个
- 警告项目: ${warningChecks.value}个  
- 失败项目: ${failedChecks.value}个

主要问题:
${allChecks.value.filter(c => c.issues.length > 0).map(c => 
  `- ${c.title}: ${c.issues.join(', ')}`
).join('\n')}

改进建议:
${allChecks.value.filter(c => c.suggestions.length > 0).map(c => 
  `- ${c.title}: ${c.suggestions.join(', ')}`
).join('\n')}

总体评价: ${getScoreStatus(overallScore.value)}
    `.trim()
    
    checkReport.value = report
    ElMessage.success('检查报告生成完成')
    
  } catch (error) {
    ElMessage.error('生成报告失败: ' + error.message)
  } finally {
    generatingReport.value = false
  }
}

const approveQuality = async () => {
  try {
    await ElMessageBox.confirm(
      `综合评分: ${overallScore.value}分，确定通过质量检查吗？`,
      '确认质量检查',
      {
        confirmButtonText: '确定通过',
        cancelButtonText: '取消',
        type: 'success'
      }
    )
    
    emit('quality-approved', {
      score: overallScore.value,
      report: checkReport.value,
      checkResults: allChecks.value,
      approveTime: new Date().toISOString()
    })
    
    ElMessage.success('质量检查通过，可以分发给工人')
    
  } catch {
    // 用户取消
  }
}

const rejectQuality = async () => {
  try {
    await ElMessageBox.confirm(
      `综合评分: ${overallScore.value}分，确定退回修改吗？`,
      '确认退回',
      {
        confirmButtonText: '确定退回',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    emit('quality-rejected', {
      score: overallScore.value,
      report: checkReport.value,
      issues: allChecks.value.filter(c => c.status === '失败'),
      rejectTime: new Date().toISOString()
    })
    
    ElMessage.warning('已退回修改，请完善后重新提交')
    
  } catch {
    // 用户取消
  }
}
</script>

<style scoped>
.quality-check-section {
  padding: 20px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.check-header {
  text-align: center;
  margin-bottom: 20px;
}

.check-header h3 {
  color: #303133;
  margin-bottom: 8px;
}

.check-header p {
  color: #909399;
  margin: 0;
}

.check-overview {
  display: flex;
  gap: 20px;
  margin-bottom: 30px;
  align-items: center;
}

.overview-card {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 20px;
  border: 2px solid #e4e7ed;
  border-radius: 8px;
  min-width: 200px;
}

.overview-card.passed {
  border-color: #67c23a;
  background: #f0f9ff;
}

.overview-card.warning {
  border-color: #e6a23c;
  background: #fdf6ec;
}

.overview-card.failed {
  border-color: #f56c6c;
  background: #fef0f0;
}

.score-display {
  text-align: center;
}

.score-number {
  font-size: 36px;
  font-weight: bold;
  color: #409eff;
  line-height: 1;
}

.score-label {
  font-size: 14px;
  color: #606266;
  margin-top: 5px;
}

.score-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.success-icon { color: #67c23a; }
.warning-icon { color: #e6a23c; }
.error-icon { color: #f56c6c; }

.check-stats {
  display: flex;
  gap: 30px;
}

.stat-item {
  text-align: center;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #409eff;
}

.stat-label {
  font-size: 14px;
  color: #606266;
  margin-top: 5px;
}

.category-title {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}

.check-items {
  padding: 15px 0;
}

.check-item {
  margin-bottom: 20px;
  padding: 15px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.item-description {
  color: #606266;
  font-size: 14px;
  margin-bottom: 10px;
}

.item-confidence, .item-risk, .item-safety {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
}

.item-issues, .item-suggestions {
  margin-top: 10px;
}

.item-issues h5, .item-suggestions h5 {
  margin: 0 0 5px 0;
  color: #606266;
  font-size: 14px;
}

.item-issues ul, .item-suggestions ul {
  margin: 0;
  padding-left: 20px;
}

.item-issues li {
  color: #f56c6c;
}

.item-suggestions li {
  color: #409eff;
}

.check-report {
  margin: 30px 0;
}

.check-report h4 {
  margin-bottom: 15px;
  color: #606266;
}

.check-actions {
  text-align: center;
  margin-top: 30px;
}

.check-actions .el-button {
  margin: 0 10px;
}
</style>
