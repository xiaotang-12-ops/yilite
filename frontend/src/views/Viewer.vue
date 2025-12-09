<template>
  <div class="viewer-page">
    <!-- 项目历史选择对话框 -->
    <el-dialog
      v-model="showProjectDialog"
      title="选择项目"
      width="80%"
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
          <el-table
            :data="filteredProjects"
            @row-click="selectProject"
            highlight-current-row
            class="projects-table"
            v-loading="loading"
          >
            <el-table-column prop="projectName" label="项目名称" min-width="200">
              <template #default="{ row }">
                <div class="project-name">
                  <el-icon class="project-icon"><Document /></el-icon>
                  <span>{{ row.projectName }}</span>
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
            
            <el-table-column label="操作" width="200">
              <template #default="{ row }">
                <el-button
                  type="primary"
                  size="small"
                  @click.stop="viewProject(row)"
                  :disabled="row.status !== 'completed'"
                >
                  <el-icon><View /></el-icon>
                  查看说明书
                </el-button>
                <el-button
                  type="danger"
                  size="small"
                  @click.stop="deleteProject(row)"
                  plain
                >
                  <el-icon><Delete /></el-icon>
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          
          <!-- 分页 -->
          <div class="pagination-section">
            <el-pagination
              v-model:current-page="currentPage"
              v-model:page-size="pageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="totalProjects"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="handleSizeChange"
              @current-change="handleCurrentChange"
            />
          </div>
        </div>
        
        <!-- 空状态 -->
        <div v-if="filteredProjects.length === 0 && !loading" class="empty-state">
          <el-empty description="暂无项目数据">
            <el-button type="primary" @click="$router.push('/generator')">
              创建新项目
            </el-button>
          </el-empty>
        </div>
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="handleClose">取消</el-button>
          <el-button type="primary" @click="$router.push('/generator')">
            <el-icon><Plus /></el-icon>
            新建项目
          </el-button>
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
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMediaQuery } from '@vueuse/core'
import {
  Search, Document, View, Delete, Plus, FolderOpened
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

const router = useRouter()
const isMobile = useMediaQuery('(max-width: 768px)')

// 响应式数据
const showProjectDialog = ref(true)
const loading = ref(false)
const searchQuery = ref('')
const statusFilter = ref('')
const dateRange = ref([])
const currentPage = ref(1)
const pageSize = ref(20)

// ✅ 从 localStorage 加载项目数据
const projects = ref<any[]>([])

// 加载历史记录
const loadHistory = async () => {
  try {
    // ✅ 优先从后端API获取所有已生成的说明书
    try {
      const response = await axios.get('/api/manuals')
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
        description: `装配步骤: ${item.stepCount || 0} 个`
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
  return projects.value
    .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
    .slice(0, 5)
})

// 过滤后的项目
const filteredProjects = computed(() => {
  let filtered = projects.value
  
  // 搜索过滤
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(p => 
      p.projectName.toLowerCase().includes(query) ||
      p.description.toLowerCase().includes(query)
    )
  }
  
  // 状态过滤
  if (statusFilter.value) {
    filtered = filtered.filter(p => p.status === statusFilter.value)
  }
  
  // 日期过滤
  if (dateRange.value && dateRange.value.length === 2) {
    const [start, end] = dateRange.value
    filtered = filtered.filter(p => {
      const date = new Date(p.createdAt)
      return date >= start && date <= end
    })
  }
  
  return filtered
})

const totalProjects = computed(() => filteredProjects.value.length)

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
    router.push(`/manual/${project.id}`)
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
    router.push(`/manual/${project.id}`)
  } catch (error: any) {
    console.error('加载说明书失败:', error)
    ElMessage.error('加载说明书失败: ' + (error.response?.data?.detail || error.message))
  }
}

const deleteProject = async (project: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除项目"${project.projectName}"吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    // ✅ 调用后端API删除服务器文件
    try {
      await axios.delete(`/api/manual/${project.id}`)
      console.log(`✅ 服务器文件删除成功: ${project.id}`)
    } catch (apiError: any) {
      console.error('删除服务器文件失败:', apiError)
      ElMessage.error('删除服务器文件失败: ' + (apiError.response?.data?.detail || apiError.message))
      return
    }

    // ✅ 从 localStorage 删除项目
    const historyKey = 'assembly_manual_history'
    const stored = localStorage.getItem(historyKey)

    if (stored) {
      let history = JSON.parse(stored)
      history = history.filter((item: any) => item.taskId !== project.id)
      localStorage.setItem(historyKey, JSON.stringify(history))
    }

    // 如果当前查看的是被删除的项目，也清除current_manual
    const currentManual = localStorage.getItem('current_manual')
    if (currentManual) {
      const current = JSON.parse(currentManual)
      if (current.metadata?.task_id === project.id) {
        localStorage.removeItem('current_manual')
      }
    }

    // 从列表中删除
    const index = projects.value.findIndex(p => p.id === project.id)
    if (index > -1) {
      projects.value.splice(index, 1)
      ElMessage.success('项目删除成功')
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('删除项目失败:', error)
      ElMessage.error('删除失败: ' + (error.response?.data?.detail || error.message || '未知错误'))
    }
  }
}

const handleClose = () => {
  router.push('/')
}

const handleSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
}

const handleCurrentChange = (page: number) => {
  currentPage.value = page
}

// 生命周期
onMounted(() => {
  loading.value = true

  // ✅ 加载历史记录
  loadHistory()

  setTimeout(() => {
    loading.value = false
  }, 500)
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

  .status-filter {
    width: 120px;
  }

  .date-picker {
    width: 240px;
  }
}

// 项目表格
.projects-section {
  .projects-table {
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);

    .project-name {
      display: flex;
      align-items: center;
      gap: 8px;

      .project-icon {
        color: var(--el-color-primary);
      }
    }

    .file-count {
      font-size: 12px;
      color: var(--el-text-color-secondary);
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
  .search-section {
    flex-direction: column;
    align-items: stretch;

    .search-input,
    .status-filter,
    .date-picker {
      width: 100%;
      max-width: none;
    }
  }

  .projects-section {
    overflow-x: auto;

    :deep(.el-table__body-wrapper) {
      overflow-x: auto;
    }
  }

  .projects-table {
    min-width: 720px;
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
