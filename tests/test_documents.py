"""文档 CRUD 接口测试。

覆盖：CRUD 全链路、404、校验错误、payload 原样往返（中文/嵌套）、
列表不含 payload、重启（新实例）后数据仍在。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.store import InMemoryDocumentStore, SqliteDocumentStore


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test-agentgis.db"


@pytest.fixture()
def client(db_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("AGENTGIS_DB_PATH", str(db_path))
    # get_store() 在请求时调用 database_path()，monkeypatch 环境变量即生效
    return TestClient(app)


SAMPLE_PAYLOAD = {
    "kind": "draft",
    "name": "测试地图",
    "viewport": {"center": [108.4177, 22.8416], "zoom": 13, "bounds": None},
    "layers": [
        {
            "id": "layer-1",
            "name": "导入图层 · 点",
            "role": "work",
            "geometryType": "point",
            "visible": True,
            "locked": False,
            "order": 0,
            "featureIds": ["feature-1"],
            "style": {},
            "imageResources": [],
        }
    ],
    "features": {
        "feature-1": {
            "id": "feature-1",
            "layerId": "layer-1",
            "geojson": {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [108.4, 22.8]},
                "properties": {"名称": "青秀山", "等级": "5A"},
            },
            "imageResourceId": None,
        }
    },
}


def create_sample(client: TestClient) -> dict:
    response = client.post("/api/documents", json={"name": "测试地图", "payload": SAMPLE_PAYLOAD})
    assert response.status_code == 201
    return response.json()


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_returns_document_detail(client: TestClient) -> None:
    body = create_sample(client)
    assert body["id"].startswith("doc-")
    assert body["name"] == "测试地图"
    assert body["payload"] == SAMPLE_PAYLOAD
    assert body["createdAt"] and body["updatedAt"]


def test_payload_roundtrip_keeps_chinese_and_nested(client: TestClient) -> None:
    created = create_sample(client)
    fetched = client.get(f"/api/documents/{created['id']}").json()
    assert fetched["payload"] == SAMPLE_PAYLOAD
    # 中文属性与坐标数值都要原样
    feature = fetched["payload"]["features"]["feature-1"]
    assert feature["geojson"]["properties"]["名称"] == "青秀山"
    assert feature["geojson"]["geometry"]["coordinates"] == [108.4, 22.8]


def test_list_returns_meta_without_payload(client: TestClient) -> None:
    create_sample(client)
    items = client.get("/api/documents").json()
    assert len(items) == 1
    assert "payload" not in items[0]
    assert set(items[0].keys()) == {"id", "name", "createdAt", "updatedAt"}


def test_update_overwrites_payload_and_name(client: TestClient) -> None:
    created = create_sample(client)
    new_payload = {**SAMPLE_PAYLOAD, "name": "改名后的地图"}
    response = client.put(
        f"/api/documents/{created['id']}",
        json={"name": "改名后的地图", "payload": new_payload},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "改名后的地图"
    fetched = client.get(f"/api/documents/{created['id']}").json()
    assert fetched["payload"]["name"] == "改名后的地图"


def test_update_keeps_name_when_omitted(client: TestClient) -> None:
    created = create_sample(client)
    response = client.put(
        f"/api/documents/{created['id']}",
        json={"payload": {**SAMPLE_PAYLOAD, "name": "只改内容"}},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "测试地图"


def test_get_missing_returns_404_with_error_shape(client: TestClient) -> None:
    response = client.get("/api/documents/doc-nope")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "not_found"
    assert "不存在" in body["error"]["message"]


def test_update_missing_returns_404(client: TestClient) -> None:
    response = client.put("/api/documents/doc-nope", json={"payload": {}})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_delete_then_get_returns_404(client: TestClient) -> None:
    created = create_sample(client)
    response = client.delete(f"/api/documents/{created['id']}")
    assert response.status_code == 204
    assert client.get(f"/api/documents/{created['id']}").status_code == 404


def test_delete_missing_returns_404(client: TestClient) -> None:
    response = client.delete("/api/documents/doc-nope")
    assert response.status_code == 404


def test_create_with_empty_name_is_rejected(client: TestClient) -> None:
    response = client.post("/api/documents", json={"name": "", "payload": {}})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_create_without_payload_is_rejected(client: TestClient) -> None:
    response = client.post("/api/documents", json={"name": "无载荷"})
    assert response.status_code == 422


def test_data_survives_new_connection(client: TestClient, db_path: Path) -> None:
    created = create_sample(client)
    # 新开一个 store 实例（模拟服务重启后新的连接）
    store = SqliteDocumentStore(db_path)
    fetched = store.get_document(created["id"])
    assert fetched["payload"] == SAMPLE_PAYLOAD


def test_in_memory_store_satisfies_same_contract() -> None:
    store = InMemoryDocumentStore()
    created = store.create_document("内存文档", {"hello": "世界"})
    assert store.get_document(created["id"])["payload"] == {"hello": "世界"}
    metas = store.list_documents()
    assert "payload" not in metas[0]
    store.update_document(created["id"], None, {"hello": "更新"})
    assert store.get_document(created["id"])["name"] == "内存文档"
    store.delete_document(created["id"])
    with pytest.raises(Exception):
        store.get_document(created["id"])
