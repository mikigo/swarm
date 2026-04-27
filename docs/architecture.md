# Swarm 架构设计文档

## 1. 架构概述

### 1.1 设计目标

Swarm 是一个分布式自动化测试执行框架，采用 **微服务架构** 模式，服务端和客户端独立部署，通过 HTTP 和 WebSocket 进行通信。

核心设计原则：
- **高可用**：客户端支持断线重连，心跳检测
- **可扩展**：支持多客户端并发，任务自动负载均衡
- **易部署**：单包安装，内网可用，无外网依赖
- **可调试**：保持 pytest 原生输出，调试友好

### 1.2 系统组件

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Swarm 系统                                  │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                         服务端 (Server)                          │   │
│  │                                                                  │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │   │
│  │  │  FastAPI    │  │  WebSocket  │  │    Task Manager        │  │   │
│  │  │  (HTTP)     │  │  (WS)       │  │    - 任务创建          │  │   │
│  │  │             │  │             │  │    - 用例收集          │  │   │
│  │  └─────────────┘  └─────────────┘  │    - 分发调度          │  │   │
│  │           │              │         │    - 结果汇总          │  │   │
│  │           └──────────────┬─────────┘                         │  │   │
│  │                          │                                   │  │   │
│  │  ┌─────────────┐  ┌─────┴────────┐  ┌─────────────────────────┐  │   │
│  │  │  File       │  │  Client      │  │    Report Generator    │  │   │
│  │  │  Storage    │  │  Registry    │  │    - Allure JSON 汇总  │  │   │
│  │  │             │  │  - 注册      │  │    - HTML 生成         │  │   │
│  │  │             │  │  - 心跳      │  │                         │  │   │
│  │  └─────────────┘  └──────────────┘  └─────────────────────────┘  │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                          HTTP / WebSocket                              │
│                                    │                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                         客户端 (Client)                          │   │
│  │                                                                  │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │   │
│  │  │  WebSocket  │  │  Task       │  │    Executor            │  │   │
│  │  │  Client     │  │  Receiver   │  │    - Git Clone         │  │   │
│  │  │             │  │             │  │    - 虚拟环境          │  │   │
│  │  └─────────────┘  └─────────────┘  │    - pytest 执行       │  │   │
│  │           │              │         │    - 结果上传          │  │   │
│  │           └──────────────┴─────────┘                         │  │   │
│  │                          │                                   │  │   │
│  │  ┌─────────────────────────────────────────────────────────┐  │   │
│  │  │              Task Runner                                 │  │   │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │  │   │
│  │  │  │Git Clone │→ │  VEnv    │→ │  Pytest  │→ │  Upload  │ │  │   │
│  │  │  │ 代码同步 │  │ 环境创建  │  │ 执行测试  │  │ 结果上传 │ │  │   │
│  │  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │  │   │
│  │  └─────────────────────────────────────────────────────────┘  │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 通信设计

### 2.1 端口分配

| 服务 | 默认端口 | 可配置 | 说明 |
|------|----------|--------|------|
| 服务端 | 8000 | 是 | HTTP + WebSocket 统一入口 |
| 客户端 | 8001 | 是 | 仅用于客户端间区分，无实际监听 |

### 2.2 HTTP API

所有非实时操作通过 HTTP 处理：

```
POST   /api/tasks              # 创建任务
GET    /api/tasks              # 任务列表
GET    /api/tasks/{task_id}    # 任务详情
DELETE /api/tasks/{task_id}    # 取消任务
POST   /api/tasks/{task_id}/retry   # 重试任务
GET    /api/tasks/{task_id}/results # 任务结果
POST   /api/tasks/{task_id}/upload  # 上传 Allure 结果
GET    /api/clients            # 客户端列表
GET    /api/clients/{client_id}     # 客户端详情
GET    /api/reports/{task_id}       # 访问 Allure 报告
GET    /docs                    # Swagger 文档
GET    /openapi.json            # OpenAPI schema
```

### 2.3 WebSocket 通道

实时通信使用 WebSocket，路径：`/ws/{client_id}`

#### 2.3.1 客户端 → 服务端消息

| 消息类型 | 用途 | 格式 |
|----------|------|------|
| `register` | 注册 | `{"action": "register", "hostname": "...", "ip": "...", ...}` |
| `heartbeat` | 心跳 | `{"action": "heartbeat"}` |
| `next` | 请求下一个任务 | `{"action": "next", "task_id": "xxx", "result": {...}}` |
| `log` | 推送日志 | `{"action": "log", "message": "..."}` |

#### 2.3.2 服务端 → 客户端消息

| 消息类型 | 用途 | 格式 |
|----------|------|------|
| `registered` | 注册确认 | `{"action": "registered", "client_id": "xxx"}` |
| `task` | 下发任务 | `{"action": "task", "task_id": "xxx", "test_file": "..."}` |
| `cancel` | 取消任务 | `{"action": "cancel", "task_id": "xxx"}` |

### 2.4 双向通信原理

由于采用**反向连接**模式（客户端主动连接服务端），服务端可以：
1. 通过已有的 WebSocket 连接向客户端推送任务
2. 客户端通过同一连接推送日志和请求下一个任务

```
┌──────────────┐                      ┌──────────────┐
│   服务端      │                      │   客户端      │
│              │                      │              │
│  WebSocket   │◄────── 连接 ────────►│  WebSocket   │
│   Server     │    (保持长连接)       │   Client     │
│              │                      │              │
│              │◄────── 推送日志 ─────│              │
│              │                      │              │
│ ──────推送任务─────►                 │              │
│              │                      │              │
└──────────────┘                      └──────────────┘
```

---

## 3. 任务调度设计

### 3.1 分布式调度模型

Swarm 采用 **集中式调度** 模式：

```
┌─────────────────────────────────────────────────────────────────┐
│                        服务端                                    │
│                                                                  │
│   ┌────────────────────────────────────────────────────────┐   │
│   │                   Task Queue                            │   │
│   │   [test_a.py, test_b.py, test_c.py, test_d.py, ...]    │   │
│   │                        ↑                                │   │
│   │                        │ pop                            │   │
│   │                    ┌───┴───┐                            │   │
│   │                    │       │                            │   │
│   └────────────────────│ 调度器 ├────────────────────────────┘   │
│                        │       │                                    │
│                        └───┬───┘                                    │
│                            │ push                                   │
│                            ↓                                        │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │         空闲客户端             │
              │   Client-1   Client-2   ...   │
              └──────────────────────────────┘
```

### 3.2 调度算法

```python
# 伪代码：任务分发逻辑
def dispatch_task():
    # 1. 获取空闲客户端
    idle_clients = get_idle_clients()  # status=online, no current_task
    
    if not idle_clients:
        # 无空闲客户端，等待
        return
    
    # 2. 获取待执行任务
    task = get_next_pending_task()
    if not task:
        return
    
    # 3. 获取下一个待执行文件
    test_file = task.pop_next_file()
    if not test_file:
        return
    
    # 4. 分配给客户端
    client = idle_clients[0]
    client.current_task = task.id
    
    # 5. 推送任务到客户端
    ws_client = get_ws_client(client.id)
    ws_client.send({
        "action": "task",
        "task_id": task.id,
        "test_file": test_file,
        "branch": task.branch,
        "client_args": task.client_args
    })
```

### 3.3 状态机

#### 3.3.1 任务状态

```
                    ┌──────────┐
                    │ pending  │
                    └────┬─────┘
                         │ 创建
                         ▼
┌──────────┐      ┌──────────┐      ┌──────────┐
│ cancelled│◄─────│ running  │─────►│ completed│
└──────────┘      └────┬─────┘      └──────────┘
     │                 │                   │
     │           执行中/失败            全部完成
     │                 │                   │
     └─────────────────┴───────────────────┘
```

#### 3.3.2 客户端状态

```
┌──────────┐      ┌──────────┐      ┌──────────┐
│ offline  │─────►│  online  │─────►│  busy    │
└──────────┘      └────┬─────┘      └────┬─────┘
     ▲                 │                 │
     │           启动/重连            接任务
     │                 │                 │
     └─────────────────┴─────────────────┘
              心跳超时/断开
```

---

## 4. 客户端执行设计

### 4.1 执行流水线

客户端执行任务采用流水线模式：

```
┌──────────────────────────────────────────────────────────────────────┐
│                        客户端执行流水线                                │
│                                                                      │
│  1. 接收任务                                                           │
│     ┌─────────────────────────────────────────────────────────────┐  │
│     │ {                                                            │  │
│     │   task_id: "xxx",                                           │  │
│     │   test_file: "tests/api/test_user.py",                     │  │
│     │   branch: "main",                                           │  │
│     │   client_args: {"timeout": 60, "reruns": 2}                │  │
│     │ }                                                            │  │
│     └─────────────────────────────────────────────────────────────┘  │
│                                   │                                   │
│                                   ▼                                   │
│  2. Git Clone (若需要)                                                │
│     ┌─────────────────────────────────────────────────────────────┐  │
│     │ if not repo_exists:                                         │  │
│     │     git clone <repo_url> -b <branch>                        │  │
│     │ else:                                                       │  │
│     │     git fetch && git checkout <branch>                      │  │
│     └─────────────────────────────────────────────────────────────┘  │
│                                   │                                   │
│                                   ▼                                   │
│  3. 创建虚拟环境                                                      │
│     ┌─────────────────────────────────────────────────────────────┐  │
│     │ detect_env_tool()  # uv / pipenv / venv                     │  │
│     │ create_venv()                                                  │  │
│     │ activate_venv()                                               │  │
│     └─────────────────────────────────────────────────────────────┘  │
│                                   │                                   │
│                                   ▼                                   │
│  4. 安装依赖                                                          │
│     ┌─────────────────────────────────────────────────────────────┐  │
│     │ if Pipfile:      pipenv install                              │  │
│     │ elif pyproject.toml: uv pip install -e .                    │  │
│     │ elif requirements.txt: pip install -r requirements.txt     │  │
│     │ else: pass  # 无依赖                                         │  │
│     └─────────────────────────────────────────────────────────────┘  │
│                                   │                                   │
│                                   ▼                                   │
│  5. 执行测试                                                          │
│     ┌─────────────────────────────────────────────────────────────┐  │
│     │ pytest <test_file>                                          │  │
│     │   --alluredir=/tmp/allure-results                           │  │
│     │   --client-timeout=60                                       │  │
│     │   --client-reruns=2                                         │  │
│     │   -v  # 输出实时推送                                         │  │
│     └─────────────────────────────────────────────────────────────┘  │
│                                   │                                   │
│                                   ▼                                   │
│  6. 打包结果                                                          │
│     ┌─────────────────────────────────────────────────────────────┐  │
│     │ zip -r /tmp/allure.zip /tmp/allure-results/                 │  │
│     └─────────────────────────────────────────────────────────────┘  │
│                                   │                                   │
│                                   ▼                                   │
│  7. 上传结果                                                          │
│     ┌─────────────────────────────────────────────────────────────┐  │
│     │ POST /api/tasks/{task_id}/upload                            │  │
│     │   Content-Type: multipart/form-data                         │  │
│     │   Body: allure.zip                                          │  │
│     └─────────────────────────────────────────────────────────────┘  │
│                                   │                                   │
│                                   ▼                                   │
│  8. 请求下一个任务                                                    │
│     ┌─────────────────────────────────────────────────────────────┐  │
│     │ WS: {"action": "next", "task_id": "xxx", "result": {...}}  │  │
│     └─────────────────────────────────────────────────────────────┘  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.2 文件粒度执行

为了避免 pytest 重复收集用例，采用**文件级分发**：

```
服务端收集: pytest --collect-only tests/
结果: [test_a.py, test_b.py, test_c.py, test_d.py, ...]

分发: 每个客户端每次只分一个文件

客户端执行: pytest test_a.py -v --alluredir=...
            # 跳过收集，直接执行整个文件

优势:
- 客户端无需收集用例，减少开销
- 调试友好，输出和本地运行一致
- 实现简单
```

### 4.3 本地队列

客户端维护本地任务队列，避免频繁请求：

```python
class LocalQueue:
    def __init__(self, threshold=10):
        self.queue = []
        self.threshold = threshold
    
    def push(self, items):
        self.queue.extend(items)
    
    def pop(self):
        return self.queue.pop(0)
    
    def need_refill(self):
        return len(self.queue) < self.threshold
```

```
服务端一次性发送 50 个文件到客户端队列
客户端本地队列: [file_2, file_3, ..., file_50]
当前执行: file_1

执行完成后:
- 从本地队列取 file_2 执行
- 若队列剩余 < 10，向服务端请求补充
```

---

## 5. 数据存储设计

### 5.1 目录结构

```
data/
├── tasks/
│   ├── {task_id}.json      # 每个任务一个 JSON 文件
│   ├── {task_id}.json
│   └── {task_id}.json
│
├── allure/
│   └── {task_id}/
│       ├── client_1.zip
│       ├── client_2.zip
│       └── ...
│
├── reports/
│   └── {task_id}/
│       ├── index.html
│       ├── app.js
│       └── ...
│
└── repos/
    └── {repo_name}/
        ├── .git/
        ├── tests/
        └── ...
```

### 5.2 任务文件 ({task_id}.json)

```json
{
  "id": "uuid",
  "name": "API Tests",
  "status": "running",
  "created_at": "2024-01-01T00:00:00Z",
  "started_at": "2024-01-01T00:01:00Z",
  "finished_at": null,
  "repo_url": "https://github.com/xxx/tests.git",
  "branch": "main",
  "test_paths": ["tests/api/"],
  "filter_args": {
    "k": "api",
    "m": "smoke"
  },
  "client_args": {
    "timeout": 60,
    "reruns": 2
  },
  "test_files": ["tests/api/test_user.py", "tests/api/test_order.py"],
  "total_files": 100,
  "completed_files": 50,
  "failed_files": 2,
  "ip": "192.168.1.100",
  "results": [
    {
      "file": "tests/api/test_user.py",
      "status": "passed",
      "duration": 1.23,
      "passed": 10,
      "failed": 1,
      "error": 0,
      "skipped": 0
    }
  ],
  "report_url": "/api/reports/{task_id}"
}
```

### 5.3 CLI 任务列表配置

任务列表使用 rich 库展示，支持可配置的列定义和样式。

#### 5.3.1 默认列定义

| 列名 | 来源 | 宽度 | 说明 |
|------|------|------|------|
| id | task.id | 36 | 任务 UUID |
| name | task.name | 20 | 任务名称 |
| status | task.status | 10 | 任务状态 |
| created_at | task.created_at | 20 | 创建时间 |
| duration | 计算 | 10 | 执行时长 |
| ip | task.ip | 15 | 客户端 IP |
| passed | task.passed | 8 | 通过数 |
| failed | task.failed | 8 | 失败数 |
| report_url | 计算 | 30 | 报告地址 |

#### 5.3.2 状态颜色

| 状态 | 颜色 |
|------|------|
| passed | green |
| failed | red |
| running | yellow |
| pending | blue |
| completed | green |
| cancelled | gray |

#### 5.3.3 配置文件

配置文件位于 `~/.swarm/config.yaml` 或项目根目录 `swarm.config.yaml`：

```yaml
task:
  list:
    # 显示的列及顺序
    columns:
      - id
      - name
      - status
      - created_at
      - duration
      - ip
      - passed
      - failed
      - report_url
    
    # 列宽配置
    width:
      id: 36
      name: 20
      repo_url: 40
      report_url: 30
    
    # 状态颜色配置
    color:
      passed: green
      failed: red
      running: yellow
      pending: blue
      completed: green
      cancelled: gray
```

#### 5.3.4 命令行覆盖

命令行参数可以覆盖配置文件：

```bash
# 自定义列
swarm task list --columns id,name,status,report_url

# 自定义列宽
swarm task list --width name=30,repo_url=50

# 自定义颜色
swarm task list --color passed=green,failed=red
```

### 5.4 文件存储策略

- **JSON 文件**：任务信息、结果数据，使用 JSON 格式存储
- **ZIP 文件**：Allure 原始结果，客户端上传的压缩包
- **HTML 文件**：Allure 生成的报告
- **代码仓库**：`~/swarm/repos/{repo_name}/`

---

## 6. 异常处理设计

### 6.1 客户端异常

| 场景 | 处理方式 |
|------|----------|
| 网络断开 | 自动重连，30 秒重试间隔 |
| Git clone 失败 | 重试 3 次，失败则标记任务失败 |
| 虚拟环境创建失败 | 重试 3 次，失败则标记任务失败 |
| pytest 执行崩溃 | 捕获异常，上报错误，继续下一个任务 |
| Allure 生成失败 | 跳过报告生成，记录日志 |

### 6.2 服务端异常

| 场景 | 处理方式 |
|------|----------|
| 客户端心跳超时 | 60 秒内无心跳，标记为 offline |
| 任务分发失败 | 重新放入队列，等待其他客户端 |
| Allure 报告生成失败 | 返回错误，仍保存 JSON 结果 |
| 文件上传失败 | 客户端重试上传 |

### 6.3 任务取消

```
客户端收到取消消息:
1. 发送 SIGTERM 到 pytest 进程
2. 等待 5 秒优雅退出
3. 若未退出，发送 SIGKILL
4. 清理虚拟环境
5. 上传已生成的结果
6. 报告任务取消
```

---

## 7. 安全性设计

### 7.1 当前版本（无认证）

初始版本不包含认证机制，仅依赖：
- 内网环境（网络隔离）
- 客户端注册时的基本信息验证

### 7.2 后续版本规划

| 功能 | 描述 |
|------|------|
| Token 认证 | 请求时携带 Authorization: Bearer token |
| API Key | 每个用户独立的 API Key |
| 客户端白名单 | 限制允许注册的客户端 IP |

---

## 8. 性能优化

### 8.1 连接复用

- WebSocket 保持长连接，避免频繁建立
- HTTP 使用 httpx 保持连接池

### 8.2 批量操作

- 任务文件批量分发到客户端本地队列
- Allure 结果打包上传，减少请求次数

### 8.3 异步处理

- 文件上传异步执行，不阻塞测试执行
- WebSocket 消息异步推送

---

## 9. 扩展性设计

### 9.1 多任务支持

单个服务端支持多个任务并行：

```
Task Queue: [Task-A, Task-B, Task-C]
                │
                ▼
         ┌──────────────┐
         │  调度器      │
         └──────────────┘
          │     │     │
          ▼     ▼     ▼
     Client-1 Client-2 Client-3
```

### 9.2 插件化设计

未来可支持：
- 自定义报告格式
- 自定义通知渠道
- 自定义任务过滤规则

---

## 10. 部署架构

### 10.1 单机部署

```
┌─────────────────────────────────────────┐
│           单机部署模式                   │
│                                          │
│  ┌─────────────────────────────────────┐ │
│  │           服务端                     │ │
│  │  swarm server start --port 8000    │ │
│  │                                      │ │
│  │  - API: http://localhost:8000      │ │
│  │  - WS:  ws://localhost:8000/ws     │ │
│  │  - Docs: http://localhost:8000/docs│ │
│  │  - Report: http://localhost:8000/  │ │
│  │              api/reports/{id}       │ │
│  └─────────────────────────────────────┘ │
│                                          │
│  ┌─────────────────────────────────────┐ │
│  │  客户端 (可多台)                      │ │
│  │  swarm client start --server        │ │
│  │    http://server:8000              │ │
│  └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### 10.2 多客户端部署

```
┌─────────────────────────────────────────────────────────────────┐
│                      多客户端部署                                │
│                                                                  │
│  服务端 (Server)                                                 │
│  ┌─────────────────┐                                            │
│  │  :8000          │◄────── Client 1 (192.168.1.10)             │
│  │                 │◄────── Client 2 (192.168.1.11)             │
│  │  任务管理        │◄────── Client 3 (192.168.1.12)             │
│  │  报告生成        │◄────── ...                                 │
│  └─────────────────┘                                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 11. 依赖设计

### 11.1 核心依赖

| 包名 | 版本 | 用途 |
|------|------|------|
| fastapi | ≥0.110 | Web 框架 |
| uvicorn | * | ASGI 服务器 |
| websockets | * | WebSocket 支持 |
| httpx | * | HTTP 客户端 |
| loguru | * | 日志 |
| pydantic | * | 数据验证 |
| all/allure-pytest | * | Allure 支持 |
| fastapi-self-hosting-docs | * | API 文档自托管 |

### 11.2 客户端依赖

| 包名 | 版本 | 用途 |
|------|------|------|
| gitpython | * | Git 操作 |
| uv | * | 虚拟环境 |
| pipenv | * | 虚拟环境 |
| pytest | ≥7.0 | 测试框架 |

---

## 12. 监控与日志

### 12.1 日志级别

| 级别 | 使用场景 |
|------|----------|
| DEBUG | 详细调试信息 |
| INFO | 正常业务流程 |
| WARNING | 可恢复的异常 |
| ERROR | 不可恢复的错误 |

### 12.2 日志格式

```
# 服务端
2024-01-01 12:00:00 |server | INFO  | Client client-001 connected
2024-01-01 12:00:01 | server | INFO  | Task task-001 created with 100 test files
2024-01-01 12:00:02 | server | INFO  | Dispatched test_file_001 to client-001

# 客户端
2024-01-01 12:00:05 | client | INFO  | Received task: task-001
2024-01-01 12:00:06 | client | INFO  | Git clone: branch=main
2024-01-01 12:00:10 | client | INFO  | Virtual env created: /home/user/swarm/venv
2024-01-01 12:00:15 | client | INFO  | pytest executed: passed=10, failed=1
2024-01-01 12:00:16 | client | INFO  | Uploading allure results...
```

### 12.3 心跳机制

```
客户端:
  每 30 秒发送: {"action": "heartbeat"}

服务端:
  记录最后心跳时间
  60 秒内无心跳 → 标记为 offline
  恢复连接 → 标记为 online
```

---

## 13. API 详细设计

### 13.1 创建任务

```
POST /api/tasks
Content-Type: application/json

Request:
{
  "name": "API Tests",
  "test_paths": ["tests/api/", "tests/unit/"],
  "filter_args": {
    "k": "api",
    "m": "smoke"
  },
  "client_args": {
    "timeout": 60,
    "reruns": 2
  },
  "branch": "main"
}

Response (201):
{
  "id": "uuid",
  "status": "pending",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### 13.2 上传 Allure 结果

```
POST /api/tasks/{task_id}/upload
Content-Type: multipart/form-data

Request:
  file: allure-results.zip

Response (200):
{
  "success": true,
  "files_count": 15
}
```

### 13.3 获取报告

```
GET /api/reports/{task_id}

Response:
  HTML 页面 (text/html)
```

---

## 14. 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 通信协议 | WebSocket + HTTP | 实时双向，简洁高效 |
| 分发策略 | 动态按需 | 类似 pytest-xdist，智能调度 |
| 用例粒度 | 文件级 | 避免重复收集，调试友好 |
| 代码同步 | 每次 clone | 简单可靠，支持分支/Tag |
| 虚拟环境 | 任务独立 | 隔离性好，避免污染 |
| 报告生成 | 服务端汇总 | 统一入口，便于管理 |
| 部署模式 | 单包安装 | 简化部署，内网友好 |