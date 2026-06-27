// leaflet.heat 0.2.0 是早期 UMD 插件，依赖全局变量 L 才能注册 L.heatLayer。
// 在 ESM/Vite 下需先把 Leaflet 暴露到 window，再加载该插件。
import L from 'leaflet'

if (typeof window !== 'undefined' && !window.L) {
  window.L = L
}

export default L
