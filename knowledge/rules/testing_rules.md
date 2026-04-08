# Testing Rules

## Scope

- 适用于 PRD、Design、Coding、Verification 各阶段与最终交付校验。

## Rules

- 单元测试覆盖核心纯逻辑和状态转换
- 集成测试覆盖模块边界、数据访问和外部依赖适配
- 契约测试覆盖 API / typed client / event schema
- 验收测试必须能回溯到 PRD acceptance criteria
- 修复 bug 时，优先补能防止回归的最小测试
