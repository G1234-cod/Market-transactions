import subprocess
import sys
import os

def has_nvidia_gpu():
    """检测本机是否存在 Nvidia GPU 并已安装驱动"""
    try:
        subprocess.check_output(['nvidia-smi'], stderr=subprocess.STDOUT)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def clear_proxy_env():
    """清除代理环境变量（如果有）"""
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy']
    for var in proxy_vars:
        if var in os.environ:
            print(f"⚠️ 检测到代理环境变量: {var}={os.environ[var]}")
            del os.environ[var]
            print(f"✅ 已清除 {var}")

def install_dependencies():
    print("="*50)
    print("🚀 开始配置项目环境...")
    print("="*50)
    
    # 清除代理
    clear_proxy_env()
    
    # 1. 安装基础通用依赖
    print("\n[1/2] 正在安装通用依赖 (requirements.txt)...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ 通用依赖安装完成")
    except subprocess.CalledProcessError as e:
        print(f"❌ 通用依赖安装失败: {e}")
        print("尝试使用 --ignore-dependencies 重新安装...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "-r", "requirements.txt",
                "--ignore-dependencies"
            ])
            print("✅ 通用依赖安装完成（忽略依赖冲突）")
        except subprocess.CalledProcessError:
            print("❌ 通用依赖安装失败，请检查网络或 requirements.txt 文件。")
            sys.exit(1)

    # 2. 检测硬件并安装特定的 torch 和 torchvision
    print("\n[2/2] 正在检测本地硬件环境...")
    if has_nvidia_gpu():
        print("✅ 检测到 NVIDIA GPU！准备安装 GPU 版本 PyTorch (CUDA 12.1)...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install",
                "torch==2.2.2+cu121", "torchvision==0.17.2+cu121",
                "--extra-index-url", "https://download.pytorch.org/whl/cu121"
            ])
            print("✅ PyTorch GPU 版本安装完成")
        except subprocess.CalledProcessError:
            print("❌ PyTorch GPU 版本安装失败。")
            sys.exit(1)
    else:
        print("🖥️ 未检测到 NVIDIA GPU (或未安装驱动)。准备安装纯 CPU 版本 PyTorch...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install",
                "torch==2.2.2+cpu", "torchvision==0.17.2+cpu",
                "--extra-index-url", "https://download.pytorch.org/whl/cpu"
            ])
            print("✅ PyTorch CPU 版本安装完成")
        except subprocess.CalledProcessError:
            print("❌ PyTorch CPU 版本安装失败。")
            sys.exit(1)
    
    # 3. 验证安装
    print("\n验证关键包版本...")
    try:
        import numpy
        import torch
        import rembg
        print(f"✅ numpy: {numpy.__version__}")
        print(f"✅ torch: {torch.__version__}")
        print(f"✅ rembg: {rembg.__version__}")
        print("✅ 所有关键包导入成功！")
    except ImportError as e:
        print(f"⚠️ 部分包导入失败: {e}")
        
    print("\n" + "="*50)
    print("🎉 环境配置全部完成！你可以开始运行项目了。")
    print("="*50)

if __name__ == "__main__":
    install_dependencies()