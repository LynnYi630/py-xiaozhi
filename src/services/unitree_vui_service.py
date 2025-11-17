# src/services/unitree_vui_service.py
import threading
import asyncio
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# 延迟导入，以便 main.py 中的 ChannelFactoryInitialize 首先运行
try:
    from unitree_sdk2py.core.channel import ChannelSubscriber
    from unitree_sdk2py.idl.unitree_go.msg.dds_ import AudioData_
    from unitree_sdk2py.idl.std_msgs.msg.dds_ import String_
    SDK_AVAILABLE = True
except ImportError:
    logger.critical("Unitree SDK 库未找到。DDS 订阅服务无法启动。")
    SDK_AVAILABLE = False
except Exception as e:
    logger.critical(f"加载 Unitree SDK 时出错 (可能 ChannelFactory 未初始化?): {e}")
    SDK_AVAILABLE = False


class UnitreeVuiService:
    def __init__(self, app_instance):
        self.app = app_instance
        # 获取在 application.py 中创建的主事件循环
        self.main_loop = app_instance._main_loop 
        self._running = False
        self._thread = None
        
        if not SDK_AVAILABLE:
            logger.error("UnitreeVuiService 无法运行，因为 SDK 不可用。")

    def start(self):
        if not SDK_AVAILABLE or self._running:
            return
            
        self._running = True
        # DDS 订阅器的 Recv() 是阻塞的，必须在新线程中运行
        self._thread = threading.Thread(target=self._run_subscriber_loop, daemon=True)
        self._thread.start()
        logger.info("Unitree VUI Service (DDS Subscriber) 线程已启动")

    def stop(self):
        self._running = False
        if self._thread:
            logger.info("正在停止 Unitree VUI Service 线程...")
            self._thread.join(timeout=1.0)
            
    def _run_subscriber_loop(self):
        try:
            # 1. 订阅唤醒 (rt/wakeup_msg), 类型: std_msgs::msg::dds_::String_
            wakeup_sub = ChannelSubscriber("rt/wakeup_msg", String_)
            
            # 2. 订阅ASR文本 (rt/audio_msg), 类型: unitree_go::msg::dds_::AudioData_
            # (根据文档, AudioData_ 包含一个 'text' 字段)
            asr_sub = ChannelSubscriber("rt/audio_msg", AudioData_)

            logger.info("DDS 订阅器已初始化，正在监听 'rt/wakeup_msg' 和 'rt/audio_msg'")

            # 我们需要两个子线程，因为两个 Recv() 都会阻塞
            t_wakeup = threading.Thread(target=self._wakeup_loop, args=(wakeup_sub,), daemon=True)
            t_asr = threading.Thread(target=self._asr_loop, args=(asr_sub,), daemon=True)
            
            t_wakeup.start()
            t_asr.start()

            while self._running:
                # 主订阅线程仅用于监控子线程
                t_wakeup.join(0.5)
                t_asr.join(0.5)
                if not t_wakeup.is_alive():
                    logger.error("DDS 唤醒订阅子线程意外终止!")
                    break
                if not t_asr.is_alive():
                    logger.error("DDS ASR 订阅子线程意外终止!")
                    break
                    
        except Exception as e:
            logger.critical(f"Unitree VUI Service 发生致命错误: {e}", exc_info=True)
            if self.main_loop and not self.main_loop.is_closed():
                # 线程安全地通知主应用
                self.main_loop.call_soon_threadsafe(
                    asyncio.create_task,
                    self.app._on_network_error("Unitree VUI Service 失败")
                )
        
        logger.info("Unitree VUI 订阅循环已停止。")

    def _wakeup_loop(self, sub: ChannelSubscriber):
        """在专用线程中监听唤醒词"""
        while self._running:
            try:
                # Recv() 是一个阻塞操作, 设置1秒超时
                msg_data = sub.Recv(timeout=1.0) 
                if msg_data:
                    # msg_data 是 String_ 类型的实例
                    wake_word_text = msg_data.data
                    logger.info(f"DDS 收到唤醒: {wake_word_text}")
                    
                    # 线程安全地调用主 asyncio 循环的异步方法
                    if self.main_loop and not self.main_loop.is_closed():
                        # call_soon_threadsafe 用于调度一个 *同步* 函数
                        # 我们用它来调度 asyncio.create_task 这个 *同步* 函数
                        # asyncio.create_task 再去调度我们的 *异步* 协程
                        self.main_loop.call_soon_threadsafe(
                            asyncio.create_task,
                            self.app._on_unitree_wake_word_detected(wake_word_text)
                        )
            except Exception as e:
                # Time out 是正常的
                if "Time out" not in str(e):
                    logger.error(f"DDS 唤醒订阅循环出错: {e}")
                    break # 退出循环

    def _asr_loop(self, sub: ChannelSubscriber):
        """在专用线程中监听ASR结果"""
        while self._running:
            try:
                # Recv() 是一个阻塞操作, 设置1秒超时
                msg_data = sub.Recv(timeout=1.0)
                if msg_data:
                    # msg_data 是 AudioData_ 类型的实例
                    asr_text = msg_data.text
                    if asr_text:
                        logger.info(f"DDS 收到 ASR: {asr_text}")
                        # 线程安全地调用主 asyncio 循环
                        if self.main_loop and not self.main_loop.is_closed():
                            self.main_loop.call_soon_threadsafe(
                                asyncio.create_task,
                                self.app._on_unitree_asr_received(asr_text)
                            )
            except Exception as e:
                if "Time out" not in str(e):
                    logger.error(f"DDS ASR 订阅循环出错: {e}")
                    break # 退出循环