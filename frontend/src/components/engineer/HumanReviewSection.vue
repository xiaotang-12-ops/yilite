<template>
  <div class="human-review-section">
    <div class="review-header">
      <h3>人工复核</h3>
      <p>请仔细检查AI解析结果，确认或修正关键信息</p>
    </div>

    <!-- 复核统计 -->
    <div class="review-stats">
      <div class="stat-card">
        <div class="stat-number">{{ candidateFacts?.text_channel?.bom_items?.length || 0 }}</div>
        <div class="stat-label">BOM项目</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">{{ candidateFacts?.text_channel?.technical_requirements?.length || 0 }}</div>
        <div class="stat-label">技术要求</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">{{ candidateFacts?.vision_channel?.dimensions?.length || 0 }}</div>
        <div class="stat-label">尺寸信息</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">{{ assemblySpec?.parts?.length || 0 }}</div>
        <div class="stat-label">装配步骤</div>
      </div>
    </div>

    <!-- 复核内容标签页 -->
    <el-tabs v-model="activeTab" type="border-card">
      <!-- BOM表复核 -->
      <el-tab-pane label="BOM表复核" name="bom">
        <div class="review-content">
          <div class="content-header">
            <h4>BOM表信息</h4>
            <el-button type="primary" size="small" @click="addBomItem">添加项目</el-button>
          </div>
          
          <el-table :data="bomItems" style="width: 100%">
            <el-table-column prop="name" label="零件名称" width="200">
              <template #default="scope">
                <el-input v-model="scope.row.name" size="small" />
              </template>
            </el-table-column>
            <el-table-column prop="material" label="材料" width="120">
              <template #default="scope">
                <el-input v-model="scope.row.material" size="small" />
              </template>
            </el-table-column>
            <el-table-column prop="quantity" label="数量" width="80">
              <template #default="scope">
                <el-input-number v-model="scope.row.quantity" size="small" :min="1" />
              </template>
            </el-table-column>
            <el-table-column prop="unit" label="单位" width="80">
              <template #default="scope">
                <el-select v-model="scope.row.unit" size="small">
                  <el-option label="件" value="件" />
                  <el-option label="台" value="台" />
                  <el-option label="套" value="套" />
                  <el-option label="个" value="个" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column prop="weight" label="重量" width="100">
              <template #default="scope">
                <el-input v-model="scope.row.weight" size="small" />
              </template>
            </el-table-column>
            <el-table-column prop="confidence" label="置信度" width="100">
              <template #default="scope">
                <el-tag :type="getConfidenceType(scope.row.confidence)">
                  {{ (scope.row.confidence * 100).toFixed(0) }}%
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="scope">
                <el-button size="small" type="success" @click="confirmItem(scope.row)">确认</el-button>
                <el-button size="small" type="danger" @click="deleteItem(scope.$index, bomItems)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <!-- 技术要求复核 -->
      <el-tab-pane label="技术要求" name="tech">
        <div class="review-content">
          <div class="content-header">
            <h4>技术要求</h4>
            <el-button type="primary" size="small" @click="addTechRequirement">添加要求</el-button>
          </div>
          
          <div class="tech-requirements">
            <div 
              v-for="(req, index) in techRequirements" 
              :key="index"
              class="tech-item"
            >
              <div class="tech-content">
                <el-input
                  v-model="req.requirement"
                  type="textarea"
                  :rows="2"
                  placeholder="请输入技术要求"
                />
                <div class="tech-meta">
                  <el-select v-model="req.category" size="small" placeholder="分类">
                    <el-option label="公差要求" value="tolerance" />
                    <el-option label="表面处理" value="surface_treatment" />
                    <el-option label="焊接要求" value="welding" />
                    <el-option label="材料要求" value="material" />
                    <el-option label="其他" value="other" />
                  </el-select>
                  <el-tag :type="getConfidenceType(req.confidence)">
                    置信度: {{ (req.confidence * 100).toFixed(0) }}%
                  </el-tag>
                </div>
              </div>
              <div class="tech-actions">
                <el-button size="small" type="success" @click="confirmTechReq(req)">确认</el-button>
                <el-button size="small" type="danger" @click="deleteTechReq(index)">删除</el-button>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- 装配规范复核 -->
      <el-tab-pane label="装配规范" name="assembly">
        <div class="review-content">
          <div class="content-header">
            <h4>装配步骤</h4>
            <el-button type="primary" size="small" @click="addAssemblyStep">添加步骤</el-button>
          </div>
          
          <div class="assembly-steps">
            <div 
              v-for="(step, index) in assemblySteps" 
              :key="index"
              class="step-card"
            >
              <div class="step-header">
                <span class="step-number">步骤 {{ index + 1 }}</span>
                <el-button size="small" type="danger" @click="deleteStep(index)">删除</el-button>
              </div>
              
              <div class="step-content">
                <el-form :model="step" label-width="80px" size="small">
                  <el-form-item label="步骤名称">
                    <el-input v-model="step.title" placeholder="请输入步骤名称" />
                  </el-form-item>
                  <el-form-item label="操作描述">
                    <el-input 
                      v-model="step.description" 
                      type="textarea" 
                      :rows="3"
                      placeholder="请详细描述操作步骤"
                    />
                  </el-form-item>
                  <el-form-item label="预计时间">
                    <el-input-number v-model="step.estimated_time" :min="1" />
                    <span style="margin-left: 8px;">分钟</span>
                  </el-form-item>
                  <el-form-item label="涉及零件">
                    <el-select v-model="step.parts_involved" multiple placeholder="选择涉及的零件">
                      <el-option 
                        v-for="item in bomItems" 
                        :key="item.name"
                        :label="item.name" 
                        :value="item.name"
                      />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="所需工具">
                    <el-input v-model="step.tools_required" placeholder="请输入所需工具，用逗号分隔" />
                  </el-form-item>
                  <el-form-item label="安全注意">
                    <el-input 
                      v-model="step.safety_notes" 
                      type="textarea" 
                      :rows="2"
                      placeholder="请输入安全注意事项"
                    />
                  </el-form-item>
                </el-form>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- 质检要求 -->
      <el-tab-pane label="质检要求" name="qc">
        <div class="review-content">
          <div class="content-header">
            <h4>质量检查要求</h4>
            <el-button type="primary" size="small" @click="addQcItem">添加检查项</el-button>
          </div>
          
          <el-table :data="qcItems" style="width: 100%">
            <el-table-column prop="item" label="检查项目" width="200">
              <template #default="scope">
                <el-input v-model="scope.row.item" size="small" />
              </template>
            </el-table-column>
            <el-table-column prop="method" label="检查方法" width="150">
              <template #default="scope">
                <el-select v-model="scope.row.method" size="small">
                  <el-option label="目视检查" value="visual" />
                  <el-option label="尺寸测量" value="measurement" />
                  <el-option label="功能测试" value="function" />
                  <el-option label="其他" value="other" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column prop="standard" label="检查标准">
              <template #default="scope">
                <el-input v-model="scope.row.standard" size="small" />
              </template>
            </el-table-column>
            <el-table-column prop="frequency" label="检查频次" width="100">
              <template #default="scope">
                <el-select v-model="scope.row.frequency" size="small">
                  <el-option label="每件" value="each" />
                  <el-option label="抽检" value="sample" />
                  <el-option label="首件" value="first" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80">
              <template #default="scope">
                <el-button size="small" type="danger" @click="deleteQcItem(scope.$index)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 复核操作 -->
    <div class="review-actions">
      <div class="action-buttons">
        <el-button size="large" @click="requestRevision">要求AI重新解析</el-button>
        <el-button type="success" size="large" @click="approveReview">确认复核完成</el-button>
      </div>
      
      <div class="review-notes">
        <h4>复核备注</h4>
        <el-input
          v-model="reviewNotes"
          type="textarea"
          :rows="3"
          placeholder="请输入复核意见和备注..."
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, defineProps, defineEmits, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

// Props
const props = defineProps({
  candidateFacts: {
    type: Object,
    default: () => ({})
  },
  assemblySpec: {
    type: Object,
    default: () => ({})
  }
})

// 事件定义
const emit = defineEmits(['review-complete', 'request-revision'])

// 响应式数据
const activeTab = ref('bom')
const reviewNotes = ref('')

// 复核数据
const bomItems = ref([])
const techRequirements = ref([])
const assemblySteps = ref([])
const qcItems = ref([])

// 监听props变化，初始化数据
watch(() => props.candidateFacts, (newVal) => {
  if (newVal) {
    initializeReviewData()
  }
}, { immediate: true })

// 方法
const initializeReviewData = () => {
  // 初始化BOM数据
  bomItems.value = (props.candidateFacts?.text_channel?.bom_items || []).map(item => ({
    ...item,
    confirmed: false
  }))
  
  // 初始化技术要求
  techRequirements.value = (props.candidateFacts?.text_channel?.technical_requirements || []).map(req => ({
    ...req,
    confirmed: false
  }))
  
  // 初始化装配步骤
  assemblySteps.value = (props.assemblySpec?.assembly_plan?.sequence || []).map(step => ({
    ...step,
    confirmed: false
  }))
  
  // 初始化质检项目
  qcItems.value = (props.assemblySpec?.qc_plan?.items || []).map(item => ({
    ...item,
    confirmed: false
  }))
}

const addBomItem = () => {
  bomItems.value.push({
    name: '',
    material: '',
    quantity: 1,
    unit: '件',
    weight: '',
    confidence: 1.0,
    confirmed: false,
    source: 'manual'
  })
}

const addTechRequirement = () => {
  techRequirements.value.push({
    requirement: '',
    category: 'other',
    confidence: 1.0,
    confirmed: false,
    source: 'manual'
  })
}

const addAssemblyStep = () => {
  assemblySteps.value.push({
    title: '',
    description: '',
    estimated_time: 10,
    parts_involved: [],
    tools_required: '',
    safety_notes: '',
    confirmed: false
  })
}

const addQcItem = () => {
  qcItems.value.push({
    item: '',
    method: 'visual',
    standard: '',
    frequency: 'each',
    confirmed: false
  })
}

const confirmItem = (item) => {
  item.confirmed = true
  ElMessage.success('项目已确认')
}

const confirmTechReq = (req) => {
  req.confirmed = true
  ElMessage.success('技术要求已确认')
}

const deleteItem = (index, list) => {
  list.splice(index, 1)
}

const deleteTechReq = (index) => {
  techRequirements.value.splice(index, 1)
}

const deleteStep = (index) => {
  assemblySteps.value.splice(index, 1)
}

const deleteQcItem = (index) => {
  qcItems.value.splice(index, 1)
}

const getConfidenceType = (confidence) => {
  if (confidence >= 0.8) return 'success'
  if (confidence >= 0.6) return 'warning'
  return 'danger'
}

const requestRevision = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要求AI重新解析吗？这将重新开始解析流程。',
      '确认操作',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    emit('request-revision', {
      reason: reviewNotes.value,
      feedback: {
        bomIssues: bomItems.value.filter(item => !item.confirmed),
        techIssues: techRequirements.value.filter(req => !req.confirmed),
        assemblyIssues: assemblySteps.value.filter(step => !step.confirmed)
      }
    })
    
  } catch {
    // 用户取消
  }
}

const approveReview = async () => {
  // 检查是否有未确认的重要项目
  const unconfirmedBom = bomItems.value.filter(item => !item.confirmed && item.confidence < 0.8)
  const unconfirmedTech = techRequirements.value.filter(req => !req.confirmed && req.confidence < 0.8)
  
  if (unconfirmedBom.length > 0 || unconfirmedTech.length > 0) {
    try {
      await ElMessageBox.confirm(
        `还有 ${unconfirmedBom.length + unconfirmedTech.length} 个低置信度项目未确认，确定要继续吗？`,
        '确认复核',
        {
          confirmButtonText: '继续',
          cancelButtonText: '返回检查',
          type: 'warning'
        }
      )
    } catch {
      return
    }
  }
  
  // 构建复核结果
  const reviewResult = {
    bomItems: bomItems.value,
    techRequirements: techRequirements.value,
    assemblySteps: assemblySteps.value,
    qcItems: qcItems.value,
    reviewNotes: reviewNotes.value,
    reviewTime: new Date().toISOString(),
    reviewer: 'current_user' // 应该从用户状态获取
  }
  
  emit('review-complete', reviewResult)
  ElMessage.success('复核完成，进入下一步')
}
</script>

<style scoped>
.human-review-section {
  padding: 20px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.review-header {
  text-align: center;
  margin-bottom: 20px;
}

.review-header h3 {
  color: #303133;
  margin-bottom: 8px;
}

.review-header p {
  color: #909399;
  margin: 0;
}

.review-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 15px;
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 6px;
}

.stat-number {
  font-size: 24px;
  font-weight: bold;
  color: #409eff;
  margin-bottom: 5px;
}

.stat-label {
  font-size: 14px;
  color: #606266;
}

.review-content {
  padding: 20px 0;
}

.content-header {
  display: flex;
  justify-content: between;
  align-items: center;
  margin-bottom: 15px;
}

.content-header h4 {
  margin: 0;
  color: #606266;
}

.tech-requirements {
  space-y: 15px;
}

.tech-item {
  display: flex;
  gap: 15px;
  padding: 15px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  margin-bottom: 15px;
}

.tech-content {
  flex: 1;
}

.tech-meta {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-top: 10px;
}

.tech-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.assembly-steps {
  space-y: 20px;
}

.step-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  margin-bottom: 20px;
}

.step-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
}

.step-number {
  font-weight: bold;
  color: #409eff;
}

.step-content {
  padding: 20px;
}

.review-actions {
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid #e4e7ed;
}

.action-buttons {
  text-align: center;
  margin-bottom: 20px;
}

.action-buttons .el-button {
  margin: 0 10px;
}

.review-notes h4 {
  margin-bottom: 10px;
  color: #606266;
}
</style>
