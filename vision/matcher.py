"""基于 numpy FFT 的模板匹配（无需 OpenCV）。

用「零均值归一化互相关（ZNCC）」在截图中定位已知 sprite（单位/神器/专长/Boss技能等）。
透明像素（alpha）作为掩码，只对 sprite 实际内容做相关，忽略透明背景。

性能：图像的 FFT 与平方 FFT 在 match_category 中只计算一次，多个模板/多尺度复用。
坐标：若图像被 max_side 缩小，返回的坐标会按比例还原到原图。

用法：
    from vision.matcher import Matcher
    m = Matcher().load_manifest("assets/manifest.json")
    hits = m.match_category("units", "screenshot.png", threshold=0.7)
    for h in hits: print(h.zh, h.en, h.score, h.x, h.y)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image


@dataclass
class Match:
    key: str
    category: str
    en: str
    zh: str
    score: float
    x: int
    y: int
    w: int
    h: int
    scale: float = 1.0


@dataclass
class Matcher:
    manifest: dict = field(default_factory=dict)
    base_dir: Path = Path(".")
    max_side: int = 1600   # 图像长边超过该值先等比缩小（加速），坐标自动还原

    # ---- 加载 ----
    def load_manifest(self, path: str | Path) -> "Matcher":
        path = Path(path)
        self.manifest = json.load(open(path, encoding="utf-8"))
        self.base_dir = path.parent
        return self

    def _template_path(self, item: dict) -> Path:
        return self.base_dir / item["file"]

    # ---- 图像预处理 ----
    @staticmethod
    def _gray_rgba(img: Image.Image) -> np.ndarray:
        arr = np.asarray(img.convert("RGBA")).astype(np.float64) / 255.0
        alpha = arr[..., 3:4]
        rgb = arr[..., :3] * alpha
        return rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114

    @staticmethod
    def _gray_mask(img: Image.Image) -> tuple[np.ndarray, np.ndarray]:
        arr = np.asarray(img.convert("RGBA")).astype(np.float64) / 255.0
        alpha = arr[..., 3]
        mask = (alpha > 0.15).astype(np.float64)
        rgb = arr[..., :3] * alpha[..., None]
        gray = rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114
        return gray, mask

    @staticmethod
    def _prepare(img: Image.Image, H: int, W: int):
        ig = Matcher._gray_rgba(img)
        return ig, np.fft.rfft2(ig, s=(H, W)), np.fft.rfft2(ig * ig, s=(H, W))

    @staticmethod
    def _zncc(F, F2, ih, iw, H, W, t_gray, mask):
        kh, kw = t_gray.shape
        n = max(float(mask.sum()), 1.0)
        t = (t_gray - (t_gray * mask).sum() / n) * mask
        t_norm = float(np.sqrt(np.sum(t * t))) or 1.0

        Kt = np.fft.rfft2(t, s=(H, W))
        Km = np.fft.rfft2(mask, s=(H, W))
        corr = np.fft.irfft2(F * np.conj(Kt), s=(H, W))[:ih, :iw]
        sum_i = np.fft.irfft2(F * np.conj(Km), s=(H, W))[:ih, :iw]
        sum_i2 = np.fft.irfft2(F2 * np.conj(Km), s=(H, W))[:ih, :iw]

        vh, vw = ih - kh + 1, iw - kw + 1
        var = sum_i2[:vh, :vw] - sum_i[:vh, :vw] ** 2 / n
        var = np.clip(var, 1e-8, None)
        return corr[:vh, :vw] / (np.sqrt(var) * t_norm)

    # ---- 预计算（每张图/类别一次） ----
    def _prep_image(self, img: Image.Image, scale_range, max_kh: int, max_kw: int):
        r = 1.0
        if max(img.size) > self.max_side:
            r = self.max_side / max(img.size)
            img = img.resize((int(img.width * r), int(img.height * r)))
        H = img.height + max_kh - 1
        W = img.width + max_kw - 1
        ig, F, F2 = self._prepare(img, H, W)
        return {"img": img, "ig": ig, "F": F, "F2": F2, "H": H, "W": W, "ratio": r}

    def _match_scales(self, prep, tpl: Image.Image, scale_range, threshold):
        ig = prep["ig"]; F = prep["F"]; F2 = prep["F2"]
        ih, iw = ig.shape; H, W = prep["H"], prep["W"]
        lo, hi, steps = scale_range
        best = None
        for s in np.linspace(lo, hi, steps):
            th = max(2, int(round(tpl.height * s)))
            tw = max(2, int(round(tpl.width * s)))
            if th > ih or tw > iw:
                continue
            ts, ms = self._gray_mask(tpl.resize((tw, th), Image.BICUBIC))
            heat = self._zncc(F, F2, ih, iw, H, W, ts, ms)
            idx = np.unravel_index(np.argmax(heat), heat.shape)
            score = float(heat[idx])
            if best is None or score > best[0]:
                best = (score, int(idx[1]), int(idx[0]), tw, th, float(s))
        if best is None or best[0] < threshold:
            return None
        return best

    # ---- 对外接口 ----
    def match_one(self, image, template, scale_range=(0.7, 1.4, 4), threshold=0.6):
        img = image if isinstance(image, Image.Image) else Image.open(image)
        tpl = template if isinstance(template, Image.Image) else Image.open(template)
        tpl = tpl.convert("RGBA")
        lo, hi, steps = scale_range
        max_kh = int(round(tpl.height * max(lo, hi)))
        max_kw = int(round(tpl.width * max(lo, hi)))
        prep = self._prep_image(img, scale_range, max_kh, max_kw)
        r = self._match_scales(prep, tpl, scale_range, threshold)
        if r is None:
            return None
        score, x, y, w, h, s = r
        inv = 1.0 / prep["ratio"]
        return (score, int(x * inv), int(y * inv), int(w * inv), int(h * inv), s)

    def match_category(self, image, category, threshold=0.7,
                       scale_range=(0.7, 1.4, 4), top_k=20):
        items = [i for i in self.manifest.get("items", []) if i["category"] == category]
        img = image if isinstance(image, Image.Image) else Image.open(image)
        lo, hi, steps = scale_range
        mx = max((Image.open(self._template_path(i)).size for i in items), default=(112, 112))
        max_kh = int(round(mx[1] * max(lo, hi)))
        max_kw = int(round(mx[0] * max(lo, hi)))
        prep = self._prep_image(img, scale_range, max_kh, max_kw)
        inv = 1.0 / prep["ratio"]
        hits: list[Match] = []
        for it in items:
            tpl = Image.open(self._template_path(it)).convert("RGBA")
            r = self._match_scales(prep, tpl, scale_range, threshold)
            if r is None:
                continue
            score, x, y, w, h, s = r
            hits.append(Match(key=it["key"], category=category, en=it["en"], zh=it["zh"],
                              score=score, x=int(x * inv), y=int(y * inv),
                              w=int(w * inv), h=int(h * inv), scale=s))
        hits.sort(key=lambda m: -m.score)
        return hits[:top_k]

    def match_all(self, image, categories=None, threshold=0.7, scale_range=(0.7, 1.4, 4)):
        cats = categories or ["units", "artifacts", "perks", "pilot_abilities"]
        img = image if isinstance(image, Image.Image) else Image.open(image)
        hits: list[Match] = []
        for c in cats:
            hits.extend(self.match_category(img, c, threshold, scale_range))
        hits.sort(key=lambda m: -m.score)
        return hits


if __name__ == "__main__":
    import sys
    m = Matcher().load_manifest("assets/manifest.json")
    if len(sys.argv) < 3:
        print("用法: python matcher.py <截图路径> <类别> [阈值]")
        sys.exit(1)
    th = float(sys.argv[3]) if len(sys.argv) > 3 else 0.7
    for h in m.match_category(sys.argv[1], sys.argv[2], threshold=th):
        print(f"[{h.score:.3f}] {h.zh}({h.en}) @ ({h.x},{h.y}) {h.w}x{h.h} scale={h.scale:.2f}")
