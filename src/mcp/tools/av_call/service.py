import asyncio
import uuid
from typing import Callable

class MockExternalStreamService:
    """模拟一个外部的、异步的推流服务"""

    def __init__(self, state_change_callback: Callable):
        self.state_change_callback = state_change_callback
        self.current_stream_id = None
        self.stream_task = None

    async def start_stream(self) -> str:
        """模拟开始推流，返回一个唯一的推流ID"""
        if self.stream_task and not self.stream_task.done():
            raise Exception("A stream is already active.")

        self.current_stream_id = str(uuid.uuid4())
        print(f"【推流服务】: 开始推流... Stream ID: {self.current_stream_id}")
        
        # 模拟推流是一个持续的过程
        self.stream_task = asyncio.create_task(self._simulate_streaming())
        
        return self.current_stream_id

    async def _simulate_streaming(self):
        """模拟推流过程，例如每5秒打印一次日志"""
        try:
            while True:
                await asyncio.sleep(5)
                print(f"【推流服务】: Stream {self.current_stream_id} 正在推流中...")
        except asyncio.CancelledError:
            # 当任务被取消时，会抛出此异常
            print(f"【推流服务】: Stream {self.current_stream_id} 的模拟任务被取消。")
        finally:
            print(f"【推流服务】: Stream {self.current_stream_id} 已停止。")
            await self.state_change_callback(self.current_stream_id, is_active=False)

    async def stop_stream(self, stream_id: str):
        """模拟停止推流"""
        if stream_id != self.current_stream_id or not self.stream_task or self.stream_task.done():
            # 如果ID不匹配，或者任务不存在/已完成，则不执行任何操作
            return

        print(f"【推流服务】: 正在停止 Stream ID {stream_id}...")
        self.stream_task.cancel() # 取消正在运行的推流任务