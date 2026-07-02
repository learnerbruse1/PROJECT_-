<script setup>
import { onMounted, watch, computed } from 'vue'
import { store } from '../stores/mapStore.js'
import { FACILITY_TYPES, fmt, pct } from '../utils/geoUtils.js'

let timer = null
function scheduleReload() {
  clearTimeout(timer)
  timer = setTimeout(() => {
    store.loadStats()
    if (store.analysisType === 'all') store.loadTotalStats()
  }, 500)
}

onMounted(() => {
  if (store.ready) {
    store.loadStats()
    if (store.analysisType === 'all') store.loadTotalStats()
  }
})

watch(
  () => [store.bufferRadius.school, store.bufferRadius.hospital, store.bufferRadius.park, store.ready],
  scheduleReload,
)

watch(
  () => store.analysisType,
  (t) => {
    if (t === 'all') store.loadTotalStats()
  },
)

// 当前展示的统计数据
const stat = computed(() => {
  if (store.analysisType === 'all') return store.totalStats
  return store.stats[store.analysisType]
})

const label = computed(() => {
  if (store.analysisType === 'all') return '全部设施合并'
  return FACILITY_TYPES[store.analysisType]?.label || ''
})

const color = computed(() => {
  if (store.analysisType === 'all') return FACILITY_TYPES.all.color
  return FACILITY_TYPES[store.analysisType]?.color || '#6b7280'
})

function rateColor(rate) {
  if (rate == null) return '#9ca3af'
  if (rate >= 0.6) return '#16a34a'
  if (rate >= 0.3) return '#f59e0b'
  return '#dc2626'
}
</script>

<template>
  <div class="stats">
    <div class="summary">
      <span class="stats-dot" :style="{ background: color }" />
      <span class="stats-label">{{ label }}</span>
      <span class="stats-rate" :style="{ color: stat ? rateColor(stat.coverage_rate) : '#9ca3af' }">
        {{ stat ? pct(stat.coverage_rate) : '—' }}
      </span>
    </div>

    <template v-if="stat">
      <div class="bar">
        <div
          class="bar-fill"
          :style="{
            width: Math.max(2, (stat.coverage_rate * 100).toFixed(1)) + '%',
            background: rateColor(stat.coverage_rate),
          }"
        />
      </div>
      <div class="meta-row">
        <div class="meta-item">
          <span class="meta-val">{{ fmt(stat.covered_population) }}</span>
          <span class="meta-lbl">覆盖格网</span>
        </div>
        <div class="meta-item">
          <span class="meta-val">{{ fmt(stat.total_population) }}</span>
          <span class="meta-lbl">总格网</span>
        </div>
        <div v-if="store.analysisType !== 'all'" class="meta-item">
          <span class="meta-val">{{ stat.facility_count ?? '—' }}</span>
          <span class="meta-lbl">设施数</span>
        </div>
      </div>
    </template>
    <div v-else class="empty">加载中…</div>
  </div>
</template>

<style scoped>
.summary {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.stats-dot {
  width: 12px; height: 12px;
  border-radius: 50%;
  flex: none;
}
.stats-label {
  font-size: 13px;
  color: #111827;
  font-weight: 700;
}
.stats-rate {
  margin-left: auto;
  font-size: 24px;
  font-weight: 800;
  letter-spacing: -0.5px;
}
.bar {
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 12px;
}
.bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s;
}
.meta-row {
  display: flex;
  gap: 8px;
  justify-content: center;
}
.meta-item {
  flex: 1;
  text-align: center;
  background: var(--c-surface-2);
  border: 1px solid var(--c-border);
  border-radius: 9px;
  padding: 8px 4px;
}
.meta-val {
  display: block;
  font-size: 15px;
  font-weight: 700;
  color: #111827;
}
.meta-lbl {
  display: block;
  font-size: 10px;
  color: #9ca3af;
  margin-top: 2px;
}
.empty {
  font-size: 12px;
  color: #9ca3af;
  text-align: center;
  padding: 6px 0;
}
</style>
