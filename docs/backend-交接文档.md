# 后端交接文档

**项目**：人口分布热力与公共设施叠加分析系统  
**后端版本**：v1.5.0  
**交接日期**：2026-06-24（更新于 2026-07-01）

---

## 一、技术栈

| 组件 | 版本 | 用途 |
| --- | --- | --- |
| Python | 3.11+ | 运行环境 |
| FastAPI | 0.115.0 | Web 框架 |
| Uvicorn | 0.30.0 | ASGI 服务器 |
| Pydantic | 2.9.0 | 参数校验 |
| shapely | 2.0+ | 默认文件后端的空间运算 |
| numpy | 1.24+ | 向量化计算 |
| asyncpg | 0.29.0 | 异步 PostgreSQL 驱动（仅 PostGIS 后端需要） |
| PostgreSQL | 14+ | 关系型数据库（仅 PostGIS 后端需要） |
| PostGIS | 3.x | 空间扩展（仅 PostGIS 后端需要） |

---

## 二、项目结构

```
backend/
├── app/
│   ├── main.py              # FastAPI 应用入口，lifespan 管理连接池/数据预载
│   ├── db/
│   │   ├── provider.py       # 按 DATA_BACKEND 选择数据后端，对路由透明
│   │   ├── geojson_store.py  # 默认后端：shapely 读本地 GeoJSON 做全部空间计算
│   │   └── postgis.py        # 可选后端：连接池 + PostGIS 空间查询函数
│   └── routers/
│       ├── statistics.py     # 六个分析 API 路由
│       └── meta.py           # 数据自检 + 边界元数据接口
├── sql/
│   └── schema.sql            # PostGIS 建表 + 索引 DDL（仅 PostGIS 路径）
└── requirements.txt
```

---

## 三、数据后端（双模式）

### 默认：文件后端（geojson_store.py）

通过 `DATA_BACKEND=geojson`（默认）启用。读取 `data/processed/` 下的本地 GeoJSON，在内存中用 shapely + numpy 完成全部空间计算。**无需数据库，开箱即用。**

特点：
- 人口点以 numpy 数组常驻，bbox 过滤为向量化掩码运算
- 覆盖判定用 STRtree 一次性批量查询（避免逐点 contains 循环）
- 供需/盲区/覆盖结果带 LRU 缓存，通过 `asyncio.to_thread` 下放线程
- 盲区识别使用网格连通域聚类（`_cluster_blind_points`），可拆分多个独立盲区
- 通过环境变量 `DATA_DIR` 可自定义数据目录

### 可选：PostGIS 后端（postgis.py）

通过 `DATA_BACKEND=postgis` 启用。连接配置通过环境变量 `DATABASE_URL` 注入：

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/gisdb
```

需先建表（`sql/schema.sql`）并导入数据。

**population_grid** — 人口密度格网点（从 GHSL / WorldPop 导入）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | SERIAL PK | 自增主键 |
| geom | GEOMETRY(Point, 4326) | WGS84 坐标点 |
| value | FLOAT | 人口密度（人/km²） |
| dataset | VARCHAR(20) | 数据集：ghsl 或 worldpop |

**facilities** — 公共设施（从 OSM 导入）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | VARCHAR(50) PK | OSM node id |
| name | VARCHAR(255) | 设施名称 |
| type | VARCHAR(20) | school / hospital / park |
| geom | GEOMETRY(Point, 4326) | WGS84 坐标点 |

### 索引策略（PostGIS 路径）

两张表均有 GIST 空间索引；此外按 `dataset` / `type` 建了局部 GIST 索引，针对最常见的过滤模式（如 `WHERE type = 'school' AND geom && ...`）提升查询速度。

---

## 四、API 接口一览

Base URL：`http://localhost:8000/api/v1`  
完整文档见 `docs/api/接口契约.md` 和 Swagger UI (`/docs`)。

| 方法 | 路径 | 功能 |
| --- | --- | --- |
| GET | /population/heatmap | 人口密度热力点，支持 WorldPop / GHSL |
| GET | /population/at-point | 人口密度点查询（F13），返回指定坐标所属网格的人口密度 |
| GET | /facilities | 公共设施分页列表，可按类型过滤 |
| GET | /analysis/supply-demand | 覆盖率 + 千人设施量统计 |
| GET | /analysis/blind-spots | 供给盲区识别，返回 GeoJSON |
| GET | /analysis/coverage | 设施缓冲覆盖区合并，返回 GeoJSON |
| GET | /analysis/coverage-all | 三类设施合并覆盖区（全类型） |
| GET | /analysis/blind-spots-all | 三类设施合并盲区（全类型） |
| GET | /analysis/supply-demand-all | 三类设施合并供需统计（全类型） |

**公共参数**

- `bbox`：`minLng,minLat,maxLng,maxLat`（WGS84，逗号分隔）
- `facility_type`：`school` / `hospital` / `park`
- `buffer_radius`（可选）：缓冲半径（米），默认 school=1000，hospital=2000，park=500
- `pop_threshold`（可选，盲区接口）：人口密度阈值（人/km²），单类型默认 1000，全类型默认 3000
- `all` 接口额外支持 `school_radius / hospital_radius / park_radius` 分别控制三类设施半径

---

## 五、本地启动

```bash
# 默认模式（文件后端，无需数据库）
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# PostGIS 模式
DATA_BACKEND=postgis DATABASE_URL=postgresql://postgres:postgres@localhost:5432/gisdb uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

交互式文档：`http://localhost:8000/docs`

---

## 六、核心实现说明

### 文件后端（geojson_store.py，默认）

- **数据加载**：`load()` 在 FastAPI `lifespan` 启动时调用，将人口栅格（numpy 数组）和设施（Python list）常驻内存
- **向量化 bbox 过滤**：`_pop_in_bbox` 使用 numpy 布尔掩码一次筛选，O(N) → 向量化 O(1)
- **STRtree 批量覆盖判定**：`_covered_mask` 将全部人口点一次性通过 Shapely STRtree 查询，避免逐点 `contains` 循环（单次供需统计 ~0.02s）
- **LRU 缓存**：供需/盲区/覆盖三个同步函数带 `@lru_cache(maxsize=128~256)`，重复请求零延迟
- **盲区聚类**：`_cluster_blind_points` 基于网格的连通域聚类（BFS 8 邻域），将散点拆分为多个独立盲区（替代单一凸包）
- **线程池下放**：所有查询通过 `asyncio.to_thread` 在后台线程执行，不阻塞 FastAPI 事件循环
- **GZip 压缩**：`main.py` 启用 GZipMiddleware，热力点响应 ~400KB → ~50KB

### PostGIS 后端（postgis.py，可选）

`DATA_BACKEND=postgis` 时启用。

- **连接池**：全局单例 `asyncpg.Pool`，`asyncio.Lock` + double-checked locking，`min_size=2/max_size=10`
- **空间查询**：`ST_MakeEnvelope` bbox 预过滤（GIST 索引）→ `ST_Buffer(::geography)` / `ST_Union` / `ST_Within` / `ST_ConvexHull`
- **分页优化**：`COUNT(*) OVER()` 窗口函数一次查询同时返回总数和当页数据

---

## 七、待办 / 已知限制

- **数据后端（已更新）**：现支持两种后端，由环境变量 `DATA_BACKEND` 选择：
  - `geojson`（**默认**）：直接读取 `data/` 目录下的本地 GeoJSON，使用 shapely 完成空间计算，**无需数据库，开箱即用**；实现见 `app/db/geojson_store.py`。
  - `postgis`：使用 PostgreSQL + PostGIS（本文档其余部分描述的路径），需先导入数据。
  数据后端的选择对前端完全透明，各接口的请求/响应格式一致。另新增 `/meta/status`（数据自检 F11）与 `/meta/boundary`（研究区边界）两个接口。
- **数据导入（PostGIS 路径）**：`population_grid` 和 `facilities` 表仍需外部脚本从 GHSL/WorldPop/OSM 导入；文件后端则无此需求。
- **认证**：当前无鉴权，仅适合内网部署；上线前需补充 API Key 或 JWT
- **dataset 参数**：`/analysis/supply-demand`、`/blind-spots`、`/coverage` 三个接口的人口统计暂未暴露 `dataset` 参数，默认聚合所有数据集；若同时导入多套数据会重复计数，后续可扩展
- **盲区聚合粒度**：当前将所有盲区点聚合为单个凸包，如需多个独立盲区多边形需引入 DBSCAN 聚类
