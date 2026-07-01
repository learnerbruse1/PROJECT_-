<script setup>
import { onMounted, watch } from 'vue'
import { store } from '../stores/mapStore.js'
import { FACILITY_TYPES, FACILITY_POINT_ORDER, fmt, pct } from '../utils/geoUtils.js'

let timer = null
function scheduleReload() {
  clearTimeout(timer)
  timer = setTimeout(() => {
    store.loadStats()
  }, 500)
}

onMounted(() => {
  if (store.ready) {
    store.loadStats()
  }
})

// 供需统计固定按全区计算，不随地图视野变化；仅在服务半径或数据就绪状态变化时刷新
watch(
  () => [store.bufferRadius.school, store.bufferRadius.hospital, store.bufferRadius.park, store.ready],
  scheduleReload,
)

function rateColor(rate) {
  if (rate == null) return '#9ca3af'
  if (rate >= 0.6) return '#16a34a'
  if (rate >= 0.3) return '#f59e0b'
  return '#dc2626'
}
</script>

<template>
  <div class="panel stats-panel">
    <div class="hd">
      <h3>供需统计（洪山区全域）</h3>
      <button class="refresh" :disabled="store.loading.stats" @click="store.loadStats()">
        {{ store.loading.stats ? '统计中…' : '刷新' }}
      </button>
    </div>

    <div class="cards">
      <div
        v-for="t in FACILITY_POINT_ORDER"
        :key="t"
        :class="['card', { active: store.analysisType === t }]"
        @click="store.setAnalysisType(t)"
      >
        <div class="card-hd">
          <span class="dot" :style="{ background: FACILITY_TYPES[t].color }" />
          <span class="name">{{ FACILITY_TYPES[t].label }}</span>
          <span class="count">{{ fmt(store.stats[t]?.facility_count) }} 处</span>
        </div>

        <template v-if="store.stats[t]">
          <div class="rate" :style="{ color: rateColor(store.stats[t].coverage_rate) }">
            {{ pct(store.stats[t].coverage_rate) }}
          </div>
          <div class="bar">
            <div
              class="bar-fill"
              :style="{
                width: (store.stats[t].coverage_rate * 100).toFixed(1) + '%',
                background: rateColor(store.stats[t].coverage_rate),
              }"
            />
          </div>
          <div class="meta">
            <span>覆盖 {{ fmt(store.stats[t].covered_population) }}</span>
            <span>/ 共 {{ fmt(store.stats[t].total_population) }} 格</span>
          </div>
          <div class="meta">
            <span>千人设施量</span>
            <span class="strong">{{ store.stats[t].per_capita?.toFixed(3) ?? '—' }}</span>
          </div>
          <div class="meta sub">服务半径 {{ store.stats[t].buffer_radius }} m</div>
        </template>
        <div v-else class="empty">{{ store.loading.stats ? '加载中…' : '暂无数据' }}</div>
      </div>
    </div>
    <p class="foot">覆盖率 = 服务区覆盖的人口格网 / 全区总格网；按全区固定计算，不随地图缩放变化。点击卡片可切换分析类型。</p>
  </div>
</template>

<style scoped>
.stats-panel {
  width: 270px;
}
.hd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
h3 {
  margin: 0;
  font-size: 13px;
  color: #111827;
}
.refresh {
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  border-radius: 6px;
  font-size: 12px;
  padding: 3px 10px;
  cursor: pointer;
  color: #374151;
}
.cards {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.card {
  border: 1px solid #eef0f3;
  border-radius: 9px;
  padding: 10px 12px;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.card.active {
  border-color: #c7d2fe;
  box-shadow: 0 0 0 2px #eef2ff;
}
.card-hd {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 13px;
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.name {
  font-weight: 600;
  color: #111827;
}
.count {
  margin-left: auto;
  color: #6b7280;
  font-size: 12px;
}
.rate {
  font-size: 26px;
  font-weight: 800;
  line-height: 1.2;
  margin-top: 4px;
}
.bar {
  height: 6px;
  background: #f1f5f9;
  border-radius: 4px;
  overflow: hidden;
  margin: 4px 0 8px;
}
.bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s;
}
.meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #6b7280;
  margin-top: 2px;
}
.meta .strong {
  color: #111827;
  font-weight: 600;
}
.meta.sub {
  color: #9ca3af;
  font-size: 11px;
  margin-top: 4px;
}
.empty {
  color: #9ca3af;
  font-size: 12px;
  padding: 8px 0;
}
.foot {
  margin: 10px 0 0;
  font-size: 11px;
  color: #9ca3af;
  line-height: 1.5;
}
</style>
