# API Rules

## Scope

- 适用于内部和外部 HTTP/RPC/API surface，以及 typed client 契约。

## Contract Rules

- 接口必须声明版本策略和兼容策略
- 字段命名、枚举值、错误模型应保持稳定
- 写接口需要声明幂等语义
- 列表接口需要声明分页、排序、过滤约束
- 行为变化影响客户端时，必须同步更新契约和迁移说明

## Reliability Rules

- 接口必须声明 timeout budget
- 重试只能发生在明确安全的链路
- 关键接口必须带 trace / request correlation
- 错误码和错误语义要可观测、可告警、可排障
