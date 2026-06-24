-- 启用 PostGIS 扩展
CREATE EXTENSION IF NOT EXISTS postgis;

-- 人口密度栅格表（从 GHSL / WorldPop 导入）
CREATE TABLE IF NOT EXISTS population_grid (
    id      SERIAL PRIMARY KEY,
    geom    GEOMETRY(Point, 4326) NOT NULL,
    value   FLOAT  NOT NULL,          -- 人口密度（人/km²）
    dataset VARCHAR(20) DEFAULT 'ghsl'
);
CREATE INDEX IF NOT EXISTS idx_pop_geom    ON population_grid USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_pop_dataset ON population_grid(dataset);

-- 公共设施表（从 OSM 导入）
CREATE TABLE IF NOT EXISTS facilities (
    id   VARCHAR(50) PRIMARY KEY,     -- OSM node id，如 osm_node_123456
    name VARCHAR(255),
    type VARCHAR(20) NOT NULL CHECK (type IN ('school', 'hospital', 'park')),
    geom GEOMETRY(Point, 4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fac_geom ON facilities USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_fac_type ON facilities(type);
