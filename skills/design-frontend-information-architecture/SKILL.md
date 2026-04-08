---
name: design.frontend.information_architecture
description: >
  Generate page, navigation, and UI structure assets before implementation starts.
  Use this skill whenever a user asks for page mapping, route design, information architecture,
  or the structural UI breakdown for a frontend feature.
---

Generate `page_map.json`, `navigation_map.json`, and `ui_structure.json`.

Use the script:

```bash
python skills/design-frontend-information-architecture/scripts/generate_information_architecture.py \
  --final-prd artifacts/prd/final_prd.json \
  --repo-context-snapshot artifacts/design/frontend/repo_context_snapshot.json \
  --frontend-scope artifacts/design/frontend/frontend_scope.json \
  --contract-view artifacts/design/frontend/frontend_contract_view.json \
  --page-map-output artifacts/design/frontend/page_map.json \
  --navigation-map-output artifacts/design/frontend/navigation_map.json \
  --ui-structure-output artifacts/design/frontend/ui_structure.json
```
