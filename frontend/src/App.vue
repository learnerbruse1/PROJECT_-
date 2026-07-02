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

onMounted(() => store.init())

const busy = computed(() =>
  Object.values(store.loading).some(Boolean),
)
const counts = computed(() => store.status?.counts || {})

const activeTab = ref('layers')
</script>

<template>
  <div class="app">
    <header class="topbar">
      <div class="brand">
        <span class="logo">🗺️</span>
        <h1>洪山区人口分布热力与公共设施叠加分析系统</h1>
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
        <!-- Tab 切换 -->
        <div class="tabs">
          <button :class="['tab', { active: activeTab === 'layers' }]" @click="activeTab = 'layers'">👁 图层</button>
          <button :class="['tab', { active: activeTab === 'analysis' }]" @click="activeTab = 'analysis'">📊 分析</button>
        </div>
        <div class="tab-content">
          <LayerControl v-show="activeTab === 'layers'" mode="layers" />
          <LayerControl v-show="activeTab === 'analysis'" mode="analysis" />
        </div>

        <!-- 供需统计：底部折叠，始终可见 -->
        <StatsPanel />

        <!-- 人口查询提示 -->
        <div class="hint-bar">🖱 点击地图任意位置查询人口密度</div>
      </aside>

      <div class="map-area">
        <MapContainer ref="mapWrap">
          <HeatmapLayer />
          <FacilityLayer />
          <CoverageLayer />
          <BlindZoneLayer />
        </MapContainer>
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
  height: 42px;
  flex: none;
  background: #0f172a;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 14px;
  z-index: 1200;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.2);
}
.brand {
  display: flex;
  align-items: center;
  gap: 8px;
}
.logo { font-size: 20px; }
h1 { margin: 0; font-size: 14px; font-weight: 700; white-space: nowrap; }
.status { display: flex; align-items: center; gap: 8px; }
.busy { font-size: 11px; color: #fbbf24; animation: pulse 1.2s infinite; }
@keyframes pulse { 50% { opacity: 0.4; } }
.badge {
  font-size: 11px; padding: 3px 9px; border-radius: 999px; font-weight: 600; white-space: nowrap;
}
.badge.green { background: #064e3b; color: #6ee7b7; }
.badge.red   { background: #7f1d1d; color: #fca5a5; }
.badge.gray  { background: #334155; color: #cbd5e1; }

/* ── 主舞台：侧栏 + 地图 ── */
.stage {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* ── 左侧面板 ── */
.sidebar {
  width: 272px;
  flex: none;
  display: flex;
  flex-direction: column;
  background: #f8fafc;
  border-right: 1px solid #e2e8f0;
  overflow: hidden;
}
.tabs {
  display: flex;
  padding: 8px 8px 0;
  gap: 4px;
}
.tab {
  flex: 1;
  padding: 8px 0;
  border: none;
  border-radius: 8px 8px 0 0;
  background: #e2e8f0;
  font-size: 13px;
  cursor: pointer;
  color: #64748b;
  font-weight: 500;
  transition: all 0.15s;
}
.tab.active {
  background: #fff;
  color: #1e293b;
  font-weight: 700;
  box-shadow: 0 -1px 3px rgba(0,0,0,0.06);
}
.tab-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px 14px;
  background: #fff;
  margin: 0 8px;
  border-radius: 0 0 8px 8px;
}

/* ── 人口查询提示 ── */
.hint-bar {
  padding: 8px 14px;
  font-size: 11px;
  color: #64748b;
  background: #f1f5f9;
  border-top: 1px solid #e2e8f0;
  text-align: center;
}

/* ── 地图区域 ── */
.map-area {
  flex: 1;
  position: relative;
  overflow: hidden;
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
  border-radius: 8px;
  font-size: 13px;
  z-index: 1500;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
}
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* ── 数据未就绪 ── */
.not-ready {
  flex: 1;
  display: flex; align-items: center; justify-content: center;
  background: #f1f5f9;
}
.nr-card {
  background: #fff; border-radius: 14px; padding: 32px 40px;
  text-align: center; max-width: 420px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.1);
}
.nr-icon { font-size: 40px; }
.nr-card h2 { margin: 8px 0; color: #b91c1c; }
.nr-card p { color: #475569; font-size: 13px; line-height: 1.6; }
.nr-card ul { text-align: left; display: inline-block; margin: 12px 0; font-size: 13px; list-style: none; padding: 0; }
.nr-card li { padding: 2px 0; }
.ok { color: #16a34a; } .miss { color: #dc2626; }
.muted { color: #94a3b8; }
code { background: #f1f5f9; padding: 1px 5px; border-radius: 4px; font-size: 12px; }
.nr-card button {
  margin-top: 10px; padding: 8px 20px; border: none;
  background: #2563eb; color: #fff; border-radius: 8px; cursor: pointer; font-size: 13px;
}
</style>
