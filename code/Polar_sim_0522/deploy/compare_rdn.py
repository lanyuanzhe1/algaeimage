"""Compare RDN raw float outputs (skip joint-norm) vs clean target.
Matches training L1 metric exactly."""
import os, sys, time, random
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
sys.path.insert(0, '/data/lifewatch_hsv/code')
import numpy as np
from pathlib import Path
import torch
from hsv_polarization import hsv_to_polarization
from ml.reconstructor import RDN, PolarizationReconstructor

IMAGE_DIR = Path('/data/lifewatch_hsv/images')
NEW_RDN_WT = '/data/lifewatch_hsv/rdn_training/rdn_hsv_lifewatch.pth'
OLD_RDN_WT = '/data/lifewatch_hsv/rdn_training/rdn_old_fmpd.pth'
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
N = 200

# Get val stems
val_stems = set()
with open('/data/lifewatch_hsv/splits/val.txt') as f:
    for line in f:
        p = line.strip().rsplit(' ', 1)
        if len(p) == 2:
            val_stems.add(p[0].replace('\\', '/').split('/')[-1].rsplit('.', 1)[0])

all_imgs = {}
for img_path in IMAGE_DIR.rglob('*.jpg'):
    if img_path.stem in val_stems:
        all_imgs[img_path.stem] = img_path
sample = random.sample(list(all_imgs.values()), min(N, len(all_imgs)))
print(f'Comparing on {len(sample)} val images | Device: {DEVICE}')

# Load models directly as RDN (skip PolarizationReconstructor joint-norm)
def load_rdn(weights_path):
    model = RDN(num_channels=4, num_features=16, growth_rate=16,
                num_blocks=12, num_layers=6).to(DEVICE)
    sd = torch.load(weights_path, map_location=DEVICE, weights_only=True)
    model_keys = set(model.state_dict().keys())
    sd = {k: v for k, v in sd.items() if k in model_keys}
    model.load_state_dict(sd, strict=False)
    model.eval()
    return model

new_model = load_rdn(NEW_RDN_WT)
old_model = load_rdn(OLD_RDN_WT)
print('Both models loaded')

import cv2
t0 = time.time()
raw_losses, new_losses, old_losses = [], [], []

for img_path in sample:
    rgb = cv2.cvtColor(cv2.imread(str(img_path)), cv2.COLOR_BGR2RGB)

    # Clean target (no noise, per-channel normalized)
    sim_c = hsv_to_polarization(rgb, polarization_strength=1.0, add_noise=False)
    I_c = torch.from_numpy(np.stack(
        [sim_c[k].astype(np.float32)/255.0 for k in ['I0','I45','I90','I135']], axis=0
    )).unsqueeze(0).to(DEVICE)

    # Noisy input
    sim_n = hsv_to_polarization(rgb, polarization_strength=1.0, add_noise=True, noise_level=0.02)
    I_n_raw = np.stack([sim_n[k].astype(np.float32)/255.0 for k in ['I0','I45','I90','I135']], axis=0)
    I_n = torch.from_numpy(I_n_raw).unsqueeze(0).to(DEVICE)

    # Raw noisy vs clean (L1 on raw float)
    raw_losses.append(torch.mean(torch.abs(I_n - I_c)).item())

    # New RDN raw output
    with torch.no_grad():
        out_new = new_model(I_n)
    new_losses.append(torch.mean(torch.abs(out_new - I_c)).item())

    # Old RDN raw output
    with torch.no_grad():
        out_old = old_model(I_n)
    old_losses.append(torch.mean(torch.abs(out_old - I_c)).item())

print(f'\n{"="*55}')
print(f'  RDN Comparison (RAW float32 output, no joint-norm)')
print(f'  on {len(sample)} LifeWatch HSV val images')
print(f'{"="*55}')
print(f'  Noisy input (no RDN):      L1={np.mean(raw_losses):.6f}')
print(f'  Old RDN (FMPD struct):     L1={np.mean(old_losses):.6f}')
print(f'  New RDN (LifeWatch HSV):   L1={np.mean(new_losses):.6f}')
dn = (1-np.mean(new_losses)/np.mean(raw_losses))*100
do = (1-np.mean(old_losses)/np.mean(raw_losses))*100
print(f'  New RDN noise reduction:   {dn:.1f}%')
print(f'  Old RDN noise reduction:   {do:.1f}%')
print(f'  New vs Old: new L1 is {np.mean(new_losses)/np.mean(old_losses):.3f}x of old')
print(f'  Time: {(time.time()-t0):.0f}s')
