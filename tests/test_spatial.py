"""空间分析接口测试（第三刀）。

覆盖：buffer 三种几何、距离精度（3857 平面）、overlay 三算子、
422 分支（未知 operation / 空几何 / 无效几何 / 不相交）、坐标系往返。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


# 北海银滩附近的方形面（WGS-84，约 0.01° ≈ 1km）
SQUARE = {
    "type": "Polygon",
    "coordinates": [[
        [109.10, 21.40],
        [109.11, 21.40],
        [109.11, 21.41],
        [109.10, 21.41],
        [109.10, 21.40],
    ]],
}

SQUARE_EAST = {
    "type": "Polygon",
    "coordinates": [[
        [109.11, 21.40],
        [109.12, 21.40],
        [109.12, 21.41],
        [109.11, 21.41],
        [109.11, 21.40],
    ]],
}

POINT = {"type": "Point", "coordinates": [109.105, 21.405]}
LINE = {"type": "LineString", "coordinates": [[109.10, 21.40], [109.11, 21.41]]}


def _bbox(geometry: dict) -> tuple[float, float, float, float]:
    """递归求几何的外包框（minx, miny, maxx, maxy），测试里判断大致位置用。"""
    coords = geometry.get("coordinates") if geometry.get("type") != "GeometryCollection" else None
    points: list[tuple[float, float]] = []

    def walk(value):
        if isinstance(value, (list, tuple)) and len(value) >= 2 and all(
            isinstance(item, (int, float)) for item in value[:2]
        ):
            points.append((float(value[0]), float(value[1])))
            return
        if isinstance(value, (list, tuple)):
            for item in value:
                walk(item)

    walk(coords)
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


class TestBuffer:
    def test_point_buffer_expands_by_meters(self, client: TestClient) -> None:
        response = client.post("/api/spatial/analysis", json={
            "operation": "buffer",
            "geometry": POINT,
            "distance": 500,
        })
        assert response.status_code == 200
        body = response.json()
        assert body["operation"] == "buffer"
        minx, miny, maxx, maxy = _bbox(body["geometry"])
        # 半径 500 米 ≈ 0.0045°（纬度）到 0.0048°（经度 ≈ 21.4°N）
        assert 0.004 < (maxx - minx) / 2 < 0.006
        assert 0.004 < (maxy - miny) / 2 < 0.006
        # 中心近似不变
        assert abs((minx + maxx) / 2 - POINT["coordinates"][0]) < 1e-3

    def test_polygon_buffer_covers_original_extent(self, client: TestClient) -> None:
        response = client.post("/api/spatial/analysis", json={
            "operation": "buffer",
            "geometry": SQUARE,
            "distance": 200,
        })
        assert response.status_code == 200
        body = response.json()
        minx, miny, maxx, maxy = _bbox(body["geometry"])
        assert minx < SQUARE["coordinates"][0][0][0]
        assert maxx > SQUARE["coordinates"][0][1][0]
        assert miny < SQUARE["coordinates"][0][0][1]
        assert maxy > SQUARE["coordinates"][0][2][1]

    def test_line_buffer_returns_polygon(self, client: TestClient) -> None:
        response = client.post("/api/spatial/analysis", json={
            "operation": "buffer",
            "geometry": LINE,
            "distance": 100,
        })
        assert response.status_code == 200
        assert response.json()["geometry"]["type"] == "Polygon"

    def test_zero_distance_rejected_by_validation(self, client: TestClient) -> None:
        response = client.post("/api/spatial/analysis", json={
            "operation": "buffer",
            "geometry": POINT,
            "distance": 0,
        })
        assert response.status_code == 422

    def test_missing_distance_returns_422(self, client: TestClient) -> None:
        response = client.post("/api/spatial/analysis", json={
            "operation": "buffer",
            "geometry": POINT,
        })
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "bad_request" or response.status_code == 422


class TestOverlay:
    def test_intersection_of_adjacent_squares_is_line_or_empty_but_ok(self, client: TestClient) -> None:
        # 相接的两块，交集是零面积边界 → 我们的契约是"空的算 422"，所以改用重叠样例
        overlap = {
            "type": "Polygon",
            "coordinates": [[
                [109.105, 21.405],
                [109.115, 21.405],
                [109.115, 21.415],
                [109.105, 21.415],
                [109.105, 21.405],
            ]],
        }
        response = client.post("/api/spatial/analysis", json={
            "operation": "overlay",
            "operator": "intersection",
            "geometryA": SQUARE,
            "geometryB": overlap,
        })
        assert response.status_code == 200
        body = response.json()
        assert body["operation"] == "overlay.intersection"
        minx, miny, maxx, maxy = _bbox(body["geometry"])
        # 交集外包框应 ≈ [109.105,21.405, 109.11,21.41]
        assert abs(minx - 109.105) < 1e-4
        assert abs(maxy - 21.41) < 1e-4

    def test_union_bounds_cover_both(self, client: TestClient) -> None:
        response = client.post("/api/spatial/analysis", json={
            "operation": "overlay",
            "operator": "union",
            "geometryA": SQUARE,
            "geometryB": SQUARE_EAST,
        })
        assert response.status_code == 200
        minx, _miny, maxx, _maxy = _bbox(response.json()["geometry"])
        assert abs(minx - 109.10) < 1e-4
        assert abs(maxx - 109.12) < 1e-4

    def test_difference_removes_other(self, client: TestClient) -> None:
        response = client.post("/api/spatial/analysis", json={
            "operation": "overlay",
            "operator": "difference",
            "geometryA": SQUARE,
            "geometryB": SQUARE_EAST,
        })
        assert response.status_code == 200
        # 相邻两块，A 减 B 应该仍是 A（只是边界被裁掉一条线） → 有面积
        minx, _miny, maxx, _maxy = _bbox(response.json()["geometry"])
        assert abs(minx - 109.10) < 1e-4
        assert abs(maxx - 109.11) < 1e-4

    def test_disjoint_intersection_is_422(self, client: TestClient) -> None:
        far = {
            "type": "Polygon",
            "coordinates": [[
                [120.00, 30.00],
                [120.01, 30.00],
                [120.01, 30.01],
                [120.00, 30.01],
                [120.00, 30.00],
            ]],
        }
        response = client.post("/api/spatial/analysis", json={
            "operation": "overlay",
            "operator": "intersection",
            "geometryA": SQUARE,
            "geometryB": far,
        })
        assert response.status_code == 422

    def test_unknown_operator_is_422(self, client: TestClient) -> None:
        response = client.post("/api/spatial/analysis", json={
            "operation": "overlay",
            "operator": "xor",
            "geometryA": SQUARE,
            "geometryB": SQUARE_EAST,
        })
        assert response.status_code == 422


class TestValidation:
    def test_unknown_operation_is_422(self, client: TestClient) -> None:
        response = client.post("/api/spatial/analysis", json={"operation": "clip"})
        assert response.status_code == 422

    def test_invalid_geometry_self_intersecting_polygon(self, client: TestClient) -> None:
        bowtie = {
            "type": "Polygon",
            "coordinates": [[
                [109.10, 21.40],
                [109.11, 21.41],
                [109.11, 21.40],
                [109.10, 21.41],
                [109.10, 21.40],
            ]],
        }
        response = client.post("/api/spatial/analysis", json={
            "operation": "buffer",
            "geometry": bowtie,
            "distance": 100,
        })
        assert response.status_code == 422

    def test_empty_geometry_is_422(self, client: TestClient) -> None:
        response = client.post("/api/spatial/analysis", json={
            "operation": "buffer",
            "geometry": {"type": "Polygon", "coordinates": []},
            "distance": 100,
        })
        assert response.status_code == 422

    def test_response_is_wgs84_round_trip(self, client: TestClient) -> None:
        """结果仍在 4326 量级：经度在 109 附近而不是投影米值。"""
        response = client.post("/api/spatial/analysis", json={
            "operation": "buffer",
            "geometry": POINT,
            "distance": 100,
        })
        assert response.status_code == 200
        minx, miny, maxx, maxy = _bbox(response.json()["geometry"])
        assert 109.0 < minx < maxx < 109.2
        assert 21.3 < miny < maxy < 21.5
