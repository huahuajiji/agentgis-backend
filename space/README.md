---
title: AgentGIS Backend
emoji: 🗺️
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# AgentGIS 后端

AgentGIS（GIS 地图文档编辑器）的后端服务，为前端
[agentgis-frontend](https://github.com/huahuajiji/agentgis-frontend) 提供文档持久化与空间分析。

源码与开发文档在 GitHub 主仓库：
[agentgis-backend](https://github.com/huahuajiji/agentgis-backend)。

## 接口

- `GET /health`
- `GET|POST /api/documents`、`GET|PUT|DELETE /api/documents/{id}`
- `POST /api/spatial/analysis`（buffer / overlay）

## 部署说明

本 Space 由脚本从 GitHub 仓库同步（见主仓库 `docs/DEPLOY.md`），不要直接在此编辑代码。

免费容器的磁盘是临时的：容器重启（含闲置休眠后唤醒）后 SQLite 数据会重置。
需要长期保留数据时，在 Space 设置里开启 Persistent storage（付费），存储路径已是 `/data`。
