"""音视频通话(AV Call)工具包.

提供开启、关闭音视频推流的功能。
"""

from .manager import AVCallManager, get_av_call_manager

__all__ = [
    "AVCallManager",
    "get_av_call_manager",
]