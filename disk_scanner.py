import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

def get_dir_size(path):
    total = 0
    try:
        for entry in os.scandir(path):
            if entry.is_file(follow_symlinks=False):
                total += entry.stat(follow_symlinks=False).st_size
            elif entry.is_dir(follow_symlinks=False):
                total += get_dir_size(entry.path)
    except Exception:
        pass
    return total

def scan_top_dirs(base_path, min_gb=1.0):
    if not os.path.exists(base_path):
        return
    print(f"\nScanning large folders in {base_path} (limit > {min_gb} GB)...")
    target_dirs = []
    try:
        for entry in os.scandir(base_path):
            if entry.is_dir(follow_symlinks=False):
                target_dirs.append(entry.path)
    except Exception:
        pass
    
    res = []
    with ThreadPoolExecutor(max_workers=16) as executor:
        sizes = list(executor.map(get_dir_size, target_dirs))
        
    for d, s in zip(target_dirs, sizes):
        size_gb = s / (1024 ** 3)
        if size_gb >= min_gb:
            res.append((d, size_gb))
            
    res.sort(key=lambda x: x[1], reverse=True)
    for d, s_gb in res:
        print(f"  {d}: {s_gb:.2f} GB")

if __name__ == "__main__":
    t0 = time.time()
    scan_top_dirs(r'C:\Users\HP')
    scan_top_dirs(r'C:\Users\HP\AppData\Local')
    scan_top_dirs(r'C:\Users\HP\AppData\Roaming')
    scan_top_dirs(r'C:\Users\HP\Documents')
    print(f"\nDone in {time.time()-t0:.1f} seconds.")
