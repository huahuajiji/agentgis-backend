"""文档 CRUD 的请求 / 响应模型。

payload 是前端 MapDocument 的完整 JSON，后端不定义其内部结构。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CreateDocumentRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    payload: dict[str, Any]


class UpdateDocumentRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    payload: dict[str, Any]


class DocumentMeta(BaseModel):
    id: str
    name: str
    createdAt: str
    updatedAt: str


class DocumentDetail(DocumentMeta):
    payload: dict[str, Any]
