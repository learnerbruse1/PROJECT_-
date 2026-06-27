# 洪山区人口分布热力与公共设施叠加分析系统

> 选题 T8 ——「人口分布热力与公共设施叠加」。以**武汉市洪山区**为研究区，叠合人口栅格与公共设施（学校 / 医院 / 公园），用热力图与图层叠加呈现「人在何处、设施是否充足」，并识别**供给盲区**。

![默认视图](docs/images/screenshot.png)

---

## 📚 开发者文档

接手 / 协作开发请先看 `docs/`：

- [docs/开发者文档.md](docs/开发者文档.md) —— 架构、请求链路、**全量文件清单**（每个文件一句话）、分工与任务索引
- [docs/后端文件说明.md](docs/后端文件说明.md) —— 后端逐文件详解（函数签名、调用方式、扩展点）
- [docs/前端文件说明.md](docs/前端文件说明.md) —— 前端逐文件详解（组件职责、store API、数据流）
- [docs/api/接口契约.md](docs/api/接口契约.md) —— 后端接口契约（请求/响应字段）

---

## 一、功能实现

| 编号 | 功能 | 实现 |
| --- | --- | --- |
| F1 | 底图加载与地图浏览 | 天地图（矢量/影像）+ OSM/高德备用底图，自动定位洪山区并绘制边界 |
| F2 | 人口分布可视化 | WorldPop 2020 栅格 → 约 100m 网格 → 格心点，Leaflet.heat 热力渲染（均匀抽样，最多 1 万点） |
| F3 | 公共设施图层叠加 | 学校 / 医院 / 公园分色点位叠加 |
| F4 | 设施分类筛选 | 图层面板按类型独立开关 |
| F5 | 点选查询 | 点击设施 / 盲区，右侧面板展示名称、类型、来源、坐标等属性 |
| F6 | 设施服务范围展示 | 按类型默认半径（学校 1000m / 医院 2000m / 公园 500m）的缓冲服务区，可调 |
| F7 | 供给盲区识别 | 高人口密度且未被服务区覆盖的区域，网格聚类后高亮多个独立盲区 |
| F8 | 供需指标面板 | 三类设施的覆盖率、覆盖/未覆盖人口、千人设施量对比 |
| F9 | 数据来源与说明 | 右侧面板展示数据源、时间、字段、坐标系与处理流程 |
| F10 | 后端统计接口 | FastAPI 提供 5 个空间分析接口（见下） |
| F11 | 数据状态自检 | 启动调用 `/meta/status`，缺文件时显示「数据未就绪」而非空白页 |
| F12 | 云端部署 | `docker-compose` 一键起 后端 + 前端（见「四」） |

---

## 二、架构与技术栈

```
┌────────────────────────┐        /api/v1 (GET)        ┌──────────────────────────┐
│  前端 Vue3 + Leaflet    │  ───────────────────────▶  │  后端 FastAPI            │
│  · 天地图底图           │                             │  · 文件后端（默认，shapely）│
│  · 热力 / 设施 / 盲区    │  ◀───────────────────────  │  · 或 PostGIS 后端        │
│  · 供需统计面板         │        JSON / GeoJSON       │                          │
└────────────────────────┘                             └────────────┬─────────────┘
                                                          │ 读取
                                                          ┌──────────▼───────────┐
                                                          │ data/processed/ GeoJSON│
                                                          │ · 人口栅格网格        │
                                                          │ · 学校医院 / 公园绿地  │
                                                          │ · 洪山区边界          │
                                                          └──────────────────────┘
```

| 层 | 技术 |
| --- | --- |
| 前端 | Vue 3 + Vite + Leaflet 1.9 + leaflet.heat |
| 后端 | Python 3.11+ / FastAPI / Uvicorn；**文件后端用 shapely**，可选 PostGIS（asyncpg） |
| 坐标系 | WGS84 (EPSG:4326)，全链路经度在前 |
| 数据 | WorldPop 2020（人口）+ OpenStreetMap（设施），均裁取至洪山区存本地 |

> **两种数据后端**：默认 `DATA_BACKEND=geojson`，直接读 `data/processed/` 目录，**无需数据库，开箱即用**；
> 设 `DATA_BACKEND=postgis` 则改用 PostgreSQL + PostGIS（见 `backend/sql/schema.sql`、`docs/backend-交接文档.md`）。

---

## 三、本地运行

### 0. 一键启动（推荐）

在**项目根目录**执行，前后端会一起启动，`Ctrl + C` 一并退出：

```bash
npm start
```

> 首次运行前需安装依赖（仅一次）：`npm run setup`
> 它等价于 `pip install -r backend/requirements.txt && npm --prefix frontend install`。

启动后访问 **前端 <http://localhost:5173>**，后端文档 <http://localhost:8000/docs>。

根目录其他脚本：

| 命令 | 作用 |
| --- | --- |
| `npm start` / `npm run dev` | 同时启动前端 + 后端 |
| `npm run backend` | 仅启动后端（uvicorn :8000） |
| `npm run frontend` | 仅启动前端（vite :5173） |
| `npm run build` | 构建前端生产产物 |
| `npm run setup` | 安装前后端依赖 |

> 可用环境变量 `PYTHON`（python 解释器名）、`BACKEND_PORT`、`FRONTEND_PORT` 覆盖默认值。

### 1. 后端（默认文件模式，无需数据库）

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动后访问 <http://localhost:8000/docs> 在线调试。数据自检：<http://localhost:8000/api/v1/meta/status>。

### 2. 前端

```bash
cd frontend
npm install
cp .env.example .env   # 可选：填入天地图密钥（不填则自动用 OSM/高德底图）
npm run dev            # 或 npm start，均为 http://localhost:5173
```

前端 `npm run dev` 通过 Vite 代理把 `/api` 转发到 `http://127.0.0.1:8000`，无跨域问题。
天地图密钥配置在 `frontend/.env`（`VITE_TIANDITU_KEY`，模板见 `frontend/.env.example`）。

> 若仅有前端需指向远程后端：在 `frontend/.env` 设 `VITE_BACKEND_ORIGIN=http://你的后端:8000`。

---

## 四、Docker 一键部署（F12）

```bash
docker compose up --build
# 前端 http://localhost:8080   后端 http://localhost:8000/docs
```

`docker-compose.yml` 启动两个服务：后端（文件模式，只读挂载 `./data/processed`）与前端（Nginx 托管构建产物并反代 `/api` 到后端）。

---

## 五、后端 API 一览

Base URL：`/api/v1`

| 方法 | 路径 | 功能 |
| --- | --- | --- |
| GET | `/population/heatmap` | 人口密度热力点（`bbox`,`zoom`,`dataset`） |
| GET | `/facilities` | 设施分页列表（`bbox`,`facility_type`,`page`,`page_size`） |
| GET | `/analysis/supply-demand` | 覆盖率 + 千人设施量 |
| GET | `/analysis/blind-spots` | 供给盲区 GeoJSON（聚类多盲区） |
| GET | `/analysis/coverage` | 设施缓冲覆盖区 GeoJSON |
| GET | `/meta/status` | 数据状态自检（F11） |
| GET | `/meta/boundary` | 研究区边界 GeoJSON |

公共参数：`bbox=minLng,minLat,maxLng,maxLat`；`facility_type=school|hospital|park`；`buffer_radius`（米，可选）。
完整字段说明见 `docs/api/接口契约.md`。

---

## 六、目录结构

```
PROJECT2/
├── README.md / CONTRIBUTING.md / CHANGELOG.md / LICENSE
├── package.json              根脚本：npm start 一键启动前后端
├── docker-compose.yml        后端 + 前端容器编排（F12）
├── .editorconfig / .nvmrc / .gitignore
├── .github/workflows/ci.yml  CI：前端构建 + 后端导入自检
├── scripts/
│   ├── start.mjs             前后端并行启动器（纯 Node，无依赖）
│   ├── 栅格重采样.py          WorldPop 栅格 → GeoJSON 转换脚本
│   └── requirements.txt      数据处理脚本依赖
├── data/
│   ├── README.md             数据说明与再生方式
│   ├── raw/                  源数据（栅格 / Shapefile，.gitignore 排除）
│   └── processed/            成果 GeoJSON（系统直接读取，已跟踪）
│       ├── hongshan_population.geojson   人口网格
│       ├── 学校医院.geojson / 公园绿地.geojson
│       └── 洪山区_边界.geojson
├── docs/
│   ├── 开发者文档.md          总览 + 全量文件清单
│   ├── 后端文件说明.md / 前端文件说明.md
│   ├── backend-交接文档.md
│   ├── api/                  接口契约.md + API 说明 xlsx
│   ├── requirements/         需求与框架文档
│   └── images/screenshot.png
├── backend/
│   ├── app/
│   │   ├── main.py           应用入口（CORS + lifespan + 路由）
│   │   ├── db/{geojson_store,postgis,provider}.py   后端实现 + 选择器
│   │   └── routers/{statistics,meta}.py             5 接口 + 元数据
│   ├── sql/schema.sql        PostGIS 建表（可选路径）
│   ├── Dockerfile / requirements.txt
└── frontend/
    ├── index.html / vite.config.js / package.json / .env.example
    ├── Dockerfile / nginx.conf
    └── src/
        ├── main.js / App.vue / api.js / leafletSetup.js
        ├── stores/mapStore.js       图层状态、选中要素、统计
        ├── utils/geoUtils.js        类型元数据、配色、bbox 工具
        ├── styles/main.css
        └── components/
            ├── MapContainer.vue     底图与边界
            ├── HeatmapLayer.vue     人口热力
            ├── FacilityLayer.vue    设施点 + 点选
            ├── CoverageLayer.vue    服务覆盖区
            ├── BlindZoneLayer.vue   盲区高亮
            ├── LayerControl.vue     图层与分析参数面板
            ├── StatsPanel.vue       供需统计
            ├── InfoPanel.vue        属性 / 数据说明
            └── Legend.vue           图例
```

---

## 七、数据与方法说明

- **人口**：WorldPop 2020（`chn_ppp_1km`，UN 调整）裁剪至洪山区，重采样为约 100m 网格，取格心点，`pop_count` 为人口密度（人/km²）。
- **设施**：OSM 点位。学校类合并 `school/kindergarten/college/university`，医疗类合并 `hospital/clinic/doctors`，另有 `park`。
- **缓冲与盲区**：文件后端以洪山区中心做局部等距投影，在米制下做缓冲、并集、点面判断；盲区先按 ~1km 网格连通域聚类拆分，再取凸包并扣除已覆盖区域。
- **坐标系**：全链路 WGS84，接口坐标一律 `[lng, lat]`。

## 八、已知限制

- 数据集仅含 WorldPop；`dataset=ghsl` 兼容接受但返回同一套数据。
- 供需覆盖率默认对「当前地图视野」统计，缩放/平移后自动刷新。
- 盲区凸包为区域近似，非逐格精确边界。

## 九、贡献与许可

- 贡献流程、代码规范见 [CONTRIBUTING.md](CONTRIBUTING.md)；版本变更见 [CHANGELOG.md](CHANGELOG.md)。
- 代码以 [MIT License](LICENSE) 开源；第三方数据各自遵循其原始许可（WorldPop CC BY 4.0、OSM ODbL、天地图服务条款）。
