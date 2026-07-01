"""
边界坐标校正：GCJ-02 → WGS84

背景：
    data/processed 下的洪山区边界 GeoJSON 来源于高德/阿里云 DataV 行政区划服务
    （properties 中的 adcode / center / centroid / acroutes / parent 即其特征），
    其坐标是 GCJ-02（火星坐标）。而本项目其余数据——WorldPop 人口栅格、OSM 设施点、
    天地图 / OSM 底图——均为 WGS84 (EPSG:4326)。二者叠加时边界会整体偏移约 ~590m
    （洪山区处东偏 ~531m、北偏 ~-257m），表现为“行政边界与底图不重合”。

    本脚本把边界几何与 center/centroid 属性由 GCJ-02 反解为 WGS84，使其与全链路 WGS84
    对齐。转换后为每个要素写入 properties.coord_system = "WGS84" 作为标记，脚本因此幂等：
    已校正的文件再次运行会被跳过，不会二次偏移。

用法：
    python scripts/边界坐标校正.py

    默认处理 data/processed 下的三份边界文件；已带 WGS84 标记的文件自动跳过。
"""

import json
import math
import sys
from pathlib import Path

# Windows 控制台按 UTF-8 输出，避免中文日志乱码
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# ======================== GCJ-02 <-> WGS84 变换 ========================
# 标准“火星坐标”偏移算法（与前端/高德通用实现一致）。
_A = 6378245.0                      # 克拉索夫斯基椭球长半轴
_EE = 0.00669342162296594323        # 第一偏心率平方


def _transform_lat(x: float, y: float) -> float:
    ret = -100 + 2 * x + 3 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    ret += (20 * math.sin(6 * x * math.pi) + 20 * math.sin(2 * x * math.pi)) * 2 / 3
    ret += (20 * math.sin(y * math.pi) + 40 * math.sin(y / 3 * math.pi)) * 2 / 3
    ret += (160 * math.sin(y / 12 * math.pi) + 320 * math.sin(y * math.pi / 30)) * 2 / 3
    return ret


def _transform_lng(x: float, y: float) -> float:
    ret = 300 + x + 2 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    ret += (20 * math.sin(6 * x * math.pi) + 20 * math.sin(2 * x * math.pi)) * 2 / 3
    ret += (20 * math.sin(x * math.pi) + 40 * math.sin(x / 3 * math.pi)) * 2 / 3
    ret += (150 * math.sin(x / 12 * math.pi) + 300 * math.sin(x / 30 * math.pi)) * 2 / 3
    return ret


def wgs84_to_gcj02(lng: float, lat: float):
    """WGS84 → GCJ-02。"""
    d_lat = _transform_lat(lng - 105.0, lat - 35.0)
    d_lng = _transform_lng(lng - 105.0, lat - 35.0)
    rad_lat = lat / 180.0 * math.pi
    magic = math.sin(rad_lat)
    magic = 1 - _EE * magic * magic
    sqrt_magic = math.sqrt(magic)
    d_lat = (d_lat * 180.0) / ((_A * (1 - _EE)) / (magic * sqrt_magic) * math.pi)
    d_lng = (d_lng * 180.0) / (_A / sqrt_magic * math.cos(rad_lat) * math.pi)
    return lng + d_lng, lat + d_lat


def gcj02_to_wgs84(lng: float, lat: float):
    """GCJ-02 → WGS84（反解近似，误差 < 1m，远小于 6 位小数精度）。"""
    g_lng, g_lat = wgs84_to_gcj02(lng, lat)
    return lng * 2 - g_lng, lat * 2 - g_lat


# ======================== GeoJSON 坐标遍历 ========================

NDIGITS = 6  # 保留 6 位小数，与源数据精度一致（≈0.1m）


def _convert_coords(node):
    """递归转换嵌套坐标数组：叶子为 [lng, lat(, ...)] 的点。"""
    if node and isinstance(node[0], (int, float)):
        lng, lat = gcj02_to_wgs84(node[0], node[1])
        out = [round(lng, NDIGITS), round(lat, NDIGITS)]
        out.extend(node[2:])  # 保留可能存在的高程等附加维度
        return out
    return [_convert_coords(child) for child in node]


def _convert_point_prop(value):
    """转换 properties 里的 [lng, lat] 点（center / centroid）。"""
    if (
        isinstance(value, list)
        and len(value) >= 2
        and all(isinstance(v, (int, float)) for v in value[:2])
    ):
        lng, lat = gcj02_to_wgs84(value[0], value[1])
        return [round(lng, NDIGITS), round(lat, NDIGITS)]
    return value


def convert_file(path: Path) -> bool:
    """就地把一份边界 GeoJSON 由 GCJ-02 校正为 WGS84。返回是否发生转换。"""
    data = json.loads(path.read_text(encoding="utf-8"))
    features = data.get("features", [])

    # 幂等保护：已标记 WGS84 则跳过
    if features and features[0].get("properties", {}).get("coord_system") == "WGS84":
        print(f"[SKIP] {path.name} 已是 WGS84，跳过")
        return False

    for feat in features:
        geom = feat.get("geometry")
        if geom and "coordinates" in geom:
            geom["coordinates"] = _convert_coords(geom["coordinates"])
        props = feat.setdefault("properties", {})
        for key in ("center", "centroid"):
            if key in props:
                props[key] = _convert_point_prop(props[key])
        props["coord_system"] = "WGS84"  # 标记来源坐标已校正，兼作幂等依据

    # 保持源文件的紧凑单行格式，最小化版本差异
    path.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"[OK]   {path.name} 已由 GCJ-02 校正为 WGS84")
    return True


def main():
    processed = Path(__file__).resolve().parents[1] / "data" / "processed"
    targets = ["洪山区.geojson", "洪山区_边界.geojson", "洪山区_区划.geojson"]

    print("=" * 56)
    print("  边界坐标校正  GCJ-02 → WGS84")
    print("=" * 56)
    changed = 0
    for name in targets:
        p = processed / name
        if not p.is_file():
            print(f"[WARN] 未找到 {p}")
            continue
        if convert_file(p):
            changed += 1
    print("-" * 56)
    print(f"完成：{changed} 个文件被校正。")


if __name__ == "__main__":
    main()
