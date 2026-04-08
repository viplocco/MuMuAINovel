"""职业模板管理API"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional, List
import json

from app.database import get_db
from app.models.career_template import CareerTemplate
from app.models.career import Career
from app.models.project import Project
from app.schemas.career import CareerStage
from app.logger import get_logger
from app.api.common import verify_project_access

router = APIRouter(prefix="/career-templates", tags=["职业模板库"])
logger = get_logger(__name__)


# ===== Schema定义 =====
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Any


class CareerTemplateStage(BaseModel):
    """职业阶段模型"""
    level: int = Field(..., description="阶段等级")
    name: str = Field(..., description="阶段名称")
    description: Optional[str] = Field(None, description="阶段描述")


class CareerTemplateBase(BaseModel):
    """职业模板基础模型"""
    name: str = Field(..., description="职业名称")
    type: str = Field(..., description="职业类型: main/sub")
    description: Optional[str] = Field(None, description="职业描述")
    category: Optional[str] = Field(None, description="职业分类")
    applicable_genres: List[str] = Field(..., description="适用小说类型")
    stages: List[CareerTemplateStage] = Field(..., description="职业阶段列表")
    max_stage: int = Field(10, description="最大阶段数")
    requirements: Optional[str] = Field(None, description="职业要求")
    special_abilities: Optional[str] = Field(None, description="特殊能力")
    worldview_rules: Optional[str] = Field(None, description="世界观规则")
    attribute_bonuses: Optional[Dict[str, str]] = Field(None, description="属性加成")
    base_attributes: Optional[Dict[str, Any]] = Field(None, description="基础能力配置")
    per_stage_bonus: Optional[Dict[str, Any]] = Field(None, description="每阶段能力加成")


class CareerTemplateCreate(CareerTemplateBase):
    """创建职业模板的请求模型"""
    pass


class CareerTemplateUpdate(BaseModel):
    """更新职业模板的请求模型"""
    name: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    applicable_genres: Optional[List[str]] = None
    stages: Optional[List[CareerTemplateStage]] = None
    max_stage: Optional[int] = None
    requirements: Optional[str] = None
    special_abilities: Optional[str] = None
    worldview_rules: Optional[str] = None
    attribute_bonuses: Optional[Dict[str, str]] = None
    base_attributes: Optional[Dict[str, Any]] = None
    per_stage_bonus: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    order_index: Optional[int] = None


class CareerTemplateResponse(CareerTemplateBase):
    """职业模板响应模型"""
    id: str
    is_official: bool
    is_active: bool
    order_index: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CareerTemplateListResponse(BaseModel):
    """职业模板列表响应模型"""
    total: int
    templates: List[CareerTemplateResponse]


class ApplyTemplatesRequest(BaseModel):
    """应用模板到项目的请求模型"""
    project_id: str
    template_ids: List[str]


# ===== API实现 =====

@router.get("", response_model=CareerTemplateListResponse, summary="获取职业模板列表")
async def list_career_templates(
    genre: Optional[str] = None,
    type: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    获取职业模板列表

    Args:
        genre: 按小说类型筛选
        type: 按职业类型筛选 (main/sub)
        is_active: 是否只显示启用的模板
    """
    query = select(CareerTemplate)

    # 按类型筛选
    if type:
        query = query.where(CareerTemplate.type == type)

    # 按启用状态筛选
    if is_active is not None:
        query = query.where(CareerTemplate.is_active == is_active)

    # 按小说类型筛选（JSON字段查询）
    if genre:
        # PostgreSQL JSON查询
        query = query.where(
            CareerTemplate.applicable_genres.contains(f'"{genre}"')
        )

    # 排序：先按order_index，再按创建时间
    query = query.order_by(CareerTemplate.order_index, CareerTemplate.created_at.desc())

    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # 获取列表
    result = await db.execute(query)
    templates = result.scalars().all()

    # 转换响应
    template_list = []
    for t in templates:
        template_list.append(_template_to_response(t))

    return CareerTemplateListResponse(total=total, templates=template_list)


@router.get("/genres", summary="获取所有小说类型")
async def get_all_genres():
    """获取所有支持的类型列表"""
    from app.constants.attribute_definitions import get_all_genres
    return {"genres": get_all_genres()}


@router.get("/{template_id}", response_model=CareerTemplateResponse, summary="获取职业模板详情")
async def get_career_template(
    template_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取单个职业模板详情"""
    result = await db.execute(
        select(CareerTemplate).where(CareerTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="职业模板不存在")

    return _template_to_response(template)


@router.post("", response_model=CareerTemplateResponse, summary="创建自定义职业模板")
async def create_career_template(
    template_data: CareerTemplateCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建自定义职业模板（非官方）"""
    try:
        template = CareerTemplate(
            name=template_data.name,
            type=template_data.type,
            description=template_data.description,
            category=template_data.category,
            applicable_genres=json.dumps(template_data.applicable_genres, ensure_ascii=False),
            stages=json.dumps([s.model_dump() for s in template_data.stages], ensure_ascii=False),
            max_stage=template_data.max_stage,
            requirements=template_data.requirements,
            special_abilities=template_data.special_abilities,
            worldview_rules=template_data.worldview_rules,
            attribute_bonuses=json.dumps(template_data.attribute_bonuses, ensure_ascii=False) if template_data.attribute_bonuses else None,
            base_attributes=json.dumps(template_data.base_attributes, ensure_ascii=False) if template_data.base_attributes else None,
            per_stage_bonus=json.dumps(template_data.per_stage_bonus, ensure_ascii=False) if template_data.per_stage_bonus else None,
            is_official=False,
            is_active=True
        )
        db.add(template)
        await db.commit()
        await db.refresh(template)

        logger.info(f"✅ 创建职业模板成功：{template.name}")
        return _template_to_response(template)

    except Exception as e:
        logger.error(f"创建职业模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建职业模板失败: {str(e)}")


@router.put("/{template_id}", response_model=CareerTemplateResponse, summary="更新职业模板")
async def update_career_template(
    template_id: str,
    template_update: CareerTemplateUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新职业模板（只能更新非官方模板）"""
    result = await db.execute(
        select(CareerTemplate).where(CareerTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="职业模板不存在")

    if template.is_official:
        raise HTTPException(status_code=403, detail="官方模板不可修改")

    # 更新字段
    update_data = template_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field == "stages" and value is not None:
            setattr(template, field, json.dumps([s.model_dump() if hasattr(s, 'model_dump') else s for s in value], ensure_ascii=False))
        elif field == "applicable_genres" and value is not None:
            setattr(template, field, json.dumps(value, ensure_ascii=False))
        elif field in ("attribute_bonuses", "base_attributes", "per_stage_bonus") and value is not None:
            setattr(template, field, json.dumps(value, ensure_ascii=False))
        else:
            setattr(template, field, value)

    await db.commit()
    await db.refresh(template)

    logger.info(f"✅ 更新职业模板成功：{template.name}")
    return _template_to_response(template)


@router.delete("/{template_id}", summary="删除职业模板")
async def delete_career_template(
    template_id: str,
    db: AsyncSession = Depends(get_db)
):
    """删除职业模板（只能删除非官方模板）"""
    result = await db.execute(
        select(CareerTemplate).where(CareerTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="职业模板不存在")

    if template.is_official:
        raise HTTPException(status_code=403, detail="官方模板不可删除")

    await db.delete(template)
    await db.commit()

    logger.info(f"✅ 删除职业模板成功：{template.name}")
    return {"message": "职业模板删除成功"}


@router.post("/apply", summary="应用模板到项目")
async def apply_templates_to_project(
    request: ApplyTemplatesRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    将职业模板应用到项目，创建实际职业

    Args:
        request: 包含project_id和template_ids
    """
    user_id = getattr(http_request.state, 'user_id', None)
    project = await verify_project_access(request.project_id, user_id, db)

    if not request.template_ids:
        raise HTTPException(status_code=400, detail="请选择要应用的模板")

    # 获取模板
    result = await db.execute(
        select(CareerTemplate).where(CareerTemplate.id.in_(request.template_ids))
    )
    templates = result.scalars().all()

    if not templates:
        raise HTTPException(status_code=404, detail="未找到指定的模板")

    # 创建职业
    created_careers = []
    for template in templates:
        # 检查是否已存在同名职业
        existing_result = await db.execute(
            select(Career).where(
                Career.project_id == request.project_id,
                Career.name == template.name
            )
        )
        if existing_result.scalar_one_or_none():
            logger.info(f"  跳过已存在的职业：{template.name}")
            continue

        career = Career(
            project_id=request.project_id,
            name=template.name,
            type=template.type,
            description=template.description,
            category=template.category,
            stages=template.stages,
            max_stage=template.max_stage,
            requirements=template.requirements,
            special_abilities=template.special_abilities,
            worldview_rules=template.worldview_rules,
            attribute_bonuses=template.attribute_bonuses,
            base_attributes=template.base_attributes,
            per_stage_bonus=template.per_stage_bonus,
            source="template"
        )
        db.add(career)
        created_careers.append(template.name)
        logger.info(f"  ✅ 从模板创建职业：{template.name}")

    await db.commit()

    return {
        "message": f"成功创建 {len(created_careers)} 个职业",
        "created_careers": created_careers
    }


@router.post("/auto-apply/{project_id}", summary="自动应用推荐模板")
async def auto_apply_templates(
    project_id: str,
    http_request: Request,
    main_count: int = 3,
    sub_count: int = 2,
    db: AsyncSession = Depends(get_db)
):
    """
    根据项目类型自动应用推荐的职业模板

    Args:
        project_id: 项目ID
        main_count: 主职业数量
        sub_count: 副职业数量
    """
    user_id = getattr(http_request.state, 'user_id', None)
    project = await verify_project_access(project_id, user_id, db)

    genre = project.genre
    if not genre:
        raise HTTPException(status_code=400, detail="项目未设置小说类型，无法自动推荐模板")

    # 查询匹配类型的模板
    result = await db.execute(
        select(CareerTemplate).where(
            CareerTemplate.is_active == True,
            CareerTemplate.applicable_genres.contains(f'"{genre}"')
        ).order_by(CareerTemplate.order_index)
    )
    templates = result.scalars().all()

    if not templates:
        raise HTTPException(status_code=404, detail=f"未找到适用于 {genre} 类型的模板")

    # 分离主职业和副职业模板
    main_templates = [t for t in templates if t.type == "main"][:main_count]
    sub_templates = [t for t in templates if t.type == "sub"][:sub_count]

    # 创建职业
    created_main = []
    created_sub = []

    for template in main_templates + sub_templates:
        # 检查是否已存在
        existing_result = await db.execute(
            select(Career).where(
                Career.project_id == project_id,
                Career.name == template.name
            )
        )
        if existing_result.scalar_one_or_none():
            continue

        career = Career(
            project_id=project_id,
            name=template.name,
            type=template.type,
            description=template.description,
            category=template.category,
            stages=template.stages,
            max_stage=template.max_stage,
            requirements=template.requirements,
            special_abilities=template.special_abilities,
            worldview_rules=template.worldview_rules,
            attribute_bonuses=template.attribute_bonuses,
            base_attributes=template.base_attributes,
            per_stage_bonus=template.per_stage_bonus,
            source="template"
        )
        db.add(career)

        if template.type == "main":
            created_main.append(template.name)
        else:
            created_sub.append(template.name)

    await db.commit()

    logger.info(f"✅ 自动应用模板完成：主职业{len(created_main)}个，副职业{len(created_sub)}个")

    return {
        "message": "自动应用模板完成",
        "main_careers": created_main,
        "sub_careers": created_sub
    }


def _template_to_response(template: CareerTemplate) -> CareerTemplateResponse:
    """将模板对象转换为响应模型"""
    stages = json.loads(template.stages) if template.stages else []
    applicable_genres = json.loads(template.applicable_genres) if template.applicable_genres else []
    attribute_bonuses = json.loads(template.attribute_bonuses) if template.attribute_bonuses else None
    base_attributes = json.loads(template.base_attributes) if template.base_attributes else None
    per_stage_bonus = json.loads(template.per_stage_bonus) if template.per_stage_bonus else None

    return CareerTemplateResponse(
        id=template.id,
        name=template.name,
        type=template.type,
        description=template.description,
        category=template.category,
        applicable_genres=applicable_genres,
        stages=[CareerTemplateStage(**s) for s in stages],
        max_stage=template.max_stage,
        requirements=template.requirements,
        special_abilities=template.special_abilities,
        worldview_rules=template.worldview_rules,
        attribute_bonuses=attribute_bonuses,
        base_attributes=base_attributes,
        per_stage_bonus=per_stage_bonus,
        is_official=template.is_official,
        is_active=template.is_active,
        order_index=template.order_index,
        created_at=template.created_at,
        updated_at=template.updated_at
    )