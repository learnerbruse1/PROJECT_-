-- 启用 PostGIS 扩展
CREATE EXTENSION IF NOT EXISTS postgis;

-- 人口密度栅格表（从 GHSL / WorldPop 导入）
CREATE TABLE IF NOT EXISTS population_grid (
    id      SERIAL PRIMARY KEY,
    geom    GEOMETRY(Point, 4326) NOT NULL,
    value   FLOAT  NOT NULL,          -- 人口密度（人/km²）
    dataset VARCHAR(20) DEFAULT 'ghsl'
);
-- 单列索引保留用于 dataset 过滤；按 dataset 分区的局部 GIST 索引加速 bbox 查询
CREATE INDEX IF NOT EXISTS idx_pop_geom       ON population_grid USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_pop_dataset    ON population_grid(dataset);
CREATE INDEX IF NOT EXISTS idx_pop_ghsl_geom  ON population_grid USING GIST(geom) WHERE dataset = 'ghsl';
CREATE INDEX IF NOT EXISTS idx_pop_wp_geom    ON population_grid USING GIST(geom) WHERE dataset = 'worldpop';

-- 公共设施表（从 OSM 导入）
CREATE TABLE IF NOT EXISTS facilities (
    id   VARCHAR(50) PRIMARY KEY,     -- OSM node id，如 osm_node_123456
    name VARCHAR(255),
    type VARCHAR(20) NOT NULL CHECK (type IN ('school', 'hospital', 'park')),
    geom GEOMETRY(Point, 4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fac_geom      ON facilities USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_fac_type      ON facilities(type);
-- 按设施类型分区的局部 GIST 索引，加速 type + bbox 联合过滤
CREATE INDEX IF NOT EXISTS idx_fac_school    ON facilities USING GIST(geom) WHERE type = 'school';
CREATE INDEX IF NOT EXISTS idx_fac_hospital  ON facilities USING GIST(geom) WHERE type = 'hospital';
CREATE INDEX IF NOT EXISTS idx_fac_park      ON facilities USING GIST(geom) WHERE type = 'park';
