<script setup>
import { computed } from 'vue'
import { store } from '../stores/mapStore.js'
import { FACILITY_TYPES, fmt } from '../utils/geoUtils.js'

// 依据选中要素类别，决定强调色与图标
const meta = computed(() => {
  const s = store.selected
  if (!s) return null
  if (s.kind === 'facility') {
    const f = FACILITY_TYPES[s.type] || {}
    return { icon: f.emoji || '📍', color: f.color || '#2563eb' }
  }
  if (s.kind === 'blindzone') return { icon: '⚠️', color: '#ef4444' }
  if (s.kind === 'population') return { icon: '📍', color: '#2563eb' }
  return { icon: 'ℹ️', color: '#64748b' }
})

// 人口查询命中格网时，首行密度用大字展示，其余信息进列表
const listRows = computed(() => {
  const s = store.selected
  if (!s) return []
  if (s.kind === 'population' && s.density) return s.rows.slice(1)
  return s.rows
})
</script>

<template>
  <!-- 点选要素详情（F5 / F12），仅在有选中要素时浮现 -->
  <transition name="pop">
    <div v-if="store.selected" class="card detail" :style="{ '--accent': meta.color }">
      <div class="hd">
        <span class="hd-icon">{{ meta.icon }}</span>
        <h3>{{ store.selected.title }}</h3>
        <button class="close" title="关闭" @click="store.clearSelect()">✕</button>
      </div>

      <div v-if="store.selected.kind === 'population' && store.selected.density" class="pop-hero">
        <span class="pop-val">{{ fmt(store.selected.density) }}</span>
        <span class="pop-unit">人/km²</span>
      </div>

      <table class="kv">
        <tbody>
          <tr v-for="(r, i) in listRows" :key="i">
            <td class="k">{{ r.k }}</td>
            <td class="v">{{ r.v }}</td>
          </tr>
        </tbody>
      </table>
      <p class="tip">点击地图其他位置继续查询，或点击设施 / 盲区查看属性。</p>
    </div>
  </transition>
</template>

<style scoped>
.card {
  width: 244px;
  background: rgba(255, 255, 255, 0.97);
  backdrop-filter: blur(6px);
  border-radius: 12px;
  box-shadow: 0 8px 28px rgba(15, 23, 42, 0.18);
  border: 1px solid rgba(226, 232, 240, 0.9);
  font-size: 12px;
  overflow: hidden;
}

/* ── 详情卡片 ── */
.detail {
  border-left: 3px solid var(--accent);
  padding: 12px 14px 13px;
}
.hd {
  display: flex;
  align-items: center;
  gap: 8px;
}
.hd-icon {
  font-size: 16px;
  line-height: 1;
  flex: none;
}
h3 {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.3;
  flex: 1;
}
.close {
  border: none;
  background: #f1f5f9;
  border-radius: 7px;
  width: 24px;
  height: 24px;
  cursor: pointer;
  color: #64748b;
  flex: none;
  font-size: 12px;
  transition: background 0.15s, color 0.15s;
}
.close:hover {
  background: #e2e8f0;
  color: #0f172a;
}

/* 人口密度大字 */
.pop-hero {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin: 10px 0 4px;
  color: var(--accent);
}
.pop-val {
  font-size: 30px;
  font-weight: 800;
  line-height: 1;
  letter-spacing: -0.5px;
}
.pop-unit {
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
}

.kv {
  width: 100%;
  border-collapse: collapse;
  margin-top: 8px;
}
.kv td {
  padding: 4px 0;
  font-size: 11.5px;
  vertical-align: top;
  border-bottom: 1px solid #f1f5f9;
}
.kv tr:last-child td {
  border-bottom: none;
}
.kv .k {
  color: #94a3b8;
  width: 66px;
  white-space: nowrap;
}
.kv .v {
  color: #1e293b;
  padding-left: 10px;
  font-weight: 500;
}
.tip {
  margin: 10px 0 0;
  font-size: 10.5px;
  color: #94a3b8;
  line-height: 1.5;
}

/* 浮现动画 */
.pop-enter-active,
.pop-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.pop-enter-from,
.pop-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
