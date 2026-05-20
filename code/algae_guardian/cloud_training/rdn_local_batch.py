"""本地 RDN 批量处理：npz → RDN重建 → I_enh → 质量标准化 → YOLO输入

Pipeline:
    .npz (I0/I45/I90/I135) → RDN(4→16→16→4) → S0/S1/S2 → AoP/DoLP
    → I_enh = S0 + λ1·S0 + λ2·AoP + λ3·DoLP
    → QualityAssessor(Q) 标准化 → letterbox resize → YOLO数据集

用法:
    A:\Anaconda_envs\envs\ican\python.exe rdn_local_batch.py
"""

import sys, json, csv, time
from pathlib import Path
import numpy as np
import cv2
from tqdm import tqdm

# ── 项目根目录 ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── 路径配置（根据用户确认） ──
NPZ_DIR = PROJECT_ROOT / "data" / "fmpd_download" / "extracted" / "dataset" / "polarized" / "polarization"
METADATA_PATH = NPZ_DIR.parent / "metadata.json"
COCO_JSON = NPZ_DIR.parent.parent / "dataset" / "annotations.json"  # dataset/dataset/annotations.json
MODEL_PATH = PROJECT_ROOT / "ml" / "models" / "rdn_polarization.pth"
OUTPUT_DIR = PROJECT_ROOT / "data" / "fmpd_rdn_output"

IMG_SIZE = 640
DEVICE = "cuda"


def ensure_imports():
    """动态导入 algae_guardian 模块（ican 环境已有 torch）。"""
    global PolarizationReconstructor, PolarizationProcessor, ImageEnhancer, QualityAssessor

    from ml.reconstructor import PolarizationReconstructor
    from image_processing.polarization import PolarizationProcessor
    from image_processing.enhancement import ImageEnhancer
    from image_processing.quality import QualityAssessor

    return (PolarizationReconstructor, PolarizationProcessor,
            ImageEnhancer, QualityAssessor)


def convert_coco_to_yolo(coco_json: str, output_dir: str, filenames_map: set):
    """Convert COCO JSON to YOLO .txt labels (只保留 filenames_map 中的图片)。"""
    import json
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(coco_json) as f:
        coco = json.load(f)

    # category id → YOLO class id (连续)
    cat_map = {cat["id"]: i for i, cat in enumerate(coco["categories"])}
    class_names = [cat["name"] for cat in coco["categories"]]

    # image id → filename stem
    img_map = {}
    for img in coco["images"]:
        stem = Path(img["file_name"]).stem
        if stem in filenames_map:
            img_map[img["id"]] = {
                "stem": stem,
                "w": img["width"],
                "h": img["height"],
            }

    count = 0
    for ann in coco["annotations"]:
        img_id = ann["image_id"]
        if img_id not in img_map:
            continue
        info = img_map[img_id]
        w, h = info["w"], info["h"]
        x, y, bw, bh = ann["bbox"]
        cx = (x + bw / 2) / w
        cy = (y + bh / 2) / h
        bw_n = bw / w
        bh_n = bh / h
        cls_id = cat_map[ann["category_id"]]

        label_path = out_dir / f"{info['stem']}.txt"
        with open(label_path, "a") as f:
            f.write(f"{cls_id} {cx:.6f} {cy:.6f} {bw_n:.6f} {bh_n:.6f}\n")
        count += 1

    return class_names


def quality_standardize(image: np.ndarray, assessor) -> tuple:
    """质量评估 + 标准化：返回 (标准化后图像, QualityReport)。"""
    report = assessor.assess(image)

    # 标准化：将图像拉伸到目标对比度/亮度范围
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    current_mean = gray.mean()
    current_std = gray.std()

    # 目标值（经验值：显微图像最适合 YOLO 的范围）
    target_mean = 120.0
    target_std = 55.0

    if current_std > 1e-6:
        # 线性拉伸使 contrast ≈ target_std, brightness ≈ target_mean
        float_img = image.astype(np.float32)
        scaled = (float_img - current_mean) * (target_std / current_std) + target_mean
        standardized = np.clip(scaled, 0, 255).astype(np.uint8)
    else:
        standardized = image

    return standardized, report


def letterbox_resize(image: np.ndarray, target_size: int = 640):
    """Resize + letterbox padding to target_size×target_size."""
    h, w = image.shape[:2]
    scale = min(target_size / h, target_size / w)
    new_w, new_h = int(w * scale), int(h * scale)
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    dw = target_size - new_w
    dh = target_size - new_h
    top, bottom = dh // 2, dh - dh // 2
    left, right = dw // 2, dw - dw // 2
    padded = cv2.copyMakeBorder(resized, top, bottom, left, right,
                                cv2.BORDER_CONSTANT, value=(114, 114, 114))
    return padded, scale, (left, top, dw, dh)


def process_single_npz(npz_path: Path, reconstructor, polarizer, enhancer, assessor):
    """单个 npz 完整流程：RDN → I_enh → 质量标准化 → letterbox。"""
    data = np.load(npz_path)
    I0 = data["I0"].astype(np.float32)
    I45 = data["I45"].astype(np.float32)
    I90 = data["I90"].astype(np.float32)
    I135 = data["I135"].astype(np.float32)

    # ── RDN 重建 (4ch → 3ch) ──
    use_deep = reconstructor.is_available()
    recon_3ch = reconstructor.reconstruct(I0, I45, I90, I135, use_deep=use_deep)

    # ── 从 RDN 输出提取 S 参数、AoP、DoLP ──
    S0_recon = recon_3ch[:, :, 0].astype(np.float32)
    S1_recon = recon_3ch[:, :, 1].astype(np.float32) * 2 - 128
    S2_recon = recon_3ch[:, :, 2].astype(np.float32) * 2 - 128
    DoLP = np.sqrt(S1_recon**2 + S2_recon**2) / (S0_recon + 1e-10)
    AoP = 0.5 * np.arctan2(S2_recon, S1_recon)

    # ── I_enh 偏振增强 ──
    enhanced = polarizer.polarization_enhancement(S0_recon, DoLP, AoP)

    # ── 后向散射抑制 ──
    corrected = polarizer.suppress_backscatter(S0_recon, DoLP)

    # ── S0 min-max 归一化 ──
    S0_norm = (
        ((S0_recon - S0_recon.min()) / (S0_recon.max() - S0_recon.min() + 1e-10) * 255)
        .astype(np.uint8)
    )

    # ── 组合三通道 ──
    recon_input = np.stack([S0_norm, enhanced, corrected], axis=-1)
    final = enhancer.enhance(recon_input, color_correct=True, clahe=True, dehaze=False)

    # ── 质量标准化 ──
    standardized, quality_report = quality_standardize(final, assessor)

    # ── Letterbox resize ──
    padded, scale, pad = letterbox_resize(standardized, IMG_SIZE)

    # 质量检查：Q >= fair 且不模糊
    usable = assessor.is_usable(quality_report)

    return padded, quality_report, usable


def main():
    print("=" * 60)
    print("  本地 RDN 批量处理 — npz → YOLO 输入")
    print("=" * 60)
    t_start = time.time()

    # ── 导入 ──
    print("\n[1/6] 加载模块...")
    PolarizationReconstructor, PolarizationProcessor, ImageEnhancer, QualityAssessor = ensure_imports()
    print("      模块加载完成")

    # ── 收集 npz ──
    npz_files = sorted(NPZ_DIR.glob("*.npz"))
    if not npz_files:
        print(f"[ERROR] 在 {NPZ_DIR} 中未找到 .npz 文件")
        sys.exit(1)
    print(f"\n[2/6] 找到 {len(npz_files)} 个 .npz 文件")
    print(f"      输入目录: {NPZ_DIR}")

    # ── COCO → YOLO 标签 ──
    print(f"\n[3/6] 转换 COCO 标注 → YOLO 格式...")
    stems_293 = {f.stem for f in npz_files}
    class_names = []
    if COCO_JSON.exists():
        class_names = convert_coco_to_yolo(str(COCO_JSON), str(OUTPUT_DIR / "labels"), stems_293)
        print(f"      类别: {class_names} ({len(class_names)} 类)")
    else:
        print(f"      COCO JSON 未找到，跳过标签转换")

    # ── 加载 RDN 模型 ──
    print(f"\n[4/6] 加载 RDN 模型: {MODEL_PATH}")
    reconstructor = PolarizationReconstructor(model_path=str(MODEL_PATH), device=DEVICE)
    loaded = reconstructor.load_model()
    print(f"      模型加载: {'深度模式' if loaded else '解析降级'}")

    # ── 加载增强模块 + 质量评估 ──
    print(f"\n[5/6] 加载增强 & 质量评估模块...")
    polarizer = PolarizationProcessor()
    enhancer = ImageEnhancer()
    assessor = QualityAssessor(
        w_c=0.35, w_s=0.35, w_f=0.15, w_o=0.10, w_b=0.05,
        q_good=0.65, q_fair=0.40,
    )

    # ── 批量处理 ──
    print(f"\n[6/6] 处理 {len(npz_files)} 个文件...")
    (OUTPUT_DIR / "images").mkdir(parents=True, exist_ok=True)

    quality_log = []
    stats = {"total": 0, "good": 0, "fair": 0, "poor": 0, "usable": 0, "skipped": 0}

    for npz_path in tqdm(npz_files, desc="RDN 处理中"):
        stem = npz_path.stem
        try:
            result_img, q_report, usable = process_single_npz(
                npz_path, reconstructor, polarizer, enhancer, assessor
            )

            # 保存图像（无论质量好坏都保存，但记录）
            out_path = OUTPUT_DIR / "images" / f"{stem}.jpg"
            cv2.imwrite(str(out_path), cv2.cvtColor(result_img, cv2.COLOR_RGB2BGR))

            # 记录质量日志
            quality_log.append({
                "file": stem,
                "Q_score": q_report.quality_score,
                "sharpness": q_report.sharpness,
                "brightness": q_report.brightness,
                "contrast": q_report.contrast,
                "blur": q_report.blur_detected,
                "overexposed": q_report.overexposed,
                "underexposed": q_report.underexposed,
                "overall": q_report.overall_quality,
                "usable": usable,
                "issues": "; ".join(q_report.issues),
            })

            stats["total"] += 1
            stats[q_report.overall_quality] += 1
            if usable:
                stats["usable"] += 1
            else:
                stats["skipped"] += 1

        except Exception as e:
            print(f"\n  [ERROR] {stem}: {e}")
            quality_log.append({"file": stem, "error": str(e)})
            stats["skipped"] += 1
            continue

    elapsed = time.time() - t_start

    # ── 保存质量报告 ──
    log_path = OUTPUT_DIR / "quality_report.csv"
    if quality_log:
        with open(log_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=quality_log[0].keys())
            writer.writeheader()
            writer.writerows(quality_log)

    # ── 创建 dataset.yaml ──
    names_str = json.dumps(class_names) if class_names else '["algae"]'
    yaml_content = (
        f"# YOLO dataset config (auto-generated by rdn_local_batch.py)\n"
        f"path: {OUTPUT_DIR.resolve()}\n"
        f"train: images\n"
        f"val: images\n\n"
        f"nc: {len(class_names) if class_names else 1}\n"
        f"names: {names_str}\n"
    )
    with open(OUTPUT_DIR / "dataset.yaml", "w") as f:
        f.write(yaml_content)

    # ── 打印统计 ──
    print("\n" + "=" * 60)
    print(f"  处理完成！耗时: {elapsed:.1f}s")
    print(f"  {'=' * 50}")
    print(f"  总计:          {stats['total']}")
    print(f"  Good:          {stats['good']}")
    print(f"  Fair:          {stats['fair']}")
    print(f"  Poor (跳过):   {stats['poor']}")
    print(f"  可用 (YOLO):   {stats['usable']}")
    print(f"  {'=' * 50}")
    print(f"  输出目录: {OUTPUT_DIR}/")
    print(f"    images/  — {stats['total']} 张 RDN 增强图（640×640）")
    print(f"    labels/  — YOLO 格式标注")
    print(f"    quality_report.csv — 每张图的质量评分")
    print(f"    dataset.yaml — YOLO 训练配置")
    print(f"  {'=' * 50}")

    # 警告
    poor_ratio = stats["poor"] / max(stats["total"], 1)
    if poor_ratio > 0.3:
        print(f"  注意：{poor_ratio:.0%} 的图像质量评级为 poor，")
        print(f"      建议检查 RDN 输出或调整质量阈值。")
    print("=" * 60)


if __name__ == "__main__":
    main()
