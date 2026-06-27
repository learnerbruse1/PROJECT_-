<script setup>
import { ref, onMounted, onBeforeUnmount, provide, watch } from 'vue'
import L from 'leaflet'
import { store } from '../stores/mapStore.js'
import { bboxStringFromMap, HONGSHAN_BBOX } from '../utils/geoUtils.js'

const el = ref(null)
const mapRef = ref(null)
provide('map', mapRef) // 子图层组件通过 inject('map') 获取地图实例

let map = null
let moveTimer = null

const KEY = import.meta.env.VITE_TIANDITU_KEY

// 天地图 WMTS 瓦片（_w 为 web 墨卡托，与 Leaflet 默认 EPSG:3857 一致）
function tdt(type) {
  return L.tileLayer(
    `https://t{s}.tianditu.gov.cn/DataServer?T=${type}_w&x={x}&y={y}&l={z}&tk=${KEY}`,
    { subdomains: ['0', '1', '2', '3', '4', '5', '6', '7'], maxZoom: 18, attribution: '© 天地图' },
  )
}

function buildBaseLayers() {
  const layers = {}
  if (KEY) {
    layers['天地图·矢量'] = L.layerGroup([tdt('vec'), tdt('cva')])
    layers['天地图·影像'] = L.layerGroup([tdt('img'), tdt('cia')])
  }
  // 备用公开底图：高德在国内可达性好、无需密钥，放在 OSM 之前作为主要回退
  // （天地图密钥缺失或失效时，默认底图即为高德，避免出现空白底图）
  layers['高德·矢量'] = L.tileLayer(
    'https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}',
    { subdomains: ['1', '2', '3', '4'], maxZoom: 18, attribution: '© 高德地图' },
  )
  layers['OpenStreetMap'] = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap',
  })
  return layers
}

function syncView() {
  store.setView(bboxStringFromMap(map), map.getZoom())
}

onMounted(() => {
  map = L.map(el.value, { zoomControl: true, preferCanvas: true })
  // 初始视野同步定位到洪山区范围（animate:false），避免边界异步到达后再次 fitBounds 触发二次加载
  map.fitBounds(
    L.latLngBounds([HONGSHAN_BBOX[1], HONGSHAN_BBOX[0]], [HONGSHAN_BBOX[3], HONGSHAN_BBOX[2]]),
    { animate: false, padding: [10, 10] },
  )

  const bases = buildBaseLayers()
  const first = Object.values(bases)[0]
  first.addTo(map)
  L.control.layers(bases, {}, { position: 'topright', collapsed: true }).addTo(map)
  L.control.scale({ imperial: false, position: 'bottomleft' }).addTo(map)

  // 研究区边界轮廓 + 自动定位（F1）
  if (store.boundary) drawBoundary()

  map.on('moveend', () => {
    clearTimeout(moveTimer)
    moveTimer = setTimeout(syncView, 300)
  })
  syncView()

  mapRef.value = map
})

let boundaryLayer = null
function drawBoundary() {
  if (boundaryLayer) return
  // 仅绘制轮廓；初始定位已在 onMounted 用固定 bbox 完成，这里不再 fitBounds（避免二次加载）
  boundaryLayer = L.geoJSON(store.boundary, {
    style: { color: '#1d4ed8', weight: 2.5, fill: false, dashArray: '4 3' },
    interactive: false,
  }).addTo(map)
}

// 边界可能在地图就绪后才异步到达
watch(
  () => store.boundary,
  (b) => {
    if (b && map) drawBoundary()
  },
)

onBeforeUnmount(() => {
  clearTimeout(moveTimer)
  if (map) map.remove()
})
</script>

<template>
  <div class="map-root" ref="el">
    <!-- 各图层组件以子节点形式注入，通过 inject('map') 操作同一地图 -->
    <slot v-if="mapRef" />
  </div>
</template>

<style scoped>
.map-root {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
</style>
