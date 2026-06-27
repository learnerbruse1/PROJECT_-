"""元数据接口 — 数据状态自检（F11）与研究区边界。"""
from fastapi import APIRouter, HTTPException

from app.db.provider import BACKEND_NAME, data_status, get_boundary

router = APIRouter()


@router.get("/meta/status", summary="数据状态自检（F11）")
async def meta_status():
    """检测本地数据文件是否就绪；前端启动时调用，缺失则提示『数据未就绪』。"""
    status = data_status()
    return {"code": 200, "data": {**status, "query_backend": BACKEND_NAME}}


@router.get("/meta/boundary", summary="研究区边界 GeoJSON")
async def meta_boundary():
    """返回洪山区边界，前端用于绘制轮廓并自动定位。"""
    boundary = get_boundary()
    if boundary is None:
        raise HTTPException(404, "边界数据缺失")
    return {"code": 200, "data": {"boundary": boundary}}
