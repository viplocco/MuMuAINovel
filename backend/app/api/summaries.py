"""章节摘要管理API - 提供摘要的查询、生成、更新等接口"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from typing import Optional, List
from pydantic import BaseModel
from app.database import get_db
from app.models.chapter import Chapter
from app.models.memory import PlotAnalysis
from app.api.common import verify_project_access
from app.services.summary_sync_service import summary_sync_service
from app.services.ai_service import create_user_ai_service
from app.models.settings import Settings
from app.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/summaries", tags=["summaries"])


class SummaryUpdateRequest(BaseModel):
    """摘要更新请求"""
    summary: str


class SummaryResponse(BaseModel):
    """摘要响应"""
    success: bool
    chapter_id: str
    chapter_number: int
    title: str
    summary: Optional[str] = None
    has_content: bool = False  # 章节是否有正文
    has_analysis: bool = False  # 章节是否有分析记录
    summary_source: str = "none"  # 摘要来源: none/planning/analysis/manual
    message: Optional[str] = None


@router.get("/projects/{project_id}/chapters/{chapter_id}")
async def get_chapter_summary(
    project_id: str,
    chapter_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> SummaryResponse:
    """获取章节摘要

    Args:
        project_id: 项目ID
        chapter_id: 章节ID

    Returns:
        章节摘要信息，包含摘要来源判断
    """
    try:
        user_id = getattr(request.state, 'user_id', None)
        await verify_project_access(project_id, user_id, db)

        # 获取章节
        result = await db.execute(
            select(Chapter).where(
                and_(
                    Chapter.id == chapter_id,
                    Chapter.project_id == project_id
                )
            )
        )
        chapter = result.scalar_one_or_none()

        if not chapter:
            raise HTTPException(status_code=404, detail="章节不存在")

        # 检查是否有正文内容
        has_content = bool(chapter.content and chapter.content.strip())

        # 检查是否有分析记录
        analysis_result = await db.execute(
            select(PlotAnalysis).where(PlotAnalysis.chapter_id == chapter_id)
        )
        analysis = analysis_result.scalar_one_or_none()
        has_analysis = bool(analysis)

        # 判断摘要来源
        summary_source = "none"
        if chapter.summary:
            if has_analysis and has_content:
                # 有分析记录且有正文，认为是分析生成的摘要
                summary_source = "analysis"
            elif chapter.expansion_plan:
                # 有规划数据，可能是规划概要
                summary_source = "planning"
            else:
                # 其他情况，可能是手动输入
                summary_source = "manual"

        return SummaryResponse(
            success=True,
            chapter_id=chapter_id,
            chapter_number=chapter.chapter_number,
            title=chapter.title,
            summary=chapter.summary,
            has_content=has_content,
            has_analysis=has_analysis,
            summary_source=summary_source
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取章节摘要失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}")
async def get_project_summaries(
    project_id: str,
    request: Request,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """获取项目的所有章节摘要

    Args:
        project_id: 项目ID
        limit: 最大返回数量

    Returns:
        摘要列表
    """
    try:
        user_id = getattr(request.state, 'user_id', None)
        await verify_project_access(project_id, user_id, db)

        summaries = await summary_sync_service.get_project_summaries(
            db=db,
            project_id=project_id,
            limit=limit
        )

        return {
            "success": True,
            "summaries": summaries,
            "total": len(summaries)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取项目摘要列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/chapters/{chapter_id}/regenerate")
async def regenerate_chapter_summary(
    project_id: str,
    chapter_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """重新生成章节摘要

    通过AI分析章节内容，重新生成摘要。

    Args:
        project_id: 项目ID
        chapter_id: 章节ID

    Returns:
        生成结果
    """
    try:
        user_id = getattr(request.state, 'user_id', None)
        await verify_project_access(project_id, user_id, db)

        # 获取章节信息
        result = await db.execute(
            select(Chapter).where(
                and_(
                    Chapter.id == chapter_id,
                    Chapter.project_id == project_id
                )
            )
        )
        chapter = result.scalar_one_or_none()

        if not chapter:
            raise HTTPException(status_code=404, detail="章节不存在")

        if not chapter.content:
            raise HTTPException(status_code=400, detail="章节内容为空，无法生成摘要")

        # 执行摘要重新生成
        result = await summary_sync_service.regenerate_summary(
            db=db,
            project_id=project_id,
            chapter_id=chapter_id,
            user_id=user_id
        )

        if result.get('success'):
            return {
                "success": True,
                "message": "摘要已重新生成",
                "chapter_id": chapter_id,
                "chapter_number": chapter.chapter_number,
                "title": chapter.title,
                "summary": chapter.summary,
                "stats": result.get('stats')
            }
        else:
            raise HTTPException(status_code=500, detail=result.get('error', "生成失败"))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重新生成摘要失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/projects/{project_id}/chapters/{chapter_id}")
async def update_chapter_summary(
    project_id: str,
    chapter_id: str,
    request: Request,
    body: SummaryUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """手动更新章节摘要

    Args:
        project_id: 项目ID
        chapter_id: 章节ID
        body: 更新请求体

    Returns:
        更新结果
    """
    try:
        user_id = getattr(request.state, 'user_id', None)
        await verify_project_access(project_id, user_id, db)

        # 获取章节信息
        result = await db.execute(
            select(Chapter).where(
                and_(
                    Chapter.id == chapter_id,
                    Chapter.project_id == project_id
                )
            )
        )
        chapter = result.scalar_one_or_none()

        if not chapter:
            raise HTTPException(status_code=404, detail="章节不存在")

        # 执行更新
        update_result = await summary_sync_service.update_summary_manually(
            db=db,
            project_id=project_id,
            chapter_id=chapter_id,
            chapter_number=chapter.chapter_number,
            new_summary=body.summary,
            user_id=user_id
        )

        if update_result.get('success'):
            return {
                "success": True,
                "message": "摘要已更新",
                "chapter_id": chapter_id,
                "chapter_number": chapter.chapter_number,
                "title": chapter.title,
                "summary": chapter.summary,
                "stats": update_result.get('stats')
            }
        else:
            raise HTTPException(status_code=500, detail=update_result.get('error', "更新失败"))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新摘要失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))