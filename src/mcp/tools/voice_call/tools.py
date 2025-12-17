import json
from typing import Any, Dict
from src.utils.logging_config import get_logger


logger = get_logger(__name__)

async def start_voice_call(args: Dict[str, Any]) -> str:
    """启动语音通话"""
    try:
        logger.info("[VoiceCallTools] 收到启动通话请求")
        from .manager import get_voice_call_manager
        manager = get_voice_call_manager()
        result = await manager.start_call_service()
        return json.dumps({"success": True, "message": result}, ensure_ascii=False)
    except Exception as e:
        logger.error(f"[VoiceCallTools] 启动失败: {e}", exc_info=True)
        return json.dumps({"success": False, "message": str(e)}, ensure_ascii=False)

async def end_voice_call(args: Dict[str, Any]) -> str:
    """结束语音通话"""
    try:
        logger.info("[VoiceCallTools] 收到结束通话请求")
        from .manager import get_voice_call_manager
        manager = get_voice_call_manager()
        result = await manager.stop_call_service()
        return json.dumps({"success": True, "message": result}, ensure_ascii=False)
    except Exception as e:
        logger.error(f"[VoiceCallTools] 结束失败: {e}", exc_info=True)
        return json.dumps({"success": False, "message": str(e)}, ensure_ascii=False)

async def get_voice_call_status(args: Dict[str, Any]) -> str:
    """获取通话状态"""
    try:
        from .manager import get_voice_call_manager
        manager = get_voice_call_manager()
        status = manager.get_status_info()
        return json.dumps(status, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)