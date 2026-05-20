"""ML Inference Module for Algae Guardian."""

__all__ = [
    "AlgaeDetector", "AlgaePreprocessor", "DetectionResult", "BatchResult",
    "count_algae", "format_results", "PolarizationReconstructor", "AlgaeTracker",
]

# Lazily import heavy dependencies
def __getattr__(name):
    import importlib
    module_map = {
        "AlgaeDetector": ".inference",
        "AlgaePreprocessor": ".preprocessing",
        "DetectionResult": ".postprocessing",
        "BatchResult": ".postprocessing",
        "count_algae": ".postprocessing",
        "format_results": ".postprocessing",
        "PolarizationReconstructor": ".reconstructor",
        "AlgaeTracker": ".tracker",
    }
    if name in module_map:
        mod = importlib.import_module(module_map[name], __package__)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
