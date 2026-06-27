# 更新日志

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 格式，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Fixed
- 修复「分析设施类型与服务半径未一一对应」：服务半径原为全局单值，会被三类设施共用——
  改某一类半径会连带改变其余两类，供需面板三张卡片显示同一半径，且覆盖区/盲区对非选中
  类型用错半径。现改为**每类设施各自维护服务半径**（默认 学校 1000 / 医院 2000 / 公园 500 米），
  互不影响；切换分析类型时滑块与各卡片各自显示对应半径。
- 修复人口热力偶发崩溃「Cannot read properties of null (reading '_animating')」：
  `leaflet.heat` 图层被移除后 `_map` 置空，再调用 `setLatLngs` 会触发 `redraw` 读取空引用。
  现统一在 `setLatLngs` 前先把图层加入地图，并在异步取数后校验图层仍可见。

### Performance
- 后端空间查询向量化重写：人口点以 numpy 数组常驻，bbox 过滤改为掩码运算，
  覆盖判定用 STRtree 批量查询替代逐点循环 —— 供需统计单次 ~0.34s → ~0.02s。
- 供需/盲区/覆盖结果加 LRU 缓存，并经 `asyncio.to_thread` 下放线程，避免阻塞事件循环。
- 启用 GZip 压缩响应（热力点 ~400KB → ~50KB），热力坐标按精度取整减小体积。
- 前端初始视野改为同步定位到研究区 bbox，消除「边界异步到达后二次 fitBounds」导致的重复加载。

### Changed
- 供需统计改为固定按**洪山区全域**计算，不再随地图缩放/平移变化。此前按「当前视野」统计会让
  数值随缩放跳动，且视野外、服务半径内的设施被裁掉造成覆盖率偏低的边界误差；现以全区固定 bbox
  计算，数值稳定且代表全区真实供需（覆盖区/盲区地图叠加层仍按当前视野渲染，属可视化范畴）。
- 目录结构调整为开源项目标准布局：
  - 数据拆分为 `data/raw/`（源数据，忽略跟踪）与 `data/processed/`（成果数据，跟踪）；
  - 文档统一收敛至 `docs/`（含 `api/`、`requirements/`、`images/` 子目录）；
  - 数据处理脚本移至 `scripts/`。
- 后端默认数据目录改为 `data/processed/`；`docker-compose` 挂载与脚本路径同步更新。

### Added
- 开源标准文件：`LICENSE`(MIT)、`CONTRIBUTING.md`、`CHANGELOG.md`、`.editorconfig`、`.nvmrc`。
- `frontend/.env.example` 环境变量模板；真实 `.env` 改为忽略提交（密钥不入库）。
- `data/README.md`、`scripts/requirements.txt`、GitHub Actions CI（前端构建 + 后端导入自检）。

## [1.0.0] - 2026-06-27

### Added
- 前端（Vue3 + Leaflet）：天地图底图与自动定位、人口热力（F2）、设施叠加与筛选（F3/F4）、
  点选查询（F5）、服务覆盖区（F6）、供给盲区高亮（F7）、供需统计面板（F8）、
  数据来源说明（F9）、数据未就绪自检门控（F11）。
- 后端（FastAPI）：5 个空间分析接口（F10）+ 数据自检/边界元接口；
  默认**文件后端**（shapely，读本地 GeoJSON，开箱即用），可选 PostGIS 后端。
- 一键启动 `npm start`、`docker-compose` 部署（F12）。
- 开发者文档：总览 + 后端/前端逐文件说明。
