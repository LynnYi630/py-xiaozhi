# 小智AI客户端 ROS2集成说明

## 概述

小智AI客户端现已集成ROS2功能，当检测到唤醒词或对话结束时，会向ROS2话题发布消息。

## ROS2话题

- **话题名称**: `/xiaozhi/listening_state`
- **消息类型**: `std_msgs/msg/String`
- **发布的消息**:
  - `wake_word_detected`: 当检测到唤醒词时发布
  - `conversation_ended`: 当对话结束时发布

## 消息触发条件

### 发布 "wake_word_detected"
- 唤醒词检测器检测到唤醒词
- 用户通过GUI手动启动监听模式
- `self.keep_listening` 从 `False` 变为 `True`

### 发布 "conversation_ended"
- 用户说出结束词汇（"拜拜"、"再见"、"Bye"、"bye"）
- 网络错误导致连接断开
- 音频通道关闭
- 用户手动切换到非监听模式
- `self.keep_listening` 从 `True` 变为 `False`

## 安装要求

1. **ROS2环境**: 确保已安装ROS2并正确设置环境变量
2. **Python依赖**: 需要安装 `rclpy` 和 `std_msgs`

```bash
# 对于ROS2 Humble (推荐)
sudo apt install ros-humble-rclpy ros-humble-std-msgs

# 对于ROS2 Foxy
sudo apt install ros-foxy-rclpy ros-foxy-std-msgs

# 对于ROS2 Galactic
sudo apt install ros-galactic-rclpy ros-galactic-std-msgs

# 设置ROS2环境 (Humble)
source /opt/ros/humble/setup.bash

# 或者添加到 ~/.bashrc
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
```

## 使用方法

### 1. 设置ROS2环境
```bash
source /opt/ros/humble/setup.bash  # 或其他ROS2发行版
```

### 2. 启动小智AI客户端
```bash
cd py-xiaozhi
python main.py --mode cli  # 或 --mode gui
```

### 3. 监听ROS2消息（可选）
```bash
# 方法1: 使用提供的测试脚本
python test_ros_listener.py

# 方法2: 使用ROS2命令行工具
ros2 topic echo /xiaozhi/listening_state

# 方法3: 查看话题信息
ros2 topic info /xiaozhi/listening_state

# 方法4: 列出所有话题
ros2 topic list
```

## 测试脚本

提供了 `test_ros_listener.py` 脚本用于测试ROS2消息发布功能：

```bash
python test_ros_listener.py
```

该脚本会监听 `/xiaozhi/listening_state` 话题并打印接收到的消息。

## 故障排除

### 1. ROS2库未安装
如果看到 "警告: ROS2库未安装，将跳过ROS功能" 消息：
- 安装ROS2和相关Python包
- 确保 `rclpy` 和 `std_msgs` 可用

### 2. ROS2节点初始化失败
- 确保ROS2环境变量设置正确
- 检查ROS2安装是否完整
- 确认网络配置正确
- 尝试运行 `ros2 node list` 测试ROS2环境

### 3. 消息未发布
- 检查ROS2节点是否成功初始化
- 确认话题名称正确
- 使用 `ros2 topic list` 查看可用话题
- 使用 `ros2 node list` 查看运行中的节点

### 4. 环境变量问题
确保设置了正确的ROS2环境变量：
```bash
# 检查ROS2环境
echo $ROS_DISTRO
echo $ROS_VERSION

# 应该输出类似：
# humble (或 foxy, galactic等)
# 2
```

## 代码集成详情

### 主要修改

1. **main.py**: 
   - 使用ROS2的 `rclpy` 替代ROS1的 `rospy`
   - 创建ROS2节点类 `XiaozhiROS2Node`
   - 添加ROS2资源清理代码

2. **application.py**: 
   - 修改ROS消息发布方法以使用ROS2节点
   - 更新错误处理和日志信息

3. **test_ros_listener.py**:
   - 完全重写为ROS2版本
   - 使用ROS2节点类结构

### 关键类和方法

```python
class XiaozhiROS2Node(Node):
    """小智AI客户端ROS2节点"""
    
def _publish_ros_message(self, message: str):
    """发布ROS2消息"""
    
def _set_keep_listening(self, value: bool):
    """设置keep_listening状态并发布ROS2消息"""
```

