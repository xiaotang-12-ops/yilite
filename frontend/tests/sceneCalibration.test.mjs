// 通过项目内 TypeScript 编译器加载纯函数模块，验证旧手册兼容、按 GLB 隔离与自动基线。
// 测试不启动浏览器或后端，也不会写入 output 下的真实手册数据。
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import ts from 'typescript'

const sourceUrl = new URL('../src/views/manual-viewer/sceneCalibration.ts', import.meta.url)
const source = await readFile(sourceUrl, 'utf8')
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.ES2022,
    target: ts.ScriptTarget.ES2022
  },
  fileName: sourceUrl.pathname
}).outputText
const moduleUrl = `data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`
const calibration = await import(moduleUrl)

const sampleBounds = {
  min: { x: -10, y: -20, z: -5 },
  max: { x: 10, y: 30, z: 5 }
}

test('旧手册没有字段时直接使用自动默认', () => {
  assert.deepEqual(
    calibration.readSceneCalibration({ metadata: {} }, 'component_1.glb'),
    calibration.createAutomaticSceneCalibration()
  )
})

test('自动网格基线来自模型底部和相对模型尺寸的安全间距', () => {
  const geometry = calibration.createSceneCalibrationGeometry(sampleBounds)
  assert.equal(geometry.isValid, true)
  assert.equal(geometry.modelScale, 50)
  assert.equal(geometry.safeGap, 0.75)
  assert.equal(geometry.autoGridHeight, -20.75)
  assert.equal(
    calibration.calculateGridHeight(
      { gridOffsetRatio: 0.1, viewOffsetXRatio: 0, viewOffsetYRatio: 0 },
      geometry
    ),
    -15.75
  )
})

test('空或非法包围盒回退历史兼容高度且不崩溃', () => {
  const geometry = calibration.createSceneCalibrationGeometry(null)
  assert.equal(geometry.isValid, false)
  assert.equal(geometry.autoGridHeight, -5)
  assert.ok(geometry.gridMinHeight < geometry.autoGridHeight)
  assert.ok(geometry.gridMaxHeight > geometry.autoGridHeight)
})

test('同一手册多个 GLB 分别读写且不串值', () => {
  const original = { metadata: { product_name: '多模型手册' } }
  const first = calibration.writeSceneCalibration(
    original,
    'component_1.glb',
    { gridOffsetRatio: 0.1, viewOffsetXRatio: 0.2, viewOffsetYRatio: -0.1 },
    '1:2:3'
  )
  const second = calibration.writeSceneCalibration(
    first,
    'component_2.glb',
    { gridOffsetRatio: -0.2, viewOffsetXRatio: -0.3, viewOffsetYRatio: 0.15 },
    '4:5:6'
  )

  assert.deepEqual(calibration.readSceneCalibration(second, 'component_1.glb'), {
    gridOffsetRatio: 0.1,
    viewOffsetXRatio: 0.2,
    viewOffsetYRatio: -0.1
  })
  assert.deepEqual(calibration.readSceneCalibration(second, 'component_2.glb'), {
    gridOffsetRatio: -0.2,
    viewOffsetXRatio: -0.3,
    viewOffsetYRatio: 0.15
  })
  assert.deepEqual(original, { metadata: { product_name: '多模型手册' } })
})

test('恢复自动只移除当前 GLB 配置并保留其他模型', () => {
  const first = calibration.writeSceneCalibration(
    {},
    'component_1.glb',
    { gridOffsetRatio: 0.1, viewOffsetXRatio: 0, viewOffsetYRatio: 0 },
    '1:1:1'
  )
  const withTwo = calibration.writeSceneCalibration(
    first,
    'component_2.glb',
    { gridOffsetRatio: 0, viewOffsetXRatio: 0.2, viewOffsetYRatio: 0 },
    '2:2:2'
  )
  const restored = calibration.writeSceneCalibration(
    withTwo,
    'component_1.glb',
    calibration.createAutomaticSceneCalibration(),
    '1:1:1'
  )

  assert.deepEqual(
    calibration.readSceneCalibration(restored, 'component_1.glb'),
    calibration.createAutomaticSceneCalibration()
  )
  assert.equal(calibration.readSceneCalibration(restored, 'component_2.glb').viewOffsetXRatio, 0.2)
})

test('非法字段、越界值和未知 schema 安全回退', () => {
  const manual = {
    metadata: {
      viewer_settings: {
        scene_calibration_by_glb: {
          'valid.glb': {
            schema_version: 1,
            grid_offset_ratio: 99,
            view_offset_x_ratio: -99,
            view_offset_y_ratio: 'bad'
          },
          'future.glb': {
            schema_version: 999,
            grid_offset_ratio: 0.2
          }
        }
      }
    }
  }

  assert.deepEqual(calibration.readSceneCalibration(manual, 'valid.glb'), {
    gridOffsetRatio: 0.5,
    viewOffsetXRatio: -0.6,
    viewOffsetYRatio: 0
  })
  assert.deepEqual(
    calibration.readSceneCalibration(manual, 'future.glb'),
    calibration.createAutomaticSceneCalibration()
  )
})
