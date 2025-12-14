from src.utils.logging_config import get_logger
from .tools import search_employee

logger = get_logger(__name__)

class EmployeeSearchManager:
    """
    员工信息查询工具管理器
    """
    def __init__(self):
        self._initialized = False

    def init_tools(self, add_tool, PropertyList, Property, PropertyType):
        """
        注册员工查询相关工具
        """
        try:
            logger.info("[EmployeeSearch] 开始注册员工查询工具")

            add_tool((
                "company.search_employee",
                "查询公司员工详细信息（办公地址、电话等）。\n"
                "当用户询问某人办公地点、联系方式或寻找某人时使用。\n"
                "Args:\n"
                "  full_name: 员工全名（必填，支持同音字模糊匹配）\n"
                "  is_fuzzy_confirm: 是否是模糊查询后的精确查询（布尔值）\n"
                "Return:\n"
                "  返回一份回答指引，请根据指引按要求回复用户",
                PropertyList([
                    Property("full_name", PropertyType.STRING),
                    Property("is_fuzzy_confirm", PropertyType.BOOLEAN, default_value=False),
                ]),
                search_employee,
            ))
            self._initialized = True
            logger.info("[EmployeeSearch] 工具注册完成")
        except Exception as e:
            logger.error(f"[EmployeeSearch] 工具注册失败: {e}", exc_info=True)

_manager = None

def get_employee_search_manager():
    global _manager
    if _manager is None:
        _manager = EmployeeSearchManager()
    return _manager