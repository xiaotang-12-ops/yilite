<template>
  <div class="file-upload-section">
    <div class="upload-header">
      <h3>文件上传</h3>
      <p>请上传PDF工程图纸和3D模型文件</p>
    </div>

    <!-- PDF文件上传区域 -->
    <div class="upload-area">
      <h4>📄 PDF工程图纸</h4>
      <el-upload
        ref="pdfUpload"
        class="upload-dragger"
        drag
        :action="uploadUrl"
        :multiple="true"
        accept=".pdf"
        :before-upload="beforePdfUpload"
        :on-success="handlePdfSuccess"
        :on-error="handleUploadError"
        :on-progress="handleUploadProgress"
        :file-list="pdfFileList"
        :auto-upload="false"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          将PDF文件拖到此处，或<em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持多个PDF文件，单个文件不超过50MB
          </div>
        </template>
      </el-upload>
    </div>

    <!-- 3D模型文件上传区域 -->
    <div class="upload-area">
      <h4>🎯 3D模型文件 (STEP格式)</h4>
      <el-upload
        ref="modelUpload"
        class="upload-dragger"
        drag
        :action="uploadUrl"
        :multiple="true"
        accept=".step,.stp"
        :before-upload="beforeModelUpload"
        :on-success="handleModelSuccess"
        :on-error="handleUploadError"
        :on-progress="handleUploadProgress"
        :file-list="modelFileList"
        :auto-upload="false"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          将STEP模型文件拖到此处，或<em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            仅支持STEP格式 (.step, .stp)，单个文件不超过100MB
          </div>
        </template>
      </el-upload>
    </div>

    <!-- 上传进度 -->
    <div v-if="uploadProgress.show" class="upload-progress">
      <h4>上传进度</h4>
      <el-progress 
        :percentage="uploadProgress.percentage" 
        :status="uploadProgress.status"
        :stroke-width="8"
      />
      <p class="progress-text">{{ uploadProgress.text }}</p>
    </div>

    <!-- 文件列表 -->
    <div v-if="allFiles.length > 0" class="file-list">
      <h4>已选择的文件</h4>
      <el-table :data="allFiles" style="width: 100%">
        <el-table-column prop="name" label="文件名" />
        <el-table-column prop="type" label="类型" width="100" />
        <el-table-column prop="size" label="大小" width="100" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">
              {{ scope.row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="scope">
            <el-button 
              size="small" 
              type="danger" 
              @click="removeFile(scope.row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 操作按钮 -->
    <div class="upload-actions">
      <el-button 
        type="primary" 
        size="large"
        :disabled="allFiles.length === 0 || uploading"
        :loading="uploading"
        @click="startUpload"
      >
        {{ uploading ? '上传中...' : '开始上传' }}
      </el-button>
      <el-button 
        size="large"
        @click="clearFiles"
        :disabled="uploading"
      >
        清空文件
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, defineEmits } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'

// 事件定义
const emit = defineEmits(['files-uploaded', 'upload-progress'])

// 响应式数据
const uploadUrl = ref('/api/upload')
const pdfFileList = ref([])
const modelFileList = ref([])
const uploading = ref(false)
const uploadProgress = ref({
  show: false,
  percentage: 0,
  status: '',
  text: ''
})

// 计算属性
const allFiles = computed(() => {
  const files = []
  
  pdfFileList.value.forEach(file => {
    files.push({
      ...file,
      type: 'PDF',
      size: formatFileSize(file.size),
      status: file.status || '待上传'
    })
  })
  
  modelFileList.value.forEach(file => {
    files.push({
      ...file,
      type: '3D模型',
      size: formatFileSize(file.size),
      status: file.status || '待上传'
    })
  })
  
  return files
})

// 方法
const beforePdfUpload = (file) => {
  const isPDF = file.type === 'application/pdf'
  const isLt50M = file.size / 1024 / 1024 < 50

  if (!isPDF) {
    ElMessage.error('只能上传PDF文件!')
    return false
  }
  if (!isLt50M) {
    ElMessage.error('PDF文件大小不能超过50MB!')
    return false
  }
  return true
}

const beforeModelUpload = (file) => {
  const validTypes = [
    'application/step',
    'application/stp'
  ]
  const isValidType = validTypes.includes(file.type) ||
    /\.(step|stp)$/i.test(file.name)
  const isLt100M = file.size / 1024 / 1024 < 100

  if (!isValidType) {
    ElMessage.error('只能上传STEP格式的3D模型文件 (.step, .stp)!')
    return false
  }
  if (!isLt100M) {
    ElMessage.error('3D模型文件大小不能超过100MB!')
    return false
  }
  return true
}

const handlePdfSuccess = (response, file) => {
  file.status = '上传成功'
  ElMessage.success(`PDF文件 ${file.name} 上传成功`)
}

const handleModelSuccess = (response, file) => {
  file.status = '上传成功'
  ElMessage.success(`3D模型文件 ${file.name} 上传成功`)
}

const handleUploadError = (error, file) => {
  file.status = '上传失败'
  ElMessage.error(`文件 ${file.name} 上传失败`)
}

const handleUploadProgress = (event, file) => {
  const percentage = Math.round(event.percent)
  uploadProgress.value = {
    show: true,
    percentage,
    status: percentage === 100 ? 'success' : '',
    text: `正在上传 ${file.name}... ${percentage}%`
  }
  
  emit('upload-progress', { file, percentage })
}

const startUpload = async () => {
  if (allFiles.value.length === 0) {
    ElMessage.warning('请先选择要上传的文件')
    return
  }

  uploading.value = true
  uploadProgress.value.show = true

  try {
    // 上传PDF文件
    if (pdfFileList.value.length > 0) {
      await uploadFiles('pdf')
    }
    
    // 上传3D模型文件
    if (modelFileList.value.length > 0) {
      await uploadFiles('model')
    }

    ElMessage.success('所有文件上传完成!')
    
    // 发送上传完成事件
    emit('files-uploaded', {
      pdfFiles: pdfFileList.value.map(f => f.response?.filename || f.name),
      modelFiles: modelFileList.value.map(f => f.response?.filename || f.name)
    })

  } catch (error) {
    ElMessage.error('文件上传失败: ' + error.message)
  } finally {
    uploading.value = false
    uploadProgress.value.show = false
  }
}

const uploadFiles = async (type) => {
  // ✅ Bug修复：实现实际的上传逻辑
  const uploadRef = type === 'pdf' ? pdfUpload : modelUpload

  if (!uploadRef.value) {
    throw new Error(`Upload component not found: ${type}`)
  }

  // 手动触发Element Plus的upload组件提交
  uploadRef.value.submit()

  // 等待上传完成（通过监听success/error事件）
  return new Promise((resolve, reject) => {
    const checkInterval = setInterval(() => {
      const fileList = type === 'pdf' ? pdfFileList.value : modelFileList.value
      const allUploaded = fileList.every(f => f.status === 'success' || f.status === 'fail')

      if (allUploaded) {
        clearInterval(checkInterval)
        const hasFailed = fileList.some(f => f.status === 'fail')
        if (hasFailed) {
          reject(new Error('部分文件上传失败'))
        } else {
          resolve()
        }
      }
    }, 100)

    // 30秒超时
    setTimeout(() => {
      clearInterval(checkInterval)
      reject(new Error('上传超时'))
    }, 30000)
  })
}

const removeFile = (file) => {
  const pdfIndex = pdfFileList.value.findIndex(f => f.uid === file.uid)
  if (pdfIndex > -1) {
    pdfFileList.value.splice(pdfIndex, 1)
    return
  }
  
  const modelIndex = modelFileList.value.findIndex(f => f.uid === file.uid)
  if (modelIndex > -1) {
    modelFileList.value.splice(modelIndex, 1)
  }
}

const clearFiles = () => {
  pdfFileList.value = []
  modelFileList.value = []
  uploadProgress.value.show = false
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const getStatusType = (status) => {
  switch (status) {
    case '上传成功': return 'success'
    case '上传失败': return 'danger'
    case '上传中': return 'warning'
    default: return 'info'
  }
}
</script>

<style scoped>
.file-upload-section {
  padding: 20px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.upload-header {
  margin-bottom: 20px;
  text-align: center;
}

.upload-header h3 {
  color: #303133;
  margin-bottom: 8px;
}

.upload-header p {
  color: #909399;
  margin: 0;
}

.upload-area {
  margin-bottom: 30px;
}

.upload-area h4 {
  margin-bottom: 15px;
  color: #606266;
  font-size: 16px;
}

.upload-progress {
  margin: 20px 0;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 6px;
}

.upload-progress h4 {
  margin-bottom: 10px;
  color: #606266;
}

.progress-text {
  margin-top: 8px;
  color: #909399;
  font-size: 14px;
}

.file-list {
  margin: 20px 0;
}

.file-list h4 {
  margin-bottom: 15px;
  color: #606266;
}

.upload-actions {
  text-align: center;
  margin-top: 30px;
}

.upload-actions .el-button {
  margin: 0 10px;
}
</style>
