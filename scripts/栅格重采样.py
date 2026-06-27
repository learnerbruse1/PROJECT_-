"""
人口栅格 → GeoJSON 转换工具
支持 WorldPop 栅格 + 洪山区矢量边界
输出点要素或网格面 GeoJSON，带进度条
"""

import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from rasterio.mask import mask as rasterio_mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
from shapely.geometry import mapping, box, Point
from tqdm import tqdm


# ======================== 配置区 ========================

SCRIPT_DIR = Path(__file__).parent.resolve()
ROOT_DIR = SCRIPT_DIR.parent                  # 项目根目录（scripts/ 的上一级）
RAW_DIR = ROOT_DIR / "data" / "raw"           # 原始源数据
PROCESSED_DIR = ROOT_DIR / "data" / "processed"  # 处理后供系统使用

# 输入文件路径（来自 data/raw/）
WORLDPOP_RASTER = str(RAW_DIR / "chn_ppp_2020_1km_Aggregated_UNadj.tif")
HONGSHAN_BOUNDARY = str(RAW_DIR / "洪山区.shp")

# 输出配置（写入 data/processed/）
OUTPUT_FILE = str(PROCESSED_DIR / "hongshan_population.geojson")
OUTPUT_FORMAT = "grid"                        # 可选: "point"（点要素）或 "grid"（网格面）
RESAMPLE_X = 500                              # 重采样后目标像素宽度（像素），控制前端性能
TARGET_CRS = "EPSG:4326"                     # 输出坐标系（WGS84）

# 网格面模式下每个单元格的经纬度跨度（度），值越小精度越高、点数越多
GRID_LAT = 0.002
GRID_LON = 0.002

# 进度条描述前缀
PROGRESS_DESC = "Processing"


def check_file(path: str, desc: str) -> None:
    """检查文件是否存在"""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"{desc} 不存在: {path}")


def log(msg: str) -> None:
    print(f"[INFO] {msg}", flush=True)


# ======================== 1~3: 加载 & 检查 ========================

def load_raster(path: str):
    """加载栅格并返回 dataset 对象"""
    log(f"正在加载栅格: {path}")
    ds = rasterio.open(path)
    return ds


def load_boundary(path: str):
    """加载边界矢量（支持 .shp / .geojson / .gpkg）"""
    log(f"正在加载边界: {path}")
    try:
        import geopandas as gpd
        gdf = gpd.read_file(path)
        return gdf
    except Exception as e:
        raise RuntimeError(f"无法读取边界文件 {path}: {e}")


def inspect_and_align(raster_ds, boundary_gdf, target_crs_str: str):
    """
    检查坐标系与空间范围，必要时统一 CRS。
    返回: (reprojected_raster_path, aligned_boundary_gdf)
    """
    src_crs = raster_ds.crs
    bound_crs = str(boundary_gdf.crs)
    log(f"栅格 CRS : {src_crs}")
    log(f"边界 CRS : {bound_crs}")

    # 如果边界和目标 CRS 不同，先对齐边界
    if bound_crs != target_crs_str:
        log(f"边界 CRS ({bound_crs}) 与目标 CRS ({target_crs_str}) 不同，正在重投影...")
        try:
            import geopandas as gpd
            aligned = boundary_gdf.to_crs(target_crs_str)
        except Exception as e:
            raise RuntimeError(f"边界重投影失败: {e}")
    else:
        aligned = boundary_gdf.copy()

    # 栅格若也需要重投影到目标 CRS
    if src_crs != target_crs_str:
        log(f"栅格 CRS ({src_crs}) 与目标 CRS ({target_crs_str}) 不同，正在重投影...")
        reproj_path = _reproject_raster(raster_ds, target_crs_str)
        reproj_ds = rasterio.open(reproj_path)
    else:
        reproj_ds = raster_ds

    # 打印空间范围
    log(f"栅格范围: {reproj_ds.bounds}")
    log(f"边界范围: {aligned.total_bounds}")
    log("坐标系与空间范围检查完成 OK")

    return reproj_ds, aligned, reproj_path if src_crs != target_crs_str else None


def _reproject_raster(src_ds, target_crs_str: str):
    """将栅格重投影到新 CRS，写入临时文件"""
    tmp_path = src_ds.name.replace(".tif", "_reproj.tif")
    with rasterio.open(src_ds.name) as src:
        transform, width, height = calculate_default_transform(
            src.crs, target_crs_str, src.width, src.height,
            *src.bounds
        )
        kwargs = src.meta.copy()
        kwargs.update({
            "crs": target_crs_str,
            "transform": transform,
            "width": width,
            "height": height,
        })
        with rasterio.open(tmp_path, "w", **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_crs=src.crs,
                    dst_crs=target_crs_str,
                    resampling=Resampling.bilinear,
                )
    log(f"栅格重投影完成 → {tmp_path}")
    return tmp_path


# ======================== 4: 裁剪 ========================

def clip_raster_by_mask(raster_path: str, boundary_gdf, desc_prefix: str = "裁剪"):
    """用边界裁剪栅格"""
    log(f"{desc_prefix}: 按边界裁剪栅格...")
    clip_path = raster_path.replace(".tif", "_clipped.tif")

    with rasterio.open(raster_path) as src:
        out_image, out_transform = rasterio_mask(
            src, boundary_gdf.to_crs(src.crs).geometry, crop=True
        )
        out_meta = src.meta.copy()
        out_meta.update({
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform,
        })

    with rasterio.open(clip_path, "w", **out_meta) as dst:
        dst.write(out_image)

    log(f"裁剪完成 → {clip_path}")
    return clip_path


# ======================== 5: 重采样 ========================

def resample_raster(raster_path: str, target_width: int, desc_prefix: str = "重采样"):
    """按目标宽度重采样栅格（使用 rasterio reproject，保证几何正确）"""
    log(f"{desc_prefix}: 按宽度 {target_width} 重采样...")
    resamp_path = raster_path.replace(".tif", f"_resamp_{target_width}.tif")

    with rasterio.open(raster_path) as src:
        src_height = src.height
        ratio = src.width / target_width
        target_height = int(src_height / ratio)
        if target_height < 1:
            target_height = 1

        # 正确计算新仿射变换：保持地理范围不变，只改变像素尺寸
        new_pixel_w = src.transform.a * ratio
        new_pixel_h = src.transform.e * ratio
        new_transform = rasterio.transform.Affine(
            new_pixel_w, src.transform.b, src.transform.c,
            src.transform.d, new_pixel_h, src.transform.f,
        )

        out_meta = src.meta.copy()
        out_meta.update({
            "height": target_height,
            "width": target_width,
            "transform": new_transform,
        })

        with rasterio.open(resamp_path, "w", **out_meta) as dst:
            reproject(
                source=rasterio.band(src, 1),
                destination=rasterio.band(dst, 1),
                src_crs=src.crs,
                dst_crs=src.crs,
                resampling=Resampling.average,
                num_threads=2,
            )

    log(f"重采样完成 → {resamp_path}")
    return resamp_path


# ======================== 6: 转点要素 GeoJSON ========================

def raster_to_point_geojson(raster_path: str, boundary_gdf,
                            output_path: str, desc_prefix: str = "转点要素"):
    """将栅格转为点要素 GeoJSON"""
    log(f"{desc_prefix}: 栅格 → 点要素 GeoJSON")

    with rasterio.open(raster_path) as src:
        data = src.read(1).astype(float)
        transform = src.transform
        rows, cols = data.shape

    # 统计非零单元格数
    total_cells = int(np.count_nonzero(data > 0))
    features = []

    pbar = tqdm(total=total_cells, desc=desc_prefix, unit="cell")

    for r in range(rows):
        for c in range(cols):
            val = data[r, c]
            if val <= 0:
                pbar.update(1)
                continue
            # 计算像元中心经纬度
            lon, lat = transform * (c + 0.5, r + 0.5)
            # 判断是否在边界内
            pt = Point(lon, lat)
            if not boundary_gdf.contains(pt).any():
                pbar.update(1)
                continue
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {"pop_count": float(val)},
            })
            pbar.update(1)

    pbar.close()

    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)

    log(f"点要素完成: {len(features)} 个要素 → {output_path}")
    return output_path


# ======================== 7: 转网格面 GeoJSON ========================

def raster_to_grid_geojson(raster_path: str, boundary_gdf,
                           lat_span: float, lon_span: float,
                           output_path: str, desc_prefix: str = "转网格面"):
    """将栅格转为规则网格面 GeoJSON（基于栅格仿射变换精确计算）"""
    log(f"{desc_prefix}: 栅格 → 网格面 GeoJSON")

    with rasterio.open(raster_path) as src:
        data = src.read(1).astype(float)
        transform = src.transform
        rows, cols = data.shape
        pixel_w = transform.a   # 像元宽度（经度方向）
        pixel_h = abs(transform.e)  # 像元高度（纬度方向，取绝对值）

    # 收集边界要素的字段信息（取第一个要素的字段作为模板）
    boundary_props = {}
    for col in boundary_gdf.columns:
        if col != "geometry":
            val = boundary_gdf[col].iloc[0] if len(boundary_gdf) > 0 else None
            boundary_props[col] = val

    features = []
    total = int(np.count_nonzero(data > 0))

    pbar = tqdm(total=total, desc=desc_prefix, unit="cell")

    for r in range(rows):
        for c in range(cols):
            val = data[r, c]
            if val <= 0:
                pbar.update(1)
                continue
            # 使用栅格的仿射变换精确计算像元四个角点坐标
            lon_left, lat_top = transform * (c, r)
            lon_right, lat_bottom = transform * (c + 1, r + 1)
            geom = box(lon_left, lat_top, lon_right, lat_bottom)
            # 注意: box 参数顺序是 (minx, miny, maxx, maxy)
            geom = box(min(lon_left, lon_right), min(lat_bottom, lat_top),
                       max(lon_left, lon_right), max(lat_bottom, lat_top))
            # 检查是否和边界有交集
            if not boundary_gdf.intersects(geom).any():
                pbar.update(1)
                continue
            # 添加边界要素的字段信息
            props = {"pop_count": float(val)}
            props.update(boundary_props)
            features.append({
                "type": "Feature",
                "geometry": mapping(geom),
                "properties": props,
            })
            pbar.update(1)

    pbar.close()

    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)

    log(f"网格面完成: {len(features)} 个要素 → {output_path}")
    return output_path


# ======================== 主流程 ========================

def main():
    print("=" * 60)
    print("  WorldPop 人口栅格 → GeoJSON 转换工具")
    print("  支持: 点要素 / 网格面 输出")
    print("=" * 60)
    print()

    # ---- 参数校验 ----
    check_file(WORLDPOP_RASTER, "人口栅格")
    check_file(HONGSHAN_BOUNDARY, "洪山区边界")

    t0 = time.time()

    # Step 1~2: 加载
    raster_ds = load_raster(WORLDPOP_RASTER)
    boundary_gdf = load_boundary(HONGSHAN_BOUNDARY)

    # Step 3: 检查坐标系 & 对齐
    clipped_ds, aligned_boundary, temp_raster = inspect_and_align(
        raster_ds, boundary_gdf, TARGET_CRS
    )

    # 关闭原始栅格
    raster_ds.close()

    # Step 4: 裁剪
    clip_path = clip_raster_by_mask(temp_raster or WORLDPOP_RASTER, aligned_boundary)

    # Step 5: 重采样（按前端性能需要）
    resamp_path = resample_raster(clip_path, RESAMPLE_X)

    # Step 6~7: 转换并统一字段名 pop_count
    if OUTPUT_FORMAT == "point":
        raster_to_point_geojson(
            resamp_path, aligned_boundary, OUTPUT_FILE,
            desc_prefix="转点要素"
        )
    elif OUTPUT_FORMAT == "grid":
        raster_to_grid_geojson(
            resamp_path, aligned_boundary,
            None, None, OUTPUT_FILE,
            desc_prefix="转网格面"
        )
    else:
        raise ValueError(f"未知输出格式: {OUTPUT_FORMAT}，可选 point / grid")

    # 清理中间文件
    for f in [temp_raster, clip_path, resamp_path]:
        if f and os.path.isfile(f):
            os.remove(f)
            log(f"已清理临时文件: {f}")

    elapsed = time.time() - t0
    print()
    print("=" * 60)
    print(f"  OK 全部完成! 耗时 {elapsed:.1f}s")
    print(f"  输出: {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
