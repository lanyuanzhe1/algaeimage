"""Time-series tracking for algae concentration with sliding window and growth rate.

Implements the proposal's concentration estimation and growth rate formulas:

    Concentration:  C_k = N_k / V_eff * η
    Window average: C_k_bar(t) = 1/m * sum(C_k(t - j) for j=0..m-1)
    Growth rate:    G_k(t) = (C_k_bar(t) - C_k_bar(t - Δt)) / (C_k_bar(t - Δt) + ε)
"""
import numpy as np
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import time


@dataclass
class SpeciesTrack:
    """Tracking data for a single algae species."""
    concentrations: List[float] = field(default_factory=list)
    timestamps: List[float] = field(default_factory=list)
    window_avg: float = 0.0
    growth_rate: float = 0.0
    trend: str = "stable"  # stable / increasing / rapidly_increasing / decreasing


@dataclass
class TrackerReport:
    """Complete tracking report for one time step."""
    device_id: str
    timestamp: float
    per_species: Dict[str, SpeciesTrack]
    total_concentration: float
    total_trend: str
    total_growth_rate: float
    sample_count: int


class AlgaeTracker:
    """Tracks algae concentrations over time with sliding window averaging.

    Maintains separate time series per device and per algae species,
    computes running averages and growth rates for risk assessment.
    """

    def __init__(self, window_size: int = 5, # number of frames in sliding window
                 dt_minutes: float = 10.0,     # time interval for growth rate Δt
                 growth_rate_eps: float = 1e-6):
        self.window_size = window_size
        self.dt_minutes = dt_minutes
        self.growth_rate_eps = growth_rate_eps

        # Per-device storage: {device_id: {species_name: deque of (concentration, timestamp)}}
        self._data: Dict[str, Dict[str, deque]] = defaultdict(
            lambda: defaultdict(lambda: deque(maxlen=window_size))
        )

    def update(self, device_id: str,
               composition: Dict[str, int],
               total_count: int,
               sample_volume_ul: float = 0.001,
               fov_area_mm2: float = 1.0,
               depth_mm: float = 1.0,
               correction_factor: float = 1.0) -> TrackerReport:
        """Update tracker with new detection result.

        Args:
            device_id: Source device identifier
            composition: {species_name: count} dict
            total_count: Total algae count in frame
            sample_volume_ul: Effective sample volume in μL
            fov_area_mm2: Field of view area in mm²
            depth_mm: Depth of field in mm
            correction_factor: η correction factor for sampling/dilution

        Returns:
            TrackerReport with per-species and aggregate metrics
        """
        now = time.time()

        # Calculate effective volume
        V_eff = sample_volume_ul  # Already in μL

        per_species = {}

        for species, count in composition.items():
            # Concentration: C_k = N_k / V_eff * η
            conc = (count / V_eff) * correction_factor if V_eff > 0 else 0.0

            # Store in deque
            self._data[device_id][species].append((conc, now))
            track = self._compute_species_track(self._data[device_id][species])
            per_species[species] = track

        # Total concentration
        total_conc = (total_count / V_eff) * correction_factor if V_eff > 0 else 0.0

        # Store total as a pseudo-species "__total__"
        self._data[device_id]["__total__"].append((total_conc, now))
        total_track = self._compute_species_track(self._data[device_id]["__total__"])

        return TrackerReport(
            device_id=device_id,
            timestamp=now,
            per_species=per_species,
            total_concentration=total_conc,
            total_trend=total_track.trend,
            total_growth_rate=total_track.growth_rate,
            sample_count=len(self._data[device_id].get("__total__", [])),
        )

    def _compute_species_track(self, data_deque: deque) -> SpeciesTrack:
        """Compute windowed average and growth rate for a species.

        Implements:
            C_k_bar(t) = 1/m * sum(C_k(t - j) for j=0..m-1)
            G_k(t) = (C_k_bar(t) - C_k_bar(t - Δt)) / (C_k_bar(t - Δt) + ε)
        """
        if not data_deque:
            return SpeciesTrack()

        concentrations = [c for c, _ in data_deque]
        timestamps = [t for _, t in data_deque]
        m = len(concentrations)

        # Window average
        window_avg = float(np.mean(concentrations))

        # Growth rate: compare current window average to Δt ago
        if m >= 2 and timestamps[-1] - timestamps[0] >= self.dt_minutes * 60:
            # Split into two halves: recent vs earlier
            mid = m // 2
            earlier_avg = float(np.mean(concentrations[:mid]))
            growth_rate = ((window_avg - earlier_avg) /
                           (earlier_avg + self.growth_rate_eps))
        else:
            growth_rate = 0.0

        # Trend classification
        trend = self._classify_trend(growth_rate)

        return SpeciesTrack(
            concentrations=concentrations,
            timestamps=timestamps,
            window_avg=round(window_avg, 4),
            growth_rate=round(growth_rate, 6),
            trend=trend,
        )

    def _classify_trend(self, growth_rate: float) -> str:
        """Classify growth trend from rate."""
        if growth_rate > 0.5:
            return "rapidly_increasing"
        elif growth_rate > 0.1:
            return "increasing"
        elif growth_rate < -0.1:
            return "decreasing"
        return "stable"

    def get_history(self, device_id: str,
                    species: Optional[str] = None) -> Dict[str, List[Tuple[float, float]]]:
        """Get raw concentration history for analysis or plotting.

        Returns: {species_name: [(concentration, timestamp), ...]}
        """
        if device_id not in self._data:
            return {}

        if species:
            if species not in self._data[device_id]:
                return {}
            data = self._data[device_id][species]
            return {species: [(c, t) for c, t in data]}

        result = {}
        for sp, data in self._data[device_id].items():
            if sp == "__total__":
                continue
            result[sp] = [(c, t) for c, t in data]
        return result

    def reset_device(self, device_id: str):
        """Clear tracking data for a device."""
        if device_id in self._data:
            del self._data[device_id]

    def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """Get current tracking status summary for a device."""
        if device_id not in self._data:
            return {"active": False}

        species_info = {}
        for species, data in self._data[device_id].items():
            if species == "__total__":
                continue
            track = self._compute_species_track(data)
            species_info[species] = {
                "window_avg": track.window_avg,
                "growth_rate": track.growth_rate,
                "trend": track.trend,
                "samples": len(data),
            }

        total_data = self._data[device_id].get("__total__", deque())
        total_track = self._compute_species_track(total_data)

        return {
            "active": True,
            "species": species_info,
            "total_trend": total_track.trend,
            "total_growth_rate": total_track.growth_rate,
            "total_window_avg": total_track.window_avg,
            "samples": len(total_data),
        }
