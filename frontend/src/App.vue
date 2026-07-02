<script setup>
import { ref, onMounted, computed } from 'vue'
import { store } from './stores/mapStore.js'
import MapContainer from './components/MapContainer.vue'
import HeatmapLayer from './components/HeatmapLayer.vue'
import FacilityLayer from './components/FacilityLayer.vue'
import CoverageLayer from './components/CoverageLayer.vue'
import BlindZoneLayer from './components/BlindZoneLayer.vue'
import LayerControl from './components/LayerControl.vue'
import StatsPanel from './components/StatsPanel.vue'
import Legend from './components/Legend.vue'
import InfoPanel from './components/InfoPanel.vue'

onMounted(() => store.init())

const busy = computed(() =>
  Object.values(store.loading).some(Boolean),
)
const counts = computed(() => store.status?.counts || {})

// 手风琴折叠：各分区可独立展开 / 收起
const openSections = ref({ layers: true, analysis: false, stats: true })
function toggleSection(key) {
  openSections.value[key] = !openSections.value[key]
}
</script>

<template>
  <div class="app">
    <header class="topbar">
      <div class="brand">
        <span class="logo">🗺️</span>
        <div class="brand-text">
          <h1>洪山区人口分布热力与公共设施叠加分析系统</h1>
          <span class="subtitle">人口密度 · 设施覆盖 · 供给盲区识别</span>
        </div>
      </div>
      <div class="status">
        <span v-if="busy" class="busy">● 加载中…</span>
        <span v-if="store.ready === null" class="badge gray">数据检测中…</span>
        <span v-else-if="store.ready" class="badge green">
          <span class="badge-dot" />数据就绪 · 设施 {{ counts.facilities }} · 人口格 {{ counts.population_points }}
        </span>
        <span v-else class="badge red">数据未就绪</span>
      </div>
    </header>

    <!-- 数据未就绪 -->
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
      <aside class="sidebar">
        <!-- 手风琴：图层 / 分析 / 统计，纵向堆叠，可逐块折叠 -->
        <div class="accordion">
          <section class="acc-item" :class="{ open: openSections.layers }">
            <button class="acc-head" @click="toggleSection('layers')">
              <span class="acc-icon">👁</span>
              <span class="acc-title">图层控制</span>
              <span class="acc-chev">▾</span>
            </button>
            <div v-show="openSections.layers" class="acc-body">
              <LayerControl mode="layers" />
            </div>
          </section>

          <section class="acc-item" :class="{ open: openSections.analysis }">
            <button class="acc-head" @click="toggleSection('analysis')">
              <span class="acc-icon">📊</span>
              <span class="acc-title">分析配置</span>
              <span class="acc-chev">▾</span>
            </button>
            <div v-show="openSections.analysis" class="acc-body">
              <LayerControl mode="analysis" />
            </div>
          </section>

          <section class="acc-item" :class="{ open: openSections.stats }">
            <button class="acc-head" @click="toggleSection('stats')">
              <span class="acc-icon">📈</span>
              <span class="acc-title">供需统计</span>
              <span class="acc-chev">▾</span>
            </button>
            <div v-show="openSections.stats" class="acc-body">
              <StatsPanel />
            </div>
          </section>
        </div>

        <!-- 人口查询提示 -->
        <div class="hint-bar"><span class="hint-icon">🖱</span> 点击地图任意位置查询人口密度</div>
      </aside>

      <div class="map-area">
        <MapContainer ref="mapWrap">
          <HeatmapLayer />
          <FacilityLayer />
          <CoverageLayer />
          <BlindZoneLayer />
        </MapContainer>
        <!-- 点选详情 / 数据说明（浮于地图右上） -->
        <div class="map-info">
          <InfoPanel />
        </div>
        <div class="map-legend">
          <Legend />
        </div>
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
/* ── 顶栏 ── */
.topbar {
  height: 52px;
  flex: none;
  background: linear-gradient(100deg, #0b1220 0%, #172033 55%, #1e293b 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 18px;
  z-index: 1200;
  box-shadow: 0 2px 12px rgba(15, 23, 42, 0.28);
  border-bottom: 2px solid var(--c-primary);
}
.brand {
  display: flex;
  align-items: center;
  gap: 11px;
  min-width: 0;
}
.logo {
  font-size: 20px;
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 9px;
  flex: none;
}
.brand-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
h1 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  white-space: nowrap;
  letter-spacing: 0.2px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.subtitle {
  font-size: 10.5px;
  color: #94a3b8;
  letter-spacing: 1px;
  margin-top: 1px;
}
.status { display: flex; align-items: center; gap: 10px; flex: none; }
.busy { font-size: 11px; color: #fbbf24; animation: pulse 1.2s infinite; }
@keyframes pulse { 50% { opacity: 0.4; } }
.badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px; padding: 5px 11px; border-radius: 999px; font-weight: 600; white-space: nowrap;
  border: 1px solid transparent;
}
.badge-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: #34d399;
  box-shadow: 0 0 0 3px rgba(52, 211, 153, 0.25);
}
.badge.green { background: rgba(6, 78, 59, 0.55); color: #6ee7b7; border-color: rgba(52, 211, 153, 0.35); }
.badge.red   { background: rgba(127, 29, 29, 0.6); color: #fca5a5; border-color: rgba(248, 113, 113, 0.4); }
.badge.gray  { background: rgba(51, 65, 85, 0.7); color: #cbd5e1; }

/* ── 主舞台：侧栏 + 地图 ── */
.stage {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* ── 左侧面板 ── */
.sidebar {
  width: 280px;
  flex: none;
  display: flex;
  flex-direction: column;
  background: var(--c-surface-2);
  border-right: 1px solid var(--c-border);
  box-shadow: 1px 0 8px rgba(15, 23, 42, 0.05);
  overflow: hidden;
  z-index: 500;
}
/* ── 手风琴分区 ── */
.accordion {
  flex: 1;
  overflow-y: auto;
  padding: 12px 12px 4px;
}
.acc-item {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: 12px;
  box-shadow: var(--shadow-sm);
  margin-bottom: 10px;
  overflow: hidden;
}
.acc-item.open {
  border-color: #dbe4f2;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.07);
}
.acc-head {
  display: flex;
  align-items: center;
  gap: 9px;
  width: 100%;
  padding: 12px 13px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 13.5px;
  font-weight: 700;
  color: var(--c-text);
  transition: background 0.15s;
}
.acc-head:hover {
  background: #f8fafc;
}
.acc-icon {
  font-size: 15px;
  line-height: 1;
  flex: none;
}
.acc-title {
  flex: 1;
  text-align: left;
}
.acc-chev {
  color: #94a3b8;
  font-size: 12px;
  transition: transform 0.2s;
  transform: rotate(-90deg); /* 收起时朝右 */
}
.acc-item.open .acc-chev {
  transform: rotate(0deg); /* 展开时朝下 */
}
.acc-body {
  padding: 8px 14px 14px;
  border-top: 1px solid var(--c-border);
}

/* ── 人口查询提示 ── */
.hint-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin: 0 12px 12px;
  padding: 9px 12px;
  font-size: 11px;
  color: #5b6b82;
  background: linear-gradient(180deg, #f0f5fb, #e8eff8);
  border: 1px solid #dbe4f0;
  border-radius: 10px;
}
.hint-icon { font-size: 13px; }

/* ── 地图区域 ── */
.map-area {
  flex: 1;
  position: relative;
  overflow: hidden;
}
.map-info {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 1000;
}
.map-legend {
  position: absolute;
  bottom: 28px;
  left: 10px;
  z-index: 1000;
  pointer-events: none;
}
.map-legend :deep(*) {
  pointer-events: auto;
}

/* ── Toast ── */
.toast {
  position: absolute;
  bottom: 22px;
  left: 50%;
  transform: translateX(-50%);
  background: #1f2937;
  color: #fee2e2;
  padding: 10px 18px;
  border-radius: 10px;
  font-size: 13px;
  z-index: 1500;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
  border: 1px solid rgba(248, 113, 113, 0.3);
}
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* ── 数据未就绪 ── */
.not-ready {
  flex: 1;
  display: flex; align-items: center; justify-content: center;
  background: var(--c-bg);
}
.nr-card {
  background: var(--c-surface); border-radius: 16px; padding: 32px 40px;
  text-align: center; max-width: 420px;
  box-shadow: 0 12px 40px rgba(15, 23, 42, 0.12);
  border: 1px solid var(--c-border);
}
.nr-icon { font-size: 42px; }
.nr-card h2 { margin: 8px 0; color: #b91c1c; }
.nr-card p { color: #475569; font-size: 13px; line-height: 1.6; }
.nr-card ul { text-align: left; display: inline-block; margin: 12px 0; font-size: 13px; list-style: none; padding: 0; }
.nr-card li { padding: 2px 0; }
.ok { color: #16a34a; } .miss { color: #dc2626; }
.muted { color: #94a3b8; }
code { background: #f1f5f9; padding: 1px 5px; border-radius: 4px; font-size: 12px; }
.nr-card button {
  margin-top: 10px; padding: 9px 22px; border: none;
  background: var(--c-primary); color: #fff; border-radius: 9px; cursor: pointer; font-size: 13px;
  font-weight: 600; transition: background 0.15s;
}
.nr-card button:hover { background: var(--c-primary-d); }
</style>
