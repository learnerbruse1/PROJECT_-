<script setup>
import { ref, onMounted, onBeforeUnmount, provide, watch } from 'vue'
import L from 'leaflet'
import { store } from '../stores/mapStore.js'
import { bboxStringFromMap, HONGSHAN_BBOX } from '../utils/geoUtils.js'
import { api } from '../api.js'

const el = ref(null)
const mapRef = ref(null)
provide('map', mapRef) // 子图层组件通过 inject('map') 获取地图实例

let map = null
let moveTimer = null
let queryMarker = null // F12 人口密度查询的落点标记

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
  // 无天地图密钥时用 OSM 作为唯一回退
  if (!KEY) {
    layers['OpenStreetMap'] = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap',
    })
  }
  return layers
}

function syncView() {
  store.setView(bboxStringFromMap(map), map.getZoom())
}

// F12 人口密度查询落点标记（脉冲圆点，仅作视觉提示，不可交互）
const QUERY_PIN = L.divIcon({
  className: 'pop-query-pin',
  html: '<span class="ring"></span><span class="dot"></span>',
  iconSize: [22, 22],
  iconAnchor: [11, 11],
})
function clearQueryMarker() {
  if (queryMarker && map) map.removeLayer(queryMarker)
  queryMarker = null
}

// F12 点击地图空白处查询该点人口密度。
// 设施点与盲区面已设 bubblingMouseEvents:false，点击它们不会冒泡到此处，
// 因此这里只响应对底图空白区域的点击，并把结果交给侧边 InfoPanel 展示。
async function queryPopulationAt(latlng) {
  const { lat, lng } = latlng
  clearQueryMarker()
  queryMarker = L.marker([lat, lng], { icon: QUERY_PIN, interactive: false, keyboard: false }).addTo(map)
  try {
    const data = await api.populationAtPoint(lng, lat)
    const density = data?.pop_density || 0
    store.select({
      title: '人口密度查询',
      kind: 'population',
      density,
      rows: density
        ? [
            { k: '人口密度', v: fmt(density) + ' 人/km²' },
            { k: '网格中心', v: `${data.cell_lat.toFixed(4)}, ${data.cell_lng.toFixed(4)}` },
            { k: '点击坐标', v: `${lat.toFixed(5)}, ${lng.toFixed(5)}` },
          ]
        : [
            { k: '查询结果', v: data?.note || '该位置无人口栅格数据' },
            { k: '点击坐标', v: `${lat.toFixed(5)}, ${lng.toFixed(5)}` },
          ],
    })
  } catch (err) {
    clearQueryMarker()
    store.setError('人口密度查询失败：' + err.message)
  }
}

onMounted(() => {
  map = L.map(el.value, { zoomControl: true })
  // 初始视野同步定位到洪山区范围（animate:false），避免边界异步到达后再次 fitBounds 触发二次加载
  map.fitBounds(
    L.latLngBounds([HONGSHAN_BBOX[1], HONGSHAN_BBOX[0]], [HONGSHAN_BBOX[3], HONGSHAN_BBOX[2]]),
    { animate: false, padding: [10, 10] },
  )

  const bases = buildBaseLayers()
  const first = Object.values(bases)[0]
  first.addTo(map)
  const layerCtrl = L.control.layers(bases, {}, { position: 'bottomright', collapsed: false })
  if (Object.keys(bases).length > 1) layerCtrl.addTo(map)
  L.control.scale({ imperial: false, position: 'bottomleft' }).addTo(map)

  // F13 点击地图任意位置查询该点人口密度
  let popQueryPopup = null
  map.on('click', async (e) => {
    if (popQueryPopup) map.closePopup(popQueryPopup)
    const { lat, lng } = e.latlng
    try {
      const data = await api.populationAtPoint(lng, lat)
      if (!data.pop_density) {
        popQueryPopup = L.popup().setLatLng([lat, lng]).setContent('该位置无人口数据').openOn(map)
        return
      }
      popQueryPopup = L.popup()
        .setLatLng([lat, lng])
        .setContent(
          `<b>人口密度</b>&nbsp; ${data.pop_density} 人/km²<br>` +
          `<small>网格 ${data.cell_lat.toFixed(4)}, ${data.cell_lng.toFixed(4)}</small>`,
        )
        .openOn(map)
    } catch {
      // 静默失败，不打断用户操作
    }
  })

  // 研究区边界轮廓 + 自动定位（F1）
  if (store.boundary) drawBoundary()

  map.on('moveend', () => {
    clearTimeout(moveTimer)
    moveTimer = setTimeout(syncView, 500)
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

// 关闭详情面板或改选其他要素时，移除人口查询落点标记
watch(
  () => store.selected,
  (sel) => {
    if (!sel || sel.kind !== 'population') clearQueryMarker()
  },
)

onBeforeUnmount(() => {
  clearTimeout(moveTimer)
  clearQueryMarker()
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
  width: 100%;
  height: 100%;
  cursor: crosshair;
}
</style>
