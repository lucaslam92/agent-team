# Knowbase 积累设计文档（v1）

## 1. 目标

本文档定义结构化知识积累方案。

系统采用双层知识结构：

- `knowledge/`：长期人类可读知识
- `semantic-store/`：结构化语义知识与索引

统一目标链路为：

```text
signals
-> graph
-> interpreter
-> candidate cards
-> dedupe
-> promote
-> semantic-store/normalized
```

## 2. 边界

- `knowledge/` 负责长期背景、架构、规则、ADR、playbooks
- `semantic-store/generated/` 负责候选卡片与中间产物
- `semantic-store/normalized/` 负责正式结构化知识
- `semantic-store/index/` 负责 graph index
- `semantic-store/state/` 负责 registry 和 promotion state

## 3. 两条积累路径

### 3.1 需求闭环后沉淀

`mission outputs + merged code + verification artifacts -> extract -> graph -> interpreter -> candidates -> promote`

### 3.2 自动收集

`code/docs/artifacts changes -> extract -> graph -> interpreter -> generated candidates`

自动收集默认只进入 `generated/`，不直接写 `normalized/`。

## 4. 晋升原则

- generated 与 normalized 必须分层
- capability 可更积极自动晋升
- feature / rule 默认更保守
- 冲突必须显式记录

## 5. 目录建议

```text
knowledge/
  business/
  architecture/
  rules/
  decisions/
  playbooks/
semantic-store/
  generated/
  normalized/
  index/
  state/
```
