<template>
  <el-dialog
    v-model="visible"
    title="问题反馈"
    width="600px"
    :before-close="handleClose"
  >
    <div class="issue-report-form">
      <!-- 问题类型选择 -->
      <div class="form-section">
        <h4>问题类型</h4>
        <el-radio-group v-model="issueForm.type" class="issue-types">
          <el-radio-button 
            v-for="type in issueTypes" 
            :key="type.value"
            :label="type.value"
          >
            <el-icon>{{ type.icon }}</el-icon>
            {{ type.label }}
          </el-radio-button>
        </el-radio-group>
      </div>

      <!-- 问题描述 -->
      <div class="form-section">
        <h4>问题描述 <span class="required">*</span></h4>
        <el-input
          v-model="issueForm.description"
          type="textarea"
          :rows="4"
          placeholder="请详细描述遇到的问题..."
          maxlength="500"
          show-word-limit
        />
      </div>

      <!-- 涉及步骤 -->
      <div class="form-section">
        <h4>涉及步骤</h4>
        <el-select 
          v-model="issueForm.relatedSteps" 
          multiple 
          placeholder="选择相关的装配步骤"
          style="width: 100%"
        >
          <el-option
            v-for="step in assemblySteps"
            :key="step.id"
            :label="`步骤${step.id}: ${step.title}`"
            :value="step.id"
          />
        </el-select>
      </div>

      <!-- 严重程度 -->
      <div class="form-section">
        <h4>严重程度</h4>
        <el-radio-group v-model="issueForm.severity">
          <el-radio label="low">
            <el-tag type="success" size="small">轻微</el-tag>
            <span class="severity-desc">不影响继续工作</span>
          </el-radio>
          <el-radio label="medium">
            <el-tag type="warning" size="small">中等</el-tag>
            <span class="severity-desc">影响工作效率</span>
          </el-radio>
          <el-radio label="high">
            <el-tag type="danger" size="small">严重</el-tag>
            <span class="severity-desc">无法继续工作</span>
          </el-radio>
          <el-radio label="critical">
            <el-tag type="danger" size="small">紧急</el-tag>
            <span class="severity-desc">存在安全风险</span>
          </el-radio>
        </el-radio-group>
      </div>

      <!-- 图片上传 -->
      <div class="form-section">
        <h4>问题图片</h4>
        <el-upload
          ref="uploadRef"
          class="issue-upload"
          :action="uploadUrl"
          :file-list="issueForm.images"
          :before-upload="beforeUpload"
          :on-success="handleUploadSuccess"
          :on-remove="handleRemove"
          list-type="picture-card"
          :limit="5"
        >
          <el-icon class="upload-icon"><plus /></el-icon>
          <template #tip>
            <div class="upload-tip">
              支持 jpg/png 格式，最多5张图片，单张不超过2MB
            </div>
          </template>
        </el-upload>
      </div>

      <!-- 联系方式 -->
      <div class="form-section">
        <h4>联系方式</h4>
        <div class="contact-grid">
          <el-input
            v-model="issueForm.contact.phone"
            placeholder="手机号码"
            prefix-icon="Phone"
          />
          <el-input
            v-model="issueForm.contact.email"
            placeholder="邮箱地址"
            prefix-icon="Message"
          />
        </div>
      </div>

      <!-- 期望解决时间 -->
      <div class="form-section">
        <h4>期望解决时间</h4>
        <el-radio-group v-model="issueForm.urgency">
          <el-radio label="immediate">立即处理</el-radio>
          <el-radio label="today">今天内</el-radio>
          <el-radio label="tomorrow">明天内</el-radio>
          <el-radio label="week">一周内</el-radio>
        </el-radio-group>
      </div>

      <!-- 建议解决方案 -->
      <div class="form-section">
        <h4>建议解决方案</h4>
        <el-input
          v-model="issueForm.suggestion"
          type="textarea"
          :rows="3"
          placeholder="如果您有解决建议，请在此描述..."
          maxlength="300"
          show-word-limit
        />
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button 
          type="primary" 
          @click="submitIssue"
          :loading="submitting"
          :disabled="!canSubmit"
        >
          {{ submitting ? '提交中...' : '提交问题' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, defineProps, defineEmits, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Tools, Warning, QuestionFilled, Document } from '@element-plus/icons-vue'

// Props
const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  assemblySteps: {
    type: Array,
    default: () => []
  }
})

// 事件定义
const emit = defineEmits(['update:modelValue', 'issue-submitted'])

// 响应式数据
const visible = ref(false)
const submitting = ref(false)
const uploadRef = ref(null)
const uploadUrl = ref('/api/upload/images')

// 问题类型定义
const issueTypes = ref([
  { value: 'instruction', label: '说明不清', icon: Document },
  { value: 'material', label: '材料问题', icon: Tools },
  { value: 'safety', label: '安全隐患', icon: Warning },
  { value: 'other', label: '其他问题', icon: QuestionFilled }
])

// 表单数据
const issueForm = ref({
  type: 'instruction',
  description: '',
  relatedSteps: [],
  severity: 'medium',
  images: [],
  contact: {
    phone: '',
    email: ''
  },
  urgency: 'today',
  suggestion: ''
})

// 计算属性
const canSubmit = computed(() => {
  return issueForm.value.description.trim().length > 0
})

// 监听props变化
watch(() => props.modelValue, (newVal) => {
  visible.value = newVal
})

watch(visible, (newVal) => {
  emit('update:modelValue', newVal)
  
  if (!newVal) {
    resetForm()
  }
})

// 方法
const resetForm = () => {
  issueForm.value = {
    type: 'instruction',
    description: '',
    relatedSteps: [],
    severity: 'medium',
    images: [],
    contact: {
      phone: '',
      email: ''
    },
    urgency: 'today',
    suggestion: ''
  }
}

const handleClose = () => {
  if (issueForm.value.description.trim()) {
    ElMessageBox.confirm(
      '您有未保存的内容，确定要关闭吗？',
      '确认关闭',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    ).then(() => {
      visible.value = false
    }).catch(() => {
      // 用户取消
    })
  } else {
    visible.value = false
  }
}

const beforeUpload = (file) => {
  const isImage = file.type.startsWith('image/')
  const isLt2M = file.size / 1024 / 1024 < 2

  if (!isImage) {
    ElMessage.error('只能上传图片文件!')
    return false
  }
  if (!isLt2M) {
    ElMessage.error('图片大小不能超过 2MB!')
    return false
  }
  return true
}

const handleUploadSuccess = (response, file) => {
  issueForm.value.images.push({
    name: file.name,
    url: response.url,
    uid: file.uid
  })
  ElMessage.success('图片上传成功')
}

const handleRemove = (file) => {
  const index = issueForm.value.images.findIndex(img => img.uid === file.uid)
  if (index > -1) {
    issueForm.value.images.splice(index, 1)
  }
}

const submitIssue = async () => {
  if (!canSubmit.value) {
    ElMessage.warning('请填写问题描述')
    return
  }

  try {
    submitting.value = true

    // 构建提交数据
    const issueData = {
      ...issueForm.value,
      submitTime: new Date().toISOString(),
      workerId: 'current_worker_id', // 应该从用户状态获取
      manualId: 'current_manual_id'  // 应该从当前任务获取
    }

    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1500))

    // 生成问题ID
    const issueId = 'ISSUE_' + Date.now()

    ElMessage.success('问题反馈提交成功！')

    // 发送事件
    emit('issue-submitted', {
      issueId,
      ...issueData
    })

    visible.value = false

  } catch (error) {
    ElMessage.error('提交失败: ' + error.message)
  } finally {
    submitting.value = false
  }
}

const getSeverityText = (severity) => {
  const map = {
    low: '轻微',
    medium: '中等', 
    high: '严重',
    critical: '紧急'
  }
  return map[severity] || '未知'
}

const getUrgencyText = (urgency) => {
  const map = {
    immediate: '立即处理',
    today: '今天内',
    tomorrow: '明天内',
    week: '一周内'
  }
  return map[urgency] || '未知'
}
</script>

<style scoped>
.issue-report-form {
  max-height: 70vh;
  overflow-y: auto;
  padding: 0 5px;
}

.form-section {
  margin-bottom: 25px;
}

.form-section h4 {
  margin: 0 0 12px 0;
  color: #606266;
  font-size: 16px;
  font-weight: 600;
}

.required {
  color: #f56c6c;
}

.issue-types {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.issue-types .el-radio-button {
  width: 100%;
}

.issue-types .el-radio-button__inner {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
}

.severity-desc {
  margin-left: 8px;
  font-size: 12px;
  color: #909399;
}

.contact-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
}

.issue-upload {
  width: 100%;
}

.upload-icon {
  font-size: 28px;
  color: #8c939d;
}

.upload-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
}

.dialog-footer {
  text-align: right;
}

.dialog-footer .el-button {
  margin-left: 10px;
}

/* 自定义单选按钮样式 */
.form-section .el-radio {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
  width: 100%;
}

.form-section .el-radio__label {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

/* 上传组件样式调整 */
:deep(.el-upload--picture-card) {
  width: 80px;
  height: 80px;
}

:deep(.el-upload-list--picture-card .el-upload-list__item) {
  width: 80px;
  height: 80px;
}

/* 滚动条样式 */
.issue-report-form::-webkit-scrollbar {
  width: 6px;
}

.issue-report-form::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.issue-report-form::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.issue-report-form::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>
