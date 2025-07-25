# use-event

一个类似Vue.js事件总线的Python事件库，提供简洁的事件发布订阅机制。

## 特性

- 🎯 **简洁API**: 核心方法 `on`、`emit`、`off`
- 🎨 **装饰器支持**: `@on("event_name")` 语法
- 🔄 **上下文管理器**: `with on("event", handler)` 自动清理
- ⚡ **优先级配置**: 支持处理器优先级排序
- 🔀 **混合执行**: 自动检测并支持同步/异步处理器
- 📦 **参数传递**: 支持位置参数和关键字参数
- 🛡️ **错误隔离**: 单个处理器异常不影响其他处理器
- 🪶 **轻量级**: 无外部依赖，遵循"不过度设计"原则

## 安装

```bash
pip install use-event
```

## 快速开始

### 基础用法

```python
from use_event import on, emit, off

# 装饰器模式注册事件处理器
@on("user_login")
def handle_login(user_id):
    print(f"User {user_id} logged in")

# 触发事件
emit("user_login", 123)

# 移除事件处理器
off("user_login", handle_login)
```

### 优先级配置

```python
from use_event import on, emit

@on("order_created", priority=1)  # 高优先级
def send_email(order_id):
    print(f"Sending email for order {order_id}")

@on("order_created", priority=2)  # 低优先级
def log_order(order_id):
    print(f"Logging order {order_id}")

emit("order_created", "ORD-001")
# 输出:
# Sending email for order ORD-001
# Logging order ORD-001
```

### 上下文管理器

```python
from use_event import on, emit

def temp_handler(data):
    print(f"Temporary handler: {data}")

# 临时注册处理器，自动清理
with on("temp_event", temp_handler):
    emit("temp_event", "test data")  # 会触发处理器

emit("temp_event", "test data 2")  # 不会触发处理器
```

### 异步支持

```python
from use_event import on, emit
import asyncio

@on("async_event")
async def async_handler(data):
    await asyncio.sleep(0.1)
    print(f"Async: {data}")

@on("async_event")
def sync_handler(data):
    print(f"Sync: {data}")

# 自动检测并正确处理同步/异步混合执行
emit("async_event", "mixed data")
```

### 参数传递

```python
from use_event import on, emit

@on("user_action")
def handle_action(action, user_id, timestamp=None, **kwargs):
    print(f"User {user_id} performed {action} at {timestamp}")
    print(f"Additional data: {kwargs}")

# 支持位置参数和关键字参数
emit("user_action", "click", 123, timestamp="2024-01-01", page="home")
```

### 多实例支持

```python
from use_event import EventBus

# 创建独立的事件总线实例
user_events = EventBus()
system_events = EventBus()

@user_events.on("action")
def user_handler(data):
    print(f"User: {data}")

@system_events.on("action")
def system_handler(data):
    print(f"System: {data}")

user_events.emit("action", "user clicked")
system_events.emit("action", "system backup")
```

## API 参考

### 核心函数

#### `on(event_name, handler=None, priority=0)`

注册事件监听器。

**参数:**
- `event_name` (str): 事件名称
- `handler` (callable, optional): 处理函数，为None时作为装饰器使用
- `priority` (int): 优先级，数值越小优先级越高

**返回:**
- 装饰器模式: 返回装饰器函数
- 上下文管理器模式: 返回 `EventContextManager`

#### `emit(event_name, *args, **kwargs)`

触发事件。

**参数:**
- `event_name` (str): 事件名称
- `*args`: 传递给处理器的位置参数
- `**kwargs`: 传递给处理器的关键字参数

#### `off(event_name, handler=None)`

移除事件监听器。

**参数:**
- `event_name` (str): 事件名称
- `handler` (callable, optional): 要移除的处理器，为None时移除所有处理器

### EventBus 类

创建独立的事件总线实例。

```python
from use_event import EventBus

bus = EventBus()
bus.on("event", handler)
bus.emit("event", data)
bus.off("event", handler)
```

## 错误处理

库内置错误隔离机制，单个处理器的异常不会影响其他处理器的执行：

```python
from use_event import on, emit

@on("error_test")
def failing_handler():
    raise ValueError("This will not crash the program")

@on("error_test")
def working_handler():
    print("This will still execute")

emit("error_test")  # 程序继续正常运行
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！