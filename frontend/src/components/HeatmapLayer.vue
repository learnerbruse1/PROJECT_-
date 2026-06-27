<script setup>
import { inject, watch, onBeforeUnmount } from 'vue'
import L from '../leafletSetup.js' // 先暴露全局 L，再加载 leaflet.heat
import 'leaflet.heat'
import { store } from '../stores/mapStore.js'
import { api } from '../api.js'
import { toHeatPoints, HEAT_GRADIENT } from '../utils/geoUtils.js'

const map = inject('map')
let heat = null
let token = 0

function ensureLayer() {
  if (!heat) {
    heat = L.heatLayer([], {
      radius: 20,
      blur: 22,
      max: 0.5,
      minOpacity: 0.25,
      gradient: HEAT_GRADIENT,
    })
  }
}

async function refresh() {
  const m = map.value
  if (!m) return
  if (!store.layers.heatmap) {
    if (heat && m.hasLayer(heat)) m.removeLayer(heat)
    return
  }
  ensureLayer()
  const my = ++token
  store.loading.heatmap = true
  try {
    const data = await api.heatmap(store.bbox, store.zoom, store.dataset)
    // 请求期间可能已有更新的请求、用户关闭了图层、或地图被销毁
    if (my !== token || !store.layers.heatmap || !map.value) return
    // 必须先把图层加入地图：leaflet.heat 在 onAdd 时才创建 _map/_heat。
    // 对已移除（Leaflet 会把 _map 置为 null）的图层直接 setLatLngs，
    // 会在 redraw 读取 null._animating 而抛 “Cannot read properties of null”。
    if (!map.value.hasLayer(heat)) heat.addTo(map.value)
    heat.setLatLngs(toHeatPoints(data.points || []))
  } catch (e) {
    store.setError('人口热力加载失败：' + e.message)
  } finally {
    if (my === token) store.loading.heatmap = false
  }
}

watch(map, refresh, { immediate: true }) // 挂载即首次加载，不依赖后续地图移动
watch(
  () => [store.layers.heatmap, store.bbox, store.dataset],
  refresh,
)

onBeforeUnmount(() => {
  const m = map.value
  if (m && heat && m.hasLayer(heat)) m.removeLayer(heat)
})
</script>

<template><span style="display: none" /></template>
