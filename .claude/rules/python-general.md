---
paths: code/**/*.py
---

# Python General Rules

## Environment

- **Conda `ican` required** for any code that imports `torch` or `ultralytics`.
- Path: `A:\Anaconda_envs\envs\ican`, Python 3.11.
- Tests needing torch/ultralytics only pass in conda ican.
- Use `python -m pytest` not bare `pytest` to ensure correct Python.

## Dependencies

- `code/algae_image_v1/requirements.txt` uses **flexible lower bounds** (`torch>=2.0.0`).
- `code/algae_guardian/requirements.txt` uses **pinned versions** (`fastapi==0.111.0`).
- Don't mix strategies — V1 product uses `>=`, research uses `==`.

## Testing

```bash
cd e:/code/algaeimage/code/algae_image_v1
python -m pytest tests/test_pipeline.py -v   # Core engine (5 test classes)
python -m pytest tests/test_frontend.py -v   # Frontend HTML/JS structure
```

- `conftest.py` provides session-level RDN + YOLO model loading fixtures.
- Tests use synthetic images (numpy random), not real fixture images.

## Style

- **No linting/formatting configured.** No ruff, black, flake8, or isort.
- Follow whatever style the existing file uses — consistency within file > global standard.
- Comments in Chinese are acceptable in this repo.

## Git exclusions

- `*.pt`, `*.pth`, `*.tif`, `*.zip`, `*.npz` — model weights and data NOT in git.
- `data/`, `output/` directories in gitignore.
- Git LFS tracks: `*.tif *.zip *.pth *.pt *.npz *.mp4`.
- `code/SPDRDN/` is a nested independent git repo — don't commit its changes from the parent repo.
