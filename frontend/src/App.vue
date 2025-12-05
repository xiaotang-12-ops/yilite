<template>
  <div id="app" class="app-container">
    <!-- 全局导航栏 -->
    <nav class="app-nav">
      <div class="nav-content">
        <div class="nav-brand">
          <img class="brand-icon" src="/image.png" alt="品牌Logo" />
          <div class="brand-text">
            <h1>易力特AI智能装配平台</h1>
            <span>AI Assembly Manual Generator</span>
          </div>
        </div>
        
        <div class="nav-menu">
          <router-link to="/" class="nav-item" active-class="active">
            <el-icon><House /></el-icon>
            <span>首页</span>
          </router-link>
          <router-link to="/generator" class="nav-item" active-class="active">
            <el-icon><DocumentAdd /></el-icon>
            <span>生成器</span>
          </router-link>
          <router-link to="/viewer" class="nav-item" active-class="active">
            <el-icon><View /></el-icon>
            <span>查看器</span>
          </router-link>
          <router-link to="/settings" class="nav-item" active-class="active">
            <el-icon><Setting /></el-icon>
            <span v-if="false">设置</span>
          </router-link>
        </div>
        
        <div class="nav-actions">
          <el-button
            circle
            @click="toggleDark()"
            class="theme-toggle"
          >
            <el-icon>
              <Moon v-if="isDark" />
              <Sunny v-else />
            </el-icon>
          </el-button>
          <el-button type="primary" @click="showHelp" class="help-btn">
            <el-icon><QuestionFilled /></el-icon>
            帮助
          </el-button>
          <el-button
            class="mobile-menu-btn"
            circle
            @click="mobileMenuOpen = true"
            v-if="isMobile"
          >
            <el-icon><Menu /></el-icon>
          </el-button>
        </div>
      </div>
    </nav>

    <el-drawer
      v-model="mobileMenuOpen"
      direction="ltr"
      size="70%"
      custom-class="mobile-drawer"
    >
      <template #header>
        <div class="drawer-header">
          <span>导航</span>
        </div>
      </template>
      <div class="drawer-menu">
        <router-link to="/" class="drawer-item" @click="mobileMenuOpen = false">
          <el-icon><House /></el-icon>
          <span>首页</span>
        </router-link>
        <router-link to="/generator" class="drawer-item" @click="mobileMenuOpen = false">
          <el-icon><DocumentAdd /></el-icon>
          <span>生成器</span>
        </router-link>
        <router-link to="/viewer" class="drawer-item" @click="mobileMenuOpen = false">
          <el-icon><View /></el-icon>
          <span>查看器</span>
        </router-link>
        <router-link to="/settings" class="drawer-item" @click="mobileMenuOpen = false">
          <el-icon><Setting /></el-icon>
          <span>设置</span>
        </router-link>
      </div>
    </el-drawer>

    <!-- 主要内容区域 -->
    <main class="app-main">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <!-- 全局背景效果 -->
    <div class="bg-effects">
      <div class="bg-grid"></div>
      <div class="bg-gradient"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { watch, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { useDark, useToggle, useMediaQuery } from '@vueuse/core'
import { Sunny, Moon, House, DocumentAdd, View, Setting, QuestionFilled, Menu } from '@element-plus/icons-vue'

const isDark = useDark()
const toggleDark = useToggle(isDark)
const isMobile = useMediaQuery('(max-width: 1024px)')
const mobileMenuOpen = ref(false)

// 更新主题CSS变量
const updateTheme = () => {
  if (isDark.value) {
    document.documentElement.style.setProperty('--bg-color', '#0a0a0a')
    document.documentElement.style.setProperty('--text-color', '#ffffff')
    document.documentElement.style.setProperty('--text-secondary', 'rgba(255,255,255,0.65)')
    document.documentElement.style.setProperty('--grid-color', '#00ffff')
    document.documentElement.style.setProperty('--accent-color', '#00ffff')
    document.documentElement.style.setProperty('--card-bg', 'rgba(0,255,255,0.15)')
    document.documentElement.style.setProperty('--active-card-bg', 'rgba(0,255,255,0.25)')
    document.documentElement.style.setProperty('--card-border', 'rgba(0,255,255,0.4)')
  } else {
    document.documentElement.style.setProperty('--bg-color', '#f5f5f5')
    document.documentElement.style.setProperty('--text-color', '#1f2937')
    document.documentElement.style.setProperty('--text-secondary', 'rgba(0,0,0,0.55)')
    document.documentElement.style.setProperty('--grid-color', '#0066cc')
    document.documentElement.style.setProperty('--accent-color', '#0066cc')
    document.documentElement.style.setProperty('--card-bg', 'rgba(0,102,204,0.10)')
    document.documentElement.style.setProperty('--active-card-bg', 'rgba(0,102,204,0.20)')
    document.documentElement.style.setProperty('--card-border', 'rgba(0,102,204,0.35)')
  }
  document.documentElement.setAttribute('data-theme', isDark.value ? 'dark' : 'light')
}

// 监听主题变化
watch(isDark, () => {
  updateTheme()
}, { immediate: true })

const showHelp = () => {
  ElMessageBox.alert(
    '这是一个智能装配说明书生成系统，支持PDF图纸和3D模型的自动解析，生成工人友好的装配说明书。',
    '系统帮助',
    {
      confirmButtonText: '了解',
      type: 'info'
    }
  )
}
</script>

<style lang="scss">
.app-container {
  min-height: 100vh;
  background: var(--el-bg-color);
  position: relative;
  overflow-x: hidden;
}

.app-nav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 70px;
  background: rgba(var(--el-bg-color-rgb), 0.8);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--el-border-color-light);
  z-index: 1000;
  
  .nav-content {
    max-width: 1400px;
    margin: 0 auto;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 24px;
  }
  
  .nav-brand {
    display: flex;
    align-items: center;
    gap: 12px;
    
    .brand-icon {
      width: 40px;
      height: 40px;
      border-radius: 10px;
      object-fit: contain;
      display: block;
      background: none;
    }
    
    .brand-text {
      h1 {
        margin: 0;
        font-size: 18px;
        font-weight: 600;
        color: var(--el-text-color-primary);
      }
      
      span {
        font-size: 12px;
        color: var(--el-text-color-secondary);
        font-weight: 400;
      }
    }
  }
  
  .nav-menu {
    display: flex;
    gap: 8px;
    
    .nav-item {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 8px 16px;
      border-radius: 8px;
      text-decoration: none;
      color: var(--el-text-color-regular);
      transition: all 0.3s ease;
      
      &:hover {
        background: var(--el-fill-color-light);
        color: var(--el-color-primary);
      }
      
      &.active {
        background: var(--el-color-primary-light-9);
        color: var(--el-color-primary);
      }
    }
  }
  
  .nav-actions {
    display: flex;
    align-items: center;
    gap: 12px;
    
    .theme-toggle {
      background: var(--el-fill-color-light);
      border: none;
    }
  }
}

.app-main {
  margin-top: 70px;
  min-height: calc(100vh - 70px);
  position: relative;
  z-index: 1;
}

.bg-effects {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 0;
  
  .bg-grid {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-image: 
      linear-gradient(rgba(var(--el-color-primary-rgb), 0.05) 1px, transparent 1px),
      linear-gradient(90deg, rgba(var(--el-color-primary-rgb), 0.05) 1px, transparent 1px);
    background-size: 50px 50px;
    animation: grid-move 20s linear infinite;
  }
  
  .bg-gradient {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: radial-gradient(
      circle at 20% 80%,
      rgba(var(--el-color-primary-rgb), 0.1) 0%,
      transparent 50%
    ),
    radial-gradient(
      circle at 80% 20%,
      rgba(var(--el-color-success-rgb), 0.1) 0%,
      transparent 50%
    );
  }
}

@keyframes grid-move {
  0% { transform: translate(0, 0); }
  100% { transform: translate(50px, 50px); }
}

// 页面切换动画
.page-enter-active,
.page-leave-active {
  transition: all 0.3s ease;
}

.page-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.page-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}

// 移动端适配
@media (max-width: 1024px) {
  .app-nav {
    height: 64px;
    .nav-content {
      padding: 0 16px;
    }
    .nav-menu {
      display: none;
    }
    .help-btn {
      display: none;
    }
    .nav-actions {
      gap: 8px;
    }
    .nav-brand h1 {
      font-size: 16px;
    }
  }

  .mobile-menu-btn {
    background: var(--el-fill-color-light);
    border: none;
  }

  .mobile-drawer {
    .el-drawer__body {
      padding: 12px 16px;
    }
  }

  .drawer-menu {
    display: flex;
    flex-direction: column;
    gap: 12px;

    .drawer-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px;
      border-radius: 10px;
      color: var(--el-text-color-regular);
      text-decoration: none;
      background: var(--el-fill-color-light);

      &:hover {
        background: var(--el-color-primary-light-9);
        color: var(--el-color-primary);
      }
    }
  }

  .app-main {
    margin-top: 64px;
  }
}
</style>
