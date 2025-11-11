<template>
  <div class="glb-test-page">
    <div class="container">
      <h1>GLB文件测试页面</h1>
      
      <!-- 文件选择 -->
      <div class="file-selector">
        <h3>选择GLB文件进行测试</h3>
        <el-select v-model="selectedFile" placeholder="选择GLB文件" @change="loadSelectedFile">
          <el-option
            v-for="file in glbFiles"
            :key="file.path"
            :label="file.name"
            :value="file.path"
          />
        </el-select>
        
        <div class="file-info" v-if="selectedFile">
          <p>当前文件: {{ selectedFile }}</p>
          <p>文件大小: {{ currentFileSize }}</p>
        </div>
      </div>
      
      <!-- 3D查看器 -->
      <div class="viewer-section">
        <h3>3D模型查看器</h3>
        <div class="viewer-container">
          <WorkerThreeViewer 
            v-if="selectedFile"
            :model-url="selectedFile"
            :key="selectedFile"
            @part-selected="handlePartSelected"
            @view-changed="handleViewChanged"
          />
          <div v-else class="no-file-selected">
            <el-icon size="64"><Document /></el-icon>
            <p>请选择一个GLB文件进行查看</p>
          </div>
        </div>
      </div>
      
      <!-- 测试信息 -->
      <div class="test-info">
        <h3>测试信息</h3>
        <div class="info-grid">
          <div class="info-item">
            <label>可用GLB文件:</label>
            <span>{{ glbFiles.length }} 个</span>
          </div>
          <div class="info-item">
            <label>当前选择:</label>
            <span>{{ selectedFile || '无' }}</span>
          </div>
          <div class="info-item">
            <label>加载状态:</label>
            <span>{{ loadingStatus }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Document } from '@element-plus/icons-vue'
import WorkerThreeViewer from '@/components/worker/WorkerThreeViewer.vue'

// 响应式数据
const selectedFile = ref('')
const currentFileSize = ref('')
const loadingStatus = ref('未加载')

// GLB文件列表
const glbFiles = ref([
  {
    name: '产品测试.glb',
    path: '/output/processor_test/产品测试.glb',
    size: '26.3 MB'
  },
  {
    name: '组件图1.glb', 
    path: '/output/processor_test/组件图1.glb',
    size: '492 KB'
  },
  {
    name: '产品测试_trimesh.glb',
    path: '/output/trimesh_test/产品测试.glb',
    size: '26.3 MB'
  },
  {
    name: '组件图1_trimesh.glb',
    path: '/output/trimesh_test/组件图1.glb', 
    size: '492 KB'
  },
  {
    name: '组件图2_trimesh.glb',
    path: '/output/trimesh_test/组件图2.glb',
    size: '104 KB'
  }
])

// 方法
const loadSelectedFile = () => {
  if (selectedFile.value) {
    loadingStatus.value = '加载中...'
    
    const fileInfo = glbFiles.value.find(f => f.path === selectedFile.value)
    currentFileSize.value = fileInfo?.size || '未知'
    
    // 模拟加载延迟
    setTimeout(() => {
      loadingStatus.value = '加载完成'
    }, 1000)
  }
}

const handlePartSelected = (partId: string) => {
  console.log('选中零件:', partId)
  ElMessage.info(`选中零件: ${partId}`)
}

const handleViewChanged = (viewType: string) => {
  console.log('视图变化:', viewType)
}

// 生命周期
onMounted(() => {
  console.log('GLB测试页面已加载')
  loadingStatus.value = '就绪'
})
</script>

<style lang="scss" scoped>
.glb-test-page {
  min-height: 100vh;
  background: var(--el-bg-color-page);
  padding: 20px 0;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 24px;
}

h1 {
  text-align: center;
  color: var(--el-text-color-primary);
  margin-bottom: 40px;
}

.file-selector {
  background: var(--el-bg-color);
  padding: 24px;
  border-radius: 12px;
  margin-bottom: 30px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  
  h3 {
    margin-bottom: 16px;
    color: var(--el-text-color-primary);
  }
  
  .el-select {
    width: 300px;
  }
  
  .file-info {
    margin-top: 16px;
    padding: 12px;
    background: var(--el-fill-color-light);
    border-radius: 8px;
    
    p {
      margin: 4px 0;
      color: var(--el-text-color-secondary);
    }
  }
}

.viewer-section {
  background: var(--el-bg-color);
  padding: 24px;
  border-radius: 12px;
  margin-bottom: 30px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  
  h3 {
    margin-bottom: 16px;
    color: var(--el-text-color-primary);
  }
}

.viewer-container {
  height: 600px;
  border-radius: 8px;
  overflow: hidden;
  background: #f5f5f5;
  
  .no-file-selected {
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: var(--el-text-color-secondary);
    
    .el-icon {
      margin-bottom: 16px;
      color: var(--el-text-color-placeholder);
    }
  }
}

.test-info {
  background: var(--el-bg-color);
  padding: 24px;
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  
  h3 {
    margin-bottom: 16px;
    color: var(--el-text-color-primary);
  }
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: var(--el-fill-color-light);
  border-radius: 8px;
  
  label {
    font-weight: 500;
    color: var(--el-text-color-regular);
  }
  
  span {
    color: var(--el-text-color-primary);
  }
}

@media (max-width: 768px) {
  .info-grid {
    grid-template-columns: 1fr;
  }
  
  .file-selector .el-select {
    width: 100%;
  }
  
  .viewer-container {
    height: 400px;
  }
}
</style>
