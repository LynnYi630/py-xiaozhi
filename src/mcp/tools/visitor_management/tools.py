# ------------------------------------------------------------------
# 文件: py-xiaozhi/src/mcp/tools/visitor_management/tools.py
# ------------------------------------------------------------------

from src.mcp.mcp_server import McpTool, PropertyList, Property, PropertyType

def _add_visitor_callback(arguments: dict) -> str:
    """
    McpTool的回调函数.
    它不直接处理业务逻辑，而是调用 VisitorManager 来完成工作。
    """
    from .manager import get_visitor_manager
    manager = get_visitor_manager()
    return manager.add_visitor(**arguments)

def create_tools(add_tool_func, property_list_class, property_class, property_type_enum):
    """
    创建并注册所有访客管理相关的工具
    """
    # 定义“添加访客”工具的参数
    add_visitor_properties = property_list_class([
        property_class("full_name", property_type_enum.STRING),
        property_class("id_number", property_type_enum.STRING),
        property_class("phone_number", property_type_enum.STRING),
        property_class("purpose_of_visit", property_type_enum.STRING),
        property_class("company", property_type_enum.STRING, default_value=""),
        property_class("host_name", property_type_enum.STRING, default_value=""),
        property_class("license_plate", property_type_enum.STRING, default_value="")
    ])

    # 创建并注册工具
    add_tool_func(
        McpTool(
            name="add_visitor_record",
            description="添加一条新的访客记录到系统中。必须提供访客的全名、手机号码和来访事由。证件号码、公司、被访人和车牌号为可选信息。",
            properties=add_visitor_properties,
            callback=_add_visitor_callback
        )
    )

    # 未来可以在这里添加更多工具，例如查询访客、访客签出等