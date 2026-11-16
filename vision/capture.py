"""跨平台截图工具。

用法：
    from vision.capture import capture
    png_path = capture("screenshot.png")   # 全屏截图存为 png，返回路径
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def capture(path: str | Path = "screenshot.png") -> str:
    """全屏截图，返回保存路径。"""
    path = str(path)
    if sys.platform == "darwin":
        # macOS：screencapture 需要去掉已存在的旧文件（否则可能弹窗）
        subprocess.run(["screencapture", "-x", path], check=True)
    elif sys.platform.startswith("win"):
        import ctypes
        from PIL import ImageGrab
        ImageGrab.grab().save(path)
    else:  # linux
        subprocess.run(["import", "-window", "root", path], check=True)
    return path


if __name__ == "__main__":
    print(capture())
