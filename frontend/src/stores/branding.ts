// 应用公开名称与编辑草稿隔离；只有服务端确认保存才更新全局名称。-codex，2026-10-10
import { ref } from 'vue'
import { defineStore } from 'pinia'
import axios from 'axios'

export interface Branding { platform_name: string; home_title: string; dashboard_title: string }
export const DEFAULT_BRANDING: Branding = { platform_name: '装配指导', home_title: '装配指导', dashboard_title: '装配成果总览' }
const endpoint = `${(import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')}/branding`

export function brandingError(value: Branding): string {
  const platform = value.platform_name.trim()
  const title = value.home_title.trim()
  const dashboard = value.dashboard_title.trim()
  if (!platform || !title || !dashboard) return '名称和标题不能为空'
  if (Array.from(dashboard).length > 24) return '看板标题最多 24 个字符'
  if (dashboard.replace(/\r\n?/g, '\n').split('\n').length > 2) return '看板标题最多 2 行'
  if (Array.from(platform).length > 24) return '平台名称最多 24 个字符'
  if (Array.from(title).length > 60) return '首页标题最多 60 个字符'
  if (/[\r\n]/.test(platform)) return '平台名称仅支持单行'
  if (title.replace(/\r\n?/g, '\n').split('\n').length > 3) return '首页标题最多 3 行'
  if (/[\u0000-\u0009\u000b-\u001f]/.test(platform + title + dashboard)) return '名称不能包含控制字符'
  return ''
}

export const useBrandingStore = defineStore('branding', () => {
  const branding = ref<Branding>({ ...DEFAULT_BRANDING })
  const loaded = ref(false)
  const loadError = ref('')
  const warning = ref('')
  let pending: Promise<void> | undefined

  function apply(data: { branding: Branding; warning?: string }) {
    if (!data.branding || typeof data.branding.platform_name !== 'string' ||
        typeof data.branding.home_title !== 'string' || typeof data.branding.dashboard_title !== 'string' || brandingError(data.branding)) {
      throw new Error('名称接口返回格式无效')
    }
    branding.value = { ...data.branding }
    warning.value = data.warning || ''
    document.title = branding.value.platform_name
    loaded.value = true
    loadError.value = ''
  }

  async function load(force = false) {
    if (pending) return pending
    if (loaded.value && !force) return
    pending = (async () => {
      try { apply((await axios.get(endpoint, { timeout: 10000 })).data) }
      catch { loadError.value = '名称配置读取失败，请重试后编辑。' }
      finally { pending = undefined }
    })()
    return pending
  }

  async function save(value: Branding) {
    const error = brandingError(value)
    if (error) throw new Error(error)
    const { data } = await axios.put(endpoint, value, { timeout: 10000 })
    apply(data)
  }

  return { branding, loaded, loadError, warning, load, save }
})
