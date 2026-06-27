# 后端交接文档

**项目**：人口分布热力与公共设施叠加分析系统  
**后端版本**：v1.0.0  
**交接日期**：2026-06-24

---

## 一、技术栈

| 组件 | 版本 | 用途 |
| --- | --- | --- |
| Python | 3.11+ | 运行环境 |
| FastAPI | 0.115.0 | Web 框架 |
| Uvicorn | 0.30.0 | ASGI 服务器 |
| Pydantic | 2.9.0 | 参数校验 |
| asyncpg | 0.29.0 | 异步 PostgreSQL 驱动 |
| PostgreSQL | 14+ | 关系型数据库 |
| PostGIS | 3.x | 空间扩展（必须启用） |

---

## 二、项目结构

```
backend/
├── app/
│   ├── main.py              # FastAPI 应用入口，lifespan 管理连接池
│   ├── db/
│   │   └── postgis.py       # 连接池 + 所有空间查询函数
│   └── routers/
│       └── statistics.py    # 五个 API 路由
├── sql/
│   └── schema.sql           # 建表 + 索引 DDL
└── requirements.txt
```

---

## 三、数据库

### 连接配置

通过环境变量注入，本地默认值：

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/gisdb
```

### 数据表

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

### 索引策略

两张表均有 GIST 空间索引；此外按 `dataset` / `type` 建了局部 GIST 索引，针对最常见的过滤模式（如 `WHERE type = 'school' AND geom && ...`）提升查询速度。

---

## 四、API 接口一览

Base URL：`http://localhost:8000/api/v1`  
完整文档见 `API说明文档.xlsx`（位于 docs/api/）。

| 方法 | 路径 | 功能 |
| --- | --- | --- |
| GET | /population/heatmap | 人口密度热力点，支持 GHSL / WorldPop |
| GET | /facilities | 公共设施分页列表，可按类型过滤 |
| GET | /analysis/supply-demand | 覆盖率 + 千人设施量统计 |
| GET | /analysis/blind-spots | 供给盲区识别，返回 GeoJSON |
| GET | /analysis/coverage | 设施缓冲覆盖区合并，返回 GeoJSON |

**公共参数**

- `bbox`：`minLng,minLat,maxLng,maxLat`（WGS84，逗号分隔）
- `facility_type`：`school` / `hospital` / `park`
- `buffer_radius`（可选）：缓冲半径（米），默认 school=1000，hospital=2000，park=500

---

## 五、本地启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 初始化数据库（已有库则跳过）
psql -U postgres -d gisdb -f sql/schema.sql

# 3. 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

交互式文档：`http://localhost:8000/docs`

---

## 六、核心实现说明

### 连接池

`app/db/postgis.py` 使用全局单例池，通过 `asyncio.Lock` + double-checked locking 保证并发安全，`min_size=2 / max_size=10`，在 FastAPI `lifespan` 关闭时释放。

### 空间查询模式

所有查询统一用 `ST_MakeEnvelope($1,$2,$3,$4,4326)` 做 bbox 预过滤（命中 GIST 索引），再做精确空间运算：

- **缓冲服务区**：`ST_Buffer(geom::geography, radius)::geometry` — 以米为单位的地理精确缓冲
- **覆盖合并**：`ST_Union(buf)` — 消除重叠，得到真实服务区面
- **盲区识别**：`NOT ST_Within(pop_point, covered_area)` + `COALESCE` 处理无设施时 covered_area 为 NULL 的边界情况
- **盲区聚合**：`ST_ConvexHull(ST_Collect(geom))` — 将散点聚合为凸包多边形

### 分页查询优化

`/facilities` 接口使用 `COUNT(*) OVER()` 窗口函数，一次查询同时返回总数和当页数据，避免两次独立查询。

---

## 七、待办 / 已知限制

- **数据后端（已更新）**：现支持两种后端，由环境变量 `DATA_BACKEND` 选择：
  - `geojson`（**默认**）：直接读取 `data/` 目录下的本地 GeoJSON，使用 shapely 完成空间计算，**无需数据库，开箱即用**；实现见 `app/db/geojson_store.py`。
  - `postgis`：使用 PostgreSQL + PostGIS（本文档其余部分描述的路径），需先导入数据。
  数据后端的选择对前端完全透明，五个接口的请求/响应格式一致。另新增 `/meta/status`（数据自检 F11）与 `/meta/boundary`（研究区边界）两个接口。
- **数据导入（PostGIS 路径）**：`population_grid` 和 `facilities` 表仍需外部脚本从 GHSL/WorldPop/OSM 导入；文件后端则无此需求。
- **认证**：当前无鉴权，仅适合内网部署；上线前需补充 API Key 或 JWT
- **dataset 参数**：`/analysis/supply-demand`、`/blind-spots`、`/coverage` 三个接口的人口统计暂未暴露 `dataset` 参数，默认聚合所有数据集；若同时导入多套数据会重复计数，后续可扩展
- **盲区聚合粒度**：当前将所有盲区点聚合为单个凸包，如需多个独立盲区多边形需引入 DBSCAN 聚类
