# Utility Scripts

云端训练管理及辅助工具脚本，非产品代码。

| 脚本 | 用途 |
|------|------|
| `check_yolo_training.py` | SSH 连接云 GPU 服务器，监控 YOLO 训练状态（epoch/mAP/GPU） |
| `convert_to_docx.py` | 将 `defense_qa_comprehensive.md` 转换为格式化 Word 文档 |
| `disk_scanner.py` | 并发扫描目录磁盘占用，识别大文件/目录 |
| `download_previews.py` | 从云服务器下载训练预览图（results.png, batch samples） |
| `download_results_20260522.py` | 批量递归下载训练结果目录 |
| `plot_metrics.py` | 从 results.csv 生成 mAP/loss 训练曲线图 |
| `tmp_download_500.py` | 随机选取 500 张 LifeWatch 样本并从云服务器打包下载 |
