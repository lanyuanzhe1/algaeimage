"""Check image dimensions and class distribution for Lifewatch dataset."""
import cv2
import os
import glob
import sys

base = "/data/datasets/lifewatch/images_all"

# Check sample images from different classes
class_dirs = sorted(os.listdir(base))[:10]
for cls in class_dirs:
    d = os.path.join(base, cls)
    imgs = glob.glob(os.path.join(d, "*.jpg"))[:3]
    sizes = set()
    for p in imgs:
        img = cv2.imread(p)
        if img is not None:
            sizes.add(f"{img.shape[1]}x{img.shape[0]}")
    n = len(os.listdir(d))
    print(f"  {cls}: {n} images, sizes: {sizes}")

total = sum(len(os.listdir(os.path.join(base, d))) for d in os.listdir(base))
print(f"\nTotal images: {total}")
print(f"Total classes: {len(os.listdir(base))}")
