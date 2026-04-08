# Capacity Profile

## Goal

本文件定义默认的容量与性能约束，用于 PRD、Design、Coding、Verification 阶段统一对齐。

这些约束是默认工程基线；如业务有更严格或更宽松要求，应在 repo-local overlay 或 ADR 中覆盖说明。

## Required Capacity Inputs

每个关键功能在设计阶段至少要声明：

- steady-state QPS / RPS
- peak QPS / RPS
- critical path latency target
- consistency requirements
- retry tolerance
- downstream dependency limits

## Default Performance Budgets

默认预算建议：

- 读接口
  - p95 latency 目标小于 300ms
- 写接口
  - p95 latency 目标小于 500ms
- 关键同步链路
  - 至少声明 timeout budget
  - 至少声明重试策略
- 异步消费
  - 必须声明幂等键或等价幂等策略

## Availability And Degradation

关键能力必须声明：

- 目标可用性
- 降级路径
- 限流策略
- 熔断策略
- 人工恢复或回滚方式

## Common Bottlenecks

默认优先检查以下瓶颈：

- 数据库热点
- 索引缺失
- N+1 查询
- 上游接口抖动
- 大对象序列化
- 前端首屏阻塞资源
- 移动端弱网与重试放大

## Observability Requirements

容量相关改动至少需要补齐：

- request volume
- error rate
- latency percentile
- queue depth or backlog
- retry count
- saturation signal

## Review Rule

当功能涉及以下任一情况时，必须补容量说明：

- 新增公共接口
- 高并发入口
- 大批量任务
- 调用多个下游的聚合链路
- 依赖缓存、消息队列或搜索系统
