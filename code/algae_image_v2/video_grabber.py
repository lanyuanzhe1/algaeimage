"""Video grabber — read AVI frames and POST to detection backend.

Usage:
    python video_grabber.py video/Video_20260611215520245.avi
    python video_grabber.py video/Video_20260611215520245.avi --fps 5 --loop

Without camera hardware, this simulates the live acquisition flow:
AVI file → cv2 frame → POST /api/v1/detect/visualize → backend pipeline.
"""
import argparse
import sys
import time
from pathlib import Path

import cv2
import requests

BASE_URL = "http://127.0.0.1:8000/api/v1"
DEFAULT_FPS = 10  # target frames per second to send


def main():
    parser = argparse.ArgumentParser(description="AVI frame grabber → detection backend")
    parser.add_argument("video", help="Path to AVI file")
    parser.add_argument("--fps", type=float, default=DEFAULT_FPS,
                        help=f"Target frames/sec to POST (default: {DEFAULT_FPS})")
    parser.add_argument("--loop", action="store_true",
                        help="Loop video continuously (for demo mode)")
    parser.add_argument("--once", action="store_true",
                        help="Send one frame and exit (quick smoke test)")
    parser.add_argument("--base-url", default=BASE_URL,
                        help=f"Backend base URL (default: {BASE_URL})")
    args = parser.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        print(f"[ERROR] Video not found: {video_path}")
        sys.exit(1)

    cap = cv2.VideoCapture(str(video_path))
    source_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"[INFO] Video: {video_path.name} | {w}x{h} | {source_fps:.1f} fps | {total_frames} frames")
    print(f"[INFO] Target send rate: {args.fps} fps")
    print(f"[INFO] Backend: {args.base_url}")

    interval = 1.0 / args.fps
    frame_idx = 0
    sent_count = 0
    fail_count = 0
    start_time = time.time()

    try:
        while True:
            if args.once and sent_count >= 1:
                break

            ret, frame = cap.read()
            if not ret:
                if args.loop:
                    print("[INFO] Video ended, looping...")
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    frame_idx = 0
                    continue
                else:
                    print("[INFO] Video ended.")
                    break

            frame_idx += 1

            # Throttle to target fps
            elapsed = time.time() - start_time
            expected = frame_idx / args.fps
            if elapsed < expected:
                time.sleep(expected - elapsed)

            # Encode frame as JPEG bytes
            _, jpeg = cv2.imencode(".jpg", frame)
            files = {"file": (f"frame_{frame_idx:06d}.jpg", jpeg.tobytes(), "image/jpeg")}

            try:
                t0 = time.time()
                resp = requests.post(
                    f"{args.base_url}/detect/visualize",
                    files=files,
                    timeout=30,
                )
                dt = (time.time() - t0) * 1000

                if resp.status_code == 200:
                    data = resp.json()
                    n_det = len(data.get("detections", []))
                    risk = data.get("risk_level", "-")
                    sent_count += 1
                    print(f"  [{sent_count:04d}] frame={frame_idx} | "
                          f"{n_det} detections | risk={risk} | {dt:.0f}ms")
                else:
                    fail_count += 1
                    print(f"  [FAIL] frame={frame_idx} | HTTP {resp.status_code} | {resp.text[:80]}")

            except requests.exceptions.ConnectionError:
                print("[FATAL] Cannot connect to backend. Is it running?")
                print("        Start with: python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000")
                sys.exit(1)
            except Exception as e:
                fail_count += 1
                print(f"  [ERR] frame={frame_idx} | {e}")

    except KeyboardInterrupt:
        print("\n[INFO] Stopped by user.")

    finally:
        cap.release()
        elapsed = time.time() - start_time
        print(f"\n[DONE] Sent={sent_count} Failed={fail_count} in {elapsed:.1f}s "
              f"({sent_count / max(elapsed, 0.1):.1f} fps effective)")


if __name__ == "__main__":
    main()
