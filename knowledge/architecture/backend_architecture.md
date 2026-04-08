# Backend Architecture

## Scope

- 适用于后端服务、任务消费、数据访问层和外部集成层。
- 本文件描述“默认后端架构形态”，repo-local 差异通过 overlay 或 ADR 记录。

## Layering

- `handler / controller`
  - 负责协议适配、鉴权入口、参数校验、响应映射
- `service / use case`
  - 负责业务流程编排
  - 不直接持有协议层细节
- `domain`
  - 负责核心业务规则、领域对象、状态转换
- `repository`
  - 负责数据库访问、缓存访问、持久化模型映射
- `integration / gateway`
  - 负责第三方依赖、RPC、消息队列、搜索、对象存储等

依赖方向固定为：

`handler -> service -> domain / repository / integration`

不允许 repository 反向依赖 handler，也不允许 handler 内直接拼装复杂业务流程。

## Module Boundaries

- 按领域能力拆模块，而不是按技术细节堆目录
- 公共模块只放稳定接口，不放业务特例
- 同步 API、异步 consumer、定时任务若共享同一领域能力，应收敛到同一 service/domain 层
- 跨模块调用优先通过稳定接口，不直接读取对方内部表结构或内部对象

## Data And Integration

- 数据库 schema 变更必须可迁移、可回滚、可审计
- 对外依赖必须通过 integration/gateway 层封装
- 事件、消息、缓存键、幂等键都应有统一命名策略
- 写路径必须明确幂等与重试行为

## Reliability

- 每个外部依赖都要声明 timeout、retry、fallback、observability
- 关键写路径默认要求幂等
- 对高风险链路优先使用限流、熔断、降级，而不是无限重试
- 所有关键接口都要有 request id / trace id

## Async And Batch Work

- 异步任务必须声明重试上限和死信策略
- 批处理任务必须声明分片或批次策略
- 消费逻辑必须避免“重复消费导致状态污染”

## Observability

默认要求补齐：

- structured logs
- metrics
- tracing
- error classification
- dependency timing

## Architecture Review Checklist

- 是否遵守分层与依赖方向
- 是否明确幂等、重试、超时、降级
- 是否声明数据库与缓存影响
- 是否声明容量风险与观测指标

## Reliability

- Document retry, timeout, idempotency, and observability expectations here.
