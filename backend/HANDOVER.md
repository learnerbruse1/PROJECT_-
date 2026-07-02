# 后端交接文档（⚠️ 已过时）

> **本文件基于 v1.0.0（PostGIS-only 模式）编写，已严重过时。**
> 
> 当前系统默认使用**文件后端**（`geojson_store.py`），无需 PostgreSQL/PostGIS 即可运行。
> 请参阅以下最新文档：
> - [docs/backend-交接文档.md](../docs/backend-交接文档.md) — 当前后端交接文档（双后端模式 + 全部 11 个接口）
> - [docs/后端文件说明.md](../docs/后端文件说明.md) — 逐文件详解
> - [docs/api/接口契约.md](../docs/api/接口契约.md) — API 接口契约
> - [docs/开发者文档.md](../docs/开发者文档.md) — 架构总览
>
> 以下内容保留仅供历史参考。

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
| shapely | 2.x | 默认文件后端的空间计算 |
| numpy | 1.x | 人口点数组常驻 + 向量化计算 |
| asyncpg | 0.29.0 | 异步 PostgreSQL 驱动（PostGIS 后端） |
| PostgreSQL | 14+ | 关系型数据库（PostGIS 后端） |
| PostGIS | 3.x | 空间扩展（PostGIS 后端必须启用） |

---

## 二、项目结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 应用入口，lifespan 管理数据预载/连接池
│   ├── db/
│   │   ├── __init__.py
│   │   ├── provider.py       # 按 DATA_BACKEND 选择数据后端，对路由透明
│   │   ├── geojson_store.py  # 默认后端：shapely 读本地 GeoJSON 做全部空间计算
│   │   └── postgis.py        # 可选后端：连接池 + PostGIS 空间查询函数
│   └── routers/
│       ├── __init__.py
│       ├── statistics.py     # 六个分析 API 路由
│       └── meta.py           # 数据自检 + 边界元数据接口
├── sql/
│   └── schema.sql            # PostGIS 建表 + 索引 DDL（仅 PostGIS 路径）
├── Dockerfile
└── requirements.txt
```

---

## 三、数据后端

系统支持两种数据后端，由环境变量 `DATA_BACKEND` 选择：

### 3.1 文件后端（默认，`DATA_BACKEND=geojson`）

- 实现：`app/db/geojson_store.py`
- 启动时从 `DATA_DIR`（默认 `data/processed/`）读取本地 GeoJSON 文件
- 人口数据以 numpy 数组常驻内存，设施以 list[dict] 常驻
- 使用 shapely 完成全部空间计算：局部等距投影做米制缓冲、STRtree 做空间索引
- **无需数据库，开箱即用**

### 3.2 PostGIS 后端（`DATA_BACKEND=postgis`）

- 实现：`app/db/postgis.py`
- 使用 asyncpg 连接 PostgreSQL + PostGIS
- 全局单例连接池（`asyncio.Lock` + double-checked locking，`min_size=2 / max_size=10`）
- 所有查询用 `ST_MakeEnvelope` 做 bbox 预过滤（命中 GIST 索引）

---

## 四、数据库（PostGIS 路径）

### 连接配置

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/gisdb
```

### 数据表

**population_grid** — 人口密度格网点

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | SERIAL PK | 自增主键 |
| geom | GEOMETRY(Point, 4326) | WGS84 坐标点 |
| value | FLOAT | 人口密度（人/km²） |
| dataset | VARCHAR(20) | 数据集：worldpop 或 ghsl |

**facilities** — 公共设施

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | VARCHAR(50) PK | OSM node id |
| name | VARCHAR(255) | 设施名称 |
| type | VARCHAR(20) | school / hospital / park |
| geom | GEOMETRY(Point, 4326) | WGS84 坐标点 |

### 索引策略

两张表均有 GIST 空间索引；按 `dataset` / `type` 建了局部 GIST 索引。

---

## 五、API 接口一览

Base URL：`http://localhost:8000/api/v1`

| 方法 | 路径 | 功能 |
| --- | --- | --- |
| GET | /population/heatmap | 人口密度热力点，支持 WorldPop / GHSL |
| GET | /population/at-point | 人口密度点查询（F13），返回指定坐标所属网格的密度值 |
| GET | /facilities | 公共设施分页列表，可按类型过滤 |
| GET | /analysis/supply-demand | 覆盖率 + 千人设施量统计 |
| GET | /analysis/blind-spots | 供给盲区识别，返回 GeoJSON FeatureCollection |
| GET | /analysis/coverage | 设施缓冲覆盖区合并，返回 GeoJSON Geometry |
| GET | /analysis/coverage-all | 三类设施合并覆盖区（全类型） |
| GET | /analysis/blind-spots-all | 三类设施合并盲区（全类型） |
| GET | /analysis/supply-demand-all | 三类设施合并供需统计（全类型） |
| GET | /meta/status | 数据状态自检（F11） |
| GET | /meta/boundary | 研究区边界 GeoJSON |
| GET | / | 健康检查 |

**公共参数**

- `bbox`：`minLng,minLat,maxLng,maxLat`（WGS84，逗号分隔）
- `facility_type`：`school` / `hospital` / `park`
- `buffer_radius`（可选）：缓冲半径（米），默认 school=1000，hospital=2000，park=500
- `dataset`（可选）：`worldpop`（默认） / `ghsl`

---

## 六、核心实现说明

### 连接池（PostGIS 路径）

`app/db/postgis.py` 使用全局单例池，通过 `asyncio.Lock` + double-checked locking 保证并发安全，`min_size=2 / max_size=10`，在 FastAPI `lifespan` 关闭时释放。

### 文件后端空间查询

- **缓冲服务区**：局部等距投影（`_LNG0/_LAT0`）→ shapely `buffer(radius)` → 回转为经纬度
- **覆盖合并**：`unary_union` 消除重叠
- **盲区识别**：STRtree 批量 `query(covered_union, 'within')` → 取反 → 网格聚类 → 凸包
- **人口密度点查询**：STRtree 空间索引 `query(point, 'intersects')` 定位所在网格

### PostGIS 空间查询模式

- **缓冲服务区**：`ST_Buffer(geom::geography, radius)::geometry`
- **覆盖合并**：`ST_Union(buf)`
- **盲区识别**：`NOT ST_Within(pop_point, covered_area)` + `COALESCE` 处理 NULL
- **盲区聚合**：`ST_ConvexHull(ST_Collect(geom))`

### 性能优化

- 人口点以 numpy 数组常驻，bbox 过滤用掩码运算；STRtree 批量查询替代逐点循环
- 供需/盲区/覆盖结果加 LRU 缓存，`asyncio.to_thread` 下放线程
- GZip 压缩响应（热力点 ~400KB → ~50KB）
- 前端热力点按精度取整减小体积

---

## 七、本地启动

```bash
# 1. 安装依赖
cd backend && pip install -r requirements.txt

# 2. 默认文件后端，直接启动（无需数据库）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 3. 若需 PostGIS 后端，先初始化数据库
# psql -U postgres -d gisdb -f sql/schema.sql
# 然后导入数据，设环境变量
# DATA_BACKEND=postgis DATABASE_URL=postgresql://postgres:postgres@localhost:5432/gisdb uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

交互式文档：`http://localhost:8000/docs`

---

## 八、已知限制与待办

| 项目 | 说明 |
| --- | --- |
| 数据导入（PostGIS） | `population_grid` 和 `facilities` 表需外部脚本从 WorldPop/OSM 导入 |
| 认证 | 当前无鉴权，仅适合内网部署 |
| dataset 参数 | 供需统计/盲区/覆盖区接口的人口统计未暴露 `dataset` 参数 |
| 盲区聚合粒度 | 当前将所有盲区点聚合为凸包，如需多个独立多边形需引入 DBSCAN 聚类 |
| PostGIS 后端 | 未实现 `query_population_at_point`（文件后端已实现） |

---

## 九、联系方式与协作

本项目为 **6 人协作项目**，分工如下：

| 角色 | 负责内容 |
| --- | --- |
| 数据组 | WorldPop 人口栅格处理 + OSM 设施数据导入 |
| 前端 A | 人口热力图层（Leaflet.heat / Canvas） |
| 前端 B | 设施叠加 + 盲区高亮 + 图层控制 |
| 后端 | 供需统计接口 + 空间查询 |
| 集成 | 前后端联调 + 部署 |
