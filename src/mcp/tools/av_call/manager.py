# 文件: py-xiaozhi/src/mcp/tools/av_call/manager.py

import asyncio
import os
import json # 确保导入 json
from token import OP
from typing import Optional
from pathlib import Path # 导入 Path
from .models import StreamState
from .service import ExternalStreamService
from .tools import create_tools
from src.utils.resource_finder import find_file # 导入正确的便捷函数
from src.utils.logging_config import get_logger
from src.constants.constants import DeviceState # 导入设备状态枚举

logger = get_logger(__name__)

class AVCallManager:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = AVCallManager()
        return cls._instance

    def __init__(self):
        if AVCallManager._instance is not None:
            logger.warning("AVCallManager instance already exists. Returning existing instance.")
             # 这里不应该抛出异常，而是遵循单例模式返回已有实例
             # 这个检查理论上不应该被触发，因为 get_instance 会处理
            return
             
        self.state: StreamState = StreamState.IDLE
        self.current_process_id: Optional[str] = None
        self.mcp_server = None
        self.is_stopping_manually = False

        script_relative_path = os.path.join("scripts", "start_call.sh")
        script_path_obj: Optional[Path] = find_file(script_relative_path)

        if script_path_obj is None:
            logger.error(f"严重错误：无法找到推流脚本 '{script_relative_path}'。请确保它位于 'scripts' 目录下。")
            self.script_full_path = None # 或者 raise FileNotFoundError(...)
        else:
            self.script_full_path = str(script_path_obj.resolve()) # 获取绝对路径字符串
            logger.info(f"定位到的推流脚本路径: {self.script_full_path}")

        self.stream_service = ExternalStreamService(
            script_path=self.script_full_path,
            on_exit_callback=self._on_stream_process_exit # 传递回调函数
        ) if self.script_full_path else None # 只有找到脚本才初始化服务

        AVCallManager._instance = self # 在初始化完成时赋值单例

    def init_tools(self, mcp_server, add_tool_func, property_list_class, property_class, property_type_enum):
        self.mcp_server = mcp_server
        create_tools(add_tool_func, property_list_class, property_class, property_type_enum)

    async def _on_stream_process_exit(self, process_id_str: str):
        """当推流脚本进程结束时的回调"""
        if self.current_process_id != process_id_str:
            return

        logger.info(f"【AVCallManager】: 推流进程 {process_id_str} 已结束。")

        original_state = self.state
        self.state = StreamState.IDLE
        self.current_process_id = None

        if not self.is_stopping_manually and original_state == StreamState.STREAMING:
            if self.mcp_server and hasattr(self.mcp_server, '_send_callback') and self.mcp_server._send_callback:
                logger.info("【AVCallManager】: 向服务端发送 'stream_ended' 通知 (因进程意外退出)...")
                notification = {
                    "jsonrpc": "2.0",
                    "method": "notifications/streamStateChanged",
                    "params": {"stream_id": process_id_str, "state": "ended", "reason": "process_exited"}
                }
                try:
                   await self.mcp_server._send_callback(json.dumps(notification))
                except Exception as e:
                   logger.error(f"发送MCP通知失败: {e}", exc_info=True)

        self.is_stopping_manually = False # 重置标志位

    async def start_stream(self) -> str:
        if self.state == StreamState.STREAMING:
            return "无法开启，当前已经有一个通话正在进行中。"
        
        # 增加对 stream_service 是否存在的检查
        if not self.stream_service or not self.script_full_path:
             error_msg = "通话服务未正确初始化，可能是因为未找到启动脚本。"
             logger.error(f"【AVCallManager】: {error_msg}")
             return f"启动通话失败：{error_msg}"


        logger.info("【AVCallManager】: 准备开启新的推流...")
        self.is_stopping_manually = False
        try:
            self.current_process_id = await self.stream_service.start_stream()
            self.state = StreamState.STREAMING
            logger.info(f"【AVCallManager】: 推流已启动，进程ID: {self.current_process_id}")
            return "已开启视频通话，请等待后台人员连接。"
        except FileNotFoundError as e:
            logger.error(f"【AVCallManager】: 启动失败，脚本文件未找到: {e}")
            self.state = StreamState.IDLE
            return f"启动通话失败：所需脚本文件未找到 ({self.script_full_path})。"
        except PermissionError as e:
             logger.error(f"【AVCallManager】: 启动失败，脚本无执行权限: {e}")
             self.state = StreamState.IDLE
             return f"启动通话失败：脚本文件无执行权限 ({self.script_full_path})。"
        except Exception as e:
            logger.error(f"【AVCallManager】: 启动推流时发生未知错误: {e}", exc_info=True)
            self.state = StreamState.IDLE
            self.current_process_id = None
            return f"开启通话失败: {e}"

    async def stop_stream(self) -> str:
        if self.state == StreamState.IDLE or not self.current_process_id:
            return "当前没有正在进行的通话可以关闭。"
        
        # 增加对 stream_service 是否存在的检查
        if not self.stream_service:
             logger.error("【AVCallManager】: 无法停止推流，服务未初始化。")
             return "停止通话失败：服务未初始化。"

        logger.info(f"【AVCallManager】: 收到手动停止推流请求，进程ID: {self.current_process_id}")
        self.is_stopping_manually = True

        await self.stream_service.stop_stream(self.current_process_id)

        return "正在关闭通话..."

    def get_stream_status(self) -> str:
        return f"当前的通话状态是: {self.state.name}。" + (f" (进程ID: {self.current_process_id})" if self.current_process_id else "")

def get_av_call_manager():
    return AVCallManager.get_instance()