from typing import Optional
from .models import StreamState
from .service import MockExternalStreamService
from .tools import create_tools

class AVCallManager:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = AVCallManager()
        return cls._instance

    def __init__(self):
        self.state: StreamState = StreamState.IDLE
        self.current_stream_id: Optional[str] = None
        self.stream_service = MockExternalStreamService(state_change_callback=self._on_stream_state_change)
        self.mcp_server = None

    def init_tools(self, mcp_server, add_tool_func, property_list_class, property_class, property_type_enum):
        self.mcp_server = mcp_server
        create_tools(add_tool_func, property_list_class, property_class, property_type_enum)

    async def _on_stream_state_change(self, stream_id: str, is_active: bool):
        """推流服务的核心回调，用于处理状态变更和发送通知"""
        if self.current_stream_id != stream_id:
            return

        if not is_active:
            print(f"【AVCallManager】: 推流 {stream_id} 已结束。状态变为空闲。")
            self.state = StreamState.IDLE
            self.current_stream_id = None
            
            if self.mcp_server and self.mcp_server._send_callback:
                print("【AVCallManager】: 向服务端发送 'stream_ended' 通知...")
                notification = {
                    "jsonrpc": "2.0",
                    "method": "notifications/streamStateChanged",
                    "params": {"stream_id": stream_id, "state": "ended"}
                }
                # 使用 mcp_server 的内部方法异步发送通知
                # 注意：此处需要将dict转换为字符串
                import json
                await self.mcp_server._send_callback(json.dumps(notification))

    async def start_stream(self) -> str:
        if self.state == StreamState.STREAMING:
            return "无法开启，当前已经有一个通话正在进行中。"

        print("【AVCallManager】: 准备开启新的推流...")
        self.state = StreamState.STREAMING
        try:
            self.current_stream_id = await self.stream_service.start_stream()
            return "已开启视频通话，请等待后台人员连接。"
        except Exception as e:
            self.state = StreamState.IDLE
            self.current_stream_id = None
            return f"开启通话失败: {e}"

    async def stop_stream(self) -> str:
        if self.state == StreamState.IDLE or not self.current_stream_id:
            return "当前没有正在进行的通话可以关闭。"
        
        await self.stream_service.stop_stream(self.current_stream_id)
        # 状态的清理将在 _on_stream_state_change 回调中完成
        return "通话已关闭。"

    def get_stream_status(self) -> str:
        return f"当前的通话状态是: {self.state.name}。"

def get_av_call_manager():
    return AVCallManager.get_instance()