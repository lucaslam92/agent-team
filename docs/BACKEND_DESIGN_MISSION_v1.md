# Backend Design Mission 技术方案（v1）

## 1. 目标

Backend Design Mission 的目标不是产出一篇“后端设计说明文档”，而是：

> 把 `final_prd` 转换成可实施、可拆解、可验证、可被 Coding Mission 直接消费的后端设计资产。

因此 Backend Design Mission 的核心要求是：

- 可读
- 可机读
- 可追溯
- 可拆任务
- 可验证
- 可进入 Coding Mission

一句话概括：

> Backend Design Mission = 将需求合同编译为 implementation-ready backend contract。

---

## 2. 输入模型

Backend Design Mission 当前统一输入模型为：

```text
final_prd + repo_context + knowbase_context
```

### 2.1 `final_prd`

来自 PRD Mission，是当前设计阶段的唯一需求合同。

包含：

- scope
- actors
- user flows
- functional requirements
- non-functional requirements
- platform contract
- dependency contract
- state contract
- acceptance criteria

### 2.2 `repo_context`

表示当前代码与工程上下文，包括：

- 仓库结构
- 服务/模块清单
- 已有 API
- 现有依赖
- 现有技术栈
- 当前架构约束

典型输入可包括：

```text
repo_context.json
service_inventory.json
existing_api_specs/
architecture_constraints.json
```

### 2.3 `knowbase_context`

来自 Knowbase 的结构化提取结果。

这里的原则已经固定：

> Knowbase 在 Design Mission 中只是输入增强层，通过 `read_knowbase_context` 注入，不作为独立 Mission。

包含：

- 业务背景
- 架构约束
- backend rules
- API rules
- testing rules
- 技术栈约束
- 反模式
- 已引用的 knowbase 来源

---

## 3. 总体流程

Design Mission 的总体流程当前收敛为：

```text
read_design_inputs
→ read_knowbase_context
→ platform_scope_alignment
→ platform_design
→ compile_design_assets
→ verify_design
```

其中目前展开最完整的是 Backend Design Mission。

---

## 4. Backend Design Mission

### 4.1 定位

Backend Design Mission 的目标是：

> 基于 `final_prd`、`repo_context`、`knowbase_context`，生成 implementation-ready backend design assets。

它不负责：

- 写代码
- 执行 build/test
- 做最终验收

它只负责：

- 明确后端职责边界
- 设计后端对外 contract
- 设计领域模型与流程
- 设计存储与依赖
- 前置工程质量要求
- 生成 coding-ready task graph
- 验证设计是否足够进入 Coding Mission

### 4.2 核心问题

Backend Design Mission 需要回答以下问题：

- 后端负责什么
- 后端不负责什么
- 前后端边界是什么
- 提供哪些 API / event / job
- 后端领域模型和状态模型是什么
- 主流程 / 异常流程 / 补偿流程是什么
- 数据落点和依赖关系如何设计
- 幂等、一致性、权限、观测、回滚如何保证
- 如何拆成 Coding Mission 可执行任务
- 如何验证设计完整性与可实施性

### 4.3 Backend 流程

当前后端设计流程为：

```text
read_design_inputs
→ read_knowbase_context
→ backend_scope_alignment
→ backend_api_design
→ backend_domain_model_design
→ backend_flow_design
→ backend_storage_and_dependency_design
→ backend_quality_and_risk_design
→ compile_backend_design
→ verify_backend_design
```

---

## 5. 后端设计产物

当前已经明确的后端设计产物如下：

```text
artifacts/design/backend/
  backend_scope.json
  knowbase_context.json
  api_contract.yaml
  domain_model.json
  flow_model.json
  storage_plan.json
  quality_plan.json
  risk_register.json
  backend_design.md
  backend_task_graph.json
  design_context_snapshot.json
  design_check_report.json
```

### 5.1 `backend_scope.json`

作用：定义后端职责边界。

包含：

- backend_responsibilities
- frontend_responsibilities
- shared_contracts
- out_of_scope
- assumptions

### 5.2 `knowbase_context.json`

作用：统一承载本次设计所需的 knowbase 结构化上下文。

包含：

- business_context
- architecture_constraints
- backend_rules
- api_rules
- testing_rules
- technical_stack
- resolved_references

它的定位是：

> 后续所有 backend design skill 统一消费的知识上下文。

### 5.3 `api_contract.yaml`

这是当前 Backend Design Mission 中最核心的中轴产物。

它的定位不是普通接口文档，而是：

> 后端对外能力合同 + 行为合同 + 验证映射合同

它直接连接：

- Frontend Design Mission
- Coding Mission
- Verification Mission

### 5.4 `domain_model.json`

作用：定义业务模型与状态规则。

包含：

- entities
- value_objects
- aggregates
- state_machines
- invariants

### 5.5 `flow_model.json`

作用：定义后端主流程与异常流程。

包含：

- main_flows
- error_flows
- retry_flows
- compensation_flows

### 5.6 `storage_plan.json`

作用：定义存储、缓存、topic、依赖和迁移计划。

包含：

- tables
- indexes
- cache
- topics
- external_dependencies
- migration_plan

### 5.7 `quality_plan.json`

作用：把工程质量要求前置到设计阶段。

包含：

- idempotency_strategy
- consistency_strategy
- concurrency_control
- permission_model
- observability
- rollout_plan
- rollback_plan

### 5.8 `risk_register.json`

作用：记录风险、影响与缓解措施。

### 5.9 `backend_task_graph.json`

作用：

> 把设计资产翻译为 Coding Mission 可直接消费的任务图。

它是 Design → Coding 的关键桥接资产。

### 5.10 `backend_design.md`

作用：

> 结构化设计产物的人类可读编译版

用于：

- 人审阅
- agent 快速理解全局设计
- 后续交付与追溯

### 5.11 `design_context_snapshot.json`

作用：记录本次设计的依据与引用来源。

包括：

- prd_source
- repo_context_sources
- knowbase_sources
- key_constraints

### 5.12 `design_check_report.json`

作用：汇总所有 verifier 的检查结果，作为最终 gate 判断依据之一。

---

## 6. `read_knowbase_context` 设计

### 6.1 定位

它的目标不是读取完整 knowbase，而是：

> 基于当前 feature 与 backend 平台，提取真正相关的知识上下文。

### 6.2 输入

- `final_prd.json`
- `knowbase_refs.json`

### 6.3 输出

- `knowbase_context.json`

### 6.4 提取内容

业务约束：

- feature_goal
- core_flows
- domain_constraints

架构约束：

- service_boundaries
- module_constraints
- integration_constraints

规则约束：

- layering_rules
- api_rules
- data_rules
- testing_rules
- anti_patterns

技术栈事实：

- language
- framework
- storage
- cache
- mq

### 6.5 结论

Design Mission 中已经明确：

> 后续 design skill 不应各自直接扫描 knowbase 原文，而应统一消费 `knowbase_context.json`。

---

## 7. Backend Skills 设计

当前后端 skill 已收敛为：

- `design.backend.read_inputs`
- `design.backend.read_knowbase_context`
- `design.backend.scope_alignment`
- `design.backend.api_contract`
- `design.backend.domain_model`
- `design.backend.flow_model`
- `design.backend.storage_plan`
- `design.backend.quality_plan`
- `design.backend.compile_doc`
- `design.backend.verify`

这些 skill 的共同要求是：

- 单职责
- 固定输入
- 固定输出
- 结构化产物优先
- 可被 Claude Code / Codex 消费
- 可被 verifier 独立校验

---

## 8. `api_contract.yaml` 方案

### 8.1 定位

`api_contract.yaml` 当前已经明确为：

> 后端设计的中轴资产

它不仅定义接口，还定义：

- 行为
- side effects
- consistency
- testability
- acceptance mapping

### 8.2 顶层结构

当前结论中其顶层结构包括：

- version
- feature_id
- feature_name
- service
- owners
- status
- design_basis
- global_conventions
- apis
- events
- jobs
- shared_types
- verification_mapping

### 8.3 API 级字段

每个 API 已经明确应至少包含：

- id
- name
- summary
- kind
- protocol
- method
- path
- tags
- ownership
- auth
- idempotency
- request
- response
- errors
- side_effects
- state_effects
- consistency
- observability
- dependencies
- acceptance_refs
- test_requirements

### 8.4 `errors`

每个错误至少包含：

- code
- category
- http_status
- retryable
- user_visible
- description

### 8.5 `side_effects`

固定为：

- writes
- publishes
- cache_updates
- external_calls

### 8.6 `consistency`

固定为：

- mode
- boundary
- client_expectation

### 8.7 `events`

`event` 已经提升为 contract 一级公民，至少包含：

- id
- name
- topic
- producer
- consumers
- trigger
- payload
- delivery
- observability
- acceptance_refs
- test_requirements

### 8.8 `jobs`

`job` 也进入 contract 体系，至少包含：

- id
- name
- trigger
- schedule
- module
- input
- effects
- failure_policy
- observability
- acceptance_refs

### 8.9 `shared_types`

统一 request / response / event payload schema。

### 8.10 `verification_mapping`

直接为 Verification Mission 提供：

- AC → contract 映射
- contract → checks 映射

---

## 9. `backend_task_graph.json` 方案

### 9.1 定位

它是：

> Design Mission → Coding Mission 的桥接资产。

### 9.2 顶层结构

当前结论中其顶层结构包括：

- version
- feature_id
- service
- generated_from
- execution_policy
- tasks
- checkpoints
- final_gate

### 9.3 task 标准字段

每个 task 当前已统一为：

- id
- title
- category
- module
- depends_on
- parallel_group
- priority
- from_contract
- from_design_artifacts
- acceptance_refs
- goal
- files_hint
- implementation_notes
- done_when
- verification_hooks
- retryable
- blocking

### 9.4 task 分类

当前固定为 8 类：

- api
- domain
- storage
- integration
- event
- job
- observability
- test

### 9.5 task 拆分规则

当前已明确：

每个 API 最少拆出：

- api
- domain
- test

如满足条件，再增加：

- 有持久化写入 → storage
- 有外部依赖 → integration
- 有事件发布 → event
- 有异步恢复 → job
- 有观测要求 → observability

### 9.6 依赖规则

当前默认依赖关系为：

- domain 先于 storage
- storage / domain 先于 api
- event 依赖 api / storage
- job 依赖 event
- test 依赖被测 task
- observability 依赖被观测对象

### 9.7 粒度规则

当前已明确：

- 不能过粗
- 不能没有完成标准
- 应能在一次 coding loop 内完成
- `done_when` 必须是可观察完成条件

### 9.8 `verification_hooks`

建议标准枚举为：

- compile
- lint
- unit_test
- integration_test
- contract_test
- smoke_test
- manual_rule_check

### 9.9 `checkpoints`

用于把任务图切成若干阶段里程碑，方便 Coding Mission 分阶段闭环。

### 9.10 `final_gate`

用于定义 backend implementation 何时 truly ready。

---

## 10. `backend_design.md` 方案

### 10.1 定位

它是：

> 结构化设计资产的人类可读编译版

不是 machine-readable 主资产。

### 10.2 固定章节

当前已经固定为：

- Overview
- Design Basis
- Scope and Responsibilities
- API Contract Summary
- Domain Model Summary
- Main Flows and Error Flows
- Storage and Dependencies
- Reliability and Quality Plan
- Risks and Deferred Items
- Coding Task Breakdown
- Verification Mapping
- Open Issues

### 10.3 写法原则

已明确：

- 只写摘要
- 不复制整段 yaml/json
- 每节都能追溯到结构化 artifact
- 方便人快速审阅

---

## 11. Verifier 体系

当前 Backend Design Mission 已明确的 verifier 包括：

- `backend_prd_coverage_verifier`
- `backend_contract_completeness_verifier`
- `backend_domain_integrity_verifier`
- `design_knowbase_alignment_verifier`
- `design_stack_conformance_verifier`
- `backend_operability_verifier`
- `backend_task_executability_verifier`

此外还细化出专属 verifier：

contract 侧：

- `api_contract_schema_verifier`
- `api_contract_completeness_verifier`
- `api_contract_rule_alignment_verifier`
- `api_contract_ac_mapping_verifier`
- `api_contract_testability_verifier`

task graph 侧：

- `task_graph_schema_verifier`
- `task_graph_dag_verifier`
- `task_graph_granularity_verifier`
- `task_graph_coverage_verifier`

---

## 12. Gate 体系

当前 Backend Design Mission 已明确 3 个 gate：

### 12.1 Scope Gate

通过条件：

- 后端职责明确
- 前后端边界明确
- knowbase 关键约束已纳入

### 12.2 Contract Gate

通过条件：

- API contract 完整
- domain model 完整
- flow model 完整
- storage plan 完整

### 12.3 Implementation Ready Gate

通过条件：

- operability 设计完整
- task graph 可执行
- acceptance mapping 完整
- 无 blocking issue

---

## 13. Analyzer 体系

当前已明确 3 类 analyzer：

- `backend_scope_analyzer`
- `backend_contract_analyzer`
- `backend_ready_gate_analyzer`

统一输出格式为：

- failure_type
- reasons
- repair_actions
- resume_from

---

## 14. 当前 Backend Design Mission 的总体结论

到目前为止，Backend Design Mission 已经收敛出的结论是：

### 14.1 本质

不是写设计说明，而是生成一组 implementation-ready 设计资产。

### 14.2 输入模型已经固定

即：

```text
final_prd + repo_context + knowbase_context
```

### 14.3 Knowbase 已经被纳入设计输入

通过 `read_knowbase_context` 注入，而不是独立主流程。

### 14.4 已形成完整链路

```text
final_prd
+ repo_context
+ knowbase_context
→ backend_scope.json
→ api_contract.yaml
→ domain_model.json
→ flow_model.json
→ storage_plan.json
→ quality_plan.json
→ risk_register.json
→ backend_task_graph.json
→ backend_design.md
→ design_check_report.json
```

### 14.5 两个核心中轴已经明确

- `api_contract.yaml`
- `backend_task_graph.json`

### 14.6 已具备进入工程实现定义的条件

也就是已经可以进一步落成：

- workflow config
- skill mapping
- schema 文件
- verifier 规则实现

---

## 15. 后续展开方向

当前这一版后端设计方案已经足够作为 Backend Design Mission 的主文档。

后续可以继续展开为：

- schema 文件
- skill 目录与 `SKILL.md`
- verifier 脚本
- gate 实现规则
- 与 Frontend Design Mission 的 contract 对齐机制
