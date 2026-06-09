import paramiko
import pandas as pd
import io

HOST = "xkh2l3rq6jm4cpuhunt.funhpc.com"
PORT = 30769
USER = "root"
PASSWORD = "wEoOG5Y791pBAT5CmRvyre2yI8Sgr1hv"

def check_training():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print(f"🔄 正在连接到服务器 {HOST}:{PORT}...")
    try:
        client.connect(hostname=HOST, port=PORT, username=USER, password=PASSWORD, timeout=15)
        print("✅ 连接成功！\n")
        
        # 1. 检查 Python 进程
        stdin, stdout, stderr = client.exec_command("ps aux | grep train_yolo_v2.py | grep -v grep")
        ps_output = stdout.read().decode("utf-8").strip()
        if ps_output:
            print("▶️ [训练状态] 正在运行 (Alive):")
            for line in ps_output.split("\n")[:2]:
                print(f"   {line}")
        else:
            print("⏹️ [训练状态] 未发现正在运行的训练进程 (Dead/Stopped)。")
            
        print("-" * 50)
        
        # 2. 获取 results.csv 数据以查看训练指标
        csv_path = "/data/lifewatch_hsv/yolo_results/v8l_hsv_stable/results.csv"
        stdin, stdout, stderr = client.exec_command(f"cat {csv_path} 2>/dev/null || echo 'FILE_NOT_FOUND'")
        csv_text = stdout.read().decode("utf-8").strip()
        
        if csv_text == "FILE_NOT_FOUND" or not csv_text:
            print("⚠️ 未找到 results.csv，或者文件为空。")
        else:
            print(f"📊 [指标监测] 当前 CSV: {csv_path}")
            # 用 pandas 解析
            df = pd.read_csv(io.StringIO(csv_text))
            df.columns = df.columns.str.strip()  # 清理列名空格
            
            # 打印最近 5 个 epoch 的各项关键数据
            latest = df.tail(5)
            cols = [
                'epoch', 
                'train/box_loss', 'val/box_loss', 
                'train/cls_loss', 'val/cls_loss', 
                'metrics/precision(B)', 'metrics/recall(B)', 
                'metrics/mAP50(B)', 'metrics/mAP50-95(B)'
            ]
            avail_cols = [c for c in cols if c in df.columns]
            print("\n📈 最近 5 个 Epoch 的全面指标:")
            print(" [指标说明]")
            print("  - box_loss: 目标框位置回归损失，评估框的准确度 (越低越好)")
            print("  - cls_loss: 分类识别损失，评估认错类别的概率 (越低越好)")
            print("  - precision: 精确率，模型标出的框里，标对的占比 (越高越好)")
            print("  - recall: 召回率，所有真实的藻类中，被模型找出来的占比 (越高越好)")
            print("  - mAP50: IoU=0.5 时的平均精度，本项目最核心的关键指标 (越高越好)")
            print("  - mAP50-95: 更加苛刻的高维度平均精度，衡量框贴合的完美程度\n")
            
            print(latest[avail_cols].to_string(index=False, float_format=lambda x: f"{x:.4f}"))
            
            # 最高 mAP
            best_map = df['metrics/mAP50(B)'].max()
            best_epoch = df.loc[df['metrics/mAP50(B)'].idxmax(), 'epoch']
            print("\n🏆 历史最高 mAP50:", f"{best_map*100:.2f}% (Epoch {int(best_epoch)})")
            
        print("-" * 50)
        
        # 3. 抓取日志最新情况
        log_path = "/data/lifewatch_hsv/yolo_results/train_stable.log"
        stdin, stdout, stderr = client.exec_command(f"tail -n 10 {log_path} 2>/dev/null || echo 'LOG_NOT_FOUND'")
        log_text = stdout.read().decode("utf-8").strip()
        
        print("📝 [日志追踪] 最新日志输出:")
        if log_text == "LOG_NOT_FOUND":
            print("⚠️ 未找到日志文件。")
        else:
            for line in log_text.split('\n'):
                print(f"   {line}")

    except Exception as e:
        print(f"❌ 发生错误: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    check_training()
