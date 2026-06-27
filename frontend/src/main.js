import './leafletSetup.js' // 必须最先执行：把 L 暴露为全局，供 leaflet.heat 注册
import { createApp } from 'vue'
import 'leaflet/dist/leaflet.css'
import './styles/main.css'
import App from './App.vue'

createApp(App).mount('#app')
