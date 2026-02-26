<template>
  <div class="viewer-page">
    <!-- 项目历史选择对话框 -->
    <el-dialog
      v-model="showProjectDialog"
      title="选择项目"
      :width="projectDialogWidth"
      :before-close="handleClose"
      class="project-dialog"
    >
      <div class="dialog-content">
        <!-- 搜索和筛选 -->
        <div class="search-section">
          <el-input
            v-model="searchQuery"
            placeholder="搜索项目名称或描述..."
            :prefix-icon="Search"
            clearable
            class="search-input"
          />
          <el-button
            class="scan-button"
            :loading="scanStarting"
            @click="openScannerDialog"
          >
            <el-icon><Camera /></el-icon>
            扫一扫
          </el-button>
          <!-- 状态筛选已隐藏 -->
          <!-- 移动端隐藏日期筛选 -->
          <el-date-picker
            v-if="!isMobile"
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            class="date-picker"
          />
        </div>
        
        <!-- 项目列表 -->
        <div class="projects-section">
          <!-- 桌面端：表格布局 -->
          <el-table
            v-if="!isMobile"
            :data="paginatedProjects"
            @row-click="selectProject"
            highlight-current-row
            class="projects-table"
            v-loading="loading"
          >
            <el-table-column
              prop="projectName"
              label="项目名称"
              :min-width="200"
            >
              <template #default="{ row }">
                <div class="project-name">
                  <el-icon class="project-icon"><Document /></el-icon>
                  <span class="project-name-text">{{ row.projectName }}</span>
                </div>
              </template>
            </el-table-column>
            
            <el-table-column prop="status" label="状态" width="120">
              <template #default="{ row }">
                <el-tag
                  :type="getStatusType(row.status)"
                  size="small"
                >
                  {{ getStatusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            
            <el-table-column prop="createdAt" label="生成时间" width="180">
              <template #default="{ row }">
                {{ formatDate(row.createdAt) }}
              </template>
            </el-table-column>
            
            <el-table-column prop="fileCount" label="文件数量" width="120" v-if="false">
              <template #default="{ row }">
                <span class="file-count">
                  {{ row.pdfCount }}PDF + {{ row.stepCount }}STEP
                </span>
              </template>
            </el-table-column>
            
            <el-table-column prop="processingTime" label="处理时间" width="120" v-if="false">
              <template #default="{ row }">
                {{ row.processingTime }}s
              </template>
            </el-table-column>
            
            <el-table-column label="操作" width="240">
              <template #default="{ row }">
                <template v-if="row.status === 'completed'">
                  <el-button
                    type="primary"
                    size="small"
                    @click.stop="viewProject(row)"
                  >
                    <el-icon><View /></el-icon>
                    查看说明书
                  </el-button>
                </template>
                <template v-else-if="row.status === 'failed'">
                  <el-button
                    type="danger"
                    size="small"
                    @click.stop="deleteProject(row)"
                  >
                    <el-icon><Delete /></el-icon>
                    删除任务
                  </el-button>
                </template>
                <template v-else-if="row.status === 'processing'">
                  <el-button
                    type="danger"
                    size="small"
                    plain
                    @click.stop="deleteProject(row)"
                  >
                    <el-icon><Delete /></el-icon>
                    中断/删除
                  </el-button>
                </template>
              </template>
            </el-table-column>
          </el-table>

          <!-- 移动端：卡片布局 -->
          <div v-if="isMobile" class="project-cards" v-loading="loading">
            <div
              v-for="project in paginatedProjects"
              :key="project.id"
              class="project-card"
              @click="selectProject(project)"
            >
              <!-- 项目名称 -->
              <div class="card-header">
                <el-icon class="card-icon"><Document /></el-icon>
                <span class="card-title">{{ project.projectName }}</span>
              </div>

              <!-- 状态和时间 -->
              <div class="card-meta">
                <el-tag :type="getStatusType(project.status)" size="small">
                  {{ getStatusText(project.status) }}
                </el-tag>
                <span class="card-time">{{ formatDate(project.createdAt) }}</span>
              </div>

              <!-- 操作按钮 -->
              <div class="card-actions">
                <template v-if="project.status === 'completed'">
                  <el-button
                    type="primary"
                    size="small"
                    @click.stop="viewProject(project)"
                  >
                    <el-icon><View /></el-icon>
                    查看说明书
                  </el-button>
                </template>
                <template v-else-if="project.status === 'failed'">
                  <el-button
                    type="danger"
                    size="small"
                    @click.stop="deleteProject(project)"
                  >
                    <el-icon><Delete /></el-icon>
                    删除任务
                  </el-button>
                </template>
                <template v-else-if="project.status === 'processing'">
                  <el-button
                    type="danger"
                    size="small"
                    plain
                    @click.stop="deleteProject(project)"
                  >
                    <el-icon><Delete /></el-icon>
                    中断/删除
                  </el-button>
                </template>
              </div>
            </div>
          </div>
          
          <!-- 分页 -->
          <div class="pagination-section">
            <el-pagination
              v-model:current-page="currentPage"
              v-model:page-size="pageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="totalProjects"
              :layout="paginationLayout"
              :small="isMobile"
              :pager-count="isMobile ? 5 : 7"
              :background="isMobile"
              @size-change="handleSizeChange"
              @current-change="handleCurrentChange"
            />
          </div>
        </div>
        
        <!-- 空状态 -->
        <div v-if="filteredProjects.length === 0 && !loading" class="empty-state">
          <el-empty description="暂无项目数据">
            <el-button v-if="isAdmin" type="primary" @click="$router.push('/generator')">
              创建新项目
            </el-button>
          </el-empty>
        </div>
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="handleClose">取消</el-button>
          <el-button v-if="isAdmin" type="primary" @click="$router.push('/generator')">
            <el-icon><Plus /></el-icon>
            新建项目
          </el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="showScannerDialog"
      title="扫一扫填充搜索"
      :width="scannerDialogWidth"
      class="scanner-dialog"
      :close-on-click-modal="false"
      @closed="handleScannerDialogClosed"
    >
      <div class="scanner-dialog-body">
        <el-alert
          v-if="scanError"
          type="warning"
          :title="scanError"
          :closable="false"
          show-icon
        />

        <div class="scanner-video-wrapper">
          <video
            v-show="!scanError"
            ref="scannerVideoRef"
            class="scanner-video"
            autoplay
            muted
            playsinline
          />
          <div v-if="scanError" class="scanner-video-placeholder">
            当前环境无法启用摄像头扫码
          </div>
        </div>

        <div class="scanner-tip">
          将物料二维码/条码放在取景框中央，识别后会自动填入搜索框。
        </div>

        <el-input
          v-model="manualScanInput"
          placeholder="扫码不可用时，可手动输入物料代码（如 01.09.0436）"
          clearable
          @keyup.enter="confirmManualScan"
        />
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showScannerDialog = false">关闭</el-button>
          <el-button type="primary" @click="confirmManualScan">填入搜索</el-button>
        </div>
      </template>
    </el-dialog>
    
    <!-- 项目详情预览 -->
    <div v-if="!showProjectDialog" class="project-preview">
      <div class="preview-header">
        <h2>项目历史</h2>
        <el-button type="primary" @click="showProjectDialog = true">
          <el-icon><FolderOpened /></el-icon>
          选择项目
        </el-button>
      </div>
      
      <div class="preview-content">
        <div class="stats-cards">
          <div class="stat-card">
            <div class="stat-value">{{ projectStats.total }}</div>
            <div class="stat-label">总项目数</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ projectStats.completed }}</div>
            <div class="stat-label">已完成</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ projectStats.processing }}</div>
            <div class="stat-label">处理中</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ projectStats.avgTime }}s</div>
            <div class="stat-label">平均处理时间</div>
          </div>
        </div>
        
        <div class="recent-projects">
          <h3>最近项目</h3>
          <div class="recent-list">
            <div
              v-for="project in recentProjects"
              :key="project.id"
              class="recent-item"
              @click="viewProject(project)"
            >
              <div class="recent-info">
                <div class="recent-name">{{ project.projectName }}</div>
                <div class="recent-time">{{ formatDate(project.createdAt) }}</div>
              </div>
              <el-tag :type="getStatusType(project.status)" size="small">
                {{ getStatusText(project.status) }}
              </el-tag>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch, nextTick, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useMediaQuery } from '@vueuse/core'
import {
  Search, Document, View, Plus, FolderOpened, Delete, Camera
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import { BrowserMultiFormatReader, type IScannerControls } from '@zxing/browser'
import { useAdminStore } from '../stores/admin'

const router = useRouter()
const isMobile = useMediaQuery('(max-width: 768px)')
const adminStore = useAdminStore()
const { isAdmin } = storeToRefs(adminStore)

adminStore.ensureInit()

// 响应式数据
const showProjectDialog = ref(true)
const loading = ref(false)
const searchQuery = ref('')
const statusFilter = ref('')
const dateRange = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const showScannerDialog = ref(false)
const scanStarting = ref(false)
const scanError = ref('')
const manualScanInput = ref('')
const scannerVideoRef = ref<HTMLVideoElement | null>(null)
const projectDialogWidth = computed(() => (isMobile.value ? '96%' : '80%'))
const scannerDialogWidth = computed(() => (isMobile.value ? '96%' : '420px'))
const paginationLayout = computed(() =>
  isMobile.value ? 'prev, pager, next' : 'total, sizes, prev, pager, next, jumper'
)
const GENERATOR_LAST_TASK_KEY = 'generator_last_task'
const GENERATOR_RECOVERY_TASK_KEY = 'generator_current_task'

// ✅ 从 localStorage 加载项目数据
const projects = ref<any[]>([])
let scannerControls: IScannerControls | null = null
let scannerReader: BrowserMultiFormatReader | null = null

// 加载历史记录
const loadHistory = async () => {
  try {
    // ✅ 优先从后端API获取所有已生成的说明书
    try {
      const response = await axios.get('/api/manuals', { params: { include_failed: true } })
      const manuals = response.data.manuals || []

      console.log(`✅ 从后端加载了 ${manuals.length} 个说明书`)

      // 转换为项目格式
      projects.value = manuals.map((item: any) => ({
        id: item.taskId,
        projectName: item.productName || '未命名产品',
        status: item.status || 'completed',
        createdAt: item.timestamp,
        pdfCount: 0,
        stepCount: item.stepCount || 0,
        processingTime: 0,
        description: item.status === 'failed'
          ? '任务未完成或失败，可删除后重试'
          : `装配步骤: ${item.stepCount || 0} 个`
      }))

      return
    } catch (apiError) {
      console.warn('从后端加载失败，尝试从localStorage加载:', apiError)
    }

    // ✅ 如果后端API失败，回退到localStorage
    const historyKey = 'assembly_manual_history'
    const stored = localStorage.getItem(historyKey)

    if (stored) {
      const history = JSON.parse(stored)

      // 转换为项目格式
      projects.value = history.map((item: any) => ({
        id: item.taskId,
        projectName: item.productName || '未命名产品',
        status: 'completed',
        createdAt: item.timestamp,
        pdfCount: item.data?.pdf_files?.length || 0,
        stepCount: item.data?.assembly_steps?.length || 0,
        processingTime: 0,
        description: `装配步骤: ${item.data?.assembly_steps?.length || 0} 个`,
        data: item.data
      }))

      console.log(`✅ 从localStorage加载了 ${projects.value.length} 个说明书`)
    }
  } catch (e) {
    console.error('加载历史记录失败:', e)
    ElMessage.warning('加载历史记录失败')
  }
}

// 项目统计
const projectStats = computed(() => {
  const total = projects.value.length
  const completed = projects.value.filter(p => p.status === 'completed').length
  const processing = projects.value.filter(p => p.status === 'processing').length
  const avgTime = Math.round(
    projects.value
      .filter(p => p.processingTime > 0)
      .reduce((sum, p) => sum + p.processingTime, 0) / 
    projects.value.filter(p => p.processingTime > 0).length || 0
  )
  
  return { total, completed, processing, avgTime }
})

// 最近项目
const recentProjects = computed(() => {
  return [...projects.value]
    .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
    .slice(0, 5)
})

// 过滤后的项目
const filteredProjects = computed(() => {
  let filtered = projects.value
  
  // 搜索过滤
  if (searchQuery.value) {
    const query = searchQuery.value.trim().toLowerCase()
    filtered = filtered.filter(p => 
      String(p.projectName || '').toLowerCase().includes(query) ||
      String(p.projectNumber || '').toLowerCase().includes(query) ||
      String(p.description || '').toLowerCase().includes(query) ||
      String(p.id || '').toLowerCase().includes(query)
    )
  }
  
  // 状态过滤
  if (statusFilter.value) {
    filtered = filtered.filter(p => p.status === statusFilter.value)
  }
  
  // 日期范围过滤
  if (dateRange.value && dateRange.value.length === 2) {
    const [start, end] = dateRange.value
    filtered = filtered.filter(p => {
      const date = new Date(p.createdAt)
      return date >= start && date <= end
    })
  }
  
  return filtered
})

const isCameraApiSupported = () => {
  return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)
}

const isSecureCameraContext = () => {
  const host = window.location.hostname
  const localHosts = ['localhost', '127.0.0.1', '::1']
  return window.isSecureContext || localHosts.includes(host)
}

const normalizeScannedText = (rawText: string) => {
  const value = rawText.trim()
  if (!value) return ''

  try {
    const url = new URL(value)
    const queryCandidate =
      url.searchParams.get('code') ||
      url.searchParams.get('materialCode') ||
      url.searchParams.get('material')

    if (queryCandidate && queryCandidate.trim()) {
      return queryCandidate.trim()
    }

    const lastPathPart = decodeURIComponent(
      url.pathname
        .split('/')
        .filter(Boolean)
        .pop() || ''
    ).trim()

    if (lastPathPart) {
      return lastPathPart
    }
  } catch {
    // 不是 URL，直接使用原值
  }

  return value
}

const stopScanner = () => {
  if (scannerControls) {
    try {
      scannerControls.stop()
    } catch (error) {
      console.warn('停止扫码失败:', error)
    }
    scannerControls = null
  }

  if (scannerReader) {
    try {
      scannerReader.reset()
    } catch (error) {
      console.warn('重置扫码器失败:', error)
    }
  }
}

const applyScannedValue = (rawText: string) => {
  const normalized = normalizeScannedText(rawText)
  if (!normalized) {
    ElMessage.warning('扫码结果为空，请重试')
    return
  }

  searchQuery.value = normalized
  manualScanInput.value = normalized
  ElMessage.success(`已填入物料代码：${normalized}`)
  showScannerDialog.value = false
  stopScanner()
}

const startScanner = async () => {
  if (!scannerVideoRef.value) return

  if (!scannerReader) {
    scannerReader = new BrowserMultiFormatReader()
  }

  scanStarting.value = true
  scanError.value = ''

  try {
    scannerControls = await scannerReader.decodeFromVideoDevice(
      undefined,
      scannerVideoRef.value,
      (result, error) => {
        if (result) {
          applyScannedValue(result.getText())
          return
        }

        if (error && error.name !== 'NotFoundException') {
          console.warn('扫码识别异常:', error)
        }
      }
    )
  } catch (error: any) {
    console.error('启动扫码失败:', error)
    scanError.value = `启动扫码失败：${error?.message || '请检查摄像头权限'}`
  } finally {
    scanStarting.value = false
  }
}

const openScannerDialog = async () => {
  showScannerDialog.value = true
  manualScanInput.value = ''
  scanError.value = ''

  if (!isCameraApiSupported()) {
    scanError.value = '当前浏览器不支持摄像头访问，请手动输入物料代码。'
    return
  }

  if (!isSecureCameraContext()) {
    scanError.value = '当前页面为 HTTP 非安全上下文，浏览器通常会禁用摄像头，请切换 HTTPS。'
    ElMessage.warning('HTTP 环境可能无法调起摄像头，请优先切换到 HTTPS。')
    return
  }

  await nextTick()
  await startScanner()
}

const confirmManualScan = () => {
  const manualValue = manualScanInput.value.trim()
  if (!manualValue) {
    ElMessage.warning('请输入物料代码')
    return
  }
  applyScannedValue(manualValue)
}

const handleScannerDialogClosed = () => {
  stopScanner()
  scanError.value = ''
  scanStarting.value = false
}

const totalProjects = computed(() => filteredProjects.value.length)

// 分页后的项目（用于表格显示）
const paginatedProjects = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredProjects.value.slice(start, end)
})

// 方法
const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleString('zh-CN')
}

const getStatusType = (status: string) => {
  const types = {
    completed: 'success',
    processing: 'warning', 
    failed: 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status: string) => {
  const texts = {
    completed: '已完成',
    processing: '处理中',
    failed: '失败'
  }
  return texts[status] || '未知'
}

const selectProject = (row: any) => {
  if (row.status === 'completed') {
    viewProject(row)
  }
}

const viewProject = async (project: any) => {
  if (project.status !== 'completed') {
    ElMessage.warning('项目尚未完成，无法查看说明书')
    return
  }

  // ✅ 如果项目数据已经存在，直接使用
  if (project.data) {
    localStorage.setItem('current_manual', JSON.stringify(project.data))
    router.push({ path: `/manual/${project.id}`, query: { source: 'viewer' } })
    return
  }

  // ✅ 如果没有数据，从后端API获取
  try {
    const loading = ElMessage({
      message: '正在加载说明书数据...',
      type: 'info',
      duration: 0
    })

    const response = await axios.get(`/api/manual/${project.id}`)
    const manualData = response.data

    loading.close()

    // 保存到 localStorage
    localStorage.setItem('current_manual', JSON.stringify(manualData))

    // 跳转到装配说明书页面
    router.push({ path: `/manual/${project.id}`, query: { source: 'viewer' } })
  } catch (error: any) {
    console.error('加载说明书失败:', error)
    ElMessage.error('加载说明书失败: ' + (error.response?.data?.detail || error.message))
  }
}

const deleteProject = async (project: any) => {
  try {
    await ElMessageBox.confirm(
      `确认删除任务「${project.projectName}」吗？删除后可重新上传生成。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )

    await axios.delete(`/api/manual/${project.id}`)
    if (localStorage.getItem(GENERATOR_LAST_TASK_KEY) === project.id) {
      localStorage.removeItem(GENERATOR_LAST_TASK_KEY)
    }
    if (localStorage.getItem(GENERATOR_RECOVERY_TASK_KEY) === project.id) {
      localStorage.removeItem(GENERATOR_RECOVERY_TASK_KEY)
    }
    ElMessage.success('删除成功')
    loadHistory()
  } catch (error: any) {
    if (error === 'cancel') return
    console.error('删除任务失败:', error)
    ElMessage.error('删除失败: ' + (error.response?.data?.detail || error.message))
  }
}

const handleClose = () => {
  router.push('/')
}

const handleSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1  // 切换每页数量时重置到第一页
}

const handleCurrentChange = (page: number) => {
  currentPage.value = page
}

// 监听过滤条件变化，重置到第一页
watch([searchQuery, statusFilter, dateRange], () => {
  currentPage.value = 1
})

// 生命周期
onMounted(() => {
  loading.value = true

  // ✅ 加载历史记录
  loadHistory()

  setTimeout(() => {
    loading.value = false
  }, 500)
})

onBeforeUnmount(() => {
  stopScanner()
})
</script>

<style lang="scss" scoped>
.viewer-page {
  min-height: 100vh;
  background: var(--el-bg-color-page);
  padding: 24px;
}

// 项目对话框
.project-dialog {
  :deep(.el-dialog) {
    border-radius: 16px;

    .el-dialog__header {
      background: var(--el-fill-color-lighter);
      border-radius: 16px 16px 0 0;
      padding: 24px;

      .el-dialog__title {
        font-size: 1.5rem;
        font-weight: 600;
      }
    }

    .el-dialog__body {
      padding: 0;
    }

    .el-dialog__footer {
      background: var(--el-fill-color-lighter);
      border-radius: 0 0 16px 16px;
      padding: 20px 24px;
    }
  }
}

.dialog-content {
  padding: 24px;
}

// 搜索区域
.search-section {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
  align-items: center;

  .search-input {
    flex: 1;
    max-width: 300px;
  }

  .scan-button {
    flex-shrink: 0;
  }

  .status-filter {
    width: 120px;
  }

  .date-picker {
    width: 240px;
  }
}

.scanner-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.scanner-video-wrapper {
  width: 100%;
  aspect-ratio: 1 / 1;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--el-border-color);
  background: #111;
}

.scanner-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.scanner-video-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  padding: 16px;
  text-align: center;
  font-size: 14px;
}

.scanner-tip {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

// 项目表格
.projects-section {
  .projects-table {
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);

    .project-name {
      display: flex;
      align-items: flex-start;
      gap: 8px;

      .project-icon {
        color: var(--el-color-primary);
        margin-top: 2px;
      }

      .project-name-text {
        display: block;
        line-height: 1.5;
        word-break: break-word;
        overflow-wrap: anywhere;
      }
    }

    .file-count {
      font-size: 12px;
      color: var(--el-text-color-secondary);
    }
  }

  // 移动端卡片布局
  .project-cards {
    display: flex;
    flex-direction: column;
    gap: 12px;

    .project-card {
      background: white;
      border-radius: 12px;
      padding: 16px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
      cursor: pointer;
      transition: all 0.2s ease;

      &:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
        transform: translateY(-2px);
      }

      &:active {
        transform: translateY(0);
      }

      .card-header {
        display: flex;
        align-items: flex-start;
        gap: 10px;
        margin-bottom: 12px;

        .card-icon {
          color: var(--el-color-primary);
          font-size: 20px;
          flex-shrink: 0;
          margin-top: 2px;
        }

        .card-title {
          font-size: 16px;
          font-weight: 600;
          line-height: 1.5;
          color: var(--el-text-color-primary);
          word-break: break-word;
          overflow-wrap: anywhere;
          flex: 1;
        }
      }

      .card-meta {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 12px;
        flex-wrap: wrap;

        .card-time {
          font-size: 12px;
          color: var(--el-text-color-secondary);
        }
      }

      .card-actions {
        display: flex;
        justify-content: flex-end;

        .el-button {
          min-width: auto;
        }
      }
    }
  }

  .pagination-section {
    margin-top: 24px;
    display: flex;
    justify-content: center;
  }
}

// 空状态
.empty-state {
  text-align: center;
  padding: 60px 20px;
}

// 项目预览
.project-preview {
  max-width: 1200px;
  margin: 0 auto;

  .preview-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 32px;

    h2 {
      margin: 0;
      font-size: 2rem;
      font-weight: 600;
      color: var(--el-text-color-primary);
    }
  }

  .preview-content {
    .stats-cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 24px;
      margin-bottom: 40px;

      .stat-card {
        background: var(--el-bg-color);
        border-radius: 16px;
        padding: 32px;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;

        &:hover {
          transform: translateY(-4px);
          box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
        }

        .stat-value {
          font-size: 2.5rem;
          font-weight: 700;
          color: var(--el-color-primary);
          margin-bottom: 8px;
        }

        .stat-label {
          color: var(--el-text-color-secondary);
          font-size: 14px;
        }
      }
    }

    .recent-projects {
      background: var(--el-bg-color);
      border-radius: 16px;
      padding: 32px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);

      h3 {
        margin: 0 0 24px 0;
        font-size: 1.3rem;
        font-weight: 600;
        color: var(--el-text-color-primary);
      }

      .recent-list {
        .recent-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px;
          border-radius: 12px;
          margin-bottom: 12px;
          cursor: pointer;
          transition: all 0.3s ease;

          &:hover {
            background: var(--el-fill-color-lighter);
          }

          &:last-child {
            margin-bottom: 0;
          }

          .recent-info {
            .recent-name {
              font-weight: 500;
              color: var(--el-text-color-primary);
              margin-bottom: 4px;
            }

            .recent-time {
              font-size: 12px;
              color: var(--el-text-color-secondary);
            }
          }
        }
      }
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .viewer-page {
    padding: 12px;
  }

  .project-dialog {
    :deep(.el-dialog) {
      width: calc(100vw - 16px) !important;
      max-width: none;
      margin: 8px auto !important;
      border-radius: 16px;
    }

    :deep(.el-dialog__header) {
      padding: 18px 16px 14px;
    }

    :deep(.el-dialog__body) {
      padding: 0 16px 16px;
    }

    :deep(.el-dialog__footer) {
      padding: 14px 16px;
    }
  }

  .dialog-content {
    padding: 0;
  }

  .search-section {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 10px;
    margin-bottom: 16px;

    .search-input {
      flex: 1;
      max-width: none;
    }

    .scan-button {
      flex-shrink: 0;
      width: auto;
    }

    .status-filter,
    .date-picker {
      display: none;
    }
  }

  .projects-section {
    overflow-x: visible;

    .project-cards {
      gap: 12px;
    }
  }

  .projects-table {
    min-width: 100%;
    box-shadow: none;
  }

  .projects-table :deep(.el-table__cell) {
    padding: 14px 8px;
  }

  .projects-table :deep(.cell) {
    padding: 0;
  }

  .pagination-section :deep(.el-pagination) {
    justify-content: center;
    flex-wrap: wrap;
    gap: 6px;
  }

  .preview-header {
    flex-direction: column;
    gap: 16px;
    text-align: center;

    h2 {
      font-size: 1.5rem;
    }
  }

  .stats-cards {
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;

    .stat-card {
      padding: 20px;

      .stat-value {
        font-size: 2rem;
      }
    }
  }
}
</style>
