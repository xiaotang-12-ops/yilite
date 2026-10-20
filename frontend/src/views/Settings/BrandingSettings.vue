<script setup lang="ts">
// 名称草稿仅在本面板预览，避免未保存输入污染首页和导航。-codex，2026-10-10
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { brandingError, DEFAULT_BRANDING, useBrandingStore } from '@/stores/branding'

const store = useBrandingStore()
const draft = ref({ ...DEFAULT_BRANDING })
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const saveUncertain = ref(false)

async function reload() {
  loading.value = true
  await store.load(true)
  if (!store.loadError) {
    draft.value = { ...store.branding }
    error.value = ''
    saveUncertain.value = false
  }
  loading.value = false
}

async function save() {
  if (loading.value || saving.value || store.loadError) return
  saveUncertain.value = false
  error.value = brandingError(draft.value)
  if (error.value) return
  saving.value = true
  try {
    await store.save({ ...draft.value })
    draft.value = { ...store.branding }
    ElMessage.success('名称已保存，页面展示已更新')
  } catch {
    // 网络响应丢失时服务端可能已保存；保留草稿，并让用户明确重读确认。-codex，2026-10-10
    saveUncertain.value = true
    error.value = '未能确认保存结果。可重新读取已保存名称核对，或重试保存。'
  } finally { saving.value = false }
}

function onKey(event: KeyboardEvent, multiline = false) {
  if (event.isComposing || event.keyCode === 229 || event.key !== 'Enter') return
  if (multiline && !event.ctrlKey && !event.metaKey) return
  event.preventDefault()
  void save()
}
onMounted(reload)
</script>

<template>
  <section class="branding-settings" aria-labelledby="branding-heading">
    <el-divider content-position="left"><span id="branding-heading">平台展示名称</span></el-divider>
    <el-alert v-if="store.loadError" :title="store.loadError" type="error" :closable="false">
      <el-button size="small" :loading="loading" @click="reload">重新读取</el-button>
    </el-alert>
    <el-alert v-if="store.warning" :title="store.warning" type="warning" :closable="false" />
    <div class="branding-grid" v-loading="loading">
      <el-form label-position="top" :disabled="loading || saving || !!store.loadError" @submit.prevent="save">
        <el-form-item label="平台名称">
          <el-input v-model="draft.platform_name" aria-label="平台名称" placeholder="例如：装配指导" @keydown="onKey($event)" />
          <p class="field-tip">顶部与浏览器标签使用，最多 24 字；回车保存。</p>
        </el-form-item>
        <el-form-item label="首页标题">
          <el-input v-model="draft.home_title" aria-label="首页标题" type="textarea" :rows="3" placeholder="例如：装配指导" @keydown="onKey($event, true)" />
          <p class="field-tip">最多 60 字、3 行；回车换行，Ctrl + Enter 保存。</p>
        </el-form-item>
        <el-form-item label="看板标题">
          <el-input v-model="draft.dashboard_title" aria-label="看板标题" type="textarea" :rows="2" placeholder="例如：装配成果总览" @keydown="onKey($event, true)" />
          <p class="field-tip">厂区成果看板使用，最多 24 字、2 行；回车换行，Ctrl + Enter 保存。</p>
        </el-form-item>
        <p v-if="error" class="save-error" role="alert">{{ error }}</p>
        <el-button v-if="saveUncertain" @click="reload">重新读取已保存名称（替换草稿）</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存名称</el-button>
      </el-form>
      <div class="branding-preview" aria-label="名称即时预览">
        <div class="preview-caption">即时预览 · 保存后生效</div>
        <div class="preview-nav"><img src="/logo.png" alt="品牌 Logo" /><div><strong>{{ draft.platform_name || '平台名称' }}</strong><small>Assembly Instructions</small></div></div>
        <div class="preview-home">{{ draft.home_title || '首页标题' }}</div>
        <div class="preview-caption">厂区成果看板</div>
        <div class="preview-dashboard">{{ draft.dashboard_title || '看板标题' }}</div>
        <p class="field-tip">预览字体与布局仅供参考，实际页面会随窗口宽度调整。</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.branding-settings { margin-bottom: 28px; }
.branding-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 32px; padding-top: 12px; }
.field-tip { margin: 6px 0 0; color: var(--el-text-color-secondary); font-size: 12px; line-height: 1.6; }
.branding-preview { border: 1px solid var(--el-border-color-light); border-radius: 12px; padding: 20px; background: var(--el-fill-color-extra-light); min-width: 0; }
.preview-caption { color: var(--el-text-color-secondary); font-size: 12px; margin-bottom: 20px; }
.preview-nav { display: flex; gap: 12px; align-items: center; }
.preview-nav img { width: 48px; object-fit: contain; }
.preview-nav > div { min-width: 0; }
.preview-nav strong { display: block; overflow-wrap: anywhere; }
.preview-nav small { color: var(--el-text-color-secondary); font-size: 11px; }
.preview-home { white-space: pre-wrap; overflow-wrap: anywhere; font-size: clamp(24px, 3vw, 38px); font-weight: 900; line-height: 1.15; margin: 32px 0; color: var(--el-color-primary); }
.preview-dashboard { white-space: pre-wrap; overflow-wrap: anywhere; font-size: 26px; font-weight: 700; line-height: 1.3; margin-bottom: 20px; }
.save-error { color: var(--el-color-danger); font-size: 13px; }
@media (max-width: 700px) { .branding-grid { grid-template-columns: 1fr; gap: 16px; } }
</style>
