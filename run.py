"""
一键启动整个项目：后端（Qdrant + 索引 + FastAPI） + 前端（Vite）

双击或在终端运行:
    python run.py
    python run.py --skip-qdrant
    python run.py --no-browser
"""
import subprocess
import sys
import time
import webbrowser
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"


def main():
    parser = argparse.ArgumentParser(description="一键启动全栈项目")
    parser.add_argument("--skip-qdrant", action="store_true")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    print("""
  ╔══════════════════════════════════════════╗
  ║   智能二手商品发布助手 - 一键启动       ║
  ╚══════════════════════════════════════════╝
    """)

    qdrant_flag = "--skip-qdrant" if args.skip_qdrant else ""
    browser_flag = "--no-browser" if args.no_browser else ""

    # 启动后端
    print("[后端] 启动中...")
    backend_cmd = [sys.executable, str(BACKEND / "run-backend.py")]
    if args.skip_qdrant:
        backend_cmd.append("--skip-qdrant")
    if args.no_browser:
        backend_cmd.append("--no-browser")

    backend_proc = subprocess.Popen(
        backend_cmd,
        cwd=str(BACKEND),
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    # 等后端先启动
    print("[后端] 等待就绪...")
    time.sleep(4)

    # 启动前端
    print("[前端] 启动中...")
    frontend_cmd = [sys.executable, str(FRONTEND / "run-frontend.py")]
    if args.no_browser:
        frontend_cmd.append("--no-browser")

    frontend_proc = subprocess.Popen(
        frontend_cmd,
        cwd=str(FRONTEND),
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    print(f"""
  ╔══════════════════════════════════════════╗
  ║  后端:  http://localhost:8000           ║
  ║  文档:  http://localhost:8000/docs      ║
  ║  前端:  http://localhost:5173           ║
  ║  Ctrl+C 停止所有服务                    ║
  ╚══════════════════════════════════════════╝
    """)

    try:
        backend_proc.wait()
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("\n  正在停止...")
        backend_proc.terminate()
        frontend_proc.terminate()
        backend_proc.wait()
        frontend_proc.wait()
        print("  已停止")


if __name__ == "__main__":
    main()