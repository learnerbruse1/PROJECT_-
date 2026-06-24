"""PostGIS 连接池与所有空间查询函数"""
import json
import os
from typing import Optional

import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/gisdb")

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
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
    """分页查询设施列表，可按 type 过滤"""
    pool = await get_pool()
    base = "FROM facilities WHERE geom && ST_MakeEnvelope($1,$2,$3,$4,4326)"
    args: list = list(bbox)

    if fac_type:
        base += " AND type = $5"
        args.append(fac_type)
        offset_idx, limit_idx = "$6", "$7"
    else:
        offset_idx, limit_idx = "$5", "$6"

    total = await pool.fetchval(f"SELECT COUNT(*) {base}", *args)
    args += [page_size, (page - 1) * page_size]
    rows = await pool.fetch(
        f"SELECT id, name, type, ST_X(geom) AS lng, ST_Y(geom) AS lat {base} "
        f"LIMIT {limit_idx} OFFSET {offset_idx}",
        *args,
    )
    return int(total), [dict(r) for r in rows]


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
        covered_area AS (
            SELECT ST_Union(ST_Buffer(f.geom::geography, $5)::geometry) AS geom
            FROM   facilities f, envelope e
            WHERE  f.type = $6 AND ST_Within(f.geom, e.geom)
        )
        SELECT
            (SELECT COUNT(*) FROM facilities f, envelope e
             WHERE  f.type = $6 AND ST_Within(f.geom, e.geom))  AS facility_count,
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
    PostGIS: ST_Difference(高密度聚合区, 设施缓冲 union)
    """
    pool = await get_pool()
    rows = await pool.fetch(
        """
        WITH envelope AS (
            SELECT ST_MakeEnvelope($1,$2,$3,$4,4326) AS geom
        ),
        covered_area AS (
            SELECT ST_Union(ST_Buffer(f.geom::geography, $5)::geometry) AS geom
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
    return json.loads(row["geojson"]) if row and row["geojson"] else {"type": "MultiPolygon", "coordinates": []}
