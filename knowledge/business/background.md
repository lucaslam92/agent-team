# Business Background

## Product Goal

- 构建一套 AI 驱动的软件工程系统，把原始需求和工程信号逐步转成结构化知识、工程决策与可执行任务。

## Target Users

- 使用 Claude Code / Codex 等 agent 工具推进需求、设计、编码、验证流程的工程团队。
- 需要把长期规则、架构知识、任务产物和可复用流程拆层治理的项目维护者。

## Core Scenarios

- 输入原始需求后，生成结构化 PRD。
- 基于 PRD 和上下文知识，生成设计与任务拆解。
- 结合长期规则和语义知识，辅助 coding / verification / PR 流程。
- 在每次任务闭环后沉淀结构化知识，持续积累 semantic store。

## Success Metrics

- Mission 各阶段都有稳定的输入输出契约。
- 长期知识与当前任务产物分层清晰，不相互污染。
- 能持续从代码、文档和任务产物中积累可复用知识。
- Agent 在不同工具环境中都能按同一套结构运行。

## Long-Term Constraints

- 任务层、执行层、能力层、知识层必须分离。
- 长期文档知识与结构化语义知识必须分离。
- Graph retrieval 应逐步替代 keyword-only 检索。
- 结构化知识必须可追踪来源、可晋升、可治理。

## Non-Goals

- 不把所有背景都塞进单个系统提示或单个 skill。
- 不把 mission artifacts 当成长期知识库。
- 不让 generated 候选知识直接充当正式规则真相。

## Related Terminology

- `knowledge/`：长期文档知识
- `semantic-store/`：结构化语义知识与索引
- `artifacts/`：当前任务产物
- `skills/`：可复用工作流能力

## References

- `docs/PRD_Mission_Design_v3.md`
- `docs/AI_Software_Engineering_System_TODO.md`
