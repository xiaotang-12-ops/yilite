<template>
  <div class="worker-distribution-section">
    <div class="distribution-header">
      <h3>工人分发</h3>
      <p>将装配说明书分发给相关工人，开始生产任务</p>
    </div>

    <!-- 说明书信息 -->
    <div class="manual-info">
      <div class="info-card">
        <h4>装配说明书信息</h4>
        <div class="info-grid">
          <div class="info-item">
            <span class="label">说明书ID:</span>
            <span class="value">{{ manualId }}</span>
          </div>
          <div class="info-item">
            <span class="label">产品名称:</span>
            <span class="value">{{ manualInfo.productName }}</span>
          </div>
          <div class="info-item">
            <span class="label">创建时间:</span>
            <span class="value">{{ formatDate(manualInfo.createTime) }}</span>
          </div>
          <div class="info-item">
            <span class="label">装配步骤:</span>
            <span class="value">{{ manualInfo.stepCount }} 步</span>
          </div>
          <div class="info-item">
            <span class="label">预计时间:</span>
            <span class="value">{{ manualInfo.estimatedTime }} 分钟</span>
          </div>
          <div class="info-item">
            <span class="label">质量评分:</span>
            <span class="value">{{ manualInfo.qualityScore }} 分</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 工人选择 -->
    <div class="worker-selection">
      <div class="selection-header">
        <h4>选择工人</h4>
        <div class="selection-actions">
          <el-button size="small" @click="selectAllWorkers">全选</el-button>
          <el-button size="small" @click="clearSelection">清空</el-button>
          <el-button size="small" type="primary" @click="showWorkerDialog = true">添加工人</el-button>
        </div>
      </div>

      <div class="worker-grid">
        <div 
          v-for="worker in availableWorkers" 
          :key="worker.id"
          class="worker-card"
          :class="{ selected: selectedWorkers.includes(worker.id) }"
          @click="toggleWorkerSelection(worker.id)"
        >
          <div class="worker-avatar">
            <el-avatar :size="50" :src="worker.avatar">
              {{ worker.name.charAt(0) }}
            </el-avatar>
          </div>
          
          <div class="worker-info">
            <div class="worker-name">{{ worker.name }}</div>
            <div class="worker-department">{{ worker.department }}</div>
            <div class="worker-skills">
              <el-tag 
                v-for="skill in worker.skills" 
                :key="skill"
                size="small"
                type="info"
              >
                {{ skill }}
              </el-tag>
            </div>
          </div>
          
          <div class="worker-status">
            <el-tag :type="getStatusType(worker.status)" size="small">
              {{ getStatusText(worker.status) }}
            </el-tag>
            <div class="worker-workload">
              <span>当前任务: {{ worker.currentTasks }}</span>
            </div>
          </div>
          
          <div class="selection-indicator">
            <el-icon v-if="selectedWorkers.includes(worker.id)" class="selected-icon">
              <circle-check />
            </el-icon>
          </div>
        </div>
      </div>
    </div>

    <!-- 分发设置 -->
    <div class="distribution-settings">
      <h4>分发设置</h4>
      <el-form :model="distributionForm" label-width="120px">
        <el-form-item label="任务优先级">
          <el-select v-model="distributionForm.priority">
            <el-option label="低" value="low" />
            <el-option label="普通" value="normal" />
            <el-option label="高" value="high" />
            <el-option label="紧急" value="urgent" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="截止时间">
          <el-date-picker
            v-model="distributionForm.deadline"
            type="datetime"
            placeholder="选择截止时间"
            format="YYYY-MM-DD HH:mm"
            value-format="YYYY-MM-DD HH:mm:ss"
          />
        </el-form-item>
        
        <el-form-item label="任务说明">
          <el-input
            v-model="distributionForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入任务说明和特殊要求..."
          />
        </el-form-item>
        
        <el-form-item label="通知方式">
          <el-checkbox-group v-model="distributionForm.notificationMethods">
            <el-checkbox label="系统通知">系统内通知</el-checkbox>
            <el-checkbox label="邮件通知">邮件通知</el-checkbox>
            <el-checkbox label="短信通知">短信通知</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
    </div>

    <!-- 分发预览 -->
    <div v-if="selectedWorkers.length > 0" class="distribution-preview">
      <h4>分发预览</h4>
      <div class="preview-summary">
        <div class="summary-item">
          <span class="label">选中工人:</span>
          <span class="value">{{ selectedWorkers.length }} 人</span>
        </div>
        <div class="summary-item">
          <span class="label">预计完成时间:</span>
          <span class="value">{{ estimatedCompletionTime }}</span>
        </div>
        <div class="summary-item">
          <span class="label">任务优先级:</span>
          <el-tag :type="getPriorityType(distributionForm.priority)">
            {{ getPriorityText(distributionForm.priority) }}
          </el-tag>
        </div>
      </div>
      
      <div class="selected-workers-list">
        <div 
          v-for="workerId in selectedWorkers" 
          :key="workerId"
          class="selected-worker-item"
        >
          <el-avatar :size="30" :src="getWorkerById(workerId)?.avatar">
            {{ getWorkerById(workerId)?.name.charAt(0) }}
          </el-avatar>
          <span>{{ getWorkerById(workerId)?.name }}</span>
          <span class="department">{{ getWorkerById(workerId)?.department }}</span>
        </div>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="distribution-actions">
      <el-button 
        size="large"
        @click="previewDistribution"
        :disabled="selectedWorkers.length === 0"
      >
        预览分发
      </el-button>
      
      <el-button 
        type="primary" 
        size="large"
        @click="confirmDistribution"
        :disabled="selectedWorkers.length === 0"
        :loading="distributing"
      >
        {{ distributing ? '分发中...' : '确认分发' }}
      </el-button>
    </div>

    <!-- 添加工人对话框 -->
    <el-dialog v-model="showWorkerDialog" title="添加工人" width="600px">
      <div class="add-worker-form">
        <el-form :model="newWorkerForm" label-width="80px">
          <el-form-item label="姓名" required>
            <el-input v-model="newWorkerForm.name" placeholder="请输入工人姓名" />
          </el-form-item>
          <el-form-item label="部门" required>
            <el-select v-model="newWorkerForm.department" placeholder="选择部门">
              <el-option label="装配车间" value="assembly" />
              <el-option label="焊接车间" value="welding" />
              <el-option label="机加工车间" value="machining" />
              <el-option label="质检部门" value="qc" />
            </el-select>
          </el-form-item>
          <el-form-item label="技能">
            <el-select v-model="newWorkerForm.skills" multiple placeholder="选择技能">
              <el-option label="装配" value="assembly" />
              <el-option label="焊接" value="welding" />
              <el-option label="机械加工" value="machining" />
              <el-option label="质量检验" value="qc" />
              <el-option label="设备操作" value="equipment" />
            </el-select>
          </el-form-item>
          <el-form-item label="联系方式">
            <el-input v-model="newWorkerForm.contact" placeholder="请输入联系方式" />
          </el-form-item>
        </el-form>
      </div>
      
      <template #footer>
        <el-button @click="showWorkerDialog = false">取消</el-button>
        <el-button type="primary" @click="addNewWorker">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, defineProps, defineEmits } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CircleCheck } from '@element-plus/icons-vue'

// Props
const props = defineProps({
  manualId: {
    type: String,
    required: true
  }
})

// 事件定义
const emit = defineEmits(['distribution-complete'])

// 响应式数据
const selectedWorkers = ref([])
const distributing = ref(false)
const showWorkerDialog = ref(false)

// 说明书信息
const manualInfo = ref({
  productName: 'V型推雪板EURO连接器',
  createTime: new Date(),
  stepCount: 8,
  estimatedTime: 120,
  qualityScore: 85
})

// 分发表单
const distributionForm = ref({
  priority: 'normal',
  deadline: '',
  description: '',
  notificationMethods: ['系统通知']
})

// 新工人表单
const newWorkerForm = ref({
  name: '',
  department: '',
  skills: [],
  contact: ''
})

// 可用工人列表
const availableWorkers = ref([
  {
    id: 'w001',
    name: '张师傅',
    department: '装配车间',
    skills: ['装配', '焊接'],
    status: 'available',
    currentTasks: 2,
    avatar: '/avatars/worker1.png'
  },
  {
    id: 'w002',
    name: '李师傅',
    department: '装配车间',
    skills: ['装配', '机械加工'],
    status: 'busy',
    currentTasks: 4,
    avatar: '/avatars/worker2.png'
  },
  {
    id: 'w003',
    name: '王师傅',
    department: '焊接车间',
    skills: ['焊接', '质量检验'],
    status: 'available',
    currentTasks: 1,
    avatar: '/avatars/worker3.png'
  },
  {
    id: 'w004',
    name: '赵师傅',
    department: '装配车间',
    skills: ['装配', '设备操作'],
    status: 'available',
    currentTasks: 3,
    avatar: '/avatars/worker4.png'
  }
])

// 计算属性
const estimatedCompletionTime = computed(() => {
  if (selectedWorkers.value.length === 0) return '未知'
  
  const avgTime = manualInfo.value.estimatedTime / selectedWorkers.value.length
  const deadline = new Date()
  deadline.setMinutes(deadline.getMinutes() + avgTime)
  
  return deadline.toLocaleString()
})

// 方法
const toggleWorkerSelection = (workerId) => {
  const index = selectedWorkers.value.indexOf(workerId)
  if (index > -1) {
    selectedWorkers.value.splice(index, 1)
  } else {
    selectedWorkers.value.push(workerId)
  }
}

const selectAllWorkers = () => {
  selectedWorkers.value = availableWorkers.value
    .filter(w => w.status === 'available')
    .map(w => w.id)
}

const clearSelection = () => {
  selectedWorkers.value = []
}

const getWorkerById = (id) => {
  return availableWorkers.value.find(w => w.id === id)
}

const getStatusType = (status) => {
  switch (status) {
    case 'available': return 'success'
    case 'busy': return 'warning'
    case 'offline': return 'danger'
    default: return 'info'
  }
}

const getStatusText = (status) => {
  switch (status) {
    case 'available': return '空闲'
    case 'busy': return '忙碌'
    case 'offline': return '离线'
    default: return '未知'
  }
}

const getPriorityType = (priority) => {
  switch (priority) {
    case 'low': return 'info'
    case 'normal': return 'success'
    case 'high': return 'warning'
    case 'urgent': return 'danger'
    default: return 'info'
  }
}

const getPriorityText = (priority) => {
  switch (priority) {
    case 'low': return '低优先级'
    case 'normal': return '普通'
    case 'high': return '高优先级'
    case 'urgent': return '紧急'
    default: return '未知'
  }
}

const formatDate = (date) => {
  return new Date(date).toLocaleString()
}

const addNewWorker = () => {
  if (!newWorkerForm.value.name || !newWorkerForm.value.department) {
    ElMessage.warning('请填写必要信息')
    return
  }
  
  const newWorker = {
    id: 'w' + Date.now(),
    name: newWorkerForm.value.name,
    department: newWorkerForm.value.department,
    skills: newWorkerForm.value.skills,
    status: 'available',
    currentTasks: 0,
    avatar: '/avatars/default.png'
  }
  
  availableWorkers.value.push(newWorker)
  
  // 重置表单
  newWorkerForm.value = {
    name: '',
    department: '',
    skills: [],
    contact: ''
  }
  
  showWorkerDialog.value = false
  ElMessage.success('工人添加成功')
}

const previewDistribution = () => {
  const selectedWorkerNames = selectedWorkers.value
    .map(id => getWorkerById(id)?.name)
    .join('、')
  
  ElMessageBox.alert(
    `将向以下工人分发装配任务：\n\n${selectedWorkerNames}\n\n任务优先级：${getPriorityText(distributionForm.value.priority)}\n预计完成时间：${estimatedCompletionTime.value}`,
    '分发预览',
    {
      confirmButtonText: '确定',
      type: 'info'
    }
  )
}

const confirmDistribution = async () => {
  try {
    await ElMessageBox.confirm(
      `确定要向 ${selectedWorkers.value.length} 名工人分发装配任务吗？`,
      '确认分发',
      {
        confirmButtonText: '确定分发',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    distributing.value = true
    
    // 模拟分发过程
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    // 构建分发结果
    const distributionResult = {
      manualId: props.manualId,
      workers: selectedWorkers.value.map(id => getWorkerById(id)),
      settings: distributionForm.value,
      distributionTime: new Date().toISOString(),
      estimatedCompletion: estimatedCompletionTime.value
    }
    
    emit('distribution-complete', distributionResult)
    
    ElMessage.success('装配任务分发成功！')
    
  } catch {
    // 用户取消
  } finally {
    distributing.value = false
  }
}
</script>

<style scoped>
.worker-distribution-section {
  padding: 20px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.distribution-header {
  text-align: center;
  margin-bottom: 20px;
}

.distribution-header h3 {
  color: #303133;
  margin-bottom: 8px;
}

.distribution-header p {
  color: #909399;
  margin: 0;
}

.manual-info {
  margin-bottom: 30px;
}

.info-card {
  padding: 20px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background: #f9f9f9;
}

.info-card h4 {
  margin: 0 0 15px 0;
  color: #606266;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.info-item {
  display: flex;
  justify-content: space-between;
}

.info-item .label {
  color: #909399;
  font-weight: 500;
}

.info-item .value {
  color: #303133;
  font-weight: 600;
}

.worker-selection {
  margin-bottom: 30px;
}

.selection-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.selection-header h4 {
  margin: 0;
  color: #606266;
}

.selection-actions {
  display: flex;
  gap: 10px;
}

.worker-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 15px;
}

.worker-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 15px;
  border: 2px solid #e4e7ed;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.worker-card:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.2);
}

.worker-card.selected {
  border-color: #67c23a;
  background: #f0f9ff;
}

.worker-info {
  flex: 1;
}

.worker-name {
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}

.worker-department {
  color: #909399;
  font-size: 14px;
  margin-bottom: 8px;
}

.worker-skills {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}

.worker-status {
  text-align: right;
}

.worker-workload {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}

.selection-indicator {
  position: absolute;
  top: 10px;
  right: 10px;
}

.selected-icon {
  color: #67c23a;
  font-size: 20px;
}

.distribution-settings {
  margin-bottom: 30px;
}

.distribution-settings h4 {
  margin-bottom: 15px;
  color: #606266;
}

.distribution-preview {
  margin-bottom: 30px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
}

.distribution-preview h4 {
  margin: 0 0 15px 0;
  color: #606266;
}

.preview-summary {
  display: flex;
  gap: 30px;
  margin-bottom: 15px;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.summary-item .label {
  color: #909399;
  font-weight: 500;
}

.summary-item .value {
  color: #303133;
  font-weight: 600;
}

.selected-workers-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.selected-worker-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #fff;
  border-radius: 6px;
  border: 1px solid #e4e7ed;
}

.selected-worker-item .department {
  color: #909399;
  font-size: 12px;
}

.distribution-actions {
  text-align: center;
}

.distribution-actions .el-button {
  margin: 0 10px;
}

.add-worker-form {
  padding: 20px 0;
}
</style>
