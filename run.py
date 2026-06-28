"""
一键启动整个项目：先启动后端（后台），后端就绪后启动前端（弹窗）

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
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"

BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"


def is_backend_ready(url: str, timeout: float = 2.0) -> bool:
    """检查后端是否就绪"""
    try:
        req = urllib.request.Request(f"{url}/health")
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.status == 200
    except Exception:
        return False


def wait_for_backend(url: str, max_wait: int = 60) -> bool:
    """轮询等待后端就绪，最多等 max_wait 秒"""
    print(f"[后端] 等待就绪", end="", flush=True)
    for i in range(max_wait):
        if is_backend_ready(url):
            print(" ✅")
            return True
        print(".", end="", flush=True)
        time.sleep(1)
    print(" ❌ 超时")
    return False


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

    # ============================================================
    # 第一步：启动后端（后台，不弹页面）
    # ============================================================
    print("[后端] 启动中（后台运行，不弹窗口）...")
    backend_cmd = [
        sys.executable, str(BACKEND / "run-backend.py"),
        "--no-browser",   # 后端永远不弹页面
    ]
    if args.skip_qdrant:
        backend_cmd.append("--skip-qdrant")

    backend_proc = subprocess.Popen(
        backend_cmd,
        cwd=str(BACKEND),
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    # ============================================================
    # 第二步：轮询等待后端就绪
    # ============================================================
    if not wait_for_backend(BACKEND_URL, max_wait=60):
        print("\n[错误] 后端启动失败，终止")
        backend_proc.terminate()
        sys.exit(1)

    # ============================================================
    # 第三步：后端就绪后，启动前端
    # ============================================================
    print("[前端] 启动中...")
    frontend_cmd = [
        sys.executable, str(FRONTEND / "run-frontend.py"),
    ]
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
  ║  ✅ 全部就绪                            ║
  ║  后端:  {BACKEND_URL}                  ║
  ║  文档:  {BACKEND_URL}/docs             ║
  ║  前端:  {FRONTEND_URL}                  ║
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
