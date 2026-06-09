import pandas as pd
import matplotlib.pyplot as plt
import os

# 读取 CSV
csv_path = r"e:\code\codex\pic\yolo_intermediate\results.csv"
output_path = r"e:\code\codex\pic\yolo_intermediate\training_curves.png"

df = pd.read_csv(csv_path)

# 清理列名（YOLO生成的CSV列名常带有空格）
df.columns = [col.strip() for col in df.columns]

epochs = df['epoch']

plt.figure(figsize=(15, 8))

# 1. 损失函数曲线 (Box)
plt.subplot(2, 2, 1)
plt.plot(epochs, df['train/box_loss'], label='Train Box Loss', color='blue')
plt.plot(epochs, df['val/box_loss'], label='Val Box Loss', color='orange')
plt.title('Box Loss')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.6)

# 2. 损失函数曲线 (Cls)
plt.subplot(2, 2, 2)
plt.plot(epochs, df['train/cls_loss'], label='Train Cls Loss', color='blue')
plt.plot(epochs, df['val/cls_loss'], label='Val Cls Loss', color='orange')
plt.title('Classification Loss')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.6)

# 3. 精度曲线 (mAP)
plt.subplot(2, 2, 3)
plt.plot(epochs, df['metrics/mAP50(B)'], label='mAP50', color='green')
plt.plot(epochs, df['metrics/mAP50-95(B)'], label='mAP50-95', color='purple')
plt.title('Mean Average Precision (mAP)')
plt.xlabel('Epoch')
plt.ylabel('mAP')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.6)

# 4. Precision & Recall 
plt.subplot(2, 2, 4)
plt.plot(epochs, df['metrics/precision(B)'], label='Precision', color='red')
plt.plot(epochs, df['metrics/recall(B)'], label='Recall', color='brown')
plt.title('Precision & Recall')
plt.xlabel('Epoch')
plt.ylabel('Score')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.6)

plt.tight_layout()
plt.savefig(output_path, dpi=150)
print(f"Plot saved to {output_path}")

# 输出最新的一些关键数据
last_row = df.iloc[-1]
print("\n--- 最新一轮 (Epoch {}) 的关键指标 ---".format(int(last_row['epoch'])))
print("Train Box Loss:", last_row['train/box_loss'])
print("Train Cls Loss:", last_row['train/cls_loss'])
print("Val Box Loss:", last_row['val/box_loss'])
print("Val Cls Loss:", last_row['val/cls_loss'])
print("mAP50:", last_row['metrics/mAP50(B)'])
print("mAP50-95:", last_row['metrics/mAP50-95(B)'])
print("Precision:", last_row['metrics/precision(B)'])
print("Recall:", last_row['metrics/recall(B)'])
