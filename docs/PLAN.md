# AgentGIS 后端

> 阶段 3 开始时在这里创建。当前目录只有本说明，是布局占位。

## 规划结构（第一刀）

```
backend/
├── app/
│   ├── main.py            # FastAPI 实例：CORS、统一错误结构、路由注册、/health
│   ├── config.py          # 数据库路径等配置（环境变量优先）
│   ├── db.py              # SQLite 连接与建表（documents: id / name / payload / updatedAt）
│   ├── documents.py       # 五个端点：列表 / 读单个 / 新建 / 整体保存 / 删除
│   └── schemas.py         # 请求 / 响应模型（payload 即前端 MapDocument JSON）
├── tests/
│   └── test_documents.py  # pytest + httpx：CRUD 全链路
├── requirements.txt       # fastapi / uvicorn / pytest / httpx（不含 langgraph 等）
└── README.md
```

## 契约（V1，已确定）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/documents` | 文档列表（只返回元数据，不扛全量 JSON） |
| GET | `/api/documents/{id}` | 单个文档（完整 MapDocument JSON） |
| POST | `/api/documents` | 新建 |
| PUT | `/api/documents/{id}` | 整体保存（前端文档模型原样上传） |
| DELETE | `/api/documents/{id}` | 删除 |

错误统一为 `{"error": {"code", "message"}}`。

后续刀次在此追加：空间分析 `POST /api/spatial/analysis`（buffer / overlay）。

## 与旧后端（`aigc/rag-agent（后端）/vision/v0.7`）的关系

旧后端里 `app/api/project_api.py` 的 CRUD 形状与 `json_project_store.py` 的"列表只返回元数据"策略可借鉴；其数据模型（title / features 为 list、自有 op 类型）与现前端 Zod MapDocument 不兼容，代码不直接移植。LangGraph / 记忆 / RAG / Qdrant 一律不引入。
