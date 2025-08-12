import asyncio
import random
from re import sub
import websockets
import threading
import logging
import subprocess
from typing import Optional  # 添加新导入

# 导入唤醒词检测相关模块
from src.audio_processing.wake_word_detect import WakeWordDetector
from src.utils.config_manager import ConfigManager  # 添加配置管理

# 导入你提供的audio_codec模块
# 假设audio_codec.py和它的依赖项在你的PYTHONPATH中
from src.audio_codecs.audio_codec import AudioCodec

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class ActionPublisherNode(Node):
    def __init__(self):
        super().__init__('action_publisher_node')
        self.publisher_ = self.create_publisher(String, '/action_command', 10)

    def send_action_command(self, action):
        msg = String()
        msg.data = action
        self.publisher_.publish(msg)
        self.get_logger().info(f"Published action command: '{action}'")

# --- 配置 ---
SERVER_URI = "ws://192.168.1.111:8765"  # 修改为你的服务器地址
KEYWORDS_ACTIONS = [
    {
        "name": "握手",
        "keywords": ["握手", "握个手"],  # 多个关键词对应同一指令
        "command": ["handshake", "aplay /home/ubuntu/py-xiaozhi/audio/audio.wav"]
    },
    {
        "name": "招手",
        "keywords": ["招手", "招个手", "招个拿手", "挥挥手", "招招手"],
        "command": ["hello", "aplay /home/ubuntu/py-xiaozhi/audio/audio.wav"]
    },
    {
        "name": "再见",
        "keywords": ["再见", "拜拜"],
        "command": ["hello", "aplay /home/ubuntu/py-xiaozhi/audio/goodbye.wav"]
    },
    {
        "name": "敬礼",
        "keywords": ["敬礼", "敬个礼", "敬个里", "敬一个里", "敬一个你", "敬个你", "记个礼", "记个里", "记个你"],
        "command": ["salute", "aplay /home/ubuntu/py-xiaozhi/audio/audio.wav"]
    },
    {
        "name": "欢迎",
        "keywords": ["招待", "请进"],
        "command": ["welcome", "aplay /home/ubuntu/py-xiaozhi/audio/audio.wav"]
    },
    {
        "name": "拦截",
        "keywords": ["禁止通行", "拦截", "请勿通过", "阻拦", "挡住", "制止"],
        "command": ["intercept_left", "intercept_right", "aplay /home/ubuntu/py-xiaozhi/audio/intercept.wav"]
    },
    {
        "name": "结束",
        "keywords": ["结束", "终止监听"]
    },
]

# 新增唤醒词相关配置
WAKE_CONFIG = {
    "USE_WAKE_WORD": True,
    "MODEL_PATH": "models/vosk-model-small-cn-0.22",
    "WAKE_WORDS": ["小金小金", "你好小金", "小京小京", "你好小京","小鸡小鸡","你好小鸡"],  # 自定义唤醒词
    "SIMILARITY_THRESHOLD": 0.65,
    "MAX_EDIT_DISTANCE": 2
}

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("RobotClient")

# 新增状态变量
is_awake = False  # 是否处于唤醒状态
wake_detector: Optional[WakeWordDetector] = None  # 唤醒词检测器实例
audio_stream_task: Optional[asyncio.Task] = None  # 音频流任务

def process_command(text: str):
    """检查文本是否包含关键词并执行相应动作"""
    global is_awake, action_publisher  # 添加全局变量声明
    for action in KEYWORDS_ACTIONS:
        for keyword in action["keywords"]:
            if keyword in text:
                logger.info(f"识别到关键词 '{keyword}'，正在执行指令: {action['name']}")
                try:
                    if action["name"] == "拦截":
                        # 随机抽取0和1号命令
                        random_index = random.randint(0, 1)
                        cmd = action["command"][random_index]
                        print(action_publisher)
                        action_publisher.send_action_command(cmd)
                        thread = threading.Thread(target=subprocess.run, args=(action["command"][2],), kwargs={"shell": True, "check": True})
                        thread.start()
                        action_publisher.send_action_command("reset")
                    elif action["name"] == "结束":
                        # 终止程序
                        logger.info("收到结束指令，终止程序")
                        subprocess.run("aplay /home/ubuntu/py-xiaozhi/audio/shutdown.wav", shell=True, check=True)
                        exit(0)
                    else: 
                        # 通过ros2节点发送指令
                        action_publisher.send_action_command(action["command"][0])
                        thread = threading.Thread(target=subprocess.run, args=(action["command"][1],), kwargs={"shell": True, "check": True})
                        thread.start()
                        action_publisher.send_action_command("reset")
                    # 执行完指令后自动休眠
                    logger.info("指令执行完成，进入休眠状态")
                    is_awake = False
                    
                except subprocess.CalledProcessError as e:
                    logger.error(f"执行指令失败: {e}")
                    # 即使执行失败也进入休眠状态
                    is_awake = False
                except Exception as e:
                    logger.error(f"未知错误: {e}")
                    # 发生错误也进入休眠状态
                    is_awake = False
                # 找到一个关键词就执行并返回，避免一句话触发多个动作
                return

# 新增唤醒词检测回调函数
async def on_wake_word_detected(wake_word: str, text: str):
    """唤醒词检测到后的回调处理"""
    global is_awake, audio_stream_task
    
    if not is_awake:
        logger.info(f"唤醒词 '{wake_word}' 已检测到，开始监听...")
        is_awake = True
        # 播放唤醒成功提示音
        subprocess.run("aplay /home/ubuntu/py-xiaozhi/audio/hello.wav", shell=True, check=True)
        # 如果音频流任务不存在或已完成，创建新任务
        if not audio_stream_task or audio_stream_task.done():
            audio_stream_task = asyncio.create_task(start_audio_stream())

async def start_audio_stream():
    """开始发送音频流到服务器"""
    global is_awake
    
    try:
        while is_awake:
            # 这里可以添加超时逻辑，如一段时间无交互后自动休眠
            await asyncio.sleep(0.1)
            
    except asyncio.CancelledError:
        logger.info("音频流任务已取消")
    finally:
        logger.info("音频流已停止")

async def receive_messages(websocket):
    """异步接收来自服务器的消息"""
    global is_awake
    
    try:
        async for message in websocket:
            logger.info(f"<-- 收到服务端文本: '{message}'")
            process_command(str(message))
            
            # 基于服务器消息的休眠逻辑
            if any(keyword in message for keyword in ["休眠", "停止监听"]):
                logger.info("收到休眠指令，进入等待唤醒状态")
                is_awake = False
                
    except websockets.exceptions.ConnectionClosed:
        logger.info("与服务器的连接已关闭。")

# 修改音频发送回调函数
def send_audio_callback(encoded_data: bytes):
    """此回调函数由AudioCodec的录音线程调用"""
    global is_awake
    
    # 只有在唤醒状态下才发送音频数据
    if is_awake:
        asyncio.run_coroutine_threadsafe(websocket.send(encoded_data), loop)

async def main(args=None):
    """主程序"""
    global wake_detector, is_awake, loop, websocket, action_publisher  # 添加全局变量声明
    rclpy.init(args=args)
    action_publisher = ActionPublisherNode()
    audio_codec = AudioCodec()
    config_manager = ConfigManager.get_instance()
    
    try:
        # 配置唤醒词参数
        config_manager.update_config("WAKE_WORD_OPTIONS", WAKE_CONFIG)
        
        logger.info("正在初始化音频编解码器...")
        await audio_codec.initialize()
        logger.info("音频编解码器初始化成功。")
        
        logger.info("正在初始化唤醒词检测器...")
        wake_detector = WakeWordDetector()
        wake_detector.on_detected(on_wake_word_detected)
        await wake_detector.start(audio_codec)
        logger.info("唤醒词检测器初始化成功，等待唤醒...")

        async with websockets.connect(SERVER_URI, ping_interval=5, ping_timeout=20) as websocket:
            logger.info(f"成功连接到服务器: {SERVER_URI}")
            
            # 获取当前事件循环，用于线程安全地发送数据
            loop = asyncio.get_running_loop()

            # 设置回调，开始实时编码和发送
            audio_codec.set_encoded_audio_callback(send_audio_callback)

            logger.info("开始唤醒词监听...")

            # 启动音频流（但此时is_awake为False，不会发送数据）
            await audio_codec.start_streams()
            
            # 创建一个任务来接收服务器消息
            receiver_task = asyncio.create_task(receive_messages(websocket))

            # 等待接收任务完成（通常是在连接关闭时）
            await receiver_task

    except websockets.exceptions.InvalidURI:
        logger.error(f"服务器地址无效: '{SERVER_URI}'")
    except ConnectionRefusedError:
        logger.error(f"无法连接到服务器 {SERVER_URI}。请确保服务器正在运行。")
    except asyncio.CancelledError:
        logger.info("任务被取消，正在清理资源...")
    except Exception as e:
        logger.error(f"发生未预料的错误: {e}", exc_info=True)
    finally:
        logger.info("正在关闭音频编解码器...")
        if audio_codec:
            await audio_codec.close()
            
        # 停止唤醒词检测器
        if wake_detector:
            try:
                await wake_detector.stop()
            except Exception as e:
                logger.error(f"停止唤醒词检测器失败: {e}")
                
        # 关闭rclpy
        rclpy.shutdown()
        logger.info("程序退出。")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("客户端已手动关闭。")