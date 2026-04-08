# Backend Design Schemas

这组 schema 草稿对应 [`BACKEND_DESIGN_MISSION_v1.md`](/Users/lindonghua/Documents/project/agent/auto-dev-agent/docs/BACKEND_DESIGN_MISSION_v1.md) 里定义的后端设计输入与产物。

## Inputs

- `repo_context.schema.json`
- `knowbase_context.schema.json`

## Design Assets

- `backend_scope.schema.json`
- `api_contract.schema.yaml`
- `domain_model.schema.json`
- `flow_model.schema.json`
- `storage_plan.schema.json`
- `quality_plan.schema.json`
- `risk_register.schema.json`
- `backend_task_graph.schema.json`
- `design_context_snapshot.schema.json`
- `design_check_report.schema.json`

## Notes

- 这是 v1 草稿，优先保证字段契约清晰，而不是一次性做成最终严格校验。
- JSON schema 采用 Draft 2020-12。
- `api_contract.yaml` 的 schema 使用 YAML 形式表达 JSON Schema，方便和产物格式保持一致。
