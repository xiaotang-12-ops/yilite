<template>
  <div id="app" class="app-container">
    <!-- 全局导航栏 -->
    <nav class="app-nav">
      <div class="nav-content">
        <div
          class="nav-brand"
          @mousedown.left="handleLogoPressStart"
          @mouseup="handleLogoPressEnd"
          @mouseleave="handleLogoPressEnd"
          @contextmenu.prevent
        >
          <!-- 用户现场版本保留原 Logo 与标题，仅把隐藏设置入口改成左键长按 5 秒。 -->
          <img class="brand-icon" src="/logo.png" alt="品牌Logo" />
          <div class="brand-text">
            <h1>装配指导</h1>
            <span>Assembly Instructions</span>
          </div>
        </div>
        
        <div class="nav-menu">
          <router-link to="/" class="nav-item" active-class="active">
            <el-icon><House /></el-icon>
            <span>首页</span>
          </router-link>
          <router-link v-if="isAdmin" to="/generator" class="nav-item" active-class="active">
            <el-icon><DocumentAdd /></el-icon>
            <span>生成器</span>
          </router-link>
          <router-link to="/viewer" class="nav-item" active-class="active">
            <el-icon><View /></el-icon>
            <span>查看器</span>
          </router-link>
          <router-link to="/settings" class="nav-item" active-class="active" v-if="false">
            <el-icon v-if="false"><Setting /></el-icon>
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
          <!-- 管理员登录/退出按钮（手机端隐藏） -->
          <template v-if="!isMobile">
            <template v-if="!isAdmin">
              <el-button type="primary" @click="showLoginDialog = true" class="admin-login-btn">
                <el-icon><Lock /></el-icon>
                管理员登录
              </el-button>
            </template>
            <template v-else>
              <span class="admin-badge">
                <el-icon><User /></el-icon>
                管理员
              </span>
              <el-button @click="handleLogout" class="admin-logout-btn">
                退出
              </el-button>
            </template>
          </template>
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
        <!-- 移动端隐藏生成器入口 -->
        <router-link to="/viewer" class="drawer-item" @click="mobileMenuOpen = false">
          <el-icon><View /></el-icon>
          <span>查看器</span>
        </router-link>
        <!-- 移动端隐藏设置入口 -->
      </div>
    </el-drawer>

    <!-- 管理员登录Dialog -->
    <el-dialog
      v-model="showLoginDialog"
      title="管理员登录"
      width="400px"
      :close-on-click-modal="false"
      @closed="resetLoginForm"
    >
      <el-form :model="loginForm" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="loginForm.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            @keyup.enter="handleLogin"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showLoginDialog = false">取消</el-button>
        <el-button type="primary" @click="handleLogin">登录</el-button>
      </template>
    </el-dialog>

    <!-- 主要内容区域 -->
    <main class="app-main">
      <router-view v-slot="{ Component }">
        <component
          v-if="Component"
          :is="Component"
          :key="$route.fullPath"
        />
        <div v-else class="route-fallback">
          页面加载中，请稍候…
        </div>
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
import { watch, ref, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { storeToRefs } from 'pinia'
import { useDark, useToggle, useMediaQuery } from '@vueuse/core'
import { Sunny, Moon, House, DocumentAdd, View, Setting, Menu, Lock, User } from '@element-plus/icons-vue'
import { useAdminStore } from './stores/admin'

const isDark = useDark()
const toggleDark = useToggle(isDark)
const isMobile = useMediaQuery('(max-width: 1024px)')
const mobileMenuOpen = ref(false)
const router = useRouter()
const settingsUnlockTimer = ref<number | null>(null)
const adminStore = useAdminStore()
const { isAdmin } = storeToRefs(adminStore)

adminStore.ensureInit()

const SETTINGS_UNLOCK_KEY = 'settings_unlock_until'
const SETTINGS_UNLOCK_HOLD_MS = 5000
const SETTINGS_UNLOCK_TTL_MS = 15000

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

const showLoginDialog = ref(false)
const loginForm = ref({
  username: '',
  password: ''
})

const resetLoginForm = () => {
  loginForm.value.username = ''
  loginForm.value.password = ''
}

const handleLogin = () => {
  const username = loginForm.value.username.trim()
  const password = loginForm.value.password
  if (!username || !password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  if (username === 'admin' && password === 'admin123') {
    adminStore.login()
    showLoginDialog.value = false
    resetLoginForm()
    ElMessage.success('登录成功！')
    return
  }
  ElMessage.error('用户名或密码错误')
}

const handleLogout = () => {
  adminStore.logout()
  ElMessage.success('已退出管理员模式')
  if (router.currentRoute.value.path.startsWith('/generator')) {
    router.push('/')
  }
}

const clearSettingsUnlockTimer = () => {
  if (settingsUnlockTimer.value !== null) {
    window.clearTimeout(settingsUnlockTimer.value)
    settingsUnlockTimer.value = null
  }
}

const handleLogoPressStart = (event: MouseEvent) => {
  if (event.button !== 0) {
    return
  }

  clearSettingsUnlockTimer()
  settingsUnlockTimer.value = window.setTimeout(() => {
    sessionStorage.setItem(SETTINGS_UNLOCK_KEY, String(Date.now() + SETTINGS_UNLOCK_TTL_MS))
    clearSettingsUnlockTimer()
    router.push('/settings')
  }, SETTINGS_UNLOCK_HOLD_MS)
}

const handleLogoPressEnd = () => {
  clearSettingsUnlockTimer()
}

onBeforeUnmount(() => {
  clearSettingsUnlockTimer()
})
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
      width: 56px;
      height: 56px;
      border-radius: 12px;
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

  .admin-login-btn {
    font-weight: 600;
  }

  .admin-logout-btn {
    background: var(--el-fill-color-light);
    border: none;
  }

  .admin-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 999px;
    background: var(--el-fill-color-light);
    color: var(--text-secondary);
    font-size: 12px;
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

.route-fallback {
  padding: 48px 24px;
  text-align: center;
  color: var(--el-text-color-regular);
  font-size: 16px;
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
