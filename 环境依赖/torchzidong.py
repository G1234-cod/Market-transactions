import subprocess
import sys
import os
import re
import chardet  # 需要先安装: pip install chardet

def has_nvidia_gpu():
    """检测本机是否存在 Nvidia GPU 并已安装驱动"""
    try:
        subprocess.check_output(['nvidia-smi'], stderr=subprocess.STDOUT)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def clear_proxy_env():
    """清除代理环境变量（如果有）"""
    proxy_vars = ['HTTP_PROXY', 'HTTPS_URL', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy']
    for var in proxy_vars:
        if var in os.environ:
            print(f"[WARN] 检测到代理环境变量: {var}={os.environ[var]}")
            del os.environ[var]
            print(f"[OK] 已清除 {var}")

def get_installed_packages():
    """获取已安装包的字典 {包名: 版本}"""
    try:
        result = subprocess.check_output(
            [sys.executable, "-m", "pip", "list", "--format=freeze"],
            universal_newlines=True,
            encoding='utf-8'
        )
        installed = {}
        for line in result.strip().split('\n'):
            if '==' in line:
                name, version = line.split('==', 1)
                installed[name.lower().replace('-', '_')] = version
        return installed
    except subprocess.CalledProcessError:
        return {}

def detect_encoding(filepath):
    """检测文件编码"""
    try:
        with open(filepath, 'rb') as f:
            raw_data = f.read()
        result = chardet.detect(raw_data)
        return result['encoding'] or 'utf-8'
    except Exception:
        return 'utf-8'

def parse_requirements(filename):
    """解析 requirements.txt，返回 {包名: 版本} 字典"""
    requirements = {}
    if not os.path.exists(filename):
        print(f"[ERROR] 文件 {filename} 不存在")
        return requirements
    
    # ✅ 自动检测编码
    encoding = detect_encoding(filename)
    print(f"[INFO] 检测到文件编码: {encoding}")
    
    content = None
    try:
        # 尝试用检测到的编码读取
        with open(filename, 'r', encoding=encoding) as f:
            content = f.read()
    except UnicodeDecodeError:
        # 如果还是失败，尝试其他编码
        try:
            with open(filename, 'r', encoding='utf-8-sig') as f:
                content = f.read()
            print("[INFO] 使用 UTF-8-SIG 编码读取成功")
        except UnicodeDecodeError:
            try:
                with open(filename, 'r', encoding='gbk') as f:
                    content = f.read()
                print("[INFO] 使用 GBK 编码读取成功")
            except UnicodeDecodeError:
                try:
                    with open(filename, 'r', encoding='gb2312') as f:
                        content = f.read()
                    print("[INFO] 使用 GB2312 编码读取成功")
                except UnicodeDecodeError:
                    try:
                        with open(filename, 'r', encoding='latin-1') as f:
                            content = f.read()
                        print("[INFO] 使用 Latin-1 编码读取成功")
                    except UnicodeDecodeError:
                        # 最后尝试忽略错误
                        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        print("[WARN] 使用 UTF-8（忽略错误）编码读取")
    
    if content is None:
        print("[ERROR] 无法读取文件内容")
        return requirements
    
    # 解析内容
    for line in content.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        # 处理 pip 的 -e 安装
        if line.startswith('-e'):
            match = re.search(r'#egg=([a-zA-Z0-9_-]+)', line)
            if match:
                name = match.group(1).lower().replace('-', '_')
                requirements[name] = 'editable'
            continue
        # 处理 @ 语法 (pip 21+)
        if ' @ ' in line:
            match = re.match(r'^([a-zA-Z0-9_-]+)\s*@', line)
            if match:
                name = match.group(1).lower().replace('-', '_')
                requirements[name] = 'direct_url'
            continue
        # 标准格式
        match = re.match(r'^([a-zA-Z0-9_-]+)(.*)$', line)
        if match:
            name = match.group(1).lower().replace('-', '_')
            version_spec = match.group(2).strip()
            if version_spec.startswith('=='):
                version = version_spec[2:]
            elif version_spec.startswith('>=') or version_spec.startswith('>') or version_spec.startswith('~='):
                version = version_spec
            else:
                version = version_spec
            requirements[name] = version if version else 'any'
    
    return requirements

def check_torch_conflict(installed):
    """检查torch和torchvision的冲突"""
    conflicts = []
    
    torch_pkg = installed.get('torch', '')
    torchvision_pkg = installed.get('torchvision', '')
    
    if torch_pkg:
        if '+cu' in torch_pkg:
            if not has_nvidia_gpu():
                conflicts.append(('torch', torch_pkg, 'CPU版本（未检测到GPU）'))
                conflicts.append(('torchvision', torchvision_pkg, 'CPU版本（未检测到GPU）'))
        elif '+cpu' in torch_pkg:
            if has_nvidia_gpu():
                conflicts.append(('torch', torch_pkg, 'GPU版本（检测到GPU）'))
                conflicts.append(('torchvision', torchvision_pkg, 'GPU版本（检测到GPU）'))
        else:
            if has_nvidia_gpu():
                print(f"[WARN] 检测到GPU但torch版本为 {torch_pkg}（标准版本），建议安装GPU版本")
    
    return conflicts

def install_dependencies():
    print("="*50)
    print("[START] 开始配置项目环境...")
    print("="*50)
    
    clear_proxy_env()
    
    print("\n[1/3] 正在检查已安装的包...")
    installed = get_installed_packages()
    print(f"[OK] 检测到 {len(installed)} 个已安装包")
    
    print("\n[2/3] 正在分析依赖需求...")
    requirements = parse_requirements('requirements.txt')
    print(f"[OK] requirements.txt 包含 {len(requirements)} 个依赖")
    
    if not requirements:
        print("[ERROR] 没有解析到任何依赖，请检查 requirements.txt 文件")
        return
    
    to_install = []
    to_upgrade = []
    already_ok = []
    skipped = []
    
    for pkg_name, req_version in requirements.items():
        installed_version = installed.get(pkg_name)
        
        if not installed_version:
            to_install.append(pkg_name)
        elif req_version in ['any', 'editable', 'direct_url']:
            # 无法确定版本，跳过
            skipped.append(pkg_name)
            already_ok.append(pkg_name)
        elif req_version.startswith('>=') or req_version.startswith('>') or req_version.startswith('~='):
            # 版本约束，需要升级检查
            to_upgrade.append(pkg_name)
        elif installed_version != req_version and not req_version.startswith('<=') and not req_version.startswith('<'):
            to_upgrade.append(pkg_name)
            print(f"   [WARN] {pkg_name}: 已安装 {installed_version}，需要 {req_version}")
        else:
            already_ok.append(pkg_name)
    
    print(f"\n[OK] 已满足要求: {len(already_ok)} 个包")
    print(f"[INFO] 需要新安装: {len(to_install)} 个包")
    print(f"[INFO] 需要升级: {len(to_upgrade)} 个包")
    if skipped:
        print(f"[INFO] 跳过: {len(skipped)} 个包（无法确定版本）")
    
    if to_install or to_upgrade:
        print("\n[3/3] 正在处理依赖...")
        
        if to_install:
            print(f"\n📦 安装新包: {', '.join(to_install[:5])}{'...' if len(to_install) > 5 else ''}")
            try:
                install_cmd = [sys.executable, "-m", "pip", "install"]
                for pkg in to_install:
                    version = requirements.get(pkg, '')
                    if version and version not in ['any', 'editable', 'direct_url']:
                        if version.startswith('>=') or version.startswith('>') or version.startswith('~='):
                            install_cmd.append(f"{pkg}{version}")
                        else:
                            install_cmd.append(f"{pkg}=={version}")
                    else:
                        install_cmd.append(pkg)
                subprocess.check_call(install_cmd)
                print("[OK] 新包安装完成")
            except subprocess.CalledProcessError as e:
                print(f"[ERROR] 安装失败: {e}")
                # 不退出，继续尝试
    
        if to_upgrade:
            print(f"\n⬆️  升级包: {', '.join(to_upgrade[:5])}{'...' if len(to_upgrade) > 5 else ''}")
            try:
                upgrade_cmd = [sys.executable, "-m", "pip", "install", "--upgrade"]
                for pkg in to_upgrade:
                    version = requirements.get(pkg, '')
                    if version and version not in ['any', 'editable', 'direct_url']:
                        if version.startswith('>=') or version.startswith('>') or version.startswith('~='):
                            upgrade_cmd.append(f"{pkg}{version}")
                        else:
                            upgrade_cmd.append(f"{pkg}=={version}")
                    else:
                        upgrade_cmd.append(pkg)
                subprocess.check_call(upgrade_cmd)
                print("[OK] 包升级完成")
            except subprocess.CalledProcessError as e:
                print(f"[ERROR] 升级失败: {e}")
                # 不退出，继续尝试
    else:
        print("\n[3/3] 所有依赖已满足，无需安装")
    
    print("\n[EXTRA] 检测 PyTorch 版本...")
    installed = get_installed_packages()
    torch_conflicts = check_torch_conflict(installed)
    
    if torch_conflicts:
        print("[WARN] 检测到 PyTorch 版本冲突：")
        for pkg, current, target in torch_conflicts:
            print(f"   - {pkg}: 当前 {current}，建议 {target}")
        
        print("\n卸载旧版本 PyTorch...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "uninstall", "-y",
                "torch", "torchvision"
            ])
            print("[OK] 卸载完成")
        except subprocess.CalledProcessError:
            print("[WARN] 卸载时出现警告（可能是未安装）")
    
    installed = get_installed_packages()
    if 'torch' not in installed:
        print("\n正在安装 PyTorch...")
        if has_nvidia_gpu():
            print("[OK] 检测到 NVIDIA GPU！准备安装 GPU 版本 PyTorch (CUDA 12.1)...")
            try:
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install",
                    "torch==2.2.2+cu121", "torchvision==0.17.2+cu121",
                    "--extra-index-url", "https://download.pytorch.org/whl/cu121"
                ])
                print("[OK] PyTorch GPU 版本安装完成")
            except subprocess.CalledProcessError:
                print("[ERROR] PyTorch GPU 版本安装失败。")
                # 尝试安装 CPU 版本作为备选
                print("[INFO] 尝试安装 CPU 版本...")
                try:
                    subprocess.check_call([
                        sys.executable, "-m", "pip", "install",
                        "torch==2.2.2+cpu", "torchvision==0.17.2+cpu",
                        "--extra-index-url", "https://download.pytorch.org/whl/cpu"
                    ])
                    print("[OK] PyTorch CPU 版本安装完成（作为备选）")
                except subprocess.CalledProcessError:
                    print("[ERROR] PyTorch 安装完全失败。")
                    sys.exit(1)
        else:
            print("[INFO] 未检测到 NVIDIA GPU (或未安装驱动)。准备安装纯 CPU 版本 PyTorch...")
            try:
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install",
                    "torch==2.2.2+cpu", "torchvision==0.17.2+cpu",
                    "--extra-index-url", "https://download.pytorch.org/whl/cpu"
                ])
                print("[OK] PyTorch CPU 版本安装完成")
            except subprocess.CalledProcessError:
                print("[ERROR] PyTorch CPU 版本安装失败。")
                sys.exit(1)
    else:
        print(f"[OK] PyTorch 已安装: {installed['torch']}")
        print(f"[OK] TorchVision 已安装: {installed.get('torchvision', '未安装')}")
    
    print("\n验证关键包版本...")
    try:
        import numpy
        import torch
        import rembg
        print(f"[OK] numpy: {numpy.__version__}")
        print(f"[OK] torch: {torch.__version__}")
        print(f"[OK] rembg: {rembg.__version__}")
        
        if torch.cuda.is_available():
            print(f"[OK] CUDA 可用: {torch.cuda.get_device_name(0)}")
        else:
            print("[INFO] CUDA 不可用（使用 CPU 模式）")
        
        print("[OK] 所有关键包导入成功！")
    except ImportError as e:
        print(f"[WARN] 部分包导入失败: {e}")
        
    print("\n" + "="*50)
    print("[DONE] 环境配置全部完成！你可以开始运行项目了。")
    print("="*50)

if __name__ == "__main__":
    install_dependencies()