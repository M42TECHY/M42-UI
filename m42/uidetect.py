"""UI elements in a screenshot, by UI-DETR-1 (racineai, MIT: RF-DETR-M trained on web page screenshots, one class:
any UI element). It finds what the pixel card finder misses (designref.cards): cards with no surface of their own,
step pills, pickers, rows of icons, photo cards (the cooking shot), in under a second on the CPU at its training
size (576; at 1600 it took 5 s and missed the photo cards).

Optional: without the model file or the rfdetr package, elements() returns [] and the pixel finder works alone.
The checkpoint was checked to hold only weights and its training settings (an argparse.Namespace), the one class
allowed besides tensors when it is loaded."""
import argparse
import threading
from pathlib import Path

MODEL = Path(__file__).resolve().parent.parent / "models" / "UI-DETR-1" / "model.pth"
RESOLUTION = 576  # the checkpoint's own training size
THRESHOLD = .2    # 0.35 missed the cooking shot's photo cards; 0.15 added empty boxes
_model, _lock, _failed = None, threading.Lock(), False


def available():
    return MODEL.is_file() and not _failed


def _load():
    global _model, _failed
    with _lock:
        if _model is None and not _failed:
            try:
                import torch
                torch.serialization.add_safe_globals([argparse.Namespace])
                from rfdetr.detr import RFDETRMedium
                _model = RFDETRMedium(pretrain_weights=str(MODEL), resolution=RESOLUTION)
            except Exception:  # no rfdetr / torch, a broken file: the pixel finder alone
                _failed = True
    return _model


def elements(im):
    """[(x0, y0, x1, y1) in pixels of `im` (a PIL RGB image)]: UI elements, the picture's frame and empty strips
    left out. [] when the model can't be used."""
    if not available():
        return []
    model = _load()
    if model is None:
        return []
    import numpy as np
    W, H = im.size
    try:
        det = model.predict(np.asarray(im), threshold=THRESHOLD)
    except Exception:
        return []
    out = []
    for x0, y0, x1, y1 in det.xyxy.tolist():
        w, h = x1 - x0, y1 - y0
        if w * h > .3 * W * H or w < 4 or h < 4:  # the whole screen / the board around it; specks
            continue
        out.append((max(0.0, x0), max(0.0, y0), min(float(W), x1), min(float(H), y1)))
    return out
