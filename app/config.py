"""应用配置：全部可通过环境变量覆盖，本地开发零配置即可启动。"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = BASE_DIR / "data"


def database_path() -> Path:
    """SQLite 文件路径。AGENTGIS_DB_PATH 可覆盖（测试用临时文件）。"""
    configured = os.environ.get("AGENTGIS_DB_PATH")
    if configured:
        return Path(configured)
    return DEFAULT_DATA_DIR / "agentgis.db"


def cors_origins() -> list[str]:
    """允许的前端来源。AGENTGIS_CORS_ORIGINS 逗号分隔；默认本地 Vite 开发端口。"""
    configured = os.environ.get("AGENTGIS_CORS_ORIGINS", "")
    if configured.strip():
        return [origin.strip() for origin in configured.split(",") if origin.strip()]
    return [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]
