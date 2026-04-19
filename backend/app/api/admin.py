"""
管理员API - 用户管理功能
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import hashlib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.user_manager import user_manager
from app.user_password import password_manager
from app.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["管理员"])


# ==================== 请求/响应模型 ====================

class CreateUserRequest(BaseModel):
    """创建用户请求"""
    username: str = Field(..., min_length=3, max_length=20, description="用户名")
    display_name: str = Field(..., min_length=2, max_length=50, description="显示名称")
    password: Optional[str] = Field(None, min_length=6, description="初始密码，留空则自动生成")
    avatar_url: Optional[str] = Field(None, description="头像URL")
    trust_level: int = Field(0, ge=0, le=9, description="信任等级")
    is_admin: bool = Field(False, description="是否为管理员")


class UpdateUserRequest(BaseModel):
    """更新用户请求"""
    display_name: Optional[str] = Field(None, min_length=2, max_length=50)
    avatar_url: Optional[str] = None
    trust_level: Optional[int] = Field(None, ge=-1, le=9)
    is_admin: Optional[bool] = Field(None, description="是否为管理员")


class ToggleStatusRequest(BaseModel):
    """切换用户状态请求"""
    is_active: bool = Field(..., description="true=启用, false=禁用")


class ResetPasswordRequest(BaseModel):
    """重置密码请求"""
    new_password: Optional[str] = Field(None, min_length=6, description="新密码，留空则重置为默认密码")


class UserResponse(BaseModel):
    """用户响应"""
    user_id: str
    username: str
    display_name: str
    avatar_url: Optional[str]
    trust_level: int
    is_admin: bool
    is_active: bool
    linuxdo_id: str
    created_at: str
    last_login: Optional[str]


class CreateUserResponse(BaseModel):
    """创建用户响应"""
    success: bool
    message: str
    user: dict
    default_password: Optional[str] = None


# ==================== 权限检查依赖 ====================

async def check_admin(request: Request) -> User:
    """检查管理员权限"""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="未登录")
    
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    return user


# ==================== API 端点 ====================

@router.get("/users")
async def get_users(
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """获取用户列表（仅管理员）"""
    try:
        all_users = await user_manager.get_all_users()
        
        users_data = []
        for user in all_users:
            # user_manager 返回的是 Pydantic User 对象，直接转为 dict
            user_dict = user.model_dump()
            user_dict["is_active"] = user.trust_level != -1
            users_data.append(user_dict)
        
        logger.info(f"管理员 {admin.user_id} 获取用户列表，共 {len(users_data)} 个用户")
        
        return {
            "total": len(users_data),
            "users": users_data
        }
    except Exception as e:
        logger.error(f"获取用户列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取用户列表失败: {str(e)}")


@router.post("/users")
async def create_user(
    data: CreateUserRequest,
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """添加用户（仅管理员）"""
    try:
        # 检查用户名是否已存在
        all_users = await user_manager.get_all_users()
        for user in all_users:
            if user.username == data.username:
                raise HTTPException(status_code=409, detail="用户名已存在")
        
        # 生成用户ID
        user_id = f"admin_created_{hashlib.md5(data.username.encode()).hexdigest()[:16]}"
        
        # 创建用户
        new_user = await user_manager.create_or_update_from_linuxdo(
            linuxdo_id=user_id,
            username=data.username,
            display_name=data.display_name,
            avatar_url=data.avatar_url,
            trust_level=data.trust_level
        )
        
        # 设置管理员标志
        if data.is_admin:
            # 直接更新数据库中的is_admin字段
            async with await user_manager._get_session() as session:
                result = await session.execute(
                    select(User).where(User.user_id == user_id)
                )
                db_user = result.scalar_one_or_none()
                if db_user:
                    db_user.is_admin = True  # type: ignore[assignment]
                    await session.commit()
                    new_user.is_admin = True
        
        # 设置密码
        actual_password = await password_manager.set_password(
            user_id=new_user.user_id,
            username=data.username,
            password=data.password
        )
        
        # Settings 将在首次访问设置页面时自动创建（延迟初始化）
        
        logger.info(f"管理员 {admin.user_id} 创建了新用户 {new_user.user_id} ({data.username})")
        
        return CreateUserResponse(
            success=True,
            message="用户创建成功",
            user=new_user.model_dump(),
            default_password=actual_password if not data.password else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建用户失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建用户失败: {str(e)}")


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    data: UpdateUserRequest,
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """编辑用户信息（仅管理员）"""
    try:
        # 获取目标用户
        target_user = await user_manager.get_user(user_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 更新用户信息
        async with await user_manager._get_session() as session:
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            db_user = result.scalar_one_or_none()
            
            if not db_user:
                raise HTTPException(status_code=404, detail="用户不存在")
            
            # 更新字段
            if data.display_name is not None:
                db_user.display_name = data.display_name  # type: ignore[assignment]
            if data.avatar_url is not None:
                db_user.avatar_url = data.avatar_url  # type: ignore[assignment]
            if data.trust_level is not None:
                db_user.trust_level = data.trust_level  # type: ignore[assignment]
            if data.is_admin is not None:
                # 检查是否是最后一个管理员
                if db_user.is_admin and not data.is_admin:  # type: ignore[misc]
                    all_users = await user_manager.get_all_users()
                    admin_count = sum(1 for u in all_users if u.is_admin)
                    if admin_count <= 1:
                        raise HTTPException(status_code=400, detail="不能取消最后一个管理员的权限")
                db_user.is_admin = data.is_admin  # type: ignore[assignment]
            
            await session.commit()
            await session.refresh(db_user)
        
        logger.info(f"管理员 {admin.user_id} 更新了用户 {user_id} 的信息")
        
        updated_user = await user_manager.get_user(user_id)
        if updated_user:
            user_dict = updated_user.model_dump()
            user_dict["is_active"] = updated_user.trust_level != -1
        else:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        return {
            "success": True,
            "message": "用户信息更新成功",
            "user": user_dict
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新用户失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新用户失败: {str(e)}")


@router.post("/users/{user_id}/toggle-status")
async def toggle_user_status(
    user_id: str,
    data: ToggleStatusRequest,
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """切换用户状态（启用/禁用）（仅管理员）"""
    try:
        # 不允许禁用自己
        if user_id == admin.user_id:
            raise HTTPException(status_code=400, detail="不能禁用自己的账号")
        
        # 获取目标用户
        target_user = await user_manager.get_user(user_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 更新状态
        async with await user_manager._get_session() as session:
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            db_user = result.scalar_one_or_none()
            
            if not db_user:
                raise HTTPException(status_code=404, detail="用户不存在")
            
            if data.is_active:
                # 启用用户：恢复trust_level为0（或之前的值）
                db_user.trust_level = 0  # type: ignore[assignment]
            else:
                # 禁用用户：设置trust_level为-1
                db_user.trust_level = -1  # type: ignore[assignment]
            
            await session.commit()
        
        status_text = "启用" if data.is_active else "禁用"
        logger.info(f"管理员 {admin.user_id} {status_text}了用户 {user_id}")
        
        return {
            "success": True,
            "message": f"用户已{status_text}",
            "is_active": data.is_active
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"切换用户状态失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"切换用户状态失败: {str(e)}")


@router.post("/users/{user_id}/reset-password")
async def reset_password(
    user_id: str,
    data: ResetPasswordRequest,
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """重置用户密码（仅管理员）"""
    try:
        # 获取目标用户
        target_user = await user_manager.get_user(user_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 重置密码
        actual_password = await password_manager.set_password(
            user_id=user_id,
            username=target_user.username,
            password=data.new_password
        )
        
        logger.info(f"管理员 {admin.user_id} 重置了用户 {user_id} 的密码")
        
        return {
            "success": True,
            "message": "密码重置成功",
            "new_password": actual_password
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重置密码失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"重置密码失败: {str(e)}")


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """删除用户（仅管理员，慎用）"""
    try:
        # 不允许删除自己
        if user_id == admin.user_id:
            raise HTTPException(status_code=400, detail="不能删除自己的账号")
        
        # 获取目标用户
        target_user = await user_manager.get_user(user_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 检查是否是最后一个管理员
        if target_user.is_admin:
            all_users = await user_manager.get_all_users()
            admin_count = sum(1 for u in all_users if u.is_admin)
            if admin_count <= 1:
                raise HTTPException(status_code=400, detail="不能删除最后一个管理员账号")
        
        # 删除用户（包括密码记录）
        async with await user_manager._get_session() as session:
            # 删除用户记录
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            db_user = result.scalar_one_or_none()
            if db_user:
                await session.delete(db_user)
            
            # 删除密码记录
            from app.models.user import UserPassword
            result = await session.execute(
                select(UserPassword).where(UserPassword.user_id == user_id)
            )
            pwd_record = result.scalar_one_or_none()
            if pwd_record:
                await session.delete(pwd_record)
            
            await session.commit()
        
        logger.warning(f"管理员 {admin.user_id} 删除了用户 {user_id}")
        
        return {
            "success": True,
            "message": "用户已删除"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除用户失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除用户失败: {str(e)}")


# ==================== 装饰管理 API ====================

from app.models.system_config import SystemDecorationConfig
from typing import Literal

# 装饰类型验证
VALID_DECORATION_TYPES = ['spring-festival', 'spring', 'summer', 'autumn', 'winter', 'auto', 'none']


class DecorationConfigResponse(BaseModel):
    """装饰配置响应"""
    id: str
    decoration_type: str
    force_enabled: bool
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None


class UpdateDecorationConfigRequest(BaseModel):
    """更新装饰配置请求"""
    decoration_type: str = Field(
        ...,
        description="装饰类型: spring-festival, spring, summer, autumn, winter, auto, none"
    )
    force_enabled: bool = Field(
        default=False,
        description="是否强制启用(覆盖用户本地设置)"
    )
    description: Optional[str] = Field(None, description="装饰说明")


@router.get("/decoration-config", response_model=DecorationConfigResponse)
async def get_decoration_config(
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    获取系统装饰配置（仅管理员）

    返回当前全局装饰设置
    """
    result = await db.execute(
        select(SystemDecorationConfig).limit(1)
    )
    config = result.scalar_one_or_none()

    if not config:
        # 如果不存在，创建默认配置
        config = SystemDecorationConfig(
            id="default_decoration_config",
            decoration_type='auto',
            force_enabled=False
        )
        db.add(config)
        await db.commit()
        await db.refresh(config)

    return config.to_dict()


@router.put("/decoration-config", response_model=DecorationConfigResponse)
async def update_decoration_config(
    data: UpdateDecorationConfigRequest,
    admin: User = Depends(check_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    更新系统装饰配置（仅管理员）

    管理员可以：
    - 设置全局装饰类型
    - 强制启用特定装饰（覆盖用户本地设置）
    """
    # 验证装饰类型
    if data.decoration_type not in VALID_DECORATION_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"无效的装饰类型，可选值: {', '.join(VALID_DECORATION_TYPES)}"
        )

    result = await db.execute(
        select(SystemDecorationConfig).limit(1)
    )
    config = result.scalar_one_or_none()

    if not config:
        config = SystemDecorationConfig(
            id="default_decoration_config",
            decoration_type=data.decoration_type,
            force_enabled=data.force_enabled,
            description=data.description,
            updated_by=admin.user_id
        )
        db.add(config)
    else:
        config.decoration_type = data.decoration_type
        config.force_enabled = data.force_enabled
        if data.description is not None:
            config.description = data.description
        config.updated_by = admin.user_id

    await db.commit()
    await db.refresh(config)

    logger.info(f"管理员 {admin.user_id} 更新了系统装饰配置: type={data.decoration_type}, force={data.force_enabled}")

    return config.to_dict()