<template>
  <div class="engineer-page">
    <div class="container">
      <!-- 页面标题 -->
      <div class="page-header">
        <h1>🔬 AI Agent 协作监控台</h1>
        <p>实时监控多Agent协作过程，查看后端日志和Agent对话</p>
      </div>

      <!-- Agent状态总览 -->
      <div class="agent-overview">
        <div class="overview-cards">
          <div
            v-for="agent in agents"
            :key="agent.id"
            class="agent-overview-card"
            :class="{ active: agent.status === 'working' }"
          >
            <div class="agent-avatar">{{ agent.icon }}</div>
            <div class="agent-info">
              <h3>{{ agent.name }}</h3>
              <p class="agent-status" :class="agent.status">{{ getStatusText(agent.status) }}</p>
              <div class="agent-progress">
                <el-progress
                  :percentage="agent.progress"
                  :status="agent.status === 'error' ? 'exception' : 'success'"
                  :stroke-width="4"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 主要内容区域 -->
      <div class="main-content">
        <!-- 左侧：Agent对话流 -->
        <div class="dialog-section">
          <div class="section-header">
            <h2>🤖 Agent 协作对话</h2>
            <div class="dialog-controls">
              <el-button size="small" @click="clearDialogs">清空日志</el-button>
              <el-button size="small" @click="toggleAutoScroll">
                {{ autoScroll ? '停止滚动' : '自动滚动' }}
              </el-button>
            </div>
          </div>

          <div class="dialog-container" ref="dialogContainer">
            <div
              v-for="dialog in agentDialogs"
              :key="dialog.id"
              class="dialog-message"
              :class="[dialog.type, dialog.status]"
            >
              <div class="dialog-avatar">{{ dialog.agentIcon }}</div>
              <div class="dialog-content">
                <div class="dialog-header">
                  <span class="agent-name">{{ dialog.agent }}</span>
                  <span class="dialog-time">{{ dialog.timestamp }}</span>
                </div>
                <div class="dialog-text" :class="{ typing: dialog.status === 'typing' }">
                  {{ dialog.message }}
                  <span v-if="dialog.status === 'typing'" class="typing-cursor">▋</span>
                </div>
              </div>
            </div>

            <!-- 空状态 -->
            <div v-if="agentDialogs.length === 0" class="empty-state">
              <div class="empty-icon">🤖</div>
              <p>等待Agent开始工作...</p>
              <el-button type="primary" @click="startDemo">启动演示模式</el-button>
            </div>
          </div>
        </div>

        <!-- 右侧：系统日志和统计 -->
        <div class="log-section">
          <div class="section-header">
            <h2>📊 系统监控</h2>
          </div>

          <!-- 实时统计 -->
          <div class="stats-panel">
            <div class="stat-item">
              <div class="stat-value">{{ stats.totalTasks }}</div>
              <div class="stat-label">总任务数</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ stats.completedTasks }}</div>
              <div class="stat-label">已完成</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ stats.activeAgents }}</div>
              <div class="stat-label">活跃Agent</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ stats.avgProcessTime }}s</div>
              <div class="stat-label">平均处理时间</div>
            </div>
          </div>

          <!-- 系统日志 -->
          <div class="system-logs">
            <h3>系统日志</h3>
            <div class="log-container">
              <div
                v-for="log in systemLogs"
                :key="log.id"
                class="log-entry"
                :class="log.level"
              >
                <span class="log-time">{{ log.timestamp }}</span>
                <span class="log-level">{{ log.level.toUpperCase() }}</span>
                <span class="log-message">{{ log.message }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'

// Agent数据
const agents = ref([
  {
    id: 'file-manager',
    name: '文件管理员',
    icon: '📁',
    status: 'idle',
    progress: 0
  },
  {
    id: 'qwen-vl',
    name: 'Qwen-VL视觉分析师',
    icon: '👁️',
    status: 'idle',
    progress: 0
  },
  {
    id: 'deepseek',
    name: 'DeepSeek推理专家',
    icon: '🧠',
    status: 'idle',
    progress: 0
  },
  {
    id: 'bom-extractor',
    name: 'BOM提取器',
    icon: '📋',
    status: 'idle',
    progress: 0
  },
  {
    id: 'assembly-expert',
    name: '装配专家',
    icon: '🔧',
    status: 'idle',
    progress: 0
  }
])

// Agent对话数据
const agentDialogs = ref([])
const systemLogs = ref([])
const autoScroll = ref(true)
const dialogContainer = ref(null)

// 统计数据
const stats = reactive({
  totalTasks: 0,
  completedTasks: 0,
  activeAgents: 0,
  avgProcessTime: 0
})

// 方法
const getStatusText = (status: string) => {
  const statusMap = {
    idle: '待机中',
    working: '工作中',
    completed: '已完成',
    error: '错误'
  }
  return statusMap[status] || status
}

const clearDialogs = () => {
  agentDialogs.value = []
  systemLogs.value = []
}

const toggleAutoScroll = () => {
  autoScroll.value = !autoScroll.value
}

const startDemo = () => {
  // 演示模式：模拟Agent协作过程
  const demoDialogs = [
    {
      id: 1,
      agent: '文件管理员',
      agentIcon: '📁',
      message: '我开始分析上传的文件结构...',
      timestamp: new Date().toLocaleTimeString(),
      type: 'working',
      status: 'typing'
    },
    {
      id: 2,
      agent: 'Qwen-VL视觉分析师',
      agentIcon: '👁️',
      message: '收到文件管理员的分类结果，开始视觉分析PDF图纸...',
      timestamp: new Date().toLocaleTimeString(),
      type: 'collaborating',
      status: 'typing'
    },
    {
      id: 3,
      agent: 'BOM提取器',
      agentIcon: '📋',
      message: '我从PDF中提取到53个BOM项目，传递给推理专家...',
      timestamp: new Date().toLocaleTimeString(),
      type: 'reporting',
      status: 'complete'
    }
  ]

  // 逐个添加对话，模拟实时效果
  demoDialogs.forEach((dialog, index) => {
    setTimeout(() => {
      agentDialogs.value.push(dialog)
      updateAgentStatus(dialog.agent, 'working', dialog.message)
      scrollToBottom()
    }, index * 2000)
  })
}

const updateAgentStatus = (agentName: string, status: string, message: string) => {
  const agent = agents.value.find(a => a.name === agentName)
  if (agent) {
    agent.status = status
    if (status === 'working') {
      agent.progress = Math.min(agent.progress + 20, 90)
    } else if (status === 'completed') {
      agent.progress = 100
    }
  }

  // 更新活跃Agent数量
  stats.activeAgents = agents.value.filter(a => a.status === 'working').length
}

const scrollToBottom = () => {
  if (autoScroll.value && dialogContainer.value) {
    nextTick(() => {
      dialogContainer.value.scrollTop = dialogContainer.value.scrollHeight
    })
  }
}

const addSystemLog = (level: string, message: string) => {
  systemLogs.value.unshift({
    id: Date.now(),
    level,
    message,
    timestamp: new Date().toLocaleTimeString()
  })

  // 限制日志数量
  if (systemLogs.value.length > 100) {
    systemLogs.value = systemLogs.value.slice(0, 100)
  }
}

// WebSocket连接（用于接收后端Agent日志）
let ws = null

const connectWebSocket = () => {
  // 这里可以连接到后端WebSocket来接收实时Agent日志
  // ws = new WebSocket('ws://localhost:8000/ws/agent-logs')
  // ws.onmessage = (event) => {
  //   const data = JSON.parse(event.data)
  //   handleAgentMessage(data)
  // }
}

const handleAgentMessage = (data: any) => {
  // 处理从后端接收到的Agent消息
  if (data.type === 'agent_dialog') {
    agentDialogs.value.push(data)
    scrollToBottom()
  } else if (data.type === 'system_log') {
    addSystemLog(data.level, data.message)
  }
}

// 生命周期
onMounted(() => {
  // 初始化统计数据
  stats.totalTasks = 0
  stats.completedTasks = 0
  stats.activeAgents = 0
  stats.avgProcessTime = 0

  // 连接WebSocket（如果需要）
  // connectWebSocket()

  // 添加初始系统日志
  addSystemLog('info', 'Agent协作监控台已启动')
  addSystemLog('info', '等待Agent开始工作...')
})

onUnmounted(() => {
  // 清理WebSocket连接
  if (ws) {
    ws.close()
  }
})
</script>

<style lang="scss" scoped>
.engineer-page {
  min-height: 100vh;
  padding: 40px 0;
  background: var(--el-bg-color-page);

  .container {
    max-width: 1600px;
    margin: 0 auto;
    padding: 0 24px;
  }
}

.page-header {
  text-align: center;
  margin-bottom: 40px;

  h1 {
    font-size: 2.5rem;
    font-weight: 600;
    margin-bottom: 16px;
    background: linear-gradient(135deg, #409eff, #67c23a);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  p {
    font-size: 1.1rem;
    color: var(--el-text-color-secondary);
  }
}

// Agent状态总览
.agent-overview {
  margin-bottom: 40px;

  .overview-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 20px;

    .agent-overview-card {
      background: var(--el-bg-color);
      border-radius: 16px;
      padding: 24px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
      border: 2px solid transparent;
      transition: all 0.3s ease;

      &.active {
        border-color: var(--el-color-primary);
        box-shadow: 0 8px 30px rgba(64, 158, 255, 0.2);
        animation: pulse 2s infinite;
      }

      .agent-avatar {
        font-size: 32px;
        text-align: center;
        margin-bottom: 16px;
      }

      .agent-info {
        text-align: center;

        h3 {
          margin: 0 0 8px 0;
          font-size: 16px;
          font-weight: 600;
          color: var(--el-text-color-primary);
        }

        .agent-status {
          font-size: 14px;
          margin-bottom: 16px;

          &.idle { color: var(--el-text-color-secondary); }
          &.working { color: var(--el-color-primary); }
          &.completed { color: var(--el-color-success); }
          &.error { color: var(--el-color-danger); }
        }

        .agent-progress {
          margin-top: 12px;
        }
      }
    }
  }
}

// 主要内容区域
.main-content {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 32px;

  @media (max-width: 1200px) {
    grid-template-columns: 1fr;
  }
}

// 对话区域
.dialog-section {
  background: var(--el-bg-color);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;

    h2 {
      margin: 0;
      font-size: 1.5rem;
      font-weight: 600;
      color: var(--el-text-color-primary);
    }

    .dialog-controls {
      display: flex;
      gap: 12px;
    }
  }

  .dialog-container {
    height: 600px;
    overflow-y: auto;
    padding: 16px;
    background: var(--el-fill-color-lighter);
    border-radius: 12px;

    .dialog-message {
      display: flex;
      gap: 12px;
      margin-bottom: 16px;
      padding: 16px;
      background: var(--el-bg-color);
      border-radius: 12px;
      border-left: 4px solid var(--el-color-primary);
      transition: all 0.3s ease;

      &.working {
        border-left-color: var(--el-color-warning);
        background: rgba(230, 162, 60, 0.1);
      }

      &.collaborating {
        border-left-color: var(--el-color-info);
        background: rgba(144, 147, 153, 0.1);
      }

      &.reporting {
        border-left-color: var(--el-color-success);
        background: rgba(103, 194, 58, 0.1);
      }

      .dialog-avatar {
        font-size: 24px;
        flex-shrink: 0;
      }

      .dialog-content {
        flex: 1;

        .dialog-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;

          .agent-name {
            font-weight: 600;
            color: var(--el-text-color-primary);
          }

          .dialog-time {
            font-size: 12px;
            color: var(--el-text-color-secondary);
          }
        }

        .dialog-text {
          line-height: 1.6;
          color: var(--el-text-color-regular);

          &.typing {
            .typing-cursor {
              animation: blink 1s infinite;
              color: var(--el-color-primary);
            }
          }
        }
      }
    }

    .empty-state {
      text-align: center;
      padding: 60px 20px;
      color: var(--el-text-color-secondary);

      .empty-icon {
        font-size: 48px;
        margin-bottom: 16px;
      }

      p {
        margin-bottom: 24px;
        font-size: 16px;
      }
    }
  }
}

// 日志区域
.log-section {
  background: var(--el-bg-color);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);

  .section-header {
    margin-bottom: 24px;

    h2 {
      margin: 0;
      font-size: 1.5rem;
      font-weight: 600;
      color: var(--el-text-color-primary);
    }
  }

  .stats-panel {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
    margin-bottom: 32px;

    .stat-item {
      text-align: center;
      padding: 20px;
      background: var(--el-fill-color-lighter);
      border-radius: 12px;

      .stat-value {
        font-size: 24px;
        font-weight: 700;
        color: var(--el-color-primary);
        margin-bottom: 4px;
      }

      .stat-label {
        font-size: 12px;
        color: var(--el-text-color-secondary);
      }
    }
  }

  .system-logs {
    h3 {
      margin: 0 0 16px 0;
      font-size: 1.2rem;
      font-weight: 600;
      color: var(--el-text-color-primary);
    }

    .log-container {
      height: 300px;
      overflow-y: auto;
      background: var(--el-fill-color-darker);
      border-radius: 8px;
      padding: 12px;
      font-family: 'Courier New', monospace;

      .log-entry {
        display: flex;
        gap: 12px;
        margin-bottom: 8px;
        font-size: 12px;
        line-height: 1.4;

        .log-time {
          color: var(--el-text-color-secondary);
          flex-shrink: 0;
        }

        .log-level {
          flex-shrink: 0;
          width: 50px;
          font-weight: 600;
        }

        .log-message {
          flex: 1;
        }

        &.info {
          .log-level { color: var(--el-color-info); }
        }

        &.success {
          .log-level { color: var(--el-color-success); }
        }

        &.warning {
          .log-level { color: var(--el-color-warning); }
        }

        &.error {
          .log-level { color: var(--el-color-danger); }
        }
      }
    }
  }
}

// 动画
@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 8px 30px rgba(64, 158, 255, 0.2);
  }
  50% {
    transform: scale(1.02);
    box-shadow: 0 12px 40px rgba(64, 158, 255, 0.3);
  }
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}
</style>
