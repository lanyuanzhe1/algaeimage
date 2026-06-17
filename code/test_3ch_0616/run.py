"""全量 FMPD 293 张三通道融合 vs 单通道 I_enh×3 baseline 对比测试

技术路线:
  Baseline (当前V2产线):  RGB → 结构张量偏振模拟 → RDN → I_enh v2 (1ch) → [×3] → YOLO
  三通道融合 (本测试):     RGB → 结构张量偏振模拟 → RDN → [S0, I_enh_v2, corrected] 3ch → YOLO

输出: pic/pic_0616/11_三通道融合_0616测试/
  ├── YOLO输入前/    fusion_3ch.jpg + Ienh_1ch.jpg  (每样本2张)
  ├── YOLO结果/      detect_3ch.jpg + detect_1ch.jpg (每样本2张)
  └── comparison_summary.csv
"""
import os, sys, time, csv, cv2, numpy as np, traceback

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # code/
sys.path.insert(0, os.path.join(BASE, 'algae_image_v2'))

from core_engine.polarization_sim import simulate_polarization
from core_engine.reconstructor import load_rdn_model, reconstruct
from core_engine.enhancement import enhance, compute_stokes
from core_engine.inference import load_yolo, detect
from core_engine.config import IENH_ALPHA, IENH_BETA, IENH_GAMMA, PIPELINE_MAX_WIDTH

# ── Config ───────────────────────────────────────────────────────
V2_ROOT = os.path.join(BASE, 'algae_image_v2')
RDN_WEIGHTS = os.path.join(V2_ROOT, 'weights', 'rdn_polarization.pth')
YOLO_WEIGHTS = os.path.join(V2_ROOT, 'weights', 'best_v8s.pt')
OUT_DIR = os.path.join(BASE, '..', 'pic', 'pic_0616', '11_三通道融合_0616测试')
PRE_DIR = os.path.join(OUT_DIR, 'YOLO输入前')   # fusion_3ch + Ienh_1ch
DET_DIR = os.path.join(OUT_DIR, 'YOLO结果')     # detect_3ch + detect_1ch
os.makedirs(PRE_DIR, exist_ok=True)
os.makedirs(DET_DIR, exist_ok=True)

TIFF_DIR = os.path.join(BASE, 'algae_guardian', 'data',
                        'download', 'extracted', 'dataset', 'dataset')
DEVICE = 'cuda'

# ── Risk colors ──────────────────────────────────────────────────
RISK_COLORS = {'high': (38, 38, 220), 'medium': (11, 158, 245), 'low': (74, 163, 22)}

# ── Draw detection boxes ─────────────────────────────────────────
def draw_boxes(img, dets, w, h):
    """Draw YOLO detection boxes on image. img: uint8 RGB (H,W,3) or (H,W)."""
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
    out = img.copy()
    for d in dets:
        x1, y1, x2, y2 = [max(0, int(v)) for v in d['bbox']]
        x2, y2 = min(x2, w - 1), min(y2, h - 1)
        risk = d.get('risk_level', 'low')
        color = RISK_COLORS.get(risk, (128, 128, 128))
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 4)
        label = f"{d.get('class_name_zh', d['class_name'])} {d['confidence']:.2f}"
        cv2.putText(out, label, (x1, max(y1 - 6, 18)),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
    return out

# ── Load models ──────────────────────────────────────────────────
print('Loading models...', flush=True)
rdn = load_rdn_model(RDN_WEIGHTS, DEVICE)
yolo = load_yolo(YOLO_WEIGHTS, DEVICE)
print(f'  RDN: 612,356 params (PSNR 62.46dB)', flush=True)
print(f'  YOLO: best_v8s.pt (FMPD 5-class, mAP50 73.9%)', flush=True)

# ── Discover all TIFFs ───────────────────────────────────────────
all_tiffs = sorted([f for f in os.listdir(TIFF_DIR) if f.endswith('.tif')])
print(f'\nFMPD dataset: {len(all_tiffs)} TIFFs')

# ── CSV ──────────────────────────────────────────────────────────
csv_path = os.path.join(OUT_DIR, 'comparison_summary.csv')
csv_f = open(csv_path, 'w', newline='', encoding='utf-8')
csv_w = csv.writer(csv_f)
csv_w.writerow(['snap_id', 'width', 'height',
                'time_total_s', 'time_rdn_s',
                'det_1ch_count', 'det_3ch_count',
                'det_1ch_classes', 'det_3ch_classes',
                'avg_conf_1ch', 'avg_conf_3ch'])

# ── Stats ────────────────────────────────────────────────────────
stats = {'total': 0, 'rdn_time': 0, 'yolo_time': 0,
         'det_1ch': 0, 'det_3ch': 0,
         'same': 0, 'more_3ch': 0, 'more_1ch': 0}

# ── Process all TIFFs ────────────────────────────────────────────
try:
 for idx, tiff_name in enumerate(all_tiffs):
    snap_id = tiff_name.replace('.tif', '')
    tiff_path = os.path.join(TIFF_DIR, tiff_name)
    t_start = time.time()

    # 0. Load RGB + resize to max_width (prevent GPU OOM on 2080px)
    rgb = cv2.imread(tiff_path)
    rgb = cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB)
    h, w = rgb.shape[:2]
    if PIPELINE_MAX_WIDTH and w > PIPELINE_MAX_WIDTH:
        scale = PIPELINE_MAX_WIDTH / w
        new_h = int(h * scale)
        rgb = cv2.resize(rgb, (PIPELINE_MAX_WIDTH, new_h), interpolation=cv2.INTER_AREA)
        h, w = rgb.shape[:2]

    # 1. 结构张量偏振模拟
    I_channels = simulate_polarization(rgb)  # (4, H, W) float32

    # 2. RDN 去噪
    t_rdn0 = time.time()
    I_clean = reconstruct(rdn, I_channels, DEVICE)
    t_rdn = time.time() - t_rdn0

    # 3. Stokes + I_enh v2
    stokes = compute_stokes(I_clean)
    S0 = stokes['S0']
    DoLP = stokes['DoLP']
    I_enh_v2 = enhance(I_clean, alpha=IENH_ALPHA, beta=IENH_BETA, gamma=IENH_GAMMA)

    # 4. 三通道融合 [S0_norm, I_enh_v2, corrected]
    s0_min, s0_max = S0.min(), S0.max()
    S0_norm = ((S0 - s0_min) / (s0_max - s0_min + 1e-10) * 255).astype(np.uint8)

    I_enh_uint8 = np.clip(I_enh_v2 * 255, 0, 255).astype(np.uint8)

    corrected = S0_norm.astype(np.float32) * (1.0 - 0.5 * DoLP)
    corrected_uint8 = np.clip(corrected, 0, 255).astype(np.uint8)

    fusion_3ch = np.stack([S0_norm, I_enh_uint8, corrected_uint8], axis=-1)  # (H,W,3)

    # 5. YOLO 检测对比
    t_yolo0 = time.time()
    det_1ch = detect(yolo, I_enh_v2)    # 单通道×3 (当前V2)
    det_3ch = detect(yolo, fusion_3ch)   # 三通道融合 (本测试)
    t_yolo = time.time() - t_yolo0
    t_total = time.time() - t_start

    # 6. 保存图片 — YOLO输入前
    cv2.imwrite(os.path.join(PRE_DIR, f'{snap_id}_Ienh_1ch.jpg'),
                I_enh_uint8)  # 灰度，YOLO会自动cv2读取为灰度
    cv2.imwrite(os.path.join(PRE_DIR, f'{snap_id}_fusion_3ch.jpg'),
                cv2.cvtColor(fusion_3ch, cv2.COLOR_RGB2BGR))

    # 7. 保存图片 — YOLO结果
    cv2.imwrite(os.path.join(DET_DIR, f'{snap_id}_detect_1ch.jpg'),
                cv2.cvtColor(draw_boxes(I_enh_uint8, det_1ch, w, h), cv2.COLOR_RGB2BGR))
    cv2.imwrite(os.path.join(DET_DIR, f'{snap_id}_detect_3ch.jpg'),
                cv2.cvtColor(draw_boxes(fusion_3ch, det_3ch, w, h), cv2.COLOR_RGB2BGR))

    # 8. Stats + CSV
    n1, n3 = len(det_1ch), len(det_3ch)
    stats['total'] += 1
    stats['rdn_time'] += t_rdn
    stats['yolo_time'] += t_yolo
    stats['det_1ch'] += n1
    stats['det_3ch'] += n3
    if n1 == n3: stats['same'] += 1
    elif n3 > n1: stats['more_3ch'] += 1
    else: stats['more_1ch'] += 1

    avg_c1 = np.mean([d['confidence'] for d in det_1ch]) if det_1ch else 0
    avg_c3 = np.mean([d['confidence'] for d in det_3ch]) if det_3ch else 0

    csv_w.writerow([snap_id, w, h,
                    f'{t_total:.2f}', f'{t_rdn:.2f}',
                    n1, n3,
                    '|'.join(d['class_name'] for d in det_1ch),
                    '|'.join(d['class_name'] for d in det_3ch),
                    f'{avg_c1:.4f}', f'{avg_c3:.4f}'])

    # Progress
    if (idx + 1) % 10 == 0 or idx < 3:
        done = idx + 1
        remaining = len(all_tiffs) - done
        eta = (t_total * remaining) / 60 if done > 0 else 0
        print(f'  [{done:3d}/{len(all_tiffs)}] '
              f'R={t_rdn:.1f}s Y={t_yolo:.1f}s T={t_total:.1f}s | '
              f'1ch={n1} 3ch={n3} | ETA {eta:.0f}min', flush=True)
    csv_f.flush()

except Exception:
    traceback.print_exc()
    csv_f.close()
    sys.exit(1)

# ── Summary ──────────────────────────────────────────────────────
print(f'\n{"="*70}')
print(f'FMPD {stats["total"]} images 完成')
print(f'  RDN   耗时: {stats["rdn_time"]:.0f}s  ({stats["rdn_time"]/stats["total"]:.1f}s/img)')
print(f'  YOLO  耗时: {stats["yolo_time"]:.0f}s')
print(f'  检测数相同:   {stats["same"]}')
print(f'  3ch 更多:     {stats["more_3ch"]}')
print(f'  1ch 更多:     {stats["more_1ch"]}')
print(f'  1ch 总检测数: {stats["det_1ch"]}')
print(f'  3ch 总检测数: {stats["det_3ch"]}')
print(f'\n  输出目录: {OUT_DIR}')
print(f'    YOLO输入前/ : {len(os.listdir(PRE_DIR))} files')
print(f'    YOLO结果/   : {len(os.listdir(DET_DIR))} files')
csv_f.close()
