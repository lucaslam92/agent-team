# Android Architecture

## Scope

- 适用于 Android 客户端模块、Compose UI、导航、状态管理与数据访问边界。

## UI And State

- Kotlin 为默认语言
- Jetpack Compose 为默认 UI 模型
- 页面状态由 ViewModel 或等价 state holder 管理
- UI composable 负责声明式渲染，不直接承载复杂业务流程
- 导航层只负责页面跳转与参数边界，不负责业务判断

## Module Boundaries

- `ui`
- `domain`
- `data`
- `platform / integration`

依赖方向保持单向，避免 feature module 之间直接耦合实现细节。
