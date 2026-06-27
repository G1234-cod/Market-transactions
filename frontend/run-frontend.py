"""
一键启动前端：启动开发服务器 → 打开浏览器

用法:
    python run-frontend.py
    python run-frontend.py --no-browser
"""
import os
import subprocess
import webbrowser
import argparse
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
os.chdir(SCRIPT_DIR)


def main():
    parser = argparse.ArgumentParser(description="一键启动前端")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    print("\n  智能二手商品发布助手 - 前端启动\n")
    print(f"  前端:    http://localhost:5173")
    print(f"  Ctrl+C  停止\n")

    if not args.no_browser:
        webbrowser.open("http://localhost:5173")

    subprocess.run("npm run dev", shell=True, cwd=SCRIPT_DIR)


if __name__ == "__main__":
    main()
