"""FastAPI 入口：CORS、统一错误结构、路由注册、健康检查。"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import cors_origins
from .documents import router as documents_router
from .spatial import router as spatial_router

app = FastAPI(
    title="AgentGIS 后端",
    version="0.1.0",
    description="AgentGIS 地图文档持久化服务（阶段 3 第一刀：文档 CRUD）。",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = {404: "not_found", 400: "bad_request"}.get(exc.status_code, "error")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": code, "message": str(exc.detail)}},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "validation_error", "message": "请求参数不合法"}},
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "agentgis-backend", "version": "0.1.0"}


app.include_router(documents_router)
app.include_router(spatial_router)
