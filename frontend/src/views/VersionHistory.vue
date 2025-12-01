<template>
  <div class="version-history-page">
    <el-page-header content="装配手册历史版本" @back="goBack" />

    <el-card class="history-card" shadow="hover">
      <div class="header-row">
        <div>
          <h2>任务 {{ taskId }}</h2>
          <p class="current-version">当前版本：{{ history.current_version || '无' }}</p>
        </div>
        <el-button type="primary" :loading="loading" @click="loadHistory">刷新</el-button>
      </div>

      <el-timeline v-if="history.versions.length">
        <el-timeline-item
          v-for="item in history.versions"
          :key="item.version"
          :timestamp="item.published_at"
          :type="item.version === history.current_version ? 'primary' : 'info'"
        >
          <div class="version-item">
            <div class="title-row">
              <div class="left">
                <el-tag v-if="item.version === history.current_version" type="success" size="small">当前</el-tag>
                <strong>{{ item.version }}</strong>
              </div>
              <div class="actions">
                <el-button size="small" @click="preview(item.version)">预览</el-button>
                <el-button size="small" type="warning" @click="rollback(item.version)">回滚</el-button>
              </div>
            </div>
            <p class="changelog">{{ item.changelog || '无变更说明' }}</p>
            <p class="meta">发布于 {{ item.published_at || '-' }} · 来源 {{ item.source || 'publish' }}</p>
          </div>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-else description="暂无历史版本" />
    </el-card>

    <el-dialog v-model="showPreview" title="版本预览" width="70%">
      <div v-if="previewData">
        <p class="preview-meta">
          版本：{{ previewVersion }} · 组件章节：{{ previewData.component_assembly?.length || 0 }} · 产品步骤：{{ previewData.product_assembly?.steps?.length || 0 }}
        </p>
        <el-scrollbar height="480px">
          <pre class="preview-json">{{ formatJson(previewData) }}</pre>
        </el-scrollbar>
      </div>
      <template #footer>
        <el-button @click="showPreview = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

const route = useRoute()
const router = useRouter()
const taskId = route.params.taskId as string

const history = ref<{ current_version: string | null; versions: any[] }>({
  current_version: null,
  versions: []
})
const loading = ref(false)
const showPreview = ref(false)
const previewVersion = ref('')
const previewData = ref<any>(null)

const formatJson = (data: any) => JSON.stringify(data, null, 2)

const loadHistory = async () => {
  if (!taskId) {
    ElMessage.error('任务ID不存在')
    return
  }
  try {
    loading.value = true
    const resp = await axios.get(`/api/manual/${taskId}/history`)
    history.value = resp.data
  } catch (error: any) {
    console.error('❌ 获取历史失败', error)
    ElMessage.error('获取历史失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const preview = async (version: string) => {
  try {
    const resp = await axios.get(`/api/manual/${taskId}/version/${version}`)
    previewData.value = resp.data
    previewVersion.value = version
    showPreview.value = true
  } catch (error: any) {
    console.error('❌ 预览失败', error)
    ElMessage.error('预览失败: ' + (error.response?.data?.detail || error.message))
  }
}

const rollback = async (version: string) => {
  try {
    const { value: changelog } = await ElMessageBox.prompt(
      `确认回滚到版本 ${version} 吗？回滚会生成新版本。`,
      '确认回滚',
      { confirmButtonText: '回滚', cancelButtonText: '取消', inputPlaceholder: '请输入回滚说明（可选）', inputValue: `回滚到 ${version}` }
    )

    const resp = await axios.post(`/api/manual/${taskId}/rollback/${version}`, { changelog })
    ElMessage.success(`回滚成功，新版本: ${resp.data.version}`)
    await loadHistory()
  } catch (error: any) {
    if (error === 'cancel') return
    console.error('❌ 回滚失败', error)
    ElMessage.error('回滚失败: ' + (error.response?.data?.detail || error.message))
  }
}

const goBack = () => {
  router.back()
}

onMounted(() => {
  loadHistory()
})
</script>

<style scoped>
.version-history-page {
  padding: 16px;
}

.history-card {
  margin-top: 12px;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.current-version {
  margin: 4px 0 0;
  color: #666;
}

.version-item {
  padding: 12px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.title-row .left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.changelog {
  margin: 8px 0;
  color: #333;
}

.meta {
  margin: 0;
  color: #999;
  font-size: 12px;
}

.actions {
  display: flex;
  gap: 8px;
}

.preview-json {
  background: #0b1021;
  color: #e5e7eb;
  padding: 12px;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.5;
}

.preview-meta {
  margin-bottom: 8px;
  color: #666;
}
</style>
