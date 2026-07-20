<!-- 位置调整面板只负责桌面管理员输入、状态提示与事件上抛。 -->
<!-- Three.js 预览和草稿写入仍由 ManualViewer 统一控制，避免组件隐藏副作用。 -->
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Close } from '@element-plus/icons-vue'
import {
  MAX_VIEW_OFFSET_RATIO,
  calculateGridHeight,
  createAutomaticSceneCalibration,
  sanitizeSceneCalibration,
  type SceneCalibration,
  type SceneCalibrationGeometry
} from '../sceneCalibration'

interface Props {
  modelValue: boolean
  glbFile: string
  calibration: SceneCalibration
  geometry: SceneCalibrationGeometry
  saving: boolean
  saveError: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  preview: [calibration: SceneCalibration]
  cancel: []
  save: [calibration: SceneCalibration]
}>()

const draft = ref<SceneCalibration>(createAutomaticSceneCalibration())

const syncDraftFromProps = () => {
  draft.value = sanitizeSceneCalibration(props.calibration)
}

// 只监听三个标量，避免对整份手册或大型对象做深层 watch。
watch(
  [
    () => props.modelValue,
    () => props.calibration.gridOffsetRatio,
    () => props.calibration.viewOffsetXRatio,
    () => props.calibration.viewOffsetYRatio
  ],
  ([visible]) => {
    if (visible) syncDraftFromProps()
  },
  { immediate: true }
)

const currentGridHeight = computed(() => calculateGridHeight(draft.value, props.geometry))

const emitPreview = () => {
  draft.value = sanitizeSceneCalibration(draft.value)
  emit('preview', { ...draft.value })
}

const normalizeSliderValue = (value: number | number[]) => (
  Array.isArray(value) ? Number(value[0]) : Number(value)
)

const handleGridHeightInput = (value: number | number[]) => {
  const height = normalizeSliderValue(value)
  const modelScale = props.geometry.modelScale
  draft.value = sanitizeSceneCalibration({
    ...draft.value,
    gridOffsetRatio: modelScale > 0
      ? (height - props.geometry.autoGridHeight) / modelScale
      : 0
  })
  emitPreview()
}

const handleViewOffsetInput = (
  axis: 'viewOffsetXRatio' | 'viewOffsetYRatio',
  value: number | number[]
) => {
  draft.value = sanitizeSceneCalibration({
    ...draft.value,
    [axis]: normalizeSliderValue(value)
  })
  emitPreview()
}

const restoreAutomatic = () => {
  draft.value = createAutomaticSceneCalibration()
  emitPreview()
}

const requestCancel = () => {
  if (!props.saving) emit('cancel')
}

const requestSave = () => emit('save', { ...draft.value })
</script>

<template>
  <Transition name="position-panel">
    <section
      v-if="modelValue"
      class="scene-calibration-panel"
      role="dialog"
      aria-modal="false"
      aria-labelledby="scene-calibration-title"
      @click.stop
    >
      <header class="panel-header">
        <div class="header-copy">
          <h2 id="scene-calibration-title">调整模型和网格</h2>
          <p>拖动滑块，边看模型边调整</p>
        </div>
        <el-button
          class="panel-close"
          :icon="Close"
          circle
          text
          :disabled="saving"
          aria-label="关闭调整面板"
          @click="requestCancel"
        />
      </header>

      <div class="panel-body">
        <div v-if="glbFile" class="current-file" :title="glbFile">
          <span>正在调整：</span>
          <strong>{{ glbFile }}</strong>
        </div>

        <el-alert
          v-if="!geometry.isValid"
          title="当前模型的位置读取不完整，已使用默认位置，可以继续手动调整。"
          type="warning"
          :closable="false"
          show-icon
          class="calibration-alert"
        />

        <div class="calibration-field">
          <div class="field-heading">
            <span>网格上下位置</span>
          </div>
          <el-slider
            :model-value="currentGridHeight"
            :min="geometry.gridMinHeight"
            :max="geometry.gridMaxHeight"
            :step="geometry.gridStep"
            :disabled="saving"
            aria-label="网格上下位置"
            @input="handleGridHeightInput"
          />
        </div>

        <div class="calibration-field">
          <div class="field-heading">
            <span>模型左右位置</span>
          </div>
          <el-slider
            :model-value="draft.viewOffsetXRatio"
            :min="-MAX_VIEW_OFFSET_RATIO"
            :max="MAX_VIEW_OFFSET_RATIO"
            :step="0.01"
            :disabled="saving"
            aria-label="模型左右位置"
            @input="handleViewOffsetInput('viewOffsetXRatio', $event)"
          />
        </div>

        <div class="calibration-field">
          <div class="field-heading">
            <span>模型上下位置</span>
          </div>
          <el-slider
            :model-value="draft.viewOffsetYRatio"
            :min="-MAX_VIEW_OFFSET_RATIO"
            :max="MAX_VIEW_OFFSET_RATIO"
            :step="0.01"
            :disabled="saving"
            aria-label="模型上下位置"
            @input="handleViewOffsetInput('viewOffsetYRatio', $event)"
          />
        </div>

        <el-alert
          v-if="saveError"
          :title="saveError"
          type="error"
          :closable="false"
          show-icon
          class="calibration-alert"
        />
      </div>

      <footer class="calibration-actions">
        <el-button :disabled="saving" @click="restoreAutomatic">恢复默认</el-button>
        <div class="primary-actions">
          <el-button :disabled="saving" @click="requestCancel">取消</el-button>
          <el-button type="primary" :loading="saving" @click="requestSave">保存</el-button>
        </div>
      </footer>
    </section>
  </Transition>
</template>

<style scoped lang="scss">
.scene-calibration-panel {
  position: absolute;
  inset: 0;
  z-index: 25;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  box-sizing: border-box;
  border: 1px solid #d9e5f3;
  border-radius: 12px;
  background: #fff;
  box-shadow: -12px 0 28px rgba(31, 41, 55, 0.12);
}

.panel-header {
  display: flex;
  flex: 0 0 auto;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 20px 16px;
  border-bottom: 1px solid #e7edf5;
  background: linear-gradient(135deg, #f7faff 0%, #fff 100%);
}

.header-copy {
  min-width: 0;

  h2 {
    margin: 0;
    color: #25324a;
    font-size: 20px;
    line-height: 1.4;
  }

  p {
    margin: 6px 0 0;
    color: #6b7280;
    font-size: 14px;
    line-height: 1.5;
  }
}

.panel-close {
  flex: 0 0 auto;
}

.panel-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 18px 20px;
}

.current-file {
  display: flex;
  min-width: 0;
  margin-bottom: 16px;
  padding: 10px 12px;
  border-radius: 8px;
  color: #526079;
  background: #f4f7fb;
  font-size: 13px;

  span {
    flex: 0 0 auto;
  }

  strong {
    min-width: 0;
    overflow: hidden;
    color: #25324a;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.calibration-field {
  padding: 14px 4px 16px;

  .field-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
    color: #303133;
    font-size: 15px;
    font-weight: 600;
  }
}

.calibration-alert {
  margin: 4px 0 14px;
}

.calibration-actions {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid #e7edf5;
  background: #fff;

  .primary-actions {
    display: flex;
    gap: 10px;
  }
}

.position-panel-enter-active,
.position-panel-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.position-panel-enter-from,
.position-panel-leave-to {
  opacity: 0;
  transform: translateX(16px);
}

</style>
