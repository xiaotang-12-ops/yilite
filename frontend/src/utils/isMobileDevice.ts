// 设备判定用于电脑专属展示入口，窗口宽度由调用方媒体查询管理。
// iPad桌面UA与手机横屏不能仅按窗口宽度放行。-codex，2026-10-08
export function isMobileDevice(): boolean {
  return /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent)
    || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
}
