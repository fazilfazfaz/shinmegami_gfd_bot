import asyncio
import logging
from typing import Callable, Any


class QueueBasedWorker:
    def __init__(self):
        self.queue = asyncio.Queue()
        self._worker_task = None

    async def start(self):
        if self._worker_task is not None and not self._worker_task.done():
            return
        self._worker_task = asyncio.create_task(self._worker())

    async def clear(self):
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                self.queue.task_done()
            except asyncio.QueueEmpty:
                pass

    def submit(self, func: Callable, *args: Any, **kwargs: Any):
        self.queue.put_nowait((func, args, kwargs))

    async def _worker(self):
        while True:
            task = await self.queue.get()
            func, args, kwargs = task
            try:
                await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            except Exception as e:
                logging.error('Failure to process queue worker item' + str(e))
            finally:
                self.queue.task_done()
