PYTHON ?= python3
WORKSPACE_ROOT ?= .
KNOWLEDGE_ROOT ?= semantic-store

.PHONY: knowbase-accumulate knowbase-pr-merge

knowbase-accumulate:
	$(PYTHON) scripts/run_knowbase_accumulation.py \
		--workspace-root $(WORKSPACE_ROOT) \
		--knowledge-root $(KNOWLEDGE_ROOT)

knowbase-pr-merge:
	$(PYTHON) scripts/run_pr_merge_promotion.py \
		--workspace-root $(WORKSPACE_ROOT) \
		--knowledge-root $(KNOWLEDGE_ROOT)
