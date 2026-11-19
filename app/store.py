"""文档存储的端口（Protocol）与 SQLite 实现。

轻量六边形：documents.py（驱动适配器）只依赖 DocumentStore 协议，
换存储（SQLite → PostGIS 等）只改 SqliteDocumentStore 一处，
pytest 里也可以用 InMemoryDocumentStore 不碰磁盘。
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from .db import get_connection


class DocumentNotFoundError(KeyError):
    pass


class DocumentStore(Protocol):
    def list_documents(self) -> list[dict[str, Any]]: ...

    def get_document(self, document_id: str) -> dict[str, Any]: ...

    def create_document(self, name: str, payload: dict[str, Any]) -> dict[str, Any]: ...

    def update_document(self, document_id: str, name: str | None, payload: dict[str, Any]) -> dict[str, Any]: ...

    def delete_document(self, document_id: str) -> None: ...


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _row_to_meta(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


def _row_to_document(row: Any) -> dict[str, Any]:
    return {
        **_row_to_meta(row),
        "payload": json.loads(row["payload"]),
    }


class SqliteDocumentStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path

    def list_documents(self) -> list[dict[str, Any]]:
        with get_connection(self._db_path) as connection:
            rows = connection.execute(
                "SELECT id, name, created_at, updated_at FROM documents ORDER BY updated_at DESC"
            ).fetchall()
        return [_row_to_meta(row) for row in rows]

    def get_document(self, document_id: str) -> dict[str, Any]:
        with get_connection(self._db_path) as connection:
            row = connection.execute(
                "SELECT id, name, payload, created_at, updated_at FROM documents WHERE id = ?",
                (document_id,),
            ).fetchone()
        if row is None:
            raise DocumentNotFoundError(document_id)
        return _row_to_document(row)

    def create_document(self, name: str, payload: dict[str, Any]) -> dict[str, Any]:
        document_id = f"doc-{uuid.uuid4().hex[:12]}"
        now = _now()
        with get_connection(self._db_path) as connection:
            connection.execute(
                "INSERT INTO documents (id, name, payload, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (document_id, name, json.dumps(payload, ensure_ascii=False), now, now),
            )
        return {"id": document_id, "name": name, "createdAt": now, "updatedAt": now, "payload": payload}

    def update_document(self, document_id: str, name: str | None, payload: dict[str, Any]) -> dict[str, Any]:
        now = _now()
        with get_connection(self._db_path) as connection:
            row = connection.execute(
                "SELECT id, name, created_at FROM documents WHERE id = ?",
                (document_id,),
            ).fetchone()
            if row is None:
                raise DocumentNotFoundError(document_id)
            next_name = name if name is not None else row["name"]
            connection.execute(
                "UPDATE documents SET name = ?, payload = ?, updated_at = ? WHERE id = ?",
                (next_name, json.dumps(payload, ensure_ascii=False), now, document_id),
            )
        return {
            "id": document_id,
            "name": next_name,
            "createdAt": row["created_at"],
            "updatedAt": now,
            "payload": payload,
        }

    def delete_document(self, document_id: str) -> None:
        with get_connection(self._db_path) as connection:
            cursor = connection.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        if cursor.rowcount == 0:
            raise DocumentNotFoundError(document_id)


class InMemoryDocumentStore:
    """测试用假存储，验证端口设计的可替换性。"""

    def __init__(self) -> None:
        self._documents: dict[str, dict[str, Any]] = {}

    def list_documents(self) -> list[dict[str, Any]]:
        metas = [
            {key: value for key, value in doc.items() if key != "payload"}
            for doc in self._documents.values()
        ]
        return sorted(metas, key=lambda item: item["updatedAt"], reverse=True)

    def get_document(self, document_id: str) -> dict[str, Any]:
        if document_id not in self._documents:
            raise DocumentNotFoundError(document_id)
        return self._documents[document_id]

    def create_document(self, name: str, payload: dict[str, Any]) -> dict[str, Any]:
        document_id = f"doc-{uuid.uuid4().hex[:12]}"
        now = _now()
        document = {"id": document_id, "name": name, "createdAt": now, "updatedAt": now, "payload": payload}
        self._documents[document_id] = document
        return document

    def update_document(self, document_id: str, name: str | None, payload: dict[str, Any]) -> dict[str, Any]:
        if document_id not in self._documents:
            raise DocumentNotFoundError(document_id)
        current = self._documents[document_id]
        updated = {
            **current,
            "name": name if name is not None else current["name"],
            "payload": payload,
            "updatedAt": _now(),
        }
        self._documents[document_id] = updated
        return updated

    def delete_document(self, document_id: str) -> None:
        if document_id not in self._documents:
            raise DocumentNotFoundError(document_id)
        del self._documents[document_id]
