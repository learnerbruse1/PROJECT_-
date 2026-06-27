# 数据说明

研究区：**武汉市洪山区**（行政区划代码 420111）。坐标系全程 WGS84 (EPSG:4326)，经度在前。

## 目录约定

| 目录 | 是否入库 | 内容 |
| --- | --- | --- |
| `data/raw/` | ❌ `.gitignore` 排除 | 原始下载与中间产物（大文件、可再生） |
| `data/processed/` | ✅ 跟踪 | 处理后、系统运行直接读取的 GeoJSON 成果 |

> 之所以保留 `processed/` 入库：系统启动即依赖这些 GeoJSON，克隆后无需重跑处理流程即可运行。

## data/processed/（系统依赖）

| 文件 | 内容 | 后端用途 |
| --- | --- | --- |
| `hongshan_population.geojson` | 人口栅格网格（约 100m，属性 `pop_count` 人/km²） | 热力 / 供需 / 盲区 |
| `学校医院.geojson` | 学校 + 医疗设施点（OSM） | 设施图层（归并为 school/hospital） |
| `公园绿地.geojson` | 公园绿地点（OSM，type=park） | 设施图层（park） |
| `洪山区_边界.geojson` | 研究区边界（MultiPolygon） | `/meta/boundary`，前端定位与轮廓 |
| `洪山区.geojson` / `洪山区_区划.geojson` | 边界的其它版本 | 备用，系统未直接使用 |

> 后端默认从 `data/processed/` 读取（可用环境变量 `DATA_DIR` 覆盖）。

## data/raw/（源数据，需自行下载/再生）

| 文件 | 来源 |
| --- | --- |
| `chn_ppp_2020_1km_Aggregated_UNadj.tif` | WorldPop 2020 中国 1km 人口栅格（UN 调整），<https://www.worldpop.org/> |
| `洪山区.shp`（及配套 .dbf/.shx/.prj 等） | 洪山区行政边界矢量 |
| `hongshan_population.shp`（及配套） | 人口网格的 Shapefile 版本（QGIS 产物） |
| `hongshan_pop_clipped.tif` | 裁剪后的人口栅格中间产物 |

## 由原始数据再生 processed

```bash
pip install -r scripts/requirements.txt
python scripts/栅格重采样.py
```

脚本会读取 `data/raw/` 下的栅格与边界，裁剪、重采样为约 100m 网格，输出
`data/processed/hongshan_population.geojson`（点要素或网格面，可在脚本顶部 `OUTPUT_FORMAT` 切换）。

设施数据（`学校医院.geojson`、`公园绿地.geojson`）为 OSM 提取结果，按需用 QGIS / Overpass 重新导出即可。

## 数据来源与许可

- 人口：WorldPop 2020（CC BY 4.0）。
- 设施：OpenStreetMap（ODbL）。
- 边界：公开行政区划数据。
