"""算法配置 — 藻种分类、风险映射、模型选择和管线参数。

职责边界:
  · 此文件 = 算法/业务（类名映射, 风险等级, 模型元数据, I_enh 参数, 阈值）
  · backend/app/config.py = 部署/路径（resource_path, HOST, PORT, 目录结构）

注意: 路径常量不在这里定义；算法参数不放在 backend/app/config.py。
"""
from typing import Dict, Tuple

# ── FMPD 5 Class Mapping ──────────────────────────────────────────
FMPD_5_CLASSES: Dict[int, str] = {
    0: "Other-phytoplankton",
    1: "Non-phytoplankton",
    2: "Woronichinia",
    3: "Spiroides",
    4: "Dinobryon",
}

FMPD_5_CLASSES_ZH: Dict[str, str] = {
    "Other-phytoplankton": "其他浮游植物",
    "Non-phytoplankton": "非浮游植物(杂质)",
    "Woronichinia": "沃氏藻",
    "Spiroides": "螺旋藻",
    "Dinobryon": "锥囊藻",
}

# ── Risk Level Mapping ────────────────────────────────────────────
RISK_LEVELS: Dict[str, str] = {
    "Woronichinia": "high",       # 产毒蓝藻
    "Spiroides": "medium",        # 潜在水华形成种
    "Dinobryon": "medium",        # 异味藻
}

RISK_COLORS: Dict[str, str] = {
    "high": "#dc2626", "medium": "#f59e0b", "low": "#16a34a",
}

RISK_LABELS_ZH: Dict[str, str] = {
    "high": "高危", "medium": "中危", "low": "低危",
}

# ── Model Selection ───────────────────────────────────────────────
AVAILABLE_MODELS: Dict[str, Dict] = {
    "v8l": {
        "name": "YOLOv8l (高精度)",
        "weights": "weights/best_v8l.pt",
        "mAP50": 0.429,
        "note": "80/20 split, honest held-out eval",
    },
    "v8s": {
        "name": "YOLOv8s (轻量快速)",
        "weights": "weights/best_v8s.pt",
        "mAP50": 0.739,
        "note": "train=val eval, inflated estimate",
    },
}
DEFAULT_MODEL: str = "v8l"

# ── Pipeline Toggle ───────────────────────────────────────────────
SKIP_RDN: bool = True   # HSV deterministic → no denoising needed

# ── Detection Thresholds ──────────────────────────────────────────
DEFAULT_CONFIDENCE: float = 0.25
DEFAULT_IOU: float = 0.7
DEFAULT_IMAGE_SIZE: Tuple[int, int] = (640, 640)

# ── Quality Thresholds ────────────────────────────────────────────
Q_GOOD: float = 0.7
Q_FAIR: float = 0.4

# ── I_enh v2 Parameters (tuned for HSV pipeline) ──────────────────
IENH_ALPHA: float = 0.05
IENH_BETA: float = 0.20
IENH_GAMMA: float = 0.30


def get_class_name(class_id: int) -> str:
    return FMPD_5_CLASSES.get(class_id, f"Unknown_{class_id}")


def get_class_name_zh(class_name: str) -> str:
    return FMPD_5_CLASSES_ZH.get(class_name, class_name)


def get_risk_level(class_name: str) -> str:
    return RISK_LEVELS.get(class_name, "low")


def get_risk_label(risk_level: str) -> str:
    return RISK_LABELS_ZH.get(risk_level, risk_level)


def get_risk_color(risk_level: str) -> str:
    return RISK_COLORS.get(risk_level, "#6b7280")
