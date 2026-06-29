"""
一键启动前端：启动 Vite 开发服务器 → 打开浏览器
"""
import subprocess
import webbrowser
import time
import socket
import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
HOST = "localhost"
PORT = 5173


def is_ready(host, port, timeout=1.0):
    """用 socket 检测端口是否在监听"""
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True
    except (ConnectionRefusedError, OSError, socket.timeout):
        return False


def main():
    parser = argparse.ArgumentParser(description="一键启动前端")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    print(f"\n[前端] 启动 Vite 开发服务器...")
    print(f"[前端] 地址: http://{HOST}:{PORT}")

    # 启动 Vite
    proc = subprocess.Popen(
        "npm run dev",
        shell=True,
        cwd=str(SCRIPT_DIR),
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    # 等待就绪
    print(f"[前端] 等待就绪", end="", flush=True)
    for _ in range(30):
        if is_ready(HOST, PORT):
            print(" ✓")
            break
        time.sleep(1)
        print(".", end="", flush=True)
    else:
        print(f"\n[前端] 等不及了，直接打开浏览器...")

    if not args.no_browser:
        webbrowser.open(f"http://{HOST}:{PORT}")
        print(f"[前端] 浏览器已打开: http://{HOST}:{PORT}")

    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\n[前端] 已停止")


if __name__ == "__main__":
    main()
