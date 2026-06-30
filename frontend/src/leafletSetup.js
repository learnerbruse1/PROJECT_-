// leaflet.heat 0.2.0 是早期 UMD 插件，依赖全局变量 L 才能注册 L.heatLayer。
// 在 ESM/Vite 下需先把 Leaflet 暴露到 window，再加载该插件。
import L from 'leaflet'

if (typeof window !== 'undefined' && !window.L) {
  window.L = L
}

// Leaflet 在快速缩放/热更新销毁图层时，个别 DivOverlay 事件可能晚于 remove 执行，
// 原始 Tooltip._updatePosition 会直接读取已置空的 _map，导致缩放流程中断、覆盖层不同步。
function patchDivOverlaySafety() {
  const types = [L.Tooltip, L.Popup]
  for (const Type of types) {
    const proto = Type?.prototype
    if (!proto || proto.__nullMapPatched) continue
    const rawUpdatePosition = proto._updatePosition
    const rawAnimateZoom = proto._animateZoom
    if (rawUpdatePosition) {
      proto._updatePosition = function (...args) {
        if (!this._map) return
        return rawUpdatePosition.apply(this, args)
      }
    }
    if (rawAnimateZoom) {
      proto._animateZoom = function (...args) {
        if (!this._map) return
        return rawAnimateZoom.apply(this, args)
      }
    }
    proto.__nullMapPatched = true
  }
}

patchDivOverlaySafety()

export default L
