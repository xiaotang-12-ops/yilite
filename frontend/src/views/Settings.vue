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
            统一使用OpenRouter调用所有AI模型，
            <el-link type="primary" href="https://openrouter.ai/keys" target="_blank">
              获取API Key
            </el-link>
          </div>
        </el-form-item>

        <!-- 模型配置 -->
        <el-divider content-position="left">
          <el-icon><Cpu /></el-icon>
          <span style="margin-left: 8px;">模型配置</span>
        </el-divider>

        <el-form-item label="默认模型">
          <el-input
            v-model="settings.defaultModel"
            placeholder="google/gemini-2.0-flash-exp:free"
            clearable
          >
            <template #prepend>
              <el-icon><Cpu /></el-icon>
            </template>
          </el-input>
          <div class="form-item-tip">
            OpenRouter模型ID，例如: google/gemini-2.0-flash-exp:free, anthropic/claude-3.5-sonnet
            <el-link type="primary" href="https://openrouter.ai/models" target="_blank">
              查看可用模型
            </el-link>
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
            <span>测试模型连接</span>
          </el-button>
        </el-form-item>

        <!-- 状态信息 -->
        <el-alert
          v-if="statusMessage"
          :title="statusMessage"
          :type="statusType"
          :closable="false"
          show-icon
          style="margin-top: 20px;"
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
        <el-step title="获取OpenRouter API Key">
          <template #description>
            <div>
              1. 访问 <el-link type="primary" href="https://openrouter.ai/keys" target="_blank">OpenRouter API Keys</el-link><br>
              2. 登录/注册账号（支持Google登录）<br>
              3. 创建API Key并复制<br>
              4. 充值余额（支持信用卡）
            </div>
          </template>
        </el-step>
        <el-step title="选择模型">
          <template #description>
            <div>
              1. 访问 <el-link type="primary" href="https://openrouter.ai/models" target="_blank">OpenRouter模型列表</el-link><br>
              2. 选择合适的模型（推荐Gemini 2.0 Flash免费版）<br>
              3. 复制模型ID（例如: google/gemini-2.0-flash-exp:free）<br>
              4. 粘贴到"默认模型"输入框
            </div>
          </template>
        </el-step>
        <el-step title="配置并测试">
          <template #description>
            <div>
              1. 将API Key和模型ID粘贴到上方输入框<br>
              2. 点击"保存设置"按钮<br>
              3. 点击"测试后端连接"验证后端服务<br>
              4. 点击"测试模型连接"验证模型配置是否正确
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

interface Settings {
  openrouterApiKey: string
  defaultModel: string
  websocketUrl: string
  apiBaseUrl: string
}

const settings = ref<Settings>({
  openrouterApiKey: '',
  defaultModel: 'google/gemini-2.0-flash-exp:free',
  websocketUrl: 'ws://localhost:8008',
  apiBaseUrl: '/api'
})

const saving = ref(false)
const testing = ref(false)
const testingModel = ref(false)
const statusMessage = ref('')
const statusType = ref<'success' | 'warning' | 'error' | 'info'>('info')

// 加载设置
onMounted(() => {
  loadSettings()
})

const loadSettings = () => {
  const saved = localStorage.getItem('app_settings')
  if (saved) {
    try {
      const parsed = JSON.parse(saved)
      settings.value = { ...settings.value, ...parsed }
    } catch (e) {
      console.error('加载设置失败:', e)
    }
  }
}

const saveSettings = async () => {
  saving.value = true
  statusMessage.value = ''

  try {
    // 保存到localStorage
    localStorage.setItem('app_settings', JSON.stringify(settings.value))

    // 发送到后端
    await axios.post(`${settings.value.apiBaseUrl}/settings`, {
      openrouter_api_key: settings.value.openrouterApiKey,
      default_model: settings.value.defaultModel
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
    defaultModel: 'google/gemini-2.0-flash-exp:free',
    websocketUrl: 'ws://localhost:8008',
    apiBaseUrl: '/api'
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

  try {
    // 先保存设置
    localStorage.setItem('app_settings', JSON.stringify(settings.value))

    // 测试模型连接
    const response = await axios.post(`${settings.value.apiBaseUrl}/test-model`, {
      openrouter_api_key: settings.value.openrouterApiKey,
      model: settings.value.defaultModel
    })

    if (response.data.success) {
      statusMessage.value = `✅ 模型连接成功！\n模型: ${settings.value.defaultModel}\n响应: ${response.data.message || '测试通过'}`
      statusType.value = 'success'
      ElMessage.success('模型连接测试成功')
    } else {
      statusMessage.value = `❌ 模型连接失败: ${response.data.error || '未知错误'}`
      statusType.value = 'error'
      ElMessage.error('模型连接测试失败')
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

.help-card {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

:deep(.el-step__description) {
  padding-right: 20px;
  line-height: 1.8;
}
</style>

