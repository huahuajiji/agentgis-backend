"""SQLite 连接与建表。

V1 只有一张 documents 表：payload 存前端 MapDocument 的完整 JSON 原样，
后端不拆字段、不做业务校验。
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .config import database_path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    """打开连接并确保表存在。每次请求一条连接，FastAPI 下单线程使用足够。"""
    path = db_path or database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.executescript(_SCHEMA)
    return connection


@contextmanager
def get_connection(db_path: Path | None = None):
    connection = connect(db_path)
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()
