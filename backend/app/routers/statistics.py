"""供需统计接口 — 涵盖人口热力、设施查询、空间分析五个路由"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.db.provider import (
    query_blind_spots,
    query_blind_spots_all,
    query_coverage,
    query_coverage_all,
    query_facilities,
    query_heatmap,
    query_population_at_point,
    query_supply_demand,
    query_supply_demand_all,
)

router = APIRouter()

DEFAULT_RADIUS = {"school": 1000, "hospital": 2000, "park": 500}
VALID_TYPES = set(DEFAULT_RADIUS)


def _parse_bbox(bbox: str) -> list[float]:
    try:
        parts = [float(x) for x in bbox.split(",")]
    except ValueError:
        raise HTTPException(400, "bbox 格式错误，应为 minLng,minLat,maxLng,maxLat")
    if len(parts) != 4:
        raise HTTPException(400, "bbox 格式错误，应为 minLng,minLat,maxLng,maxLat")
    return parts


def _check_type(fac_type: str):
    if fac_type not in VALID_TYPES:
        raise HTTPException(400, f"facility_type 只允许：{VALID_TYPES}")


def _resolve_all_radii(
    school_radius: Optional[int],
    hospital_radius: Optional[int],
    park_radius: Optional[int],
) -> dict[str, int]:
    return {
        "school": school_radius or DEFAULT_RADIUS["school"],
        "hospital": hospital_radius or DEFAULT_RADIUS["hospital"],
        "park": park_radius or DEFAULT_RADIUS["park"],
    }


# ── ① 人口热力 ────────────────────────────────────────────────────────────────

@router.get("/population/heatmap", summary="人口密度热力数据")
async def population_heatmap(
    bbox: str = Query(..., description="minLng,minLat,maxLng,maxLat"),
    zoom: int = Query(..., ge=1, le=18),
    dataset: str = Query("ghsl", description="ghsl 或 worldpop"),
):
    bbox_coords = _parse_bbox(bbox)
    points = await query_heatmap(bbox_coords, dataset)
    return {
        "code": 200,
        "data": {
            "dataset": dataset,
            "bbox": bbox_coords,
            "resolution": max(10, 1000 // zoom),
            "points": points,
        },
    }


# ── 人口密度点查询（F13）───────────────────────────────────────────────────────

@router.get("/population/at-point", summary="查询指定坐标的人口密度")
async def population_at_point(
    lng: float = Query(..., ge=113.5, le=115.1, description="经度"),
    lat: float = Query(..., ge=29.9, le=31.4, description="纬度"),
):
    result = await query_population_at_point(lng, lat)
    if result is None:
        return {
            "code": 200,
            "data": {"lng": lng, "lat": lat, "pop_density": 0, "note": "该点不在人口栅格覆盖范围内"},
        }
    return {"code": 200, "data": result}


# ── ② 公共设施列表 ────────────────────────────────────────────────────────────

@router.get("/facilities", summary="公共设施列表")
async def facilities(
    bbox: str = Query(...),
    facility_type: Optional[str] = Query(None, description="school / hospital / park"),
    page: int = Query(1, ge=1),
    page_size: int = Query(500, ge=1, le=2000),
):
    if facility_type:
        _check_type(facility_type)
    bbox_coords = _parse_bbox(bbox)
    total, items = await query_facilities(bbox_coords, facility_type, page, page_size)
    return {
        "code": 200,
        "data": {"total": total, "page": page, "page_size": page_size, "facilities": items},
    }


# ── ③ 供需统计 ────────────────────────────────────────────────────────────────

@router.get("/analysis/supply-demand", summary="供需统计（覆盖率 + 人均供给）")
async def supply_demand(
    bbox: str = Query(...),
    facility_type: str = Query(..., description="school / hospital / park"),
    buffer_radius: Optional[int] = Query(None, description="缓冲半径（米），不传使用默认值"),
):
    _check_type(facility_type)
    bbox_coords = _parse_bbox(bbox)
    radius = buffer_radius or DEFAULT_RADIUS[facility_type]
    row = await query_supply_demand(bbox_coords, facility_type, radius)
    total = row.get("total", 0) or 1  # 防零除
    covered = row.get("covered", 0)
    facility_count = row.get("facility_count", 0)
    return {
        "code": 200,
        "data": {
            "facility_type": facility_type,
            "buffer_radius": radius,
            "total_population": row.get("total", 0),
            "covered_population": covered,
            "coverage_rate": round(covered / total, 3),
            "facility_count": facility_count,
            "per_capita": round(facility_count / (total / 1000), 3) if total else 0,
            "per_capita_unit": "facility per 1000 persons",
        },
    }


# ── ④ 盲区识别 ────────────────────────────────────────────────────────────────

@router.get("/analysis/blind-spots", summary="识别供给盲区（GeoJSON）")
async def blind_spots(
    bbox: str = Query(...),
    facility_type: str = Query(...),
    buffer_radius: Optional[int] = Query(None),
    pop_threshold: float = Query(1000.0, description="人口密度阈值（人/km²）"),
):
    _check_type(facility_type)
    bbox_coords = _parse_bbox(bbox)
    radius = buffer_radius or DEFAULT_RADIUS[facility_type]
    features = await query_blind_spots(bbox_coords, facility_type, radius, pop_threshold)
    return {
        "code": 200,
        "data": {
            "facility_type": facility_type,
            "pop_threshold": pop_threshold,
            "blind_spot_count": len(features),
            "blind_spots": {"type": "FeatureCollection", "features": features},
        },
    }


# ── ⑤ 缓冲覆盖区 ──────────────────────────────────────────────────────────────

@router.get("/analysis/coverage", summary="设施缓冲覆盖区（GeoJSON）")
async def coverage(
    bbox: str = Query(...),
    facility_type: str = Query(...),
    buffer_radius: Optional[int] = Query(None),
):
    _check_type(facility_type)
    bbox_coords = _parse_bbox(bbox)
    radius = buffer_radius or DEFAULT_RADIUS[facility_type]
    geojson = await query_coverage(bbox_coords, facility_type, radius)
    return {
        "code": 200,
        "data": {"facility_type": facility_type, "buffer_radius": radius, "coverage_geojson": geojson},
    }


# ── ⑥ 全类型覆盖区叠加 ─────────────────────────────────────────────────────────

@router.get("/analysis/coverage-all", summary="全设施类型覆盖区叠加")
async def coverage_all(
    bbox: str = Query(...),
    school_radius: Optional[int] = Query(None, ge=1),
    hospital_radius: Optional[int] = Query(None, ge=1),
    park_radius: Optional[int] = Query(None, ge=1),
):
    bbox_coords = _parse_bbox(bbox)
    radii = _resolve_all_radii(school_radius, hospital_radius, park_radius)
    fc = await query_coverage_all(bbox_coords, radii)
    return {"code": 200, "data": {"radii": radii, "coverage_geojson": fc}}


# ── ⑦ 全类型盲区识别 ────────────────────────────────────────────────────────────

@router.get("/analysis/blind-spots-all", summary="全设施类型供给盲区识别")
async def blind_spots_all(
    bbox: str = Query(...),
    pop_threshold: float = Query(3000.0, description="人口密度阈值（人/km²）"),
    school_radius: Optional[int] = Query(None, ge=1),
    hospital_radius: Optional[int] = Query(None, ge=1),
    park_radius: Optional[int] = Query(None, ge=1),
):
    bbox_coords = _parse_bbox(bbox)
    radii = _resolve_all_radii(school_radius, hospital_radius, park_radius)
    features = await query_blind_spots_all(bbox_coords, radii, pop_threshold)
    return {
        "code": 200,
        "data": {
            "radii": radii,
            "pop_threshold": pop_threshold,
            "blind_spot_count": len(features),
            "blind_spots": {"type": "FeatureCollection", "features": features},
        },
    }


# ── ⑧ 全类型供需统计 ────────────────────────────────────────────────────────────

@router.get("/analysis/supply-demand-all", summary="全设施类型供需统计")
async def supply_demand_all(
    bbox: str = Query(...),
    school_radius: Optional[int] = Query(None, ge=1),
    hospital_radius: Optional[int] = Query(None, ge=1),
    park_radius: Optional[int] = Query(None, ge=1),
):
    bbox_coords = _parse_bbox(bbox)
    radii = _resolve_all_radii(school_radius, hospital_radius, park_radius)
    row = await query_supply_demand_all(bbox_coords, radii)
    total = row.get("total", 0) or 1
    covered = row.get("covered", 0)
    return {
        "code": 200,
        "data": {
            "radii": radii,
            "total_population": row.get("total", 0),
            "covered_population": covered,
            "coverage_rate": round(covered / total, 3),
            "facility_count": row.get("facility_count", 0),
        },
    }
