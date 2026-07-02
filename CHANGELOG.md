# 更新日志

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 格式，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.5.0] - 2026-07-01

### Added
- **人口密度点查询（F13）**：点击地图任意位置，弹窗显示该坐标所属网格的
  人口密度值（人/km²）及网格中心坐标。
  - 后端新增 `query_population_at_point()`：基于 STRtree 空间索引，
    通过 `intersects` 谓词快速定位点击坐标所在的人口栅格多边形，
    返回网格人口值和 centroid。
  - 新增 `GET /population/at-point` 接口（`statistics.py`），
    接受 `lng` / `lat` 参数，经纬度范围验证后返回密度数据。
  - 前端 `MapContainer.vue` 监听地图 `click` 事件，调用 `api.populationAtPoint()`
    并用 Leaflet Popup 展示结果；无数据或请求失败时优雅降级不打断用户操作。

## [1.4.0] - 2026-07-01

### Fixed
- 修复**行政边界与底图存在偏差**的问题。根因是 `geoUtils.js` 中硬编码的
  `HONGSHAN_CENTER` 和 `HONGSHAN_BBOX` 与边界 GeoJSON 实际范围不匹配，
  导致初始视野 `fitBounds` 定位偏移。现修正：
  - `HONGSHAN_CENTER`：`[30.504259, 114.400718]` → `[30.506565, 114.395178]`
  - `HONGSHAN_BBOX` 西边界：`114.17` → `114.16`

## [1.3.0] - 2026-07-01

### Fixed
- 修复 Leaflet Tooltip / Popup 在快速缩放时偶发崩溃
  「Cannot read properties of null (reading 'latLngToLayerPoint')」。
  根因是 DivOverlay 的 `_updatePosition` / `_animateZoom` 在图层销毁后仍可能被延迟调用，
  此时 `_map` 已置空。现对 `L.Tooltip` 和 `L.Popup` 原型增加空 map 检查。
- 修复 `leaflet.heat` 在快速缩放 / 图层切换中引发崩溃的问题。
  对 `L.HeatLayer` 原型的 `redraw`、`_redraw`、`_animateZoom`、`_reset`、`onRemove`
  增加空 map / canvas / heat 对象检查，并在 `onRemove` 时取消未完成的动画帧。
- 修复热力图 `getImageData` 性能警告（willReadFrequently）。
  在热力图层 `_initCanvas` 时为 canvas 注入 `getContext('2d', { willReadFrequently: true })`。
- 修复热力图数据刷新时旧请求可能覆盖新视野的问题。
  `refresh()` 请求前保存 bbox / zoom，返回后再次校验，旧响应直接丢弃。
- 修复热力图未随 zoom 变化刷新的问题：watch 依赖补充 `store.zoom`。

## [1.2.0] - 2026-07-01

### Added
- 新增三个全类型分析接口：`/analysis/coverage-all`、`/analysis/blind-spots-all`、
  `/analysis/supply-demand-all`，支持三类设施合并缓冲后统一分析。
- 前端 `mapStore` 新增 `totalStats`（全类型合并统计）、`loadTotalStats()`、
  `radiusOf()`、`radiiByType()`、`setBufferRadius()` 等方法。

### Fixed
- 修复「分析设施类型与服务半径未一一对应」：服务半径原为全局单值，会被三类设施共用——
  改某一类半径会连带改变其余两类。现改为**每类设施各自维护服务半径**
  （默认 学校 1000 / 医院 2000 / 公园 500 米），互不影响。
- 修复人口热力偶发崩溃「Cannot read properties of null (reading '_animating')」：
  `leaflet.heat` 图层被移除后 `_map` 置空，再调用 `setLatLngs` 触发 `redraw` 读取空引用。
  现统一在 `setLatLngs` 前先把图层加入地图，并在异步取数后校验图层仍可见。

### Changed
- 供需统计改为固定按**洪山区全域**计算，不再随地图缩放/平移变化。此前按「当前视野」统计
  数值随缩放跳动，且视野外、服务半径内的设施被裁掉造成覆盖率偏低；现以全区固定 bbox 计算，
  数值稳定且代表全区真实供需（覆盖区/盲区地图叠加层仍按当前视野渲染）。

## [1.1.0] - 2026-06-28

### Performance
- 后端空间查询向量化重写：人口点以 numpy 数组常驻，bbox 过滤改为掩码运算，
  覆盖判定用 STRtree 批量查询替代逐点循环 —— 供需统计单次 ~0.34s → ~0.02s。
- 供需 / 盲区 / 覆盖结果加 LRU 缓存，并经 `asyncio.to_thread` 下放线程，避免阻塞事件循环。
- 启用 GZip 压缩响应（热力点 ~400KB → ~50KB），热力坐标按精度取整减小体积。
- 前端初始视野改为同步定位到研究区 bbox，消除「边界异步到达后二次 fitBounds」导致的重复加载。

### Changed
- 目录结构调整为开源项目标准布局：
  - 数据拆分为 `data/raw/`（源数据，.gitignore 排除）与 `data/processed/`（成果数据，Git 跟踪）；
  - 文档统一收敛至 `docs/`（含 `api/`、`requirements/`、`images/` 子目录）；
  - 数据处理脚本移至 `scripts/`。
- 后端默认数据目录改为 `data/processed/`；`docker-compose` 挂载与脚本路径同步更新。

### Added
- 开源标准文件：`LICENSE`(MIT)、`CONTRIBUTING.md`、`CHANGELOG.md`、`.editorconfig`、`.nvmrc`。
- `frontend/.env.example`、`data/README.md`、`scripts/requirements.txt`、GitHub Actions CI。

## [1.0.0] - 2026-06-27

### Added
- 前端（Vue3 + Leaflet）：天地图底图、人口热力（F2）、设施叠加与筛选（F3/F4）、
  点选查询（F5）、服务覆盖区（F6）、供给盲区高亮（F7）、供需统计面板（F8）、
  数据来源说明（F9）、数据未就绪自检门控（F11）。
- 后端（FastAPI）：5 个空间分析接口（F10）+ 数据自检 / 边界元接口；
  默认**文件后端**（shapely，读本地 GeoJSON，开箱即用），可选 PostGIS 后端。
- 一键启动 `npm start`、`docker-compose` 部署（F12）。
- 开发者文档：总览 + 后端 / 前端逐文件说明。
