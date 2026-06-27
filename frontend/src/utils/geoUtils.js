// 公共地理工具：设施类型元数据、颜色分级、坐标与范围换算

// 研究区：武汉市洪山区
export const HONGSHAN_CENTER = [30.504259, 114.400718] // [lat, lng]，Leaflet 顺序
export const HONGSHAN_BBOX = [114.17, 30.38, 114.65, 30.70] // [minLng,minLat,maxLng,maxLat]
export const DEFAULT_ZOOM = 12

// 三大类公共设施的展示元数据（颜色、中文名、默认服务半径、图例符号）
export const FACILITY_TYPES = {
  school: { label: '学校', color: '#2563eb', radius: 1000, emoji: '🏫' },
  hospital: { label: '医院', color: '#dc2626', radius: 2000, emoji: '🏥' },
  park: { label: '公园', color: '#16a34a', radius: 500, emoji: '🌳' },
}

export const FACILITY_ORDER = ['school', 'hospital', 'park']

// OSM 细分类型 → 中文标签（用于点选弹窗展示原始类别）
export const SUBTYPE_LABELS = {
  school: '中小学', kindergarten: '幼儿园', college: '学院', university: '大学',
  hospital: '医院', clinic: '诊所', doctors: '门诊',
  park: '公园绿地',
}

// 人口密度热力的分级配色（由低到高），用于图例与渐变
export const HEAT_GRADIENT = {
  0.2: '#2b83ba',
  0.4: '#abdda4',
  0.6: '#ffffbf',
  0.8: '#fdae61',
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
// intensity 以批次内最大值归一化并做平方根压缩，避免少数极值淹没整体梯度
export function toHeatPoints(points) {
  if (!points.length) return []
  let maxV = 0
  for (const p of points) if (p.value > maxV) maxV = p.value
  const ref = maxV || 1
  return points.map((p) => [p.lat, p.lng, Math.min(1, Math.sqrt(p.value / ref))])
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
