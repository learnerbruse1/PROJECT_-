# 洪山区人口分布热力与公共设施叠加分析系统

> 选题 T8：「人口分布热力与公共设施叠加」。以**武汉市洪山区**为研究区，叠合人口栅格与公共设施（学校 / 医院 / 公园），用热力图与图层叠加呈现“人在何处、设施是否充足”，并识别**供给盲区**。

![默认视图](docs/images/screenshot.png)

---

## 项目概览

这是一个 **前后端分离** 的 GIS 可视化项目：

- **前端**：Vue 3 + Vite + Leaflet + leaflet.heat
- **后端**：FastAPI + Uvicorn
- **数据**：WorldPop 2020 人口栅格、OpenStreetMap 设施点、洪山区边界
- **坐标系**：全链路使用 WGS84 / EPSG:4326，经度在前 `[lng, lat]`

前端负责地图交互、图层切换、热力渲染和结果面板；后端负责空间查询、缓冲覆盖、盲区识别和统计接口。

---

## 功能

| 编号 | 功能 | 说明 |
| --- | --- | --- |
| F1 | 底图加载与地图浏览 | 天地图（矢量/影像）+ OSM/高德备用底图，自动定位洪山区并绘制边界 |
| F2 | 人口分布可视化 | WorldPop 2020 栅格 → 约 100m 网格 → 格心点，Leaflet.heat 热力渲染 |
| F3 | 公共设施图层叠加 | 学校 / 医院 / 公园分色点位叠加 |
| F4 | 设施分类筛选 | 图层面板按类型独立开关 |
| F5 | 点选查询 | 点击设施 / 盲区，在右侧面板查看属性 |
| F6 | 设施服务范围展示 | 按类型默认半径（学校 1000m / 医院 2000m / 公园 500m）的缓冲服务区，可调 |
| F7 | 供给盲区识别 | 高人口密度且未被服务区覆盖的区域高亮展示 |
| F8 | 供需指标面板 | 三类设施的覆盖率、覆盖/未覆盖人口、千人设施量对比 |
| F9 | 数据来源与说明 | 右侧面板展示数据源、坐标系与处理流程 |
| F10 | 后端统计接口 | FastAPI 提供空间分析接口 |
| F11 | 数据状态自检 | 启动时检测本地数据是否齐全，避免空白页 |
| F12 | 云端部署 | `docker compose` 一键起前后端 |

---

## 目录结构

```text
V1/
├── backend/        # FastAPI 后端、数据后端实现、空间分析路由
├── frontend/       # Vue 3 + Leaflet 前端
├── data/           # 处理后的 GeoJSON 数据与说明
├── docs/           # 开发者文档、接口说明、需求文档
├── scripts/        # 数据处理与启动脚本
├── docker-compose.yml
└── package.json    # 根目录一键启动脚本
```

---

## 常用命令

### 一键启动（推荐）

在**项目根目录**执行：

```bash
npm start
```

首次运行前先安装依赖（以管理员身份运行）：

```bash
npm run setup
```

`npm run setup` 等价于：

```bash
pip install -r backend/requirements.txt && npm --prefix frontend install
```

启动后访问：

- 前端：<http://localhost:5173>
- 后端文档：<http://localhost:8000/docs>

### 单独启动前后端

仅后端：

```bash
npm run backend
```

仅前端：

```bash
npm run frontend
```

### 构建

只构建前端生产产物：

```bash
npm run build
```

### Docker 部署

```bash
docker compose up --build
```

- 前端：<http://localhost:8080>
- 后端文档：<http://localhost:8000/docs>

### 目前没有单独的测试脚本

这个仓库当前没有独立的 `test` 命令；如果你要快速验证改动，通常用下面两步：

1. `npm run build`
2. 启动后端并在前端页面手动检查地图、图层和接口表现

---

## 后端 API

Base URL：`/api/v1`

| 方法 | 路径 | 功能 |
| --- | --- | --- |
| GET | `/population/heatmap` | 人口密度热力点（`bbox`,`zoom`,`dataset`） |
| GET | `/facilities` | 设施分页列表（`bbox`,`facility_type`,`page`,`page_size`） |
| GET | `/analysis/supply-demand` | 覆盖率 + 千人设施量 |
| GET | `/analysis/blind-spots` | 供给盲区 GeoJSON |
| GET | `/analysis/coverage` | 设施缓冲覆盖区 GeoJSON |
| GET | `/meta/status` | 数据状态自检 |
| GET | `/meta/boundary` | 研究区边界 GeoJSON |

公共参数：`bbox=minLng,minLat,maxLng,maxLat`；`facility_type=school|hospital|park`；`buffer_radius`（米，可选）。

---

## 本地开发配置

### 前端环境变量

`frontend/.env.example` 提供模板，常用变量如下：

- `VITE_TIANDITU_KEY`：天地图密钥（可选，不填时会回退到 OSM / 高德）
- `VITE_BACKEND_ORIGIN`：远程后端地址（默认本地开发走 Vite 代理）

### 后端环境变量

- `DATA_BACKEND=geojson`：默认文件模式，直接读取 `data/processed/`
- `DATA_BACKEND=postgis`：切换到 PostgreSQL + PostGIS
- `CORS_ORIGINS`：允许的前端来源，默认 `*`
- `PYTHON`：`scripts/start.mjs` 使用的 Python 解释器名
- `BACKEND_PORT` / `FRONTEND_PORT`：一键启动脚本使用的端口

---

## 数据与实现说明

- **人口**：WorldPop 2020（`chn_ppp_1km`，UN 调整）裁剪至洪山区，重采样为约 100m 网格，取格心点后渲染热力图。
- **设施**：OpenStreetMap 点位，学校类合并 `school/kindergarten/college/university`，医疗类合并 `hospital/clinic/doctors`，另有 `park`。
- **缓冲与盲区**：文件后端使用局部等距投影做米制缓冲、并集和点面判断；盲区先做网格聚类，再高亮多块区域。
- **地图交互**：地图视野变化会同步 bbox / zoom，并驱动人口热力、覆盖区、盲区等图层重新请求。

---

## 参考文档

更详细的说明请看：

- [docs/开发者文档.md](docs/开发者文档.md) —— 架构、请求链路、文件索引
- [docs/后端文件说明.md](docs/后端文件说明.md) —— 后端逐文件说明
- [docs/前端文件说明.md](docs/前端文件说明.md) —— 前端逐文件说明
- [docs/api/接口契约.md](docs/api/接口契约.md) —— 接口字段与契约
- [docs/backend-交接文档.md](docs/backend-交接文档.md) —— 后端交接说明

---

## 许可

代码采用 [MIT License](LICENSE) 开源；第三方数据各自遵循其原始许可（WorldPop CC BY 4.0、OSM ODbL、天地图服务条款）。
