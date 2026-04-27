# Swarm 项目 AGENTS.md

本文件为 Swarm 项目的 AI 协作规范。

## 项目概述

Swarm 是一个分布式自动化测试执行框架，采用客户端/服务端架构，通过 WebSocket 和 HTTP 通信。

## 技术栈

- Python 3.8+
- FastAPI (Web 框架)
- WebSocket (实时通信)
- loguru (日志)
- httpx (HTTP 客户端)
- GitPython (Git 操作)
- Allure (测试报告)

## 项目结构

```
swarm/
├── swarm/                 # 主包
│   ├── __init__.py
│   ├── server/            # 服务端
│   │   ├── __init__.py
│   │   ├── main.py        # FastAPI 应用
│   │   ├── api.py         # API 路由
│   │   ├── websocket.py   # WebSocket 处理
│   │   ├── task.py        # 任务管理
│   │   ├── client.py      # 客户端管理
│   │   ├── collector.py   # 用例收集
│   │   └── report.py      # 报告生成
│   └── client/            # 客户端
│       ├── __init__.py
│       ├── main.py        # 客户端入口
│       ├── runner.py      # 任务执行
│       ├── git.py         # Git 操作
│       ├── venv.py        # 虚拟环境管理
│       └── uploader.py    # 结果上传
├── tests/                 # 测试
├── docs/                  # 文档
├── PROGRESS.md            # 项目进度
├── pyproject.toml
└── README.md
```

## 代码规范

### 1. 遵循全局规范

优先遵循全局 `AGENTS.md` 的原则：
- Think Before Coding - 不确定的地方先问
- Simplicity First - 最小代码解决问题
- Surgical Changes - 只改需要改的
- Goal-Driven Execution - 定义成功标准

### 2. 项目特定规范

| 规范 | 说明 |
|------|------|
| **类型标注** | 必须使用类型提示 |
| **异常处理** | 使用 loguru 记录日志，不生吞异常 |
| **配置管理** | 使用 pydantic Settings |
| **CLI** | 使用 click 或 argparse |
| **异步** | 服务端使用 async/await |

### 3. 命名约定

| 类型 | 约定 | 示例 |
|------|------|------|
| 模块 | 小写下划线 | `task_manager.py` |
| 类 | 大驼峰 | `TaskManager` |
| 函数/方法 | 小写下划线 | `create_task()` |
| 常量 | 大写下划线 | `DEFAULT_PORT` |

### 4. API 设计

- RESTful 风格
- 使用 pydantic 定义请求/响应模型
- 错误响应使用 HTTPException

## 工作流程

### 实现新功能

1. **确认需求** - 查看 `PROGRESS.md` 确认任务
2. **创建 Todo** - 拆解任务为具体步骤
3. **实现** - 按照项目结构创建/修改文件
4. **验证** - 运行 linter/type check
5. **提交** - 按照 commit 规范提交

### Commit 规范

```
feat: 新功能
fix: 修复
docs: 文档
refactor: 重构
test: 测试
chore: 杂项
```

## 文档关联

- 需求规格: `docs/requirements.md`
- 架构设计: `docs/architecture.md`
- 项目进度: `PROGRESS.md`

## 进度追踪

当前实现进度查看 `PROGRESS.md`