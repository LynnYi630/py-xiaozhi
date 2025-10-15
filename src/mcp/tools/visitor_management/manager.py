# ------------------------------------------------------------------
# 文件: py-xiaozhi/src/mcp/tools/visitor_management/manager.py
# ------------------------------------------------------------------

from .database import VisitorDatabase
from .models import Visitor
from .tools import create_tools

class VisitorManager:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = VisitorManager()
        return cls._instance

    def __init__(self):
        if VisitorManager._instance is not None:
            raise Exception("This class is a singleton!")
        self.db = VisitorDatabase()

    def init_tools(self, add_tool_func, property_list_class, property_class, property_type_enum):
        """由mcp_server调用，用于初始化并注册本模块的所有工具"""
        create_tools(add_tool_func, property_list_class, property_class, property_type_enum)

    def add_visitor(self, **kwargs) -> str:
        """
        处理添加访客的业务逻辑.
        接收来自tool回调的参数，创建模型，并调用数据库层。
        """
        try:
            # 1. 使用kwargs创建Visitor数据模型实例
            #    kwargs的键应该与Visitor类的字段名匹配
            new_visitor = Visitor(**kwargs)
            
            # 2. 调用数据库层来插入数据
            new_id, error = self.db.add_visitor(new_visitor)
            
            # 3. 根据数据库操作结果，返回格式化的字符串给用户
            if error:
                return f"添加访客记录失败: {error}"
            else:
                return f"访客 {new_visitor.full_name} 的记录已成功添加，访客ID为 {new_id}。"

        except TypeError as e:
            # 捕获因参数不匹配等原因导致的模型创建失败
            return f"参数错误，无法创建访客记录: {e}"
        except Exception as e:
            return f"处理访客记录时发生未知错误: {e}"

def get_visitor_manager():
    return VisitorManager.get_instance()