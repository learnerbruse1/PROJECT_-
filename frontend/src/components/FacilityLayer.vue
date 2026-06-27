<script setup>
import { inject, watch, onBeforeUnmount } from 'vue'
import L from 'leaflet'
import { store } from '../stores/mapStore.js'
import { api } from '../api.js'
import { FACILITY_TYPES, FACILITY_ORDER, SUBTYPE_LABELS } from '../utils/geoUtils.js'

const map = inject('map')
const groups = { school: L.layerGroup(), hospital: L.layerGroup(), park: L.layerGroup() }
let token = 0

function syncVisibility() {
  const m = map.value
  if (!m) return
  for (const t of FACILITY_ORDER) {
    const on = store.layers[t]
    if (on && !m.hasLayer(groups[t])) groups[t].addTo(m)
    if (!on && m.hasLayer(groups[t])) m.removeLayer(groups[t])
  }
}

function makeMarker(f) {
  const meta = FACILITY_TYPES[f.type]
  const marker = L.circleMarker([f.lat, f.lng], {
    radius: 6,
    color: '#fff',
    weight: 1.5,
    fillColor: meta.color,
    fillOpacity: 0.9,
  })
  marker.bindTooltip(f.name, { direction: 'top', offset: [0, -4] })
  marker.on('click', () => {
    store.select({
      title: f.name,
      kind: 'facility',
      type: f.type,
      rows: [
        { k: '设施类型', v: meta.label },
        { k: '细分类别', v: SUBTYPE_LABELS[f.subtype] || f.subtype || '—' },
        { k: '经度', v: f.lng.toFixed(5) },
        { k: '纬度', v: f.lat.toFixed(5) },
        { k: '数据来源', v: f.source || 'OSM' },
        { k: '设施 ID', v: f.id },
      ],
    })
  })
  return marker
}

async function refresh() {
  const m = map.value
  if (!m) return
  const my = ++token
  store.loading.facilities = true
  try {
    const data = await api.facilities(store.bbox, null, 1, 2000)
    if (my !== token) return
    for (const t of FACILITY_ORDER) groups[t].clearLayers()
    for (const f of data.facilities || []) {
      if (groups[f.type]) makeMarker(f).addTo(groups[f.type])
    }
    syncVisibility()
  } catch (e) {
    store.setError('设施数据加载失败：' + e.message)
  } finally {
    if (my === token) store.loading.facilities = false
  }
}

watch(map, refresh, { immediate: true }) // 挂载即首次加载
watch(() => store.bbox, refresh)
watch(
  () => [store.layers.school, store.layers.hospital, store.layers.park],
  syncVisibility,
)

onBeforeUnmount(() => {
  const m = map.value
  if (!m) return
  for (const t of FACILITY_ORDER) if (m.hasLayer(groups[t])) m.removeLayer(groups[t])
})
</script>

<template><span style="display: none" /></template>
