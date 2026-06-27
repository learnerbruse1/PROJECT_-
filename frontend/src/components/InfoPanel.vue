<script setup>
import { store } from '../stores/mapStore.js'

const dataSources = [
  { k: '人口数据', v: 'WorldPop 2020（chn_ppp 1km, UN 调整）' },
  { k: '设施数据', v: 'OpenStreetMap：学校 / 医院 / 公园' },
  { k: '研究区', v: '武汉市洪山区（行政区划 420111）' },
  { k: '坐标系', v: 'WGS84 / EPSG:4326（经度在前）' },
  { k: '人口字段', v: 'pop_count — 人口密度（人/km²）' },
  { k: '处理流程', v: '裁剪研究区 → 重采样约 100m 网格 → 取格心点 → 空间叠加分析' },
]
</script>

<template>
  <div class="panel info-panel">
    <!-- 点选要素详情（F5） -->
    <template v-if="store.selected">
      <div class="hd">
        <h3>{{ store.selected.title }}</h3>
        <button class="close" @click="store.clearSelect()">✕</button>
      </div>
      <table class="kv">
        <tbody>
          <tr v-for="(r, i) in store.selected.rows" :key="i">
            <td class="k">{{ r.k }}</td>
            <td class="v">{{ r.v }}</td>
          </tr>
        </tbody>
      </table>
      <p class="tip">点击地图上其他要素查看其属性，或关闭返回数据说明。</p>
    </template>

    <!-- 数据来源与说明（F9） -->
    <template v-else>
      <h3>数据来源与说明</h3>
      <table class="kv">
        <tbody>
          <tr v-for="(r, i) in dataSources" :key="i">
            <td class="k">{{ r.k }}</td>
            <td class="v">{{ r.v }}</td>
          </tr>
        </tbody>
      </table>
      <p class="tip">点击地图上的设施点或盲区，可在此查看详细属性。</p>
    </template>
  </div>
</template>

<style scoped>
.info-panel {
  width: 270px;
}
.hd {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}
h3 {
  margin: 0 0 10px;
  font-size: 13px;
  color: #111827;
  line-height: 1.4;
}
.close {
  border: none;
  background: #f3f4f6;
  border-radius: 6px;
  width: 24px;
  height: 24px;
  cursor: pointer;
  color: #6b7280;
  flex: none;
}
.kv {
  width: 100%;
  border-collapse: collapse;
}
.kv td {
  padding: 5px 0;
  font-size: 12px;
  vertical-align: top;
  border-bottom: 1px solid #f3f4f6;
}
.kv .k {
  color: #9ca3af;
  width: 78px;
  white-space: nowrap;
}
.kv .v {
  color: #1f2937;
  padding-left: 10px;
}
.tip {
  margin: 10px 0 0;
  font-size: 11px;
  color: #9ca3af;
  line-height: 1.5;
}
</style>
