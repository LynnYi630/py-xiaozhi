import re
from typing import Dict, List

class KeywordMatcher:
    def __init__(self, cfg: Dict[str, dict]):
        # 1) 反向表：keyword -> 主键（如 "握手"）
        self._kw2key: Dict[str, str] = {}
        for key, item in cfg.items():
            for kw in item.get("keywords", []):
                self._kw2key[kw] = key

        # 2) 生成一次性正则：\b(握手|握个手|招手|再见|拜拜|结束|终止监听)\b
        #    加\b是为了整词匹配，避免“再见到”被误触发
        escaped = [re.escape(k) for k in self._kw2key]
        self._pattern = re.compile(r'\b(' + '|'.join(escaped) + r')\b')

    def first_hit(self, text: str):
        """返回 (主键, 命中的关键词) 或 None"""
        m = self._pattern.search(text)
        if not m:
            return None
        kw = m.group(0)
        return self._kw2key[kw], kw