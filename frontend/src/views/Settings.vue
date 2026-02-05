<template>
  <div class="settings-container">
    <el-card class="settings-card">
      <template #header>
        <div class="card-header">
          <el-icon><Setting /></el-icon>
          <span>系统设置</span>
        </div>
      </template>

      <el-form :model="settings" label-width="150px" label-position="left">
        <!-- API密钥配置 -->
        <el-divider content-position="left">
          <el-icon><Key /></el-icon>
          <span style="margin-left: 8px;">API密钥配置</span>
        </el-divider>

        <el-form-item label="OpenRouter API Key">
          <el-input
            v-model="settings.openrouterApiKey"
            type="password"
            show-password
            placeholder="请输入OpenRouter API Key"
            clearable
          >
            <template #prepend>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
          <div class="form-item-tip">
            视觉调用点使用OpenRouter，
            <el-link type="primary" href="https://openrouter.ai/keys" target="_blank">
              获取API Key
            </el-link>
          </div>
        </el-form-item>
        <el-form-item label="DeepSeek API Key">
          <el-input
            v-model="settings.deepseekApiKey"
            type="password"
            show-password
            placeholder="请输入DeepSeek API Key"
            clearable
          >
            <template #prepend>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
          <div class="form-item-tip">
            DeepSeek用于文本类调用点（匹配/安全）
          </div>
        </el-form-item>
        <el-form-item label="豆包(ARK) API Key">
          <el-input
            v-model="settings.doubaoApiKey"
            type="password"
            show-password
            placeholder="请输入豆包(ARK) API Key"
            clearable
          >
            <template #prepend>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
          <div class="form-item-tip">
            豆包用于视觉/文本调用点，
            <el-link type="primary" href="https://console.volcengine.com/ark" target="_blank">
              获取API Key
            </el-link>
          </div>
        </el-form-item>

        <!-- 模型配置 -->
        <el-divider content-position="left">
          <el-icon><Cpu /></el-icon>
          <span style="margin-left: 8px;">调用点模型配置</span>
        </el-divider>

        <el-form-item label="调用点">
          <div class="callpoint-config">
            <div
              v-for="callPointId in callPointOrder"
              :key="callPointId"
              class="callpoint-item"
            >
              <div class="callpoint-row">
                <div class="callpoint-label">{{ settings.callPoints[callPointId].label }}</div>
                <el-select
                  v-model="settings.callPoints[callPointId].provider"
                  class="callpoint-provider"
                  placeholder="提供方"
                  :disabled="settings.callPoints[callPointId].allowedProviders.length === 1"
                  @change="handleProviderChange(callPointId)"
                >
                  <el-option
                    v-for="provider in settings.callPoints[callPointId].allowedProviders"
                    :key="provider"
                    :label="providerLabels[provider]"
                    :value="provider"
                  />
                </el-select>
                <el-input
                  v-model="settings.callPoints[callPointId].model"
                  class="callpoint-model"
                  placeholder="模型ID"
                  clearable
                />
                <el-select
                  v-if="settings.callPoints[callPointId].provider === 'doubao'"
                  v-model="modelPresetSelections[callPointId]"
                  class="callpoint-model-preset"
                  placeholder="快捷模型"
                  clearable
                  @change="applyModelPreset(callPointId, $event)"
                >
                  <el-option
                    v-for="preset in modelPresets"
                    :key="preset.value"
                    :label="preset.label"
                    :value="preset.value"
                  />
                </el-select>
              </div>
              <!-- 新增：独立Key输入框（第二行） -->
              <div class="callpoint-key-row">
                <el-input
                  v-model="settings.callPoints[callPointId].customKey"
                  class="callpoint-custom-key"
                  type="password"
                  placeholder="独立Key（可选，留空则使用上方对应提供方的默认Key）"
                  show-password
                  clearable
                >
                  <template #prepend>
                    <el-icon><Key /></el-icon>
                  </template>
                </el-input>
              </div>
            </div>
          </div>
          <div class="form-item-tip">
            视觉调用点支持OpenRouter/豆包；文本调用点可选OpenRouter/DeepSeek/豆包
            <el-link type="primary" href="https://openrouter.ai/models" target="_blank">
              OpenRouter模型列表
            </el-link>
            <br />
            💡 如果某个调用点需要不同的Key（如NewAPI中不同渠道的Key），请填写"独立Key"
          </div>
        </el-form-item>

        <!-- 系统配置 -->
        <el-divider content-position="left">
          <el-icon><Tools /></el-icon>
          <span style="margin-left: 8px;">系统配置</span>
        </el-divider>

        <el-form-item label="WebSocket地址">
          <el-input
            v-model="settings.websocketUrl"
            placeholder="ws://localhost:8008"
            clearable
          >
            <template #prepend>
              <el-icon><Connection /></el-icon>
            </template>
          </el-input>
          <div class="form-item-tip">
            WebSocket服务器地址，用于实时进度推送
          </div>
        </el-form-item>

        <el-form-item label="API基础地址">
          <el-input
            v-model="settings.apiBaseUrl"
            placeholder="http://localhost:8008/api"
            clearable
          >
            <template #prepend>
              <el-icon><Link /></el-icon>
            </template>
          </el-input>
          <div class="form-item-tip">
            后端API服务器地址
          </div>
        </el-form-item>

        <!-- 操作按钮 -->
        <el-form-item>
          <el-button type="primary" @click="saveSettings" :loading="saving">
            <el-icon><Select /></el-icon>
            <span>保存设置</span>
          </el-button>
          <el-button @click="resetSettings">
            <el-icon><RefreshLeft /></el-icon>
            <span>重置为默认</span>
          </el-button>
          <el-button @click="testConnection" :loading="testing">
            <el-icon><Connection /></el-icon>
            <span>测试后端连接</span>
          </el-button>
          <el-button @click="testModel" :loading="testingModel" type="success">
            <el-icon><Cpu /></el-icon>
            <span>一键全测</span>
          </el-button>
        </el-form-item>

        <!-- 状态信息 -->
        <el-alert
          v-if="statusMessage"
          :title="statusMessage"
          :type="statusType"
          :closable="false"
          show-icon
          style="margin-top: 20px; white-space: pre-line;"
        />
      </el-form>
    </el-card>

    <!-- 使用说明 -->
    <el-card class="help-card" style="margin-top: 20px;">
      <template #header>
        <div class="card-header">
          <el-icon><QuestionFilled /></el-icon>
          <span>使用说明</span>
        </div>
      </template>

      <el-steps direction="vertical" :active="3">
        <el-step title="获取 OpenRouter / 豆包 API Key">
          <template #description>
            <div>
              1. 访问 <el-link type="primary" href="https://openrouter.ai/keys" target="_blank">OpenRouter API Keys</el-link><br>
              2. 或访问 <el-link type="primary" href="https://console.volcengine.com/ark" target="_blank">豆包控制台</el-link><br>
              3. 创建API Key并复制
            </div>
          </template>
        </el-step>
        <el-step title="配置调用点模型">
          <template #description>
            <div>
              1. 按调用点选择提供方（OpenRouter/DeepSeek/豆包）<br>
              2. 选择提供方后会自动填入默认模型ID<br>
              3. 如需自定义模型，可手动修改
            </div>
          </template>
        </el-step>
        <el-step title="配置并测试">
          <template #description>
            <div>
              1. 将API Key和模型ID粘贴到上方输入框<br>
              2. 点击"保存设置"按钮<br>
              3. 点击"测试后端连接"验证后端服务<br>
              4. 点击"一键全测"验证所有调用点模型是否可用
            </div>
          </template>
        </el-step>
      </el-steps>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Setting, Key, Lock, Tools, Connection, Link, Select, RefreshLeft, QuestionFilled, Cpu } from '@element-plus/icons-vue'
import axios from 'axios'

const DEFAULT_OPENROUTER_MODEL = 'google/gemini-2.5-flash-preview-09-2025'
const DEFAULT_DEEPSEEK_MODEL = 'deepseek-chat'
const DEFAULT_DOUBAO_MODEL = 'doubao-seed-1-8-251228'

type Provider = 'openrouter' | 'deepseek' | 'doubao'

const modelPresets = [
  { label: 'gemini3-flash', value: 'google/gemini-3-flash-preview' }
]

const DEFAULT_PROVIDER_MODELS: Record<Provider, string> = {
  openrouter: DEFAULT_OPENROUTER_MODEL,
  deepseek: DEFAULT_DEEPSEEK_MODEL,
  doubao: DEFAULT_DOUBAO_MODEL
}

interface CallPointConfig {
  label: string
  provider: Provider
  model: string
  allowedProviders: Provider[]
  requiresImages: boolean
  customKey?: string  // 新增：调用点独立的API Key
}

interface Settings {
  openrouterApiKey: string
  deepseekApiKey: string
  doubaoApiKey: string
  websocketUrl: string
  apiBaseUrl: string
  callPoints: Record<string, CallPointConfig>
}

const callPointOrder = ['matching', 'assembly', 'welding', 'safety', 'bom_vision'] as const
const providerLabels: Record<Provider, string> = {
  openrouter: 'OpenRouter',
  deepseek: 'DeepSeek',
  doubao: '豆包'
}

const buildDefaultCallPoints = (): Record<string, CallPointConfig> => ({
  matching: {
    label: '匹配',
    provider: 'openrouter',
    model: DEFAULT_PROVIDER_MODELS.openrouter,
    allowedProviders: ['openrouter', 'deepseek', 'doubao'],
    requiresImages: false
  },
  assembly: {
    label: '组件/产品',
    provider: 'openrouter',
    model: DEFAULT_PROVIDER_MODELS.openrouter,
    allowedProviders: ['openrouter', 'doubao'],
    requiresImages: true
  },
  welding: {
    label: '焊接',
    provider: 'openrouter',
    model: DEFAULT_PROVIDER_MODELS.openrouter,
    allowedProviders: ['openrouter', 'doubao'],
    requiresImages: true
  },
  safety: {
    label: '安全',
    provider: 'openrouter',
    model: DEFAULT_PROVIDER_MODELS.openrouter,
    allowedProviders: ['openrouter', 'deepseek', 'doubao'],
    requiresImages: false
  },
  bom_vision: {
    label: 'BOM视觉提取',
    provider: 'openrouter',
    model: DEFAULT_PROVIDER_MODELS.openrouter,
    allowedProviders: ['openrouter', 'doubao'],
    requiresImages: true
  }
})

const settings = ref<Settings>({
  openrouterApiKey: '',
  deepseekApiKey: '',
  doubaoApiKey: '',
  websocketUrl: 'ws://localhost:8008',
  apiBaseUrl: '/api',
  callPoints: buildDefaultCallPoints()
})

const saving = ref(false)
const testing = ref(false)
const testingModel = ref(false)
const statusMessage = ref('')
const statusType = ref<'success' | 'warning' | 'error' | 'info'>('info')
const modelPresetSelections = ref<Record<string, string>>({})

const resolveProviderModel = (provider: Provider, model?: string) => {
  const trimmed = model?.trim()
  if (trimmed) {
    return trimmed
  }
  return DEFAULT_PROVIDER_MODELS[provider] || ''
}

const normalizeLocalCallPoints = (incoming?: Record<string, any>) => {
  const normalized = buildDefaultCallPoints()
  if (!incoming) {
    return normalized
  }

  Object.keys(normalized).forEach((id) => {
    const source = incoming[id]
    if (!source) {
      return
    }
    normalized[id] = {
      ...normalized[id],
      label: source.label || normalized[id].label,
      provider: source.provider || normalized[id].provider,
      model: resolveProviderModel(source.provider || normalized[id].provider, source.model || normalized[id].model),
      allowedProviders: Array.isArray(source.allowedProviders) ? source.allowedProviders : normalized[id].allowedProviders,
      requiresImages: typeof source.requiresImages === 'boolean' ? source.requiresImages : normalized[id].requiresImages,
      customKey: source.customKey || ''  // 新增：读取独立Key
    }
  })

  return normalized
}

const normalizeServerCallPoints = (incoming?: Record<string, any>) => {
  const normalized = buildDefaultCallPoints()
  if (!incoming) {
    return normalized
  }

  Object.keys(normalized).forEach((id) => {
    const source = incoming[id]
    if (!source) {
      return
    }
    normalized[id] = {
      ...normalized[id],
      label: source.label || normalized[id].label,
      provider: source.provider || normalized[id].provider,
      model: resolveProviderModel(source.provider || normalized[id].provider, source.model || normalized[id].model),
      allowedProviders: Array.isArray(source.allowed_providers) ? source.allowed_providers : normalized[id].allowedProviders,
      requiresImages: typeof source.requires_images === 'boolean' ? source.requires_images : normalized[id].requiresImages,
      customKey: source.custom_key || ''  // 新增：读取独立Key
    }
  })

  return normalized
}

const applyDefaultModel = (model: string) => {
  const merged = buildDefaultCallPoints()
  Object.keys(merged).forEach((key) => {
    merged[key].model = model
  })
  return merged
}

const handleProviderChange = (callPointId: string) => {
  const provider = settings.value.callPoints[callPointId].provider
  settings.value.callPoints[callPointId].model = DEFAULT_PROVIDER_MODELS[provider] || ''
  modelPresetSelections.value[callPointId] = ''
}

const applyModelPreset = (callPointId: string, value?: string) => {
  if (!value) return
  settings.value.callPoints[callPointId].model = value
  modelPresetSelections.value[callPointId] = value
}

const loadSettings = async () => {
  const saved = localStorage.getItem('app_settings')
  if (saved) {
    try {
      const parsed = JSON.parse(saved)
      if (typeof parsed.apiBaseUrl === 'string') {
        settings.value.apiBaseUrl = parsed.apiBaseUrl
      }
      if (typeof parsed.websocketUrl === 'string') {
        settings.value.websocketUrl = parsed.websocketUrl
      }
      if (typeof parsed.openrouterApiKey === 'string') {
        settings.value.openrouterApiKey = parsed.openrouterApiKey
      }
      if (typeof parsed.deepseekApiKey === 'string') {
        settings.value.deepseekApiKey = parsed.deepseekApiKey
      }
      if (typeof parsed.doubaoApiKey === 'string') {
        settings.value.doubaoApiKey = parsed.doubaoApiKey
      }
      if (parsed.callPoints) {
        settings.value.callPoints = normalizeLocalCallPoints(parsed.callPoints)
      } else if (parsed.defaultModel) {
        settings.value.callPoints = applyDefaultModel(parsed.defaultModel)
      }
    } catch (e) {
      console.error('加载设置失败:', e)
    }
  }

  try {
    const response = await axios.get(`${settings.value.apiBaseUrl}/settings`)
    if (response.data?.call_points) {
      settings.value.callPoints = normalizeServerCallPoints(response.data.call_points)
    }
  } catch (error) {
    console.warn('获取后端设置失败:', error)
  }
}

// 加载设置
onMounted(() => {
  loadSettings()
})

const saveSettings = async () => {
  saving.value = true
  statusMessage.value = ''

  try {
    // 保存到localStorage
    localStorage.setItem('app_settings', JSON.stringify(settings.value))

    const callPointsPayload: Record<string, { provider: Provider; model: string; custom_key?: string }> = {}
    callPointOrder.forEach((id) => {
      const point = settings.value.callPoints[id]
      callPointsPayload[id] = {
        provider: point.provider,
        model: point.model,
        custom_key: point.customKey || undefined  // 新增：发送独立Key
      }
    })

    // 发送到后端
    await axios.post(`${settings.value.apiBaseUrl}/settings`, {
      openrouter_api_key: settings.value.openrouterApiKey,
      deepseek_api_key: settings.value.deepseekApiKey,
      doubao_api_key: settings.value.doubaoApiKey,
      call_points: callPointsPayload
    })

    statusMessage.value = '设置保存成功！'
    statusType.value = 'success'
    ElMessage.success('设置已保存')
  } catch (error: any) {
    statusMessage.value = `保存失败: ${error.message}`
    statusType.value = 'error'
    ElMessage.error('保存设置失败')
  } finally {
    saving.value = false
  }
}

const resetSettings = () => {
  settings.value = {
    openrouterApiKey: '',
    deepseekApiKey: '',
    doubaoApiKey: '',
    websocketUrl: 'ws://localhost:8008',
    apiBaseUrl: '/api',
    callPoints: buildDefaultCallPoints()
  }
  localStorage.removeItem('app_settings')
  statusMessage.value = '已重置为默认设置'
  statusType.value = 'info'
  ElMessage.info('已重置为默认设置')
}

const testConnection = async () => {
  testing.value = true
  statusMessage.value = ''

  try {
    const response = await axios.get(`${settings.value.apiBaseUrl}/health`)

    if (response.data.status === 'healthy') {
      statusMessage.value = '✅ 后端连接成功！服务运行正常'
      statusType.value = 'success'
      ElMessage.success('后端连接测试成功')
    } else {
      statusMessage.value = '⚠️ 后端服务状态异常'
      statusType.value = 'warning'
    }
  } catch (error: any) {
    statusMessage.value = `❌ 后端连接失败: ${error.message}`
    statusType.value = 'error'
    ElMessage.error('后端连接测试失败')
  } finally {
    testing.value = false
  }
}

const testModel = async () => {
  testingModel.value = true
  statusMessage.value = ''
  statusType.value = 'info'

  try {
    // 先保存设置
    localStorage.setItem('app_settings', JSON.stringify(settings.value))

    const results: string[] = []
    let hasFailure = false

    for (let index = 0; index < callPointOrder.length; index += 1) {
      const callPointId = callPointOrder[index]
      const testPoint = settings.value.callPoints[callPointId]
      const provider = testPoint.provider
      const model = testPoint.model
      const providerLabel = providerLabels[provider] || provider

      statusMessage.value = `🔄 正在测试 ${testPoint.label} (${index + 1}/${callPointOrder.length})...`
      if (!model) {
        results.push(`❌ ${testPoint.label}：模型ID为空`)
        hasFailure = true
        continue
      }

      try {
        // 顺序测试避免触发限流
        const response = await axios.post(`${settings.value.apiBaseUrl}/test-model`, {
          provider,
          model,
          openrouter_api_key: settings.value.openrouterApiKey,
          deepseek_api_key: settings.value.deepseekApiKey,
          doubao_api_key: settings.value.doubaoApiKey,
          custom_key: testPoint.customKey || undefined  // 新增：发送独立Key
        })

        if (response.data.success) {
          results.push(`✅ ${testPoint.label}：${providerLabel} / ${model}`)
        } else {
          results.push(`❌ ${testPoint.label}：${providerLabel} / ${model}，${response.data.error || '未知错误'}`)
          hasFailure = true
        }
      } catch (error: any) {
        const errorMsg = error.response?.data?.detail || error.message
        results.push(`❌ ${testPoint.label}：${providerLabel} / ${model}，${errorMsg}`)
        hasFailure = true
      }
    }

    statusMessage.value = `模型连接测试结果：\n${results.join('\n')}`
    statusType.value = hasFailure ? 'error' : 'success'
    if (hasFailure) {
      ElMessage.warning('部分模型连接失败')
    } else {
      ElMessage.success('模型连接全部通过')
    }
  } catch (error: any) {
    const errorMsg = error.response?.data?.detail || error.message
    statusMessage.value = `❌ 模型连接失败: ${errorMsg}`
    statusType.value = 'error'
    ElMessage.error('模型连接测试失败')
  } finally {
    testingModel.value = false
  }
}
</script>

<style scoped>
.settings-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px;
}

.settings-card {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
}

.form-item-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.callpoint-config {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
}

.callpoint-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  padding: 12px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  background-color: #fafafa;
}

.callpoint-row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.callpoint-key-row {
  display: flex;
  align-items: center;
  width: 100%;
  margin-left: 122px;
}

.callpoint-label {
  width: 110px;
  font-size: 13px;
  color: #606266;
  flex-shrink: 0;
  font-weight: 500;
}

.callpoint-provider {
  width: 160px;
}

.callpoint-model {
  flex: 1;
}

.callpoint-model-preset {
  width: 180px;
}

.callpoint-custom-key {
  flex: 1;
}

.help-card {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

:deep(.el-step__description) {
  padding-right: 20px;
  line-height: 1.8;
}
</style>

