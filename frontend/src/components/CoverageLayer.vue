<script setup>
import { inject, watch, onBeforeUnmount } from 'vue'
import L from 'leaflet'
import { store } from '../stores/mapStore.js'
import { api } from '../api.js'
import { FACILITY_TYPES } from '../utils/geoUtils.js'

const map = inject('map')
let layer = null
let token = 0

function clear() {
  const m = map.value
  if (m && layer && m.hasLayer(layer)) m.removeLayer(layer)
  layer = null
}

async function refresh() {
  const m = map.value
  if (!m) return
  if (!store.layers.coverage) {
    clear()
    return
  }
  const my = ++token
  store.loading.coverage = true
  try {
    const t = store.analysisType
    if (t === 'all') {
      const data = await api.coverageAll(store.bbox, store.radiiByType())
      if (my !== token || !store.layers.coverage || !map.value) return
      clear()
      const fc = data.coverage_geojson
      if (!fc || !(fc.features || []).length) return
      const color = FACILITY_TYPES[t].color
      layer = L.geoJSON(fc, {
        style: { color, weight: 1, fillColor: color, fillOpacity: 0.15, opacity: 0.5 },
        interactive: false,
      }).addTo(m)
    } else {
      const data = await api.coverage(store.bbox, t, store.radiusOf(t))
      if (my !== token || !store.layers.coverage || !map.value) return
      clear()
      const geom = data.coverage_geojson
      if (!geom || (geom.type === 'GeometryCollection' && !(geom.geometries || []).length)) return
      const color = FACILITY_TYPES[t].color
      layer = L.geoJSON(
        { type: 'Feature', geometry: geom, properties: {} },
        { style: { color, weight: 1, fillColor: color, fillOpacity: 0.18, opacity: 0.5 }, interactive: false },
      ).addTo(m)
    }
  } catch (e) {
    store.setError('覆盖区加载失败：' + e.message)
  } finally {
    if (my === token) store.loading.coverage = false
  }
}

watch(map, refresh, { immediate: true })
watch(
  () => [
    store.layers.coverage,
    store.analysisType,
    store.bufferRadius.school,
    store.bufferRadius.hospital,
    store.bufferRadius.park,
    store.bbox,
  ],
  refresh,
)

onBeforeUnmount(clear)
</script>

<template><span style="display: none" /></template>
