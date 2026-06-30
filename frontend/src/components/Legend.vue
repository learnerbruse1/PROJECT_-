<script setup>
import { computed } from 'vue'
import { store } from '../stores/mapStore.js'
import { HEAT_LEGEND, FACILITY_TYPES } from '../utils/geoUtils.js'

function rgba(hex, alpha) {
  const value = hex.replace('#', '')
  const r = parseInt(value.slice(0, 2), 16)
  const g = parseInt(value.slice(2, 4), 16)
  const b = parseInt(value.slice(4, 6), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

const coverageLegendStyle = computed(() => {
  const color = FACILITY_TYPES[store.analysisType]?.color || FACILITY_TYPES.school.color
  return { background: rgba(color, 0.3), borderColor: color }
})
</script>

<template>
  <div class="legend">
    <div class="grp" v-if="store.layers.heatmap">
      <div class="t">人口密度</div>
      <div class="ramp">
        <span v-for="s in HEAT_LEGEND" :key="s.color" class="sw" :style="{ background: s.color }" :title="s.label" />
      </div>
      <div class="ends"><span>低</span><span>高</span></div>
    </div>

    <div class="grp">
      <div class="t">设施 / 分析</div>
      <div class="item" v-for="t in ['school', 'hospital', 'park']" :key="t">
        <span class="dot" :style="{ background: FACILITY_TYPES[t].color }" />{{ FACILITY_TYPES[t].label }}
      </div>
      <div class="item"><span class="box cover" :style="coverageLegendStyle" />服务覆盖区</div>
      <div class="item"><span class="box blind" />供给盲区</div>
    </div>
  </div>
</template>

<style scoped>
.legend {
  background: rgba(255, 255, 255, 0.94);
  border-radius: 8px;
  padding: 9px 12px;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.18);
  font-size: 11px;
  color: #374151;
  pointer-events: auto;
}
.grp + .grp {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #eef0f3;
}
.t {
  font-weight: 600;
  margin-bottom: 4px;
  color: #111827;
}
.ramp {
  display: flex;
  width: 130px;
  height: 10px;
  border-radius: 3px;
  overflow: hidden;
}
.sw {
  flex: 1;
}
.ends {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: #9ca3af;
  margin-top: 2px;
}
.item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 1px 0;
}
.dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
}
.box {
  width: 11px;
  height: 9px;
  border-radius: 2px;
}
.box.cover {
  border: 1px solid;
}
.box.blind {
  background: rgba(239, 68, 68, 0.4);
  border: 1px solid #b91c1c;
}
</style>
