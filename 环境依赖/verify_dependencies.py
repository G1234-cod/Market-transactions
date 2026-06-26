import subprocess
import sys
import re

def get_installed_packages():
    """获取已安装包"""
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

def parse_requirements(filename):
    """解析 requirements.txt"""
    requirements = {}
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            match = re.match(r'^([a-zA-Z0-9_-]+)(.*)$', line)
            if match:
                name = match.group(1).lower().replace('-', '_')
                version_spec = match.group(2).strip()
                if version_spec.startswith('=='):
                    version = version_spec[2:]
                else:
                    version = version_spec
                requirements[name] = version
    return requirements

installed = get_installed_packages()
requirements = parse_requirements('requirements.txt')

print("依赖验证结果:")
print("="*60)

missing = []
version_mismatch = []
matched = []

for pkg_name, req_version in requirements.items():
    installed_version = installed.get(pkg_name)
    
    if not installed_version:
        missing.append((pkg_name, req_version))
    elif req_version.startswith('>=') or req_version.startswith('>') or req_version.startswith('~='):
        matched.append((pkg_name, installed_version, req_version))
    elif installed_version != req_version and not req_version.startswith('<=') and not req_version.startswith('<'):
        version_mismatch.append((pkg_name, installed_version, req_version))
    else:
        matched.append((pkg_name, installed_version, req_version))

print(f"\n[OK] 匹配的包: {len(matched)}")
print(f"[WARN] 版本不匹配: {len(version_mismatch)}")
print(f"[ERROR] 缺失的包: {len(missing)}")

if missing:
    print("\n缺失的包:")
    for pkg, req_ver in missing:
        print(f"  - {pkg}: 需要 {req_ver}")

if version_mismatch:
    print("\n版本不匹配:")
    for pkg, inst_ver, req_ver in version_mismatch:
        print(f"  - {pkg}: 已安装 {inst_ver}, 需要 {req_ver}")

# 检查 torch 和 torchvision
print("\n特殊包验证:")
torch_ver = installed.get('torch', '未安装')
torchvision_ver = installed.get('torchvision', '未安装')
print(f"  torch: {torch_ver}")
print(f"  torchvision: {torchvision_ver}")

if '+cu' in torch_ver:
    print(f"  [OK] PyTorch GPU 版本已安装")
elif '+cpu' in torch_ver:
    print(f"  [INFO] PyTorch CPU 版本已安装")
else:
    print(f"  [WARN] PyTorch 标准版本")

print("\n" + "="*60)
print("验证完成！")