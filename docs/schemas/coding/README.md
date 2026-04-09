# Coding Mission Schemas

This directory defines core schema contracts for Coding Mission artifacts.

## Schemas

- `execution_context.schema.json`: coding run input snapshot and selected checkpoint context.
- `selected_task_batch.schema.json`: normalized output of `coding.select_task_batch`.
- `task_execution_report.schema.json`: per-task execution and hook outcome evidence.
- `changed_files.schema.json`: task-to-file trace map used by safety and handoff gates.
- `implementation_evidence.schema.json`: compile/lint/test/contract/smoke evidence summary.
- `coding_design_trace.schema.json`: task -> design -> acceptance trace payload.
- `coding_check_report.schema.json`: gate/verifier/analyzer summary output from `coding.verify`.
- `verification_handoff.schema.json`: structured payload handed to Verification Mission.

## Notes

- All schemas follow JSON Schema draft 2020-12.
- They align with `docs/CODING_MISSION_v1.md` section 8/11/13.
