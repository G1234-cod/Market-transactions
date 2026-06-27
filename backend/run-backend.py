"""
一键启动后端：启动 Qdrant → 索引数据 → 启动服务 → 打开浏览器

用法:
    python run-backend.py                   # 默认：启动 Qdrant + 索引 + 启动服务
    python run-backend.py --skip-qdrant     # 跳过 Qdrant
    python run-backend.py --skip-index      # 跳过索引
    python run-backend.py --no-browser      # 不自动打开浏览器
"""
import os
import subprocess
import time
import webbrowser
import argparse
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

os.chdir(SCRIPT_DIR)


def step(msg):
    print(f"\n{'='*50}")
    print(f"  {msg}")
    print(f"{'='*50}")


def ok(msg):
    print(f"  [OK] {msg}")


def fail(msg):
    print(f"  [FAIL] {msg}")


def run(cmd, timeout=120):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, cwd=SCRIPT_DIR)
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return -1, "timeout"
    except Exception as e:
        return -1, str(e)


# ============================================================
def start_qdrant():
    step("启动 Qdrant 向量数据库")

    # Docker 可用？
    code, _ = run("docker --version")
    if code != 0:
        fail("Docker 未安装或未启动，跳过")
        return False

    # 已经在运行？
    try:
        urllib.request.urlopen(urllib.request.Request("http://localhost:6333/healthz"), timeout=3)
        ok("Qdrant 已在运行")
        return True
    except Exception:
        pass

    # 启动
    data_dir = PROJECT_DIR / "backend" / "data" / "qdrant"
    data_dir.mkdir(parents=True, exist_ok=True)

    code, out = run(f'docker run -d -p 6333:6333 -v "{data_dir}":/qdrant/storage qdrant/qdrant:latest')
    if code != 0:
        fail(f"启动失败: {out[:200]}")
        return False

    # 等待就绪
    for i in range(15):
        time.sleep(2)
        try:
            urllib.request.urlopen(urllib.request.Request("http://localhost:6333/healthz"), timeout=3)
            ok("Qdrant 就绪")
            return True
        except Exception:
            print(f"  等待... ({i+1}/15)")

    fail("Qdrant 启动超时")
    return False


# ============================================================
def index_items():
    step("以图搜图索引")
    code, out = run("python scripts/index_items.py --all")
    if code == 0:
        ok("索引完成")
    else:
        print(f"  {out[:300]}") if out else None


# ============================================================
def start_server(open_browser=True):
    step("启动后端服务")
    print(f"  后端:    http://localhost:8000")
    print(f"  文档:    http://localhost:8000/docs")
    print(f"  Ctrl+C  停止\n{'='*50}\n")

    if open_browser:
        time.sleep(2)
        webbrowser.open("http://localhost:8000/docs")

    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


# ============================================================
def main():
    parser = argparse.ArgumentParser(description="一键启动后端")
    parser.add_argument("--skip-qdrant", action="store_true")
    parser.add_argument("--skip-index", action="store_true")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    print("\n  智能二手商品发布助手 - 后端启动\n")

    qdrant_ok = True
    if not args.skip_qdrant:
        qdrant_ok = start_qdrant()

    if qdrant_ok and not args.skip_index:
        index_items()

    start_server(open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
