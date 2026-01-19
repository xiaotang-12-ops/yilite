import { createApp, nextTick } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import Home from './views/HomeNew.vue'
import Generator from './views/Generator.vue'
import Viewer from './views/Viewer.vue'
import ManualViewer from './views/ManualViewer.vue'
import Engineer from './views/Engineer.vue'
import Settings from './views/Settings.vue'
import GLBTest from './views/GLBTest.vue'
import SimpleGLBTest from './views/SimpleGLBTest.vue'
import IconTest from './views/IconTest.vue'
import VersionHistory from './views/VersionHistory.vue'

import './style/main.scss'

// 路由配置
const routes = [
  { path: '/', name: 'Home', component: Home },
  { path: '/generator', name: 'Generator', component: Generator },
  { path: '/viewer/:id?', name: 'Viewer', component: Viewer, props: true },
  { path: '/manual/:taskId', name: 'ManualViewer', component: ManualViewer, props: true },
  { path: '/version-history/:taskId', name: 'VersionHistory', component: VersionHistory, props: true },
  { path: '/engineer', name: 'Engineer', component: Engineer },
  { path: '/settings', name: 'Settings', component: Settings },
  { path: '/glb-test', name: 'GLBTest', component: GLBTest },
  { path: '/simple-glb-test', name: 'SimpleGLBTest', component: SimpleGLBTest },
  { path: '/icon-test', name: 'IconTest', component: IconTest }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

const SETTINGS_UNLOCK_KEY = 'settings_unlock_until'

router.beforeEach((to, _from, next) => {
  if (to.path === '/settings') {
    const unlockUntil = Number(sessionStorage.getItem(SETTINGS_UNLOCK_KEY) || 0)
    if (unlockUntil && unlockUntil >= Date.now()) {
      sessionStorage.removeItem(SETTINGS_UNLOCK_KEY)
      next()
      return
    }
    sessionStorage.removeItem(SETTINGS_UNLOCK_KEY)
    next({ path: '/' })
    return
  }
  next()
})

// 捕获路由错误，避免静默失败
router.onError((err) => {
  console.error('router error', err)
})

// 创建应用
const app = createApp(App)
const pinia = createPinia()

// 注册Element Plus图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(pinia)
app.use(router)
app.use(ElementPlus)

// 全局错误处理，避免渲染错误被吞掉
app.config.errorHandler = (err, instance, info) => {
  console.error('vue error', err, { instance, info })
}

// 隐藏加载屏幕
app.mount('#app')

// 应用挂载后隐藏加载屏幕
nextTick(() => {
  const loading = document.getElementById('loading')
  if (loading) {
    setTimeout(() => {
      loading.style.opacity = '0'
      setTimeout(() => {
        loading.remove()
      }, 500)
    }, 1000)
  }
})
