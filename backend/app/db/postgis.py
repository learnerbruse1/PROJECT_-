"""PostGIS 连接池与所有空间查询函数"""
import asyncio
import json
import os
from typing import Optional

import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/gisdb")

_pool: Optional[asyncpg.Pool] = None
_pool_lock = asyncio.Lock()


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        async with _pool_lock:
            if _pool is None:  # double-checked locking
                _pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


# ── 人口热力 ──────────────────────────────────────────────────────────────────

async def query_heatmap(bbox: list[float], dataset: str) -> list[dict]:
    """返回 bbox 内的人口密度点列表"""
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT ST_X(geom) AS lng, ST_Y(geom) AS lat, value
        FROM   population_grid
        WHERE  dataset = $1
          AND  geom && ST_MakeEnvelope($2, $3, $4, $5, 4326)
        LIMIT  10000
        """,
        dataset, *bbox,
    )
    return [dict(r) for r in rows]


# ── 公共设施 ──────────────────────────────────────────────────────────────────

async def query_facilities(
    bbox: list[float],
    fac_type: Optional[str],
    page: int,
    page_size: int,
) -> tuple[int, list[dict]]:
    """分页查询设施列表，可按 type 过滤；用窗口函数一次查询同时获取 total。"""
    pool = await get_pool()
    where = "WHERE geom && ST_MakeEnvelope($1,$2,$3,$4,4326)"
    args: list = list(bbox)

    if fac_type:
        where += " AND type = $5"
        args.append(fac_type)

    offset = (page - 1) * page_size
    # COUNT(*) OVER() 与数据行同时返回，避免两次独立查询
    rows = await pool.fetch(
        f"SELECT id, name, type, ST_X(geom) AS lng, ST_Y(geom) AS lat,"
        f"       COUNT(*) OVER() AS _total"
        f" FROM facilities {where}"
        f" LIMIT {page_size} OFFSET {offset}",
        *args,
    )
    total = int(rows[0]["_total"]) if rows else 0
    items = [{k: v for k, v in r.items() if k != "_total"} for r in rows]

    # 当 page > 1 且当页无数据时，仍需返回正确 total
    if not rows and page > 1:
        total = await pool.fetchval(f"SELECT COUNT(*) FROM facilities {where}", *args) or 0

    return total, items


# ── 供需统计 ──────────────────────────────────────────────────────────────────

async def query_supply_demand(bbox: list[float], fac_type: str, radius: int) -> dict:
    """
    ST_Buffer + ST_Intersects 计算服务区覆盖人口数及人均供给量。
    返回: facility_count, total, covered
    """
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        WITH envelope AS (
            SELECT ST_MakeEnvelope($1,$2,$3,$4,4326) AS geom
        ),
        facs AS (
            SELECT ST_Buffer(f.geom::geography, $5)::geometry AS buf
            FROM   facilities f, envelope e
            WHERE  f.type = $6 AND ST_Within(f.geom, e.geom)
        ),
        covered_area AS (
            SELECT ST_Union(buf) AS geom FROM facs
        )
        SELECT
            (SELECT COUNT(*) FROM facs)                          AS facility_count,
            COUNT(*)                                             AS total,
            COUNT(*) FILTER (
                WHERE ST_Within(p.geom, (SELECT geom FROM covered_area))
            )                                                    AS covered
        FROM population_grid p, envelope e
        WHERE p.geom && e.geom
        """,
        *bbox, radius, fac_type,
    )
    return dict(row) if row else {}


# ── 盲区识别 ──────────────────────────────────────────────────────────────────

async def query_blind_spots(
    bbox: list[float], fac_type: str, radius: int, pop_threshold: float
) -> list[dict]:
    """
    盲区 = 人口密度 > pop_threshold 且不在任何设施服务区内。
    当无设施时 covered_area.geom 为 NULL，COALESCE 替换为空几何确保盲区正常返回。
    """
    pool = await get_pool()
    rows = await pool.fetch(
        """
        WITH envelope AS (
            SELECT ST_MakeEnvelope($1,$2,$3,$4,4326) AS geom
        ),
        covered_area AS (
            SELECT COALESCE(
                ST_Union(ST_Buffer(f.geom::geography, $5)::geometry),
                ST_GeomFromText('GEOMETRYCOLLECTION EMPTY', 4326)
            ) AS geom
            FROM   facilities f, envelope e
            WHERE  f.type = $6 AND ST_Within(f.geom, e.geom)
        ),
        blind_pts AS (
            SELECT p.geom, p.value
            FROM   population_grid p, envelope e, covered_area ca
            WHERE  p.geom && e.geom
              AND  p.value > $7
              AND  NOT ST_Within(p.geom, ca.geom)
        )
        SELECT
            ST_AsGeoJSON(ST_ConvexHull(ST_Collect(geom))) AS geojson,
            AVG(value)                                    AS avg_density,
            COUNT(*)                                      AS pt_count
        FROM blind_pts
        HAVING COUNT(*) > 0
        """,
        *bbox, radius, fac_type, pop_threshold,
    )
    features = []
    for r in rows:
        if r["geojson"]:
            features.append({
                "type": "Feature",
                "properties": {
                    "avg_population_density": round(r["avg_density"], 1),
                    "area_km2": round(r["pt_count"] * 0.01, 2),
                },
                "geometry": json.loads(r["geojson"]),
            })
    return features


# ── 缓冲覆盖区 ────────────────────────────────────────────────────────────────

async def query_coverage(bbox: list[float], fac_type: str, radius: int) -> dict:
    """ST_Union 所有设施缓冲区，返回覆盖区 GeoJSON"""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        SELECT ST_AsGeoJSON(
            ST_Union(ST_Buffer(f.geom::geography, $5)::geometry)
        ) AS geojson
        FROM facilities f
        WHERE f.type = $6
          AND f.geom && ST_MakeEnvelope($1,$2,$3,$4,4326)
        """,
        *bbox, radius, fac_type,
    )
    return json.loads(row["geojson"]) if row and row["geojson"] else {"type": "GeometryCollection", "geometries": []}
