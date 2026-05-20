"""Quick-start script: init DB, download YOLO model, start server."""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.app.database import init_db
from ml.inference import AlgaeDetector
from backend.app.config import HOST, PORT


def main():
    print("=" * 50)
    print("  藻影卫士 · Algae Guardian")
    print("  初始化系统...")
    print("=" * 50)

    # 1. Init database
    print("\n[1/3] 初始化数据库...")
    tables = init_db()
    print(f"      ✓ 数据库表: {tables}")

    # 2. Download YOLO model
    print("\n[2/3] 准备 YOLO 模型...")
    detector = AlgaeDetector()
    if detector.load_model():
        info = detector.get_model_info()
        print(f"      ✓ 模型加载完成: {info.get('class_names', 'N/A')}")
    else:
        print("      ⚠ 模型加载失败，将使用占位模型")

    # 3. Instructions
    print("\n[3/3] 启动服务器")
    print(f"\n  ✓ 初始化完成!")
    print(f"\n  启动命令:")
    print(f"    python -m uvicorn backend.app.main:app --host {HOST} --port {PORT} --reload")
    print(f"\n  访问地址:")
    print(f"    API 文档:  http://{HOST}:{PORT}/docs")
    print(f"    监控面板:  http://{HOST}:{PORT}/static/index.html")
    print(f"    健康检查:  http://{HOST}:{PORT}/health")
    print(f"\n  {'=' * 50}")


if __name__ == "__main__":
    main()
