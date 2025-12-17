from enum import Enum, auto

class CallState(Enum):
    """通话状态枚举"""
    IDLE = auto()      # 空闲
    IN_CALL = auto()   # 通话中