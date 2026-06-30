"""
一键启动前端：启动 Vite 开发服务器 → 打开浏览器
"""
import subprocess
import webbrowser
import time
import urllib.request
import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
URL = "http://localhost:5173"


def is_http_ready(url, timeout=2.0):
    """用 HTTP 请求检测是否就绪"""
    try:
        req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.status == 200
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="一键启动前端")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    print(f"\n[前端] 启动 Vite 开发服务器...")
    print(f"[前端] 地址: {URL}")

    proc = subprocess.Popen(
        "npm run dev",
        shell=True,
        cwd=str(SCRIPT_DIR),
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    # 等待 Vite HTTP 就绪（最多 30 秒）
    print(f"[前端] 等待就绪", end="", flush=True)
    for _ in range(30):
        if is_http_ready(URL):
            print(" ✓")
            break
        time.sleep(1)
        if proc.poll() is not None:
            print(f"\n[前端] Vite 进程意外退出 (code={proc.returncode})")
            return
        print(".", end="", flush=True)
    else:
        print(f"\n[前端] 超时，直接打开浏览器...")

    if not args.no_browser:
        webbrowser.open(URL)
        print(f"[前端] 浏览器已打开: {URL}")

    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\n[前端] 已停止")


if __name__ == "__main__":
    main()
