import os
import cv2
import glob
from pathlib import Path

def convert_to_grayscale(input_dir, output_dir):
    """
    将指定目录下的彩色图片转换为黑白（灰度）图，并保存在新建的平级目录中。
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    # 确保输出目录存在
    output_path.mkdir(parents=True, exist_ok=True)

    # 支持的图片格式
    extensions = ['*.tif', '*.tiff', '*.png', '*.jpg', '*.jpeg']
    
    image_files = []
    for ext in extensions:
        image_files.extend(input_path.glob(ext))
        image_files.extend(input_path.glob(ext.upper()))

    if not image_files:
        print(f"在 {input_dir} 下没有找到图片文件。")
        return

    print(f"找到 {len(image_files)} 张图片，开始转换...")
    
    count = 0
    for img_path in image_files:
        # 读取图像
        img = cv2.imread(str(img_path))
        if img is not None:
            # 转换为灰度图 (黑白)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # 构造输出路径
            out_path = output_path / img_path.name
            # 保存
            cv2.imwrite(str(out_path), gray)
            count += 1
            if count % 50 == 0:
                print(f"已处理 {count} 张图片...")
        else:
            print(f"无法读取图片: {img_path}")

    print(f"转换完成！共成功转换 {count} 张图片。")
    print(f"图片保存在: {output_path}")

if __name__ == "__main__":
    # 输入路径
    IN_DIR = r"e:\code\algaeimage\code\algae_guardian\data\fmpd_download\extracted\dataset\dataset"
    # 输出路径（同级目录下的 dataset_bw）
    OUT_DIR = r"e:\code\algaeimage\code\algae_guardian\data\fmpd_download\extracted\dataset\dataset_bw"
    
    convert_to_grayscale(IN_DIR, OUT_DIR)
