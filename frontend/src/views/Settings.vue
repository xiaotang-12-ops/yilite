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
        <el-form-item label="NewAPI API Key">
          <el-input
            v-model="settings.newapiApiKey"
            type="password"
            show-password
            placeholder="请输入NewAPI API Key"
            clearable
          >
            <template #prepend>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
          <div class="form-item-tip">
            NewAPI用于视觉/文本调用点（兼容 OpenAI 协议）
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
                  v-if="isNewApiProvider(settings.callPoints[callPointId].provider)"
                  v-model="modelPresetSelections[callPointId]"
                  class="callpoint-model-preset"
                  placeholder="快捷模型"
                  clearable
                  @change="applyModelPreset(callPointId, $event)"
                >
                  <el-option
                    v-for="preset in getModelPresetsForCallPoint(callPointId)"
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
              <div class="callpoint-fallback-row">
                <el-input
                  v-model="settings.callPoints[callPointId].fallbackModel"
                  class="callpoint-fallback-model"
                  placeholder="兜底模型（可选，主模型失败时自动切换）"
                  clearable
                >
                  <template #prepend>
                    <el-icon><RefreshLeft /></el-icon>
                  </template>
                </el-input>
              </div>
            </div>
          </div>
          <div class="form-item-tip">
            视觉调用点支持OpenRouter/NewAPI；文本调用点可选OpenRouter/DeepSeek/NewAPI
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

        <!-- 界面字号配置 -->
        <el-divider content-position="left">
          <el-icon><Tools /></el-icon>
          <span style="margin-left: 8px;">界面字号调节</span>
        </el-divider>

        <div class="visual-font-panel">
          <div class="visual-font-grid">
            <el-form-item label="首页标题整体">
              <el-slider
                v-model="visualFontSettings.homeTitleScale"
                :min="visualFontLimits.homeTitleScale.min"
                :max="visualFontLimits.homeTitleScale.max"
                :step="visualFontLimits.homeTitleScale.step"
                :format-tooltip="formatScaleTip"
                show-input
              />
              <div class="form-item-tip">
                调整桌面和平板端首页主标题整体比例。
              </div>
            </el-form-item>

            <el-form-item label="首页标题手机">
              <el-slider
                v-model="visualFontSettings.homeMobileTitleScale"
                :min="visualFontLimits.homeMobileTitleScale.min"
                :max="visualFontLimits.homeMobileTitleScale.max"
                :step="visualFontLimits.homeMobileTitleScale.step"
                :format-tooltip="formatScaleTip"
                show-input
              />
              <div class="form-item-tip">
                单独控制手机端首页标题，避免长标题显示不全。
              </div>
            </el-form-item>

            <el-form-item label="首页说明文字">
              <el-slider
                v-model="visualFontSettings.homeFeatureScale"
                :min="visualFontLimits.homeFeatureScale.min"
                :max="visualFontLimits.homeFeatureScale.max"
                :step="visualFontLimits.homeFeatureScale.step"
                :format-tooltip="formatScaleTip"
                show-input
              />
              <div class="form-item-tip">
                调整首页左侧“上传图纸”等说明文字比例。
              </div>
            </el-form-item>

            <el-form-item label="手机导航字号">
              <el-slider
                v-model="visualFontSettings.navMobileFontSize"
                :min="visualFontLimits.navMobileFontSize.min"
                :max="visualFontLimits.navMobileFontSize.max"
                :step="visualFontLimits.navMobileFontSize.step"
                :format-tooltip="formatPxTip"
                show-input
              />
              <div class="form-item-tip">
                调整顶部导航长系统名在手机端的字号，单位 px。
              </div>
            </el-form-item>

            <el-form-item label="手机导航宽度">
              <el-slider
                v-model="visualFontSettings.navMobileMaxWidth"
                :min="visualFontLimits.navMobileMaxWidth.min"
                :max="visualFontLimits.navMobileMaxWidth.max"
                :step="visualFontLimits.navMobileMaxWidth.step"
                :format-tooltip="formatPxTip"
                show-input
              />
              <div class="form-item-tip">
                控制手机端系统名最大占宽，右侧按钮空间仍会自动保留。
              </div>
            </el-form-item>
          </div>

          <div class="visual-preview">
            <div class="visual-preview-title">
              <span class="preview-kicker">工业装配工艺知识</span>
              <strong>自动解析</strong>
              <span>数字孪生化指导系统</span>
            </div>
            <div class="visual-preview-nav">
              工业装配工艺知识自动解析与数字孪生化指导系统
            </div>
          </div>

          <div class="visual-font-actions">
            <el-button type="primary" plain @click="saveVisualSettings">
              <el-icon><Select /></el-icon>
              <span>保存界面字号</span>
            </el-button>
            <el-button @click="resetVisualSettings">
              <el-icon><RefreshLeft /></el-icon>
              <span>恢复字号默认</span>
            </el-button>
          </div>
        </div>

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
        <el-step title="获取 OpenRouter / NewAPI API Key">
          <template #description>
            <div>
              1. 访问 <el-link type="primary" href="https://openrouter.ai/keys" target="_blank">OpenRouter API Keys</el-link><br>
              2. 或在你的 NewAPI 平台创建 API Key<br>
              3. 创建API Key并复制
            </div>
          </template>
        </el-step>
        <el-step title="配置调用点模型">
          <template #description>
            <div>
              1. 按调用点选择提供方（OpenRouter/DeepSeek/NewAPI）<br>
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
import { ref, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Setting, Key, Lock, Tools, Connection, Link, Select, RefreshLeft, QuestionFilled, Cpu } from '@element-plus/icons-vue'
import axios from 'axios'
import { useVisualFontSettings } from '../composables/useVisualFontSettings'

const DEFAULT_OPENROUTER_MODEL = 'google/gemini-2.5-flash-preview-09-2025'
const DEFAULT_DEEPSEEK_MODEL = 'deepseek-chat'
const DEFAULT_NEWAPI_MODEL = 'doubao-seed-2-0-lite-260215'
const UNSUPPORTED_NEWAPI_IMAGE_MODELS = new Set(['glm-5'])
const TEST_BACKEND_TIMEOUT_MS = 10000
const TEST_MODEL_TIMEOUT_MS = 75000

type Provider = 'openrouter' | 'deepseek' | 'newapi' | 'doubao'

const modelPresets = [
  { label: 'doubao-seed-2-0-lite-260215', value: 'doubao-seed-2-0-lite-260215' },
  { label: 'doubao-seed-2-0-pro-260215', value: 'doubao-seed-2-0-pro-260215' },
  { label: 'qwen3.5-plus-2026-02-15', value: 'qwen3.5-plus-2026-02-15' },
  { label: 'gpt-5-mini', value: 'gpt-5-mini' },
  { label: 'glm-5', value: 'glm-5' }
]

const DEFAULT_PROVIDER_MODELS: Record<Provider, string> = {
  openrouter: DEFAULT_OPENROUTER_MODEL,
  deepseek: DEFAULT_DEEPSEEK_MODEL,
  newapi: DEFAULT_NEWAPI_MODEL,
  doubao: DEFAULT_NEWAPI_MODEL
}

interface CallPointConfig {
  label: string
  provider: Provider
  model: string
  fallbackModel: string
  allowedProviders: Provider[]
  requiresImages: boolean
  customKey?: string  // 新增：调用点独立的API Key
}

interface Settings {
  openrouterApiKey: string
  deepseekApiKey: string
  newapiApiKey: string
  websocketUrl: string
  apiBaseUrl: string
  callPoints: Record<string, CallPointConfig>
}

const resolveDefaultWebsocketUrl = () => {
  if (typeof window === 'undefined') return 'ws://localhost:8008'
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}`
}

const callPointOrder = ['matching', 'assembly', 'welding', 'safety', 'bom_vision'] as const
const providerLabels: Record<Provider, string> = {
  openrouter: 'OpenRouter',
  deepseek: 'DeepSeek',
  newapi: 'NewAPI',
  doubao: 'NewAPI(兼容)'
}

const normalizeProvider = (provider?: string): Provider => {
  const value = (provider || '').trim().toLowerCase()
  if (value === 'doubao') return 'newapi'
  if (value === 'newapi' || value === 'openrouter' || value === 'deepseek') {
    return value as Provider
  }
  return 'openrouter'
}

const normalizeAllowedProviders = (providers: any, fallback: Provider[]) => {
  if (!Array.isArray(providers) || providers.length === 0) {
    return fallback
  }
  const mapped = providers.map((item) => normalizeProvider(String(item)))
  return Array.from(new Set(mapped))
}

const isNewApiProvider = (provider?: string) => normalizeProvider(provider) === 'newapi'

const buildDefaultCallPoints = (): Record<string, CallPointConfig> => ({
  matching: {
    label: '匹配',
    provider: 'openrouter',
    model: DEFAULT_PROVIDER_MODELS.openrouter,
    fallbackModel: '',
    allowedProviders: ['openrouter', 'deepseek', 'newapi'],
    requiresImages: false
  },
  assembly: {
    label: '组件/产品',
    provider: 'openrouter',
    model: DEFAULT_PROVIDER_MODELS.openrouter,
    fallbackModel: '',
    allowedProviders: ['openrouter', 'newapi'],
    requiresImages: true
  },
  welding: {
    label: '焊接',
    provider: 'openrouter',
    model: DEFAULT_PROVIDER_MODELS.openrouter,
    fallbackModel: '',
    allowedProviders: ['openrouter', 'newapi'],
    requiresImages: true
  },
  safety: {
    label: '安全',
    provider: 'openrouter',
    model: DEFAULT_PROVIDER_MODELS.openrouter,
    fallbackModel: '',
    allowedProviders: ['openrouter', 'deepseek', 'newapi'],
    requiresImages: false
  },
  bom_vision: {
    label: 'BOM视觉提取',
    provider: 'openrouter',
    model: DEFAULT_PROVIDER_MODELS.openrouter,
    fallbackModel: '',
    allowedProviders: ['openrouter', 'newapi'],
    requiresImages: true
  }
})

const settings = ref<Settings>({
  openrouterApiKey: '',
  deepseekApiKey: '',
  newapiApiKey: '',
  websocketUrl: resolveDefaultWebsocketUrl(),
  apiBaseUrl: '/api',
  callPoints: buildDefaultCallPoints()
})

const {
  visualFontSettings,
  visualFontLimits,
  applyVisualFontSettings,
  saveVisualFontSettings,
  resetVisualFontSettings
} = useVisualFontSettings()

// 设置页拖动滑块时先实时预览，是否长期保留由“保存界面字号”决定。
watch(visualFontSettings, () => {
  applyVisualFontSettings()
}, { deep: true })

const saving = ref(false)
const testing = ref(false)
const testingModel = ref(false)
const statusMessage = ref('')
const statusType = ref<'success' | 'warning' | 'error' | 'info'>('info')
const modelPresetSelections = ref<Record<string, string>>({})

const resolveProviderModel = (provider: Provider, model?: string) => {
  const normalizedProvider = normalizeProvider(provider)
  const trimmed = model?.trim()
  if (trimmed) {
    return trimmed
  }
  return DEFAULT_PROVIDER_MODELS[normalizedProvider] || ''
}

const isUnsupportedNewApiImageModel = (model?: string) => {
  const normalized = (model || '').trim().toLowerCase()
  return normalized.length > 0 && UNSUPPORTED_NEWAPI_IMAGE_MODELS.has(normalized)
}

const sanitizeCallPointModel = (
  callPointId: string,
  provider: Provider,
  model?: string,
  requiresImages?: boolean
) => {
  const resolved = resolveProviderModel(provider, model)
  const needImages = typeof requiresImages === 'boolean'
    ? requiresImages
    : Boolean(settings.value.callPoints[callPointId]?.requiresImages)
  if (needImages && isNewApiProvider(provider) && isUnsupportedNewApiImageModel(resolved)) {
    return DEFAULT_NEWAPI_MODEL
  }
  return resolved
}

const sanitizeFallbackModel = (
  callPointId: string,
  provider: Provider,
  fallbackModel?: string,
  requiresImages?: boolean
) => {
  const trimmed = (fallbackModel || '').trim()
  if (!trimmed) {
    return ''
  }
  return sanitizeCallPointModel(callPointId, provider, trimmed, requiresImages)
}

const getModelPresetsForCallPoint = (callPointId: string) => {
  const point = settings.value.callPoints[callPointId]
  if (!point) {
    return modelPresets
  }
  if (point.requiresImages && isNewApiProvider(point.provider)) {
    return modelPresets.filter((preset) => !isUnsupportedNewApiImageModel(preset.value))
  }
  return modelPresets
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
    const provider = normalizeProvider(source.provider || normalized[id].provider)
    const requiresImages = typeof source.requiresImages === 'boolean'
      ? source.requiresImages
      : normalized[id].requiresImages
    normalized[id] = {
      ...normalized[id],
      label: source.label || normalized[id].label,
      provider,
      model: sanitizeCallPointModel(id, provider, source.model || normalized[id].model, requiresImages),
      fallbackModel: sanitizeFallbackModel(
        id,
        provider,
        source.fallbackModel || source.fallback_model || normalized[id].fallbackModel,
        requiresImages
      ),
      allowedProviders: normalizeAllowedProviders(source.allowedProviders, normalized[id].allowedProviders),
      requiresImages,
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
    const provider = normalizeProvider(source.provider || normalized[id].provider)
    const requiresImages = typeof source.requires_images === 'boolean'
      ? source.requires_images
      : normalized[id].requiresImages
    normalized[id] = {
      ...normalized[id],
      label: source.label || normalized[id].label,
      provider,
      model: sanitizeCallPointModel(id, provider, source.model || normalized[id].model, requiresImages),
      fallbackModel: sanitizeFallbackModel(
        id,
        provider,
        source.fallback_model || source.fallbackModel || normalized[id].fallbackModel,
        requiresImages
      ),
      allowedProviders: normalizeAllowedProviders(source.allowed_providers, normalized[id].allowedProviders),
      requiresImages,
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
  const provider = normalizeProvider(settings.value.callPoints[callPointId].provider)
  settings.value.callPoints[callPointId].provider = provider
  settings.value.callPoints[callPointId].model = sanitizeCallPointModel(
    callPointId,
    provider,
    DEFAULT_PROVIDER_MODELS[provider] || '',
    settings.value.callPoints[callPointId].requiresImages
  )
  settings.value.callPoints[callPointId].fallbackModel = sanitizeFallbackModel(
    callPointId,
    provider,
    settings.value.callPoints[callPointId].fallbackModel,
    settings.value.callPoints[callPointId].requiresImages
  )
  modelPresetSelections.value[callPointId] = ''
}

const applyModelPreset = (callPointId: string, value?: string) => {
  if (!value) return
  const point = settings.value.callPoints[callPointId]
  settings.value.callPoints[callPointId].model = sanitizeCallPointModel(
    callPointId,
    normalizeProvider(point.provider),
    value,
    point.requiresImages
  )
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
      if (typeof parsed.newapiApiKey === 'string') {
        settings.value.newapiApiKey = parsed.newapiApiKey
      } else if (typeof parsed.doubaoApiKey === 'string') {
        settings.value.newapiApiKey = parsed.doubaoApiKey
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

const formatScaleTip = (value: number) => `${Math.round(value * 100)}%`

const formatPxTip = (value: number) => `${value}px`

const saveVisualSettings = () => {
  saveVisualFontSettings()
  ElMessage.success('界面字号已保存')
}

const resetVisualSettings = () => {
  resetVisualFontSettings()
  ElMessage.success('界面字号已恢复默认')
}

const saveSettings = async () => {
  saving.value = true
  statusMessage.value = ''

  try {
    // 保存到localStorage
    localStorage.setItem('app_settings', JSON.stringify(settings.value))
    saveVisualFontSettings()

    const callPointsPayload: Record<string, { provider: Provider; model: string; fallback_model?: string; custom_key?: string }> = {}
    const adjustedMainPoints: string[] = []
    const adjustedFallbackPoints: string[] = []
    callPointOrder.forEach((id) => {
      const point = settings.value.callPoints[id]
      const provider = normalizeProvider(point.provider)
      const sanitizedModel = sanitizeCallPointModel(id, provider, point.model, point.requiresImages)
      const sanitizedFallbackModel = sanitizeFallbackModel(id, provider, point.fallbackModel, point.requiresImages)
      if (sanitizedModel !== point.model) {
        point.model = sanitizedModel
        adjustedMainPoints.push(point.label)
      }
      if (sanitizedFallbackModel !== (point.fallbackModel || '')) {
        point.fallbackModel = sanitizedFallbackModel
        adjustedFallbackPoints.push(point.label)
      }
      callPointsPayload[id] = {
        provider,
        model: sanitizedModel,
        fallback_model: sanitizedFallbackModel || undefined,
        custom_key: point.customKey || undefined  // 新增：发送独立Key
      }
    })

    // 发送到后端
    await axios.post(`${settings.value.apiBaseUrl}/settings`, {
      openrouter_api_key: settings.value.openrouterApiKey,
      deepseek_api_key: settings.value.deepseekApiKey,
      newapi_api_key: settings.value.newapiApiKey,
      doubao_api_key: settings.value.newapiApiKey, // legacy payload for backward compatibility
      call_points: callPointsPayload
    })

    statusMessage.value = '设置保存成功！'
    statusType.value = 'success'
    ElMessage.success('设置已保存')
    if (adjustedMainPoints.length > 0 || adjustedFallbackPoints.length > 0) {
      const warningParts: string[] = []
      if (adjustedMainPoints.length > 0) {
        warningParts.push(`主模型：${adjustedMainPoints.join('、')}`)
      }
      if (adjustedFallbackPoints.length > 0) {
        warningParts.push(`兜底模型：${adjustedFallbackPoints.join('、')}`)
      }
      ElMessage.warning(`已自动替换不支持多模态的模型（${warningParts.join('；')}）`)
    }
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
    newapiApiKey: '',
    websocketUrl: resolveDefaultWebsocketUrl(),
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
    const response = await axios.get(`${settings.value.apiBaseUrl}/health`, {
      timeout: TEST_BACKEND_TIMEOUT_MS
    })

    if (response.data.status === 'healthy') {
      statusMessage.value = '✅ 后端连接成功！服务运行正常'
      statusType.value = 'success'
      ElMessage.success('后端连接测试成功')
    } else {
      statusMessage.value = '⚠️ 后端服务状态异常'
      statusType.value = 'warning'
    }
  } catch (error: any) {
    const timeoutHint = error.code === 'ECONNABORTED' ? `请求超时（>${TEST_BACKEND_TIMEOUT_MS / 1000}s）` : ''
    statusMessage.value = `❌ 后端连接失败: ${timeoutHint || error.message}`
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
      const provider = normalizeProvider(testPoint.provider)
      const model = testPoint.model
      const configuredFallbackModel = (testPoint.fallbackModel || '').trim()
      const providerLabel = providerLabels[provider] || provider

      statusMessage.value = `🔄 正在测试 ${testPoint.label} (${index + 1}/${callPointOrder.length})...`
      if (!model) {
        results.push(`❌ ${testPoint.label}：模型ID为空`)
        hasFailure = true
        continue
      }

      const runTestRequest = async (targetModel: string, fallbackModel?: string) => {
        return axios.post(`${settings.value.apiBaseUrl}/test-model`, {
          provider,
          model: targetModel,
          fallback_model: fallbackModel || undefined,
          openrouter_api_key: settings.value.openrouterApiKey,
          deepseek_api_key: settings.value.deepseekApiKey,
          newapi_api_key: settings.value.newapiApiKey,
          doubao_api_key: settings.value.newapiApiKey, // legacy payload
          probe_capabilities: true,
          custom_key: testPoint.customKey || undefined // 新增：发送独立Key
        }, {
          timeout: TEST_MODEL_TIMEOUT_MS
        })
      }

      try {
        // 顺序测试避免触发限流
        const response = await runTestRequest(model, configuredFallbackModel || undefined)

        if (response.data.success) {
          const warnings = Array.isArray(response.data.warnings) ? response.data.warnings : []
          results.push(`✅ ${testPoint.label}：${providerLabel} / ${model}`)
          if (response.data.used_fallback) {
            const fallbackModel = response.data.used_model || configuredFallbackModel
            results.push(`⚠️ ${testPoint.label}：主模型失败，已自动切换兜底模型 ${fallbackModel}`)
          }
          if (warnings.length > 0) {
            warnings.forEach((msg: string) => {
              results.push(`⚠️ ${testPoint.label}：${msg}`)
            })
          }
        } else {
          results.push(`❌ ${testPoint.label}：${providerLabel} / ${model}，${response.data.error || '未知错误'}`)
          hasFailure = true
        }
      } catch (error: any) {
        const timeoutHint = error.code === 'ECONNABORTED' ? `请求超时（>${TEST_MODEL_TIMEOUT_MS / 1000}s）` : ''
        const errorMsg = timeoutHint || error.response?.data?.detail || error.message
        results.push(`❌ ${testPoint.label}：${providerLabel} / ${model}，${errorMsg}`)
        hasFailure = true
      }

      if (configuredFallbackModel && configuredFallbackModel !== model) {
        statusMessage.value = `🔄 正在测试 ${testPoint.label} 兜底模型 (${index + 1}/${callPointOrder.length})...`
        try {
          const fallbackResponse = await runTestRequest(configuredFallbackModel)
          if (fallbackResponse.data.success) {
            const fallbackWarnings = Array.isArray(fallbackResponse.data.warnings) ? fallbackResponse.data.warnings : []
            results.push(`✅ ${testPoint.label}（兜底）: ${providerLabel} / ${configuredFallbackModel}`)
            if (fallbackWarnings.length > 0) {
              fallbackWarnings.forEach((msg: string) => {
                results.push(`⚠️ ${testPoint.label}（兜底）: ${msg}`)
              })
            }
          } else {
            results.push(`❌ ${testPoint.label}（兜底）: ${providerLabel} / ${configuredFallbackModel}，${fallbackResponse.data.error || '未知错误'}`)
            hasFailure = true
          }
        } catch (fallbackError: any) {
          const timeoutHint = fallbackError.code === 'ECONNABORTED' ? `请求超时（>${TEST_MODEL_TIMEOUT_MS / 1000}s）` : ''
          const fallbackErrorMsg = timeoutHint || fallbackError.response?.data?.detail || fallbackError.message
          results.push(`❌ ${testPoint.label}（兜底）: ${providerLabel} / ${configuredFallbackModel}，${fallbackErrorMsg}`)
          hasFailure = true
        }
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

.callpoint-fallback-row {
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

.callpoint-fallback-model {
  flex: 1;
}

.visual-font-panel {
  width: 100%;
  margin-bottom: 18px;
}

.visual-font-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 2px;
}

.visual-font-grid :deep(.el-form-item) {
  margin-bottom: 18px;
}

.visual-font-grid :deep(.el-slider) {
  width: 100%;
}

.visual-preview {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(180px, 280px);
  gap: 16px;
  align-items: center;
  margin: 4px 0 16px 150px;
  padding: 16px;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  background: #f7fbff;
}

.visual-preview-title {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  color: #1f2937;
  line-height: 1.05;
}

.visual-preview-title .preview-kicker {
  width: fit-content;
  padding: 3px 8px;
  border-left: 3px solid var(--el-color-primary);
  background: rgba(64, 158, 255, 0.08);
  font-size: var(--visual-preview-kicker-font-size, 12px);
  font-weight: 700;
}

.visual-preview-title strong {
  font-size: var(--visual-preview-primary-font-size, 28px);
  font-weight: 900;
}

.visual-preview-title span:last-child {
  font-size: var(--visual-preview-secondary-font-size, 20px);
  font-weight: 800;
}

.visual-preview-nav {
  max-width: min(var(--visual-nav-mobile-max-width, 226px), 100%);
  padding: 10px;
  border: 1px dashed var(--el-color-primary);
  border-radius: 8px;
  color: #1f2937;
  font-size: var(--visual-nav-mobile-font-size, 10px);
  line-height: 1.18;
  word-break: break-all;
}

.visual-font-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-left: 150px;
}

.help-card {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

:deep(.el-step__description) {
  padding-right: 20px;
  line-height: 1.8;
}

@media (max-width: 768px) {
  .settings-container {
    padding: 12px;
  }

  :deep(.el-form-item) {
    display: block;
  }

  :deep(.el-form-item__label) {
    width: 100% !important;
    justify-content: flex-start;
    margin-bottom: 6px;
  }

  :deep(.el-form-item__content) {
    margin-left: 0 !important;
  }

  .callpoint-row {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .callpoint-key-row,
  .callpoint-fallback-row {
    margin-left: 0;
  }

  .callpoint-label,
  .callpoint-provider,
  .callpoint-model,
  .callpoint-model-preset {
    width: 100%;
  }

  .visual-preview {
    grid-template-columns: 1fr;
    margin-left: 0;
  }

  .visual-font-actions {
    margin-left: 0;
  }
}
</style>
