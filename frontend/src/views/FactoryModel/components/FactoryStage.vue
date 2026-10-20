<!-- 厂区铺满画布，仅保留鼠标操作提示与复位，不提供预设视角栏。-codex，2026-10-09 -->
<template>
  <div class="factory-stage-shell">
    <div ref="container" class="factory-canvas" aria-label="易力特厂房三维模型" :aria-busy="!ready && !error">
      <div v-if="!ready || error" class="stage-message" role="status">
        <template v-if="error"><strong>模型暂时无法显示</strong><span>{{ error }}</span><button @click="reload">重新加载</button></template>
        <template v-else><span class="loading-ring"></span><strong>正在载入易力特厂区</strong><span>{{ status }}</span></template>
      </div>
    </div>
    <div v-if="ready && !error" class="scene-label"><span class="mouse-mark" aria-hidden="true"></span>拖动探索 <i>·</i> 滚轮缩放</div>
    <button class="reset-button" aria-label="复位视角" :disabled="!ready" @click="setView('overview')"><span aria-hidden="true">↻</span><small>复位</small></button>
  </div>
</template>
<script setup lang="ts">
import { useFactoryScene } from '../useFactoryScene'
import { watch } from 'vue'
const emit = defineEmits<{ state: [value: { ready: boolean; error: string; status: string }] }>()
const { container, ready, error, status, setView } = useFactoryScene()
watch([ready, error, status], () => emit('state', { ready: ready.value, error: error.value, status: status.value }), { immediate: true })
const reload = () => window.location.reload()
</script>
<style scoped>
.factory-stage-shell, .factory-canvas { position: absolute; inset: 0; min-width: 0; min-height: 0; }
.factory-canvas :deep(canvas) { display: block; width: 100%; height: 100%; touch-action: none; cursor: grab; }
.factory-canvas :deep(canvas:active) { cursor: grabbing; }
.stage-message { position: absolute; inset: 0 0 0 28%; display: flex; align-items: center; justify-content: center; flex-direction: column; gap: 14px; color: #4d6b7b; z-index: 1; }
.stage-message span { font-size: 13px; }.stage-message button { border: 1px solid #8c9ea6; border-radius: 5px; padding: 8px 16px; background: #fff9; color: inherit; cursor: pointer; }
.scene-label { position: absolute; bottom: 40px; left: 3.6%; pointer-events: none; display: flex; align-items: center; gap: 10px; color: #667681; font-size: 12px; z-index: 2; }
.scene-label i { font-style: normal; }.mouse-mark { position: relative; width: 19px; height: 30px; border: 1.3px solid #73818a; border-radius: 12px; margin-right: 5px; }
.mouse-mark::after { content: ''; position: absolute; top: 5px; left: 8px; height: 7px; border-left: 1px solid #73818a; }
.reset-button { position: absolute; right: 3.6%; bottom: 48px; width: 58px; height: 58px; border: 1px solid #ffffffab; border-radius: 50%; background: #ffffffc7; backdrop-filter: blur(12px); box-shadow: 0 7px 25px #3c50641a; display: flex; flex-direction: column; justify-content: center; align-items: center; gap: 1px; color: #3e515e; cursor: pointer; }
.reset-button > span { font-size: 27px; line-height: 1; }.reset-button small { font-size: 10px; }.reset-button:hover { background: #fff; color: #d86424; }.reset-button:disabled { opacity: .4; cursor: default; }
button:focus-visible { outline: 2px solid #d86424; outline-offset: 4px; }
.loading-ring { width: 24px; height: 24px; border: 2px solid #b7c7cd; border-top-color: #cc773d; border-radius: 50%; animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (max-height: 700px) { .scene-label { bottom: 18px; }.reset-button { bottom: 36px; } }
@media (prefers-reduced-motion: reduce) { .loading-ring { animation: none; } }
</style>
