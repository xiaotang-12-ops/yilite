// 负责锁定位置调整面板的非模态呈现、挂载区域和既有事件契约。
// 这些断言不替代真实页面视觉验收，只防止遮罩弹窗或技术文案被静默带回。
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const testsDir = dirname(fileURLToPath(import.meta.url))
const frontendRoot = resolve(testsDir, '..')
const panelSource = readFileSync(
  resolve(frontendRoot, 'src/views/manual-viewer/components/SceneCalibrationPanel.vue'),
  'utf8'
)
const viewerSource = readFileSync(
  resolve(frontendRoot, 'src/views/ManualViewer.vue'),
  'utf8'
)
const panelTemplate = panelSource.match(/<template>([\s\S]*?)<\/template>/)?.[1] || ''

test('位置调整面板不再使用模态遮罩或页面滚动锁定', () => {
  assert.doesNotMatch(panelSource, /<el-dialog\b/)
  assert.doesNotMatch(panelSource, /el-overlay|lock-scroll/)
  assert.match(panelTemplate, /<section[\s\S]*role="dialog"[\s\S]*aria-modal="false"/)
  assert.match(panelSource, /\.scene-calibration-panel\s*\{[\s\S]*position:\s*absolute;[\s\S]*inset:\s*0;/)
})

test('面板挂载在右侧说明栏内且不改变保存取消事件契约', () => {
  const rightSidebarStart = viewerSource.indexOf('<div class="right-sidebar"')
  const panelMount = viewerSource.indexOf('<SceneCalibrationPanel', rightSidebarStart)
  const rightSplitHandle = viewerSource.indexOf('split-handle-right', rightSidebarStart)

  assert.ok(rightSidebarStart >= 0)
  assert.ok(panelMount > rightSidebarStart)
  assert.ok(panelMount < rightSplitHandle)
  assert.match(viewerSource, /const RIGHT_SIDEBAR_DEFAULT_WIDTH = 400/)
  assert.match(panelSource, /preview:\s*\[calibration:\s*SceneCalibration\]/)
  assert.match(panelSource, /cancel:\s*\[\]/)
  assert.match(panelSource, /save:\s*\[calibration:\s*SceneCalibration\]/)
  assert.match(panelSource, /emit\('preview',\s*\{ \.\.\.draft\.value \}\)/)
  assert.match(panelSource, /emit\('cancel'\)/)
  assert.match(panelSource, /emit\('save',\s*\{ \.\.\.draft\.value \}\)/)
})

test('用户可见文案使用已确认的普通表达', () => {
  for (const text of [
    '调整模型和网格',
    '拖动滑块，边看模型边调整',
    '网格上下位置',
    '模型左右位置',
    '模型上下位置',
    '恢复默认',
    '取消',
    '保存'
  ]) {
    assert.match(panelTemplate, new RegExp(text))
  }

  for (const technicalText of [
    '场景校准',
    '自动网格',
    '观察中心',
    '世界坐标',
    '归一化',
    '本地实时预览',
    '自适应安全间距'
  ]) {
    assert.doesNotMatch(panelTemplate, new RegExp(technicalText))
  }

  assert.match(viewerSource, />\s*调整位置\s*<\/el-button>/)
  assert.match(viewerSource, /sceneCalibrationSaveError\.value = '保存失败，当前调整仍保留，可以重试'/)
  assert.match(viewerSource, /ElMessage\.success\('位置已保存'\)/)
})
