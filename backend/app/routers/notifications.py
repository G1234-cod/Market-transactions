"""通知路由 —— 获取通知、标记已读"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from starlette.status import HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND

from app.db import crud
from app.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["通知"])


# ============================================================
# 1. 获取通知列表
# ============================================================
@router.get("/notifications")
async def get_notifications(
    user_id: int = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    is_read: Optional[bool] = Query(default=None, description="是否已读"),
):
    """
    获取用户通知列表
    
    用户可以查看自己的通知
    """
    try:
        notifications = await crud.get_notifications(user_id=user_id, limit=limit, offset=offset, is_read=is_read)
        return {
            'success': True,
            'notifications': notifications,
            'count': len(notifications),
        }
    except Exception as e:
        logger.error(f"获取通知失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 2. 标记单个通知为已读
# ============================================================
@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    user_id: int = Depends(get_current_user),
):
    """
    标记单个通知为已读
    
    用户只能标记自己的通知
    """
    try:
        success = await crud.mark_notification_read(notification_id=notification_id, user_id=user_id)
        if not success:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="通知不存在或无权访问")
        return {
            'success': True,
            'message': '通知已标记为已读',
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"标记通知已读失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 3. 标记所有通知为已读
# ============================================================
@router.post("/notifications/read-all")
async def mark_all_notifications_read(
    user_id: int = Depends(get_current_user),
):
    """
    标记所有通知为已读
    """
    try:
        await crud.mark_all_notifications_read(user_id=user_id)
        return {
            'success': True,
            'message': '所有通知已标记为已读',
        }
    except Exception as e:
        logger.error(f"标记所有通知已读失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
