"""文档路由：五个 CRUD 端点。

只依赖 DocumentStore 协议（通过 Depends 注入），不知道存储实现。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .schemas import CreateDocumentRequest, DocumentDetail, DocumentMeta, UpdateDocumentRequest
from .store import DocumentNotFoundError, DocumentStore, SqliteDocumentStore


def get_store() -> DocumentStore:
    return SqliteDocumentStore()


router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("", response_model=list[DocumentMeta])
def list_documents(store: DocumentStore = Depends(get_store)) -> list[dict]:
    return store.list_documents()


@router.post("", response_model=DocumentDetail, status_code=201)
def create_document(
    request: CreateDocumentRequest,
    store: DocumentStore = Depends(get_store),
) -> dict:
    return store.create_document(request.name, request.payload)


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(document_id: str, store: DocumentStore = Depends(get_store)) -> dict:
    try:
        return store.get_document(document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="文档不存在") from exc


@router.put("/{document_id}", response_model=DocumentDetail)
def update_document(
    document_id: str,
    request: UpdateDocumentRequest,
    store: DocumentStore = Depends(get_store),
) -> dict:
    try:
        return store.update_document(document_id, request.name, request.payload)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="文档不存在") from exc


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: str, store: DocumentStore = Depends(get_store)) -> None:
    try:
        store.delete_document(document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="文档不存在") from exc
