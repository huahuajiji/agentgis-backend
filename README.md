# AgentGIS 后端

AgentGIS（GIS 地图文档编辑器）的后端服务。为前端仓库 [`agentgis-frontend`](https://github.com/huahuajiji/agentgis-frontend) 提供：

- **文档持久化**：MapDocument JSON 的 CRUD（替换前端 localStorage）—— **已实现**（第一刀）
- **空间分析**：buffer / overlay（交集/并集/差集）三算子，单端点 + operation 分发 —— **已实现**（第三刀，2026-11-26）

## 技术栈

当前已使用：

- Python 3.11+ · FastAPI · uvicorn
- SQLite（单文件，v1 不做数据库恢复机制）
- pytest + httpx（接口测试）

第三刀引入：Shapely + pyproj（空间分析，4326 进出 / 3857 内部计算，`run_in_threadpool` 防阻塞）。

**不引入**：LangGraph、记忆系统、RAG/向量库、Key 池。旧后端（rag-agent v0.7）的教训见项目文档。

## 依赖的前端契约

前端文档模型是单一的 Zod schema（`MapDocument`：viewport / layers / features / edit），本服务**原样存储**该 JSON，不拆字段、不重校验业务规则。

## API 契约（V1）

### 已实现（第一刀）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/documents` | 文档列表（只返回元数据：id / name / createdAt / updatedAt） |
| GET | `/api/documents/{id}` | 单个文档（完整 MapDocument JSON） |
| POST | `/api/documents` | 新建（body: `{ name, payload }`）→ 201 |
| PUT | `/api/documents/{id}` | 整体保存（body: `{ name?, payload }`） |
| DELETE | `/api/documents/{id}` | 删除 → 204 |
| GET | `/health` | 健康检查 |

### 空间分析（第三刀，已实现）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/spatial/analysis` | 空间分析单端点：`operation: buffer`（geometry + distance 米）或 `overlay`（operator: intersection/union/difference + geometryA/geometryB）；4326 进 4326 出，内部 3857 计算 |

422 语义：几何解析失败 / 自相交 / 空几何 / 运算结果为空（不相交）都返回 `invalid_geometry`。

错误统一结构：`{"error": {"code": "not_found", "message": "文档不存在"}}`

## 开发

```bash
python -m venv .venv && .venv/Scripts/activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
pytest
```

## 部署

线上运行在 Hugging Face Spaces（Docker，端口 7860），Space 内容由 `space/sync.ps1`
从本仓库同步。完整步骤、CORS 与存储说明见 [docs/DEPLOY.md](docs/DEPLOY.md)。

## 状态

**第一刀已完成（2026-11-19）**：FastAPI 骨架 + 文档 CRUD + 14 个 pytest 用例。

- `app/main.py` — 入口：CORS、统一错误结构 `{"error":{code,message}}`、`/health`
- `app/config.py` — 数据库路径与 CORS 来源（环境变量可覆盖）
- `app/db.py` — SQLite 连接与建表
- `app/store.py` — `DocumentStore` Protocol + `SqliteDocumentStore` 实现 + 测试用 `InMemoryDocumentStore`（轻量六边形：路由只依赖协议）
- `app/documents.py` — 五端点 CRUD
- `app/spatial.py` — 空间分析单端点：buffer / overlay 分发，Shapely + pyproj，几何校验与 422 归一化
- `app/schemas.py` — 请求/响应模型（payload 不定义内部结构）
- `tests/test_documents.py` — 14 例：CRUD 往返 / 404 / 422 / 列表无 payload / 重启持久化 / 假存储契约
- `tests/test_spatial.py` — 14 例：buffer 三种几何与距离精度 / overlay 三算子 / 422（未知 operation、空几何、自相交、不相交）/ WGS-84 往返

本地验证：`pytest` 28 passed；uvicorn 实跑 + curl 全链路（创建→列表→详情→更新→重启→删除→404；空间分析 buffer/overlay/422）通过。

前端接入：手动同步（拉取 / 上传）+ 空间分析工具坞已接（分析模式下选要素 → 缓冲区/叠加 → 结果进新图层）。测试 14 → 28 例。
