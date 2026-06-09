# Handoff: V2 架构改进 + 阿里云部署

**日期**: 2026-06-09
**分支**: `HSV`
**最新 commit**: `9e5bf1e` (已推送)

---

## 完成了什么

### 1. 仓库清理 (`2192fdf`)
- 根目录 7 个工具脚本移至 `scripts/` 目录
- 删除过时的 `docs/Temp/`、`results/yolo_results_20260522/`、`git_status.txt`
- `.gitignore` 修复：去重 `__pycache__/`、补末尾换行
- 新建 `scripts/README.md` + `scripts/server_manager.py`（SSH 密钥管理工具）

### 2. 阿里云 ECS 部署
- **前端** `http://120.27.15.235` — Vue3 SPA，nginx 托管，SPA fallback 已配置
- **后端** 轻量 FastAPI — systemd `algae-image.service`，端口 8000
- **架构**: nginx → `/` Vue3 静态文件, `/api/v1/*` 反向代理 FastAPI
- **资源占用**: 内存 ~330MB / 1.6GB，磁盘 8.6GB / 40GB

服务器详情见 [[aliyun-ecs-deployment]] memory。

### 3. 安全修复 (`384d092`, `a94457e`)
- `server_manager.py`: AutoAddPolicy → RejectPolicy + load_system_host_keys
- `server_light.py`: 文件后缀白名单校验、错误信息脱敏

### 4. 架构改进 (`9e5bf1e`)
按照用户确认的优先级（[[architecture-pragmatism]]）：

**#1 共享 Schemas**:
- 新建 `shared/schemas.py` — 12 个 Pydantic 模型的唯一定义处
- `backend/app/schemas.py` → re-export from shared
- `deploy/server_light.py` → import from shared（不再重复定义）

**#3 拆分路由**:
- `backend/app/routes.py` — 仅保留检测端点（需 torch/cv2）
- `backend/app/routes_data.py` — 仪表板 + 历史 CRUD（零 ML 依赖，可独立 import）

**#4 Config 边界**:
- `backend/app/config.py` 和 `core_engine/config.py` 各加 docstring 声明职责

### 5. Memory 更新
- `aliyun-ecs-deployment` — 服务器连接信息
- `architecture-pragmatism` — 用户架构偏好的 Why/How

---

## 当前状态

| 组件 | 位置 | 状态 |
|------|------|------|
| Vue3 前端 | `/www/wwwroot/algae_image/` | ✅ 运行中 |
| 轻量 API | `/opt/algae_image/server_light.py` | ✅ systemd 托管 |
| Shared schemas | `/opt/algae_image/shared/schemas.py` | ✅ 已同步 |
| Git | `origin/HSV` @ `9e5bf1e` | ✅ 已推送 |

---

## 部署命令（备忘）

```bash
# 更新前端
scp -r code/algae_image_v2/frontend/dist/* aliyun-ecs:/www/wwwroot/algae_image/

# 更新后端（含 shared schemas）
scp code/algae_image_v2/deploy/server_light.py aliyun-ecs:/opt/algae_image/
scp code/algae_image_v2/shared/schemas.py aliyun-ecs:/opt/algae_image/shared/
ssh aliyun-ecs "systemctl restart algae-image"
```

---

## 未完成的架构候选

用户在架构审查中选择了 #1、#3、#4。以下被明确跳过：

- **#2 分离 PipelineRunner 可视化逻辑** — 用户说"没有测试需求"，不做

---

## 建议 Skills

新会话接手时建议加载：
- `superpowers:brainstorming` — 如需继续架构讨论
- `superpowers:requesting-code-review` — 代码改动后审查
- `skill-creator:skill-creator` — 如需为部署流程创建 skill
