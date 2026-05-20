"""Risk assessment combining biological evidence and environmental factors.

Implements the proposal's fused risk scoring formula:
    R_k = α·f(C_k) + β·f(G_k) + γ·E_k + δ·H_k

where:
    f(C_k) = normalized concentration score for species k
    f(G_k) = normalized growth rate score for species k
    E_k    = environmental suitability for species k
    H_k    = historical risk / recent alert state

Outputs a four-level warning: green, yellow, orange, red
"""
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.config import TEMP_RANGE, SALINITY_RANGE, PH_RANGE, DO_LOW
from ml.tracker import AlgaeTracker, TrackerReport


@dataclass
class RiskResult:
    level: str                    # green / yellow / orange / red
    score: float                  # 0-100 composite score
    factors: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    per_species_scores: Dict[str, float] = field(default_factory=dict)


class RiskAssessor:
    """Multi-factor risk assessment using the fused scoring formula.

    R_k = α·f(C_k) + β·f(G_k) + γ·E_k + δ·H_k

    Default weights (α:β:γ:δ = 40:30:20:10) prioritize biological evidence
    while incorporating environmental suitability and history.
    """

    def __init__(self,
                 # Scoring weights for R_k formula
                 alpha: float = 0.40,   # Concentration weight
                 beta: float = 0.30,    # Growth rate weight
                 gamma: float = 0.20,   # Environmental suitability weight
                 delta: float = 0.10,   # Historical risk weight
                 # Thresholds
                 T1: float = 25.0,      # green -> yellow
                 T2: float = 50.0,      # yellow -> orange
                 T3: float = 75.0):     # orange -> red
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.delta = delta
        self.T1 = T1
        self.T2 = T2
        self.T3 = T3

        # Shared tracker instance for growth rate calculation
        self.tracker = AlgaeTracker()

    def assess(self,
               concentration_per_ul: float,
               risk_level_from_detection: str,
               toxic_detected: bool,
               high_risk_detected: bool,
               environment: Optional[Dict[str, float]] = None,
               composition: Optional[Dict[str, int]] = None,
               device_id: str = "",
               growth_rate: float = 0.0,
               trend: str = "stable") -> RiskResult:
        """Assess overall risk using the fused R_k formula.

        Args:
            concentration_per_ul: Algae concentration
            risk_level_from_detection: Current detection risk level
            toxic_detected: Whether toxic algae species detected
            high_risk_detected: Whether high-risk species detected
            environment: Dict with temperature, salinity, ph, dissolved_oxygen
            composition: {species_name: count} for per-species tracking
            device_id: Device identifier for historical tracking
            growth_rate: Pre-computed growth rate (from tracker)
            trend: Trend classification (stable/increasing/rapidly_increasing/decreasing)

        Returns:
            RiskResult with level, score, factors, suggestions
        """
        score = 0.0
        factors = []
        suggestions = []

        # ── α · f(C_k): Concentration score (0-40) ──
        conc_score = self._score_concentration(concentration_per_ul, toxic_detected,
                                                high_risk_detected)
        score += conc_score
        if conc_score > 10:
            factors.append(f"藻类浓度评分: {conc_score:.1f}/40")

        # ── β · f(G_k): Growth rate score (0-30) ──
        growth_score = self._score_growth_rate(trend, growth_rate)
        score += growth_score
        if growth_score > 5:
            factors.append(f"增长趋势评分: {growth_score:.1f}/30")

        # ── γ · E_k: Environmental suitability score (0-20) ──
        env_score = 0.0
        if environment:
            env_score = self._score_environment(environment, factors, suggestions)
            score += env_score

        # ── δ · H_k: Historical risk score (0-10) ──
        hist_score = self._score_history(device_id, risk_level_from_detection)
        score += hist_score
        if hist_score > 2:
            factors.append(f"历史状态评分: {hist_score:.1f}/10")

        # ── Normalize to 0-100 ──
        score = min(score, 100.0)

        # ── Determine final level ──
        level = self._level_from_score(score)

        # ── Generate suggestions ──
        suggestions = self._generate_suggestions(level, toxic_detected, environment, suggestions)

        return RiskResult(
            level=level,
            score=round(score, 1),
            factors=factors,
            suggestions=suggestions,
            per_species_scores={"total": round(score, 1)},
        )

    def assess_with_tracker(self,
                            device_id: str,
                            total_count: int,
                            composition: Dict[str, int],
                            environment: Optional[Dict[str, float]] = None) -> RiskResult:
        """Full assessment including tracker update for growth rate.

        This method updates the internal tracker and uses the growth rate
        and trend in the R_k formula.
        """
        # Update tracker
        from ml.config import SAMPLE_VOLUME_UL
        track_report = self.tracker.update(
            device_id=device_id,
            composition=composition,
            total_count=total_count,
            sample_volume_ul=SAMPLE_VOLUME_UL,
        )

        # Determine detection-level risk (simplified)
        toxic_detected = False
        high_risk_detected = False

        concentration = track_report.total_concentration
        growth_rate = track_report.total_growth_rate
        trend = track_report.total_trend

        return self.assess(
            concentration_per_ul=concentration,
            risk_level_from_detection=self._detection_risk_from_composition(composition),
            toxic_detected=toxic_detected,
            high_risk_detected=high_risk_detected,
            environment=environment,
            composition=composition,
            device_id=device_id,
            growth_rate=growth_rate,
            trend=trend,
        )

    def get_tracker(self) -> AlgaeTracker:
        return self.tracker

    def _score_concentration(self, conc: float, toxic: bool,
                              high_risk: bool) -> float:
        """Score concentration component (0-40 points)."""
        score = 0.0

        if conc > 500:
            score += 25
        elif conc > 100:
            score += 15
        elif conc > 20:
            score += 8
        elif conc > 5:
            score += 3

        # Toxicity bonus
        if toxic:
            score += 15
        elif high_risk:
            score += 8

        return min(score, 40.0)

    def _score_growth_rate(self, trend: str, rate: float) -> float:
        """Score growth rate component (0-30 points)."""
        if trend == "rapidly_increasing":
            return 30.0
        elif trend == "increasing":
            return 15.0 + min(rate * 10, 10.0)
        elif trend == "decreasing":
            return 0.0
        else:  # stable
            return 5.0 if rate > 0 else 0.0

    def _score_environment(self, env: Dict[str, float],
                           factors: List[str],
                           suggestions: List[str]) -> float:
        """Score environmental suitability (0-20 points)."""
        score = 0.0
        temp = env.get("temperature", 25)
        salinity = env.get("salinity", 30)
        ph = env.get("ph", 8.0)
        do_val = env.get("dissolved_oxygen", 8.0)
        chlorophyll = env.get("chlorophyll", 0.0)
        turbidity = env.get("turbidity", 0.0)

        if TEMP_RANGE[0] <= temp <= TEMP_RANGE[1]:
            score += 6
            factors.append(f"水温处于适宜范围 ({temp}°C)")

        if SALINITY_RANGE[0] <= salinity <= SALINITY_RANGE[1]:
            score += 4
            factors.append(f"盐度处于适宜范围 ({salinity} psu)")

        if do_val < DO_LOW:
            score += 5
            factors.append(f"溶解氧偏低 ({do_val} mg/L)，存在缺氧风险")
            if do_val < 2.0:
                suggestions.append("立即启动增氧设备")
        else:
            score += 2

        if ph < PH_RANGE[0] or ph > PH_RANGE[1]:
            score += 3
            factors.append(f"pH值异常 ({ph})")
        else:
            score += 1

        # Chlorophyll bonus
        if chlorophyll > 10:
            score += 2
            factors.append(f"叶绿素偏高 ({chlorophyll} μg/L)")

        # Turbidity indicator
        if turbidity > 50:
            score += 2
            factors.append(f"浊度偏高 ({turbidity} NTU)")

        return min(score, 20.0)

    def _score_history(self, device_id: str,
                       current_risk: str) -> float:
        """Score historical risk component (0-10 points).

        Checks recent alert state from the tracker for this device.
        """
        try:
            status = self.tracker.get_device_status(device_id)
            if not status.get("active", False):
                return 0.0

            # Recent high trend increases score
            if status.get("total_trend") == "rapidly_increasing":
                return 8.0
            elif status.get("total_trend") == "increasing":
                return 4.0

            # Recent high concentration
            if status.get("total_window_avg", 0) > 100:
                return 5.0

            return 0.0
        except Exception:
            return 0.0

    def _level_from_score(self, score: float) -> str:
        """Map score to risk level using thresholds."""
        if score >= self.T3:
            return "red"
        elif score >= self.T2:
            return "orange"
        elif score >= self.T1:
            return "yellow"
        return "green"

    def _detection_risk_from_composition(self, composition: Dict[str, int]) -> str:
        """Infer risk level from species composition."""
        from ml.config import ALGAE_CLASSES

        high_risk_species = {v["name"] for v in ALGAE_CLASSES.values()
                             if v["risk"] == "high"}

        has_high = any(sp in high_risk_species for sp in composition)
        total = sum(composition.values())

        if has_high and total > 10:
            return "red"
        if has_high:
            return "orange"
        if total > 20:
            return "yellow"
        return "green"

    def _generate_suggestions(self, level: str, toxic: bool,
                               environment: Optional[Dict],
                               existing: List[str]) -> List[str]:
        """Generate action suggestions based on risk level."""
        suggestions = list(existing)

        if level == "red":
            suggestions.append("启动应急处置预案")
            suggestions.append("通知相关管理部门")
            suggestions.append("加密采样监测频率")
            if toxic:
                suggestions.append("建议暂停取水/养殖作业并进一步确认")
        elif level == "orange":
            suggestions.append("加强人工复核与巡检")
            suggestions.append("做好应急处置准备")
            suggestions.append("增加监测频次至每小时一次")
        elif level == "yellow":
            suggestions.append("提高监测频率")
            suggestions.append("关注趋势变化")
        else:
            suggestions.append("保持常规监测")

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for s in suggestions:
            if s not in seen:
                seen.add(s)
                unique.append(s)
        return unique
