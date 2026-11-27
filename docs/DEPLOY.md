# AgentGIS 部署

两个目标：

| 部分 | 平台 | 地址 |
|---|---|---|
| 前端 | GitHub Pages | `https://huahuajiji.github.io/agentgis/` |
| 后端 | Hugging Face Spaces（Docker） | `https://huahuajiji-agentgis-backend.hf.space` |

## 前端（GitHub Pages）

配置已在仓库里（`.github/workflows/deploy.yml` + `vite.config.ts` 的 `VITE_BASE`），
一次性设置只有两处：

1. 仓库 Settings → Pages → Source 选 **GitHub Actions**。
2. 仓库 Settings → Secrets and variables → **Actions → Variables** 新增
   `VITE_API_BASE_URL`，值为后端地址（HF Space 域名）。

之后每次 push 到 `main` 自动跑：测试 → 类型检查 → 构建 → 发布。
仓库变量缺失时工作流会主动失败，避免发布连不上后端的版本。

## 后端（Hugging Face Spaces）

Space 使用 Docker SDK，端口 7860，本仓库根目录的 `Dockerfile` 即部署描述。
SQLite 指向 `/data`（`AGENTGIS_DB_PATH`），免费容器不持久，重启后数据重置。

### 首次创建

1. huggingface.co → New Space → Docker → 名称 `agentgis-backend`，公开。
2. 用脚本把本仓库代码同步过去（不依赖 HF 的 GitHub 集成）：

   Windows PowerShell：

   ```powershell
   # 首次：把 Space 加为 git remote（替换为你的用户名）
   git remote add space https://huggingface.co/spaces/huahuajiji/agentgis-backend
   # 推送（HF 要用户名 + access token 作密码）
   cd C:\Users\32083\aigc\webgis\fristwebgis\agentgis-backend
   .\space\sync.ps1
   ```

3. Space 构建完成后访问 `https://huahuajiji-agentgis-backend.hf.space/health` 应返回
   `{"status":"ok",...}`。

### 之后每次更新

代码在 GitHub 提交后，再跑一次 `.\space\sync.ps1`。Space 上的提交历史只是部署产物，
不作为开发主线。

### CORS

Space 的环境变量（Settings → Variables and secrets）设置
`AGENTGIS_CORS_ORIGINS`，逗号分隔：

```
https://huahuajiji.github.io,http://127.0.0.1:5173
```

默认只放行本地 5173，不配置的话 Pages 上的前端会被浏览器拦掉。

### 存储

免费 CPU Basic 的磁盘随容器重建而清空。需要跨重启保留文档时开启 Paid
Persistent storage（挂载 `/data`，代码已按此路径配置），无需改代码。

## 验证清单（上线后）

- Pages 打开不白屏，hash 路由跳转正常（`/#/map`）
- 账户弹窗填高德 Key → 底图加载
- 画一个面 → 打包 → 同步到云端 → 无痕窗口拉取 → 要素还在
- 分析模式选中面 → 缓冲区 500 米 → 结果出现在新图层
