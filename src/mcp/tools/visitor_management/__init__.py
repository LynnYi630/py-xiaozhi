"""访客管理工具包.

提供添加、查询、管理访客记录等功能。
"""

from .manager import VisitorManager, get_visitor_manager

__all__ = [
    "VisitorManager",
    "get_visitor_manager",
]