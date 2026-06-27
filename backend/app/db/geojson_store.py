"""基于本地 GeoJSON 文件的数据后端。

不依赖 PostgreSQL / PostGIS，直接读取 data/ 目录下的洪山区人口栅格与设施数据，
在内存中用 shapely + numpy 完成与 PostGIS 后端完全一致的五类空间查询，使整个系统开箱即用。

性能要点：
- 人口点以 numpy 数组常驻内存，bbox 过滤为向量化掩码运算；
- 覆盖判定用 STRtree 一次性批量查询（避免逐点 contains 循环）；
- 供需/盲区/覆盖结果带 LRU 缓存，并通过 asyncio.to_thread 下放线程，避免阻塞事件循环。

通过环境变量 DATA_BACKEND=geojson（默认）启用；DATA_BACKEND=postgis 时改用 app.db.postgis。
数据目录由 DATA_DIR 指定，默认指向项目根目录下的 data/processed/。
"""
import asyncio
import json
import math
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np
from shapely import points as _shp_points
from shapely.geometry import Point, mapping
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree

# ── 数据目录与文件名 ──────────────────────────────────────────────────────────
# 默认指向项目根目录下的 data/processed/（处理后、供系统直接使用的 GeoJSON）。
DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parents[3] / "data" / "processed"))

POP_FILE = "hongshan_population.geojson"      # 人口栅格（多边形网格，属性 pop_count）
SCHOOL_HOSPITAL_FILE = "学校医院.geojson"      # 学校 + 医疗设施（OSM 点）
PARK_FILE = "公园绿地.geojson"                 # 公园绿地（OSM 点）
BOUNDARY_FILE = "洪山区_边界.geojson"          # 研究区边界（用于地图定位）

# OSM 原始类型 → 三大类（school / hospital / park）的归并映射
TYPE_MAP = {
    "school": "school", "kindergarten": "school", "college": "school", "university": "school",
    "hospital": "hospital", "clinic": "hospital", "doctors": "hospital",
    "park": "park",
}

# 研究区中心，作为局部等距投影原点（用于以米为单位的缓冲计算）
_LNG0, _LAT0 = 114.40, 30.50
_M_PER_DEG_LAT = 111320.0
_M_PER_DEG_LNG = 111320.0 * math.cos(math.radians(_LAT0))


def _to_metric(lng: float, lat: float) -> tuple[float, float]:
    """经纬度 → 局部平面米坐标（等距近似，适用于区县尺度缓冲）。"""
    return (lng - _LNG0) * _M_PER_DEG_LNG, (lat - _LAT0) * _M_PER_DEG_LAT


def _to_lnglat_xy(x: float, y: float, z=None):
    return _LNG0 + x / _M_PER_DEG_LNG, _LAT0 + y / _M_PER_DEG_LAT


# ── 内存数据 ──────────────────────────────────────────────────────────────────
_loaded = False
_pop_arr: np.ndarray = np.empty((0, 3), dtype=float)  # 列：lng, lat, value
_facilities: list[dict] = []                          # {id,name,type,subtype,lng,lat,source}
_boundary_geojson: Optional[dict] = None


def _read_geojson(name: str) -> dict:
    path = DATA_DIR / name
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_population() -> np.ndarray:
    """读取人口栅格多边形，取每个网格中心点 + pop_count，得到 (N,3) 密度数组。"""
    gj = _read_geojson(POP_FILE)
    rows: list[tuple[float, float, float]] = []
    for feat in gj.get("features", []):
        geom = feat.get("geometry") or {}
        if geom.get("type") != "Polygon":
            continue
        ring = geom["coordinates"][0]
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        val = float((feat.get("properties") or {}).get("pop_count", 0) or 0)
        if val > 0:
            rows.append(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, val))
    return np.array(rows, dtype=float) if rows else np.empty((0, 3), dtype=float)


def _load_facilities() -> list[dict]:
    """读取学校/医院/公园点，按 TYPE_MAP 归并为三大类。"""
    out: list[dict] = []
    for fname, source in ((SCHOOL_HOSPITAL_FILE, "OSM/学校医院"), (PARK_FILE, "OSM/公园绿地")):
        gj = _read_geojson(fname)
        for feat in gj.get("features", []):
            props = feat.get("properties") or {}
            raw_type = (props.get("type") or "").lower()
            mapped = TYPE_MAP.get(raw_type)
            if not mapped:
                continue
            geom = feat.get("geometry") or {}
            if geom.get("type") != "Point":
                continue
            lng, lat = geom["coordinates"][0], geom["coordinates"][1]
            osm_id = props.get("osm_id") or props.get("OBJECTID")
            name = (props.get("name") or "").strip() or {
                "school": "未命名学校", "hospital": "未命名医疗设施", "park": "未命名公园",
            }[mapped]
            out.append({
                "id": f"osm_node_{osm_id}",
                "name": name,
                "type": mapped,
                "subtype": raw_type,        # 保留 OSM 原始细分类型，供前端弹窗展示
                "lng": float(lng),
                "lat": float(lat),
                "source": source,
            })
    return out


def load() -> None:
    """加载全部本地数据进内存（幂等）。在 FastAPI 启动时调用。"""
    global _loaded, _pop_arr, _facilities, _boundary_geojson
    if _loaded:
        return
    _pop_arr = _load_population()
    _facilities = _load_facilities()
    try:
        _boundary_geojson = _read_geojson(BOUNDARY_FILE)
    except FileNotFoundError:
        _boundary_geojson = None
    _loaded = True


def _ensure_loaded() -> None:
    if not _loaded:
        load()


# ── 空间工具 ──────────────────────────────────────────────────────────────────

def _in_bbox(lng: float, lat: float, bbox) -> bool:
    return bbox[0] <= lng <= bbox[2] and bbox[1] <= lat <= bbox[3]


def _facilities_in_bbox(bbox, fac_type: Optional[str]) -> list[dict]:
    return [
        f for f in _facilities
        if (fac_type is None or f["type"] == fac_type) and _in_bbox(f["lng"], f["lat"], bbox)
    ]


def _pop_in_bbox(bbox) -> np.ndarray:
    """向量化筛选 bbox 内的人口点，返回 (K,3) 子数组。"""
    if _pop_arr.size == 0:
        return _pop_arr
    lng, lat = _pop_arr[:, 0], _pop_arr[:, 1]
    mask = (lng >= bbox[0]) & (lng <= bbox[2]) & (lat >= bbox[1]) & (lat <= bbox[3])
    return _pop_arr[mask]


def _facility_circles(bbox, fac_type: str, radius: float) -> tuple[list, int]:
    """bbox 内该类型设施的米制缓冲圆列表 + 设施数量。"""
    facs = _facilities_in_bbox(bbox, fac_type)
    circles = [Point(_to_metric(f["lng"], f["lat"])).buffer(radius, quad_segs=16) for f in facs]
    return circles, len(facs)


def _covered_mask(lnglat: np.ndarray, circles: list) -> np.ndarray:
    """返回布尔掩码：每个点是否落入任一缓冲圆。STRtree 批量查询，避免逐点循环。"""
    n = len(lnglat)
    if n == 0 or not circles:
        return np.zeros(n, dtype=bool)
    mx = (lnglat[:, 0] - _LNG0) * _M_PER_DEG_LNG
    my = (lnglat[:, 1] - _LAT0) * _M_PER_DEG_LAT
    pts = _shp_points(mx, my)
    tree = STRtree(circles)
    pairs = tree.query(pts, predicate="intersects")  # shape (2, M)：[点索引, 圆索引]
    mask = np.zeros(n, dtype=bool)
    if pairs.size:
        mask[np.unique(pairs[0])] = True
    return mask


# ── ① 人口热力 ────────────────────────────────────────────────────────────────

async def query_heatmap(bbox: list[float], dataset: str) -> list[dict]:
    """返回 bbox 内人口密度点（最多 10000 条）。本数据集为 WorldPop，dataset 参数被兼容性接受。

    点数超限时按等步长在全集上均匀抽样（而非截断前 N 条），避免热力图只覆盖研究区一隅。
    """
    _ensure_loaded()
    sub = _pop_in_bbox(bbox)
    LIMIT = 10000
    if len(sub) > LIMIT:
        idx = np.linspace(0, len(sub) - 1, LIMIT).astype(int)
        sub = sub[idx]
    return [
        {"lng": round(float(r[0]), 5), "lat": round(float(r[1]), 5), "value": round(float(r[2]), 1)}
        for r in sub
    ]


# ── ② 公共设施 ────────────────────────────────────────────────────────────────

async def query_facilities(
    bbox: list[float], fac_type: Optional[str], page: int, page_size: int
) -> tuple[int, list[dict]]:
    """分页查询 bbox 内设施列表，可按 type 过滤。"""
    _ensure_loaded()
    matched = _facilities_in_bbox(bbox, fac_type)
    total = len(matched)
    start = (page - 1) * page_size
    items = [
        {"id": f["id"], "name": f["name"], "type": f["type"],
         "subtype": f["subtype"], "lng": f["lng"], "lat": f["lat"], "source": f["source"]}
        for f in matched[start:start + page_size]
    ]
    return total, items


# ── ③ 供需统计 ────────────────────────────────────────────────────────────────

@lru_cache(maxsize=256)
def _supply_demand_sync(bbox: tuple, fac_type: str, radius: int) -> dict:
    sub = _pop_in_bbox(bbox)
    total = int(len(sub))
    circles, n_fac = _facility_circles(bbox, fac_type, radius)
    covered = int(_covered_mask(sub[:, :2], circles).sum()) if total else 0
    return {"facility_count": n_fac, "total": total, "covered": covered}


async def query_supply_demand(bbox: list[float], fac_type: str, radius: int) -> dict:
    """统计 bbox 内总人口点数、被服务区覆盖的人口点数、设施数量。"""
    _ensure_loaded()
    return await asyncio.to_thread(_supply_demand_sync, tuple(bbox), fac_type, int(radius))


# ── ④ 盲区识别 ────────────────────────────────────────────────────────────────

def _cluster_blind_points(arr: np.ndarray, cell_deg: float = 0.01) -> list[list[int]]:
    """对盲区点做基于网格的连通域聚类，拆分为多个独立盲区（替代单一凸包）。"""
    grid: dict[tuple[int, int], list[int]] = {}
    for idx in range(len(arr)):
        key = (int(arr[idx, 0] / cell_deg), int(arr[idx, 1] / cell_deg))
        grid.setdefault(key, []).append(idx)

    seen: set[tuple[int, int]] = set()
    clusters: list[list[int]] = []
    for key in list(grid):
        if key in seen:
            continue
        stack, members = [key], []      # 广度优先合并 8 邻域内的占用网格
        seen.add(key)
        while stack:
            cx, cy = stack.pop()
            members.extend(grid[(cx, cy)])
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nb = (cx + dx, cy + dy)
                    if nb in grid and nb not in seen:
                        seen.add(nb)
                        stack.append(nb)
        clusters.append(members)
    return clusters


@lru_cache(maxsize=128)
def _blind_spots_sync(bbox: tuple, fac_type: str, radius: int, pop_threshold: float) -> list[dict]:
    sub = _pop_in_bbox(bbox)
    if len(sub) == 0:
        return []
    high = sub[sub[:, 2] > pop_threshold]
    if len(high) == 0:
        return []
    circles, _ = _facility_circles(bbox, fac_type, radius)
    blind = high[~_covered_mask(high[:, :2], circles)]
    if len(blind) == 0:
        return []
    coverage = unary_union(circles) if circles else None

    features = []
    for members in _cluster_blind_points(blind):
        if len(members) < 3:           # 点太少无法构成有意义的面，跳过
            continue
        cpts = blind[members]
        metric_hull = unary_union(
            [Point(_to_metric(r[0], r[1])) for r in cpts]
        ).convex_hull
        if metric_hull.geom_type != "Polygon":
            continue
        # 扣除已被服务区覆盖的部分，确保盲区不与覆盖区重叠
        zone = metric_hull.difference(coverage) if coverage is not None and not coverage.is_empty else metric_hull
        if zone.is_empty or zone.geom_type not in ("Polygon", "MultiPolygon"):
            continue
        features.append({
            "type": "Feature",
            "properties": {
                "avg_population_density": round(float(cpts[:, 2].mean()), 1),
                "area_km2": round(zone.area / 1_000_000, 3),
                "point_count": int(len(cpts)),
            },
            "geometry": mapping(transform(_to_lnglat_xy, zone)),
        })
    features.sort(key=lambda f: f["properties"]["area_km2"], reverse=True)
    return features


async def query_blind_spots(
    bbox: list[float], fac_type: str, radius: int, pop_threshold: float
) -> list[dict]:
    """盲区 = 人口密度 > 阈值且不在任何设施服务区内的区域，聚类后输出多个凸包多边形。"""
    _ensure_loaded()
    return await asyncio.to_thread(
        _blind_spots_sync, tuple(bbox), fac_type, int(radius), float(pop_threshold)
    )


# ── ⑤ 缓冲覆盖区 ──────────────────────────────────────────────────────────────

@lru_cache(maxsize=128)
def _coverage_sync(bbox: tuple, fac_type: str, radius: int) -> dict:
    circles, _ = _facility_circles(bbox, fac_type, radius)
    if not circles:
        return {"type": "GeometryCollection", "geometries": []}
    return mapping(transform(_to_lnglat_xy, unary_union(circles)))


async def query_coverage(bbox: list[float], fac_type: str, radius: int) -> dict:
    """合并 bbox 内该类型设施的缓冲服务区，返回 GeoJSON 几何。"""
    _ensure_loaded()
    return await asyncio.to_thread(_coverage_sync, tuple(bbox), fac_type, int(radius))


# ── 元数据 / 健康检查（F11 数据状态自检） ────────────────────────────────────

def data_status() -> dict:
    """检测本地数据文件是否就绪，供前端启动自检（F11）。"""
    files = {
        "population": POP_FILE,
        "school_hospital": SCHOOL_HOSPITAL_FILE,
        "park": PARK_FILE,
        "boundary": BOUNDARY_FILE,
    }
    detail = {k: (DATA_DIR / v).is_file() for k, v in files.items()}
    ready = all(detail.values())
    counts = {}
    if ready:
        _ensure_loaded()
        counts = {
            "population_points": int(len(_pop_arr)),
            "facilities": len(_facilities),
            "schools": sum(1 for f in _facilities if f["type"] == "school"),
            "hospitals": sum(1 for f in _facilities if f["type"] == "hospital"),
            "parks": sum(1 for f in _facilities if f["type"] == "park"),
        }
    return {
        "ready": ready,
        "data_dir": str(DATA_DIR),
        "files": detail,
        "counts": counts,
        "backend": "geojson",
    }


def get_boundary() -> Optional[dict]:
    """返回研究区边界 GeoJSON，供前端绘制轮廓与定位。"""
    _ensure_loaded()
    return _boundary_geojson


async def close_pool() -> None:
    """与 PostGIS 后端接口对齐的空操作（文件后端无连接池需释放）。"""
    return None
