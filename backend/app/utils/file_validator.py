"""
文件上传校验工具
"""
import os
import logging
from pathlib import Path
from typing import Tuple, Optional
from fastapi import UploadFile, HTTPException, status
from PIL import Image
import io

logger = logging.getLogger(__name__)

# ============================================================
# 配置
# ============================================================

# 允许的图片 MIME 类型
ALLOWED_MIME_TYPES = {
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "image/gif": [".gif"],
    "image/webp": [".webp"],
    "image/bmp": [".bmp"],
    "image/tiff": [".tiff", ".tif"],
}

# 允许的图片扩展名
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".tif"}

# 最大文件大小（默认 10MB）
DEFAULT_MAX_SIZE = 10 * 1024 * 1024

# 最大图片尺寸
MAX_IMAGE_WIDTH = 4096
MAX_IMAGE_HEIGHT = 4096

# 预览验证块大小（用于流式读取）
CHUNK_SIZE = 8192
PREVIEW_SIZE = 1024 * 1024  # 1MB 用于验证


# ============================================================
# 使用 PIL 验证图片（替代已弃用的 imghdr）
# ============================================================

def validate_image_with_pil(content: bytes) -> Tuple[bool, str]:
    """
    使用 PIL 验证图片内容（替代已弃用的 imghdr）
    
    Args:
        content: 文件内容
    
    Returns:
        (is_valid, error_message)
    """
    if not content or len(content) < 8:
        return False, "文件内容为空或太短"
    
    try:
        # 使用 PIL 验证图片
        img = Image.open(io.BytesIO(content))
        img.verify()  # 验证图片完整性
        
        # 重新打开以获取格式（verify 后需要重新打开）
        img = Image.open(io.BytesIO(content))
        img_format = img.format.lower() if img.format else 'unknown'
        width, height = img.size
        
        # 检查尺寸限制
        if width > MAX_IMAGE_WIDTH or height > MAX_IMAGE_HEIGHT:
            return False, f"图片尺寸过大: {width}x{height}，最大 {MAX_IMAGE_WIDTH}x{MAX_IMAGE_HEIGHT}"
        
        logger.debug(f"图片验证通过: 格式={img_format}, 尺寸={width}x{height}")
        return True, ""
        
    except Exception as e:
        logger.warning(f"图片验证失败: {e}")
        return False, f"无效的图片文件: {str(e)}"


# ============================================================
# 流式文件验证（防止 OOM）
# ============================================================

async def validate_file_stream(
    file: UploadFile,
    max_size: int = DEFAULT_MAX_SIZE,
    check_content: bool = True,
    chunk_size: int = CHUNK_SIZE
) -> Tuple[bool, str, Optional[bytes]]:
    """
    流式验证上传文件（防止 OOM）
    
    Args:
        file: 上传的文件
        max_size: 最大文件大小
        check_content: 是否检查内容
        chunk_size: 读取块大小
    
    Returns:
        (is_valid, error_message, file_content)
    """
    # 1. 验证文件名
    valid, msg = validate_filename(file.filename)
    if not valid:
        return False, msg, None
    
    # 2. 验证文件类型
    valid, msg = validate_file_type(
        file.filename,
        file.content_type or "application/octet-stream"
    )
    if not valid:
        return False, msg, None
    
    # 3. 流式读取文件（限制大小）
    content = bytearray()
    total_size = 0
    
    try:
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            
            total_size += len(chunk)
            
            # 在读取过程中检查大小
            if total_size > max_size:
                return False, f"文件大小 {total_size / 1024 / 1024:.2f}MB 超过限制 {max_size / 1024 / 1024:.0f}MB", None
            
            content.extend(chunk)
            
            # 如果只需要检查内容，读取足够验证即可
            if check_content and total_size >= PREVIEW_SIZE:
                # 已经读取了足够验证的内容，可以继续读取但不影响验证
                pass
                
    except Exception as e:
        return False, f"读取文件失败: {str(e)}", None
    
    if total_size == 0:
        return False, "文件为空", None
    
    content_bytes = bytes(content)
    
    # 4. 使用 PIL 验证图片内容（替代已弃用的 imghdr）
    if check_content:
        valid, msg = validate_image_with_pil(content_bytes)
        if not valid:
            return False, msg, None
    
    return True, "", content_bytes


def validate_file_type(
    filename: str,
    content_type: str,
    allowed_mime_types: Optional[dict] = None
) -> Tuple[bool, str]:
    """
    验证文件类型
    
    Args:
        filename: 文件名
        content_type: MIME 类型
        allowed_mime_types: 允许的 MIME 类型字典
    
    Returns:
        (is_valid, error_message)
    """
    allowed = allowed_mime_types or ALLOWED_MIME_TYPES
    
    # 获取扩展名
    ext = Path(filename).suffix.lower()
    
    # 优先检查扩展名是否在允许列表中
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"不支持的文件扩展名: {ext}，仅支持: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
    
    # MIME 类型检查（宽松模式：允许不匹配，因为浏览器发送的 MIME 类型不可靠）
    # 如果 MIME 类型不在允许列表中但扩展名是允许的，给予警告但不阻止
    if content_type not in allowed:
        logger.warning(f"⚠️ 文件 MIME 类型 {content_type} 不在允许列表中，但扩展名 {ext} 是允许的，继续处理")
    
    return True, ""


def validate_file_size(
    file_size: int,
    max_size: Optional[int] = None
) -> Tuple[bool, str]:
    """
    验证文件大小（向后兼容）
    
    Args:
        file_size: 文件大小（字节）
        max_size: 最大允许大小（字节）
    
    Returns:
        (is_valid, error_message)
    """
    max_sz = max_size or DEFAULT_MAX_SIZE
    
    if file_size <= 0:
        return False, "文件为空"
    
    if file_size > max_sz:
        max_mb = max_sz / 1024 / 1024
        return False, f"文件大小 {file_size / 1024 / 1024:.2f}MB 超过限制 {max_mb:.0f}MB"
    
    return True, ""


def validate_filename(filename: str) -> Tuple[bool, str]:
    """
    验证文件名安全性
    
    Args:
        filename: 文件名
    
    Returns:
        (is_valid, error_message)
    """
    # 检查是否包含路径遍历字符
    dangerous_chars = ['..', '/', '\\', '\x00']
    for char in dangerous_chars:
        if char in filename:
            return False, f"文件名包含非法字符: {char}"
    
    # 检查是否为空
    if not filename or filename.strip() == "":
        return False, "文件名为空"
    
    # 检查是否包含控制字符
    if any(ord(c) < 32 for c in filename):
        return False, "文件名包含控制字符"
    
    return True, ""


def get_safe_filename(filename: str) -> str:
    """
    生成安全的文件名
    
    Args:
        filename: 原始文件名
    
    Returns:
        str: 安全的文件名
    """
    import re
    
    # 移除路径
    safe_name = Path(filename).name
    
    # 移除危险字符
    dangerous_chars = ['..', '/', '\\', '\x00']
    for char in dangerous_chars:
        safe_name = safe_name.replace(char, '_')
    
    # 只保留 ASCII 字母数字和下划线
    safe_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', safe_name)
    
    # 限制长度
    if len(safe_name) > 255:
        name, ext = os.path.splitext(safe_name)
        safe_name = name[:245] + ext
    
    return safe_name


class FileValidator:
    """文件验证器类"""
    
    def __init__(
        self,
        max_size: int = DEFAULT_MAX_SIZE,
        allowed_mime_types: Optional[dict] = None,
        allowed_extensions: Optional[set] = None,
        chunk_size: int = CHUNK_SIZE
    ):
        self.max_size = max_size
        self.allowed_mime_types = allowed_mime_types or ALLOWED_MIME_TYPES
        self.allowed_extensions = allowed_extensions or ALLOWED_EXTENSIONS
        self.chunk_size = chunk_size
    
    async def validate(
        self,
        file: UploadFile,
        check_content: bool = True
    ) -> Tuple[bool, str, Optional[bytes]]:
        """
        完整验证上传文件（流式）
        
        Args:
            file: 上传的文件
            check_content: 是否检查文件内容
        
        Returns:
            (is_valid, error_message, file_content)
        """
        return await validate_file_stream(
            file=file,
            max_size=self.max_size,
            check_content=check_content,
            chunk_size=self.chunk_size
        )
    
    def get_safe_filename(self, filename: str) -> str:
        """获取安全的文件名"""
        return get_safe_filename(filename)


# ============================================================
# 便捷函数
# ============================================================

def get_file_validator() -> FileValidator:
    """获取文件验证器实例"""
    from app.config import settings
    return FileValidator(
        max_size=settings.MAX_UPLOAD_SIZE
    )


async def validate_upload_file(
    file: UploadFile,
    max_size: Optional[int] = None,
    check_content: bool = True
) -> Tuple[bytes, str]:
    """
    验证上传文件的便捷函数（流式）
    
    Args:
        file: 上传的文件
        max_size: 最大文件大小
        check_content: 是否检查内容
    
    Returns:
        (file_content, safe_filename)
    
    Raises:
        HTTPException: 验证失败时抛出
    """
    from app.config import settings
    
    validator = FileValidator(
        max_size=max_size or settings.MAX_UPLOAD_SIZE
    )
    
    valid, msg, content = await validator.validate(file, check_content)
    
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )
    
    safe_filename = validator.get_safe_filename(file.filename)
    
    return content, safe_filename