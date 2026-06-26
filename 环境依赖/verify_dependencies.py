"""
验证依赖是否安装完成
"""
import sys
import importlib

def check_package(pkg_name, import_name=None):
    """检查包是否已安装"""
    if import_name is None:
        import_name = pkg_name.replace('-', '_')
    try:
        module = importlib.import_module(import_name)
        version = getattr(module, '__version__', '未知')
        print(f"✅ {pkg_name}: {version}")
        return True
    except ImportError:
        print(f"❌ {pkg_name}: 未安装")
        return False

def main():
    print("=" * 60)
    print("📋 依赖验证")
    print("=" * 60)
    print(f"Python: {sys.version}")
    print("-" * 60)
    
    # 需要检查的包
    packages = [
        ("fastapi",),
        ("uvicorn",),
        ("python-multipart", "multipart"),
        ("aiofiles",),
        ("aiomysql",),
        ("PyMySQL", "pymysql"),
        ("torch",),
        ("torchvision",),
        ("ultralytics",),
        ("open-clip-torch", "open_clip"),
        ("Pillow", "PIL"),
        ("opencv-python", "cv2"),
        ("rembg",),
        ("openai",),
        ("dashscope",),
        ("httpx",),
        ("qdrant-client", "qdrant_client"),
        ("python-jose", "jose"),
        ("passlib",),
        ("python-dotenv", "dotenv"),
        ("pydantic",),
        ("pydantic-settings", "pydantic_settings"),
        ("pytest",),
        ("pytest-asyncio", "pytest_asyncio"),
        ("PyYAML", "yaml"),
        ("pandas",),
        ("numpy",),
        ("requests",),
        ("tqdm",),
    ]
    
    success = 0
    fail = 0
    
    for pkg in packages:
        name = pkg[0]
        import_name = pkg[1] if len(pkg) > 1 else None
        if check_package(name, import_name):
            success += 1
        else:
            fail += 1
    
    print("-" * 60)
    print(f"✅ 成功: {success} 个")
    print(f"❌ 失败: {fail} 个")
    print("=" * 60)

if __name__ == "__main__":
    main()