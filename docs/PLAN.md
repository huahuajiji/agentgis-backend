# AgentGIS 后端 · 规划与刀次记录

> 本文件起初是阶段 3 开始前的布局占位说明，第一刀落地后改为「规划 + 刀次记录」。
> 最后更新：2026-11-24。**以 README 与代码为准，本文件只记录规划和历史。**

## 状态一览

| 刀次 | 内容 | 状态 |
|---|---|---|
| 第一刀 | FastAPI 骨架 + 文档 CRUD + 14 例 pytest | ✅ 2026-11-19 |
| 第二刀 | 前端持久化适配层接后端 | 前端仓库进行中（后端无需改动） |
| 第三刀 | 空间分析 `POST /api/spatial/analysis`（buffer / overlay） | ✅ 2026-11-26，`app/spatial.py` + 14 例测试 |

## 实际结构（第一刀落地后）

```
agentgis-backend/
├── app/
│   ├── main.py            # FastAPI 实例：CORS、统一错误结构、路由注册、/health
│   ├── config.py          # 数据库路径与 CORS 来源（环境变量优先）
│   ├── db.py              # SQLite 连接与建表
│   ├── store.py           # DocumentStore Protocol + SqliteDocumentStore + InMemoryDocumentStore
│   ├── documents.py       # 五个端点：列表 / 读单个 / 新建 / 整体保存 / 删除
│   └── schemas.py         # 请求 / 响应模型（payload 即前端 MapDocument JSON）
├── tests/
│   └── test_documents.py  # pytest + httpx：CRUD 全链路
├── docs/PLAN.md           # 本文件
└── requirements.txt       # fastapi / uvicorn / pytest / httpx（不含 langgraph 等）
```

与最初规划的差异：`store.py` 是规划外的拆分（轻量六边形——路由只依赖 `DocumentStore` 协议，SQLite 实现可替换、测试可用内存实现），已落地并有 14 例测试覆盖。

## 契约（V1，已确定）

已实现（第一刀）：

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/documents` | 文档列表（只返回元数据，不扛全量 JSON） |
| GET | `/api/documents/{id}` | 单个文档（完整 MapDocument JSON） |
| POST | `/api/documents` | 新建 → 201 |
| PUT | `/api/documents/{id}` | 整体保存（前端文档模型原样上传；全量覆盖，不做增量） |
| DELETE | `/api/documents/{id}` | 删除 → 204 |
| GET | `/health` | 健康检查 |

错误统一为 `{"error": {"code", "message"}}`。

已实现（第三刀）：空间分析 `POST /api/spatial/analysis`（buffer / overlay），4326 进 4326 出、内部转 3857 用 Shapely；算子写纯函数、分发处注册一行。

## 与旧后端（`aigc/rag-agent（后端）/vision/v0.7`）的关系

旧后端里 `app/api/project_api.py` 的 CRUD 形状与 `json_project_store.py` 的"列表只返回元数据"策略可借鉴；其数据模型（title / features 为 list、自有 op 类型）与现前端 Zod MapDocument 不兼容，代码不直接移植。LangGraph / 记忆 / RAG / Qdrant 一律不引入。
