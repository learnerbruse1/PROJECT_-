<script setup>
import { inject, watch, onBeforeUnmount } from 'vue'
import L from 'leaflet'
import { store } from '../stores/mapStore.js'
import { api } from '../api.js'
import { FACILITY_TYPES, HONGSHAN_BBOX, fmt } from '../utils/geoUtils.js'

const map = inject('map')
let layer = null
let token = 0
const analysisBbox = HONGSHAN_BBOX.join(',')

function clear() {
  const m = map.value
  if (m && layer && m.hasLayer(layer)) m.removeLayer(layer)
  layer = null
}

async function refresh() {
  const m = map.value
  if (!m) return
  if (!store.layers.blindzone) {
    clear()
    return
  }
  const my = ++token
  store.loading.blindzone = true
  try {
    const t = store.analysisType
    if (t === 'all') {
      const data = await api.blindSpotsAll(analysisBbox, store.radiiByType(), store.popThreshold)
      if (my !== token || !store.layers.blindzone || !map.value) return
      clear()
      const fc = data.blind_spots
      if (!fc || !(fc.features || []).length) { store.blindCount = 0; return }
      store.blindCount = data.blind_spot_count
      layer = L.geoJSON(fc, {
        style: { color: '#b91c1c', weight: 1, fillColor: '#ef4444', fillOpacity: 0.35, stroke: false },
        bubblingMouseEvents: false, // 点击盲区不冒泡到地图，避免同时触发人口点查询
        onEachFeature: (feature, lyr) => {
          const p = feature.properties || {}
          lyr.on('click', () => {
            store.select({
              title: '供给盲区（全类型服务不足）',
              kind: 'blindzone', type: 'all',
              rows: [
                { k: '平均人口密度', v: fmt(p.avg_population_density) + ' 人/km²' },
                { k: '盲区面积', v: (p.area_km2 ?? '—') + ' km²' },
                { k: '高密度格网数', v: fmt(p.point_count) },
                { k: '人口阈值', v: fmt(store.popThreshold) + ' 人/km²' },
              ],
            })
          })
        },
      }).addTo(m)
    } else {
      const data = await api.blindSpots(analysisBbox, t, store.radiusOf(t), store.popThreshold)
      if (my !== token || !store.layers.blindzone || !map.value) return
      clear()
      const fc = data.blind_spots
      if (!fc || !(fc.features || []).length) { store.blindCount = 0; return }
      store.blindCount = data.blind_spot_count
      layer = L.geoJSON(fc, {
        style: { color: '#b91c1c', weight: 1, fillColor: '#ef4444', fillOpacity: 0.35, stroke: false },
        bubblingMouseEvents: false, // 点击盲区不冒泡到地图，避免同时触发人口点查询
        onEachFeature: (feature, lyr) => {
          const p = feature.properties || {}
          lyr.on('click', () => {
            store.select({
              title: `供给盲区（${FACILITY_TYPES[t].label}服务不足）`,
              kind: 'blindzone', type: t,
              rows: [
                { k: '平均人口密度', v: fmt(p.avg_population_density) + ' 人/km²' },
                { k: '盲区面积', v: (p.area_km2 ?? '—') + ' km²' },
                { k: '高密度格网数', v: fmt(p.point_count) },
                { k: '人口阈值', v: fmt(store.popThreshold) + ' 人/km²' },
              ],
            })
          })
        },
      }).addTo(m)
    }
  } catch (e) {
    store.setError('盲区分析失败：' + e.message)
  } finally {
    if (my === token) store.loading.blindzone = false
  }
}

watch(map, refresh, { immediate: true })
watch(
  () => [
    store.layers.blindzone,
    store.analysisType,
    store.bufferRadius.school,
    store.bufferRadius.hospital,
    store.bufferRadius.park,
    store.popThreshold,
    analysisBbox,
  ],
  refresh,
)

onBeforeUnmount(clear)
</script>

<template><span style="display: none" /></template>
