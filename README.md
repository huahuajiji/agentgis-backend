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

阶段 3 第一刀尚未开始（骨架 + 文档 CRUD）。目录结构规划见 `docs/PLAN.md`。
