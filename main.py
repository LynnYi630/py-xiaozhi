import argparse
import asyncio
import sys
import time

# ROS2 imports
try:
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String
    ROS_AVAILABLE = True
except ImportError:
    print("警告: ROS2库未安装，将跳过ROS功能")
    ROS_AVAILABLE = False

from src.application import Application
from src.utils.logging_config import get_logger, setup_logging

logger = get_logger(__name__)

# ROS2状态跟踪
_ros2_initialized = False
_ros2_shutdown = False


class XiaozhiROS2Node(Node):
    """小智AI客户端ROS2节点"""
    
    def __init__(self):
        super().__init__('xiaozhi_ai_client')
        # 创建发布器，发布到 /xiaozhi/listening_state 话题
        self.publisher = self.create_publisher(String, '/xiaozhi/listening_state', 10)
        self.get_logger().info('小智AI ROS2节点已初始化，话题: /xiaozhi/listening_state')


def init_ros2_node():
    """
    初始化ROS2节点.
    """
    global _ros2_initialized, _ros2_shutdown
    
    if not ROS_AVAILABLE:
        return None
    
    try:
        if not _ros2_initialized:
            rclpy.init()
            _ros2_initialized = True
            _ros2_shutdown = False
            
        node = XiaozhiROS2Node()
        logger.info("ROS2节点初始化成功，话题: /xiaozhi/listening_state")
        return node
    except Exception as e:
        logger.error(f"ROS2节点初始化失败: {e}")
        return None


def cleanup_ros2(ros_node=None):
    """
    安全清理ROS2资源
    """
    global _ros2_initialized, _ros2_shutdown
    
    if not ROS_AVAILABLE or _ros2_shutdown:
        return
    
    try:
        # 先销毁节点
        if ros_node:
            ros_node.destroy_node()
            logger.debug("ROS2节点已销毁")
        
        # 再关闭rclpy，但只关闭一次
        if _ros2_initialized and not _ros2_shutdown:
            rclpy.shutdown()
            _ros2_shutdown = True
            logger.info("ROS2资源已清理")
            
    except Exception as e:
        # 检查是否是重复关闭的错误
        if "rcl_shutdown already called" in str(e):
            logger.debug("ROS2已经关闭，跳过重复清理")
            _ros2_shutdown = True
        else:
            logger.error(f"清理ROS2资源时出错: {e}")


def parse_args():
    """
    解析命令行参数.
    """
    parser = argparse.ArgumentParser(description="小智Ai客户端")
    parser.add_argument(
        "--mode",
        choices=["gui", "cli"],
        default="cli",
        help="运行模式：gui(图形界面) 或 cli(命令行)",
    )
    parser.add_argument(
        "--protocol",
        choices=["mqtt", "websocket"],
        default="websocket",
        help="通信协议：mqtt 或 websocket",
    )
    parser.add_argument(
        "--skip-activation",
        action="store_true",
        help="跳过激活流程，直接启动应用（仅用于调试）",
    )
    return parser.parse_args()


async def handle_activation(mode: str) -> bool:
    """处理设备激活流程.

    Args:
        mode: 运行模式，"gui"或"cli"

    Returns:
        bool: 激活是否成功
    """
    try:
        from src.core.system_initializer import SystemInitializer

        logger.info("开始设备激活流程检查...")

        # 创建SystemInitializer实例
        system_initializer = SystemInitializer()

        # 运行初始化流程
        init_result = await system_initializer.run_initialization()

        # 检查初始化是否成功
        if not init_result.get("success", False):
            logger.error(f"系统初始化失败: {init_result.get('error', '未知错误')}")
            return False

        # 获取激活版本
        activation_version = init_result.get("activation_version", "v1")
        logger.info(f"当前激活版本: {activation_version}")

        # 如果是v1协议，直接返回成功
        if activation_version == "v1":
            logger.info("v1协议：系统初始化完成，无需激活流程")
            return True

        # 如果是v2协议，检查是否需要激活界面
        if not init_result.get("need_activation_ui", False):
            logger.info("v2协议：无需显示激活界面，设备已激活")
            return True

        logger.info("v2协议：需要显示激活界面，准备激活流程")

        # 需要激活界面，根据模式处理
        if mode == "gui":
            # GUI模式需要先创建QApplication
            try:
                # 导入必要的库
                import qasync
                from PyQt5.QtCore import QTimer
                from PyQt5.QtWidgets import QApplication

                # 创建临时QApplication实例
                logger.info("创建临时QApplication实例用于激活流程")
                temp_app = QApplication(sys.argv)

                # 创建事件循环
                loop = qasync.QEventLoop(temp_app)
                asyncio.set_event_loop(loop)

                # 创建Future来等待激活完成（使用新的事件循环）
                activation_future = loop.create_future()

                # 创建激活窗口
                from src.views.activation.activation_window import ActivationWindow

                activation_window = ActivationWindow(system_initializer)

                # 设置激活完成回调
                def on_activation_completed(success: bool):
                    logger.info(f"激活完成，结果: {success}")
                    if not activation_future.done():
                        activation_future.set_result(success)

                # 设置窗口关闭回调
                def on_window_closed():
                    logger.info("激活窗口被关闭")
                    if not activation_future.done():
                        activation_future.set_result(False)

                # 连接信号
                activation_window.activation_completed.connect(on_activation_completed)
                activation_window.window_closed.connect(on_window_closed)

                # 显示激活窗口
                activation_window.show()
                logger.info("激活窗口已显示")

                # 确保窗口显示出来
                QTimer.singleShot(100, lambda: logger.info("激活窗口显示确认"))

                # 等待激活完成
                try:
                    logger.info("开始等待激活完成")
                    activation_success = loop.run_until_complete(activation_future)
                    logger.info(f"激活流程完成，结果: {activation_success}")
                except Exception as e:
                    logger.error(f"激活流程异常: {e}")
                    activation_success = False

                # 关闭窗口
                activation_window.close()

                # 销毁临时QApplication
                logger.info("激活流程完成，销毁临时QApplication实例")
                activation_window = None
                temp_app = None

                # 强制垃圾回收，确保QApplication被销毁
                import gc

                gc.collect()

                # 等待一小段时间确保资源释放（使用同步sleep）
                logger.info("等待资源释放...")
                time.sleep(0.5)

                return activation_success

            except ImportError as e:
                logger.error(f"GUI模式需要qasync和PyQt5库: {e}")
                return False
        else:
            # CLI模式
            from src.views.activation.cli_activation import CLIActivation

            cli_activation = CLIActivation(system_initializer)
            return await cli_activation.run_activation_process()

    except Exception as e:
        logger.error(f"激活流程异常: {e}", exc_info=True)
        return False


async def main():
    """
    主函数.
    """
    setup_logging()
    args = parse_args()

    logger.info("启动小智AI客户端")

    # 处理激活流程
    if not args.skip_activation:
        activation_success = await handle_activation(args.mode)
        if not activation_success:
            logger.error("设备激活失败，程序退出")
            return 1
    else:
        logger.warning("跳过激活流程（调试模式）")

    # 初始化ROS2节点
    ros_node = init_ros2_node()

    # 创建并启动应用程序
    app = Application.get_instance()
    result = await app.run(mode=args.mode, protocol=args.protocol, ros_publisher=ros_node)
    
    # 清理ROS2资源
    cleanup_ros2(ros_node)
    
    return result


if __name__ == "__main__":
    ros_node = None
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
        # 确保ROS2资源被清理
        cleanup_ros2()
        sys.exit(0)
    except Exception as e:
        logger.error(f"程序异常退出: {e}", exc_info=True)
        # 确保ROS2资源被清理
        cleanup_ros2()
        sys.exit(1)
