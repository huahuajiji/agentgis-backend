# AgentGIS 后端

AgentGIS（GIS 地图文档编辑器）的后端服务。为前端仓库 [`agentgis-frontend`](../agentgis-frontend) 提供：

- **文档持久化**：MapDocument JSON 的 CRUD（替换前端 localStorage）
- **空间分析**（阶段 3 第二刀）：buffer / overlay 两个算子，单端点 + operation 分发

## 技术栈

- Python 3.11+ · FastAPI · uvicorn
- SQLite（单文件，v1 不做数据库恢复机制）
- Shapely + pyproj（空间分析，4326 进出 / 3857 内部计算）
- pytest + httpx（接口测试）

**不引入**：LangGraph、记忆系统、RAG/向量库、Key 池。旧后端（rag-agent v0.7）的教训见项目文档。

## 依赖的前端契约

前端文档模型是单一的 Zod schema（`MapDocument`：viewport / layers / features / edit），本服务**原样存储**该 JSON，不拆字段、不重校验业务规则。

## API 契约（V1）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/documents` | 文档列表（只返回元数据：id / name / updatedAt） |
| GET | `/api/documents/{id}` | 单个文档（完整 MapDocument JSON） |
| POST | `/api/documents` | 新建（body: `{ name, payload }`） |
| PUT | `/api/documents/{id}` | 整体保存（body: `{ name?, payload }`） |
| DELETE | `/api/documents/{id}` | 删除 |
| POST | `/api/spatial/analysis` | 空间分析（`operation: buffer | overlay`） |
| GET | `/health` | 健康检查 |

错误统一结构：`{"error": {"code": "not_found", "message": "文档不存在"}}`

## 开发

```bash
python -m venv .venv && .venv/Scripts/activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
pytest
```

## 状态

**第一刀已完成（2026-11-19）**：FastAPI 骨架 + 文档 CRUD + 14 个 pytest 用例。

- `app/main.py` — 入口：CORS、统一错误结构 `{"error":{code,message}}`、`/health`
- `app/config.py` — 数据库路径与 CORS 来源（环境变量可覆盖）
- `app/db.py` — SQLite 连接与建表
- `app/store.py` — `DocumentStore` Protocol + `SqliteDocumentStore` 实现 + 测试用 `InMemoryDocumentStore`（轻量六边形：路由只依赖协议）
- `app/documents.py` — 五端点 CRUD
- `app/schemas.py` — 请求/响应模型（payload 不定义内部结构）
- `tests/test_documents.py` — 14 例：CRUD 往返 / 404 / 422 / 列表无 payload / 重启持久化 / 假存储契约

本地验证：`pytest` 14 passed；uvicorn 实跑 + curl 全链路（创建→列表→详情→更新→重启→删除→404）通过。

下一刀：前端接入（`agentgis-frontend` 持久化适配层，localStorage 降级保留）。第三刀：空间分析（buffer / overlay）。
