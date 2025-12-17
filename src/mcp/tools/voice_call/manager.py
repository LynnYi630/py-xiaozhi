import asyncio
import socket
import json
from typing import Any, Dict, Optional

from src.utils.logging_config import get_logger
from src.constants.constants import DeviceState
from .models import CallState
# 导入具体的工具函数实现
from .tools import start_voice_call, end_voice_call, get_voice_call_status

logger = get_logger(__name__)

# 配置端口
LOCAL_PORT = 12345       # 监听外部信号
TARGET_IP = "127.0.0.1"
TARGET_PORT = 12346      # 发送给外部程序

class CallSignalProtocol(asyncio.DatagramProtocol):
    def __init__(self, manager):
        self.manager = manager

    def datagram_received(self, data, addr):
        msg = data.decode().strip()
        if msg == "STOP_CALL":
            logger.info(f"[VoiceCallManager] 收到外部挂断信号来自 {addr}")
            asyncio.create_task(self.manager.handle_external_stop())

class VoiceCallManager:
    """语音通话管理器"""
    
    def __init__(self):
        self._initialized = False
        self.state = CallState.IDLE
        self.app = None # Application 引用
        self._transport = None
        logger.info("[VoiceCallManager] 初始化")

    def set_app_instance(self, app):
        """注入 Application 实例"""
        self.app = app

    def init_tools(self, mcp_server, add_tool, PropertyList, Property, PropertyType):
        """
        [标准模式] 在这里注册工具定义
        """
        try:
            logger.info("[VoiceCallManager] 开始注册工具")

            # 1. 注册开始通话工具
            add_tool(
                (
                    "voice_call.start",
                    "开启语音通话会话。此操作会暂时挂起语音助手对麦克风的占用，并将控制权移交给外部通话程序。\n"
                    "当用户想要打电话或开始远程通讯时使用此工具。",
                    PropertyList(), # 无参数
                    start_voice_call, # 引用 tools.py 中的实现
                )
            )

            # 2. 注册结束通话工具
            add_tool(
                (
                    "voice_call.end",
                    "挂断或结束当前的语音通话会话。\n"
                    "此操作会将麦克风控制权恢复给语音助手。",
                    PropertyList(),
                    end_voice_call,
                )
            )

            # 3. 注册状态查询工具
            add_tool(
                (
                    "voice_call.status",
                    "检查当前是否正处于语音通话状态。",
                    PropertyList(),
                    get_voice_call_status,
                )
            )
            
            # 启动 UDP 监听
            asyncio.create_task(self._start_udp_listener())
            
            self._initialized = True
            logger.info("[VoiceCallManager] 工具注册完成")

        except Exception as e:
            logger.error(f"[VoiceCallManager] 注册失败: {e}", exc_info=True)

    async def _start_udp_listener(self):
        """启动 UDP 监听"""
        loop = asyncio.get_running_loop()
        try:
            self._transport, _ = await loop.create_datagram_endpoint(
                lambda: CallSignalProtocol(self),
                local_addr=('0.0.0.0', LOCAL_PORT)
            )
            logger.info(f"[VoiceCallManager] UDP监听已启动端口 {LOCAL_PORT}")
        except Exception as e:
            logger.error(f"[VoiceCallManager] UDP监听启动失败: {e}")

    def _send_udp_cmd(self, cmd: str):
        """发送 UDP 命令"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(cmd.encode(), (TARGET_IP, TARGET_PORT))
            sock.close()
            return True
        except Exception as e:
            logger.error(f"[VoiceCallManager] 发送指令失败: {e}")
            return False

    async def handle_external_stop(self):
        """处理外部挂断信号"""
        if self.state == CallState.IDLE:
            return
        
        logger.info("[VoiceCallManager] 外部触发挂断，恢复资源...")
        if self.app:
            await self.app.acquire_peripherals()
            await self.app._set_device_state(DeviceState.LISTENING)
            system_instruction = "【系统消息】外部通话已结束，资源已释放。请告知用户通话已完成，并询问还有什么可以帮他。"
            await self.app._send_text_tts(system_instruction)
        
        self.state = CallState.IDLE

    # --- 供 tools.py 调用的业务逻辑 ---

    async def start_call_service(self) -> str:
        if self.state == CallState.IN_CALL:
            return "通话已在进行中"
        
        if not self.app:
            return "系统错误: Application 未连接"

        # 1. 释放资源
        await self.app.release_peripherals()
        
        # 2. 发送信号
        if self._send_udp_cmd("START_CALL"):
            self.state = CallState.IN_CALL
            # 复用ACTING状态，作用是阻止服务端LLM回复并且丢弃音频
            await self.app._set_device_state(DeviceState.ACTING) 
            return "通话请求已发送，麦克风已释放，请等待用户通话完毕。"
        else:
            # 失败回滚
            await self.app.acquire_peripherals()
            return "启动失败: 无法连接通话服务"

    async def stop_call_service(self) -> str:
        if self.state == CallState.IDLE:
            return "当前无通话"

        # 1. 发送挂断信号
        self._send_udp_cmd("STOP_CALL")
        
        # 2. 强制恢复本地资源
        if self.app:
            await self.app.acquire_peripherals()
            await self.app._set_device_state(DeviceState.LISTENING)
            
        self.state = CallState.IDLE
        return "通话已结束，请继续和用户对话。"

    def get_status_info(self) -> Dict[str, Any]:
        return {
            "state": self.state.name,
            "port_listening": LOCAL_PORT
        }

# 单例模式
_manager = None
def get_voice_call_manager():
    global _manager
    if _manager is None:
        _manager = VoiceCallManager()
    return _manager