from enum import Enum, auto

class StreamState(Enum):
    """推流状态的枚举"""
    IDLE = auto()      # 空闲
    STREAMING = auto() # 正在推流