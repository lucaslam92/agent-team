# Android Rules

## Scope

- 适用于 Android 模块、Compose UI、导航、状态与数据访问实现。

## Architecture Rules

- Compose UI 不直接访问 repository 或 gateway
- ViewModel 或等价 state holder 负责状态收敛与副作用编排
- data 层负责 DTO、cache、remote/local source 组合
- 领域规则优先放到 use case / domain，而不是散在 composable 中

## UI Rules

- composable 尽量保持无副作用、可预览、可复用
- 页面状态区分 persistent state 与 transient state
- 导航参数必须显式声明，不依赖隐式全局单例
- 用户可见错误态、空态、弱网态必须有统一表达

## Testing Rules

- ViewModel 状态转换需要测试
- 关键 composable 至少验证基础展示与交互
- data 层需要覆盖 remote/local fallback 与错误映射

## Anti-Patterns

- 在 composable 中直接执行复杂 IO
- 页面级 giant ViewModel 承担过多无关职责
- feature module 直接访问其他 feature 内部实现
