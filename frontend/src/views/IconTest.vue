<template>
  <div class="icon-test-page">
    <h1>Element Plus 图标测试</h1>
    
    <div class="icon-grid">
      <div class="icon-item">
        <el-icon size="24"><circle-check /></el-icon>
        <div class="icon-name">CircleCheck</div>
        <div class="icon-kebab">&lt;circle-check /&gt;</div>
      </div>
      <div class="icon-item">
        <el-icon size="24"><circle-close /></el-icon>
        <div class="icon-name">CircleClose</div>
        <div class="icon-kebab">&lt;circle-close /&gt;</div>
      </div>
      <div class="icon-item">
        <el-icon size="24"><warning /></el-icon>
        <div class="icon-name">Warning</div>
        <div class="icon-kebab">&lt;warning /&gt;</div>
      </div>
      <div class="icon-item">
        <el-icon size="24"><info-filled /></el-icon>
        <div class="icon-name">InfoFilled</div>
        <div class="icon-kebab">&lt;info-filled /&gt;</div>
      </div>
      <div class="icon-item">
        <el-icon size="24"><document /></el-icon>
        <div class="icon-name">Document</div>
        <div class="icon-kebab">&lt;document /&gt;</div>
      </div>
      <div class="icon-item">
        <el-icon size="24"><upload /></el-icon>
        <div class="icon-name">Upload</div>
        <div class="icon-kebab">&lt;upload /&gt;</div>
      </div>
      <div class="icon-item">
        <el-icon size="24"><download /></el-icon>
        <div class="icon-name">Download</div>
        <div class="icon-kebab">&lt;download /&gt;</div>
      </div>
      <div class="icon-item">
        <el-icon size="24"><edit /></el-icon>
        <div class="icon-name">Edit</div>
        <div class="icon-kebab">&lt;edit /&gt;</div>
      </div>
      <div class="icon-item">
        <el-icon size="24"><delete /></el-icon>
        <div class="icon-name">Delete</div>
        <div class="icon-kebab">&lt;delete /&gt;</div>
      </div>
      <div class="icon-item">
        <el-icon size="24"><setting /></el-icon>
        <div class="icon-name">Setting</div>
        <div class="icon-kebab">&lt;setting /&gt;</div>
      </div>
      <div class="icon-item">
        <el-icon size="24"><user /></el-icon>
        <div class="icon-name">User</div>
        <div class="icon-kebab">&lt;user /&gt;</div>
      </div>
      <div class="icon-item">
        <el-icon size="24"><search /></el-icon>
        <div class="icon-name">Search</div>
        <div class="icon-kebab">&lt;search /&gt;</div>
      </div>
      <div class="icon-item">
        <el-icon size="24"><refresh /></el-icon>
        <div class="icon-name">Refresh</div>
        <div class="icon-kebab">&lt;refresh /&gt;</div>
      </div>
      <div class="icon-item">
        <el-icon size="24"><plus /></el-icon>
        <div class="icon-name">Plus</div>
        <div class="icon-kebab">&lt;plus /&gt;</div>
      </div>
      <div class="icon-item">
        <el-icon size="24"><minus /></el-icon>
        <div class="icon-name">Minus</div>
        <div class="icon-kebab">&lt;minus /&gt;</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
CircleCheck,
  CircleClose,
  Warning,
  InfoFilled,
  Document,
  Upload,
  Download,
  Edit,
  Delete,
  Setting,
  User,
  Search,
  Refresh,
  Plus,
  Minus
} from '@element-plus/icons-vue'
</script>

<style lang="scss" scoped>
.icon-test-page {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

h1 {
  text-align: center;
  margin-bottom: 30px;
  color: var(--el-text-color-primary);
}

.icon-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 20px;
}

.icon-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  background: var(--el-bg-color);
  
  .el-icon {
    margin-bottom: 10px;
    color: var(--el-color-primary);
  }
  
  .icon-name {
    font-weight: bold;
    margin-bottom: 5px;
    color: var(--el-text-color-primary);
  }
  
  .icon-kebab {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    font-family: monospace;
  }
}
</style>