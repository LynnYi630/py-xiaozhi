# 文件: py-xiaozhi/src/mcp/tools/av_call/tools.py

import asyncio
from src.mcp.mcp_server import McpTool, PropertyList, Property, PropertyType

# ！！！注意：确保回调函数是异步的，或者能正确处理异步任务！！！
async def _start_call_callback(arguments: dict):
    from .manager import get_av_call_manager
    manager = get_av_call_manager()
    # 直接 await 调用异步方法
    return await manager.start_stream()

async def _stop_call_callback(arguments: dict):
    from .manager import get_av_call_manager
    manager = get_av_call_manager()
    return await manager.stop_stream()

def _get_status_callback(arguments: dict):
    from .manager import get_av_call_manager
    manager = get_av_call_manager()
    # get_stream_status 是同步方法，直接返回
    return manager.get_stream_status()

def create_tools(add_tool_func, property_list_class, property_class, property_type_enum):
    """创建并注册所有通话相关的工具"""
    
    # --- 工具1: 开始通话 (推流) ---
    add_tool_func(McpTool(
        name="start_call",
        description="开启一个音视频通话直播流，等待后台人员连接。在调用此工具前，应先向用户确认。",
        properties=property_list_class(), # 无参数
        callback=_start_call_callback # 使用异步回调
    ))

    # --- 工具2: 结束通话 (停止推流) ---
    add_tool_func(McpTool(
        name="hang_up_call",
        description="关闭当前正在进行的音视频通话直播流。",
        properties=property_list_class(), # 无参数
        callback=_stop_call_callback # 使用异步回调
    ))

    # --- 工具3: 查询通话状态 ---
    add_tool_func(McpTool(
        name="get_call_status",
        description="查询当前的通话状态（是否正在通话中）。",
        properties=property_list_class(), # 无参数
        callback=_get_status_callback
    ))