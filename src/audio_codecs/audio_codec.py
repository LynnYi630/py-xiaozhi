import asyncio
import gc
import time
from collections import deque
from typing import Optional

import numpy as np
import opuslib
import sounddevice as sd
import soxr

from src.constants.constants import AudioConfig
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class AudioCodec:
    """
    音频编解码器，负责录音编码和播放解码
    """

    def __init__(self):
        self.opus_decoder = None
        self.unitree_client = None # <--- G1 音频客户端
        self._is_closing = False

        # 播放缓冲区 (作为备用，但我们可能直接流式)
        self._output_buffer = asyncio.Queue(maxsize=500)

        # 实时编码回调 (禁用)
        self._encoded_audio_callback = None

        # G1 模式下不需要以下组件:
        # self.opus_encoder = None
        # self.device_input_sample_rate = None
        # self.device_output_sample_rate = None
        # self.input_resampler = None
        # self._resample_input_buffer = deque()
        # self._device_input_frame_size = None
        # self.input_stream = None
        # self.output_stream = None
        # self._wakeword_buffer = asyncio.Queue(maxsize=100)

    async def initialize(self):
        """
        G1 模式: 初始化音频解码器和宇树客户端
        """
        logger.info("G1 模式: 初始化 AudioCodec (仅播放)...")
        self.unitree_client = unitree_client
        if self.unitree_client is None:
            logger.error("Unitree Audio Client 未提供给 AudioCodec，播放将失败。")

        try:
            # 仅初始化 Opus 解码器 (用于 24kHz 播放数据)
            self.opus_decoder = opuslib.Decoder(
                AudioConfig.OUTPUT_SAMPLE_RATE, AudioConfig.CHANNELS
            )
            logger.info("Opus 解码器初始化成功")
        except Exception as e:
            logger.error(f"初始化 Opus 解码器失败: {e}")
            await self.close()
            raise

    async def write_audio(self, opus_data: bytes):
        """
        G1 模式: 解码Opus音频数据并使用Unitree SDK播放
        """
        if not self.unitree_client:
            logger.warning("Unitree Audio Client 未初始化，无法播放。")
            return

        try:
            # Opus解码为24kHz PCM数据
            pcm_data = self.opus_decoder.decode(
                opus_data, AudioConfig.OUTPUT_FRAME_SIZE
            )

            # 验证数据长度
            expected_length = AudioConfig.OUTPUT_FRAME_SIZE * AudioConfig.CHANNELS * 2 # 2 bytes per int16
            if len(pcm_data) != expected_length:
                logger.warning(f"解码音频长度异常: {len(pcm_data)}, 期望: {expected_length}")
                # 尝试填充或截断 (G1 SDK 可能很挑剔)
                if len(pcm_data) < expected_length:
                    pcm_data += b'\x00' * (expected_length - len(pcm_data))
                else:
                    pcm_data = pcm_data[:expected_length]

            # g1_audio_client.py: PlayStream(self, app_name: str, stream_id: str, pcm_data: bytes)
            # 这是一个阻塞调用，必须在新线程中运行
            await asyncio.to_thread(
                self.unitree_client.PlayStream,
                "py-xiaozhi",  # app_name
                "tts_stream",  # stream_id
                pcm_data        # pcm_data (bytes)
            )

        except opuslib.OpusError as e:
            logger.warning(f"Opus解码失败，丢弃此帧: {e}")
        except Exception as e:
            logger.warning(f"Unitree SDK 音频播放失败: {e}", exc_info=True)

    async def wait_for_audio_complete(self, timeout=10.0):
        """
        G1 模式: SDK播放是流式的，我们无法简单等待队列。
        """
        logger.debug("等待 G1 SDK 音频流...")
        # 增加一个小的延迟，以允许最后的数据包被发送和播放
        await asyncio.sleep(0.2)

    async def clear_audio_queue(self):
        """
        G1 模式: 清空缓冲区并请求 Unitree SDK 停止播放。
        """
        if self.unitree_client:
            logger.info("G1: 请求 Unitree SDK 停止播放...")
            try:
                # g1_audio_client.py: PlayStop(self, app_name: str)
                await asyncio.to_thread(self.unitree_client.PlayStop, "py-xiaozhi")
            except Exception as e:
                logger.error(f"Unitree SDK PlayStop 失败: {e}")
    
        # 清空所有队列 (虽然现在只有 output_buffer)
        queues_to_clear = [
            self._output_buffer,
        ]

        for queue in queues_to_clear:
            while not queue.empty():
                try:
                    queue.get_nowait()
                    cleared_count += 1
                except asyncio.QueueEmpty:
                    break

        # 清空重采样缓冲区
        if self._resample_input_buffer:
            cleared_count += len(self._resample_input_buffer)
            self._resample_input_buffer.clear()

        # 等待正在处理的音频数据完成
        await asyncio.sleep(0.01)

        if cleared_count > 0:
            logger.info(f"清空音频队列，丢弃 {cleared_count} 帧音频数据")

        # 数据量大时执行垃圾回收
        if cleared_count > 100:
            gc.collect()
            logger.debug("执行垃圾回收以释放内存")

    async def close(self):
        """
        关闭音频编解码器，释放所有资源
        """
        if self._is_closing:
            return

        self._is_closing = True
        logger.info("开始关闭音频编解码器...")

        try:
            # 清空队列
            await self.clear_audio_queue()

            # 关闭流
            if self.input_stream:
                try:
                    self.input_stream.stop()
                    self.input_stream.close()
                except Exception as e:
                    logger.warning(f"关闭输入流失败: {e}")
                finally:
                    self.input_stream = None

            if self.output_stream:
                try:
                    self.output_stream.stop()
                    self.output_stream.close()
                except Exception as e:
                    logger.warning(f"关闭输出流失败: {e}")
                finally:
                    self.output_stream = None

            # 清理重采样器
            await self._cleanup_resampler(self.input_resampler, "输入")
            self.input_resampler = None

            # 清理重采样缓冲区
            self._resample_input_buffer.clear()

            # 清理编解码器
            self.opus_encoder = None
            self.opus_decoder = None

            gc.collect()  # 强制释放 nanobind 的 C++ 对象

            logger.info("音频资源已完全释放")
        except Exception as e:
            logger.error(f"关闭音频编解码器过程中发生错误: {e}")

    def __del__(self):
        """
        析构函数，检查资源是否正确释放
        """
        if not self._is_closing:
            # 在析构函数中不能使用asyncio.create_task，改为记录警告
            logger.warning("AudioCodec对象被销毁但未正确关闭，请确保调用close()方法")
