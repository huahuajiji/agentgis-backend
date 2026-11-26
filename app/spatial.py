"""空间分析：单端点 + operation 分发（第三刀）。

契约（docs/PLAN.md 与前端 mapDocumentAnalysis 一致）：
- 输入输出都是 GeoJSON 几何，坐标系 WGS-84（EPSG:4326，方案 B 后前端统一）；
- 内部转 EPSG:3857 做平面计算，距离单位米；
- buffer 与 overlay（intersection / union / difference）两组算子；
- 算子写成一个纯函数放在模块底部，分发处注册一行，加新算子只改这两处。

计算是 CPU 密集的，路由用 run_in_threadpool 包一层，避免阻塞事件循环。
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pyproj import Transformer
from pydantic import BaseModel, Field
from shapely.errors import GEOSException
from shapely.geometry import mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform as shapely_transform

router = APIRouter(prefix="/api/spatial", tags=["spatial"])


class InvalidGeometryError(ValueError):
    """输入几何无法解析或运算失败（→ 422 invalid_geometry）。"""


class AnalysisRequest(BaseModel):
    """单端点请求：按 operation 字段分发（Literal 保证未知 operation 得到 422）。"""

    operation: Literal["buffer", "overlay"]
    geometry: dict[str, Any] | None = None
    distance: float | None = Field(default=None, gt=0, le=100_000)
    segments: int = Field(default=64, ge=8, le=256)
    operator: Literal["intersection", "union", "difference"] | None = None
    geometryA: dict[str, Any] | None = None
    geometryB: dict[str, Any] | None = None


class AnalysisResponse(BaseModel):
    operation: str
    geometry: dict[str, Any]


_TO_WEB = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
_TO_WGS = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)


def _parse_geometry(raw: dict[str, Any]) -> BaseGeometry:
    try:
        geometry = shape(raw)
    except Exception as exc:  # noqa: BLE001 - shapely 的异常类型随版本变化，统一归一化
        raise InvalidGeometryError(f"无法解析几何：{exc}") from exc
    if geometry.is_empty:
        raise InvalidGeometryError("几何为空")
    if not geometry.is_valid:
        raise InvalidGeometryError("几何无效（自相交或环方向错误）")
    return geometry


def _to_web(geometry: BaseGeometry) -> BaseGeometry:
    return shapely_transform(_TO_WEB.transform, geometry)


def _to_wgs(geometry: BaseGeometry) -> BaseGeometry:
    return shapely_transform(_TO_WGS.transform, geometry)


def _run_buffer(geometry: BaseGeometry, distance: float, segments: int) -> BaseGeometry:
    return _to_web(geometry).buffer(distance, quad_segs=segments)


def _run_overlay(operator: str, a: BaseGeometry, b: BaseGeometry) -> BaseGeometry:
    web_a, web_b = _to_web(a), _to_web(b)
    if operator == "intersection":
        return web_a.intersection(web_b)
    if operator == "union":
        return web_a.union(web_b)
    if operator == "difference":
        return web_a.difference(web_b)
    raise InvalidGeometryError(f"未知的 overlay 算子：{operator}")


# ── 算子注册表：加算子在这里加一行 ────────────────────────────────


def _dispatch(request: AnalysisRequest) -> tuple[str, BaseGeometry]:
    if request.operation == "buffer":
        if request.geometry is None:
            raise InvalidGeometryError("buffer 需要 geometry")
        if request.distance is None:
            raise InvalidGeometryError("buffer 需要 distance（米）")
        result = _run_buffer(_parse_geometry(request.geometry), request.distance, request.segments)
        return "buffer", result

    if request.operation == "overlay":
        if request.operator is None:
            raise InvalidGeometryError("overlay 需要 operator")
        if request.geometryA is None or request.geometryB is None:
            raise InvalidGeometryError("overlay 需要 geometryA 与 geometryB")
        result = _run_overlay(
            request.operator,
            _parse_geometry(request.geometryA),
            _parse_geometry(request.geometryB),
        )
        return f"overlay.{request.operator}", result

    raise InvalidGeometryError(f"未知的 operation：{request.operation}")


def analyze_sync(request: AnalysisRequest) -> AnalysisResponse:
    """同步执行一次分析（测试直接调用，路由经线程池调用）。"""
    label, result = _dispatch(request)
    if result.is_empty:
        raise InvalidGeometryError("运算结果为空（例如两个几何不相交）")
    wgs_geometry = _to_wgs(result)
    coordinates = mapping(wgs_geometry)
    return AnalysisResponse(operation=label, geometry=dict(coordinates))


@router.post("/analysis", response_model=AnalysisResponse)
async def run_analysis(request: AnalysisRequest) -> AnalysisResponse:
    try:
        return await run_in_threadpool(analyze_sync, request)
    except InvalidGeometryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except GEOSException as exc:
        raise HTTPException(status_code=422, detail=f"几何运算失败：{exc}") from exc
