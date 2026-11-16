"""把「模板匹配 + OCR + 知识库」整合成结构化棋盘状态（供 Agent 决策）。

核心流程：
    screenshot --matcher--> 检测到的单位/神器/专长/Boss技能（含坐标）
                 --layout---> 按 x 坐标归入 6 列
                 --kb-------> 关联 dicevaders_data.json 补全数值/效果
                 --ocr------> 读数字（目标分数、资源、单位力量等，可选）
                 --> BoardState(JSON)

用法：
    from vision import parse_screenshot
    st = parse_screenshot("screenshot.png", kb="dicevaders_data.json")
    print(st.to_dict())
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from .matcher import Matcher


@dataclass
class DetectedEntity:
    key: str
    category: str          # units / artifacts / perks / pilot_abilities / ...
    en: str
    zh: str
    x: int
    y: int
    w: int
    h: int
    score: float
    column: int | None = None   # 1..6，按 x 坐标归列
    row: int | None = None      # 按 y 坐标（自下而上）


@dataclass
class BoardLayout:
    """把截图坐标映射到 6 列。默认按宽度均分（可传入 left/right 边距与列边界覆盖）。"""
    left: int = 0
    right: int | None = None
    columns: list[tuple[int, int]] | None = None   # 手动指定 6 个 [x0,x1) 区间

    def assign(self, x: int, width: int) -> int:
        if self.columns:
            for i, (x0, x1) in enumerate(self.columns, 1):
                if x0 <= x < x1:
                    return i
            return 6
        r = self.right if self.right is not None else width
        span = r - self.left
        col = int((x - self.left) / span * 6) + 1
        return max(1, min(6, col))


@dataclass
class BoardState:
    image: str = ""
    units: list[DetectedEntity] = field(default_factory=list)
    artifacts: list[DetectedEntity] = field(default_factory=list)
    perks: list[DetectedEntity] = field(default_factory=list)
    pilot_abilities: list[DetectedEntity] = field(default_factory=list)
    commanders: list[DetectedEntity] = field(default_factory=list)
    pilots: list[DetectedEntity] = field(default_factory=list)
    # OCR/数值（由外部读取或视觉模型填充）
    resources: dict[str, Any] = field(default_factory=dict)   # budge/chrono/money/mult/...
    target: dict[str, Any] = field(default_factory=dict)      # defense / turns_left / hearts
    dice: list[dict[str, Any]] = field(default_factory=list)  # [{value, column, frozen}]
    raw: list[DetectedEntity] = field(default_factory=list)   # 所有命中（未分类）

    def to_dict(self) -> dict:
        return asdict(self)


def parse_screenshot(
    image,
    kb: str | Path = "dicevaders_data.json",
    manifest: str | Path = "vision/assets/manifest.json",
    layout: BoardLayout | None = None,
    threshold: float = 0.7,
    scale_range: tuple[float, float, int] = (0.5, 2.0, 7),
    categories: list[str] | None = None,
) -> BoardState:
    """主入口：对截图做多类别模板匹配并归类到 6 列。

    image: PIL.Image 或截图路径。
    返回 BoardState；数值类字段（resources/target/dice）留空，由 OCR 或视觉模型补全。
    """
    from PIL import Image
    img = image if isinstance(image, Image.Image) else Image.open(image)
    m = Matcher().load_manifest(manifest)
    cats = categories or ["units", "artifacts", "perks", "pilot_abilities", "commanders", "pilots"]
    hits = m.match_all(img, categories=cats, threshold=threshold, scale_range=scale_range)
    layout = layout or BoardLayout()
    st = BoardState(image=str(image))
    bucket = {
        "units": st.units, "artifacts": st.artifacts, "perks": st.perks,
        "pilot_abilities": st.pilot_abilities, "commanders": st.commanders, "pilots": st.pilots,
    }
    for h in hits:
        e = DetectedEntity(key=h.key, category=h.category, en=h.en, zh=h.zh,
                           x=h.x, y=h.y, w=h.w, h=h.h, score=h.score,
                           column=layout.assign(h.x + h.w // 2, img.width))
        st.raw.append(e)
        bucket.get(h.category, []).append(e)
    return st


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python state.py <截图路径> [阈值]")
        sys.exit(1)
    th = float(sys.argv[2]) if len(sys.argv) > 2 else 0.7
    st = parse_screenshot(sys.argv[1], threshold=th)
    print(json.dumps(st.to_dict(), ensure_ascii=False, indent=2))
