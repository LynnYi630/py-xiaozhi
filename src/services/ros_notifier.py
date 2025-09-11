from typing import Optional


class RosNotifier:
    """
    负责ROS相关的消息发布封装，避免应用层直接依赖rclpy/std_msgs。
    """

    def __init__(self, ros_publisher: Optional[object] = None, logger: Optional[object] = None):
        self._pub = ros_publisher
        self._log = logger

    def set_publisher(self, ros_publisher: Optional[object]):
        self._pub = ros_publisher

    def publish(self, message: str):
        """
        发布字符串消息到 /xiaozhi/listening_state
        """
        if not self._pub:
            return
        try:
            from std_msgs.msg import String
            msg = String()
            msg.data = message
            # 约定：传入的 ros_publisher 对象上有 .publisher 属性，其为 rclpy 的 Publisher
            self._pub.publisher.publish(msg)
            if self._log:
                self._log.info(f"已发布ROS2消息: {message}")
        except ImportError:
            if self._log:
                self._log.warning("ROS2库未安装，跳过消息发布")
        except Exception as e:
            if self._log:
                self._log.error(f"发布ROS2消息失败: {e}")

    def set_keep_listening(self, value: bool):
        """
        根据 keep_listening 的变更发布对应事件。
        """
        self.publish("wake_word_detected" if value else "conversation_ended")