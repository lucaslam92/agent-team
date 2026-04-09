# Coding Mission Remaining Tasks (as of 2026-04-08)

## Completion Snapshot

Current implementation has completed the MVP orchestration chain and outputs the 9 core artifacts:

- `execution_context.json`
- `selected_task_batch.json`
- `task_execution_report.json`
- `changed_files.json`
- `implementation_evidence.json`
- `coding_design_trace.json`
- `coding_check_report.json`
- `verification_handoff.json`
- `coding_summary.md`

## Remaining Work (Prioritized)

### P0 (Blocking for production use)

1. **Schema validation enforcement in runtime**
   - Validate all generated JSON artifacts against `docs/schemas/coding/*.schema.json` before write and/or before handoff.
   - Fail `coding_handoff_ready_gate` when schema validation fails.

2. **Endpoint-specific evidence execution matrix**
   - Execute `compile/lint/integration/contract/smoke` by `endpoint + stack_profile` rather than one flat command list.
   - Ensure each selected task has at least one relevant evidence command for its profile.

3. **Coverage gating and thresholds**
   - Add explicit gate criteria for acceptance coverage:
     - selected tasks covered by verification hooks
     - changed files covered by at least one test/evidence command
     - acceptance criteria (`done_when`) trace completeness

### P1 (Strongly recommended)

4. **Split execution stage into dedicated runners**
   - Implement standalone script entrypoints for:
     - `coding.backend.execute_tasks`
     - `coding.frontend.execute_tasks`
     - `coding.compile_report`
   - Keep orchestrator as composition layer only.

5. **Stronger dependency readiness checks**
   - Extend task readiness to include checkpoint/contract/resource completeness checks (not only depends_on + blocked + asset flag).

6. **Verification handoff quality checks**
   - Enforce `verification_handoff.status=ready` only when no failed hooks and required evidence groups are present.

### P2 (Scale/readability)

7. **Per-endpoint summary sections in `coding_summary.md`**
   - Show status, changed files, and failed checks grouped by endpoint.

8. **Drift detection between design and implementation**
   - Flag tasks/files without `design_artifact_refs` or missing acceptance mappings.

## Definition of Done for “Coding Phase Complete”

Coding phase is considered complete only when:

- All selected tasks are mapped to design artifacts and acceptance references.
- Evidence execution is profile-aware for every endpoint in batch.
- `coding_check_report.summary.status` is `passed` or approved `degraded` with explicit risks.
- `verification_handoff.json` is `ready` and schema-valid.
