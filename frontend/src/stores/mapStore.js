// 全局地图状态（轻量 reactive store，无需 Pinia）
// 集中管理：图层开关、当前分析设施类型、缓冲半径、视野 bbox、点选要素、统计指标、数据自检结果。
import { reactive } from 'vue'
import { FACILITY_TYPES, HONGSHAN_BBOX, DEFAULT_ZOOM } from '../utils/geoUtils.js'
import { api } from '../api.js'

export const store = reactive({
  // —— 数据自检（F11） ——
  ready: null, // null=检测中, true/false
  status: null,
  boundary: null,

  // —— 视野 ——
  bbox: HONGSHAN_BBOX.join(','),
  zoom: DEFAULT_ZOOM,

  // —— 人口数据集 ——
  dataset: 'worldpop',

  // —— 图层可见性 ——
  layers: {
    heatmap: true,
    school: true,
    hospital: true,
    park: true,
    coverage: false,
    blindzone: false,
  },

  // —— 分析参数（覆盖区 / 盲区 / 供需，针对单一设施类型） ——
  analysisType: 'school',
  // 每类设施各自的服务半径覆盖值（null = 用该类型默认半径），保证「设施类型 ↔ 服务半径」一一对应
  bufferRadius: { school: null, hospital: null, park: null },
  popThreshold: 1000,

  // —— 交互结果 ——
  selected: null, // { title, type, rows:[{k,v}] }
  stats: {}, // { school:{...}, hospital:{...}, park:{...} }
  blindCount: 0, // 最近一次盲区分析识别出的盲区数量

  // —— 状态 ——
  loading: { heatmap: false, facilities: false, coverage: false, blindzone: false, stats: false },
  error: '',

  // ———————————————————— actions ————————————————————
  radiusOf(type) {
    return this.bufferRadius[type] || FACILITY_TYPES[type].radius
  },

  effectiveRadius() {
    return this.radiusOf(this.analysisType)
  },

  setView(bbox, zoom) {
    this.bbox = bbox
    this.zoom = zoom
  },

  toggle(layer) {
    this.layers[layer] = !this.layers[layer]
  },

  setAnalysisType(t) {
    this.analysisType = t
  },

  select(info) {
    this.selected = info
  },

  clearSelect() {
    this.selected = null
  },

  setError(msg) {
    this.error = msg
    if (msg) setTimeout(() => { if (this.error === msg) this.error = '' }, 5000)
  },

  async init() {
    try {
      const status = await api.status()
      this.status = status
      this.ready = !!status.ready
    } catch (e) {
      this.ready = false
      this.setError('数据自检失败：' + e.message)
    }
    try {
      const { boundary } = await api.boundary()
      this.boundary = boundary
    } catch (e) {
      /* 边界可缺省，不阻断 */
    }
  },

  // F8：拉取三类设施的供需统计用于对比面板
  async loadStats() {
    this.loading.stats = true
    try {
      const types = ['school', 'hospital', 'park']
      const bbox = HONGSHAN_BBOX.join(',') // 固定按全区计算，与地图缩放/平移无关
      const results = await Promise.all(
        types.map((t) =>
          api
            .supplyDemand(bbox, t, this.radiusOf(t))
            .then((d) => [t, d])
            .catch(() => [t, null]),
        ),
      )
      const next = {}
      for (const [t, d] of results) next[t] = d
      this.stats = next
    } catch (e) {
      this.setError('供需统计加载失败：' + e.message)
    } finally {
      this.loading.stats = false
    }
  },
})
