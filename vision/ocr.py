"""数字/文本 OCR 接口。

默认后端是 pytesseract（需本机安装 Tesseract）。也可注入自定义识别函数——
例如把截图裁剪区域发给本地/远程视觉大模型，由它读出数字，比传统 OCR 对游戏 UI 更稳。

用法：
    from vision.ocr import OCR
    ocr = OCR()                       # 用 pytesseract（若已安装）
    text = ocr.read(image_crop)       # 读文字
    num = ocr.read_int(image_crop)    # 读整数（分数、力量、货币等）

    # 自定义后端（接视觉大模型）：
    ocr = OCR(reader=lambda img: my_vlm_extract(img))
"""
from __future__ import annotations

import re
from typing import Callable

try:
    import pytesseract
    from PIL import Image
    _HAS_TESSERACT = True
except Exception:  # pragma: no cover
    _HAS_TESSERACT = False


class OCR:
    def __init__(self, reader: Callable[..., str] | None = None, lang: str = "eng"):
        """
        reader: 自定义识别函数，接收 PIL.Image，返回字符串。
                缺省时用 pytesseract（若可用）。
        """
        self.reader = reader
        self.lang = lang
        if reader is None and not _HAS_TESSERACT:
            self.reader = self._noop

    @staticmethod
    def _noop(img) -> str:
        raise RuntimeError(
            "未安装 pytesseract，也未提供自定义 reader。"
            "安装 OCR：brew install tesseract && pip install pytesseract，"
            "或传入 reader=lambda img: 视觉模型识别(img)。"
        )

    def read(self, image) -> str:
        if self.reader is not None:
            out = self.reader(image)
        else:
            out = pytesseract.image_to_string(image, lang=self.lang)
        return out.strip()

    def read_int(self, image) -> int | None:
        """读取整数，忽略千分位逗号/空格。失败返回 None。"""
        s = self.read(image)
        s = s.replace(",", "").replace(" ", "").replace("，", "")
        m = re.search(r"-?\d+", s)
        return int(m.group()) if m else None

    def read_float(self, image) -> float | None:
        s = self.read(image).replace(",", "").replace(" ", "")
        m = re.search(r"-?\d+(\.\d+)?", s)
        return float(m.group()) if m else None
