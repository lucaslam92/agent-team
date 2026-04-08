# Frontend Stack

## Goal

前端相关知识需要同时覆盖 Web、Android、iOS，但不要把三端混成一套抽象过度的规范。

本文件定义跨端统一原则，各端具体约束再落到各自 architecture/rules 文档。

## Default Stack

默认技术栈约定如下：

- Web
  - TypeScript
  - React 组件模型
  - 仓库既有路由方案
  - 仓库既有样式方案
- Android
  - Kotlin
  - Jetpack Compose 优先
  - ViewModel + state holder
- iOS
  - Swift
  - SwiftUI 优先
  - Observable state / coordinator-like navigation

如需偏离以上默认栈，必须在 ADR 或 repo-local rules 中记录原因。

## Shared Frontend Principles

- 组件应优先保持可组合，而不是把业务流程写死在单个页面
- 页面层负责编排，不负责复杂业务规则
- 远程数据、页面状态、派生 UI 状态应分开表达
- 交互文案、错误态、空态必须可追踪到产品要求
- 不在 UI 层直接硬编码后端契约特例

## State Model

状态建议拆成三类：

- server state
- view state
- transient interaction state

不要把三类状态混在同一个巨型 store 或单个页面对象里。

## Component Reuse

组件复用优先级：

1. 设计系统组件
2. 领域组件
3. 页面局部组件

只有当两个以上场景已经稳定复用时，才应把页面局部组件提升为共享组件。
