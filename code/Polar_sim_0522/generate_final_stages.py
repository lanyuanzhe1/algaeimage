import os, sys, time, glob
from pathlib import Path
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import warnings
warnings.filterwarnings('ignore')

# Paths
LOCAL_DIR = r"e:\code\algaeimage\code\Polar_sim_0522"
sys.path.insert(0, LOCAL_DIR)
# Also add algae_guardian for fallback modules if needed
sys.path.insert(0, r"e:\code\algaeimage\code\algae_guardian")

import numpy as np
import cv2
import torch
from hsv_polarization import hsv_to_polarization
from image_processing.polarization import PolarizationProcessor
from image_processing.enhancement import ImageEnhancer
from ml.reconstructor import RDN
from ultralytics import YOLO

ALPHA, BETA, GAMMA = 0.6, 0.25, 0.35
POL_STRENGTH, NOISE_LEVEL = 1.0, 0.02
OUTPUT_SIZE = 320
PATCH_SIZE = 128

def _norm_u8(x):
    x = x.astype(np.float32)
    d = x.max() - x.min()
    return np.zeros_like(x, dtype=np.uint8) if d < 1e-10 else ((x - x.min()) / d * 255).astype(np.uint8)

def pad_to_square_numpy(ch, target):
    c, h, w = ch.shape
    if max(h, w) > target:
        scale = target / max(h, w)
        h, w = int(h * scale), int(w * scale)
        ch_resized = []
        for i in range(c):
            ch_resized.append(cv2.resize(ch[i], (w, h), interpolation=cv2.INTER_LINEAR))
        ch = np.array(ch_resized)
    else:
        h, w = ch.shape[1], ch.shape[2]
    out = np.zeros((c, target, target), dtype=ch.dtype)
    out[:, :h, :w] = ch
    return out, h, w

def process_4_channels(channels, oh, ow, pp, enhancer):
    I0 = channels[0]
    I45 = channels[1]
    I90 = channels[2]
    I135 = channels[3]

    S0 = I0 + I90
    S1 = I0 - I90
    S2 = I45 - I135
    DoLP = np.clip(np.sqrt(S1**2+S2**2)/(S0+1e-10), 0, 1)
    AoP = 0.5 * np.arctan2(S2, S1)

    S0_ch = _norm_u8(S0)
    enh_ch = pp.polarization_enhancement_v2(S0, DoLP, AoP, alpha=ALPHA, beta=BETA, gamma=GAMMA)
    corrected_raw = S0 * (1.0 - 0.5 * DoLP.astype(np.float32))
    cor_ch = _norm_u8(corrected_raw)

    h, w = S0_ch.shape[:2]
    s = OUTPUT_SIZE / max(h, w)
    nh, nw = int(h*s), int(w*s)
    S0_lb = np.zeros((OUTPUT_SIZE, OUTPUT_SIZE), dtype=np.uint8)
    enh_lb = np.zeros((OUTPUT_SIZE, OUTPUT_SIZE), dtype=np.uint8)
    cor_lb = np.zeros((OUTPUT_SIZE, OUTPUT_SIZE), dtype=np.uint8)
    S0_lb[:nh,:nw] = cv2.resize(S0_ch, (nw,nh), interpolation=cv2.INTER_LINEAR)
    enh_lb[:nh,:nw] = cv2.resize(enh_ch, (nw,nh), interpolation=cv2.INTER_LINEAR)
    cor_lb[:nh,:nw] = cv2.resize(cor_ch, (nw,nh), interpolation=cv2.INTER_LINEAR)

    stacked = np.stack([S0_lb, enh_lb, cor_lb], axis=-1)
    final = enhancer.enhance(stacked, color_correct=True, clahe=True, dehaze=False)
    return final

def main():
    img_dir = r"e:\code\algaeimage\lifewatch_raw_samples\test_500\img500"
    out_dir = r"e:\code\algaeimage\code\Polar_sim_0522\data\final_samples_500"
    rdn_model_path = r"e:\code\algaeimage\code\algae_guardian\ml\models\rdn_polarization.pth"
    yolo_model_path = r"e:\code\algaeimage\code\Polar_sim_0522\output\hsv_training_artifacts_20260524\v8l_hsv_stable\weights\best.pt"
    
    os.makedirs(out_dir, exist_ok=True)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    
    # Load RDN
    model = RDN(num_channels=4, num_features=16, growth_rate=16, num_blocks=12, num_layers=6).to(device)
    sd = torch.load(rdn_model_path, map_location=device, weights_only=True)
    model.load_state_dict({k:v for k,v in sd.items() if k in model.state_dict().keys()}, strict=False)
    model.eval()
    print("RDN Loaded.")
    
    # Load YOLO
    yolo_model = YOLO(yolo_model_path)
    print("YOLO Loaded.")
    
    pp = PolarizationProcessor()
    enhancer = ImageEnhancer()
    
    img_paths = glob.glob(os.path.join(img_dir, "*.jpg"))
    if not img_paths:
        print("No images found in", img_dir)
        return
        
    print(f"Processing {len(img_paths)} images...")
    
    for idx, path in enumerate(img_paths):
        fname = os.path.basename(path)
        img = cv2.imread(path)
        if img is None: continue
        
        # 1. Raw
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Resize raw to 320x320 for display
        raw_disp = np.zeros((OUTPUT_SIZE, OUTPUT_SIZE, 3), dtype=np.uint8)
        c, h, w = img.shape[2], img.shape[0], img.shape[1]
        s = OUTPUT_SIZE / max(h, w)
        nh, nw = int(h*s), int(w*s)
        raw_resized = cv2.resize(img, (nw, nh))
        raw_disp[:nh, :nw, :] = raw_resized
        
        # 2. HSV Sim
        sim = hsv_to_polarization(rgb, polarization_strength=POL_STRENGTH, add_noise=True, noise_level=NOISE_LEVEL)
        ch_raw = np.stack([sim[k].astype(np.float32)/255.0 for k in ['I0','I45','I90','I135']], axis=0)
        
        # padding for RDN input
        ch_pad, orig_h, orig_w = pad_to_square_numpy(ch_raw, PATCH_SIZE)
        
        # Process NO RDN (Stage 1) -> using un-reconstructed channels
        stage1_hsv = process_4_channels(ch_pad[:, :orig_h, :orig_w], orig_h, orig_w, pp, enhancer)
        
        # Process WITH RDN (Stage 2)
        batch = torch.from_numpy(np.expand_dims(ch_pad, axis=0)).to(device)
        with torch.no_grad():
            rdn_out = model(batch).cpu().numpy()[0]
        
        stage2_rdn = process_4_channels(rdn_out[:, :orig_h, :orig_w], orig_h, orig_w, pp, enhancer)
        
        # Process YOLO (Stage 3)
        results = yolo_model.predict(stage2_rdn, verbose=False)
        stage3_yolo = results[0].plot() # numpy array with BGR image
        
        # Concatenate sid-by-side
        # Raw | HSV模拟后 | RDN处理后 | YOLO输出
        # Add labels on top of each
        def add_label(image, text):
            # Put black rect at top
            res = image.copy()
            cv2.rectangle(res, (0, 0), (OUTPUT_SIZE, 30), (0,0,0), -1)
            cv2.putText(res, text, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1, cv2.LINE_AA)
            return res
            
        l_raw = add_label(raw_disp, "1. Raw RGB")
        l_hsv = add_label(stage1_hsv, "2. HSV Sim")
        l_rdn = add_label(stage2_rdn, "3. RDN Output")
        l_yolo = add_label(stage3_yolo, "4. YOLO Pred")
        
        collage = np.hstack([l_raw, l_hsv, l_rdn, l_yolo])
        
        out_path = os.path.join(out_dir, fname)
        cv2.imwrite(out_path, collage)
        
        if (idx+1) % 50 == 0:
            print(f"Processed {idx+1}/{len(img_paths)}")

    print(f"Done! Saved 500 collages to {out_dir}")

if __name__ == "__main__":
    main()
