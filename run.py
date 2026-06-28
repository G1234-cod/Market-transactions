"""
一键启动前后端

用法:
    python run.py
"""
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def kill_port(port):
    """杀掉占用端口的旧进程"""
    try:
        r = subprocess.run(f'netstat -ano | findstr ":{port}"', shell=True,
                           capture_output=True, text=True)
        pids = {line.strip().split()[-1] for line in r.stdout.split('\n')
                if 'LISTENING' in line and len(line.strip().split()) >= 5}
        for pid in pids:
            subprocess.run(f'taskkill /F /PID {pid} >nul 2>&1', shell=True)
        if pids:
            print(f"  已清理端口 {port}")
    except Exception:
        pass


def main():
    print("""
  ╔══════════════════════════════════════════╗
  ║   智能二手商品发布助手 - 一键启动       ║
  ╚══════════════════════════════════════════╝
    """)

    kill_port(8000)
    kill_port(5173)

    # --- 后端 ---
    print("[1/2] 启动后端...")
    subprocess.Popen(
        [sys.executable, "run-backend.py", "--skip-qdrant", "--skip-index", "--no-browser"],
        cwd=str(ROOT / "backend"),
    )
    time.sleep(4)
    print("      后端: http://localhost:8000")

    # --- 前端 ---
    print("[2/2] 启动前端...")
    subprocess.Popen(
        [sys.executable, "run-frontend.py", "--no-browser"],
        cwd=str(ROOT / "frontend"),
    )
    time.sleep(4)
    print("      前端: http://localhost:5173")

    # --- 弹浏览器 ---
    webbrowser.open("http://localhost:8000/docs")
    time.sleep(0.5)
    webbrowser.open("http://localhost:5173")

    print("""
  ╔══════════════════════════════════════════╗
  ║  Ctrl+C 停止                             ║
  ╚══════════════════════════════════════════╝
    """)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n  已停止")


if __name__ == "__main__":
    main()
