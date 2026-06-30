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

function patchHeatLayer() {
  const proto = L.HeatLayer?.prototype
  if (!proto || proto.__safeZoomPatched) return
  const rawInitCanvas = proto._initCanvas
  const rawRedraw = proto.redraw
  const rawRedrawFrame = proto._redraw
  const rawAnimateZoom = proto._animateZoom
  const rawReset = proto._reset
  const rawOnRemove = proto.onRemove
  if (rawInitCanvas) {
    proto._initCanvas = function (...args) {
      const Canvas = window.HTMLCanvasElement
      const rawGetContext = Canvas?.prototype?.getContext
      if (!rawGetContext) return rawInitCanvas.apply(this, args)
      Canvas.prototype.getContext = function (type, options) {
        if (type === '2d' && this.classList?.contains('leaflet-heatmap-layer')) {
          return rawGetContext.call(this, type, { ...(options || {}), willReadFrequently: true })
        }
        return rawGetContext.call(this, type, options)
      }
      try {
        return rawInitCanvas.apply(this, args)
      } finally {
        Canvas.prototype.getContext = rawGetContext
      }
    }
  }
  if (rawRedraw) {
    proto.redraw = function (...args) {
      if (!this._map || !this._heat) return this
      return rawRedraw.apply(this, args)
    }
  }
  if (rawRedrawFrame) {
    proto._redraw = function (...args) {
      if (!this._map || !this._heat) {
        this._frame = null
        return this
      }
      return rawRedrawFrame.apply(this, args)
    }
  }
  if (rawAnimateZoom) {
    proto._animateZoom = function (...args) {
      if (!this._map || !this._canvas) return
      return rawAnimateZoom.apply(this, args)
    }
  }
  if (rawReset) {
    proto._reset = function (...args) {
      if (!this._map || !this._canvas || !this._heat) return
      return rawReset.apply(this, args)
    }
  }
  if (rawOnRemove) {
    proto.onRemove = function (...args) {
      if (this._frame) {
        L.Util.cancelAnimFrame(this._frame)
        this._frame = null
      }
      const canvas = this._canvas
      const parent = canvas?.parentNode
      if (!parent) return
      return rawOnRemove.apply(this, args)
    }
  }
  proto.__safeZoomPatched = true
}

patchHeatLayer()

function ensureLayer() {
  if (!heat) {
    heat = L.heatLayer([], {
      radius: 32,
      blur: 17,
      max: 1.0,
      minOpacity: 0.17,
      gradient: HEAT_GRADIENT,
    })
  }
}

async function refresh() {
  const m = map.value
  if (!m) return
  if (!store.layers.heatmap) {
    token++
    if (heat && m.hasLayer(heat)) m.removeLayer(heat)
    return
  }
  ensureLayer()
  const my = ++token
  store.loading.heatmap = true
  try {
    const bbox = store.bbox
    const zoom = store.zoom
    const data = await api.heatmap(bbox, zoom, store.dataset)
    // 请求期间可能已有更新的请求、用户关闭了图层、视野变化或地图被销毁
    if (my !== token || !store.layers.heatmap || !map.value || bbox !== store.bbox || zoom !== store.zoom) return
    // 必须先把图层加入地图：leaflet.heat 在 onAdd 时才创建 _map/_heat。
    // 对已移除（Leaflet 会把 _map 置为 null）的图层直接 setLatLngs，
    // 会在 redraw 读取 null._animating 而抛 “Cannot read properties of null”。
    if (!map.value.hasLayer(heat)) heat.addTo(map.value)
    heat.setLatLngs(toHeatPoints(data.points || []))
    heat.redraw()
  } catch (e) {
    store.setError('人口热力加载失败：' + e.message)
  } finally {
    if (my === token) store.loading.heatmap = false
  }
}

watch(map, refresh, { immediate: true }) // 挂载即首次加载，不依赖后续地图移动
watch(
  () => [store.layers.heatmap, store.bbox, store.zoom, store.dataset],
  refresh,
)

onBeforeUnmount(() => {
  token++
  const m = map.value
  if (m && heat && m.hasLayer(heat)) m.removeLayer(heat)
  heat = null
})
</script>

<template><span style="display: none" /></template>
