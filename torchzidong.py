import subprocess
import sys
import os
import re

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

def get_installed_packages():
    """获取已安装包的字典 {包名: 版本}"""
    try:
        result = subprocess.check_output(
            [sys.executable, "-m", "pip", "list", "--format=freeze"],
            universal_newlines=True
        )
        installed = {}
        for line in result.strip().split('\n'):
            if '==' in line:
                name, version = line.split('==', 1)
                installed[name.lower().replace('-', '_')] = version
        return installed
    except subprocess.CalledProcessError:
        return {}

def parse_requirements(filename):
    """解析 requirements.txt，返回 {包名: 版本} 字典"""
    requirements = {}
    if not os.path.exists(filename):
        print(f"❌ 文件 {filename} 不存在")
        return requirements
    
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # 跳过注释和空行
            if not line or line.startswith('#'):
                continue
            # 解析包名和版本 (支持 ==, >=, <=, >, <, ~= 等格式)
            match = re.match(r'^([a-zA-Z0-9_-]+)(.*)$', line)
            if match:
                name = match.group(1).lower().replace('-', '_')
                version_spec = match.group(2).strip()
                # 提取精确版本号（如果有==）
                if version_spec.startswith('=='):
                    version = version_spec[2:]
                else:
                    version = version_spec  # 保留完整版本规范
                requirements[name] = version
    
    return requirements

def check_torch_conflict(installed):
    """检查torch和torchvision的冲突"""
    conflicts = []
    
    # torch可能的版本格式：2.2.2, 2.2.2+cu121, 2.2.2+cpu
    torch_pkg = installed.get('torch', '')
    torchvision_pkg = installed.get('torchvision', '')
    
    if torch_pkg:
        # 检查是否是GPU版本
        if '+cu' in torch_pkg:
            if not has_nvidia_gpu():
                conflicts.append(('torch', torch_pkg, 'CPU版本（未检测到GPU）'))
                conflicts.append(('torchvision', torchvision_pkg, 'CPU版本（未检测到GPU）'))
        elif '+cpu' in torch_pkg:
            if has_nvidia_gpu():
                conflicts.append(('torch', torch_pkg, 'GPU版本（检测到GPU）'))
                conflicts.append(('torchvision', torchvision_pkg, 'GPU版本（检测到GPU）'))
        else:
            # 标准版本（可能是CPU版本）
            if has_nvidia_gpu():
                print(f"⚠️ 检测到GPU但torch版本为 {torch_pkg}（标准版本），建议安装GPU版本")
    
    return conflicts

def install_dependencies():
    print("="*50)
    print("🚀 开始配置项目环境...")
    print("="*50)
    
    # 清除代理
    clear_proxy_env()
    
    # 获取已安装包
    print("\n[1/3] 正在检查已安装的包...")
    installed = get_installed_packages()
    print(f"✅ 检测到 {len(installed)} 个已安装包")
    
    # 解析requirements.txt
    print("\n[2/3] 正在分析依赖需求...")
    requirements = parse_requirements('requirements.txt')
    print(f"✅ requirements.txt 包含 {len(requirements)} 个依赖")
    
    # 找出需要安装/升级的包
    to_install = []
    to_upgrade = []
    already_ok = []
    
    for pkg_name, req_version in requirements.items():
        installed_version = installed.get(pkg_name)
        
        if not installed_version:
            to_install.append(pkg_name)
        elif req_version.startswith('>=') or req_version.startswith('>') or req_version.startswith('~='):
            # 版本范围，使用pip自行处理
            to_upgrade.append(pkg_name)
        elif installed_version != req_version and not req_version.startswith('<=') and not req_version.startswith('<'):
            # 版本不匹配（精确版本要求）
            to_upgrade.append(pkg_name)
            print(f"   ⚠️ {pkg_name}: 已安装 {installed_version}，需要 {req_version}")
        else:
            already_ok.append(pkg_name)
    
    print(f"\n✅ 已满足要求: {len(already_ok)} 个包")
    print(f"📦 需要新安装: {len(to_install)} 个包")
    print(f"🔄 需要升级: {len(to_upgrade)} 个包")
    
    # 安装/升级依赖
    if to_install or to_upgrade:
        print("\n[3/3] 正在处理依赖...")
        
        if to_install:
            print(f"\n安装新包: {', '.join(to_install[:5])}{'...' if len(to_install) > 5 else ''}")
            try:
                # 只安装未安装的包
                install_cmd = [sys.executable, "-m", "pip", "install"]
                for pkg in to_install:
                    # 找到原始包名（从requirements中）
                    for orig_name, version in requirements.items():
                        if orig_name == pkg:
                            if version.startswith('>=') or version.startswith('>') or version.startswith('~='):
                                install_cmd.append(f"{pkg}{version}")
                            else:
                                install_cmd.append(f"{pkg}=={version}")
                            break
                subprocess.check_call(install_cmd)
                print("✅ 新包安装完成")
            except subprocess.CalledProcessError as e:
                print(f"❌ 安装失败: {e}")
                sys.exit(1)
        
        if to_upgrade:
            print(f"\n升级包: {', '.join(to_upgrade[:5])}{'...' if len(to_upgrade) > 5 else ''}")
            try:
                upgrade_cmd = [sys.executable, "-m", "pip", "install", "--upgrade"]
                for pkg in to_upgrade:
                    for orig_name, version in requirements.items():
                        if orig_name == pkg:
                            if version.startswith('>=') or version.startswith('>') or version.startswith('~='):
                                upgrade_cmd.append(f"{pkg}{version}")
                            else:
                                upgrade_cmd.append(f"{pkg}=={version}")
                            break
                subprocess.check_call(upgrade_cmd)
                print("✅ 包升级完成")
            except subprocess.CalledProcessError as e:
                print(f"❌ 升级失败: {e}")
                sys.exit(1)
    else:
        print("\n[3/3] 所有依赖已满足，无需安装")
    
    # 检查torch冲突
    print("\n[额外检查] 检测 PyTorch 版本...")
    torch_conflicts = check_torch_conflict(installed)
    
    if torch_conflicts:
        print("⚠️ 检测到 PyTorch 版本冲突：")
        for pkg, current, target in torch_conflicts:
            print(f"   - {pkg}: 当前 {current}，建议 {target}")
        
        # 先卸载冲突的torch版本
        print("\n卸载旧版本 PyTorch...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "uninstall", "-y",
                "torch", "torchvision"
            ])
            print("✅ 卸载完成")
        except subprocess.CalledProcessError:
            print("⚠️ 卸载时出现警告（可能是未安装）")
    
    # 检查是否需要安装torch
    installed = get_installed_packages()  # 重新获取
    if 'torch' not in installed:
        print("\n正在安装 PyTorch...")
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
    else:
        print(f"✅ PyTorch 已安装: {installed['torch']}")
        print(f"✅ TorchVision 已安装: {installed.get('torchvision', '未安装')}")
    
    # 验证安装
    print("\n验证关键包版本...")
    try:
        import numpy
        import torch
        import rembg
        print(f"✅ numpy: {numpy.__version__}")
        print(f"✅ torch: {torch.__version__}")
        print(f"✅ rembg: {rembg.__version__}")
        
        if torch.cuda.is_available():
            print(f"✅ CUDA 可用: {torch.cuda.get_device_name(0)}")
        else:
            print("ℹ️ CUDA 不可用（使用 CPU 模式）")
        
        print("✅ 所有关键包导入成功！")
    except ImportError as e:
        print(f"⚠️ 部分包导入失败: {e}")
        
    print("\n" + "="*50)
    print("🎉 环境配置全部完成！你可以开始运行项目了。")
    print("="*50)

if __name__ == "__main__":
    install_dependencies()