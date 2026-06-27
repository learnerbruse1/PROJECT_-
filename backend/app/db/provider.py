"""数据后端选择器。

根据环境变量 DATA_BACKEND 决定五类空间查询的实现来源：
  - geojson（默认）：读取本地 GeoJSON 文件，开箱即用，无需数据库
  - postgis        ：使用 PostgreSQL + PostGIS（见 app/db/postgis.py）

元数据接口（数据自检、研究区边界）始终读取本地文件，与查询后端无关。
"""
import os

_BACKEND = os.getenv("DATA_BACKEND", "geojson").lower()

if _BACKEND == "postgis":
    from app.db.postgis import (
        close_pool,
        query_blind_spots,
        query_coverage,
        query_facilities,
        query_heatmap,
        query_supply_demand,
    )
else:
    from app.db.geojson_store import (
        close_pool,
        query_blind_spots,
        query_coverage,
        query_facilities,
        query_heatmap,
        query_supply_demand,
    )

# 元数据接口固定走文件实现（边界与数据自检都基于本地文件）
from app.db.geojson_store import data_status, get_boundary, load as load_data

BACKEND_NAME = _BACKEND

__all__ = [
    "BACKEND_NAME",
    "close_pool",
    "data_status",
    "get_boundary",
    "load_data",
    "query_blind_spots",
    "query_coverage",
    "query_facilities",
    "query_heatmap",
    "query_supply_demand",
]
