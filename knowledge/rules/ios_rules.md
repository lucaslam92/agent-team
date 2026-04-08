# iOS Rules

## Scope

- 适用于 iOS 模块、SwiftUI 视图、导航、状态与数据访问实现。

## Architecture Rules

- View 负责渲染与轻交互，不直接承载复杂业务逻辑
- presentation / view model 层负责状态收敛与副作用编排
- data / gateway 层负责接口、缓存、持久化与错误映射
- 领域规则优先放在 domain/use case，而不是分散在多个 View 中

## UI Rules

- SwiftUI 视图应保持可组合、可测试、可预览
- 导航与页面编排不应散在多个子视图内
- 页面状态要明确区分加载、空、失败、成功
- 文案和交互边界应与产品需求保持可追踪关系

## Testing Rules

- ViewModel 或 presentation 层状态转换需要测试
- 关键 View 至少验证主流程展示与错误态
- gateway/data 层需要覆盖契约映射与失败回退

## Anti-Patterns

- 在 View 中直接处理复杂异步编排
- 依赖全局单例跨页面传递业务状态
- 视图层直接依赖底层网络模型
