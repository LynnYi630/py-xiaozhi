from src.utils.logging_config import get_logger
from .tools import search_employee, get_employee_detail

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

            # 1. 核心查询工具
            add_tool((
                "company.search_employee",
                "查询公司员工信息。当用户询问某人是谁、在哪个部门、或寻找某人时使用。先返回摘要供用户确认。",
                PropertyList([
                    Property("full_name", PropertyType.STRING, "员工全名（必填）", required=True),
                    Property("department", PropertyType.STRING, "员工所在部门（选填，用于辅助筛选）", required=False),
                ]),
                search_employee,
            ))

            # 2. 获取详情工具 (可选，为了让 LLM 在用户确认后能查到具体地址电话)
            add_tool((
                "company.get_employee_detail",
                "获取员工的详细联系方式和办公地点。当用户确认了要找的人选后使用。",
                PropertyList([
                    Property("name", PropertyType.STRING, "员工姓名", required=True),
                    Property("department", PropertyType.STRING, "部门", required=False),
                ]),
                get_employee_detail,
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