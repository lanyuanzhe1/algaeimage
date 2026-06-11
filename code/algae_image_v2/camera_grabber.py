"""Camera grabber — MVS SDK direct frame capture → detection backend.

MV-CA013-20GC (GigE, 1.3MP color).
Requires: MVS installed at A:/Program Files/MVS.

Usage:
    python camera_grabber.py              # continuous, sends frames to backend
    python camera_grabber.py --fps 10     # throttle to 10 fps
    python camera_grabber.py --once       # grab one frame and exit (quick test)

Architecture:
    SDK callback → numpy frame → JPEG encode → POST /api/v1/detect/visualize
"""
import argparse
import ctypes
import os
import sys
import time
from ctypes import POINTER, byref, cast, c_bool, c_void_p, memset

import cv2
import numpy as np
import requests

# ═══════════════════════════════════════════════════════════════
# MVS SDK setup
# ═══════════════════════════════════════════════════════════════
_MVS_DIR = r"A:\Program Files\MVS"
_MVIMP_DIR = os.path.join(_MVS_DIR, "Development", "Samples", "Python", "MvImport")
_DLL_DIR = r"C:\Program Files (x86)\Common Files\MVS\Runtime\Win64_x64"

if _MVIMP_DIR not in sys.path:
    sys.path.insert(0, _MVIMP_DIR)

# Must add DLL directory to PATH and loader BEFORE importing SDK classes
os.environ["PATH"] = _DLL_DIR + ";" + os.environ.get("PATH", "")
try:
    os.add_dll_directory(_DLL_DIR)
except AttributeError:
    pass  # Python < 3.8

from MvCameraControl_class import (
    MvCamera, MV_CC_DEVICE_INFO_LIST, MV_CC_DEVICE_INFO,
    MV_FRAME_OUT, MV_CC_HB_DECODE_PARAM, MV_CC_PIXEL_CONVERT_PARAM_EX,
    MV_ACCESS_Exclusive, MV_TRIGGER_MODE_OFF,
    MV_GIGE_DEVICE, MV_USB_DEVICE, MV_GENTL_GIGE_DEVICE,
    get_platform_functype,
    PixelType_Gvsp_Mono8, PixelType_Gvsp_RGB8_Packed,
    PixelType_Gvsp_Undefined,
)

# Pixel type constants for HB decode check
_PIXEL_TYPES_HB = {
    0x02180001, 0x02180003, 0x02180005, 0x02180007,  # Mono HB
    0x02180009, 0x0218000B, 0x0218000D, 0x0218000F, 0x02180011,
    0x02180013, 0x02180015,  # Bayer HB
    0x02280001, 0x02280003, 0x02280005, 0x02280007,  # RGB/BGR HB packed
    0x02280009, 0x0228000B, 0x0228000D, 0x0228000F,
    0x02280011, 0x02280013,  # YUV HB
}

BASE_URL = "http://127.0.0.1:8000/api/v1"

# ═══════════════════════════════════════════════════════════════
# Frame queue (SDK callback → send loop)
# ═══════════════════════════════════════════════════════════════
import threading

_frame_queue = []
_frame_lock = threading.Lock()
_running = True


def _decode_frame(cam, stFrame):
    """HB decode + pixel convert → RGB numpy array, or None on failure."""
    w, h = stFrame.stFrameInfo.nWidth, stFrame.stFrameInfo.nHeight
    pixel_type = stFrame.stFrameInfo.enPixelType

    stDecodeParam = MV_CC_HB_DECODE_PARAM()
    stConvertParam = MV_CC_PIXEL_CONVERT_PARAM_EX()
    memset(byref(stConvertParam), 0, ctypes.sizeof(stConvertParam))

    if pixel_type in _PIXEL_TYPES_HB:
        decode_len = w * h * 3
        decode_buf = (ctypes.c_ubyte * decode_len)()
        stDecodeParam.pSrcBuf = stFrame.pBufAddr
        stDecodeParam.nSrcLen = stFrame.stFrameInfo.nFrameLen
        stDecodeParam.pDstBuf = decode_buf
        stDecodeParam.nDstBufSize = decode_len
        ret = cam.MV_CC_HBDecode(stDecodeParam)
        if ret != 0:
            return None
        stConvertParam.pSrcData = stDecodeParam.pDstBuf
        stConvertParam.nSrcDataLen = stDecodeParam.nDstBufLen
        stConvertParam.enSrcPixelType = stDecodeParam.enDstPixelType
    else:
        stConvertParam.pSrcData = stFrame.pBufAddr
        stConvertParam.nSrcDataLen = stFrame.stFrameInfo.nFrameLen
        stConvertParam.enSrcPixelType = pixel_type

    dst_ch = 3
    dst_len = dst_ch * w * h
    dst_buf = (ctypes.c_ubyte * dst_len)()
    stConvertParam.nWidth = w
    stConvertParam.nHeight = h
    stConvertParam.enDstPixelType = PixelType_Gvsp_RGB8_Packed
    stConvertParam.pDstBuffer = dst_buf
    stConvertParam.nDstBufferSize = dst_len

    ret = cam.MV_CC_ConvertPixelTypeEx(stConvertParam)
    if ret != 0:
        return None

    return np.frombuffer(dst_buf, dtype=np.uint8, count=dst_len).reshape(h, w, 3)


# ═══════════════════════════════════════════════════════════════
# SDK callback
# ═══════════════════════════════════════════════════════════════
_functype = get_platform_functype()
_FrameCallbackType = _functype(None, POINTER(MV_FRAME_OUT), c_void_p, c_bool)


def _image_callback(pstFrame, pUser, bAutoFree):
    """Called by SDK for each incoming frame."""
    stFrame = cast(pstFrame, POINTER(MV_FRAME_OUT)).contents
    if not stFrame:
        return
    user_obj = cast(pUser, ctypes.py_object).value
    cam = user_obj
    rgb = _decode_frame(cam, stFrame)
    if rgb is not None:
        with _frame_lock:
            _frame_queue.append(rgb)
    if not bAutoFree and pUser is not None:
        cam.MV_CC_FreeImageBuffer(stFrame)


_CALLBACK = _FrameCallbackType(_image_callback)


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

def main():
    global _running

    parser = argparse.ArgumentParser(description="MVS SDK camera grabber — MV-CA013-20GC")
    parser.add_argument("--fps", type=float, default=5,
                        help="Target send rate in fps (default: 5)")
    parser.add_argument("--duration", type=float, default=0,
                        help="Run for N seconds (0 = until Ctrl+C)")
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--once", action="store_true",
                        help="Grab one frame and exit")
    args = parser.parse_args()

    # ── Init SDK ───────────────────────────────────────────────
    MvCamera.MV_CC_Initialize()
    print(f"[INFO] SDK version: 0x{MvCamera.MV_CC_GetSDKVersion():x}")

    # ── Enum devices ───────────────────────────────────────────
    deviceList = MV_CC_DEVICE_INFO_LIST()
    tlayer = MV_GIGE_DEVICE | MV_USB_DEVICE
    ret = MvCamera.MV_CC_EnumDevices(tlayer, deviceList)
    if ret != 0 or deviceList.nDeviceNum == 0:
        print("[FATAL] No camera found. Is MVS client closed? Check GigE connection.")
        MvCamera.MV_CC_Finalize()
        sys.exit(1)

    print(f"[INFO] Found {deviceList.nDeviceNum} device(s)")

    # Pick first device
    dev_info = cast(deviceList.pDeviceInfo[0], POINTER(MV_CC_DEVICE_INFO)).contents
    if dev_info.nTLayerType in (MV_GIGE_DEVICE, MV_GENTL_GIGE_DEVICE):
        try:
            name = bytes(dev_info.SpecialInfo.stGigEInfo.chModelName).decode("ascii", errors="replace").strip("\x00")
            print(f"[INFO] GigE device: {name}")
        except Exception:
            pass

    # ── Create handle + open ──────────────────────────────────
    cam = MvCamera()
    ret = cam.MV_CC_CreateHandle(dev_info)
    if ret != 0:
        print(f"[FATAL] CreateHandle failed: 0x{ret:x}")
        MvCamera.MV_CC_Finalize()
        sys.exit(1)

    ret = cam.MV_CC_OpenDevice(MV_ACCESS_Exclusive, 0)
    if ret != 0:
        print(f"[FATAL] OpenDevice failed: 0x{ret:x}. Is MVS client running? Close it first.")
        cam.MV_CC_DestroyHandle()
        MvCamera.MV_CC_Finalize()
        sys.exit(1)

    # GigE optimisation
    if dev_info.nTLayerType in (MV_GIGE_DEVICE, MV_GENTL_GIGE_DEVICE):
        pkt = cam.MV_CC_GetOptimalPacketSize()
        if pkt > 0:
            cam.MV_CC_SetIntValue("GevSCPSPacketSize", pkt)

    cam.MV_CC_SetEnumValue("TriggerMode", MV_TRIGGER_MODE_OFF)

    # Register callback
    ret = cam.MV_CC_RegisterImageCallBackEx2(_CALLBACK, ctypes.py_object(cam), True)
    if ret != 0:
        print(f"[FATAL] RegisterImageCallBackEx2 failed: 0x{ret:x}")
        cam.MV_CC_CloseDevice()
        cam.MV_CC_DestroyHandle()
        MvCamera.MV_CC_Finalize()
        sys.exit(1)

    # Start grabbing
    ret = cam.MV_CC_StartGrabbing()
    if ret != 0:
        print(f"[FATAL] StartGrabbing failed: 0x{ret:x}")
        cam.MV_CC_CloseDevice()
        cam.MV_CC_DestroyHandle()
        MvCamera.MV_CC_Finalize()
        sys.exit(1)

    print(f"[INFO] Grabbing started. Sending at ~{args.fps} fps to {args.base_url}")
    if args.once:
        print("[INFO] --once mode: will exit after first frame sent")

    # ── Send loop ─────────────────────────────────────────────
    interval = 1.0 / args.fps
    start_time = time.time()
    sent_count = 0
    fail_count = 0
    last_send = 0.0

    try:
        while _running:
            now = time.time()

            if args.duration > 0 and (now - start_time) >= args.duration:
                break

            if now - last_send < interval:
                time.sleep(0.01)
                continue

            with _frame_lock:
                if _frame_queue:
                    frame = _frame_queue[-1]
                    _frame_queue.clear()
                else:
                    frame = None

            if frame is None:
                time.sleep(0.01)
                continue

            _, jpeg = cv2.imencode(".jpg", frame)
            files = {"file": (f"cam_{sent_count:06d}.jpg", jpeg.tobytes(), "image/jpeg")}

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
                    sent_count += 1
                    last_send = now
                    n_det = len(data.get("detections", []))
                    risk = data.get("risk_level", "-")
                    print(f"  [{sent_count:04d}] {n_det} detections | risk={risk} | {dt:.0f}ms")
                    if args.once:
                        break
                else:
                    fail_count += 1
                    print(f"  [FAIL] HTTP {resp.status_code} | {resp.text[:80]}")
            except Exception as e:
                fail_count += 1
                print(f"  [ERR] {e}")

    except KeyboardInterrupt:
        print("\n[INFO] Stopped by user.")

    finally:
        _running = False
        cam.MV_CC_StopGrabbing()
        cam.MV_CC_CloseDevice()
        cam.MV_CC_DestroyHandle()
        MvCamera.MV_CC_Finalize()
        elapsed = time.time() - start_time
        print(f"\n[DONE] Sent={sent_count} Failed={fail_count} in {elapsed:.1f}s "
              f"({sent_count / max(elapsed, 0.1):.1f} fps effective)")


if __name__ == "__main__":
    main()
