<script setup lang="ts">
// 本面板只提交菜单配置，保持AI设置与名称设置的保存流程独立。-codex，2026-10-12
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { DEFAULT_NAVIGATION, NAVIGATION_ITEMS, useNavigationStore } from '@/stores/navigation'

const store = useNavigationStore()
const draft = ref({ ...DEFAULT_NAVIGATION })
const loading = ref(true)
const saving = ref(false)
const error = ref('')

async function reload() {
  loading.value = true
  await store.load(true)
  if (!store.loadError) {
    draft.value = { ...store.visible }
    error.value = ''
  }
  loading.value = false
}

async function save() {
  if (loading.value || saving.value || store.loadError) return
  saving.value = true
  error.value = ''
  try {
    await store.save({ ...draft.value })
    draft.value = { ...store.visible }
    ElMessage.success('菜单显示已保存，其他电脑刷新后生效')
  } catch {
    // 响应丢失不代表服务端未保存，保留草稿并允许重新读取核对。-codex，2026-10-12
    error.value = '未能确认保存结果，草稿已保留。可重新读取已保存配置核对，或重试保存。'
  } finally { saving.value = false }
}

onMounted(reload)
</script>

<template>
  <section class="navigation-settings" aria-labelledby="navigation-heading">
    <el-divider content-position="left"><span id="navigation-heading">管理员菜单显示</span></el-divider>
    <p class="navigation-tip">控制管理员登录后顶部菜单的显示。隐藏入口仍可通过网址访问；普通用户菜单保持原样。</p>
    <el-alert v-if="store.loadError" :title="store.loadError" type="error" :closable="false" />
    <el-alert v-if="store.warning" :title="store.warning" type="warning" :closable="false" />
    <el-form class="navigation-form" label-width="100px" :disabled="loading || saving || !!store.loadError" @submit.prevent="save">
      <el-form-item v-for="item in NAVIGATION_ITEMS" :key="item.key" :label="item.label">
        <el-switch v-model="draft[item.key]" :aria-label="`${item.label}菜单显示`" inline-prompt active-text="显示" inactive-text="隐藏" />
      </el-form-item>
      <el-button type="primary" :loading="saving" :disabled="loading || !!store.loadError" @click="save">保存菜单显示</el-button>
    </el-form>
    <el-button class="reload-button" :loading="loading" :disabled="saving" @click="reload">重新读取已保存配置</el-button>
    <p v-if="error" class="navigation-error" role="alert">{{ error }}</p>
    <p class="navigation-tip">所有电脑共用此配置，其他电脑刷新页面后生效。即使全部隐藏，仍可长按左上角品牌 5 秒进入设置恢复。</p>
  </section>
</template>

<style scoped>
.navigation-settings { margin-bottom: 28px; }
.navigation-form { margin: 20px 0 12px; }
.navigation-tip { color: var(--text-secondary, #64748b); line-height: 1.6; font-size: 13px; }
.navigation-error { color: var(--el-color-danger); line-height: 1.6; }
.reload-button { margin-bottom: 8px; }
</style>
