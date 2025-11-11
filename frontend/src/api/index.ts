// API服务模块
import axios from 'axios'

// 创建axios实例
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8008/api',
  timeout: 300000, // 5分钟超时
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证token等
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    // 统一错误处理
    const message = error.response?.data?.message || error.message || '请求失败'
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

// 类型定义
export interface GenerationConfig {
  focus: 'general' | 'welding' | 'precision' | 'heavy'
  quality: 'basic' | 'standard' | 'high' | 'critical'
  language: 'zh' | 'en'
  requirements: string
}

export interface UploadedFile {
  id: string
  filename: string
  path: string
  size: number
}

export interface UploadResponse {
  success: boolean
  message: string
  data: {
    pdf_files: UploadedFile[]
    model_files: UploadedFile[]
  }
}

export interface GenerationTask {
  task_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  message: string
  result?: {
    output_dir: string
    output_file: string
    statistics: Record<string, any>
    files: string[]
  }
  created_at: string
  updated_at: string
}

export interface GenerationRequest {
  config: GenerationConfig
  pdf_files: string[]
  model_files: string[]
}

// API方法
export const apiService = {
  // 健康检查
  async healthCheck() {
    return api.get('/health')
  },

  // 上传文件
  async uploadFiles(pdfFiles: File[], modelFiles: File[]): Promise<UploadResponse> {
    const formData = new FormData()
    
    // 添加PDF文件
    pdfFiles.forEach(file => {
      formData.append('pdf_files', file)
    })
    
    // 添加模型文件
    modelFiles.forEach(file => {
      formData.append('model_files', file)
    })
    
    return api.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      onUploadProgress: (progressEvent) => {
        const percentCompleted = Math.round(
          (progressEvent.loaded * 100) / (progressEvent.total || 1)
        )
        console.log('Upload progress:', percentCompleted)
      }
    })
  },

  // 开始生成
  async startGeneration(request: GenerationRequest) {
    return api.post('/generate', request)
  },

  // 获取任务状态
  async getTaskStatus(taskId: string): Promise<GenerationTask> {
    return api.get(`/task/${taskId}`)
  },

  // 获取任务列表
  async listTasks() {
    return api.get('/tasks')
  },

  // 下载结果
  async downloadResult(taskId: string) {
    return api.get(`/download/${taskId}`, {
      responseType: 'blob'
    })
  },

  // 删除任务
  async deleteTask(taskId: string) {
    return api.delete(`/task/${taskId}`)
  },

  // 获取生成结果预览
  async getResultPreview(taskId: string) {
    return api.get(`/preview/${taskId}`)
  },

  // 工人界面相关API
  // 获取装配数据
  async getAssemblyData(taskId: string) {
    return api.get(`/assembly/${taskId}`)
  },

  // 提交问题报告
  async submitIssueReport(issueData: any) {
    return api.post('/issue-report', issueData)
  },

  // 请求帮助
  async requestHelp(helpData: any) {
    return api.post('/help-request', helpData)
  },

  // 更新任务进度
  async updateTaskProgress(taskId: string, progress: number) {
    return api.put(`/task/${taskId}/progress`, { progress })
  }
}

// 轮询任务状态的工具函数
export const pollTaskStatus = (
  taskId: string,
  onUpdate: (task: GenerationTask) => void,
  onComplete: (task: GenerationTask) => void,
  onError: (error: any) => void,
  interval: number = 2000
) => {
  const poll = async () => {
    try {
      const task = await apiService.getTaskStatus(taskId)
      onUpdate(task)
      
      if (task.status === 'completed') {
        onComplete(task)
        return
      }
      
      if (task.status === 'failed') {
        onError(new Error(task.message))
        return
      }
      
      // 继续轮询
      setTimeout(poll, interval)
      
    } catch (error) {
      onError(error)
    }
  }
  
  // 开始轮询
  poll()
}

// 文件下载工具函数
export const downloadFile = (blob: Blob, filename: string) => {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

// 文件大小格式化
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

// 时间格式化
export const formatTime = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 错误处理工具
export const handleApiError = (error: any, defaultMessage: string = '操作失败') => {
  const message = error.response?.data?.message || error.message || defaultMessage
  ElMessage.error(message)
  console.error('API Error:', error)
  return message
}

// WebSocket连接（用于实时状态更新）
export class TaskWebSocket {
  private ws: WebSocket | null = null
  private taskId: string
  private onUpdate: (task: GenerationTask) => void
  private onError: (error: any) => void

  constructor(
    taskId: string,
    onUpdate: (task: GenerationTask) => void,
    onError: (error: any) => void
  ) {
    this.taskId = taskId
    this.onUpdate = onUpdate
    this.onError = onError
  }

  connect() {
    const wsUrl = `ws://localhost:8008/ws/task/${this.taskId}`
    this.ws = new WebSocket(wsUrl)

    this.ws.onopen = () => {
      console.log('WebSocket connected')
    }

    this.ws.onmessage = (event) => {
      try {
        const task = JSON.parse(event.data)
        this.onUpdate(task)
      } catch (error) {
        this.onError(error)
      }
    }

    this.ws.onerror = (error) => {
      this.onError(error)
    }

    this.ws.onclose = () => {
      console.log('WebSocket disconnected')
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }
}

export default api
