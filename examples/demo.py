import sys, os
import asyncio

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import the library
from use_event import on, emit, off, EventBus


@on("async_event", priority=10)
async def async_handler(data):
    # await asyncio.sleep(0.1)
    print(f"Async: {data}")

@on("async_event", priority=5)
def sync_handler(data):
    print(f"Sync: {data}")

# 自动检测并正确处理同步/异步混合执行
# emit("async_event", "mixed data")


from use_event import on, emit

@on("error_test")
def failing_handler():
    raise ValueError("This will not crash the program")

@on("error_test")
def working_handler():
    print("This will still execute")

emit("error_test")  # 程序继续正常运行