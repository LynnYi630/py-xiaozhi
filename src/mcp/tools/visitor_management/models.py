# ------------------------------------------------------------------
# 文件: py-xiaozhi/src/mcp/tools/visitor_management/models.py
# ------------------------------------------------------------------

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

@dataclass
class Visitor:
    """对应于数据库中 visitors 表的数据模型"""
    
    # 核心信息 (通常由用户提供)
    full_name: str
    id_number: str
    phone_number: str
    purpose_of_visit: str
    
    # 可选信息
    id_type: Optional[str] = None
    company: Optional[str] = None
    host_name: Optional[str] = None
    host_department: Optional[str] = None
    license_plate: Optional[str] = None
    badge_number: Optional[str] = None
    notes: Optional[str] = None
    
    # 状态与时间戳 (通常由系统管理)
    id: Optional[int] = None
    entry_time: Optional[datetime] = field(default_factory=datetime.now)
    exit_time: Optional[datetime] = None
    status: str = '在厂内'

    def to_dict(self):
        """将模型实例转换为可用于数据库插入的字典"""
        data = {k: v for k, v in self.__dict__.items() if v is not None and k != 'id'}
        return data