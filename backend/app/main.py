from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.postgis import close_pool
from app.routers import statistics


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_pool()


app = FastAPI(
    title="人口分布热力与公共设施叠加 API",
    version="1.0.0",
    description="供需统计与空间分析后端服务",
    lifespan=lifespan,
)

app.include_router(statistics.router, prefix="/api/v1", tags=["统计分析"])
