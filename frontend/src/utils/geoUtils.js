// 公共地理工具：设施类型元数据、颜色分级、坐标与范围换算

// 研究区：武汉市洪山区（均为 WGS84 / EPSG:4326，与边界、人口、设施数据同一坐标系）
export const HONGSHAN_CENTER = [30.506565, 114.395178] // [lat, lng]，Leaflet 顺序
export const HONGSHAN_BBOX = [114.16, 30.38, 114.65, 30.70] // [minLng,minLat,maxLng,maxLat]，含边距覆盖全区
export const DEFAULT_ZOOM = 12

// 三大类公共设施的展示元数据（颜色、中文名、默认服务半径、图例符号）
export const FACILITY_TYPES = {
  all: { label: '全部', color: '#8b5cf6', radius: null, emoji: '📊' },
  school: { label: '学校', color: '#2563eb', radius: 1000, emoji: '🏫' },
  hospital: { label: '医院', color: '#dc2626', radius: 2000, emoji: '🏥' },
  park: { label: '公园', color: '#16a34a', radius: 500, emoji: '🌳' },
}

export const FACILITY_POINT_ORDER = ['school', 'hospital', 'park']
export const ANALYSIS_TYPE_ORDER = ['school', 'hospital', 'park', 'all']

// OSM 细分类型 → 中文标签（用于点选弹窗展示原始类别）
export const SUBTYPE_LABELS = {
  school: '中小学', kindergarten: '幼儿园', college: '学院', university: '大学',
  hospital: '医院', clinic: '诊所', doctors: '门诊',
  park: '公园绿地',
}

// 人口密度热力的分级配色（由低到高），用于图例与渐变
export const HEAT_GRADIENT = {
  0.1: '#2b83ba',
  0.3: '#abdda4',
  0.55: '#ffffbf',
  0.75: '#fdae61',
  0.9: '#f46d43',
  1.0: '#d7191c',
}

export const HEAT_LEGEND = [
  { color: '#2b83ba', label: '低' },
  { color: '#abdda4', label: '较低' },
  { color: '#ffffbf', label: '中' },
  { color: '#fdae61', label: '较高' },
  { color: '#d7191c', label: '高' },
]

// 由 Leaflet 地图取得 bbox 字符串：minLng,minLat,maxLng,maxLat
export function bboxStringFromMap(map) {
  const b = map.getBounds()
  const sw = b.getSouthWest()
  const ne = b.getNorthEast()
  return `${sw.lng},${sw.lat},${ne.lng},${ne.lat}`
}

// 将后端人口点 {lng,lat,value} 列表转为 leaflet.heat 的 [lat,lng,intensity]
// 使用洪山区人口密度分位阈值近似映射：p50≈400、p75≈1900、p90≈5700、p95≈12000、p99≈24500。
function heatIntensity(value) {
  if (value <= 400) return 0.10
  if (value <= 1900) return 0.28
  if (value <= 5300) return 0.48
  if (value <= 11000) return 0.68
  if (value <= 24500) return 0.90
  return 1
}

export function toHeatPoints(points) {
  if (!points.length) return []
  return points.map((p) => [p.lat, p.lng, heatIntensity(Math.max(p.value, 0))])
}

// 千分位格式化
export function fmt(n) {
  if (n === null || n === undefined) return '—'
  return Number(n).toLocaleString('zh-CN')
}

export function pct(rate) {
  if (rate === null || rate === undefined) return '—'
  return (rate * 100).toFixed(1) + '%'
}
