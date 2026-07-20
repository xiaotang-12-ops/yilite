// 负责 ManualViewer 场景校准的纯数据转换与自适应尺寸计算。
// 输入来自手册 metadata 和归位模型包围盒，输出供 UI、Three.js 预览与草稿保存共用。

export const SCENE_CALIBRATION_SCHEMA_VERSION = 1
export const MAX_GRID_OFFSET_RATIO = 0.5
export const MAX_VIEW_OFFSET_RATIO = 0.6

const LEGACY_GRID_HEIGHT = -5
const FALLBACK_MODEL_SCALE = 100
const CALIBRATION_EPSILON = 1e-6

export interface SceneCalibration {
  gridOffsetRatio: number
  viewOffsetXRatio: number
  viewOffsetYRatio: number
}

export interface BoundsSnapshot {
  min: { x: number; y: number; z: number }
  max: { x: number; y: number; z: number }
}

export interface SceneCalibrationGeometry {
  isValid: boolean
  modelScale: number
  safeGap: number
  autoGridHeight: number
  gridMinHeight: number
  gridMaxHeight: number
  gridStep: number
  boxSignature: string
}

interface PersistedSceneCalibration {
  schema_version: number
  grid_offset_ratio: number
  view_offset_x_ratio: number
  view_offset_y_ratio: number
  box_signature: string
}

type UnknownRecord = Record<string, unknown>

const isRecord = (value: unknown): value is UnknownRecord => (
  typeof value === 'object' && value !== null && !Array.isArray(value)
)

const toFiniteNumber = (value: unknown, fallback = 0) => {
  const numeric = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(numeric) ? numeric : fallback
}

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value))

// 偏移值保留固定小数便于稳定回放；尺寸签名保留有效数字，兼顾大小尺度模型的可读性。
const roundForStorage = (value: number) => Number(value.toFixed(6))

const roundForSignature = (value: number) => Number(value.toPrecision(6)).toString()

export const createAutomaticSceneCalibration = (): SceneCalibration => ({
  gridOffsetRatio: 0,
  viewOffsetXRatio: 0,
  viewOffsetYRatio: 0
})

export const sanitizeSceneCalibration = (value: unknown): SceneCalibration => {
  const source = isRecord(value) ? value : {}
  return {
    gridOffsetRatio: clamp(
      toFiniteNumber(source.gridOffsetRatio),
      -MAX_GRID_OFFSET_RATIO,
      MAX_GRID_OFFSET_RATIO
    ),
    viewOffsetXRatio: clamp(
      toFiniteNumber(source.viewOffsetXRatio),
      -MAX_VIEW_OFFSET_RATIO,
      MAX_VIEW_OFFSET_RATIO
    ),
    viewOffsetYRatio: clamp(
      toFiniteNumber(source.viewOffsetYRatio),
      -MAX_VIEW_OFFSET_RATIO,
      MAX_VIEW_OFFSET_RATIO
    )
  }
}

export const isAutomaticSceneCalibration = (value: SceneCalibration) => (
  Math.abs(value.gridOffsetRatio) <= CALIBRATION_EPSILON
  && Math.abs(value.viewOffsetXRatio) <= CALIBRATION_EPSILON
  && Math.abs(value.viewOffsetYRatio) <= CALIBRATION_EPSILON
)

export const createSceneCalibrationGeometry = (
  bounds: BoundsSnapshot | null | undefined
): SceneCalibrationGeometry => {
  const coords = bounds
    ? [
        bounds.min.x, bounds.min.y, bounds.min.z,
        bounds.max.x, bounds.max.y, bounds.max.z
      ]
    : []
  const hasFiniteBounds = coords.length === 6 && coords.every(Number.isFinite)

  if (bounds && hasFiniteBounds) {
    const sizeX = bounds.max.x - bounds.min.x
    const sizeY = bounds.max.y - bounds.min.y
    const sizeZ = bounds.max.z - bounds.min.z
    const modelScale = Math.max(sizeX, sizeY, sizeZ)
    const orderedBounds = sizeX >= 0 && sizeY >= 0 && sizeZ >= 0

    if (orderedBounds && modelScale > CALIBRATION_EPSILON) {
      // 间距与可调范围都跟随归位模型尺寸，避免一个绝对值覆盖所有 GLB。
      const safeGap = modelScale * 0.015
      const autoGridHeight = bounds.min.y - safeGap
      return {
        isValid: true,
        modelScale,
        safeGap,
        autoGridHeight,
        gridMinHeight: autoGridHeight - modelScale * MAX_GRID_OFFSET_RATIO,
        gridMaxHeight: autoGridHeight + modelScale * MAX_GRID_OFFSET_RATIO,
        gridStep: modelScale * 0.005,
        boxSignature: [sizeX, sizeY, sizeZ].map(roundForSignature).join(':')
      }
    }
  }

  // 历史坏模型或空包围盒沿用旧高度，管理员仍可在自适应兜底范围内手动调整。
  return {
    isValid: false,
    modelScale: FALLBACK_MODEL_SCALE,
    safeGap: 0,
    autoGridHeight: LEGACY_GRID_HEIGHT,
    gridMinHeight: LEGACY_GRID_HEIGHT - FALLBACK_MODEL_SCALE * MAX_GRID_OFFSET_RATIO,
    gridMaxHeight: LEGACY_GRID_HEIGHT + FALLBACK_MODEL_SCALE * MAX_GRID_OFFSET_RATIO,
    gridStep: FALLBACK_MODEL_SCALE * 0.005,
    boxSignature: 'invalid'
  }
}

export const calculateGridHeight = (
  calibration: SceneCalibration,
  geometry: SceneCalibrationGeometry
) => geometry.autoGridHeight + calibration.gridOffsetRatio * geometry.modelScale

export const readSceneCalibration = (manualData: unknown, glbFile: string): SceneCalibration => {
  if (!glbFile || !isRecord(manualData)) return createAutomaticSceneCalibration()
  const metadata = manualData.metadata
  if (!isRecord(metadata)) return createAutomaticSceneCalibration()
  const viewerSettings = metadata.viewer_settings
  if (!isRecord(viewerSettings)) return createAutomaticSceneCalibration()
  const calibrations = viewerSettings.scene_calibration_by_glb
  if (!isRecord(calibrations)) return createAutomaticSceneCalibration()
  const persisted = calibrations[glbFile]
  if (!isRecord(persisted)) return createAutomaticSceneCalibration()
  if (toFiniteNumber(persisted.schema_version, -1) !== SCENE_CALIBRATION_SCHEMA_VERSION) {
    return createAutomaticSceneCalibration()
  }

  return sanitizeSceneCalibration({
    gridOffsetRatio: persisted.grid_offset_ratio,
    viewOffsetXRatio: persisted.view_offset_x_ratio,
    viewOffsetYRatio: persisted.view_offset_y_ratio
  })
}

export const writeSceneCalibration = (
  manualData: UnknownRecord,
  glbFile: string,
  value: SceneCalibration,
  boxSignature: string
): UnknownRecord => {
  const key = String(glbFile || '').trim()
  if (!key) throw new Error('glb_file 不能为空')

  const nextManual: UnknownRecord = { ...manualData }
  const sourceMetadata = isRecord(manualData.metadata) ? manualData.metadata : {}
  const sourceViewerSettings = isRecord(sourceMetadata.viewer_settings)
    ? sourceMetadata.viewer_settings
    : {}
  const sourceByGlb = isRecord(sourceViewerSettings.scene_calibration_by_glb)
    ? sourceViewerSettings.scene_calibration_by_glb
    : {}

  const metadata: UnknownRecord = { ...sourceMetadata }
  const viewerSettings: UnknownRecord = { ...sourceViewerSettings }
  const calibrationByGlb: UnknownRecord = { ...sourceByGlb }
  const calibration = sanitizeSceneCalibration(value)

  if (isAutomaticSceneCalibration(calibration)) {
    // “恢复自动”不留下零值配置，旧手册与新手册继续共用同一默认路径。
    delete calibrationByGlb[key]
  } else {
    const persisted: PersistedSceneCalibration = {
      schema_version: SCENE_CALIBRATION_SCHEMA_VERSION,
      grid_offset_ratio: roundForStorage(calibration.gridOffsetRatio),
      view_offset_x_ratio: roundForStorage(calibration.viewOffsetXRatio),
      view_offset_y_ratio: roundForStorage(calibration.viewOffsetYRatio),
      box_signature: boxSignature || 'unknown'
    }
    calibrationByGlb[key] = persisted
  }

  if (Object.keys(calibrationByGlb).length > 0) {
    viewerSettings.scene_calibration_by_glb = calibrationByGlb
  } else {
    delete viewerSettings.scene_calibration_by_glb
  }

  if (Object.keys(viewerSettings).length > 0) {
    metadata.viewer_settings = viewerSettings
  } else {
    delete metadata.viewer_settings
  }

  nextManual.metadata = metadata
  return nextManual
}
