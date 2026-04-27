# Swarm

分布式自动化测试执行框架。

## 特性

- 多客户端协同执行测试
- 动态任务分发
- 自动生成 Allure 报告
- 简洁的 CLI 和 API 接口

## 快速开始

```bash
# 安装
pip install swarm

# 启动服务端
swarm server start

# 启动客户端
swarm client start --server http://localhost:8000

# 创建任务
swarm run tests/ --repo https://github.com/xxx/tests.git -b main
```

## 文档

- [需求规格说明书](docs/requirements.md)
- [架构设计文档](docs/architecture.md)

## License

MIT