import { ref } from 'vue'

export interface VisualFontSettings {
  homeTitleScale: number
  homeMobileTitleScale: number
  homeFeatureScale: number
  navMobileFontSize: number
  navMobileMaxWidth: number
}

type VisualFontSettingKey = keyof VisualFontSettings

interface VisualFontLimit {
  min: number
  max: number
  step: number
}

const STORAGE_KEY = 'visual_font_settings'

export const visualFontDefaults: VisualFontSettings = {
  homeTitleScale: 1,
  homeMobileTitleScale: 1,
  homeFeatureScale: 1,
  navMobileFontSize: 10,
  navMobileMaxWidth: 226
}

export const visualFontLimits: Record<VisualFontSettingKey, VisualFontLimit> = {
  homeTitleScale: { min: 0.75, max: 1.2, step: 0.01 },
  homeMobileTitleScale: { min: 0.6, max: 1.1, step: 0.01 },
  homeFeatureScale: { min: 0.75, max: 1.2, step: 0.01 },
  navMobileFontSize: { min: 8, max: 14, step: 0.5 },
  navMobileMaxWidth: { min: 150, max: 280, step: 1 }
}

const visualFontSettings = ref<VisualFontSettings>({ ...visualFontDefaults })
let loaded = false

const clampNumber = (value: unknown, fallback: number, limit: VisualFontLimit) => {
  const numericValue = Number(value)

  if (!Number.isFinite(numericValue)) {
    return fallback
  }

  return Math.min(Math.max(numericValue, limit.min), limit.max)
}

const normalizeVisualFontSettings = (source: Partial<VisualFontSettings> | null | undefined) => {
  const normalized = { ...visualFontDefaults }

  ;(Object.keys(visualFontDefaults) as VisualFontSettingKey[]).forEach((key) => {
    normalized[key] = clampNumber(source?.[key], visualFontDefaults[key], visualFontLimits[key])
  })

  return normalized
}

const toFixedNumber = (value: number, digits = 3) => Number(value.toFixed(digits))

const setRemVariable = (style: CSSStyleDeclaration, name: string, baseRem: number, scale: number) => {
  style.setProperty(name, `${toFixedNumber(baseRem * scale)}rem`)
}

const setPxVariable = (style: CSSStyleDeclaration, name: string, basePx: number, scale: number) => {
  style.setProperty(name, `${toFixedNumber(basePx * scale, 2)}px`)
}

export const applyVisualFontSettings = (settings: Partial<VisualFontSettings> = visualFontSettings.value) => {
  if (typeof document === 'undefined') {
    return
  }

  const normalized = normalizeVisualFontSettings(settings)
  const rootStyle = document.documentElement.style

  // 统一从根 CSS 变量下发，页面组件只消费变量，不直接读 localStorage。
  rootStyle.setProperty('--visual-home-title-scale', String(normalized.homeTitleScale))
  rootStyle.setProperty('--visual-home-mobile-title-scale', String(normalized.homeMobileTitleScale))
  rootStyle.setProperty('--visual-home-feature-scale', String(normalized.homeFeatureScale))
  rootStyle.setProperty('--visual-nav-mobile-font-size', `${normalized.navMobileFontSize}px`)
  rootStyle.setProperty('--visual-nav-mobile-max-width', `${normalized.navMobileMaxWidth}px`)

  // 兼容部分浏览器不支持 CSS calc 乘法的问题，直接下发最终字号变量。
  setRemVariable(rootStyle, '--visual-home-title-kicker-font-size', 1.35, normalized.homeTitleScale)
  setRemVariable(rootStyle, '--visual-home-title-primary-font-size', 5, normalized.homeTitleScale)
  setRemVariable(rootStyle, '--visual-home-title-secondary-font-size', 4, normalized.homeTitleScale)
  setRemVariable(rootStyle, '--visual-home-title-kicker-1400-font-size', 1.15, normalized.homeTitleScale)
  setRemVariable(rootStyle, '--visual-home-title-primary-1400-font-size', 4.4, normalized.homeTitleScale)
  setRemVariable(rootStyle, '--visual-home-title-secondary-1400-font-size', 3.1, normalized.homeTitleScale)
  setRemVariable(rootStyle, '--visual-home-title-kicker-1200-font-size', 1.05, normalized.homeTitleScale)
  setRemVariable(rootStyle, '--visual-home-title-primary-1200-font-size', 3.7, normalized.homeTitleScale)
  setRemVariable(rootStyle, '--visual-home-title-secondary-1200-font-size', 2.6, normalized.homeTitleScale)
  setRemVariable(rootStyle, '--visual-home-title-kicker-mobile-font-size', 0.95, normalized.homeMobileTitleScale)
  setRemVariable(rootStyle, '--visual-home-title-primary-mobile-font-size', 2.75, normalized.homeMobileTitleScale)
  setRemVariable(rootStyle, '--visual-home-title-secondary-mobile-font-size', 1.95, normalized.homeMobileTitleScale)
  setPxVariable(rootStyle, '--visual-home-feature-font-size', 20, normalized.homeFeatureScale)
  setPxVariable(rootStyle, '--visual-home-feature-mobile-font-size', 14, normalized.homeFeatureScale)
  setPxVariable(rootStyle, '--visual-preview-kicker-font-size', 12, normalized.homeTitleScale)
  setPxVariable(rootStyle, '--visual-preview-primary-font-size', 28, normalized.homeTitleScale)
  setPxVariable(rootStyle, '--visual-preview-secondary-font-size', 20, normalized.homeTitleScale)
}

export const loadVisualFontSettings = () => {
  if (loaded) {
    applyVisualFontSettings()
    return visualFontSettings.value
  }

  loaded = true

  if (typeof window === 'undefined') {
    return visualFontSettings.value
  }

  try {
    const saved = window.localStorage.getItem(STORAGE_KEY)
    visualFontSettings.value = normalizeVisualFontSettings(saved ? JSON.parse(saved) : null)
  } catch (error) {
    console.warn('读取界面字号设置失败，已使用默认值。', error)
    visualFontSettings.value = { ...visualFontDefaults }
  }

  applyVisualFontSettings()
  return visualFontSettings.value
}

export const saveVisualFontSettings = () => {
  visualFontSettings.value = normalizeVisualFontSettings(visualFontSettings.value)
  applyVisualFontSettings()

  if (typeof window !== 'undefined') {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(visualFontSettings.value))
  }
}

export const resetVisualFontSettings = () => {
  visualFontSettings.value = { ...visualFontDefaults }
  saveVisualFontSettings()
}

export const useVisualFontSettings = () => {
  loadVisualFontSettings()

  return {
    visualFontSettings,
    visualFontDefaults,
    visualFontLimits,
    applyVisualFontSettings,
    saveVisualFontSettings,
    resetVisualFontSettings
  }
}
