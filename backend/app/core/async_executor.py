"""
异步任务执行器
用于将阻塞任务转换为非阻塞的异步任务
"""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple
from functools import wraps
import time

logger = logging.getLogger(__name__)

class AsyncExecutor:
    """异步任务执行器"""
    
    def __init__(self, max_workers: int = 10, timeout: int = 300):
        """
        初始化异步执行器
        
        Args:
            max_workers: 最大工作线程数
            timeout: 任务超时时间（秒）
        """
        self.max_workers = max_workers
        self.timeout = timeout
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.running_tasks = {}  # 存储正在运行的任务
    
    async def run_in_thread(self, func: Callable, *args, timeout: Optional[int] = None, **kwargs) -> Any:
        """
        在线程池中运行阻塞函数
        
        Args:
            func: 要执行的函数
            timeout: 超时时间，None使用默认超时
            *args, **kwargs: 函数参数
            
        Returns:
            函数执行结果
            
        Raises:
            asyncio.TimeoutError: 任务超时
        """
        timeout = timeout or self.timeout
        task_id = f"{func.__name__}_{id(args)}_{time.time()}"
        
        try:
            logger.info(f"🚀 启动线程任务: {task_id}")
            self.running_tasks[task_id] = {
                "function": func.__name__,
                "start_time": time.time(),
                "status": "running"
            }
            
            # 使用asyncio.to_thread在线程池中执行同步函数
            result = await asyncio.wait_for(
                asyncio.to_thread(func, *args, **kwargs),
                timeout=timeout
            )
            
            duration = time.time() - self.running_tasks[task_id]["start_time"]
            logger.info(f"✅ 线程任务完成: {task_id}, 耗时: {duration:.2f}s")
            
            self.running_tasks[task_id]["status"] = "completed"
            self.running_tasks[task_id]["duration"] = duration
            
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"⏰ 线程任务超时: {task_id}, 超时时间: {timeout}s")
            self.running_tasks[task_id]["status"] = "timeout"
            raise
        except Exception as e:
            logger.error(f"❌ 线程任务失败: {task_id}, 错误: {e}")
            self.running_tasks[task_id]["status"] = "failed"
            self.running_tasks[task_id]["error"] = str(e)
            raise
        finally:
            # 清理已完成的任务记录（保留最近100个）
            if len(self.running_tasks) > 100:
                sorted_tasks = sorted(
                    self.running_tasks.items(),
                    key=lambda x: x[1].get("start_time", 0)
                )
                # 保留最新的50个任务
                self.running_tasks = dict(sorted_tasks[-50:])
    
    async def run_parallel_tasks(self, tasks: List[Tuple[Callable, tuple, dict]], 
                                max_concurrent: int = 5, timeout: Optional[int] = None) -> List[Any]:
        """
        并行执行多个任务
        
        Args:
            tasks: 任务列表，每个元素为(func, args, kwargs)
            max_concurrent: 最大并发数
            timeout: 单个任务超时时间
            
        Returns:
            所有任务的执行结果列表
        """
        timeout = timeout or self.timeout
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def run_single_task(func, args, kwargs):
            async with semaphore:
                return await self.run_in_thread(func, *args, timeout=timeout, **kwargs)
        
        # 创建所有任务的协程
        coroutines = [
            run_single_task(func, args, kwargs) 
            for func, args, kwargs in tasks
        ]
        
        # 并行执行所有任务
        results = await asyncio.gather(*coroutines, return_exceptions=True)
        return results
    
    def get_running_tasks_info(self) -> Dict[str, Any]:
        """获取正在运行的任务信息"""
        return {
            "total_tasks": len(self.running_tasks),
            "running_tasks": {
                k: v for k, v in self.running_tasks.items() 
                if v.get("status") == "running"
            },
            "completed_tasks": len([
                v for v in self.running_tasks.values() 
                if v.get("status") == "completed"
            ]),
            "failed_tasks": len([
                v for v in self.running_tasks.values() 
                if v.get("status") in ["failed", "timeout"]
            ])
        }
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)

# 创建全局执行器实例
async_executor = AsyncExecutor(max_workers=10, timeout=300)

def async_task(timeout: Optional[int] = None):
    """
    装饰器：将同步函数转换为异步函数
    
    Args:
        timeout: 任务超时时间
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await async_executor.run_in_thread(
                func, *args, timeout=timeout, **kwargs
            )
        return wrapper
    return decorator

# 便捷函数
async def run_in_background(func: Callable, *args, timeout: Optional[int] = None, **kwargs) -> Any:
    """在后台线程中运行阻塞函数"""
    return await async_executor.run_in_thread(func, *args, timeout=timeout, **kwargs)

async def run_with_timeout(coro: Coroutine, timeout: int) -> Any:
    """为协程添加超时控制"""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        logger.error(f"协程执行超时: {timeout}s")
        raise
