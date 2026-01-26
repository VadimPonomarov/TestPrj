import asyncio
import time
from functools import wraps
from typing import Callable, TypeVar, Any

F = TypeVar('F', bound=Callable[..., Any])

def time_execution(description: str = None) -> Callable[[F], F]:
    """
    Декоратор для замера времени выполнения функции.
    Выводит только общее время выполнения в конце.
    
    Args:
        description: Описание операции для вывода в лог.
                   Если не указано, будет использовано имя функции.
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            result = await func(*args, **kwargs)
            elapsed = time.time() - start_time
            func_name = description or func.__name__
            print(f"\n[TIMING] {func_name} выполнен за {elapsed:.2f} секунд")
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            func_name = description or func.__name__
            print(f"\n[TIMING] {func_name} выполнен за {elapsed:.2f} секунд")
            return result
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator
