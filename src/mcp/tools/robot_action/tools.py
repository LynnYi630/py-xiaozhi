# src/mcp/tools/robot_action/tools.py

import asyncio
import json
import random
from typing import Any, Dict
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

async def _run_shell_command(command: str) -> tuple[bool, str]:
    """
    异步执行shell命令并返回结果。
    """
    logger.info(f"[RobotAction] 执行命令: {command}")
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode == 0:
            logger.info(f"[RobotAction] 命令成功: {command}")
            return True, stdout.decode()
        else:
            error_msg = stderr.decode()
            logger.error(f"[RobotAction] 命令失败 (Code: {proc.returncode}): {command}\nStderr: {error_msg}")
            return False, error_msg
            
    except Exception as e:
        logger.error(f"[RobotAction] 执行命令异常: {command}\nError: {e}", exc_info=True)
        return False, str(e)

# --- (修改) _execute_action_flow ---
# 1. 移除 audio_cmd
# 2. 修改日志，表明这是后台任务
# 3. 简化并发，现在只执行一个动作
async def _execute_action_flow(action_cmd: str, reset_cmd: str):
    """
    (后台任务) 执行一个完整的动作流程：动作 -> 复位
    """
    try:
        logger.info(f"[RobotAction BG Task] 后台任务启动: {action_cmd}")
        
        # 1. 执行动作
        action_success, action_msg = await _run_shell_command(action_cmd)

        if not action_success:
            raise Exception(f"动作执行失败: {action_msg}")

        logger.info(f"[RobotAction BG Task] 动作执行完毕，开始执行复位: {reset_cmd}")

        # 2. 执行复位
        success, msg = await _run_shell_command(reset_cmd)
        if not success:
            raise Exception(f"动作复位失败: {msg}")

        logger.info(f"[RobotAction BG Task] 后台任务成功完成: {action_cmd}")

    except Exception as e:
        error_msg = f"执行动作流失败: {str(e)}"
        logger.error(f"[RobotAction BG Task] {error_msg}", exc_info=True)
        # 尝试在异常后执行复位，确保机器人安全
        logger.info("[RobotAction BG Task] 尝试在异常后执行复位...")
        await _run_shell_command(reset_cmd)

# --- (修改) 所有的 perform_XXX 函数 ---
# 它们现在必须返回 str, bool, 或 int (根据 mcp_server.py 定义的 ReturnValue)
# 它们不能再返回 json.dumps(...)
# 它们使用 asyncio.create_task 并且不 await

async def perform_handshake(args: Dict[str, Any]) -> str:
    """
    (非阻塞) 启动握手动作，并立即返回。
    """
    logger.info("[RobotAction] 触发 '握手' (非阻塞)")
    action_cmd = "ros2 run interface_example joint_test_example_continue_num /joint_test_handshake.yaml"
    reset_cmd = "ros2 run interface_example joint_test_example /joint_test_reset.yaml"
    
    # 1. 将耗时任务调度到后台
    asyncio.create_task(_execute_action_flow(action_cmd, reset_cmd))
    
    # 2. 立即返回一个简单的字符串给 LLM
    # LLM 会收到这个消息，解除阻塞，并可以开始说 "你好，很高兴认识你"
    return "握手动作已启动，请回复用户：\"您好，很高兴见到您。\""

async def perform_wave(args: Dict[str, Any]) -> str:
    """
    (非阻塞) 启动招手动作，并立即返回。
    """
    logger.info("[RobotAction] 触发 '招手' (非阻塞)")
    action_cmd = "ros2 run interface_example joint_test_example_continue_num /joint_test_hello.yaml"
    reset_cmd = "ros2 run interface_example joint_test_example /joint_test_reset.yaml"
    
    asyncio.create_task(_execute_action_flow(action_cmd, reset_cmd))
    return "招手动作已启动，请回复用户：\"您好，欢迎您来广东金玛。\""

async def perform_goodbye(args: Dict[str, Any]) -> str:
    """
    (非阻塞) 启动再见动作，并立即返回。
    """
    logger.info("[RobotAction] 触发 '再见' (非阻塞)")
    action_cmd = "ros2 run interface_example joint_test_example_continue_num /joint_test_hello.yaml"
    reset_cmd = "ros2 run interface_example joint_test_example /joint_test_reset.yaml"
    
    asyncio.create_task(_execute_action_flow(action_cmd, reset_cmd))
    return "再见动作已启动。请回复用户：\"期待您的下次光临。\""

async def perform_salute(args: Dict[str, Any]) -> str:
    """
    (非阻塞) 启动敬礼动作，并立即返回。
    """
    logger.info("[RobotAction] 触发 '敬礼' (非阻塞)")
    action_cmd = "ros2 run interface_example joint_test_example /joint_test_salute.yaml"
    reset_cmd = "ros2 run interface_example joint_test_example /joint_test_reset.yaml"
    
    asyncio.create_task(_execute_action_flow(action_cmd, reset_cmd))
    return "敬礼动作已启动，请回复用户：\"您好，欢迎您来广东金玛。\""

async def perform_welcome(args: Dict[str, Any]) -> str:
    """
    (非阻塞) 启动欢迎动作，并立即返回。
    """
    logger.info("[RobotAction] 触发 '欢迎' (非阻塞)")
    action_cmd = "ros2 run interface_example joint_test_example /joint_test_welcome.yaml"
    reset_cmd = "ros2 run interface_example joint_test_example /joint_test_reset.yaml"
    
    asyncio.create_task(_execute_action_flow(action_cmd, reset_cmd))
    return "欢迎动作已启动，请回复用户：\"您好，欢迎您来广东金玛。\""

async def perform_intercept(args: Dict[str, Any]) -> str:
    """
    (非阻塞) 启动拦截动作（随机），并立即返回。
    """
    logger.info("[RobotAction] 触发 '拦截' (非阻塞)")
    action_options = [
        "ros2 run interface_example joint_test_example /joint_test_intercept_left.yaml",
        "ros2 run interface_example joint_test_example /joint_test_intercept_right.yaml"
    ]
    action_cmd = random.choice(action_options)
    logger.info(f"[RobotAction] 随机选择的拦截动作为: {action_cmd}")
    
    reset_cmd = "ros2 run interface_example joint_test_example /joint_test_reset.yaml"
    
    asyncio.create_task(_execute_action_flow(action_cmd, reset_cmd))
    return "拦截动作已启动，请回复用户：\"您好，未经允许禁止入内。\""

# async def _execute_action_flow(action_cmd: str, audio_cmd: str, reset_cmd: str) -> str:
#     """
#     执行一个完整的动作流程：
#     1. (并发) 执行动作
#     2. (并发) 播放音频
#     3. (串行) 执行复位
#     """
#     try:
#         logger.info("[RobotAction] 并发执行动作和播放音频...")
        
#         # 1. & 2. 使用 asyncio.gather 同步执行动作和音频
#         # results 将会是 [(success_action, msg_action), (success_audio, msg_audio)]
#         results = await asyncio.gather(
#             _run_shell_command(action_cmd),
#             _run_shell_command(audio_cmd)
#         )

#         (action_success, action_msg) = results[0]
#         (audio_success, audio_msg) = results[1]

#         # 检查关键动作是否成功
#         if not action_success:
#             # 动作失败，即使音频成功了，也应该抛出异常
#             raise Exception(f"动作执行失败: {action_msg}")

#         # 记录音频播放的警告（如果失败）
#         if not audio_success:
#             logger.warning(f"[RobotAction] 播放音频失败: {audio_msg}")

#         logger.info("[RobotAction] 动作和音频执行完毕，开始执行复位...")

#         # 3. 执行复位 (必须在动作和音频完成后)
#         success, msg = await _run_shell_command(reset_cmd)
#         if not success:
#             raise Exception(f"动作复位失败: {msg}")

#         result = {"success": True, "message": "动作流程执行完毕 (动作与音频并发)"}
#         return json.dumps(result, ensure_ascii=False)

#     except Exception as e:
#         error_msg = f"执行动作流失败: {str(e)}"
#         logger.error(f"[RobotAction] {error_msg}", exc_info=True)
#         # 尝试在异常后执行复位，确保机器人安全
#         logger.info("[RobotAction] 尝试在异常后执行复位...")
#         await _run_shell_command(reset_cmd)
#         return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)

# async def perform_handshake(args: Dict[str, Any]) -> str:
#     """
#     执行握手动作、播放音频并复位。
#     """
#     logger.info("[RobotAction] 开始执行 '握手' 动作流")
#     action_cmd = "ros2 run interface_example joint_test_example_continue_num /joint_test_handshake.yaml"
#     audio_cmd = "aplay /home/ubuntu/py-xiaozhi/audio/audio.wav"
#     reset_cmd = "ros2 run interface_example joint_test_example /joint_test_reset.yaml"
    
#     return await _execute_action_flow(action_cmd, audio_cmd, reset_cmd)

# async def perform_wave(args: Dict[str, Any]) -> str:
#     """
#     执行招手动作、播放音频并复位。
#     """
#     logger.info("[RobotAction] 开始执行 '招手' 动作流")
#     action_cmd = "ros2 run interface_example joint_test_example_continue_num /joint_test_hello.yaml"
#     audio_cmd = "aplay /home/ubuntu/py-xiaozhi/audio/audio.wav"
#     reset_cmd = "ros2 run interface_example joint_test_example /joint_test_reset.yaml"
    
#     return await _execute_action_flow(action_cmd, audio_cmd, reset_cmd)

# async def perform_goodbye(args: Dict[str, Any]) -> str:
#     """
#     执行再见（招手）动作、播放音频并复位。
#     """
#     logger.info("[RobotAction] 开始执行 '再见' 动作流")
#     action_cmd = "ros2 run interface_example joint_test_example_continue_num /joint_test_hello.yaml"
#     audio_cmd = "aplay /home/ubuntu/py-xiaozhi/audio/goodbye.wav"
#     reset_cmd = "ros2 run interface_example joint_test_example /joint_test_reset.yaml"
    
#     return await _execute_action_flow(action_cmd, audio_cmd, reset_cmd)

# async def perform_salute(args: Dict[str, Any]) -> str:
#     """
#     执行敬礼动作、播放音频并复位。
#     """
#     logger.info("[RobotAction] 开始执行 '敬礼' 动作流")
#     action_cmd = "ros2 run interface_example joint_test_example /joint_test_salute.yaml"
#     audio_cmd = "aplay /home/ubuntu/py-xiaozhi/audio/audio.wav"
#     reset_cmd = "ros2 run interface_example joint_test_example /joint_test_reset.yaml"
    
#     return await _execute_action_flow(action_cmd, audio_cmd, reset_cmd)


# async def perform_welcome(args: Dict[str, Any]) -> str:
#     """
#     执行欢迎动作、播放音频并复位。
#     """
#     logger.info("[RobotAction] 开始执行 '欢迎' 动作流")
#     action_cmd = "ros2 run interface_example joint_test_example /joint_test_welcome.yaml"
#     audio_cmd = "aplay /home/ubuntu/py-xiaozhi/audio/audio.wav"
#     reset_cmd = "ros2 run interface_example joint_test_example /joint_test_reset.yaml"
    
#     return await _execute_action_flow(action_cmd, audio_cmd, reset_cmd)

# async def perform_intercept(args: Dict[str, Any]) -> str:
#     """
#     执行拦截动作（随机左右）、播放音频并复位。
#     """
#     logger.info("[RobotAction] 开始执行 '拦截' 动作流")
    
#     # 从 config.json 的 "actions" 列表中随机选择一个拦截动作
#     action_options = [
#         "ros2 run interface_example joint_test_example /joint_test_intercept_left.yaml",
#         "ros2 run interface_example joint_test_example /joint_test_intercept_right.yaml"
#     ]
#     action_cmd = random.choice(action_options)
#     logger.info(f"[RobotAction] 随机选择的拦截动作为: {action_cmd}")
    
#     # 从 config.json 提取音频和复位命令
#     audio_cmd = "aplay /home/ubuntu/py-xiaozhi/audio/intercept.wav"
#     reset_cmd = "ros2 run interface_example joint_test_example /joint_test_reset.yaml"
    
#     return await _execute_action_flow(action_cmd, audio_cmd, reset_cmd)