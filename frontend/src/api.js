// 后端 API 客户端 —— 封装所有 GET 接口，统一错误处理。
// 开发期 BASE 为 /api/v1，经 Vite 代理转发到 FastAPI（见 vite.config.js）。

const BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1'

function radiiParams(radii) {
  return radii ? {
    school_radius: radii.school,
    hospital_radius: radii.hospital,
    park_radius: radii.park,
  } : {}
}

async function get(path, params) {
  const qs = params ? '?' + new URLSearchParams(params).toString() : ''
  let res
  try {
    res = await fetch(BASE + path + qs)
  } catch (e) {
    throw new Error('无法连接后端服务，请确认 API 已启动')
  }
  let json = null
  try {
    json = await res.json()
  } catch (e) {
    /* 非 JSON 响应 */
  }
  if (!res.ok) {
    const msg = json?.detail || json?.message || `请求失败 (HTTP ${res.status})`
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg))
  }
  return json?.data ?? json
}

export const api = {
  // F11 数据状态自检
  status: () => get('/meta/status'),
  // 研究区边界（用于定位与轮廓）
  boundary: () => get('/meta/boundary'),
  // F2 人口热力点
  heatmap: (bbox, zoom, dataset = 'worldpop') =>
    get('/population/heatmap', { bbox, zoom, dataset }),
  // F12 点击地图查询该点人口密度
  populationAtPoint: (lng, lat) =>
    get('/population/at-point', { lng: lng.toFixed(5), lat: lat.toFixed(5) }),
  // F3/F4 设施列表（不传 facility_type 返回全部）
  facilities: (bbox, facility_type, page = 1, page_size = 2000) =>
    get('/facilities', { bbox, ...(facility_type ? { facility_type } : {}), page, page_size }),
  // F8 供需统计
  supplyDemand: (bbox, facility_type, buffer_radius) =>
    get('/analysis/supply-demand', { bbox, facility_type, ...(buffer_radius ? { buffer_radius } : {}) }),
  // F7 供给盲区
  blindSpots: (bbox, facility_type, buffer_radius, pop_threshold) =>
    get('/analysis/blind-spots', {
      bbox, facility_type,
      ...(buffer_radius ? { buffer_radius } : {}),
      ...(pop_threshold != null ? { pop_threshold } : {}),
    }),
  // F6 设施服务覆盖区
  coverage: (bbox, facility_type, buffer_radius) =>
    get('/analysis/coverage', { bbox, facility_type, ...(buffer_radius ? { buffer_radius } : {}) }),
  // 全类型覆盖区叠加
  coverageAll: (bbox, radii) =>
    get('/analysis/coverage-all', { bbox, ...radiiParams(radii) }),
  // 全类型盲区识别
  blindSpotsAll: (bbox, radii, pop_threshold) =>
    get('/analysis/blind-spots-all', { bbox, ...radiiParams(radii), ...(pop_threshold != null ? { pop_threshold } : {}) }),
  // 全类型供需统计
  supplyDemandAll: (bbox, radii) =>
    get('/analysis/supply-demand-all', { bbox, ...radiiParams(radii) }),
}
