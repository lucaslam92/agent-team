# iOS Architecture

## Scope

- 适用于 iOS 客户端模块、SwiftUI 视图、导航、状态管理与数据访问边界。

## UI And State

- Swift 为默认语言
- SwiftUI 为默认 UI 模型
- 视图层只负责渲染和轻量交互
- 可观察状态对象负责页面状态和副作用编排
- 导航协调逻辑不应散落在每个 View 内部

## Module Boundaries

- `view`
- `view model / presentation`
- `domain`
- `data / gateway`

依赖关系保持单向，避免在视图层直接访问底层数据实现。
