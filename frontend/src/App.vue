<script setup>
import { onMounted, computed } from 'vue'
import { store } from './stores/mapStore.js'
import MapContainer from './components/MapContainer.vue'
import HeatmapLayer from './components/HeatmapLayer.vue'
import FacilityLayer from './components/FacilityLayer.vue'
import CoverageLayer from './components/CoverageLayer.vue'
import BlindZoneLayer from './components/BlindZoneLayer.vue'
import LayerControl from './components/LayerControl.vue'
import StatsPanel from './components/StatsPanel.vue'
import InfoPanel from './components/InfoPanel.vue'
import Legend from './components/Legend.vue'

onMounted(() => store.init())

const busy = computed(() =>
  Object.values(store.loading).some(Boolean),
)
const counts = computed(() => store.status?.counts || {})
</script>

<template>
  <div class="app">
    <header class="topbar">
      <div class="brand">
        <span class="logo">🗺️</span>
        <div>
          <h1>洪山区人口分布热力与公共设施叠加分析系统</h1>
          <p>人口热力 · 设施叠加 · 服务覆盖 · 供给盲区 · 供需统计</p>
        </div>
      </div>
      <div class="status">
        <span v-if="busy" class="busy">● 加载中…</span>
        <span v-if="store.ready === null" class="badge gray">数据检测中…</span>
        <span v-else-if="store.ready" class="badge green">
          数据就绪 · 设施 {{ counts.facilities }} · 人口格 {{ counts.population_points }}
        </span>
        <span v-else class="badge red">数据未就绪</span>
      </div>
    </header>

    <!-- 数据未就绪（F11）：避免页面空白，明确提示缺失项 -->
    <div v-if="store.ready === false" class="not-ready">
      <div class="nr-card">
        <div class="nr-icon">⚠️</div>
        <h2>数据未就绪</h2>
        <p>后端未检测到完整的本地数据文件，请确认 <code>data/</code> 目录与后端服务已正确部署。</p>
        <ul v-if="store.status?.files">
          <li v-for="(ok, name) in store.status.files" :key="name">
            <span :class="ok ? 'ok' : 'miss'">{{ ok ? '✓' : '✗' }}</span> {{ name }}
          </li>
        </ul>
        <p v-else class="muted">无法连接后端服务（{{ store.error || '请启动 FastAPI 后端' }}）。</p>
        <button @click="store.init()">重新检测</button>
      </div>
    </div>

    <!-- 主舞台 -->
    <main v-else class="stage">
      <MapContainer>
        <HeatmapLayer />
        <FacilityLayer />
        <CoverageLayer />
        <BlindZoneLayer />
      </MapContainer>

      <div class="dock left">
        <LayerControl />
      </div>
      <div class="dock right">
        <StatsPanel />
        <InfoPanel />
      </div>
      <div class="dock legend">
        <Legend />
      </div>

      <transition name="fade">
        <div v-if="store.error" class="toast">{{ store.error }}</div>
      </transition>
    </main>
  </div>
</template>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}
.topbar {
  height: 58px;
  flex: none;
  background: #0f172a;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 18px;
  z-index: 1200;
  box-shadow: 0 1px 8px rgba(0, 0, 0, 0.25);
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}
.logo {
  font-size: 24px;
}
h1 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
}
.brand p {
  margin: 1px 0 0;
  font-size: 11px;
  color: #94a3b8;
}
.status {
  display: flex;
  align-items: center;
  gap: 12px;
}
.busy {
  font-size: 12px;
  color: #fbbf24;
  animation: pulse 1.2s infinite;
}
@keyframes pulse {
  50% {
    opacity: 0.4;
  }
}
.badge {
  font-size: 12px;
  padding: 5px 11px;
  border-radius: 999px;
  font-weight: 600;
}
.badge.green {
  background: #064e3b;
  color: #6ee7b7;
}
.badge.red {
  background: #7f1d1d;
  color: #fca5a5;
}
.badge.gray {
  background: #334155;
  color: #cbd5e1;
}
.stage {
  position: relative;
  flex: 1;
  overflow: hidden;
}
.dock {
  position: absolute;
  z-index: 1000;
  pointer-events: none;
}
.dock > :deep(*) {
  pointer-events: auto;
}
.dock.left {
  top: 14px;
  left: 14px;
}
.dock.right {
  top: 14px;
  right: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: calc(100% - 28px);
  overflow: auto;
}
.dock.legend {
  bottom: 22px;
  left: 14px;
}
.toast {
  position: absolute;
  bottom: 22px;
  left: 50%;
  transform: translateX(-50%);
  background: #1f2937;
  color: #fee2e2;
  padding: 10px 18px;
  border-radius: 8px;
  font-size: 13px;
  z-index: 1500;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
.not-ready {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f1f5f9;
}
.nr-card {
  background: #fff;
  border-radius: 14px;
  padding: 32px 40px;
  text-align: center;
  max-width: 420px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.1);
}
.nr-icon {
  font-size: 40px;
}
.nr-card h2 {
  margin: 8px 0;
  color: #b91c1c;
}
.nr-card p {
  color: #475569;
  font-size: 13px;
  line-height: 1.6;
}
.nr-card ul {
  text-align: left;
  display: inline-block;
  margin: 12px 0;
  font-size: 13px;
  list-style: none;
  padding: 0;
}
.nr-card li {
  padding: 2px 0;
}
.ok {
  color: #16a34a;
}
.miss {
  color: #dc2626;
}
.muted {
  color: #94a3b8;
}
code {
  background: #f1f5f9;
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 12px;
}
.nr-card button {
  margin-top: 10px;
  padding: 8px 20px;
  border: none;
  background: #2563eb;
  color: #fff;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
}
</style>
