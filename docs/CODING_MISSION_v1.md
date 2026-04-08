# Coding Mission 技术方案

## 1. 目标

Coding Mission 的目标不是“让 agent 自由写代码”，而是：

**把 Design Mission 产出的 implementation-ready 设计资产，转换成受约束、可验证、可追溯的代码变更与实现证据。**

因此 Coding Mission 的核心要求是：

- 可执行
- 可约束
- 可追溯
- 可验证
- 可回滚
- 可进入 Verification Mission

一句话概括：

**Coding Mission = 将 design task graph 编译为 implementation evidence。**

---

## 2. 输入模型

Coding Mission 当前建议统一输入模型为：

```text
final_prd + repo_context + knowbase_context + design_assets + task_graph + design_check_report
```

### 2.1 `final_prd`

来自 PRD Mission，是当前实现阶段的需求合同来源。

作用：

- 提供 acceptance criteria 的最终引用源
- 提供 scope 边界校验依据
- 提供 Coding → Verification 的追溯锚点

### 2.2 `repo_context`

表示当前代码与工程上下文。

包含：

- 仓库结构
- 模块与服务边界
- 当前依赖
- 技术栈
- 现有 contract / routes / entrypoints
- 本地架构约束

### 2.3 `knowbase_context`

由 Design Mission 前置读取后的结构化上下文。

Coding Mission 不应重新扫描全量 `knowledge/` 原文，而应消费已经收敛好的：

- backend/frontend rules
- stack constraints
- architecture constraints
- anti-patterns
- resolved references

### 2.4 `design_assets`

来自 Backend / Frontend Design Mission 的结构化产物。

典型包括：

- `backend_scope.json`
- `api_contract.yaml`
- `domain_model.json`
- `flow_model.json`
- `storage_plan.json`
- `quality_plan.json`
- `risk_register.json`
- `frontend_contract_view.json`
- `page_map.json`
- `navigation_map.json`
- `ui_structure.json`
- `state_model.json`
- `component_spec.json`
- `interaction_spec.json`
- `data_binding_plan.json`

### 2.5 `task_graph`

这是 Coding Mission 的直接执行入口。

当前已明确：

- 后端消费 `backend_task_graph.json`
- 前端消费 `frontend_task_graph.json`

Coding Mission 不自己重新拆任务，只能消费 Design Mission 已产出的 task graph。

### 2.6 `design_check_report`

这是 Coding Mission 的准入 gate 依据之一。

要求：

- 对应 design gate 必须通过，或至少达到允许进入 coding 的状态
- analyzer 输出应可用于 Coding 前修复不完整设计

结论：

**Coding Mission 不直接从原始需求出发，而是从“已通过设计校验的任务图”出发。**

---

## 3. 总体流程

Coding Mission 的总体流程建议收敛为：

```text
read_coding_inputs
→ load_design_gate_status
→ select_task_batch
→ resolve_task_context
→ execute_task_batch
→ run_task_verification
→ compile_coding_artifacts
→ verify_coding
→ handoff_to_verification
```

### 3.1 关键原则

- 只有通过 Design Gate 的任务才能进入 Coding
- Coding 不负责重新做设计
- Coding 不负责重新拆任务
- 一次只实现一个可控 batch
- 所有变更都要能回溯到 task 和 acceptance

---

## 4. Coding Mission 定位

Coding Mission 的职责是：

- 从 task graph 中选择 ready tasks
- 为任务补足 repo 级上下文
- 在代码仓库中完成受约束实现
- 执行对应 verification hooks
- 输出实现证据与 handoff 资产

它不负责：

- 重新定义 scope
- 重新发明 API contract
- 重写设计资产
- 做最终业务验收
- 代替 PR / review / merge

---

## 5. 核心问题

Coding Mission 当前需要回答：

- 现在应该实现哪些任务
- 这些任务的依赖是否满足
- 哪些文件允许或需要修改
- 改动是否超出 design scope
- 每个 task 的 `done_when` 是否满足
- 每个 task 的 verification hooks 是否执行
- 代码变更如何映射回 design artifact
- acceptance criteria 是否具备实现证据
- 哪些问题要阻断进入 Verification Mission

---

## 6. 任务选择机制

### 6.1 原则

Coding Mission 必须先选 batch，再执行。

标准链路为：

```text
task_graph
→ filter ready tasks
→ choose batch
→ implement
```

### 6.2 `ready task` 判定

任务只有在以下条件下才视为 ready：

- `depends_on` 已满足
- 所属 checkpoint 已开放
- 不受 blocking issue 阻断
- 对应设计资产完整
- 所需 contract / model / quality artifact 已存在

### 6.3 batch 选择规则

建议按以下优先级：

1. `blocking=true`
2. 当前 checkpoint 内任务
3. `priority=high`
4. 能在一次 coding loop 内完成的粒度

### 6.4 batch 粒度规则

一个 batch 不应过大，建议：

- 能在一轮 coding loop 内完成
- 能执行完对应 verification hooks
- 能明确判断 `done_when`

结论：

**Coding Mission 的第一步不是实现，而是确定一个可执行 task batch。**

---

## 7. 设计产物与 Coding 的衔接

### 7.1 Backend

Backend Coding Mission 直接消费：

- `backend_task_graph.json`
- `api_contract.yaml`
- `domain_model.json`
- `flow_model.json`
- `storage_plan.json`
- `quality_plan.json`
- `risk_register.json`

典型任务类型：

- `domain`
- `storage`
- `api`
- `event`
- `job`
- `observability`
- `test`

### 7.2 Frontend

Frontend Coding Mission 直接消费：

- `frontend_task_graph.json`
- `frontend_contract_view.json`
- `page_map.json`
- `navigation_map.json`
- `ui_structure.json`
- `state_model.json`
- `component_spec.json`
- `interaction_spec.json`
- `data_binding_plan.json`
- `quality_plan.json`

典型任务类型：

- `page`
- `component`
- `state`
- `data_binding`
- `contract_adapter`
- `interaction`
- `accessibility`
- `observability`
- `test`

---

## 8. Coding 产物

当前建议统一产物目录为：

```text
artifacts/coding/
  execution_context.json
  selected_task_batch.json
  task_execution_report.json
  changed_files.json
  implementation_evidence.json
  coding_design_trace.json
  coding_check_report.json
  verification_handoff.json
  coding_summary.md
```

### 8.1 `execution_context.json`

作用：

- 记录本次 coding run 的输入快照

包含：

- feature_id
- platform
- task_graph sources
- design asset refs
- repo context refs
- selected checkpoint

### 8.2 `selected_task_batch.json`

作用：

- 明确本轮真正执行的任务集

包含：

- selected_tasks
- skipped_tasks
- selection_reasons
- unresolved_dependencies
- execution_order

### 8.3 `task_execution_report.json`

作用：

- 记录每个 task 的执行结果

包含：

- task_id
- status
- changed_files
- done_when_results
- hook_results
- blockers
- notes

### 8.4 `changed_files.json`

作用：

- 记录真实修改文件及 task 映射

包含：

- path
- task_refs
- module
- change_type
- design_artifact_refs

### 8.5 `implementation_evidence.json`

作用：

- 汇总编译、lint、test、contract check 等实现证据

包含：

- compile_results
- lint_results
- unit_test_results
- integration_test_results
- contract_test_results
- smoke_results

### 8.6 `coding_design_trace.json`

作用：

- 建立 task → design → acceptance 的完整追溯

包含：

- task_ref
- design_artifact_refs
- contract_refs
- acceptance_refs
- changed_files

### 8.7 `coding_check_report.json`

作用：

- 汇总 verifier / gate / analyzer 的结果

它是 Coding Mission 的主 gate 报告。

### 8.8 `verification_handoff.json`

作用：

- 给 Verification Mission 提供结构化输入

包含：

- implemented_tasks
- changed_files
- expected_checks
- acceptance_trace
- known_risks
- open_issues

### 8.9 `coding_summary.md`

作用：

- 提供人类可读的 coding 摘要

原则：

- 只写摘要
- 重点写 batch、改动范围、证据与风险

---

## 9. Coding Skills 设计

当前建议 skill 收敛为：

- `coding.read_inputs`
- `coding.select_task_batch`
- `coding.resolve_task_context`
- `coding.backend.execute_tasks`
- `coding.frontend.execute_tasks`
- `coding.run_verification_hooks`
- `coding.compile_report`
- `coding.verify`

### 9.1 共同要求

这些 skill 的共同要求是：

- 单职责
- 固定输入
- 固定输出
- 不重新发明设计
- 优先结构化产物
- 可被 Claude Code / Codex 消费
- verifier 可独立校验

---

## 10. Backend / Frontend 执行策略

### 10.1 Backend 执行策略

建议按以下批次推进：

```text
domain
→ storage
→ api
→ event / job
→ observability
→ test
```

### 10.2 Frontend 执行策略

建议按以下批次推进：

```text
state
→ page / component
→ contract_adapter / data_binding
→ interaction
→ accessibility / observability
→ test
```

### 10.3 跨端策略

如果 feature 同时包含前后端任务：

- 先按 checkpoint 拆 batch
- 再分别执行 backend batch 与 frontend batch
- 最终在 `verification_handoff.json` 汇总

---

## 11. Gate 体系

当前建议 Coding Mission 至少有 4 个 gate：

### 11.1 Input Ready Gate

通过条件：

- 任务 batch 已选定
- 设计 gate 已通过
- 依赖满足
- design asset 完整

### 11.2 Change Safety Gate

通过条件：

- 改动文件都能解释
- 未超出 scope
- 关键 contract 未静默破坏
- 没有明显跨层越界

### 11.3 Verification Gate

通过条件：

- 已执行 task 要求的 verification hooks
- 编译 / lint / test 结果已记录
- failed hooks 已明确归因

### 11.4 Handoff Ready Gate

通过条件：

- changed files 已映射到 task
- acceptance trace 完整
- verification handoff 完整
- 无阻断问题遗留

---

## 12. Verifier 体系

当前建议的 verifier 包括：

- `coding_task_batch_readiness_verifier`
- `coding_scope_conformance_verifier`
- `coding_dependency_verifier`
- `coding_changed_files_trace_verifier`
- `coding_hook_execution_verifier`
- `coding_acceptance_trace_verifier`
- `coding_handoff_integrity_verifier`

后续可细化为：

- `backend_contract_regression_verifier`
- `backend_migration_safety_verifier`
- `frontend_state_consistency_verifier`
- `frontend_contract_adapter_verifier`

---

## 13. Analyzer 体系

当前建议 3 类 analyzer：

- `coding_batch_analyzer`
- `coding_change_analyzer`
- `coding_verification_analyzer`
- `coding_handoff_analyzer`

统一输出格式建议沿用 Design Mission：

- `failure_type`
- `reasons`
- `repair_actions`
- `resume_from`
- `suggested_skill`
- `suggested_command`
- `target_artifacts`
- `auto_fixable`
- `repair_plan`

这样 Coding 与 Design 的修复体验能够保持一致。

---

## 14. 首版实现建议

为了控制范围，第一版建议先实现：

- `coding.read_inputs`
- `coding.select_task_batch`
- `coding.backend.execute_tasks`
- `coding.frontend.execute_tasks`
- `coding.verify`
- `coding.compile_report`

第一版先只保证：

- 能读取 task graph
- 能选择 ready tasks
- 能记录 changed files
- 能执行 verification hooks
- 能生成 `coding_check_report.json`

---

## 15. 推荐实施顺序

当前建议的实施顺序为：

1. 写 `CODING_MISSION_v1.md`
2. 定义 `selected_task_batch.json` schema
3. 定义 `coding_check_report.json` schema
4. 实现 `coding.read_inputs`
5. 实现 `coding.select_task_batch`
6. 实现 `coding.verify`
7. 再补 backend/frontend execute skills

原因：

- Coding 阶段真正关键的是输入边界和 gate
- “如何写代码”反而不是第一刀
- 先收紧 task batch 和证据结构，后续执行层才不会失控

---

## 16. 当前结论

到目前为止，Coding Mission 的总体结论是：

### 16.1 本质

不是“自由编码”，而是：

**将 design task graph 编译为受约束的实现执行流。**

### 16.2 输入模型

当前建议固定为：

```text
final_prd
+ repo_context
+ knowbase_context
+ design_assets
+ task_graph
+ design_check_report
```

### 16.3 中轴产物

Coding Mission 的两个核心中轴建议是：

- `selected_task_batch.json`
- `coding_check_report.json`

### 16.4 与上下游的关系

它在整体链路中的位置为：

```text
PRD Mission
→ Design Mission
→ Coding Mission
→ Verification Mission
→ PR Mission
```

### 16.5 当前是否具备落地条件

是。

因为当前仓库已经具备：

- PRD Mission 主链
- Knowbase 主链
- Backend / Frontend Design Mission 主链
- Design verifier / gate / analyzer

因此 Coding Mission 已经可以进一步落成：

- 正式主文档
- schema 文件
- skill mapping
- verifier / gate 实现

