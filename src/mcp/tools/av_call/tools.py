import asyncio
from src.mcp.mcp_server import McpTool, PropertyList, Property, PropertyType

def _start_call_callback(arguments: dict):
    from .manager import get_av_call_manager
    manager = get_av_call_manager()
    # 确保在事件循环中运行异步函数
    return asyncio.create_task(manager.start_stream())

def _stop_call_callback(arguments: dict):
    from .manager import get_av_call_manager
    manager = get_av_call_manager()
    return asyncio.create_task(manager.stop_stream())

def _get_status_callback(arguments: dict):
    from .manager import get_av_call_manager
    manager = get_av_call_manager()
    return manager.get_stream_status()

def create_tools(add_tool_func, property_list_class, property_class, property_type_enum):
    """创建并注册所有通话相关的工具"""
    
    # --- 工具1: 开始通话 (推流) ---
    add_tool_func(McpTool(
        name="start_call",
        description="开启一个音视频通话直播流，等待后台人员连接。在调用此工具前，应先向用户确认。",
        properties=property_list_class(), # 无参数
        callback=_start_call_callback
    ))

    # --- 工具2: 结束通话 (停止推流) ---
    add_tool_func(McpTool(
        name="hang_up_call",
        description="关闭当前正在进行的音视频通话直播流。",
        properties=property_list_class(), # 无参数
        callback=_stop_call_callback
    ))

    # --- 工具3: 查询通话状态 ---
    add_tool_func(McpTool(
        name="get_call_status",
        description="查询当前的通话状态（是否正在通话中）。",
        properties=property_list_class(), # 无参数
        callback=_get_status_callback
    ))