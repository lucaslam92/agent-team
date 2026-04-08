# Web Architecture

## Scope

- 适用于 Web 前端页面、路由、共享组件、页面状态与数据获取层。

## UI And State

- 页面层负责组合组件、触发 use case，不直接承载复杂业务规则
- 共享组件应与页面业务解耦，通过 props / state contract 复用
- server state、page state、transient interaction state 需要分层表达
- 路由层负责页面边界，不承担数据拼装细节

## Default Stack

- TypeScript 优先
- React 组件模型优先
- 继续沿用仓库既有路由和样式方案，不在单个任务中随意引入新栈

## Component Boundaries

- design-system components
- domain components
- page-local components

只有当复用场景稳定时，才允许把 page-local component 提升到共享层。

## Data Flow

- 接口契约由 API 文档或 typed client 驱动
- 页面不要直接依赖裸接口返回结构做多层透传
- 派生展示状态应通过 selector / adapter 计算，不要散落在 JSX 中
