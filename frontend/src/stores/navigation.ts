// 管理员顶栏显示是公开应用配置；保存确认后更新，草稿不影响菜单。-codex，2026-10-12
import { ref } from 'vue'
import { defineStore } from 'pinia'
import axios from 'axios'

export interface NavigationVisibility { home: boolean; generator: boolean; viewer: boolean; factory: boolean }
export const NAVIGATION_ITEMS: { key: keyof NavigationVisibility; label: string }[] = [
  { key: 'home', label: '首页' }, { key: 'generator', label: '生成器' },
  { key: 'viewer', label: '查看器' }, { key: 'factory', label: '厂区模型' }
]
export const DEFAULT_NAVIGATION: NavigationVisibility = { home: true, generator: true, viewer: true, factory: true }
const endpoint = `${(import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')}/navigation`

export const useNavigationStore = defineStore('navigation', () => {
  const visible = ref<NavigationVisibility>({ ...DEFAULT_NAVIGATION })
  const loaded = ref(false)
  const loadError = ref('')
  const warning = ref('')
  let pending: Promise<void> | undefined

  function apply(data: { navigation: NavigationVisibility; warning?: string }) {
    if (!data.navigation || NAVIGATION_ITEMS.some(item => typeof data.navigation[item.key] !== 'boolean')) {
      throw new Error('菜单接口返回格式无效')
    }
    visible.value = { ...data.navigation }
    warning.value = data.warning || ''
    loadError.value = ''
    loaded.value = true
  }

  async function load(force = false) {
    if (pending) return pending
    if (loaded.value && !force) return
    pending = (async () => {
      try { apply((await axios.get(endpoint, { timeout: 10000 })).data) }
      catch { loadError.value = '菜单配置读取失败，请重试后编辑。' }
      finally { pending = undefined }
    })()
    return pending
  }

  async function save(value: NavigationVisibility) {
    const { data } = await axios.put(endpoint, value, { timeout: 10000 })
    apply(data)
  }

  return { visible, loaded, loadError, warning, load, save }
})
