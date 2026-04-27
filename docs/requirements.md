# Swarm 需求规格说明书

## 1. 项目概述

### 1.1 项目背景

在现代软件开发中，自动化测试是保障代码质量的重要环节。随着项目规模扩大，单机测试已无法满足需求，需要将测试任务分发到多台机器上并行执行，以缩短测试时间。

现有解决方案（如 pytest-xdist）虽然支持远程分发，但存在以下局限：
- **无管理界面**：纯命令行操作，缺乏统一的任务管理
- **无任务队列**：每次独立执行，无历史记录和重试机制
- **无机器管理**：每次手动指定远程机器，无法统一管理
- **无认证授权**：无用户和权限管理
- **rsync 即将废弃**：4.0 版本将移除 rsync 功能

### 1.2 项目目标

Swarm 是一个分布式自动化测试执行框架，旨在解决上述问题，提供：
- 多客户端协同执行测试
- 任务队列和历史记录
- 统一的 Web API 和 CLI 接口
- Allure 报告自动生成
- 客户端心跳监控

### 1.3 项目定义

| 属性 | 值 |
|------|-----|
| **项目名称** | Swarm |
| **CLI 命令** | `swarm` |
| **项目类型** | 分布式测试执行框架 |
| **核心语言** | Python 3.8+ |
| **核心框架** | FastAPI |

### 1.4 术语定义

| 术语 | 定义 |
|------|------|
| **服务端** | Swarm 服务器，负责任务管理、客户端管理、报告生成 |
| **客户端** | Swarm 代理，安装在测试机器上，负责执行测试 |
| **任务** | 一次完整的测试执行，包含用例集合、执行配置、结果 |
| **用例文件** | 待执行的测试文件（Python 文件或目录） |
| **用例粒度** | 分发到客户端的最小单位（文件级别，而非单条用例） |
| **动态按需** | 客户端执行完一个用例后主动请求下一个的服务端分发策略 |
| **任务模板** | 预先配置的 JSON 文件，定义任务参数 |

---

## 2. 功能需求

### 2.1 系统架构

#### 2.1.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Swarm 系统                                  │
│                                                                          │
│  ┌──────────────────────────┐         ┌──────────────────────────┐    │
│  │        服务端             │         │        客户端             │    │
│  │     (Swarm Server)       │         │    (Swarm Client)        │    │
│  │                          │         │                          │    │
│  │  ┌──────────────────┐   │   WS    │   ┌──────────────────┐   │    │
│  │  │   API Server     │◄──┼─────────┼──►│  WebSocket       │   │    │
│  │  │   (FastAPI)      │   │         │   │  Client          │   │    │
│  │  └──────────────────┘   │         │   └──────────────────┘   │    │
│  │           │             │         │           │              │    │
│  │           ▼             │         │           ▼              │    │
│  │  ┌──────────────────┐   │   HTTP  │   ┌──────────────────┐   │    │
│  │  │  Task Manager    │   │◄────────┼─►│  Task Runner     │   │    │
│  │  │  (任务管理)       │   │         │   │  (任务执行器)     │   │    │
│  │  └──────────────────┘   │         │   └──────────────────┘   │    │
│  │           │             │         │           │              │    │
│  │           ▼             │         │           ▼              │    │
│  │  ┌──────────────────┐   │         │   ┌──────────────────┐   │    │
│  │  │  Allure Report   │   │         │   │  Git Clone       │   │    │
│  │  │  Generator       │   │         │   │  (代码同步)       │   │    │
│  │  └──────────────────┘   │         │   └──────────────────┘   │    │
│  │           │             │         │           │              │    │
│  │           ▼             │         │           ▼              │    │
│  │  ┌──────────────────┐   │         │   ┌──────────────────┐   │    │
│  │  │  File Storage    │   │         │   │  Virtual Env     │   │    │
│  │  │  (文件存储)       │   │         │   │  (虚拟环境)       │   │    │
│  │  └──────────────────┘   │         │   └──────────────────┘   │    │
│  │                          │         │                          │    │
│  └──────────────────────────┘         └──────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 2.1.2 通信模式

- **HTTP**：任务管理（创建、查询、取消）、文件上传、报告访问
- **WebSocket**：任务下发、日志推送、实时交互

### 2.2 服务端功能

#### 2.2.1 任务管理

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 创建任务 | 通过 API 或 CLI 创建测试任务 | P0 |
| 任务列表 | 查询所有任务（支持分页、筛选） | P0 |
| 任务详情 | 查看单个任务的详细信息 | P0 |
| 取消任务 | 中止正在执行的任务 | P1 |
| 任务重试 | 重新执行失败的任务 | P1 |
| 任务历史 | 查看历史执行记录 | P1 |
| 任务模板 | 支持 JSON 配置文件创建任务 | P1 |
| 历史重跑 | 使用历史任务的 JSON 配置重跑 | P1 |

#### 2.2.2 用例收集

- 服务端负责收集待执行的测试用例
- 收集方式：`pytest --collect-only`
- 收集结果：文件路径列表（而非单条用例）

#### 2.2.3 任务分发

- 分发策略：动态按需，按文件粒度
- 分发过程：
  1. 服务端收集所有用例文件路径
  2. 客户端通过 WebSocket 连接
  3. 服务端推送任务到空闲客户端
  4. 客户端执行完成后请求下一个
  5. 重复直到所有用例执行完毕

#### 2.2.4 客户端管理

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 注册 | 客户端启动时自动注册 | P0 |
| 心跳 | 定期发送心跳，维护在线状态 | P0 |
| 下线 | 客户端断开后标记离线 | P0 |
| 列表 | 查看所有客户端及状态 | P1 |

#### 2.2.5 报告生成

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 结果收集 | 接收客户端上传的 Allure JSON | P0 |
| 报告生成 | 汇总所有 JSON 生成 HTML 报告 | P0 |
| 报告访问 | 通过 Web 访问报告 | P0 |

#### 2.2.6 Pytest 参数处理

采用**前缀区分**策略：

| 参数类型 | 示例 | 说明 |
|----------|------|------|
| 服务端参数 | `-k "api" -m "smoke"` | 服务端收集用例时使用 |
| 客户端参数 | `--client-timeout=60 --client-reruns=2` | 透传到客户端执行 pytest 时使用 |

客户端收到参数后，**自动去掉前缀**再传给 pytest：
```
输入: --client-timeout=60 --client-reruns=2
转换: --timeout=60 --reruns=2
执行: pytest tests/ --timeout=60 --reruns=2
```

### 2.3 客户端功能

#### 2.3.1 注册与心跳

- 启动时自动向服务端注册
- 定期发送心跳（默认 30 秒）
- 断开后自动重连
- 心跳超时后，任务重新分配给其他客户端（可配置等待时间）

#### 2.3.2 任务执行

| 功能 | 描述 |
|------|------|
| 接收任务 | 通过 WebSocket 接收任务 |
| 代码同步 | Git clone 最新代码（支持分支/Tag） |
| 环境创建 | 为每个任务创建独立虚拟环境（uv/pipenv） |
| 依赖安装 | 自动检测并安装依赖 |
| 执行测试 | 执行 pytest 命令 |
| 结果回传 | 通过 WebSocket 推送执行日志 |

#### 2.3.3 Git 仓库

任务参数中需指定仓库地址：
```bash
swarm run --repo https://github.com/xxx/tests.git -b main tests/
```

支持功能：
- 指定分支或 Tag
- 支持任务模板 JSON 文件
- 支持历史任务 JSON 配置重跑

#### 2.3.4 Allure 支持

- 执行时生成 Allure JSON：`pytest --alluredir=/tmp/allure-results`
- 执行完成后打包为 zip
- 上传到服务端

#### 2.3.5 虚拟环境

- 创建：每个任务创建新的虚拟环境
- 工具选择：
  - 项目中有 `Pipfile` → 使用 pipenv
  - 项目中有 `pyproject.toml` → 使用 uv
  - 否则使用 venv
- 清理：任务完成后销毁虚拟环境

#### 2.3.6 代码同步

- 每次任务执行前 clone 最新代码
- 支持指定分支或 Tag
- 工作目录结构：
  ```
  ~/swarm/
  └── repos/
      └── {repo_name}/
          ├── .git/
          ├── tests/
          └── ...
  ```

### 2.4 CLI 接口

#### 2.4.1 安装

```bash
pip install swarm
```

#### 2.4.2 服务端命令

```bash
# 启动服务端
swarm server start
swarm server start --port 9000  # 指定端口

# 停止服务端
swarm server stop
```

#### 2.4.3 客户端命令

```bash
# 启动客户端
swarm client start
swarm client start --server http://localhost:8000

# 停止客户端
swarm client stop
```

#### 2.4.4 任务命令

```bash
# 创建任务（直接指定参数）
swarm run tests/ -k "api" -m "smoke" --repo https://github.com/xxx/tests.git -b main --client-timeout=60 --client-reruns=2

# 创建任务（使用模板）
swarm run --config task_template.json

# 使用历史任务配置重跑
swarm run --config data/tasks/{task_id}/meta.json

# 列出任务（默认表格显示）
swarm task list
swarm task list --status running

# 自定义列显示
swarm task list --columns id,name,status,created_at,ip,repo_url
swarm task list --columns id,name,status,report_url

# 自定义列宽
swarm task list --width name=30,repo_url=50

# 自定义颜色（status 字段着色）
swarm task list --color passed=green,failed=red,running=yellow,pending=blue

# 查看任务详情
swarm task info <task_id>

# 取消任务
swarm task cancel <task_id>
```

##### 任务列表获取

任务列表通过服务端 API 获取：
```bash
GET /api/tasks
GET /api/tasks?status=running
```

- 不传 status 参数：返回全部任务
- 传 status 参数：返回指定状态的任务（如 `--status running`）

##### 任务列表显示

任务列表使用 rich 库以表格形式展示：

| 默认列名 | 来源 | 描述 |
|----------|------|------|
| `id` | task.id | 任务 UUID |
| `name` | task.name | 任务名称 |
| `status` | task.status | 任务状态 |
| `created_at` | task.created_at | 创建时间 |
| `started_at` | task.started_at | 开始时间 |
| `finished_at` | task.finished_at | 结束时间 |
| `duration` | 计算字段 | 执行时长 |
| `ip` | task.ip | 客户端 IP |
| `repo_url` | task.repo_url | 仓库地址 |
| `branch` | task.branch | 分支 |
| `test_files` | task.test_files | 测试文件数 |
| `passed` | task.passed | 通过数 |
| `failed` | task.failed | 失败数 |
| `report_url` | 计算字段 | 报告地址 |

##### 配置文件

列显示可通过配置文件自定义：

```yaml
# ~/.swarm/config.yaml 或项目根目录 swarm.config.yaml
task:
  list:
    columns:
      - id
      - name
      - status
      - created_at
      - ip
      - report_url
    width:
      id: 36
      name: 20
      repo_url: 40
    color:
      passed: green
      failed: red
      running: yellow
      pending: blue
      completed: green
      cancelled: gray
```

##### 任务存储

每个任务单独一个 JSON 文件，存放在服务端 data 目录：

```
data/tasks/
├── {task_id_1}.json
├── {task_id_2}.json
└── {task_id_3}.json
```

任务 JSON 文件内容见 3.1 节。

### 2.5 API 接口

#### 2.5.1 任务 API

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/tasks` | 创建任务 |
| GET | `/api/tasks` | 任务列表 |
| GET | `/api/tasks/{task_id}` | 任务详情 |
| DELETE | `/api/tasks/{task_id}` | 取消任务 |
| POST | `/api/tasks/{task_id}/retry` | 重试任务 |
| GET | `/api/tasks/{task_id}/results` | 任务结果 |
| POST | `/api/tasks/{task_id}/upload` | 上传 Allure 结果 |

#### 2.5.2 客户端 API

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/clients` | 客户端列表 |
| GET | `/api/clients/{client_id}` | 客户端详情 |

#### 2.5.3 报告 API

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/reports/{task_id}` | 访问 Allure 报告 |

### 2.6 WebSocket 协议

路径：`/ws/{client_id}`

连接流程：
```
1. 客户端连接 ws://server:8000/ws/temp_client_id
2. 发送: {"action": "register", "hostname": "...", ...}
3. 服务端: 返回 {"action": "registered", "client_id": "real_uuid"}
4. 客户端: 后续使用 real_uuid 通信
```

#### 2.6.1 客户端 → 服务端消息

| 消息类型 | 用途 | 格式 |
|----------|------|------|
| `register` | 注册 | `{"action": "register", "hostname": "...", "ip": "...", ...}` |
| `heartbeat` | 心跳 | `{"action": "heartbeat"}` |
| `next` | 请求下一个任务 | `{"action": "next", "task_id": "xxx", "result": {...}}` |
| `log` | 推送日志 | `{"action": "log", "message": "..."}` |

#### 2.6.2 服务端 → 客户端消息

| 消息类型 | 用途 | 格式 |
|----------|------|------|
| `registered` | 注册确认 | `{"action": "registered", "client_id": "xxx"}` |
| `task` | 下发任务 | `{"action": "task", "task_id": "xxx", "test_file": "..."}` |
| `cancel` | 取消任务 | `{"action": "cancel", "task_id": "xxx"}` |

### 2.7 非功能需求

#### 2.7.1 部署要求

- 支持内网部署（无外网依赖）
- API Docs 采用自托管方案（不依赖 cdn.jsdelivr.net）

#### 2.7.2 性能要求

- 单服务端支持至少 50 个客户端同时在线
- 单任务支持至少 10 个客户端并发执行

#### 2.7.3 可用性

- 客户端支持断线重连
- 心跳检测客户端存活状态（默认超时 60 秒）
- 服务端异常时客户端保持等待
- 心跳超时后任务重新分配

#### 2.7.4 日志

- 使用 loguru 记录日志
- 保留天数可配置
- 日志包含：任务执行日志、客户端日志、服务端日志

---

## 3. 数据模型

### 3.1 任务 (Task)

```json
{
  "id": "uuid",
  "name": "任务名称",
  "repo_url": "https://github.com/xxx/tests.git",
  "branch": "main",
  "status": "pending|running|completed|failed|cancelled",
  "created_at": "2024-01-01T00:00:00Z",
  "started_at": "2024-01-01T00:00:00Z",
  "finished_at": "2024-01-01T00:00:00Z",
  "test_paths": ["tests/api/", "tests/unit/"],
  "filter_args": {
    "k": "api",
    "m": "smoke"
  },
  "client_args": {
    "timeout": 60,
    "reruns": 2,
    "allure_results": "/tmp/allure-results"
  },
  "test_files": ["tests/api/test_user.py", "tests/api/test_order.py"],
  "total_files": 100,
  "completed_files": 50,
  "failed_files": 2,
  "results": [
    {
      "file": "tests/api/test_user.py",
      "status": "passed|failed|error",
      "duration": 1.23,
      "passed": 10,
      "failed": 1,
      "error": 0,
      "skipped": 0
    }
  ]
}
```

**状态说明**：
- `pending`：等待执行
- `running`：执行中
- `completed`：全部执行完成（无论用例通过/失败）
- `failed`：异常中断（如客户端崩溃、超时）
- `cancelled`：手动取消

### 3.2 客户端 (Client)

```json
{
  "id": "uuid",
  "name": "client-001",
  "hostname": "test-machine-1",
  "ip": "192.168.1.100",
  "os": "Linux-5.4.0-generic-x86_64",
  "python_version": "3.11.0",
  "status": "online|offline|busy",
  "registered_at": "2024-01-01T00:00:00Z",
  "last_heartbeat": "2024-01-01T00:00:00Z",
  "current_task_id": "uuid|null"
}
```

### 3.3 任务模板 (Task Template)

```json
{
  "name": "API Test Template",
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
  }
}
```

---

## 4. 执行流程

### 4.1 任务执行完整流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. 任务创建                                                              │
│    CLI: swarm run --repo https://github.com/xxx/tests.git -b main      │
│              tests/ -k "api"                                            │
│         ↓                                                               │
│    POST /api/tasks                                                      │
│         ↓                                                               │
│    服务端: 收集用例 (pytest --collect-only tests/)                      │
│         ↓                                                               │
│    返回: test_files = ["tests/api/test_user.py", ...]                   │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. 任务分发                                                              │
│    服务端: 找到空闲客户端 (status=online, current_task=null)             │
│         ↓                                                               │
│    WebSocket: 推送任务到客户端                                           │
│    {                                                                    │
│      task_id: "xxx",                                                    │
│      test_file: "tests/api/test_user.py",                               │
│      repo_url: "https://github.com/xxx/tests.git",                      │
│      branch: "main",                                                    │
│      client_args: {"timeout": 60, "reruns": 2}                          │
│    }                                                                    │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 3. 客户端执行                                                            │
│    3.1 Git clone (若不存在或需要更新)                                    │
│         ↓                                                               │
│    3.2 创建虚拟环境 (uv/pipenv)                                          │
│         ↓                                                               │
│    3.3 安装依赖 (pip install -r requirements.txt)                       │
│         ↓                                                               │
│    3.4 执行 pytest (去掉 --client- 前缀)                                 │
│         pytest tests/api/test_user.py --alluredir=/tmp/results          │
│              --timeout=60 --reruns=2                                     │
│         ↓                                                               │
│    3.5 打包 Allure 结果                                                 │
│         zip -r /tmp/allure-results.zip /tmp/allure-results/             │
│         ↓                                                               │
│    3.6 上传到服务端                                                      │
│         POST /api/tasks/{task_id}/upload                                │
│         ↓                                                               │
│    3.7 请求下一个任务                                                   │
│         WebSocket: {action: "next", "task_id": "xxx", "result": {...}} │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 4. 结果汇总                                                              │
│    所有客户端完成 → 服务端收集所有 Allure JSON                           │
│         ↓                                                               │
│    allure generate /data/allure/{task_id} -o /data/reports/{task_id}    │
│         ↓                                                               │
│    报告访问: GET /api/reports/{task_id}                                 │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 用例状态

遵循 pytest 原生状态：
- `passed`：通过
- `failed`：断言失败
- `error`：代码异常
- `skipped`：跳过
- `xfailed`：预期失败
- `xpassed`：预期失败但通过

---

## 5. 验收标准

### 5.1 功能验收

| 编号 | 功能 | 验收条件 |
|------|------|----------|
| F01 | 服务端启动 | 服务端可正常启动，监听指定端口 |
| F02 | 客户端启动 | 客户端可连接服务端，显示在线状态 |
| F03 | 任务创建 | 通过 CLI 创建任务，服务端返回任务 ID |
| F04 | 用例收集 | 服务端正确收集测试用例文件 |
| F05 | 任务分发 | 服务端将任务分发到空闲客户端 |
| F06 | 代码同步 | 客户端正确 clone 代码到本地 |
| F07 | 虚拟环境 | 客户端为任务创建独立的虚拟环境 |
| F08 | 执行测试 | 客户端正确执行 pytest |
| F09 | 结果回传 | 客户端将执行结果回传给服务端 |
| F10 | Allure 报告 | 服务端生成可访问的 Allure HTML 报告 |
| F11 | 任务取消 | 可取消正在执行的任务 |
| F12 | 客户端列表 | 可查看所有客户端及状态 |
| F13 | 任务模板 | 支持 JSON 配置文件创建任务 |
| F14 | 历史重跑 | 支持使用历史任务配置重跑 |

### 5.2 非功能验收

| 编号 | 功能 | 验收条件 |
|------|------|----------|
| N01 | 内网部署 | 在无外网环境下可正常部署和运行 |
| N02 | 自托管 Docs | Swagger UI 可正常加载，不依赖外网 |
| N03 | 心跳检测 | 客户端断线后服务端可检测到 |
| N04 | 日志记录 | 日志正常记录，可配置保留天数 |
| N05 | 断线重连 | 客户端断开后可自动重连 |

---

## 6. 附录

### 6.1 与 pytest-xdist 的对比

| 特性 | pytest-xdist | Swarm |
|------|--------------|-------|
| 远程执行 | ✅ | ✅ |
| 管理界面 | ❌ | ✅ (Web API + CLI) |
| 任务队列 | ❌ | ✅ |
| 历史记录 | ❌ | ✅ |
| Allure 集成 | 需手动 | ✅ 自动 |
| 机器管理 | 命令行指定 | Web 管理 |
| 代码同步 | rsync（将废弃） | Git clone |
| 虚拟环境 | 需手动 | ✅ 自动 |
| 任务模板 | ❌ | ✅ (JSON) |
| 认证 | ❌ | ✅ (后续版本) |

### 6.2 技术栈

| 组件 | 技术选型 |
|------|----------|
| Web 框架 | FastAPI |
| WebSocket | FastAPI (原生支持) |
| API 文档 | fastapi-self-hosting-docs (自托管) |
| 日志 | loguru |
| HTTP 客户端 | httpx |
| 虚拟环境 | uv / pipenv / venv |
| 报告 | Allure |

### 6.3 目录结构

```
swarm/
├── swarm/
│   ├── __init__.py
│   ├── server/
│   │   ├── __init__.py
│   │   ├── main.py          # 服务端入口
│   │   ├── api.py           # API 路由
│   │   ├── websocket.py     # WebSocket 处理
│   │   ├── task.py          # 任务管理
│   │   ├── client.py        # 客户端管理
│   │   ├── collector.py     # 用例收集
│   │   └── report.py        # 报告生成
│   └── client/
│       ├── __init__.py
│       ├── main.py          # 客户端入口
│       ├── runner.py        # 任务执行
│       ├── git.py           # Git 操作
│       ├── venv.py          # 虚拟环境管理
│       └── uploader.py      # 结果上传
├── tests/
├── docs/
├── pyproject.toml
└── README.md
```