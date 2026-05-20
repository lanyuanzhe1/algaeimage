"""Detection orchestration service - full pipeline integration.

Implements the complete technical pipeline described in the proposal:
    raw DoFP image → demosaic → Stokes reconstruction → polarization reconstruction
    → polarization enhancement → quality assessment → YOLO detection
    → counting & concentration → time-series tracking → multi-factor risk assessment
"""
import sys
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import numpy as np
import cv2

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.inference import AlgaeDetector
from ml.preprocessing import AlgaePreprocessor
from ml.postprocessing import BatchResult, format_results
from ml.reconstructor import PolarizationReconstructor
from ml.tracker import AlgaeTracker
from ml.config import SAMPLE_VOLUME_UL, FOV_AREA_MM2, DEPTH_MM
from image_processing.polarization import PolarizationProcessor
from image_processing.enhancement import ImageEnhancer
from image_processing.quality import QualityAssessor, QualityReport
from ..models import DetectionRecord, RiskLevel
from ..config import UPLOAD_DIR, RESULTS_DIR
from .risk_assessment import RiskAssessor, RiskResult


class DetectionService:
    """Orchestrates the complete detection pipeline."""

    def __init__(self):
        self.polarization = PolarizationProcessor()
        self.reconstructor = PolarizationReconstructor()
        self.enhancer = ImageEnhancer()
        self.quality = QualityAssessor()
        self.preprocessor = AlgaePreprocessor()
        self.detector = AlgaeDetector()
        self.risk_assessor = RiskAssessor()
        self._initialized = False

    def initialize(self):
        """Load models on first use."""
        if not self._initialized:
            self.detector.load_model()
            self.reconstructor.load_model()
            self._initialized = True

    def process_image(self, image_bytes: bytes, device_id: str = "default",
                      environment: Optional[Dict[str, float]] = None,
                      is_raw_polarization: bool = False) -> BatchResult:
        """Full pipeline: decode → polarize → enhance → detect → track → assess.

        Args:
            image_bytes: Raw image bytes (JPEG/PNG)
            device_id: Source device identifier
            environment: Optional dict with temp, salinity, pH, DO, chlorophyll, turbidity
            is_raw_polarization: If True, treat input as raw DoFP polarization frame

        Returns:
            BatchResult with detections, risk assessment, and tracking data
        """
        self.initialize()
        start_time = time.time()

        # ── Step 1: Decode image ──
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Failed to decode image")
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        pipeline_stages = {"input_shape": str(image.shape)}

        # ── Step 2: Polarization processing ──
        if is_raw_polarization and len(image.shape) == 2:
            # Raw DoFP: 2D grayscale with polarization pattern
            channels = self.polarization.demosaic_DoFP(image)
            stokes = self.polarization.reconstruct_stokes(**channels)
            I0, I45, I90 = channels["I0"], channels["I45"], channels["I90"]
            I135 = channels["I135"]
            use_deep = self.reconstructor.load_model()
            aligned_image = self.reconstructor.reconstruct(
                I0, I45, I90, I135,
                use_deep=use_deep
            )
            pipeline_stages["polarization"] = "raw_DoFP_reconstructed"
        else:
            # Standard RGB input: no real polarization data available.
            # Skip pseudo-polarization — feed original RGB straight to the enhancer.
            aligned_image = image
            pipeline_stages["polarization"] = "standard_rgb_bypass"

        # ── Step 3: Image enhancement ──
        enhanced = self.enhancer.enhance(aligned_image, dehaze=False,
                                         color_correct=True, clahe=True)

        # ── Step 4: Quality assessment (Q formula) ──
        quality_report = self.quality.assess(enhanced)
        pipeline_stages["quality_score"] = quality_report.quality_score
        pipeline_stages["quality"] = quality_report.overall_quality

        if not self.quality.is_usable(quality_report):
            pipeline_stages["quality_skip"] = True
            processing_time = (time.time() - start_time) * 1000
            result = format_results([], image_id=f"{device_id}_lowq",
                                    processing_time_ms=processing_time)
            result.risk_level = "yellow"  # Flag for human review
            cv2.imwrite(str(RESULTS_DIR / f"{result.image_id}_original.jpg"),
                        cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
            cv2.imwrite(str(RESULTS_DIR / f"{result.image_id}_processed.jpg"),
                        cv2.cvtColor(enhanced, cv2.COLOR_RGB2BGR))
            return result

        # ── Step 5: YOLO detection ──
        processed, meta = self.preprocessor.preprocess(enhanced)
        infer_image = (processed * 255).astype(np.uint8)
        detections = self.detector.detect(infer_image)
        pipeline_stages["detections"] = len(detections)

        # ── Step 6: Post-processing & counting ──
        elapsed = (time.time() - start_time) * 1000
        image_id = f"{device_id}_{uuid.uuid4().hex[:8]}"
        result = format_results(detections, sample_volume_ul=SAMPLE_VOLUME_UL,
                                image_id=image_id, processing_time_ms=elapsed)

        # ── Step 7: Multi-factor risk assessment ──
        risk_result = self.risk_assessor.assess(
            concentration_per_ul=result.concentration_cells_per_ul or 0,
            risk_level_from_detection=result.risk_level,
            toxic_detected=any(d.toxicity for d in detections),
            high_risk_detected=any(d.risk == "high" for d in detections),
            environment=environment,
            composition=result.algae_composition,
            device_id=device_id,
        )
        result.risk_level = risk_result.level
        pipeline_stages["risk_score"] = risk_result.score
        pipeline_stages["risk_level"] = risk_result.level

        # ── Save images ──
        orig_path = RESULTS_DIR / f"{image_id}_original.jpg"
        proc_path = RESULTS_DIR / f"{image_id}_processed.jpg"
        cv2.imwrite(str(orig_path), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        cv2.imwrite(str(proc_path), cv2.cvtColor(enhanced, cv2.COLOR_RGB2BGR))

        pipeline_stages["pipeline_time_ms"] = round(elapsed, 1)
        result.metadata = pipeline_stages

        return result

    def process_polarization_raw(self, raw_bayer_bytes: bytes,
                                  device_id: str = "default",
                                  environment: Optional[Dict[str, float]] = None) -> BatchResult:
        """Process a raw DoFP polarization frame through the full pipeline.

        This is the primary entry point for the DoFP polarization camera.
        """
        return self.process_image(raw_bayer_bytes, device_id, environment,
                                  is_raw_polarization=True)

    def process_batch(self, images: List[bytes], device_id: str = "default",
                      environment: Optional[Dict[str, float]] = None) -> List[BatchResult]:
        """Process multiple images in sequence, sharing tracker state."""
        results = []
        for img_bytes in images:
            result = self.process_image(img_bytes, device_id, environment)
            results.append(result)
        return results

    def assess_risk(self, device_id: str,
                    environment: Optional[Dict[str, float]] = None,
                    composition: Optional[Dict[str, int]] = None,
                    total_count: int = 0) -> RiskResult:
        """Run risk assessment with tracker context."""
        return self.risk_assessor.assess_with_tracker(
            device_id=device_id,
            total_count=total_count,
            composition=composition or {},
            environment=environment,
        )

    def create_record(self, db_session, result: BatchResult,
                      device_id: str, image_path: str,
                      processed_image_path: str,
                      environment: Optional[Dict] = None) -> DetectionRecord:
        """Save detection result to database."""
        record = DetectionRecord(
            device_id=device_id,
            image_path=image_path,
            processed_image_path=processed_image_path,
            total_count=result.total_count,
            concentration_per_ul=result.concentration_cells_per_ul or 0,
            risk_level=result.risk_level,
            algae_composition=result.algae_composition,
            processing_time_ms=result.processing_time_ms,
            environment_data=environment or {},
            full_result=result.to_dict() if hasattr(result, 'to_dict') else {},
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)
        return record
