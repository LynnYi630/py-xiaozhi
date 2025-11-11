# src/mcp/tools/robot_action/manager.py

from typing import Any, Dict
from src.utils.logging_config import get_logger

# 导入工具函数
from .tools import (
    perform_handshake,
    perform_wave,
    perform_goodbye,
    perform_salute,
    perform_welcome,
    perform_intercept
)

logger = get_logger(__name__)


class RobotActionToolsManager:
    """
    机器人动作工具管理器。
    负责将 config.json 中的动作注册为MCP工具。
    """

    def __init__(self):
        self._initialized = False
        logger.info("[RobotActionManager] 机器人动作工具管理器初始化")

    def init_tools(self, add_tool, PropertyList, Property, PropertyType):
        """
        初始化并注册所有机器人动作工具。
        """
        try:
            logger.info("[RobotActionManager] 开始注册机器人动作工具")
            
            # 1. 注册 握手 工具
            # 注意：PropertyList() 表示此工具无需额外参数
            add_tool((
                "robot.handshake",
                "机器人执行握手动作并播放提示音。当用户表达握手意图时（例如：'来握个手'）使用。",
                PropertyList(), 
                perform_handshake,
            ))

            # 2. 注册 招手 工具
            add_tool((
                "robot.wave",
                "机器人执行招手动作并播放提示音。当用户表达招手或打招呼意图时（例如：'招个手'）使用。",
                PropertyList(),
                perform_wave,
            ))

            # 3. 注册 再见 工具
            add_tool((
                "robot.goodbye",
                "与机器人执行招手动作并播放再见提示音。当用户表达再见或离开意图时（例如：'拜拜'）使用。",
                PropertyList(),
                perform_goodbye,
            ))

            # 4. 注册 敬礼 工具
            add_tool((
                "robot.salute",
                "执行机器人敬礼动作并播放提示音。当用户表达敬意或要求敬礼时（例如：'敬个礼'）使用。",
                PropertyList(),
                perform_salute,
            ))

            # 5. 注册 欢迎 工具
            add_tool((
                "robot.welcome",
                "执行机器人欢迎动作（如招待、请进）并播放提示音。当用户表达欢迎或邀请进入意图时（例如：'请进'）使用。",
                PropertyList(),
                perform_welcome,
            ))

            # 6. 注册 拦截 工具
            add_tool((
                "robot.intercept",
                "执行机器人拦截动作（随机左或右）并播放提示音。当用户要求禁止通行或进行阻拦时（例如：'禁止通行'）使用。",
                PropertyList(),
                perform_intercept,
            ))

            self._initialized = True
            logger.info("[RobotActionManager] 机器人动作工具注册完成")

        except Exception as e:
            logger.error(f"[RobotActionManager] 机器人动作工具注册失败: {e}", exc_info=True)
            raise

# --- 单例模式 (Global Manager Instance) ---

_robot_action_manager = None

def get_robot_action_manager() -> RobotActionToolsManager:
    """
    获取机器人动作工具管理器单例。
    """
    global _robot_action_manager
    if _robot_action_manager is None:
        _robot_action_manager = RobotActionToolsManager()
        logger.debug("[RobotActionManager] 创建机器人动作工具管理器实例")
    return _robot_action_manager