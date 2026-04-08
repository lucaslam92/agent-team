# Frontend Component Rules

## Scope

适用于 Web、Android、iOS 的组件层与页面层设计规范。

## Component Hierarchy

- design-system component
- domain component
- page-local component

默认从 page-local 开始，确认稳定复用后再向上提升。

## Usage Rules

- 组件输入应显式化，不依赖隐式全局状态
- 组件输出事件应语义明确，不暴露底层实现细节
- 复杂业务判断放到 container / view model / use case，不塞进纯展示组件
- 同一组件不要同时承担布局、业务编排、数据获取三种职责

## Constraints

- 不在共享组件中硬编码某个页面的业务术语
- 不在组件内部直接拼装后端契约特例
- 不在多个页面复制粘贴一套接近相同的 UI 逻辑而不抽象
- 不为了“复用”过早抽象出难以理解的万能组件

## Accessibility And States

每个用户可见组件都应考虑：

- loading
- empty
- error
- disabled
- success or confirmation

## Styling Rule

- 继续沿用仓库既有样式系统
- 新任务不要同时引入多套样式方案
- 视觉 token 优先于魔法数字
