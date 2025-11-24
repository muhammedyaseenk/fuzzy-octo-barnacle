# app/core/resource_manager.py
import asyncio
import psutil
import gc
from contextlib import asynccontextmanager
from typing import Optional
from app.core.config import settings

class ResourceManager:
    """Prevent memory leaks and resource exhaustion"""
    
    def __init__(self):
        self.max_memory_percent = 80
        self.max_connections = 1000
        self.active_tasks = set()
    
    async def monitor_resources(self):
        """Background task to monitor and cleanup resources"""
        while True:
            try:
                # Memory check
                memory = psutil.virtual_memory()
                if memory.percent > self.max_memory_percent:
                    gc.collect()
                    await self.cleanup_idle_connections()
                
                # Task cleanup
                self.active_tasks = {t for t in self.active_tasks if not t.done()}
                
                await asyncio.sleep(30)
            except Exception as e:
                print(f"Resource monitor error: {e}")
    
    async def cleanup_idle_connections(self):
        """Force cleanup of idle database connections"""
        from app.core.db import engine
        await engine.dispose()
    
    @asynccontextmanager
    async def track_task(self, task_name: str):
        """Track long-running tasks"""
        task = asyncio.current_task()
        self.active_tasks.add(task)
        try:
            yield
        finally:
            self.active_tasks.discard(task)
    
    def get_stats(self) -> dict:
        """Get current resource usage"""
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=1)
        return {
            "memory_percent": memory.percent,
            "memory_available_mb": memory.available / (1024 * 1024),
            "cpu_percent": cpu,
            "active_tasks": len(self.active_tasks)
        }

resource_manager = ResourceManager()
