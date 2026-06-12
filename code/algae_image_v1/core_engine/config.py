"""Algae species definitions, risk thresholds, and FOV parameters."""
from typing import Dict, Tuple

# ── LifeWatch 95 Class Mapping ──────────────────────────────────────────
LIFEWATCH_95_CLASSES: Dict[int, str] = {
    0: "Anabaena", 1: "Aphanizomenon", 2: "Aphanocapsa", 3: "Aphanothece",
    4: "Asterionella", 5: "Aulacoseira", 6: "Bitrichia", 7: "Botryococcus",
    8: "Ceratium", 9: "Chlamydomonas", 10: "Chlorella", 11: "Chroococcus",
    12: "Closterium", 13: "Coelastrum", 14: "Cosmarium", 15: "Cryptomonas",
    16: "Cyclotella", 17: "Cylindrospermopsis", 18: "Desmodesmus",
    19: "Dictyosphaerium", 20: "Didymocystis", 21: "Dinobryon",
    22: "Dolichospermum", 23: "Elakatothrix", 24: "Eudorina",
    25: "Euglena", 26: "Fragilaria", 27: "Gloeocapsa", 28: "Gloeotrichia",
    29: "Gomphonema", 30: "Gonyostomum", 31: "Gymnodinium",
    32: "Kirchneriella", 33: "Limnothrix", 34: "Mallomonas",
    35: "Melosira", 36: "Merismopedia", 37: "Micrasterias",
    38: "Microcystis", 39: "Monoraphidium", 40: "Mougeotia",
    41: "Navicula", 42: "Nitzschia", 43: "Nodularia", 44: "Nostoc",
    45: "Oocystis", 46: "Oscillatoria", 47: "Pandorina", 48: "Pediastrum",
    49: "Peridinium", 50: "Phacus", 51: "Phormidium", 52: "Pinnularia",
    53: "Planktolyngbya", 54: "Planktothrix", 55: "Pseudanabaena",
    56: "Radiococcus", 57: "Raphidiopsis", 58: "Rhodomonas",
    59: "Scenedesmus", 60: "Selenastrum", 61: "Snowella",
    62: "Sphaerocystis", 63: "Spirogyra", 64: "Spiroides",
    65: "Staurastrum", 66: "Staurodesmus", 67: "Stephanodiscus",
    68: "Synedra", 69: "Synura", 70: "Tabellaria", 71: "Tetraedron",
    72: "Tetrastrum", 73: "Trachelomonas", 74: "Tribonema",
    75: "Uroglena", 76: "Volvox", 77: "Woronichinia", 78: "Zygnema",
    79: "Non-phytoplankton_1", 80: "Non-phytoplankton_2",
    81: "Non-phytoplankton_3", 82: "Non-phytoplankton_4",
    83: "Non-phytoplankton_5", 84: "Other_phytoplankton_1",
    85: "Other_phytoplankton_2", 86: "Other_phytoplankton_3",
    87: "Other_phytoplankton_4", 88: "Other_phytoplankton_5",
    89: "Other_phytoplankton_6", 90: "Other_phytoplankton_7",
    91: "Other_phytoplankton_8", 92: "Other_phytoplankton_9",
    93: "Other_phytoplankton_10", 94: "Other_phytoplankton_11",
}

# ── Risk Level Mapping ──────────────────────────────────────────────────
RISK_LEVELS: Dict[str, str] = {
    "Microcystis": "high", "Woronichinia": "high",
    "Dolichospermum": "high", "Anabaena": "high",
    "Cylindrospermopsis": "high", "Raphidiopsis": "high",
    "Nodularia": "high", "Planktothrix": "high",
    "Aphanizomenon": "high", "Oscillatoria": "high",
    "Gymnodinium": "high",
    "Dinobryon": "medium", "Ceratium": "medium",
    "Peridinium": "medium", "Aulacoseira": "medium",
    "Fragilaria": "medium", "Spiroides": "medium",
}

RISK_COLORS: Dict[str, str] = {
    "high": "#dc2626", "medium": "#f59e0b", "low": "#16a34a",
}

RISK_LABELS_ZH: Dict[str, str] = {
    "high": "高危", "medium": "中危", "low": "低危",
}

# ── Confidence Threshold ────────────────────────────────────────────────
DEFAULT_CONFIDENCE: float = 0.25
DEFAULT_IOU: float = 0.7
DEFAULT_IMAGE_SIZE: Tuple[int, int] = (320, 320)

# ── Quality Thresholds ──────────────────────────────────────────────────
Q_GOOD: float = 0.7
Q_FAIR: float = 0.4

# ── I_enh v2 Parameters ─────────────────────────────────────────────────
IENH_ALPHA: float = 0.6
IENH_BETA: float = 0.25
IENH_GAMMA: float = 0.35


def get_class_name(class_id: int) -> str:
    return LIFEWATCH_95_CLASSES.get(class_id, f"Unknown_{class_id}")


def get_risk_level(class_name: str) -> str:
    return RISK_LEVELS.get(class_name, "low")


def get_risk_label(risk_level: str) -> str:
    return RISK_LABELS_ZH.get(risk_level, risk_level)


def get_risk_color(risk_level: str) -> str:
    return RISK_COLORS.get(risk_level, "#6b7280")
