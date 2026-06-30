<script setup>
import { computed } from 'vue'
import { store } from '../stores/mapStore.js'
import { FACILITY_TYPES, ANALYSIS_TYPE_ORDER } from '../utils/geoUtils.js'

const layerItems = [
  { key: 'heatmap', label: '人口密度热力', dot: '#d7191c' },
  { key: 'school', label: '学校', dot: FACILITY_TYPES.school.color, hasDot: true },
  { key: 'hospital', label: '医院', dot: FACILITY_TYPES.hospital.color, hasDot: true },
  { key: 'park', label: '公园', dot: FACILITY_TYPES.park.color, hasDot: true },
  { key: 'coverage', label: '设施服务覆盖区', dot: '#3b82f6' },
  { key: 'blindzone', label: '供给盲区高亮', dot: '#ef4444' },
]

const effectiveRadius = computed(() => store.radiusOf(store.analysisType))
const isAllAnalysis = computed(() => store.analysisType === 'all')
const isDefaultRadius = computed(() => !store.bufferRadius[store.analysisType])
const isAllDefaultRadius = computed(() =>
  ['school', 'hospital', 'park'].every((t) => !store.bufferRadius[t]),
)

function setType(t) {
  store.analysisType = t
}
function resetRadius() {
  store.resetBufferRadius(store.analysisType)
}

function resetAllRadii() {
  store.resetAllBufferRadii()
}
</script>

<template>
  <div class="panel control-panel">
    <section class="block">
      <h3>图层控制</h3>
      <label v-for="it in layerItems" :key="it.key" class="layer-row">
        <input type="checkbox" :checked="store.layers[it.key]" @change="store.toggle(it.key)" />
        <span v-if="it.hasDot" class="dot" :style="{ background: it.dot }" />
        <span class="layer-label">{{ it.label }}</span>
      </label>
    </section>

    <section class="block">
      <h3>分析设施类型</h3>
      <p class="hint">用于服务覆盖区、供给盲区与供需统计</p>
      <div class="seg">
        <button
          v-for="t in ANALYSIS_TYPE_ORDER"
          :key="t"
          :class="['seg-btn', { active: store.analysisType === t }]"
          :style="store.analysisType === t ? { background: FACILITY_TYPES[t].color } : {}"
          @click="setType(t)"
        >
          {{ FACILITY_TYPES[t].emoji }} {{ FACILITY_TYPES[t].label }}
        </button>
      </div>
    </section>

    <section class="block">
      <h3>服务半径</h3>
      <template v-if="!isAllAnalysis">
        <div class="row-between">
          <span class="big">{{ effectiveRadius }} m</span>
          <button class="link" v-if="!isDefaultRadius" @click="resetRadius">恢复默认</button>
          <span class="hint" v-else>默认值</span>
        </div>
        <input
          type="range"
          min="200"
          max="10000"
          step="100"
          :value="effectiveRadius"
          @input="store.setBufferRadius(store.analysisType, Number($event.target.value))"
        />
      </template>
      <div v-else class="all-radius">
        <div class="row-between compact-head">
          <span class="hint compact-hint">三类设施分别调整</span>
          <button class="link" v-if="!isAllDefaultRadius" @click="resetAllRadii">恢复默认</button>
          <span class="hint" v-else>默认值</span>
        </div>
        <div v-for="t in ['school', 'hospital', 'park']" :key="t" class="radius-row compact-radius-row">
          <div class="radius-line">
            <span class="radius-label">{{ FACILITY_TYPES[t].emoji }} {{ FACILITY_TYPES[t].label }}</span>
            <span class="radius-value">{{ store.radiusOf(t) }} m</span>
          </div>
          <input
            class="compact-range"
            type="range"
            min="200"
            max="10000"
            step="100"
            :value="store.radiusOf(t)"
            @input="store.setBufferRadius(t, Number($event.target.value))"
          />
        </div>
      </div>
    </section>

    <section class="block">
      <h3>盲区人口阈值</h3>
      <p class="hint">人口密度高于该值才视为需重点服务区</p>
      <div class="row-between">
        <input
          class="num"
          type="number"
          min="0"
          step="100"
          v-model.number="store.popThreshold"
        />
        <span class="hint">人/km²</span>
      </div>
    </section>
  </div>
</template>

<style scoped>
.control-panel {
  width: 240px;
}
.block + .block {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid #eef0f3;
}
h3 {
  margin: 0 0 8px;
  font-size: 13px;
  color: #111827;
}
.hint {
  margin: 0 0 8px;
  font-size: 11px;
  color: #9ca3af;
  line-height: 1.4;
}
.layer-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  cursor: pointer;
  font-size: 13px;
  color: #374151;
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex: none;
}
.dot-sq {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  flex: none;
}
.layer-label {
  flex: 1;
}
.seg {
  display: flex;
  gap: 6px;
}
.seg-btn {
  flex: 1;
  padding: 7px 4px;
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  border-radius: 7px;
  font-size: 12px;
  cursor: pointer;
  color: #374151;
  transition: all 0.15s;
}
.seg-btn.active {
  color: #fff;
  border-color: transparent;
  font-weight: 600;
}
.row-between {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.big {
  font-size: 18px;
  font-weight: 700;
  color: #111827;
}
input[type='range'] {
  width: 100%;
  margin-top: 8px;
  accent-color: #2563eb;
}
.all-radius {
  margin-bottom: 0;
}
.compact-head {
  margin-bottom: 3px;
}
.compact-hint {
  margin: 0;
}
.radius-row + .radius-row {
  margin-top: 5px;
}
.radius-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  line-height: 1.1;
}
.radius-label {
  font-size: 11px;
  color: #374151;
  font-weight: 600;
}
.radius-value {
  font-size: 11px;
  color: #111827;
  font-weight: 700;
}
.compact-range {
  margin-top: 3px !important;
}
.num {
  width: 110px;
  padding: 6px 8px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 13px;
}
.link {
  background: none;
  border: none;
  color: #2563eb;
  cursor: pointer;
  font-size: 12px;
  padding: 0;
}
</style>
