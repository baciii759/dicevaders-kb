"""视觉识别模块入口。

导出 Matcher / OCR / 状态解析，供 Agent 直接 import：
    from vision import Matcher, OCR, parse_screenshot
"""
from .matcher import Matcher, Match
from .ocr import OCR
from .state import BoardState, BoardLayout, parse_screenshot

__all__ = ["Matcher", "Match", "OCR", "BoardState", "BoardLayout", "parse_screenshot"]
