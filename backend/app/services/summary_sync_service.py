"""章节摘要同步服务 - 管理章节摘要的生成、同步和检索"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from typing import Optional, List, Dict, Any
from app.models.chapter import Chapter
from app.models.memory import StoryMemory
from app.services.memory_service import memory_service
from app.services.plot_analyzer import get_plot_analyzer
from app.services.ai_service import AIService, create_user_ai_service
from app.models.settings import Settings
from app.logger import get_logger
import uuid
import json

logger = get_logger(__name__)


class SummarySyncService:
    """章节摘要同步服务

    负责：
    1. 章节分析后自动生成摘要并同步到 Chapter.summary
    2. 生成摘要类型的 StoryMemory 记录
    3. 支持手动触发摘要重新生成
    4. 查询和检索章节摘要
    """

    async def sync_summary_from_analysis(
        self,
        db: AsyncSession,
        project_id: str,
        chapter_id: str,
        chapter_number: int,
        analysis_result: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """从分析结果同步章节摘要

        Args:
            db: 数据库会话
            project_id: 项目ID
            chapter_id: 章节ID
            chapter_number: 章节号
            analysis_result: 剧情分析结果
            user_id: 用户ID

        Returns:
            同步结果统计
        """
        stats = {"chapter_updated": False, "memory_created": False, "summary_length": 0}

        try:
            # 1. 从分析结果提取摘要
            summary = self._extract_summary_from_analysis(analysis_result)

            if not summary:
                logger.warning(f"未能从分析结果中提取有效摘要: chapter_id={chapter_id}")
                return stats

            # 2. 更新 Chapter.summary
            result = await db.execute(
                select(Chapter).where(Chapter.id == chapter_id)
            )
            chapter = result.scalar_one_or_none()

            if chapter:
                chapter.summary = summary
                stats["chapter_updated"] = True
                stats["summary_length"] = len(summary)
                logger.info(f"已更新章节摘要: 第{chapter_number}章, {len(summary)}字")

            # 3. 创建或更新 StoryMemory 记录（chapter_summary 类型）
            # 先检查是否已存在该章节的摘要记忆
            existing_result = await db.execute(
                select(StoryMemory).where(
                    and_(
                        StoryMemory.project_id == project_id,
                        StoryMemory.chapter_id == chapter_id,
                        StoryMemory.memory_type == 'chapter_summary'
                    )
                )
            )
            existing_memory = existing_result.scalar_one_or_none()

            if existing_memory:
                # 更新现有记录
                existing_memory.content = summary
                existing_memory.importance_score = 0.7
                await memory_service.update_memory(
                    user_id=user_id,
                    project_id=project_id,
                    memory_id=existing_memory.id,
                    content=summary,
                    metadata={
                        'chapter_number': chapter_number,
                        'importance_score': 0.7,
                        'tags': ['章节摘要'],
                        'is_foreshadow': 0
                    }
                )
                logger.info(f"已更新摘要记忆: chapter_id={chapter_id}")
            else:
                # 创建新记录
                memory_id = str(uuid.uuid4())
                memory = StoryMemory(
                    id=memory_id,
                    project_id=project_id,
                    chapter_id=chapter_id,
                    memory_type='chapter_summary',
                    title=f"第{chapter_number}章摘要",
                    content=summary,
                    story_timeline=chapter_number,
                    importance_score=0.7,
                    tags=['章节摘要'],
                    is_foreshadow=0,
                    vector_id=memory_id
                )
                db.add(memory)

                # 同步到向量库
                await memory_service.add_memory(
                    user_id=user_id,
                    project_id=project_id,
                    memory_id=memory_id,
                    content=summary,
                    memory_type='chapter_summary',
                    metadata={
                        'chapter_number': chapter_number,
                        'importance_score': 0.7,
                        'tags': ['章节摘要'],
                        'is_foreshadow': 0
                    }
                )
                stats["memory_created"] = True
                logger.info(f"已创建摘要记忆: chapter_id={chapter_id}, memory_id={memory_id}")

            await db.commit()
            return stats

        except Exception as e:
            logger.error(f"同步章节摘要失败: {str(e)}")
            await db.rollback()
            raise

    def _extract_summary_from_analysis(self, analysis_result: Dict[str, Any]) -> str:
        """从分析结果提取摘要文本

        Args:
            analysis_result: 剧情分析结果

        Returns:
            摘要文本（500字以内）
        """
        parts = []

        # 1. 剧情阶段
        if analysis_result.get('plot_stage'):
            parts.append(f"【剧情阶段】{analysis_result['plot_stage']}")

        # 2. 情感基调
        emotional_arc = analysis_result.get('emotional_arc', {})
        if emotional_arc.get('primary_emotion'):
            intensity = emotional_arc.get('intensity', 5)
            parts.append(f"【情感】{emotional_arc['primary_emotion']}(强度{intensity}/10)")

        # 3. 关键情节点（最重要）
        plot_points = analysis_result.get('plot_points', [])
        if plot_points:
            points_text = "【关键情节】"
            for i, point in enumerate(plot_points[:5]):  # 最多5个关键情节
                importance = point.get('importance', 0)
                if importance >= 0.6:  # 只包含高重要性情节
                    content = point.get('content', '')
                    if content:
                        points_text += f"\n- {content[:80]}"
            if points_text != "【关键情节】":
                parts.append(points_text)

        # 4. 冲突描述
        conflict = analysis_result.get('conflict', {})
        if conflict.get('level') and conflict.get('types'):
            conflict_types = ', '.join(conflict['types'][:3])
            parts.append(f"【冲突】强度{conflict['level']}/10, 类型: {conflict_types}")

        # 5. 角色状态变化
        character_states = analysis_result.get('character_states', [])
        if character_states:
            state_changes = []
            for state in character_states[:3]:  # 最多3个角色
                name = state.get('character_name', '')
                before = state.get('state_before', '')
                after = state.get('state_after', '')
                if name and after:
                    if before:
                        state_changes.append(f"{name}: {before}→{after}")
                    else:
                        state_changes.append(f"{name}: {after}")
            if state_changes:
                parts.append(f"【角色变化】{', '.join(state_changes)}")

        # 6. 伏笔信息
        foreshadows = analysis_result.get('foreshadows', [])
        if foreshadows:
            planted = [f.get('content', '')[:30] for f in foreshadows if f.get('type') == 'planted']
            resolved = [f.get('content', '')[:30] for f in foreshadows if f.get('type') == 'resolved']
            if planted:
                parts.append(f"【埋下伏笔】{', '.join(planted[:2])}")
            if resolved:
                parts.append(f"【回收伏笔】{', '.join(resolved[:2])}")

        # 7. 场景信息
        scenes = analysis_result.get('scenes', [])
        if scenes:
            locations = [s.get('location', '') for s in scenes[:3] if s.get('location')]
            if locations:
                parts.append(f"【场景】{', '.join(locations)}")

        summary = '\n'.join(parts)

        # 限制长度为500字
        if len(summary) > 500:
            summary = summary[:500]

        return summary

    async def regenerate_summary(
        self,
        db: AsyncSession,
        project_id: str,
        chapter_id: str,
        user_id: str,
        ai_service: Optional[AIService] = None
    ) -> Dict[str, Any]:
        """重新生成章节摘要

        Args:
            db: 数据库会话
            project_id: 项目ID
            chapter_id: 章节ID
            user_id: 用户ID
            ai_service: AI服务实例（可选，若不提供则从设置创建）

        Returns:
            生成结果
        """
        try:
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
                return {"success": False, "error": "章节不存在"}

            if not chapter.content:
                return {"success": False, "error": "章节内容为空"}

            # 获取或创建AI服务
            if not ai_service:
                settings_result = await db.execute(select(Settings))
                settings = settings_result.scalar_one_or_none()

                if not settings:
                    return {"success": False, "error": "请先配置AI设置"}

                ai_service = create_user_ai_service(
                    api_provider=settings.api_provider,
                    api_key=settings.api_key,
                    api_base_url=settings.api_base_url,
                    model_name=settings.llm_model,
                    temperature=settings.temperature,
                    max_tokens=settings.max_tokens,
                    user_id=user_id,
                    db_session=db
                )

            # 执行剧情分析
            analyzer = get_plot_analyzer(ai_service)
            analysis_result = await analyzer.analyze_chapter(
                chapter_number=chapter.chapter_number,
                title=chapter.title,
                content=chapter.content,
                word_count=chapter.word_count or len(chapter.content),
                user_id=user_id,
                db=db
            )

            if not analysis_result:
                return {"success": False, "error": "剧情分析失败"}

            # 同步摘要
            stats = await self.sync_summary_from_analysis(
                db=db,
                project_id=project_id,
                chapter_id=chapter_id,
                chapter_number=chapter.chapter_number,
                analysis_result=analysis_result,
                user_id=user_id
            )

            return {
                "success": True,
                "summary": chapter.summary,
                "stats": stats
            }

        except Exception as e:
            logger.error(f"重新生成摘要失败: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_chapter_summary(
        self,
        db: AsyncSession,
        project_id: str,
        chapter_id: str
    ) -> Optional[str]:
        """获取章节摘要

        Args:
            db: 数据库会话
            project_id: 项目ID
            chapter_id: 章节ID

        Returns:
            摘要文本，若无则返回None
        """
        result = await db.execute(
            select(Chapter.summary).where(
                and_(
                    Chapter.id == chapter_id,
                    Chapter.project_id == project_id
                )
            )
        )
        summary = result.scalar_one_or_none()
        return summary

    async def get_project_summaries(
        self,
        db: AsyncSession,
        project_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """获取项目的所有章节摘要

        Args:
            db: 数据库会话
            project_id: 项目ID
            limit: 最大返回数量

        Returns:
            摘要列表
        """
        result = await db.execute(
            select(
                Chapter.id,
                Chapter.chapter_number,
                Chapter.title,
                Chapter.summary
            ).where(
                Chapter.project_id == project_id
            ).where(
                Chapter.summary.isnot(None)  # 只返回有摘要的章节
            ).order_by(desc(Chapter.chapter_number)).limit(limit)
        )

        summaries = []
        for row in result:
            summaries.append({
                "chapter_id": row.id,
                "chapter_number": row.chapter_number,
                "title": row.title,
                "summary": row.summary
            })

        return summaries

    async def update_summary_manually(
        self,
        db: AsyncSession,
        project_id: str,
        chapter_id: str,
        chapter_number: int,
        new_summary: str,
        user_id: str
    ) -> Dict[str, Any]:
        """手动更新章节摘要

        Args:
            db: 数据库会话
            project_id: 项目ID
            chapter_id: 章节ID
            chapter_number: 章节号
            new_summary: 新摘要内容
            user_id: 用户ID

        Returns:
            更新结果
        """
        stats = {"chapter_updated": False, "memory_updated": False}

        try:
            # 限制摘要长度
            if len(new_summary) > 500:
                new_summary = new_summary[:500]

            # 1. 更新 Chapter.summary
            result = await db.execute(
                select(Chapter).where(Chapter.id == chapter_id)
            )
            chapter = result.scalar_one_or_none()

            if chapter:
                chapter.summary = new_summary
                stats["chapter_updated"] = True

            # 2. 更新 StoryMemory
            existing_result = await db.execute(
                select(StoryMemory).where(
                    and_(
                        StoryMemory.project_id == project_id,
                        StoryMemory.chapter_id == chapter_id,
                        StoryMemory.memory_type == 'chapter_summary'
                    )
                )
            )
            existing_memory = existing_result.scalar_one_or_none()

            if existing_memory:
                existing_memory.content = new_summary
                await memory_service.update_memory(
                    user_id=user_id,
                    project_id=project_id,
                    memory_id=existing_memory.id,
                    content=new_summary,
                    metadata={
                        'chapter_number': chapter_number,
                        'importance_score': 0.7,
                        'tags': ['章节摘要'],
                        'is_foreshadow': 0
                    }
                )
                stats["memory_updated"] = True
            else:
                # 创建新记录
                memory_id = str(uuid.uuid4())
                memory = StoryMemory(
                    id=memory_id,
                    project_id=project_id,
                    chapter_id=chapter_id,
                    memory_type='chapter_summary',
                    title=f"第{chapter_number}章摘要",
                    content=new_summary,
                    story_timeline=chapter_number,
                    importance_score=0.7,
                    tags=['章节摘要'],
                    is_foreshadow=0,
                    vector_id=memory_id
                )
                db.add(memory)

                await memory_service.add_memory(
                    user_id=user_id,
                    project_id=project_id,
                    memory_id=memory_id,
                    content=new_summary,
                    memory_type='chapter_summary',
                    metadata={
                        'chapter_number': chapter_number,
                        'importance_score': 0.7,
                        'tags': ['章节摘要'],
                        'is_foreshadow': 0
                    }
                )
                stats["memory_updated"] = True

            await db.commit()
            return {"success": True, "stats": stats}

        except Exception as e:
            logger.error(f"手动更新摘要失败: {str(e)}")
            await db.rollback()
            return {"success": False, "error": str(e)}


# 单例实例
summary_sync_service = SummarySyncService()