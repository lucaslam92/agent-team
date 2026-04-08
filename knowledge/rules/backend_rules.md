# Backend Rules

## Scope

- 适用于 backend 服务、API contract、resolver、graph/semantic 相关后端脚本与服务化逻辑。

## Architecture Rules

- 保持 Mission 编排、结构化知识处理、检索逻辑分层，不要把多层职责揉进一个脚本。
- 确定性处理优先脚本化，包括 extract、graph build、persist、index rebuild、promotion state update。
- 语义推断与确定性处理分离，LLM 或 interpreter 不应直接承担落盘和状态迁移。

## API Rules

- 任何行为变化如果影响上下游契约，必须同步更新对应 artifact 或 contract 文件。
- 结构化输出优先使用稳定 JSON/YAML 字段，而不是仅靠自然语言段落。
- 新增脚本接口时，参数名应清晰表达输入输出根目录和运行模式。

## Data Rules

- 结构化语义知识必须保留来源引用和证据字段。
- generated 与 normalized 必须分离，不能直接覆盖正式知识。
- 所有状态文件必须可重建、可审计、可增量更新。

## Reliability Rules

- graph 构建和 promotion 过程应尽量幂等。
- 非致命输入问题优先写 warning/report，不要静默吞掉。
- 冲突关系必须显式记录，不允许悄悄覆盖旧知识。

## Testing Rules

- 修改脚本后至少做一次最小冒烟验证。
- 优先验证输入输出契约、状态文件落盘和路径兼容性。
- 若无法运行完整测试，至少做语法检查和样例执行。

## Anti-Patterns

- 不要把长期背景写进 mission artifact。
- 不要把 task-specific 输出直接当成正式 knowbase。
- 不要在没有 evidence/source_refs 的情况下晋升结构化知识。
