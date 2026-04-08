# Frontend Design Mission 技术方案（v1）

## 1. 目标

Frontend Design Mission 的目标不是产出一篇“前端设计说明文档”，而是：

> 把 `final_prd` 转换成可实施、可拆解、可验证、可被 Coding Mission 直接消费的前端设计资产。

因此 Frontend Design Mission 的核心要求是：

- 可读
- 可机读
- 可追溯
- 可拆任务
- 可验证
- 可进入 Coding Mission

一句话概括：

> Frontend Design Mission = 将需求合同编译为 implementation-ready frontend contract。

---

## 2. 输入模型

Frontend Design Mission 当前统一输入模型为：

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

表示当前前端代码与工程上下文，包括：

- 仓库结构
- 页面/模块清单
- 现有路由
- 现有组件组织
- 现有状态管理方式
- 现有技术栈
- 当前架构约束

典型输入可包括：

```text
repo_context.json
ui_inventory.json
existing_routes.json
frontend_architecture_constraints.json
```

### 2.3 `knowbase_context`

来自 Knowbase 的结构化提取结果。

这里的原则已经固定：

> Knowbase 在 Design Mission 中只是输入增强层，通过 `read_knowbase_context` 注入，不作为独立 Mission。

包含：

- 业务背景
- 前端架构约束
- frontend rules
- API rules
- testing rules
- 技术栈约束
- 组件反模式
- 已引用的 knowbase 来源

### 2.4 可选增强输入

Frontend Design Mission 允许消费以下增强输入：

- `api_contract.yaml`
- `figma_context.json`
- `design_tokens.json`
- `existing_ui_inventory.json`

输入优先级建议固定为：

```text
api_contract.yaml
> final_prd accepted behavior
> figma / visual context
> repo existing UI patterns
> knowbase rules
```

---

## 3. 总体流程

Frontend Design Mission 的总体流程当前收敛为：

```text
read_design_inputs
→ read_knowbase_context
→ frontend_scope_alignment
→ frontend_contract_alignment
→ frontend_information_architecture
→ frontend_interaction_design
→ frontend_state_model_design
→ frontend_component_design
→ frontend_data_binding_design
→ frontend_quality_and_risk_design
→ compile_frontend_design
→ verify_frontend_design
```

---

## 4. Frontend Design Mission

### 4.1 定位

Frontend Design Mission 的目标是：

> 基于 `final_prd`、`repo_context`、`knowbase_context`，并在可用时消费 `api_contract.yaml`，生成 implementation-ready frontend design assets。

它不负责：

- 写代码
- 最终联调
- 执行 build/test
- 替代视觉设计工具本身

它只负责：

- 明确前端职责边界
- 明确页面/组件/状态/交互设计
- 消费后端 contract 或在缺失时建立 fallback contract
- 生成 coding-ready task graph
- 验证设计是否足够进入 Coding Mission

### 4.2 核心问题

Frontend Design Mission 需要回答以下问题：

- 前端负责什么
- 前端不负责什么
- 前后端边界是什么
- 页面结构与导航结构如何组织
- 组件如何拆分
- 状态模型如何设计
- 前端如何消费 API / event / async job 结果
- 无后端 contract 时如何基于 `final_prd` 暂行设计
- Figma / design token / 视觉规范如何进入设计链路
- 如何拆成 Coding Mission 可执行任务
- 如何验证设计完整性、可实施性与一致性

### 4.3 Frontend 流程

当前前端设计流程为：

```text
read_design_inputs
→ read_knowbase_context
→ frontend_scope_alignment
→ frontend_contract_alignment
→ frontend_information_architecture
→ frontend_interaction_design
→ frontend_state_model_design
→ frontend_component_design
→ frontend_data_binding_design
→ frontend_quality_and_risk_design
→ compile_frontend_design
→ verify_frontend_design
```

---

## 5. 前端设计产物

当前已经明确的前端设计产物如下：

```text
artifacts/design/frontend/
  frontend_scope.json
  knowbase_context.json
  frontend_contract_view.json
  page_map.json
  navigation_map.json
  ui_structure.json
  state_model.json
  component_spec.json
  interaction_spec.json
  data_binding_plan.json
  quality_plan.json
  risk_register.json
  frontend_task_graph.json
  frontend_design.md
  design_context_snapshot.json
  design_check_report.json
```

对应的 schema 草稿统一放在：

```text
docs/schemas/frontend-design/
```

### 5.1 `frontend_scope.json`

作用：定义前端职责边界。

包含：

- frontend_responsibilities
- backend_responsibilities
- shared_contracts
- out_of_scope
- assumptions

### 5.2 `knowbase_context.json`

作用：统一承载本次设计所需的 knowbase 结构化上下文。

包含：

- business_context
- architecture_constraints
- frontend_rules
- api_rules
- testing_rules
- technical_stack
- resolved_references

### 5.3 `frontend_contract_view.json`

这是 Frontend Design Mission 中最核心的中轴产物之一。

它的定位不是复制后端 contract，而是：

> 前端消费视角下的 contract 编译结果

它直接连接：

- Backend Design Mission
- Coding Mission
- Verification Mission

### 5.4 `page_map.json`

作用：定义页面与场景映射。

包含：

- pages
- entry_points
- page_goals
- acceptance_refs

### 5.5 `navigation_map.json`

作用：定义页面流转、路由、导航参数与守卫。

包含：

- routes
- transitions
- guards
- params
- deeplink_rules

### 5.6 `ui_structure.json`

作用：定义页面布局区块与组件层次。

包含：

- page_sections
- component_tree
- reusable_blocks
- empty_loading_error_states

### 5.7 `state_model.json`

作用：定义前端状态模型。

包含：

- server_state
- view_state
- transient_state
- derived_state
- state_transitions

### 5.8 `component_spec.json`

作用：定义组件 contract。

包含：

- components
- props
- events
- dependencies
- reuse_level
- constraints

### 5.9 `interaction_spec.json`

作用：定义关键交互行为。

包含：

- user_actions
- validations
- feedback
- optimistic_updates
- retry_patterns
- degraded_experience

### 5.10 `data_binding_plan.json`

作用：定义前端如何绑定 API / event / cache / local state。

包含：

- request_bindings
- response_mapping
- error_mapping
- cache_strategy
- polling_or_subscription
- async_refresh_rules

### 5.11 `quality_plan.json`

作用：把工程质量要求前置到设计阶段。

包含：

- accessibility
- performance_budget
- state_consistency
- error_handling
- observability
- rollout_plan
- fallback_plan

### 5.12 `risk_register.json`

作用：记录风险、影响与缓解措施。

### 5.13 `frontend_task_graph.json`

作用：

> 把设计资产翻译为 Coding Mission 可直接消费的任务图。

它是 Design → Coding 的关键桥接资产。

### 5.14 `frontend_design.md`

作用：

> 结构化设计产物的人类可读编译版

用于：

- 人审阅
- agent 快速理解全局设计
- 后续交付与追溯

### 5.15 `design_context_snapshot.json`

作用：记录本次设计的依据与引用来源。

包括：

- prd_source
- repo_context_sources
- knowbase_sources
- api_contract_source
- figma_sources
- key_constraints

### 5.16 `design_check_report.json`

作用：汇总所有 verifier 的检查结果，作为最终 gate 判断依据之一。

建议固定最小 schema：

- summary
  - overall_status
  - blocking_issue_count
  - warning_count
- gate_results
  - scope_gate
  - ux_contract_gate
  - implementation_ready_gate
  - criteria_results
  - analyzer_ref
- verifier_results
  - verifier_id
  - status
  - blocking
  - findings
  - repair_actions
- analyzer_results
  - analyzer_id
  - failure_type
  - reasons
  - repair_actions
  - resume_from
  - suggested_skill
  - suggested_command
  - target_artifacts
  - auto_fixable
  - repair_plan
    - step_id
    - summary
    - skill
    - target_artifacts
    - rationale
    - auto_fixable
    - command

`repair_plan.command` 可以直接执行，或交给 [`run_design_repair.py`](/Users/lindonghua/Documents/project/agent/auto-dev-agent/scripts/run_design_repair.py) 做 dry-run / 执行。
- unresolved_issues
- recommended_resume_from

---

## 6. `read_knowbase_context` 设计

### 6.1 定位

它的目标不是读取完整 knowbase，而是：

> 基于当前 feature 与 frontend 平台，提取真正相关的知识上下文。

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

- page_boundaries
- module_constraints
- component_constraints
- navigation_constraints

规则约束：

- frontend_rules
- api_rules
- testing_rules
- accessibility_rules
- anti_patterns

技术栈事实：

- language
- framework
- routing
- state_management
- design_system

### 6.5 结论

Design Mission 中已经明确：

> 后续 design skill 不应各自直接扫描 knowbase 原文，而应统一消费 `knowbase_context.json`。

---

## 7. Frontend Skills 设计

当前前端 skill 建议收敛为：

- `design.frontend.read_inputs`
- `design.frontend.read_knowbase_context`
- `design.frontend.scope_alignment`
- `design.frontend.contract_alignment`
- `design.frontend.information_architecture`
- `design.frontend.interaction_design`
- `design.frontend.state_model`
- `design.frontend.component_spec`
- `design.frontend.data_binding`
- `design.frontend.quality_plan`
- `design.frontend.compile_doc`
- `design.frontend.verify`

当前仓库中的对应 skill 目录为：

- `skills/design-frontend-read-inputs`
- `skills/design-frontend-read-knowbase-context`
- `skills/design-frontend-scope-alignment`
- `skills/design-frontend-contract-alignment`
- `skills/design-frontend-information-architecture`
- `skills/design-frontend-interaction-design`
- `skills/design-frontend-state-model`
- `skills/design-frontend-component-spec`
- `skills/design-frontend-data-binding`
- `skills/design-frontend-quality-plan`
- `skills/design-frontend-compile-doc`
- `skills/design-frontend-verify`

这些 skill 的共同要求是：

- 单职责
- 固定输入
- 固定输出
- 结构化产物优先
- 可被 Claude Code / Codex 消费
- 可被 verifier 独立校验

---

## 8. `frontend_contract_view.json` 方案

### 8.1 定位

`frontend_contract_view.json` 当前已经明确为：

> 前端设计的中轴资产之一

它不是后端 contract 的复制品，而是：

> 前端消费视角下的 contract 编译结果

### 8.2 输入来源

- 有 `api_contract.yaml` 时：
  - 直接消费并投影为前端视图
- 无 `api_contract.yaml` 时：
  - 从 `final_prd` 生成 `fallback_contracts`

### 8.3 顶层结构

当前结论中其顶层结构包括：

- version
- feature_id
- feature_name
- platform
- basis
- consumed_apis
- consumed_events
- local_commands
- async_states
- ui_visible_errors
- fallback_contracts
- acceptance_mapping

### 8.4 API 消费级字段

每个 consumed API 建议至少包含：

- id
- name
- purpose
- source_contract_ref
- request_shape
- response_shape
- ui_states
- error_states
- retry_behavior
- optimistic_behavior
- cache_behavior
- acceptance_refs
- test_requirements

### 8.5 `ui_visible_errors`

固定为：

- code
- category
- user_message_strategy
- retryable
- blocking

### 8.6 `async_states`

固定为：

- trigger
- pending_state
- success_state
- failure_state
- refresh_behavior

### 8.7 `fallback_contracts`

用于在缺失后端 `api_contract.yaml` 时，基于 `final_prd` 暂行生成前端消费合同。

### 8.8 `acceptance_mapping`

直接为 Verification Mission 提供：

- AC → UI/contract 映射
- UI behavior → checks 映射

---

## 9. `frontend_task_graph.json` 方案

### 9.1 定位

它是：

> Design Mission → Coding Mission 的桥接资产。

### 9.2 顶层结构

当前结论中其顶层结构包括：

- version
- feature_id
- platform
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

当前固定建议为：

- page
- component
- state
- data_binding
- contract_adapter
- interaction
- accessibility
- observability
- test

### 9.5 task 拆分规则

当前已明确：

每个关键页面最少拆出：

- page
- state
- test

如满足条件，再增加：

- 有复杂复用组件 → component
- 有接口绑定 → data_binding / contract_adapter
- 有复杂交互 → interaction
- 有埋点/监控要求 → observability
- 有无障碍要求 → accessibility

### 9.6 依赖规则

当前默认依赖关系为：

- state 先于 page
- contract_adapter / data_binding 先于 page
- component 先于 page
- interaction 依赖 page / state
- observability 依赖被观测对象
- test 依赖被测 task

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
- snapshot_test
- smoke_test
- manual_rule_check

### 9.9 `checkpoints`

用于把任务图切成若干阶段里程碑，方便 Coding Mission 分阶段闭环。

### 9.10 `final_gate`

用于定义 frontend implementation 何时 truly ready。

---

## 10. `frontend_design.md` 方案

### 10.1 定位

它是：

> 结构化设计资产的人类可读编译版

不是 machine-readable 主资产。

### 10.2 固定章节

当前已经固定为：

- Overview
- Design Basis
- Scope and Responsibilities
- Contract Consumption Summary
- Page and Navigation Summary
- UI Structure and Component Summary
- State Model Summary
- Data Binding Summary
- Quality and Performance Plan
- Risks and Deferred Items
- Coding Task Breakdown
- Verification Mapping
- Open Issues

### 10.3 写法原则

已明确：

- 只写摘要
- 不复制整段 json/yaml
- 每节都能追溯到结构化 artifact
- 方便人快速审阅

---

## 11. Figma 进入链路

### 11.1 定位

Figma 不是主合同，而是：

> 视觉与交互增强输入

### 11.2 使用原则

- 有 Figma 时：
  - 读取页面结构、关键交互、设计 token、组件规范
- 无 Figma 时：
  - 仍能基于 `final_prd + repo_context + knowbase_context` 产出 implementation-ready 前端设计
- Figma 不能覆盖 PRD 的行为合同
- Figma 不应替代组件规则和工程规则

### 11.3 建议中间产物

```text
figma_context.json
```

包含：

- frames
- component_refs
- tokens
- interaction_notes
- unresolved_visual_questions

---

## 12. Verifier 体系

当前 Frontend Design Mission 建议的 verifier 包括：

- `frontend_prd_coverage_verifier`
- `frontend_contract_alignment_verifier`
- `frontend_navigation_integrity_verifier`
- `frontend_state_model_verifier`
- `frontend_component_reuse_verifier`
- `design_knowbase_alignment_verifier`
- `frontend_stack_conformance_verifier`
- `frontend_operability_verifier`
- `frontend_task_executability_verifier`

此外还细化出专属 verifier：

contract 侧：

- `frontend_contract_view_schema_verifier`
- `frontend_contract_fallback_verifier`
- `frontend_ac_mapping_verifier`

task graph 侧：

- `frontend_task_graph_schema_verifier`
- `frontend_task_graph_dag_verifier`
- `frontend_task_graph_granularity_verifier`
- `frontend_task_graph_coverage_verifier`

---

## 13. Gate 体系

当前 Frontend Design Mission 已明确 3 个 gate：

### 13.1 Scope Gate

通过条件：

- 前端职责明确
- 前后端边界明确
- knowbase 关键约束已纳入

### 13.2 UX/Contract Gate

通过条件：

- contract consumption 完整
- 页面结构完整
- 状态模型完整
- 核心交互完整

### 13.3 Implementation Ready Gate

通过条件：

- 组件与状态拆分可执行
- task graph 可执行
- acceptance mapping 完整
- 无 blocking issue

---

## 14. Analyzer 体系

当前已明确 3 类 analyzer：

- `frontend_scope_analyzer`
- `frontend_contract_analyzer`
- `frontend_ready_gate_analyzer`

统一输出格式为：

- failure_type
- reasons
- repair_actions
- resume_from

---

## 15. 当前 Frontend Design Mission 的总体结论

到目前为止，Frontend Design Mission 已经收敛出的结论是：

### 15.1 本质

不是写前端设计说明，而是生成一组 implementation-ready frontend design assets。

### 15.2 输入模型已经固定

即：

```text
final_prd + repo_context + knowbase_context + optional api_contract + optional figma_context
```

### 15.3 Knowbase 已经被纳入设计输入

通过 `read_knowbase_context` 注入，而不是独立主流程。

### 15.4 已形成完整链路

```text
final_prd
+ repo_context
+ knowbase_context
+ optional api_contract
+ optional figma_context
→ frontend_scope.json
→ frontend_contract_view.json
→ page_map.json
→ navigation_map.json
→ ui_structure.json
→ state_model.json
→ component_spec.json
→ interaction_spec.json
→ data_binding_plan.json
→ quality_plan.json
→ risk_register.json
→ frontend_task_graph.json
→ frontend_design.md
→ design_check_report.json
```

### 15.5 两个核心中轴已经明确

- `frontend_contract_view.json`
- `frontend_task_graph.json`

### 15.6 已具备进入工程实现定义的条件

也就是已经可以进一步落成：

- workflow config
- skill mapping
- schema 文件
- verifier 规则实现

---

## 16. 与 Backend Design Mission 的关系

建议固定为：

- Backend Design Mission 负责“能力合同”
- Frontend Design Mission 负责“消费合同 + UI/interaction/state 编译”
- 两者通过以下资产衔接：
  - `api_contract.yaml`
  - `verification_mapping`
  - acceptance refs

一句话概括：

> Backend 设计输出系统能力合同，Frontend 设计输出用户体验与消费实现合同。

---

## 17. 后续展开方向

当前这一版前端设计方案已经足够作为 Frontend Design Mission 的主文档。

后续可以继续展开为：

- schema 文件
- skill 目录与 `SKILL.md`
- verifier 脚本
- gate 实现规则
- Figma context schema
- 与 Backend Design Mission 的 contract 对齐机制
