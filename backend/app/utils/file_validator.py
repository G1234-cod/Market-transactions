# app/utils/file_validator.py

"""
文件上传校验工具
"""
import os
import imghdr
import logging
from pathlib import Path
from typing import Tuple, Optional
from fastapi import UploadFile, HTTPException, status

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
    
    # 检查 MIME 类型
    if content_type not in allowed:
        return False, f"不支持的文件类型: {content_type}，仅支持: {', '.join(allowed.keys())}"
    
    # 检查扩展名
    ext = Path(filename).suffix.lower()
    if ext not in allowed.get(content_type, []):
        return False, f"文件扩展名与 MIME 类型不匹配: {ext} -> {content_type}"
    
    return True, ""


def validate_file_size(
    file_size: int,
    max_size: Optional[int] = None
) -> Tuple[bool, str]:
    """
    验证文件大小
    
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


def validate_image_content(
    file_content: bytes,
    allowed_types: Optional[list] = None
) -> Tuple[bool, str]:
    """
    验证图片内容（使用 imghdr）
    
    Args:
        file_content: 文件内容
        allowed_types: 允许的图片类型
    
    Returns:
        (is_valid, error_message)
    """
    if allowed_types is None:
        allowed_types = ['jpeg', 'png', 'gif', 'webp', 'bmp', 'tiff']
    
    try:
        # 使用 imghdr 检测图片类型
        img_type = imghdr.what(None, h=file_content)
        
        if img_type is None:
            return False, "无法识别图片格式，可能已损坏"
        
        if img_type not in allowed_types:
            return False, f"不支持的图片格式: {img_type}"
        
        return True, ""
        
    except Exception as e:
        logger.error(f"图片内容验证失败: {e}")
        return False, f"图片验证失败: {str(e)}"


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
    # 移除路径
    safe_name = Path(filename).name
    
    # 移除危险字符
    dangerous_chars = ['..', '/', '\\', '\x00']
    for char in dangerous_chars:
        safe_name = safe_name.replace(char, '_')
    
    # 只保留 ASCII 字母数字和下划线
    import re
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
        allowed_extensions: Optional[set] = None
    ):
        self.max_size = max_size
        self.allowed_mime_types = allowed_mime_types or ALLOWED_MIME_TYPES
        self.allowed_extensions = allowed_extensions or ALLOWED_EXTENSIONS
    
    async def validate(
        self,
        file: UploadFile,
        check_content: bool = True
    ) -> Tuple[bool, str, Optional[bytes]]:
        """
        完整验证上传文件
        
        Args:
            file: 上传的文件
            check_content: 是否检查文件内容
        
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
            file.content_type or "application/octet-stream",
            self.allowed_mime_types
        )
        if not valid:
            return False, msg, None
        
        # 3. 读取文件内容
        try:
            content = await file.read()
        except Exception as e:
            return False, f"读取文件失败: {str(e)}", None
        
        # 4. 验证文件大小
        valid, msg = validate_file_size(len(content), self.max_size)
        if not valid:
            return False, msg, None
        
        # 5. 验证图片内容
        if check_content:
            valid, msg = validate_image_content(content)
            if not valid:
                return False, msg, None
        
        return True, "", content
    
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
    验证上传文件的便捷函数
    
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