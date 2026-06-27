"""FastAPI 应用入口。

- lifespan：启动时加载本地数据（文件后端），关闭时释放资源（PostGIS 连接池）
- CORS：允许前端跨域调用（开发期前端通常经 Vite 代理，部署期可直接跨域）
- 路由：统计分析（5 个接口）+ 元数据（数据自检、边界）
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.db.provider import BACKEND_NAME, close_pool, load_data
from app.routers import meta, statistics


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 文件后端：启动即把本地数据载入内存，提前暴露数据缺失问题（F11）
    if BACKEND_NAME != "postgis":
        load_data()
    yield
    await close_pool()


app = FastAPI(
    title="人口分布热力与公共设施叠加 API",
    version="1.0.0",
    description="洪山区人口热力 / 公共设施叠加 / 供需统计 / 盲区识别 后端服务",
    lifespan=lifespan,
)

# 大体量 JSON / GeoJSON 响应（热力点、覆盖区）启用 gzip 压缩，显著减小传输体积
app.add_middleware(GZipMiddleware, minimum_size=1024)

# 允许的前端来源；逗号分隔，缺省放开所有来源便于课程演示与云端部署
_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(statistics.router, prefix="/api/v1", tags=["统计分析"])
app.include_router(meta.router, prefix="/api/v1", tags=["元数据"])


@app.get("/", tags=["元数据"], summary="服务健康检查")
async def root():
    return {"code": 200, "data": {"service": "gis-population-facility", "backend": BACKEND_NAME, "docs": "/docs"}}
