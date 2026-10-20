// 成果看板的只读统计：按现有查看器可见范围派生，取消/身份切换不会回填旧数据。
// 不把文件更新时间或说明书步骤解释成生产完成量。-codex，2026-10-09
import { computed, onBeforeUnmount, ref, shallowRef, watch, type Ref } from 'vue'
import axios from 'axios'
import api from '../../api'
import { useAdminStore } from '../../stores/admin'
import { PROJECT_CATEGORY_VALUES, PROJECT_CATEGORY_PUBLISHED, PROJECT_CATEGORY_PENDING, PROJECT_CATEGORY_ARCHIVED, type ProjectCategory } from '../../constants/projectCategories'

export interface ManualSummary { id: string; name: string; category: ProjectCategory; updatedAt: number | null; assemblySteps: number | null; drawingPages: number | null }
const metric = (value: unknown): number | null => typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? value : null

function parseManuals(payload: unknown): ManualSummary[] {
  if (!payload || typeof payload !== 'object' || !('manuals' in payload) || !Array.isArray(payload.manuals)) throw new Error('统计接口返回的数据格式不正确')
  const result: ManualSummary[] = []
  for (const item of payload.manuals) {
    if (!item || typeof item !== 'object') throw new Error('项目数据格式不正确')
    const row = item as Record<string, unknown>
    if (row.status !== 'completed') continue
    const category = PROJECT_CATEGORY_VALUES.find(value => value === row.projectCategory)
    if (typeof row.taskId !== 'string' || !row.taskId || !category) throw new Error('项目统计字段不完整')
    const timestamp = typeof row.timestamp === 'string' ? Date.parse(row.timestamp) : NaN
    result.push({ id: row.taskId, name: typeof row.productName === 'string' ? row.productName : '未命名项目', category, updatedAt: Number.isFinite(timestamp) ? timestamp : null,
      assemblySteps: metric(row.assemblyStepCount), drawingPages: metric(row.referencedDrawingPageCount) })
  }
  return result
}

export function useFactoryStats(enabled: Readonly<Ref<boolean>>) {
  const admin = useAdminStore()
  admin.ensureInit()
  // 复用应用基础地址，但不用全局错误弹窗：正常取消请求应静默，真正失败在看板内呈现。
  const client = axios.create({ baseURL: api.defaults.baseURL, timeout: 20000 })
  const records = shallowRef<ManualSummary[] | null>(null)
  const loading = ref(false)
  const error = ref('')
  const loadedAt = ref('')
  let request: AbortController | undefined
  let generation = 0

  const isAdmin = computed(() => admin.isAdmin)
  const visible = computed(() => records.value?.filter(item => isAdmin.value || item.category === PROJECT_CATEGORY_PUBLISHED).sort((a, b) => (b.updatedAt ?? 0) - (a.updatedAt ?? 0)) ?? null)
  const counts = computed(() => {
    if (!visible.value) return null
    const rows = visible.value
    return { total: rows.length, published: rows.filter(row => row.category === PROJECT_CATEGORY_PUBLISHED).length,
      pending: rows.filter(row => row.category === PROJECT_CATEGORY_PENDING).length,
      archived: rows.filter(row => row.category === PROJECT_CATEGORY_ARCHIVED).length }
  })
  const metrics = computed(() => {
    if (!visible.value) return null
    const rows = visible.value
    return {
      assemblySteps: rows.every(row => row.assemblySteps !== null) ? rows.reduce((sum, row) => sum + row.assemblySteps!, 0) : null,
      drawingPages: rows.every(row => row.drawingPages !== null) ? rows.reduce((sum, row) => sum + row.drawingPages!, 0) : null,
    }
  })
  const recent = computed(() => visible.value?.slice(0, 3) ?? [])

  // 图表与总量复用同批可见项目；分类内只要有缺失摘要就显示未知，不拿已知小计冒充总量。-codex，2026-10-12
  const categoryMetrics = computed(() => {
    if (!visible.value) return null
    return Object.fromEntries(PROJECT_CATEGORY_VALUES.map(category => {
      const rows = visible.value!.filter(row => row.category === category)
      return [category, {
        assemblySteps: rows.every(row => row.assemblySteps !== null) ? rows.reduce((sum, row) => sum + row.assemblySteps!, 0) : null,
        drawingPages: rows.every(row => row.drawingPages !== null) ? rows.reduce((sum, row) => sum + row.drawingPages!, 0) : null,
      }]
    })) as Record<ProjectCategory, { assemblySteps: number | null; drawingPages: number | null }>
  })
  const stepDistribution = computed(() => {
    if (!visible.value) return null
    const ranges = [
      { label: '1–20 步', min: 1, max: 20 },
      { label: '21–50 步', min: 21, max: 50 },
      { label: '51–80 步', min: 51, max: 80 },
      { label: '81 步及以上', min: 81, max: Infinity },
    ]
    // 零步骤和未知不能塞入1–20档；保留对账数量，让四档未覆盖的项目显式可见。-codex，2026-10-12
    return {
      bins: ranges.map(range => ({ label: range.label, count: visible.value!.filter(row => row.assemblySteps !== null && row.assemblySteps >= range.min && row.assemblySteps <= range.max).length })),
      unknown: visible.value.filter(row => row.assemblySteps === null).length,
      zero: visible.value.filter(row => row.assemblySteps === 0).length,
    }
  })

  async function refresh() {
    const current = ++generation
    request?.abort()
    records.value = null
    error.value = ''
    loadedAt.value = ''
    loading.value = enabled.value
    if (!enabled.value) return
    const controller = new AbortController()
    request = controller
    try {
      const response = await client.get<unknown>('/manuals', { signal: controller.signal })
      const parsed = parseManuals(response.data)
      if (controller.signal.aborted || current !== generation) return
      records.value = parsed
      loadedAt.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
    } catch (cause) {
      if (controller.signal.aborted || current !== generation) return
      error.value = axios.isAxiosError(cause) && cause.code === 'ECONNABORTED' ? '读取超时，请重试' : '暂时无法读取项目统计，请重试'
    } finally {
      if (current === generation) loading.value = false
    }
  }
  // 同步清空身份关联结果，避免退出后的单帧仍出现管理员项目；迟到响应另由generation隔离。
  watch([enabled, () => admin.isAdmin], () => { void refresh() }, { immediate: true, flush: 'sync' })
  onBeforeUnmount(() => { generation++; request?.abort() })
  return { counts, metrics, categoryMetrics, stepDistribution, recent, visible, loading, error, loadedAt, isAdmin, refresh }
}
