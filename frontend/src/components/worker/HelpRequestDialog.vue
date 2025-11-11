<template>
  <el-dialog
    v-model="visible"
    title="请求帮助"
    width="550px"
    :before-close="handleClose"
  >
    <div class="help-request-form">
      <!-- 帮助类型 -->
      <div class="form-section">
        <h4>帮助类型</h4>
        <el-radio-group v-model="helpForm.type" class="help-types">
          <el-radio-button 
            v-for="type in helpTypes" 
            :key="type.value"
            :label="type.value"
          >
            <el-icon>{{ type.icon }}</el-icon>
            {{ type.label }}
          </el-radio-button>
        </el-radio-group>
      </div>

      <!-- 具体问题 -->
      <div class="form-section">
        <h4>具体问题 <span class="required">*</span></h4>
        <el-input
          v-model="helpForm.question"
          type="textarea"
          :rows="3"
          placeholder="请描述您需要帮助的具体问题..."
          maxlength="300"
          show-word-limit
        />
      </div>

      <!-- 当前步骤 -->
      <div class="form-section">
        <h4>当前步骤</h4>
        <el-select 
          v-model="helpForm.currentStep" 
          placeholder="选择您当前所在的装配步骤"
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

      <!-- 紧急程度 -->
      <div class="form-section">
        <h4>紧急程度</h4>
        <el-radio-group v-model="helpForm.urgency">
          <el-radio label="low">
            <el-tag type="info" size="small">不急</el-tag>
            <span class="urgency-desc">有空时回复即可</span>
          </el-radio>
          <el-radio label="medium">
            <el-tag type="warning" size="small">一般</el-tag>
            <span class="urgency-desc">希望今天内回复</span>
          </el-radio>
          <el-radio label="high">
            <el-tag type="danger" size="small">紧急</el-tag>
            <span class="urgency-desc">需要立即帮助</span>
          </el-radio>
        </el-radio-group>
      </div>

      <!-- 希望的帮助方式 -->
      <div class="form-section">
        <h4>希望的帮助方式</h4>
        <el-checkbox-group v-model="helpForm.helpMethods">
          <el-checkbox label="text">文字说明</el-checkbox>
          <el-checkbox label="voice">语音通话</el-checkbox>
          <el-checkbox label="video">视频通话</el-checkbox>
          <el-checkbox label="onsite">现场指导</el-checkbox>
        </el-checkbox-group>
      </div>

      <!-- 可用时间 -->
      <div class="form-section">
        <h4>可用时间</h4>
        <div class="time-selection">
          <el-radio-group v-model="helpForm.availability">
            <el-radio label="now">现在有空</el-radio>
            <el-radio label="break">休息时间</el-radio>
            <el-radio label="custom">自定义时间</el-radio>
          </el-radio-group>
          
          <div v-if="helpForm.availability === 'custom'" class="custom-time">
            <el-date-picker
              v-model="helpForm.customTime"
              type="datetime"
              placeholder="选择方便的时间"
              format="YYYY-MM-DD HH:mm"
              value-format="YYYY-MM-DD HH:mm:ss"
            />
          </div>
        </div>
      </div>

      <!-- 联系方式 -->
      <div class="form-section">
        <h4>联系方式</h4>
        <div class="contact-grid">
          <el-input
            v-model="helpForm.contact.phone"
            placeholder="手机号码"
            prefix-icon="Phone"
          />
          <el-input
            v-model="helpForm.contact.workstation"
            placeholder="工位号"
            prefix-icon="Location"
          />
        </div>
      </div>

      <!-- 已尝试的解决方法 -->
      <div class="form-section">
        <h4>已尝试的解决方法</h4>
        <el-input
          v-model="helpForm.attemptedSolutions"
          type="textarea"
          :rows="2"
          placeholder="请简述您已经尝试过的解决方法..."
          maxlength="200"
          show-word-limit
        />
      </div>
    </div>

    <!-- 快速帮助选项 -->
    <div class="quick-help-section">
      <h4>常见问题快速帮助</h4>
      <div class="quick-help-buttons">
        <el-button 
          v-for="quickHelp in quickHelpOptions" 
          :key="quickHelp.id"
          size="small"
          @click="selectQuickHelp(quickHelp)"
        >
          {{ quickHelp.title }}
        </el-button>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button 
          type="primary" 
          @click="submitHelpRequest"
          :loading="submitting"
          :disabled="!canSubmit"
        >
          {{ submitting ? '提交中...' : '请求帮助' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, defineProps, defineEmits, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  QuestionFilled, Tools, ChatDotRound, 
  VideoCamera, Phone, Location 
} from '@element-plus/icons-vue'

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
const emit = defineEmits(['update:modelValue', 'help-requested'])

// 响应式数据
const visible = ref(false)
const submitting = ref(false)

// 帮助类型定义
const helpTypes = ref([
  { value: 'technical', label: '技术问题', icon: Tools },
  { value: 'procedure', label: '操作流程', icon: QuestionFilled },
  { value: 'communication', label: '沟通协调', icon: ChatDotRound },
  { value: 'other', label: '其他帮助', icon: Phone }
])

// 快速帮助选项
const quickHelpOptions = ref([
  { id: 1, title: '看不懂图纸', type: 'technical', question: '工程图纸上的标注看不懂，需要详细解释' },
  { id: 2, title: '工具使用', type: 'technical', question: '不确定应该使用哪种工具进行操作' },
  { id: 3, title: '装配顺序', type: 'procedure', question: '对装配步骤的先后顺序有疑问' },
  { id: 4, title: '质量标准', type: 'procedure', question: '不确定质量检查的具体标准' },
  { id: 5, title: '安全操作', type: 'technical', question: '需要确认安全操作规范' },
  { id: 6, title: '材料确认', type: 'technical', question: '需要确认使用的材料是否正确' }
])

// 表单数据
const helpForm = ref({
  type: 'technical',
  question: '',
  currentStep: '',
  urgency: 'medium',
  helpMethods: ['text'],
  availability: 'now',
  customTime: '',
  contact: {
    phone: '',
    workstation: ''
  },
  attemptedSolutions: ''
})

// 计算属性
const canSubmit = computed(() => {
  return helpForm.value.question.trim().length > 0
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
  helpForm.value = {
    type: 'technical',
    question: '',
    currentStep: '',
    urgency: 'medium',
    helpMethods: ['text'],
    availability: 'now',
    customTime: '',
    contact: {
      phone: '',
      workstation: ''
    },
    attemptedSolutions: ''
  }
}

const handleClose = () => {
  if (helpForm.value.question.trim()) {
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

const selectQuickHelp = (quickHelp) => {
  helpForm.value.type = quickHelp.type
  helpForm.value.question = quickHelp.question
  
  ElMessage.success('已选择常见问题，您可以继续补充详细信息')
}

const submitHelpRequest = async () => {
  if (!canSubmit.value) {
    ElMessage.warning('请填写具体问题')
    return
  }

  try {
    submitting.value = true

    // 构建提交数据
    const helpData = {
      ...helpForm.value,
      requestTime: new Date().toISOString(),
      workerId: 'current_worker_id', // 应该从用户状态获取
      manualId: 'current_manual_id',  // 应该从当前任务获取
      status: 'pending'
    }

    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1500))

    // 生成帮助请求ID
    const requestId = 'HELP_' + Date.now()

    ElMessage.success('帮助请求提交成功！我们会尽快为您安排帮助。')

    // 发送事件
    emit('help-requested', {
      requestId,
      ...helpData
    })

    visible.value = false

  } catch (error) {
    ElMessage.error('提交失败: ' + error.message)
  } finally {
    submitting.value = false
  }
}

const getUrgencyText = (urgency) => {
  const map = {
    low: '不急',
    medium: '一般',
    high: '紧急'
  }
  return map[urgency] || '未知'
}

const getAvailabilityText = (availability) => {
  const map = {
    now: '现在有空',
    break: '休息时间',
    custom: '自定义时间'
  }
  return map[availability] || '未知'
}
</script>

<style scoped>
.help-request-form {
  max-height: 60vh;
  overflow-y: auto;
  padding: 0 5px;
}

.form-section {
  margin-bottom: 20px;
}

.form-section h4 {
  margin: 0 0 10px 0;
  color: #606266;
  font-size: 15px;
  font-weight: 600;
}

.required {
  color: #f56c6c;
}

.help-types {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.help-types .el-radio-button {
  width: 100%;
}

.help-types .el-radio-button__inner {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 6px;
  justify-content: center;
  font-size: 14px;
}

.urgency-desc {
  margin-left: 8px;
  font-size: 12px;
  color: #909399;
}

.time-selection {
  space-y: 10px;
}

.custom-time {
  margin-top: 10px;
  padding-left: 24px;
}

.contact-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.quick-help-section {
  margin-top: 20px;
  padding-top: 15px;
  border-top: 1px solid #e4e7ed;
}

.quick-help-section h4 {
  margin: 0 0 12px 0;
  color: #606266;
  font-size: 15px;
  font-weight: 600;
}

.quick-help-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.quick-help-buttons .el-button {
  font-size: 12px;
  padding: 6px 12px;
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
  margin-bottom: 10px;
  width: 100%;
}

.form-section .el-radio__label {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

/* 复选框组样式 */
.form-section .el-checkbox-group {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
}

.form-section .el-checkbox {
  margin-right: 0;
}

/* 滚动条样式 */
.help-request-form::-webkit-scrollbar {
  width: 6px;
}

.help-request-form::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.help-request-form::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.help-request-form::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>
