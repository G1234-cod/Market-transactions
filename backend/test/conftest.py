"""
pytest 配置文件
解决 aiomysql + pytest + Windows 的 Event Loop 关闭问题
"""
import pytest
import asyncio
import sys
import os
import io
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import app


# ============================================================
# 核心修复：Event Loop 管理
# ============================================================

@pytest.fixture(scope="session")
def event_loop():
    """
    创建一个新的事件循环，避免 'Event loop is closed' 错误
    
    这是解决 aiomysql + pytest + Windows 兼容性问题的关键
    """
    # 对于 Windows，使用 SelectorEventLoop 替代 ProactorEventLoop
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def client(event_loop):
    """
    创建测试客户端
    
    每个测试函数使用独立的客户端，确保连接池正确清理
    """
    with TestClient(app) as test_client:
        yield test_client


# ============================================================
# 测试数据 Fixtures
# ============================================================

@pytest.fixture
def sample_image():
    """生成测试图片"""
    img = Image.new('RGB', (640, 480), color='white')
    draw = ImageDraw.Draw(img)
    draw.rectangle([100, 100, 300, 300], outline='black', width=2)
    draw.text((150, 150), "TEST", fill='black')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    return img_bytes


@pytest.fixture
def sample_image_file(sample_image):
    """返回测试图片文件（用于 multipart/form-data）"""
    return ("test.jpg", sample_image, "image/jpeg")


@pytest.fixture
def sample_image_with_object(sample_image):
    """
    生成包含明显物体的测试图片（用于 YOLO 检测测试）
    """
    img = Image.new('RGB', (640, 480), color='white')
    draw = ImageDraw.Draw(img)
    # 绘制一个类似手机的矩形
    draw.rectangle([150, 120, 490, 360], outline='black', width=3, fill='#CCCCCC')
    # 绘制屏幕
    draw.rectangle([180, 150, 460, 330], outline='gray', width=2, fill='#6699CC')
    # 绘制 home 按钮
    draw.ellipse([290, 340, 350, 380], outline='gray', width=2, fill='#888888')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    return img_bytes


# ============================================================
# 认证相关 Fixtures
# ============================================================

@pytest.fixture
def auth_token(client):
    """
    获取认证 token
    
    注意：这个 fixture 会先注册再登录，适合需要认证的测试
    """
    # 注册用户（如果已存在则忽略）
    client.post("/api/v1/register", json={
        "username": "testuser",
        "password": "test123"
    })
    
    # 登录获取 token
    response = client.post("/api/v1/login", json={
        "username": "testuser",
        "password": "test123"
    })
    
    # 根据实际返回结构提取 token
    data = response.json()
    token = data.get("token") or data.get("access_token")
    return token


@pytest.fixture
def auth_headers(auth_token):
    """获取认证请求头"""
    if auth_token:
        return {"Authorization": f"Bearer {auth_token}"}
    return {}


# ============================================================
# 数据库相关 Fixtures
# ============================================================

@pytest.fixture(scope="function")
async def db_connection():
    """
    获取数据库连接（用于需要直接操作数据库的测试）
    
    使用方式：
    async def test_something(db_connection):
        async with db_connection.cursor() as cur:
            await cur.execute("SELECT 1")
    """
    from app.db.connection import get_pool
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


@pytest.fixture(scope="function")
def cleanup_users():
    """
    清理测试用户的 fixture
    
    使用方式：
    def test_register(cleanup_users):
        # 测试代码
        pass
    """
    # 这个 fixture 在测试结束后会清理测试用户
    # 但需要配合 db_connection 使用
    async def _cleanup():
        from app.db.connection import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM users WHERE username LIKE 'test%'")
                await cur.execute("DELETE FROM users WHERE username LIKE 'flow%'")
                await cur.execute("DELETE FROM users WHERE id > 100")  # 清理测试数据
    
    return _cleanup


# ============================================================
# 清理 Fixture（自动清理）
# ============================================================

@pytest.fixture(autouse=True)
def auto_cleanup(request):
    """
    自动清理测试产生的临时数据
    
    autouse=True 表示所有测试都会自动使用
    """
    def cleanup():
        # 测试结束后的清理工作
        pass
    
    request.addfinalizer(cleanup)
    yield


# ============================================================
# 跳过条件 Fixtures
# ============================================================

@pytest.fixture
def skip_if_no_api_keys():
    """
    如果 API Key 未配置则跳过测试
    """
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    deepseek_key = os.getenv('DEEPSEEK_API_KEY')
    dashscope_key = os.getenv('DASHSCOPE_API_KEY')
    
    if not deepseek_key or not dashscope_key:
        pytest.skip("API Key 未配置，跳过需要外部 API 的测试")


# ============================================================
# 辅助 Fixtures
# ============================================================

@pytest.fixture
def mock_env():
    """
    模拟环境变量（用于测试）
    """
    import os
    from dotenv import load_dotenv
    
    original_env = os.environ.copy()
    load_dotenv()  # 加载 .env
    
    yield os.environ
    
    # 恢复原始环境变量
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def temp_upload_dir(tmp_path):
    """
    临时上传目录（用于文件上传测试）
    """
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    return upload_dir