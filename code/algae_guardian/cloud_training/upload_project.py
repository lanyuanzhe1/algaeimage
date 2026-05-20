"""Upload algae_guardian project to cloud server via tar+SSH."""
import os
import tarfile
import tempfile
from pathlib import Path
from cloud_ssh import CloudServer

PROJECT_ROOT = Path(__file__).resolve().parent.parent  # algae_guardian/
EXCLUDE_DIRS = {
    "data/rdn_training",
    "datasets/lifewatch/images",
    "datasets/lifewatch/dataset_files",
    "__pycache__",
    ".pytest_cache",
    "backend/static/results",
    "tests/samples",
    "tests/yolo_input",
}
EXCLUDE_EXTS = {".pyc", ".log", ".zip", ".tar.gz", ".tar"}


def create_project_tar(output_path: str):
    """Create a tar.gz of the project excluding large data dirs."""
    with tarfile.open(output_path, "w:gz") as tar:
        for f in PROJECT_ROOT.rglob("*"):
            # Skip excluded dirs
            rel = f.relative_to(PROJECT_ROOT)
            if any(rel.as_posix().startswith(excl) for excl in EXCLUDE_DIRS):
                continue
            if f.suffix in EXCLUDE_EXTS:
                continue
            if f.is_file():
                tar.add(str(f), arcname=str(rel))
    size_mb = Path(output_path).stat().st_size / (1024 * 1024)
    print(f"Created project archive: {output_path} ({size_mb:.1f} MB)")
    return size_mb


def upload_and_extract():
    tar_path = os.path.join(tempfile.gettempdir(), "algae_guardian.tar.gz")

    print("Step 1: Creating project archive (excluding large data dirs)...")
    create_project_tar(tar_path)

    print("\nStep 2: Uploading to cloud server...")
    with CloudServer() as s:
        # Clean up any old version
        # s.run("rm -rf /data/algae_guardian")

        # Upload tar
        s.upload(tar_path, "/data/algae_guardian.tar.gz")

        # Extract
        print("\nStep 3: Extracting on cloud server...")
        r = s.run(
            "cd /data && rm -rf algae_guardian && "
            "tar -xzf algae_guardian.tar.gz && "
            "rm -f algae_guardian.tar.gz && "
            "ls -la algae_guardian/ | head -20"
        )
        print(r.stdout)

        # Verify
        print("\nStep 4: Verifying key files...")
        for f in ["ml/reconstructor.py", "ml/models/rdn_polarization.pth",
                   "image_processing/polarization_sim.py",
                   "cloud_training/batch_process_rdn.py",
                   "cloud_training/train_yolo_cloud.py"]:
            exists = s.file_exists(f"/data/algae_guardian/{f}")
            print(f"  {'✓' if exists else '✗'} {f}")

        # Fix imports - ensure Python path
        print("\nStep 5: Testing Python import...")
        r = s.run(
            "cd /data/algae_guardian && "
            "/data/miniconda/envs/ican/bin/python -c "
            '"from ml.reconstructor import RDN; print(\'RDN import OK\')"'
        )
        print(f"  {r.stdout}")

    # Cleanup
    os.unlink(tar_path)
    print("\nDone! Project uploaded to /data/algae_guardian/")


if __name__ == "__main__":
    upload_and_extract()
