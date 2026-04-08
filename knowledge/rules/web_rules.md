# Web Rules

## Scope

- 适用于 Web 页面、组件、路由、数据获取和样式组织。

## Architecture Rules

- 页面负责编排，组件负责展示，adapter/selector 负责视图数据转换
- 不在页面 JSX 中混入大段业务分支和接口兼容逻辑
- 不跨页面直接依赖别的页面内部组件
- typed API client 或 adapter 层是契约边界，避免裸 response shape 直通 UI

## UI Rules

- 表单、弹窗、列表、详情等基础模式优先复用既有组件
- 路由层只处理页面边界与参数，不承担业务编排
- 用户可见文案必须可追踪到产品需求或 string rules
- 大页面必须区分 server state、page state、transient state

## Testing Rules

- 关键页面至少覆盖渲染、交互和错误态
- 复杂状态转换需要有 selector 或 state logic 测试
- 关键接口适配层需要有 contract-oriented 测试

## Anti-Patterns

- 页面组件直接发起多个分散请求且无统一状态管理
- 组件内部硬编码接口路径或错误码分支
- 在共享组件中嵌入页面专属业务判断
