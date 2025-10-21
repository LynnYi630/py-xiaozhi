# 文件: py-xiaozhi/src/mcp/tools/av_call/service.py

import asyncio
import os
import signal
from typing import Optional, Callable
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

class ExternalStreamService:
    """负责管理外部推流脚本的子进程"""

    def __init__(self, script_path: str, on_exit_callback: Callable):
        self.script_path = script_path
        self.on_exit_callback = on_exit_callback # 进程结束后调用的回调
        self.process: Optional[asyncio.subprocess.Process] = None
        self.monitor_task: Optional[asyncio.Task] = None

    async def start_stream(self) -> str:
        """启动推流脚本子进程"""
        if self.process and self.process.returncode is None:
            raise Exception("推流脚本已经在运行中。")

        # 确保脚本存在且可执行
        if not os.path.exists(self.script_path):
            raise FileNotFoundError(f"推流脚本未找到: {self.script_path}")
        if not os.access(self.script_path, os.X_OK):
             # 尝试添加执行权限
            try:
                os.chmod(self.script_path, 0o755)
                logger.info(f"已为脚本添加执行权限: {self.script_path}")
            except OSError as e:
                raise PermissionError(f"无法为脚本添加执行权限: {self.script_path}, 错误: {e}")

        logger.info(f"准备启动推流脚本: {self.script_path}")
        try:
            # 使用 asyncio.create_subprocess_shell 异步启动脚本
            self.process = await asyncio.create_subprocess_shell(
                self.script_path,
                stdout=asyncio.subprocess.PIPE, # 捕获标准输出
                stderr=asyncio.subprocess.PIPE, # 捕获标准错误
                preexec_fn=os.setsid # (Linux/macOS only) 创建新的进程组，方便后续终止整个组
            )
            logger.info(f"推流脚本已启动，进程 PID: {self.process.pid}")

            # 启动一个后台任务来监控进程结束和捕获输出
            self.monitor_task = asyncio.create_task(self._monitor_process())

            return str(self.process.pid) # 返回进程ID作为流ID

        except Exception as e:
            logger.error(f"启动推流脚本失败: {e}", exc_info=True)
            self.process = None
            raise Exception(f"启动推流脚本失败: {e}")

    async def _monitor_process(self):
        """监控子进程状态并处理其输出"""
        if not self.process:
            return

        pid = self.process.pid
        logger.info(f"开始监控推流进程 {pid}...")

        # 异步读取 stdout 和 stderr
        async def log_output(stream, prefix):
            while True:
                line_bytes = await stream.readline()
                if not line_bytes:
                    break
                line = line_bytes.decode(errors='ignore').strip()
                if line:
                    logger.info(f"[{prefix} {pid}]: {line}")

        try:
            await asyncio.gather(
                log_output(self.process.stdout, "stdout"),
                log_output(self.process.stderr, "stderr")
            )
            # 等待进程结束
            return_code = await self.process.wait()
            logger.info(f"推流进程 {pid} 已退出，返回码: {return_code}")

        except asyncio.CancelledError:
            logger.info(f"推流进程 {pid} 的监控任务被取消。")
        except Exception as e:
            logger.error(f"监控推流进程 {pid} 时出错: {e}", exc_info=True)
        finally:
            logger.info(f"结束监控推流进程 {pid}。")
            # 无论如何，都调用退出回调
            await self.on_exit_callback(str(pid))

    async def stop_stream(self, process_id_str: str):
        """终止指定PID的推流脚本进程"""
        if not self.process or str(self.process.pid) != process_id_str or self.process.returncode is not None:
            logger.warning(f"无法停止进程 {process_id_str}：进程不存在、PID不匹配或已结束。")
            return

        pid_to_stop = self.process.pid
        logger.info(f"准备停止推流进程 {pid_to_stop}...")

        # 尝试优雅地终止进程组 (SIGTERM)
        try:
            os.killpg(os.getpgid(pid_to_stop), signal.SIGTERM)
            logger.info(f"已发送 SIGTERM 到进程组 {os.getpgid(pid_to_stop)}")
        except ProcessLookupError:
            logger.warning(f"发送 SIGTERM 失败：进程组 {os.getpgid(pid_to_stop)} 可能已不存在。")
        except AttributeError: # preexec_fn=os.setsid 在 Windows 上不可用
             logger.info(f"正在终止进程 {pid_to_stop} (Windows)...")
             self.process.terminate()

        # 如果监控任务仍在运行，取消它
        if self.monitor_task and not self.monitor_task.done():
            self.monitor_task.cancel()
            try:
                await self.monitor_task # 等待任务真正取消完成
            except asyncio.CancelledError:
                pass # 预期中的异常

        # # (可选) 增加强制终止逻辑
        # try:
        #     await asyncio.wait_for(self.process.wait(), timeout=5.0)
        #     logger.info(f"进程 {pid_to_stop} 已优雅退出。")
        # except asyncio.TimeoutError:
        #     logger.warning(f"进程 {pid_to_stop} 未在5秒内退出，尝试强制终止 (SIGKILL)...")
        #     try:
        #         os.killpg(os.getpgid(pid_to_stop), signal.SIGKILL)
        #     except Exception as kill_err:
        #         logger.error(f"强制终止进程组 {os.getpgid(pid_to_stop)} 失败: {kill_err}")
        #     self.process.kill() # Windows 备用

        # # 确保进程引用被清理 (状态更新将在回调中处理)
        # self.process = None
        # self.monitor_task = None