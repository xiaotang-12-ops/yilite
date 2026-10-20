<!-- 成果统计固定在屏幕左侧，三维厂区和展厅环境占据整幅画面。-codex，2026-10-09 -->
<template>
  <section class="factory-page" :class="{ 'desktop-layout': desktop }">
    <template v-if="desktop">
      <div class="factory-content" :class="{ 'is-preparing': !pageReady }" :inert="!pageReady" :aria-hidden="!pageReady">
      <FactoryStage v-if="!sceneError" :key="sceneVersion" @state="onSceneState" />
      <div class="reading-scrim" aria-hidden="true"></div>
      <aside class="results-panel" :class="{ 'compact-data': compactData }" aria-label="装配成果看板">
        <header class="results-heading">
          <p class="eyebrow">EALITA <span>/</span> DIGITAL MANUFACTURING</p>
          <h1 :class="{ 'long-title': Array.from(branding.branding.dashboard_title).length > 8, 'dense-title': denseTitle }">{{ branding.branding.dashboard_title }}</h1>
          <span class="heading-rule" aria-hidden="true"></span>
        </header>
        <section class="results-data" :aria-busy="loading">
          <div class="metrics-overview">
            <div class="primary-metric"><strong>{{ counts?.total ?? '—' }}</strong><span>已生成说明书项目</span></div>
            <div class="secondary-metric"><span class="metric-icon teal"><el-icon><Operation /></el-icon></span><div><strong>{{ formatMetric(metrics?.assemblySteps) }}</strong><span>装配步骤</span></div></div>
            <div class="secondary-metric"><span class="metric-icon orange"><el-icon><Document /></el-icon></span><div><strong>{{ formatMetric(metrics?.drawingPages) }}</strong><span>引用图纸页</span></div></div>
          </div>
          <p v-if="metrics && (metrics.assemblySteps === null || metrics.drawingPages === null)" class="metric-warning" role="status">部分项目统计暂不可用 <button @click="refresh">重试</button></p>
          <section class="status-section" aria-labelledby="status-heading">
            <h2 id="status-heading" class="section-title">项目状态分布</h2>
            <p class="chart-caption">单位：项目</p>
            <div class="status-chart">
              <div v-for="item in categories" :key="item.key" class="status-column">
                <div class="column-plot" :aria-label="`${item.label}：${counts ? counts[item.key] : '不可用'}个项目`">
                  <div class="column-fill" :class="item.key" :style="{ height: `${counts ? counts[item.key] / categoryMaximum * 100 : 0}%` }"><strong>{{ counts ? counts[item.key] : '—' }}</strong></div>
                </div>
                <strong class="column-label">{{ item.label }}</strong>
                <span class="column-summary">{{ formatMetric(categoryMetrics?.[item.key].assemblySteps) }}步 · {{ formatMetric(categoryMetrics?.[item.key].drawingPages) }}页</span>
              </div>
            </div>
          </section>
          <section class="scale-section" aria-labelledby="scale-heading">
            <h2 id="scale-heading" class="section-title">项目步骤规模</h2>
            <p class="chart-caption">单个说明书步骤数</p>
            <div v-for="(label, index) in scaleLabels" :key="label" class="scale-row">
              <span>{{ label }}</span><span class="scale-track" aria-hidden="true"><i :style="{ width: `${stepDistribution ? stepDistribution.bins[index].count / scaleMaximum * 100 : 0}%` }"></i></span><strong>{{ stepDistribution ? stepDistribution.bins[index].count : '—' }}<small> 项</small></strong>
            </div>
            <p v-if="stepDistribution && (stepDistribution.zero || stepDistribution.unknown)" class="distribution-note">另有 <template v-if="stepDistribution.zero">{{ stepDistribution.zero }} 项为零步骤</template><template v-if="stepDistribution.zero && stepDistribution.unknown">，</template><template v-if="stepDistribution.unknown">{{ stepDistribution.unknown }} 项步骤暂不可用</template></p>
          </section>
          <div v-if="loading || error" class="data-connection" role="status" :class="{ failed: error }">
            <span v-if="error">{{ error }}</span>
            <span v-else-if="loading">正在读取系统数据…</span>
            <button v-if="error" :disabled="loading" @click="refresh">重试 ↻</button>
          </div>
        </section>
        <section class="recent-projects" aria-labelledby="recent-heading">
          <router-link class="recent-heading" to="/viewer"><h2 id="recent-heading" class="section-title">最近更新项目</h2><span aria-hidden="true">›</span></router-link>
          <div class="recent-columns" aria-hidden="true"><span>项目</span><span>状态</span><span>步骤</span><span>引用页</span></div>
          <router-link v-for="project in recent" :key="project.id" class="recent-row" :to="{ name: 'ManualViewer', params: { taskId: project.id }, query: { source: 'viewer' } }">
            <span class="recent-name" :title="project.name">{{ project.name }}</span><span class="recent-status"><i :class="project.category"></i>{{ PROJECT_CATEGORY_LABELS[project.category] }}</span><strong class="recent-number" :aria-label="`装配步骤${formatMetric(project.assemblySteps)}`">{{ formatMetric(project.assemblySteps) }}</strong><span class="recent-number" :aria-label="`引用图纸页${formatMetric(project.drawingPages)}`">{{ formatMetric(project.drawingPages) }}</span>
          </router-link>
          <p v-if="counts?.total === 0" class="empty-recent">暂无已生成的说明书项目</p>
          <p v-else-if="!counts" class="empty-recent">{{ loading ? '正在读取最近更新…' : '最近更新暂不可用' }}</p>
        </section>
      </aside>
      <div class="campus-sign" aria-hidden="true"><strong>EALITA</strong><span>ENGINEERING<br>IN EVERY DETAIL.</span><i></i></div>
      </div>
      <div v-if="!pageReady" class="page-preparation" :class="{ 'has-error': sceneError }" role="status" aria-live="polite">
        <span v-if="!sceneError" class="preparation-ring" aria-hidden="true"></span>
        <strong>{{ sceneError ? '厂区暂时无法显示' : '正在准备厂区成果看板' }}</strong>
        <p>{{ sceneError || (sceneReady && loading ? '正在读取项目数据…' : sceneStatus) }}</p>
        <button v-if="sceneError" @click="retryScene">重新加载</button>
      </div>
    </template>
    <div v-else class="desktop-notice">
      <el-icon :size="48"><Monitor /></el-icon>
      <h1>请在电脑上查看厂区模型</h1>
      <p>装配成果看板及三维厂区仅面向电脑端开放。</p>
      <router-link to="/">返回首页</router-link>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, ref, watch, onBeforeUnmount } from 'vue'
import { useMediaQuery } from '@vueuse/core'
import { Monitor, Document, Operation } from '@element-plus/icons-vue'
import { useBrandingStore } from '../../stores/branding'
import { isMobileDevice } from '../../utils/isMobileDevice'
import { PROJECT_CATEGORY_LABELS } from '../../constants/projectCategories'
import { useFactoryStats } from './useFactoryStats'

const wideScreen = useMediaQuery('(min-width: 1025px)')
const mobileDevice = isMobileDevice()
const desktop = computed(() => wideScreen.value && !mobileDevice)
const sceneReady = ref(false)
const sceneError = ref('')
const sceneStatus = ref('正在加载场景资源…')
const sceneVersion = ref(0)
let startupTimer: ReturnType<typeof setTimeout> | undefined
const FactoryStage = defineAsyncComponent({
  loader: () => import('./components/FactoryStage.vue'),
  onError(_error, _retry, fail) { sceneError.value = '场景程序加载失败，请刷新页面重试。'; fail() },
})
const branding = useBrandingStore()
const { counts, metrics, categoryMetrics, stepDistribution, recent, loading, error, refresh } = useFactoryStats(desktop)
const pageReady = computed(() => sceneReady.value && !sceneError.value && !loading.value && (branding.loaded || !!branding.loadError))
function onSceneState(state: { ready: boolean; error: string; status: string }) {
  sceneReady.value = state.ready
  sceneStatus.value = state.status
  if (state.error) sceneError.value = state.error
}
function armTimeout() {
  clearTimeout(startupTimer)
  if (desktop.value) startupTimer = setTimeout(() => { sceneError.value = '准备时间过长，请检查网络后重新加载。' }, 45000)
}
function retryScene() {
  sceneReady.value = false
  sceneError.value = ''
  sceneStatus.value = '正在重新准备场景…'
  sceneVersion.value++
  void refresh()
  armTimeout()
}
watch([pageReady, sceneError], ([ready, failure]) => { if (ready || failure) clearTimeout(startupTimer) })
watch(desktop, () => { sceneReady.value = false; sceneError.value = ''; armTimeout() }, { immediate: true })
onBeforeUnmount(() => clearTimeout(startupTimer))
const categories = (['published', 'pending', 'archived'] as const).map(key => ({ key, label: PROJECT_CATEGORY_LABELS[key] }))
// 柱/条都以同一最大项目数为基准，保证比例准确；空集合用1仅避免除零，不造项目。-codex，2026-10-12
const categoryMaximum = computed(() => Math.max(1, ...categories.map(item => counts.value?.[item.key] ?? 0)))
const scaleLabels = ['1–20 步', '21–50 步', '51–80 步', '81 步及以上']
const scaleMaximum = computed(() => Math.max(1, ...(stepDistribution.value?.bins.map(item => item.count) ?? [])))
// 合法双行标题或摘要告警占用额外空间时，收缩图形留出明细空间；不缩放文字或隐藏数据。-codex，2026-10-12
const compactData = computed(() => branding.branding.dashboard_title.includes('\n') || Array.from(branding.branding.dashboard_title).length > 16 || !!(metrics.value && (metrics.value.assemblySteps === null || metrics.value.drawingPages === null)) || !!(stepDistribution.value?.zero || stepDistribution.value?.unknown))
// 24字符允许极不均匀的双行标题，避免第一行软换行变成第三行；只调整这种标题的字号。-codex，2026-10-12
const denseTitle = computed(() => branding.branding.dashboard_title.includes('\n') && branding.branding.dashboard_title.split('\n').some(line => Array.from(line).length > 17))
const formatMetric = (value: number | null | undefined) => value == null ? '—' : value.toLocaleString('zh-CN')
</script>

<style scoped>
.factory-page { --ink:#1d2c38; --accent:#df641e; position:relative; min-height:calc(100vh - 70px); background:#edf0f1; color:var(--ink); box-sizing:border-box; }
.desktop-layout { height:calc(100dvh - 70px); overflow:hidden; }
.factory-content { position:absolute; inset:0; }.factory-content.is-preparing { visibility:hidden; pointer-events:none; }
.page-preparation { position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:18px; background:radial-gradient(ellipse at 50% 38%,#fafcfd,#e9edf0 70%); color:#304c5c; z-index:4; }
.page-preparation strong { font-size:21px; font-weight:600; }.page-preparation p { font-size:14px; color:#677e8b; margin:0; }.preparation-ring { width:38px; height:38px; border:2px solid #cddade; border-top-color:#c17a39; border-radius:50%; animation:prepare-spin 1.1s linear infinite; }
.page-preparation button { margin-top:8px; border:1px solid #8da4ad; color:#345b6c; border-radius:7px; background:#ffffffc9; padding:10px 22px; cursor:pointer; }.page-preparation button:hover { background:#fff; border-color:#b77335; }
@keyframes prepare-spin { to { transform:rotate(360deg); } }
@media(prefers-reduced-motion:reduce) { .preparation-ring { animation:none; } }
.reading-scrim { position:absolute; inset:0; pointer-events:none; background:linear-gradient(90deg,#fafbfbea 0%,#fafbfbdc 14%,#fafbfba3 21%,#fafbfb00 37%); }
.results-panel { --section-gap:10px; --plot-height:96px; line-height:1.3; position:relative; z-index:2; width:clamp(330px,24vw,460px); margin-left:clamp(28px,3.6vw,72px); padding-top:22px; }
.results-panel.compact-data { --section-gap:6px; --plot-height:48px; padding-top:14px; }.compact-data h1.long-title { font-size:26px; }.compact-data .primary-metric strong { font-size:60px; }.compact-data .status-chart { margin-top:32px; }.compact-data .scale-row { height:24px; }
.compact-data h1.dense-title { font-size:21px; }
.eyebrow { margin:0 0 14px; color:var(--accent); letter-spacing:1.8px; font:600 12px 'Bahnschrift',sans-serif; white-space:nowrap; }.eyebrow span { margin:0 7px; color:#2b3940; }
h1 { margin:0; font-size:46px; font-weight:750; line-height:1.2; letter-spacing:-1.5px; white-space:pre-wrap; overflow-wrap:anywhere; }h1.long-title { font-size:30px; letter-spacing:-.5px; }
.heading-rule { display:block; width:42px; height:3px; margin-top:14px; background:var(--accent); }.results-data { margin-top:16px; }
.metrics-overview { display:grid; grid-template-columns:1.14fr 1.03fr .87fr; align-items:center; gap:12px; padding-bottom:16px; border-bottom:1px solid #70828b24; }
.primary-metric strong { display:block; font:600 68px/.96 'Bahnschrift',sans-serif; font-variant-numeric:tabular-nums; letter-spacing:-3px; }.primary-metric>span { display:block; color:#536674; font-size:14px; margin-top:8px; white-space:nowrap; }
.secondary-metric { display:flex; align-items:center; gap:10px; border-left:1px solid #70828b24; padding-left:14px; }.secondary-metric>div { min-width:0; }.secondary-metric strong { display:block; font:600 29px/1.1 'Bahnschrift',sans-serif; font-variant-numeric:tabular-nums; }.secondary-metric>div>span { display:block; margin-top:6px; color:#536674; font-size:13px; white-space:nowrap; }
.metric-icon { display:grid; place-items:center; flex:0 0 32px; height:32px; border:2px solid #fff; border-radius:50%; font-size:18px; }.teal { color:#138c89; background:#eaf5f2; }.orange { color:#d97632; background:#fff2e6; }
.section-title { margin:0; display:flex; align-items:center; gap:9px; font-size:18px; font-weight:700; line-height:1.3; }.section-title::before { content:''; width:3px; height:15px; background:#1aa1a4; border-radius:1px; flex-shrink:0; }
.chart-caption { margin:5px 0 0 12px; color:#667b86; font-size:13px; line-height:1.3; }
.status-section { margin-top:var(--section-gap); }.status-chart { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); margin-top:25px; }.status-column { min-width:0; text-align:center; }.column-plot { height:var(--plot-height); display:flex; align-items:flex-end; justify-content:center; border-bottom:1px solid #74838b; }
.column-fill { width:clamp(40px,3.7vw,66px); position:relative; border-radius:6px 6px 0 0; }.column-fill.published { background:linear-gradient(#21b1b5,#a3d8d8); }.column-fill.pending { background:linear-gradient(#fa8b1a,#ecc794); }.column-fill.archived { background:linear-gradient(#7f98a9,#c6d0d6); }.column-fill strong { position:absolute; bottom:100%; left:0; right:0; padding-bottom:6px; font:600 26px/1 'Bahnschrift',sans-serif; color:var(--ink); font-variant-numeric:tabular-nums; }
.column-label { display:block; margin-top:8px; font-size:14px; line-height:1.3; }.column-summary { display:block; margin-top:4px; color:#637888; font-size:13px; white-space:nowrap; font-variant-numeric:tabular-nums; }
.scale-section { margin-top:var(--section-gap); padding-top:10px; border-top:1px solid #70828b24; }.scale-section .chart-caption { margin-bottom:7px; }.scale-row { display:grid; grid-template-columns:86px minmax(0,1fr) 42px; align-items:center; gap:10px; height:26px; color:#405866; font-size:13px; }.scale-row>strong { text-align:right; font:600 15px 'Bahnschrift',sans-serif; font-variant-numeric:tabular-nums; }.scale-row small { font-size:12px; font-weight:400; }.scale-track { height:10px; background:#d6e0e466; border-radius:6px; }.scale-track i { display:block; height:100%; border-radius:inherit; background:linear-gradient(90deg,#179ca0,#58b1b5); }
.distribution-note { margin:6px 0 0; color:#687b86; font-size:12px; line-height:1.4; }
.recent-projects { margin-top:var(--section-gap); border-top:1px solid #70828b24; padding-top:10px; }.recent-heading { display:flex; align-items:center; justify-content:space-between; text-decoration:none; color:var(--ink); padding-bottom:8px; }.recent-heading>span { line-height:1; font-size:23px; color:#72838b; }
.recent-columns,.recent-row { display:grid; grid-template-columns:minmax(0,1fr) 68px 40px 44px; align-items:center; gap:10px; }.recent-columns { color:#667b86; font-size:13px; min-height:25px; border-bottom:1px solid #70828b24; }.recent-columns>span:nth-child(n+3) { text-align:center; }.recent-row { min-height:33px; border-bottom:1px solid #70828b1c; text-decoration:none; color:#405866; font-size:13px; }.recent-name { min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }.recent-status { display:flex; align-items:center; gap:5px; font-size:12px; white-space:nowrap; }.recent-status i { width:6px; height:6px; border-radius:50%; flex-shrink:0; }.published { background:#169a9a; }.pending { background:#e99a32; }.archived { background:#9aa8b5; }.recent-number { text-align:center; font:500 14px 'Bahnschrift',sans-serif; font-variant-numeric:tabular-nums; }.recent-row strong.recent-number { font-weight:600; }
.recent-row:hover,.recent-heading:hover { color:var(--accent); background:#ffffff60; }.empty-recent { color:#697d87; font-size:13px; margin:12px 0; }
.data-connection,.metric-warning { display:flex; justify-content:space-between; align-items:center; gap:8px; margin:8px 0 0; color:#687b86; font-size:12px; min-height:22px; }.data-connection.failed,.metric-warning { color:#ae5428; }.data-connection button,.metric-warning button { border:0; background:transparent; color:#526b79; padding:4px; font:inherit; white-space:nowrap; cursor:pointer; }.data-connection button:disabled { opacity:.5; cursor:default; }
.campus-sign { position:absolute; right:4.4%; top:42px; pointer-events:none; color:#4b5e6c; }.campus-sign strong { font:600 14px 'Bahnschrift',sans-serif; letter-spacing:5px; }.campus-sign span { display:block; margin-top:13px; font:400 9px/2.2 'Bahnschrift',sans-serif; letter-spacing:3px; }.campus-sign i { display:block; height:2px; width:26px; background:var(--accent); margin-top:12px; }
button:focus-visible,a:focus-visible { outline:2px solid var(--accent); outline-offset:-2px; }
.desktop-notice { min-height:70vh; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:20px; color:#607785; text-align:center; padding:24px; }.desktop-notice h1 { font-size:22px; letter-spacing:0; white-space:normal; }.desktop-notice p { margin:0; }.desktop-notice a { color:#367c91; }
/* 主视口保留竖柱主图；矮电脑窗口只收图形弹性高度，不裁掉数据或制造内部滚动。-codex，2026-10-12 */
@media(max-width:1400px) { .results-panel { width:350px; margin-left:28px; }.metrics-overview { gap:8px; }.secondary-metric { gap:7px; padding-left:8px; }.metric-icon { flex-basis:24px; height:24px; font-size:15px; }.secondary-metric strong { font-size:24px; }.primary-metric strong { font-size:68px; }.primary-metric>span { font-size:12px; }.secondary-metric>div>span { font-size:12px; }.recent-columns,.recent-row { grid-template-columns:minmax(0,1fr) 62px 34px 40px; gap:6px; } }
@media(max-height:800px) { .results-panel { --section-gap:12px; --plot-height:100px; padding-top:18px; }.eyebrow { margin-bottom:8px; }h1 { font-size:38px; }h1.long-title { font-size:26px; line-height:1.15; }.heading-rule { margin-top:9px; }.results-data { margin-top:10px; }.metrics-overview { padding-bottom:10px; }.primary-metric strong { font-size:62px; }.primary-metric>span { margin-top:5px; }.status-chart { margin-top:25px; }.scale-row { height:23px; }.recent-projects,.scale-section { padding-top:8px; }.recent-heading { padding-bottom:4px; }.recent-row { min-height:30px; } }
@media(max-height:700px) { .results-panel { --section-gap:8px; --plot-height:66px; padding-top:12px; }.eyebrow { margin-bottom:6px; }h1 { font-size:32px; }h1.long-title { font-size:23px; }.heading-rule { margin-top:7px; }.primary-metric strong { font-size:48px; }.metrics-overview { padding-bottom:7px; }.secondary-metric strong { font-size:24px; }.status-chart { margin-top:24px; }.scale-row { height:22px; }.chart-caption { margin-top:3px; }.recent-row { min-height:28px; }.section-title { font-size:16px; } }
</style>
