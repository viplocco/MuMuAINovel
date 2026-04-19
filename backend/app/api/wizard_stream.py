"""项目创建向导流式API - 使用SSE避免超时"""
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, AsyncGenerator
import json
import re

from app.database import get_db
from app.models.project import Project
from app.models.character import Character
from app.models.outline import Outline
from app.models.chapter import Chapter
from app.models.career import Career, CharacterCareer
from app.models.relationship import CharacterRelationship, Organization, OrganizationMember, RelationshipType
from app.models.writing_style import WritingStyle
from app.models.project_default_style import ProjectDefaultStyle
from app.services.ai_service import AIService
from app.services.prompt_service import prompt_service, PromptService
from app.services.plot_expansion_service import PlotExpansionService
from app.services.json_helper import clean_json_response, safe_parse_json_v3_world_setting
from app.utils.world_setting_helper import normalize_world_setting_data
from app.logger import get_logger
from app.utils.sse_response import SSEResponse, create_sse_response, WizardProgressTracker
from app.api.settings import get_user_ai_service

router = APIRouter(prefix="/wizard-stream", tags=["项目创建向导(流式)"])
logger = get_logger(__name__)


async def world_building_generator(
    data: Dict[str, Any],
    db: AsyncSession,
    user_ai_service: AIService
) -> AsyncGenerator[str, None]:
    """世界构建流式生成器 - V3三阶段渐进生成"""
    # 标记数据库会话是否已提交
    db_committed = False
    # 初始化标准进度追踪器
    tracker = WizardProgressTracker("世界观")

    # V3 三阶段进度配置
    STAGE_CORE_START = 20
    STAGE_CORE_END = 40
    STAGE_EXTENDED_START = 40
    STAGE_EXTENDED_END = 60
    STAGE_FULL_START = 60
    STAGE_FULL_END = 85

    try:
        # 发送开始消息
        yield await tracker.start()

        # 提取参数
        title = data.get("title")
        description = data.get("description")
        theme = data.get("theme")
        genre = data.get("genre")
        narrative_perspective = data.get("narrative_perspective")
        target_words = data.get("target_words")
        chapter_count = data.get("chapter_count")
        character_count = data.get("character_count")
        outline_mode = data.get("outline_mode", "one-to-many")  # 大纲模式，默认一对多
        provider = data.get("provider")
        model = data.get("model")
        enable_mcp = data.get("enable_mcp", True)  # 默认启用MCP
        user_id = data.get("user_id")  # 从中间件注入

        if not title or not description or not theme or not genre:
            yield await tracker.error("title、description、theme 和 genre 是必需的参数", 400)
            return

        # 设置用户信息以启用MCP
        if user_id:
            user_ai_service.user_id = user_id
            user_ai_service.db_session = db

        # ===== 阶段1：核心维度生成 (0-40%) =====
        yield await SSEResponse.send_progress(
            "【阶段1/3】生成核心维度（物理+社会）...",
            STAGE_CORE_START,
            "processing"
        )

        # 获取核心阶段提示词
        template_core = await PromptService.get_template_with_fallback("WORLD_BUILDING_V3_CORE", user_id, db)
        if not template_core:
            yield await tracker.error("核心阶段模板未找到", 500)
            return
        prompt_core = PromptService.format_prompt(
            template_core,
            title=title,
            theme=theme,
            genre=genre or "通用类型",
            description=description or "暂无简介",
            chapter_count=chapter_count or 10,
            narrative_perspective=narrative_perspective or "第三人称"
        )

        MAX_WORLD_RETRIES = 3
        core_json = None

        for retry in range(MAX_WORLD_RETRIES):
            try:
                accumulated_text = ""
                chunk_count = 0

                async for chunk in user_ai_service.generate_text_stream(
                    prompt=prompt_core,
                    provider=provider,
                    model=model,
                    tool_choice="required",
                ):
                    chunk_count += 1
                    accumulated_text += chunk
                    yield await tracker.generating_chunk(chunk)

                    # 阶段内进度更新 (20-40%)
                    progress = STAGE_CORE_START + int((STAGE_CORE_END - STAGE_CORE_START) * min(len(accumulated_text) / 2000, 1.0))
                    if chunk_count % 10 == 0:
                        yield await SSEResponse.send_progress(
                            f"【阶段1/3】生成核心维度... ({len(accumulated_text)}字)",
                            progress,
                            "processing"
                        )
                    if chunk_count % 20 == 0:
                        yield await tracker.heartbeat()

                if not accumulated_text or not accumulated_text.strip():
                    if retry < MAX_WORLD_RETRIES - 1:
                        yield await tracker.retry(retry + 1, MAX_WORLD_RETRIES, "AI返回为空")
                        continue
                    else:
                        raise ValueError("核心阶段多次返回空响应")

                # 解析核心阶段JSON - 使用安全解析函数
                core_json = safe_parse_json_v3_world_setting(accumulated_text)
                if core_json and core_json.get("legacy"):
                    logger.info(f"✅ 核心阶段JSON解析成功（版本: {core_json.get('version')}）")
                else:
                    logger.warning("⚠️ 核心阶段解析部分成功，使用降级数据")
                break

            except Exception as e:
                logger.error(f"❌ 核心阶段JSON解析失败: {e}")
                if retry < MAX_WORLD_RETRIES - 1:
                    yield await tracker.retry(retry + 1, MAX_WORLD_RETRIES, "JSON解析失败")
                    continue
                else:
                    # 最终降级：使用默认结构
                    core_json = safe_parse_json_v3_world_setting("")
                    logger.warning("⚠️ 核心阶段最终降级，使用默认结构")
                    break

        # ===== 阶段1完成：发送核心维度数据 =====
        if core_json:
            # 规范化数据，确保字段结构一致
            from app.utils.world_setting_helper import normalize_world_setting_data
            core_json_normalized = normalize_world_setting_data(core_json)

            # 提取核心维度数据用于前端实时显示
            legacy = core_json_normalized.get("legacy", {})
            physical = core_json_normalized.get("physical", {})
            social = core_json_normalized.get("social", {})
            stage1_data = {
                "time_period": legacy.get("time_period", ""),
                "location": legacy.get("location", ""),
                "atmosphere": legacy.get("atmosphere", ""),
                "rules": legacy.get("rules", ""),
                "physical": physical,
                "social": social,
            }
            yield await tracker.stage_data("核心维度", stage1_data, STAGE_CORE_END)
            logger.info("📤 已发送核心维度数据用于前端实时显示")
            # 更新 core_json 为规范化后的版本
            core_json = core_json_normalized

        # ===== 阶段2：扩展维度生成 (40-60%) =====
        yield await SSEResponse.send_progress(
            "【阶段2/3】生成扩展维度（隐喻+交互）...",
            STAGE_EXTENDED_START,
            "processing"
        )

        extended_json = None
        template_extended = await PromptService.get_template_with_fallback("WORLD_BUILDING_V3_EXTENDED", user_id, db)
        if not template_extended:
            yield await tracker.error("扩展阶段模板未找到", 500)
            return
        prompt_extended = PromptService.format_prompt(
            template_extended,
            core_json=json.dumps(core_json, ensure_ascii=False),
            title=title,
            theme=theme,
            genre=genre or "通用类型"
        )

        for retry in range(MAX_WORLD_RETRIES):
            try:
                accumulated_text = ""
                chunk_count = 0

                async for chunk in user_ai_service.generate_text_stream(
                    prompt=prompt_extended,
                    provider=provider,
                    model=model,
                    tool_choice="required",
                ):
                    chunk_count += 1
                    accumulated_text += chunk
                    yield await tracker.generating_chunk(chunk)

                    # 阶段内进度更新 (40-60%)
                    progress = STAGE_EXTENDED_START + int((STAGE_EXTENDED_END - STAGE_EXTENDED_START) * min(len(accumulated_text) / 1500, 1.0))
                    if chunk_count % 10 == 0:
                        yield await SSEResponse.send_progress(
                            f"【阶段2/3】生成扩展维度... ({len(accumulated_text)}字)",
                            progress,
                            "processing"
                        )
                    if chunk_count % 20 == 0:
                        yield await tracker.heartbeat()

                if not accumulated_text or not accumulated_text.strip():
                    if retry < MAX_WORLD_RETRIES - 1:
                        yield await tracker.retry(retry + 1, MAX_WORLD_RETRIES, "AI返回为空")
                        continue
                    else:
                        # 扩展阶段失败时，使用核心阶段数据继续
                        extended_json = core_json
                        logger.warning("⚠️ 扩展阶段多次返回空响应，使用核心阶段数据")
                        break

                # 解析扩展阶段JSON - 使用安全解析函数
                extended_json = safe_parse_json_v3_world_setting(accumulated_text)
                if extended_json and extended_json.get("metaphor") or extended_json.get("interaction"):
                    logger.info(f"✅ 扩展阶段JSON解析成功")
                else:
                    # 扩展阶段部分失败，合并核心阶段数据
                    if core_json:
                        for key in ["physical", "social", "legacy"]:
                            if key in core_json and key not in extended_json:
                                extended_json[key] = core_json[key]
                    logger.warning("⚠️ 扩展阶段解析部分成功，合并核心阶段数据")
                break

            except Exception as e:
                logger.error(f"❌ 扩展阶段JSON解析失败: {e}")
                if retry < MAX_WORLD_RETRIES - 1:
                    yield await tracker.retry(retry + 1, MAX_WORLD_RETRIES, "JSON解析失败")
                    continue
                else:
                    # 解析失败时，使用核心阶段数据继续
                    extended_json = core_json
                    logger.warning("⚠️ 扩展阶段JSON解析失败，使用核心阶段数据")
                    break

        # ===== 阶段2完成：发送扩展维度数据 =====
        if extended_json:
            # 规范化数据，确保字段结构一致
            from app.utils.world_setting_helper import normalize_world_setting_data
            extended_json_normalized = normalize_world_setting_data(extended_json)

            metaphor = extended_json_normalized.get("metaphor", {})
            interaction = extended_json_normalized.get("interaction", {})
            stage2_data = {
                "metaphor": metaphor,
                "interaction": interaction,
            }
            yield await tracker.stage_data("扩展维度", stage2_data, STAGE_EXTENDED_END)
            logger.info("📤 已发送扩展维度数据用于前端实时显示")
            # 更新 extended_json 为规范化后的版本
            extended_json = extended_json_normalized

        # ===== 阶段3：完整阶段校验 (60-85%) =====
        yield await SSEResponse.send_progress(
            "【阶段3/3】校验一致性并完善...",
            STAGE_FULL_START,
            "processing"
        )

        final_json = None
        template_full = await PromptService.get_template_with_fallback("WORLD_BUILDING_V3_FULL", user_id, db)
        if not template_full:
            yield await tracker.error("完整阶段模板未找到", 500)
            return
        prompt_full = PromptService.format_prompt(
            template_full,
            extended_json=json.dumps(extended_json, ensure_ascii=False),
            title=title,
            theme=theme,
            genre=genre or "通用类型"
        )

        for retry in range(MAX_WORLD_RETRIES):
            try:
                accumulated_text = ""
                chunk_count = 0

                async for chunk in user_ai_service.generate_text_stream(
                    prompt=prompt_full,
                    provider=provider,
                    model=model,
                    tool_choice="required",
                ):
                    chunk_count += 1
                    accumulated_text += chunk
                    yield await tracker.generating_chunk(chunk)

                    # 阶段内进度更新 (60-85%)
                    progress = STAGE_FULL_START + int((STAGE_FULL_END - STAGE_FULL_START) * min(len(accumulated_text) / 1000, 1.0))
                    if chunk_count % 10 == 0:
                        yield await SSEResponse.send_progress(
                            f"【阶段3/3】校验一致性... ({len(accumulated_text)}字)",
                            progress,
                            "processing"
                        )
                    if chunk_count % 20 == 0:
                        yield await tracker.heartbeat()

                if not accumulated_text or not accumulated_text.strip():
                    if retry < MAX_WORLD_RETRIES - 1:
                        yield await tracker.retry(retry + 1, MAX_WORLD_RETRIES, "AI返回为空")
                        continue
                    else:
                        # 完整阶段失败时，使用扩展阶段数据继续
                        final_json = extended_json
                        if final_json:
                            final_json["meta"]["creation_stage"] = "extended"  # 标记为扩展阶段
                        logger.warning("⚠️ 完整阶段多次返回空响应，使用扩展阶段数据")
                        break

                # 解析完整阶段JSON - 使用安全解析函数
                final_json = safe_parse_json_v3_world_setting(accumulated_text)
                if final_json:
                    # 合并扩展阶段数据（确保完整性）
                    if extended_json:
                        for key in ["physical", "social", "metaphor", "interaction"]:
                            if key in extended_json and key not in final_json:
                                final_json[key] = extended_json[key]
                        # 确保 legacy 完整
                        if "legacy" in extended_json and "legacy" in final_json:
                            for legacy_key in ["time_period", "location", "atmosphere", "rules"]:
                                if final_json["legacy"].get(legacy_key) == "未设定":
                                    final_json["legacy"][legacy_key] = extended_json["legacy"].get(legacy_key, "未设定")
                    final_json["meta"]["creation_stage"] = "full"
                    logger.info(f"✅ 完整阶段JSON解析成功")
                else:
                    # 使用扩展阶段数据
                    final_json = extended_json
                    if final_json:
                        final_json["meta"]["creation_stage"] = "extended"
                    logger.warning("⚠️ 完整阶段解析失败，使用扩展阶段数据")
                break

            except Exception as e:
                logger.error(f"❌ 完整阶段JSON解析失败: {e}")
                if retry < MAX_WORLD_RETRIES - 1:
                    yield await tracker.retry(retry + 1, MAX_WORLD_RETRIES, "JSON解析失败")
                    continue
                else:
                    # 解析失败时，使用扩展阶段数据继续
                    final_json = extended_json
                    if final_json:
                        final_json["meta"]["creation_stage"] = "extended"
                    logger.warning("⚠️ 完整阶段JSON解析失败，使用扩展阶段数据")
                    break

        # 确保final_json有效
        if not final_json:
            final_json = core_json if core_json else {
                "version": 2,
                "meta": {"world_name": title, "genre_scale": "中篇", "creation_stage": "core"},
                "physical": {"space": {"key_locations": []}, "time": {"current_period": "未设定"}, "power": {"system_name": "无", "levels": [], "cultivation_method": "无"}},
                "social": {"power_structure": {"hierarchy_rule": "未设定", "key_organizations": []}, "culture": {"values": [], "taboos": []}},
                "metaphor": None,
                "interaction": None,
                "legacy": {"time_period": "生成失败", "location": "生成失败", "atmosphere": "生成失败", "rules": "生成失败"}
            }

        # ===== 保存到数据库 =====
        yield await tracker.saving("保存世界观到数据库...")

        # 确保user_id存在
        if not user_id:
            yield await SSEResponse.send_error("用户ID缺失，无法创建项目", 401)
            return

        # 根据类型初始化能力属性配置
        attribute_schema_json = None
        if genre:
            from app.constants.attribute_definitions import ATTRIBUTE_DEFINITIONS_BY_GENRE, DEFAULT_ATTRIBUTES
            import json as json_module
            genre_schema = ATTRIBUTE_DEFINITIONS_BY_GENRE.get(genre, DEFAULT_ATTRIBUTES)
            attribute_schema_json = json_module.dumps(genre_schema, ensure_ascii=False)

        # 规范化 final_json，确保所有字段都存在
        final_json = normalize_world_setting_data(final_json)

        # 从final_json提取legacy字段（兼容V2/V3结构）
        legacy = final_json.get("legacy", {})
        summary = final_json.get("summary", {})  # V2兼容

        project = Project(
            user_id=user_id,
            title=title,
            description=description,
            theme=theme,
            genre=genre,
            world_time_period=legacy.get("time_period") or summary.get("time_period"),
            world_location=legacy.get("location") or summary.get("location"),
            world_atmosphere=legacy.get("atmosphere") or summary.get("atmosphere"),
            world_rules=legacy.get("rules") or summary.get("rules"),
            world_setting_data=json.dumps(final_json, ensure_ascii=False),
            narrative_perspective=narrative_perspective,
            target_words=target_words,
            chapter_count=chapter_count,
            character_count=character_count,
            outline_mode=outline_mode,
            wizard_status="incomplete",
            wizard_step=1,
            status="planning",
            attribute_schema=attribute_schema_json
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)

        # 自动设置默认写作风格
        try:
            result = await db.execute(
                select(WritingStyle).where(
                    WritingStyle.user_id.is_(None),
                    WritingStyle.order_index == 1
                ).limit(1)
            )
            first_style = result.scalar_one_or_none()

            if first_style:
                default_style = ProjectDefaultStyle(
                    project_id=project.id,
                    style_id=first_style.id
                )
                db.add(default_style)
                await db.commit()
                logger.info(f"为项目 {project.id} 自动设置默认风格: {first_style.name}")
        except Exception as e:
            logger.warning(f"设置默认写作风格失败: {e}")

        project.wizard_step = 1  # type: ignore[reportAttributeAccessIssue]
        await db.commit()

        db_committed = True
        yield await tracker.complete()

        # 发送世界观结果
        physical = final_json.get("physical", {})
        social = final_json.get("social", {})
        key_locations = physical.get("space", {}).get("key_locations", [])
        key_organizations = social.get("power_structure", {}).get("key_organizations", [])

        yield await tracker.result({
            "project_id": project.id,
            "time_period": legacy.get("time_period") or summary.get("time_period"),
            "location": legacy.get("location") or summary.get("location"),
            "atmosphere": legacy.get("atmosphere") or summary.get("atmosphere"),
            "rules": legacy.get("rules") or summary.get("rules"),
            "world_setting_data": json.dumps(final_json, ensure_ascii=False),
            "key_organizations": key_organizations,
            "key_locations": key_locations,
            "creation_stage": final_json.get("meta", {}).get("creation_stage", "core")
        })

        yield await tracker.done()
        logger.info(f"✅ 世界观V3生成完成，项目ID: {project.id}")

    except GeneratorExit:
        logger.warning("世界构建生成器被提前关闭")
        if not db_committed and db.in_transaction():
            await db.rollback()
            logger.info("世界构建事务已回滚")
    except Exception as e:
        logger.error(f"世界构建流式生成失败: {str(e)}")
        if not db_committed and db.in_transaction():
            await db.rollback()
            logger.info("世界构建事务已回滚")
        yield await tracker.error(f"生成失败: {str(e)}")


async def world_building_generator_md(
    data: Dict[str, Any],
    db: AsyncSession,
    user_ai_service: AIService
) -> AsyncGenerator[str, None]:
    """
    世界构建流式生成器 - Markdown单阶段生成版本

    直接生成Markdown格式，支持自动续写机制，避免token超限中断
    """
    from app.utils.markdown_helper import (
        check_markdown_complete,
        get_last_complete_section,
        get_section_outline,
        extract_legacy_from_markdown,
        clean_ai_markdown_output,
        remove_duplicate_content,
        REQUIRED_SECTIONS,
    )

    db_committed = False
    tracker = WizardProgressTracker("世界观")
    MAX_CONTINUE_RETRIES = 3  # 最多续写3次

    try:
        yield await tracker.start()

        # 提取参数
        title = data.get("title")
        description = data.get("description")
        theme = data.get("theme")
        genre = data.get("genre")
        narrative_perspective = data.get("narrative_perspective")
        target_words = data.get("target_words")
        chapter_count = data.get("chapter_count")
        character_count = data.get("character_count")
        outline_mode = data.get("outline_mode", "one-to-many")
        provider = data.get("provider")
        model = data.get("model")
        enable_mcp = data.get("enable_mcp", True)
        user_id = data.get("user_id")

        if not title or not description or not theme or not genre:
            yield await tracker.error("title、description、theme 和 genre 是必需的参数", 400)
            return

        # 设置用户信息以启用MCP
        if user_id:
            user_ai_service.user_id = user_id
            user_ai_service.db_session = db

        # 获取Markdown提示词模板
        template = await PromptService.get_template_with_fallback("WORLD_BUILDING_MARKDOWN", user_id, db)
        if not template:
            yield await tracker.error("Markdown模板未找到", 500)
            return

        prompt = PromptService.format_prompt(
            template,
            title=title,
            theme=theme,
            genre=genre or "通用类型",
            description=description or "暂无简介",
            chapter_count=chapter_count or 10,
            narrative_perspective=narrative_perspective or "第三人称"
        )

        # ===== 单阶段Markdown生成 =====
        yield await SSEResponse.send_progress(
            "正在生成世界观设定（Markdown格式）...",
            20,
            "processing"
        )

        accumulated_markdown = ""
        continue_count = 0

        while continue_count <= MAX_CONTINUE_RETRIES:
            # 构建提示词（首次生成或续写）
            if continue_count == 0:
                current_prompt = prompt
            else:
                # 续写提示词
                continue_template = await PromptService.get_template_with_fallback(
                    "WORLD_BUILDING_MARKDOWN_CONTINUE", user_id, db
                )
                if not continue_template:
                    # 如果续写模板不存在，直接结束
                    logger.warning("续写模板未找到，停止续写")
                    break

                # 获取缺失章节
                is_complete, missing = check_markdown_complete(accumulated_markdown)
                last_section = get_last_complete_section(accumulated_markdown)
                section_outline = get_section_outline(accumulated_markdown)

                current_prompt = PromptService.format_prompt(
                    continue_template,
                    title=title,
                    previous_content_tail=accumulated_markdown[-3000:] if len(accumulated_markdown) > 3000 else accumulated_markdown,
                    last_section=last_section,
                    missing_sections="\n".join(missing),
                    section_outline=section_outline
                )

                yield await SSEResponse.send_progress(
                    f"续写中（第{continue_count}次）...",
                    70 + continue_count * 5,
                    "processing"
                )
                yield await tracker.retry(continue_count, MAX_CONTINUE_RETRIES, "内容不完整，自动续写")

            # 流式生成
            chunk_count = 0
            try:
                async for chunk in user_ai_service.generate_text_stream(
                    prompt=current_prompt,
                    provider=provider,
                    model=model,
                ):
                    chunk_count += 1

                    # 清洗首次生成的chunk（去除AI可能添加的前言）
                    if continue_count == 0 and chunk_count == 1:
                        chunk = clean_ai_markdown_output(chunk)

                    accumulated_markdown += chunk
                    yield await tracker.generating_chunk(chunk)

                    # 进度更新
                    is_complete, missing = check_markdown_complete(accumulated_markdown)
                    if is_complete:
                        progress = 85
                    else:
                        # 根据已完成章节数量计算进度
                        completed_count = len([s for s in REQUIRED_SECTIONS if s in accumulated_markdown])
                        progress = 20 + int(65 * completed_count / len(REQUIRED_SECTIONS))

                    if chunk_count % 20 == 0:
                        yield await SSEResponse.send_progress(
                            f"生成中（{len(accumulated_markdown)}字）...",
                            min(progress, 80),
                            "processing"
                        )
                    if chunk_count % 30 == 0:
                        yield await tracker.heartbeat()

            except Exception as e:
                logger.error(f"生成异常: {e}")
                if continue_count < MAX_CONTINUE_RETRIES:
                    continue_count += 1
                    continue
                else:
                    yield await tracker.error(f"生成失败: {str(e)}")
                    return

            # 检查完整性
            is_complete, missing = check_markdown_complete(accumulated_markdown)
            logger.info(f"生成状态: 完整={is_complete}, 缺失={missing}, 字数={len(accumulated_markdown)}")

            if is_complete:
                break

            # 不完整，需要续写
            continue_count += 1
            if continue_count > MAX_CONTINUE_RETRIES:
                logger.warning(f"达到最大续写次数({MAX_CONTINUE_RETRIES})，停止续写")
                yield await SSEResponse.send_progress(
                    f"生成完成（部分内容可能不完整）",
                    80,
                    "processing"
                )
                break

        # ===== 提取legacy字段 =====
        legacy = extract_legacy_from_markdown(accumulated_markdown)
        logger.info(f"提取的legacy字段: time_period={len(legacy.get('time_period', ''))}字, "
                   f"location={len(legacy.get('location', ''))}字, "
                   f"atmosphere={len(legacy.get('atmosphere', ''))}字, "
                   f"rules={len(legacy.get('rules', ''))}字")

        # ===== 保存到数据库 =====
        yield await tracker.saving("保存世界观到数据库...")

        if not user_id:
            yield await SSEResponse.send_error("用户ID缺失，无法创建项目", 401)
            return

        # 根据类型初始化能力属性配置
        attribute_schema_json = None
        if genre:
            from app.constants.attribute_definitions import ATTRIBUTE_DEFINITIONS_BY_GENRE, DEFAULT_ATTRIBUTES
            import json as json_module
            genre_schema = ATTRIBUTE_DEFINITIONS_BY_GENRE.get(genre, DEFAULT_ATTRIBUTES)
            attribute_schema_json = json_module.dumps(genre_schema, ensure_ascii=False)

        project = Project(
            user_id=user_id,
            title=title,
            description=description,
            theme=theme,
            genre=genre,
            # Legacy 4字段
            world_time_period=legacy.get("time_period", ""),
            world_location=legacy.get("location", ""),
            world_atmosphere=legacy.get("atmosphere", ""),
            world_rules=legacy.get("rules", ""),
            # Markdown格式存储
            world_setting_markdown=accumulated_markdown,
            world_setting_format="markdown",
            narrative_perspective=narrative_perspective,
            target_words=target_words,
            chapter_count=chapter_count,
            character_count=character_count,
            outline_mode=outline_mode,
            wizard_status="incomplete",
            wizard_step=1,
            status="planning",
            attribute_schema=attribute_schema_json
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)

        # 自动设置默认写作风格
        try:
            result = await db.execute(
                select(WritingStyle).where(
                    WritingStyle.user_id.is_(None),
                    WritingStyle.order_index == 1
                ).limit(1)
            )
            first_style = result.scalar_one_or_none()

            if first_style:
                default_style = ProjectDefaultStyle(
                    project_id=project.id,
                    style_id=first_style.id
                )
                db.add(default_style)
                await db.commit()
                logger.info(f"为项目 {project.id} 自动设置默认风格: {first_style.name}")
        except Exception as e:
            logger.warning(f"设置默认写作风格失败: {e}")

        project.wizard_step = 1
        await db.commit()

        db_committed = True
        yield await tracker.complete()

        # 发送结果
        yield await tracker.result({
            "project_id": project.id,
            "time_period": legacy.get("time_period", ""),
            "location": legacy.get("location", ""),
            "atmosphere": legacy.get("atmosphere", ""),
            "rules": legacy.get("rules", ""),
            "world_setting_markdown": accumulated_markdown,
            "world_setting_format": "markdown",
            "continue_count": continue_count,
        })

        yield await tracker.done()
        logger.info(f"✅ 世界观Markdown生成完成，项目ID: {project.id}, 续写次数: {continue_count}")

    except GeneratorExit:
        logger.warning("Markdown生成器被提前关闭")
        if not db_committed and db.in_transaction():
            await db.rollback()
    except Exception as e:
        logger.error(f"Markdown生成失败: {str(e)}")
        if not db_committed and db.in_transaction():
            await db.rollback()
        yield await tracker.error(f"生成失败: {str(e)}")


@router.post("/world-building", summary="流式生成世界构建")
async def generate_world_building_stream(
    request: Request,
    data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    user_ai_service: AIService = Depends(get_user_ai_service)
):
    """
    使用SSE流式生成世界构建，避免超时
    前端使用EventSource接收实时进度和结果
    默认使用Markdown生成，向后兼容JSON格式
    """
    # 从中间件注入user_id到data中
    if hasattr(request.state, 'user_id'):
        data['user_id'] = request.state.user_id

    # 使用Markdown生成器
    return create_sse_response(world_building_generator_md(data, db, user_ai_service))


async def career_system_generator(
    data: Dict[str, Any],
    db: AsyncSession,
    user_ai_service: AIService
) -> AsyncGenerator[str, None]:
    """职业体系生成流式生成器 - 独立接口"""
    db_committed = False
    # 初始化标准进度追踪器
    tracker = WizardProgressTracker("职业体系")
    
    try:
        yield await tracker.start()
        
        # 提取参数
        project_id = data.get("project_id")
        provider = data.get("provider")
        model = data.get("model")
        user_id = data.get("user_id")
        
        if not project_id:
            yield await tracker.error("project_id 是必需的参数", 400)
            return
        
        # 获取项目信息
        yield await tracker.loading("加载项目信息...")
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            yield await tracker.error("项目不存在", 404)
            return
        
        # 设置用户信息以启用MCP
        if user_id:
            user_ai_service.user_id = user_id
            user_ai_service.db_session = db
        
        # 获取世界观数据
        world_data = {
            "time_period": project.world_time_period or "未设定",
            "location": project.world_location or "未设定",
            "atmosphere": project.world_atmosphere or "未设定",
            "rules": project.world_rules or "未设定"
        }

        # 解析项目的属性配置
        attribute_schema_info = ""
        stage_attr_example = ""
        numeric_attr_example = ""

        if project.attribute_schema is not None:  # type: ignore
            try:
                schema = json.loads(project.attribute_schema)  # type: ignore
                attributes = schema.get("attributes", {})
                display_order = schema.get("display_order", list(attributes.keys()))

                stage_attrs = []
                numeric_attrs = []
                combo_attrs = []

                for attr_name in display_order:
                    config = attributes.get(attr_name, {})
                    attr_type = config.get("type", "numeric")

                    if attr_type == "stage":
                        stages = config.get("stages", [])
                        if stages:
                            stage_attrs.append(f"{attr_name}（阶段列表：{', '.join(stages)}）")
                            if not stage_attr_example:
                                stage_attr_example = stages[0] if stages else "第一阶段"
                    elif attr_type == "numeric":
                        min_val = config.get("min", 0)
                        max_val = config.get("max", 100)
                        default_val = config.get("default", 50)
                        numeric_attrs.append(f"{attr_name}（范围：{min_val}-{max_val}，默认：{default_val}）")
                        if not numeric_attr_example:
                            numeric_attr_example = attr_name
                    elif attr_type == "combo_select":
                        elements = list(config.get("elements", {}).keys())
                        max_select = config.get("max_select", 9)
                        if elements:
                            combo_attrs.append(f"{attr_name}（可选元素：{', '.join(elements)}，最多选{max_select}种）")

                if stage_attrs or numeric_attrs or combo_attrs:
                    attribute_schema_info = f"""
能力属性体系：
- 阶段型属性：{'; '.join(stage_attrs) if stage_attrs else '无'}
- 数值型属性：{'; '.join(numeric_attrs) if numeric_attrs else '无'}
- 组合型属性：{'; '.join(combo_attrs) if combo_attrs else '无'}
"""
                    logger.info(f"项目属性配置：阶段型{len(stage_attrs)}个，数值型{len(numeric_attrs)}个，组合型{len(combo_attrs)}个")
            except Exception as e:
                logger.warning(f"解析attribute_schema失败: {e}")

        # 构建动态属性示例
        attr_example_name = numeric_attr_example or "属性名"
        stage_example = stage_attr_example or "第一阶段"

        # 获取职业生成提示词模板（支持用户自定义）
        yield await tracker.preparing("准备AI提示词...")
        template = await PromptService.get_template_with_fallback("CAREER_SYSTEM_GENERATION", user_id, db)
        if not template:
            yield await tracker.error("职业生成模板未找到", 500)
            return
        career_prompt = PromptService.format_prompt(
            template,
            title=project.title,
            genre=project.genre or '未设定',
            theme=project.theme or '未设定',
            description=project.description or '暂无简介',
            time_period=world_data.get('time_period', '未设定'),
            location=world_data.get('location', '未设定'),
            atmosphere=world_data.get('atmosphere', '未设定'),
            rules=world_data.get('rules', '未设定'),
            attribute_schema_info=attribute_schema_info,
            attr_example_name=attr_example_name,
            stage_example=stage_example
        )
        
        estimated_total = 5000
        MAX_CAREER_RETRIES = 3  # 最多重试3次
        career_retry_count = 0
        career_generation_success = False
        
        while career_retry_count < MAX_CAREER_RETRIES and not career_generation_success:
            try:
                # 重试时使用指数退避延迟
                if career_retry_count > 0:
                    delay = min(0.5 * (2 ** career_retry_count), 10.0)  # 0.5, 1, 2, 4, 8, 10秒
                    logger.warning(f"⚠️ 职业体系重试 {career_retry_count}/{MAX_CAREER_RETRIES-1}，等待 {delay}s")
                    await asyncio.sleep(delay)
                    tracker.reset_generating_progress()
                
                yield await tracker.generating(
                    current_chars=0,
                    estimated_total=estimated_total,
                    retry_count=career_retry_count,
                    max_retries=MAX_CAREER_RETRIES
                )

                # 重试时添加格式纠正提示
                current_career_prompt = career_prompt
                if career_retry_count > 0:
                    format_correction = "\n\n【重要格式提醒】上次输出JSON格式有误，请确保：\n1. 使用英文双引号（不是中文引号""''）\n2. 字段间有逗号分隔\n3. 数组和对象正确闭合\n4. 输出纯JSON，不要加markdown标记\n5. 确保JSON完整，不要中途截断"
                    current_career_prompt = career_prompt + format_correction
                    logger.info(f"📝 重试时添加格式纠正提示")

                # 使用流式生成职业体系
                career_response = ""
                chunk_count = 0

                async for chunk in user_ai_service.generate_text_stream(
                    prompt=current_career_prompt,
                    provider=provider,
                    model=model,
                    max_tokens=12000,  # 职业体系JSON需要较大空间，非DeepSeek模型可使用
                ):
                    chunk_count += 1
                    career_response += chunk
                    
                    # 发送内容块
                    yield await tracker.generating_chunk(chunk)
                    
                    # 定期更新进度
                    current_len = len(career_response)
                    if chunk_count % 10 == 0:
                        yield await tracker.generating(
                            current_chars=current_len,
                            estimated_total=estimated_total,
                            retry_count=career_retry_count,
                            max_retries=MAX_CAREER_RETRIES
                        )
                    
                    # 每20个块发送心跳
                    if chunk_count % 20 == 0:
                        yield await tracker.heartbeat()
                
                if not career_response or not career_response.strip():
                    logger.warning(f"⚠️ AI返回空职业体系（尝试{career_retry_count+1}/{MAX_CAREER_RETRIES}）")
                    career_retry_count += 1
                    if career_retry_count < MAX_CAREER_RETRIES:
                        yield await tracker.retry(career_retry_count, MAX_CAREER_RETRIES, "AI返回为空")
                        continue
                    else:
                        yield await tracker.error("职业体系生成失败（AI多次返回为空）")
                        return
                
                # 诊断日志：记录AI原始响应
                logger.warning(f"🔍 AI职业体系响应长度: {len(career_response)} 字符")
                logger.warning(f"🔍 AI职业体系响应结尾200字符: {career_response[-200:] if len(career_response) > 200 else career_response}")
                
                yield await tracker.parsing("解析职业体系数据...")
                
                # 诊断日志：记录AI原始响应
                logger.warning(f"🔍 AI职业体系响应长度: {len(career_response)} 字符")
                logger.warning(f"🔍 AI职业体系响应结尾200字符: {career_response[-200:] if len(career_response) > 200 else career_response}")
                
                yield await tracker.parsing("解析职业体系数据...")
                
                # 清洗并解析JSON
                try:
                    cleaned_response = user_ai_service._clean_json_response(career_response)
                    # 诊断日志：记录清洗后的响应
                    logger.warning(f"🔍 清洗后JSON长度: {len(cleaned_response)} 字符")
                    logger.warning(f"🔍 清洗后JSON结尾200字符: {cleaned_response[-200:] if len(cleaned_response) > 200 else cleaned_response}")
                    career_data = json.loads(cleaned_response)
                    logger.info(f"✅ 职业体系JSON解析成功（尝试{career_retry_count+1}/{MAX_CAREER_RETRIES}）")
                    
                    yield await tracker.saving("保存职业数据...")
                    
                    # 保存主职业
                    main_careers_created = []
                    for idx, career_info in enumerate(career_data.get("main_careers", [])):
                        try:
                            stages_json = json.dumps(career_info.get("stages", []), ensure_ascii=False)

                            # 兼容旧格式 attribute_bonuses
                            attribute_bonuses = career_info.get("attribute_bonuses")
                            attribute_bonuses_json = json.dumps(attribute_bonuses, ensure_ascii=False) if attribute_bonuses else None

                            # 新格式：base_attributes 和 per_stage_bonus
                            base_attributes = career_info.get("base_attributes")
                            base_attributes_json = json.dumps(base_attributes, ensure_ascii=False) if base_attributes else None

                            per_stage_bonus = career_info.get("per_stage_bonus")
                            per_stage_bonus_json = json.dumps(per_stage_bonus, ensure_ascii=False) if per_stage_bonus else None

                            career = Career(
                                project_id=project.id,
                                name=career_info.get("name", f"未命名主职业{idx+1}"),
                                type="main",
                                description=career_info.get("description"),
                                category=career_info.get("category"),
                                stages=stages_json,
                                max_stage=career_info.get("max_stage", 10),
                                requirements=career_info.get("requirements"),
                                special_abilities=career_info.get("special_abilities"),
                                worldview_rules=career_info.get("worldview_rules"),
                                attribute_bonuses=attribute_bonuses_json,
                                base_attributes=base_attributes_json,
                                per_stage_bonus=per_stage_bonus_json,
                                source="ai"
                            )
                            db.add(career)
                            await db.flush()
                            main_careers_created.append(career.name)
                            logger.info(f"  ✅ 创建主职业：{career.name}")
                        except Exception as e:
                            logger.error(f"  ❌ 创建主职业失败：{str(e)}")
                            continue

                    # 保存副职业
                    sub_careers_created = []
                    for idx, career_info in enumerate(career_data.get("sub_careers", [])):
                        try:
                            stages_json = json.dumps(career_info.get("stages", []), ensure_ascii=False)

                            # 兼容旧格式 attribute_bonuses
                            attribute_bonuses = career_info.get("attribute_bonuses")
                            attribute_bonuses_json = json.dumps(attribute_bonuses, ensure_ascii=False) if attribute_bonuses else None

                            # 新格式：base_attributes 和 per_stage_bonus
                            base_attributes = career_info.get("base_attributes")
                            base_attributes_json = json.dumps(base_attributes, ensure_ascii=False) if base_attributes else None

                            per_stage_bonus = career_info.get("per_stage_bonus")
                            per_stage_bonus_json = json.dumps(per_stage_bonus, ensure_ascii=False) if per_stage_bonus else None

                            career = Career(
                                project_id=project.id,
                                name=career_info.get("name", f"未命名副职业{idx+1}"),
                                type="sub",
                                description=career_info.get("description"),
                                category=career_info.get("category"),
                                stages=stages_json,
                                max_stage=career_info.get("max_stage", 5),
                                requirements=career_info.get("requirements"),
                                special_abilities=career_info.get("special_abilities"),
                                worldview_rules=career_info.get("worldview_rules"),
                                attribute_bonuses=attribute_bonuses_json,
                                base_attributes=base_attributes_json,
                                per_stage_bonus=per_stage_bonus_json,
                                source="ai"
                            )
                            db.add(career)
                            await db.flush()
                            sub_careers_created.append(career.name)
                            logger.info(f"  ✅ 创建副职业：{career.name}")
                        except Exception as e:
                            logger.error(f"  ❌ 创建副职业失败：{str(e)}")
                            continue
                    
                    # 更新向导步骤状态为2（职业体系已完成）
                    # wizard_step: 0=未开始, 1=世界观已完成, 2=职业体系已完成, 3=角色已完成, 4=大纲已完成
                    project.wizard_step = 2  # type: ignore[reportAttributeAccessIssue]
                    
                    await db.commit()
                    db_committed = True
                    
                    # 标记成功
                    career_generation_success = True
                    logger.info(f"🎉 职业体系生成完成：主职业{len(main_careers_created)}个，副职业{len(sub_careers_created)}个")
                    
                    yield await tracker.complete()
                    
                    # 发送结果
                    yield await tracker.result({
                        "project_id": project.id,
                        "main_careers_count": len(main_careers_created),
                        "sub_careers_count": len(sub_careers_created),
                        "main_careers": main_careers_created,
                        "sub_careers": sub_careers_created
                    })
                    
                    yield await tracker.done()
                    
                except json.JSONDecodeError as e:
                    logger.error(f"❌ 职业体系JSON解析失败（尝试{career_retry_count+1}/{MAX_CAREER_RETRIES}）: {e}")
                    career_retry_count += 1
                    if career_retry_count < MAX_CAREER_RETRIES:
                        yield await tracker.retry(career_retry_count, MAX_CAREER_RETRIES, "JSON解析失败")
                        continue
                    else:
                        yield await tracker.error("职业体系解析失败（已达最大重试次数）")
                        return
                except Exception as e:
                    logger.error(f"❌ 职业体系保存失败（尝试{career_retry_count+1}/{MAX_CAREER_RETRIES}）: {e}")
                    # 回滚事务以恢复 session 状态
                    try:
                        await db.rollback()
                    except Exception as rb_err:
                        logger.warning(f"回滚失败: {rb_err}")

                    # 检测数据库连接是否失效，尝试重新连接
                    connection_error = False
                    if "connection is closed" in str(e).lower() or "connection refused" in str(e).lower():
                        connection_error = True
                        logger.warning("检测到数据库连接失效，尝试重新连接...")
                        try:
                            # 关闭并重新创建 session
                            await db.close()
                            # 刷新 session 以重新获取连接
                            await db.begin()
                        except Exception as reconnect_err:
                            logger.error(f"重新连接失败: {reconnect_err}")

                    career_retry_count += 1
                    if career_retry_count < MAX_CAREER_RETRIES:
                        yield await tracker.retry(career_retry_count, MAX_CAREER_RETRIES, "保存失败")
                        continue
                    else:
                        yield await tracker.error("职业体系保存失败（已达最大重试次数）")
                        return

            except Exception as e:
                logger.error(f"❌ 职业体系生成异常（尝试{career_retry_count+1}/{MAX_CAREER_RETRIES}）: {e}")
                # 回滚事务以恢复 session 状态
                try:
                    await db.rollback()
                except Exception as rb_err:
                    logger.warning(f"回滚失败: {rb_err}")

                # 检测数据库连接是否失效，尝试重新连接
                connection_error = False
                if "connection is closed" in str(e).lower() or "connection refused" in str(e).lower():
                    connection_error = True
                    logger.warning("检测到数据库连接失效，尝试重新连接...")
                    try:
                        # 关闭并重新创建 session
                        await db.close()
                        # 刷新 session 以重新获取连接
                        await db.begin()
                    except Exception as reconnect_err:
                        logger.error(f"重新连接失败: {reconnect_err}")

                career_retry_count += 1
                if career_retry_count < MAX_CAREER_RETRIES:
                    yield await tracker.retry(career_retry_count, MAX_CAREER_RETRIES, "生成异常")
                    continue
                else:
                    yield await tracker.error(f"职业体系生成失败: {str(e)}")
                    return
        
    except GeneratorExit:
        logger.warning("职业体系生成器被提前关闭")
        if not db_committed and db.in_transaction():
            await db.rollback()
            logger.info("职业体系事务已回滚（GeneratorExit）")
    except Exception as e:
        logger.error(f"职业体系流式生成失败: {str(e)}")
        if not db_committed and db.in_transaction():
            await db.rollback()
            logger.info("职业体系事务已回滚（异常）")
        yield await tracker.error(f"生成失败: {str(e)}")


@router.post("/career-system", summary="流式生成职业体系")
async def generate_career_system_stream(
    request: Request,
    data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    user_ai_service: AIService = Depends(get_user_ai_service)
):
    """
    使用SSE流式生成职业体系，避免超时
    前端使用EventSource接收实时进度和结果
    """
    # 从中间件注入user_id到data中
    if hasattr(request.state, 'user_id'):
        data['user_id'] = request.state.user_id
    
    return create_sse_response(career_system_generator(data, db, user_ai_service))


async def characters_generator(
    data: Dict[str, Any],
    db: AsyncSession,
    user_ai_service: AIService
) -> AsyncGenerator[str, None]:
    """角色批量生成流式生成器 - 优化版:分批+重试+MCP工具增强"""
    db_committed = False
    # 初始化标准进度追踪器
    tracker = WizardProgressTracker("角色")
    
    try:
        yield await tracker.start()
        
        project_id = data.get("project_id")
        count = data.get("count", 5)
        world_context = data.get("world_context")
        theme = data.get("theme", "")
        genre = data.get("genre", "")
        requirements = data.get("requirements", "")
        provider = data.get("provider")
        model = data.get("model")
        enable_mcp = data.get("enable_mcp", True)  # 默认启用MCP
        user_id = data.get("user_id")  # 从中间件注入
        
        # 验证项目
        yield await tracker.loading("验证项目...", 0.3)
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            yield await tracker.error("项目不存在", 404)
            return
        
        project.wizard_step = 2  # type: ignore[reportAttributeAccessIssue]
        
        world_context = world_context or {
            "time_period": project.world_time_period or "未设定",
            "location": project.world_location or "未设定",
            "atmosphere": project.world_atmosphere or "未设定",
            "rules": project.world_rules or "未设定"
        }
        
        # 设置用户信息以启用MCP
        if user_id:
            user_ai_service.user_id = user_id
            user_ai_service.db_session = db
        
        # 获取项目的职业列表，用于角色职业分配
        yield await tracker.loading("加载职业体系...", 0.8)
        career_result = await db.execute(
            select(Career).where(Career.project_id == project_id).order_by(Career.type, Career.id)
        )
        careers = career_result.scalars().all()
        
        main_careers = [c for c in careers if c.type == "main"]  # type: ignore[reportGeneralTypeIssues]
        sub_careers = [c for c in careers if c.type == "sub"]  # type: ignore[reportGeneralTypeIssues]
        
        # 构建职业上下文
        careers_context = ""
        if main_careers or sub_careers:
            careers_context = "\n\n【职业体系】\n"
            if main_careers:
                careers_context += "主职业：\n"
                for career in main_careers:
                    careers_context += f"- {career.name}: {career.description or '暂无描述'}\n"
            if sub_careers:
                careers_context += "\n副职业：\n"
                for career in sub_careers:
                    careers_context += f"- {career.name}: {career.description or '暂无描述'}\n"
            
            careers_context += "\n请为每个角色分配职业：\n"
            careers_context += "- 每个角色必须有1个主职业（从上述主职业中选择）\n"
            careers_context += "- 每个角色可以有0-2个副职业（从上述副职业中选择，可选）\n"
            careers_context += "- 主职业初始阶段建议为1-3\n"
            careers_context += "- 副职业初始阶段建议为1-2\n"
            careers_context += "- 请在返回的JSON中包含 career_assignment 字段：\n"
            careers_context += '  {"main_career": "职业名称", "main_stage": 2, "sub_careers": [{"career": "副职业名称", "stage": 1}]}\n'
            logger.info(f"✅ 加载了{len(main_careers)}个主职业和{len(sub_careers)}个副职业")
        else:
            logger.warning("⚠️ 项目没有职业体系，跳过职业分配")
        
        # 优化的分批策略:每批生成5个,平衡效率和成功率
        BATCH_SIZE = 5  # 每批生成5个角色
        MAX_RETRIES = 3  # 每批最多重试3次
        all_characters = []
        total_batches = (count + BATCH_SIZE - 1) // BATCH_SIZE
        
        for batch_idx in range(total_batches):
            # 精确计算当前批次应该生成的数量
            remaining = count - len(all_characters)
            current_batch_size = min(BATCH_SIZE, remaining)
            
            # 如果已经达到目标数量,直接退出
            if current_batch_size <= 0:
                logger.info(f"已生成{len(all_characters)}个角色,达到目标数量{count}")
                break
            
            batch_progress = 15 + (batch_idx * 60 // total_batches)
            
            # 重试逻辑
            retry_count = 0
            batch_success = False
            batch_error_message = ""

            while retry_count < MAX_RETRIES and not batch_success:
                try:
                    # 重试时使用指数退避延迟
                    if retry_count > 0:
                        delay = min(0.5 * (2 ** retry_count), 10.0)  # 0.5, 1, 2, 4, 8, 10秒
                        logger.warning(f"⚠️ 批次{batch_idx+1}重试 {retry_count}/{MAX_RETRIES-1}，等待 {delay}s")
                        await asyncio.sleep(delay)
                        tracker.reset_generating_progress()
                    
                    yield await tracker.generating(
                        current_chars=0,
                        estimated_total=BATCH_SIZE * 800,
                        message=f"生成第{batch_idx+1}/{total_batches}批角色 ({current_batch_size}个)",
                        retry_count=retry_count,
                        max_retries=MAX_RETRIES
                    )

                    # 构建批次要求 - 包含已生成角色信息保持连贯
                    existing_chars_context = ""
                    if all_characters:
                        existing_chars_context = "\n\n【已生成的角色】:\n"
                        for char in all_characters:
                            existing_chars_context += f"- {char.get('name')}: {char.get('role_type', '未知')}, {char.get('personality', '暂无')[:50]}...\n"
                        existing_chars_context += "\n请确保新角色与已有角色形成合理的关系网络和互动。\n"

                    # 构建精确的批次要求,明确告诉AI要生成的数量
                    if batch_idx == 0:
                        if current_batch_size == 1:
                            batch_requirements = f"{requirements}\n请生成1个主角(protagonist)"
                        else:
                            batch_requirements = f"{requirements}\n请精确生成{current_batch_size}个角色:1个主角(protagonist)和{current_batch_size-1}个核心配角(supporting)"
                    else:
                        batch_requirements = f"{requirements}\n请精确生成{current_batch_size}个角色{existing_chars_context}"
                        if batch_idx == total_batches - 1:
                            batch_requirements += "\n可以包含组织或反派(antagonist)"
                        else:
                            batch_requirements += "\n主要是配角(supporting)和反派(antagonist)"

                    # 获取自定义提示词模板
                    template = await PromptService.get_template_with_fallback("CHARACTERS_BATCH_GENERATION", user_id, db)
                    if not template:
                        yield await tracker.error("角色批量生成模板未找到", 500)
                        return
                    # 构建基础提示词 - 使用 world_setting_markdown
                    world_setting = project.world_setting_markdown or ""
                    if not world_setting:
                        # 兜底：如果没有 world_setting_markdown，拼接分散字段
                        world_setting = f"时间背景：{world_context.get('time_period', '未设定')}\n地理位置：{world_context.get('location', '未设定')}\n氛围基调：{world_context.get('atmosphere', '未设定')}\n世界规则：{world_context.get('rules', '未设定')}"

                    base_prompt = PromptService.format_prompt(
                        template,
                        count=current_batch_size,  # 传递精确数量
                        world_setting=world_setting,
                        theme=theme or project.theme or "",
                        genre=genre or project.genre or "",
                        requirements=batch_requirements + careers_context  # 添加职业上下文
                    )

                    # 重试时添加格式纠正提示
                    prompt = base_prompt
                    if retry_count > 0:
                        format_correction = "\n\n【重要格式提醒】上次输出JSON格式有误，请确保：\n1. 使用英文双引号（不是中文引号""''）\n2. 字段间有逗号分隔\n3. 数组正确闭合（必须有5个对象）\n4. 输出纯JSON数组，不要加markdown标记"
                        prompt = base_prompt + format_correction
                        logger.info(f"📝 批次{batch_idx+1}重试时添加格式纠正提示")

                    # 流式生成（带字数统计）
                    accumulated_text = ""
                    chunk_count = 0

                    estimated_total = BATCH_SIZE * 800

                    async for chunk in user_ai_service.generate_text_stream(
                        prompt=prompt,
                        provider=provider,
                        model=model,
                        max_tokens=12000,  # 角色JSON需要较大空间
                        tool_choice="required",
                    ):
                        chunk_count += 1
                        accumulated_text += chunk
                        
                        # 发送内容块
                        yield await tracker.generating_chunk(chunk)
                        
                        # 定期更新进度
                        current_len = len(accumulated_text)
                        if chunk_count % 10 == 0:
                            yield await tracker.generating(
                                current_chars=current_len,
                                estimated_total=estimated_total,
                                message=f"生成第{batch_idx+1}/{total_batches}批角色中",
                                retry_count=retry_count,
                                max_retries=MAX_RETRIES
                            )
                        
                        # 每20个块发送心跳
                        if chunk_count % 20 == 0:
                            yield await tracker.heartbeat()
                    
                    # 解析批次结果 - 使用统一的JSON清洗方法
                    cleaned_text = user_ai_service._clean_json_response(accumulated_text)
                    characters_data = json.loads(cleaned_text)
                    if not isinstance(characters_data, list):
                        characters_data = [characters_data]
                    
                    # 严格验证生成数量是否精确匹配
                    if len(characters_data) != current_batch_size:
                        error_msg = f"批次{batch_idx+1}生成数量不正确: 期望{current_batch_size}个, 实际{len(characters_data)}个"
                        logger.error(error_msg)
                        
                        # 如果还有重试机会，继续重试
                        if retry_count < MAX_RETRIES - 1:
                            retry_count += 1
                            yield await tracker.retry(retry_count, MAX_RETRIES, error_msg)
                            continue
                        else:
                            # 最后一次重试仍失败，直接返回错误
                            yield await tracker.error(error_msg)
                            return
                    
                    all_characters.extend(characters_data)
                    batch_success = True
                    logger.info(f"批次{batch_idx+1}成功添加{len(characters_data)}个角色,当前总数{len(all_characters)}/{count}")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"批次{batch_idx+1}解析失败(尝试{retry_count+1}/{MAX_RETRIES}): {e}")
                    batch_error_message = f"JSON解析失败: {str(e)}"
                    retry_count += 1
                    if retry_count < MAX_RETRIES:
                        yield await tracker.retry(retry_count, MAX_RETRIES, "JSON解析失败")
                except Exception as e:
                    logger.error(f"批次{batch_idx+1}生成异常(尝试{retry_count+1}/{MAX_RETRIES}): {e}")
                    batch_error_message = f"生成异常: {str(e)}"
                    retry_count += 1
                    if retry_count < MAX_RETRIES:
                        yield await tracker.retry(retry_count, MAX_RETRIES, "生成异常")
            
            # 检查批次是否成功
            if not batch_success:
                error_msg = f"批次{batch_idx+1}在{MAX_RETRIES}次重试后仍然失败"
                if batch_error_message:
                    error_msg += f": {batch_error_message}"
                logger.error(error_msg)
                yield await tracker.error(error_msg)
                return
        
        # 保存到数据库 - 分阶段处理以保证一致性
        yield await tracker.parsing("验证角色数据...")
        
        # 预处理：构建本批次所有实体的名称集合
        valid_entity_names = set()
        valid_organization_names = set()
        
        for char_data in all_characters:
            entity_name = char_data.get("name", "")
            if entity_name:
                valid_entity_names.add(entity_name)
                if char_data.get("is_organization", False):
                    valid_organization_names.add(entity_name)
        
        # 清理幻觉引用
        cleaned_count = 0
        for char_data in all_characters:
            # 清理关系数组中的无效引用
            if "relationships_array" in char_data and isinstance(char_data["relationships_array"], list):
                original_rels = char_data["relationships_array"]
                valid_rels = []
                for rel in original_rels:
                    target_name = rel.get("target_character_name", "")
                    if target_name in valid_entity_names:
                        valid_rels.append(rel)
                    else:
                        cleaned_count += 1
                        logger.debug(f"  🧹 清理无效关系引用：{char_data.get('name')} -> {target_name}")
                char_data["relationships_array"] = valid_rels
            
            # 清理组织成员关系中的无效引用
            if "organization_memberships" in char_data and isinstance(char_data["organization_memberships"], list):
                original_orgs = char_data["organization_memberships"]
                valid_orgs = []
                for org_mem in original_orgs:
                    org_name = org_mem.get("organization_name", "")
                    if org_name in valid_organization_names:
                        valid_orgs.append(org_mem)
                    else:
                        cleaned_count += 1
                        logger.debug(f"  🧹 清理无效组织引用：{char_data.get('name')} -> {org_name}")
                char_data["organization_memberships"] = valid_orgs
        
        if cleaned_count > 0:
            logger.info(f"✨ 清理了{cleaned_count}个AI幻觉引用")
            yield await tracker.parsing(f"已清理{cleaned_count}个无效引用", 0.7)
        
        yield await tracker.saving("保存角色到数据库...")
        
        # 第一阶段：创建所有Character记录
        created_characters = []
        character_name_to_obj = {}  # 名称到对象的映射，用于后续关系创建
        
        for char_data in all_characters:
            # 从relationships_array提取文本描述以保持向后兼容
            relationships_text = ""
            relationships_array = char_data.get("relationships_array", [])
            if relationships_array and isinstance(relationships_array, list):
                # 将关系数组转换为可读文本
                rel_descriptions = []
                for rel in relationships_array:
                    target = rel.get("target_character_name", "未知")
                    rel_type = rel.get("relationship_type", "关系")
                    desc = rel.get("description", "")
                    rel_descriptions.append(f"{target}({rel_type}): {desc}")
                relationships_text = "; ".join(rel_descriptions)
            # 兼容旧格式
            elif isinstance(char_data.get("relationships"), dict):
                relationships_text = json.dumps(char_data.get("relationships"), ensure_ascii=False)
            elif isinstance(char_data.get("relationships"), str):
                relationships_text = char_data.get("relationships")
            
            # 判断是否为组织
            is_organization = char_data.get("is_organization", False)
            
            character = Character(
                project_id=project_id,
                name=char_data.get("name", "未命名角色"),
                age=str(char_data.get("age", "")) if not is_organization else None,
                gender=char_data.get("gender") if not is_organization else None,
                is_organization=is_organization,
                role_type=char_data.get("role_type", "supporting"),
                personality=char_data.get("personality", ""),
                background=char_data.get("background", ""),
                appearance=char_data.get("appearance", ""),
                relationships=relationships_text,
                organization_type=char_data.get("organization_type") if is_organization else None,
                organization_purpose=char_data.get("organization_purpose") if is_organization else None,
                traits=json.dumps(char_data.get("traits", []), ensure_ascii=False) if char_data.get("traits") else None
            )
            db.add(character)
            created_characters.append((character, char_data))
        
        await db.flush()  # 获取所有角色的ID
        
        # 第二阶段：为角色分配职业并创建CharacterCareer关联
        if main_careers or sub_careers:
            yield await tracker.saving("分配角色职业...", 0.3)
            careers_assigned = 0
            
            # 构建职业名称到对象的映射
            career_name_to_obj = {c.name: c for c in careers}
            
            for character, char_data in created_characters:
                # 跳过组织
                if getattr(character, "is_organization", False):
                    continue
                
                try:
                    career_assignment = char_data.get("career_assignment", {})
                    
                    # 分配主职业
                    main_career_name = career_assignment.get("main_career")
                    main_career_stage = career_assignment.get("main_stage", 1)
                    
                    if main_career_name and main_career_name in career_name_to_obj:
                        main_career = career_name_to_obj[main_career_name]
                        
                        # 创建CharacterCareer关联
                        char_career = CharacterCareer(
                            character_id=character.id,
                            career_id=main_career.id,
                            career_type="main",
                            current_stage=min(main_career_stage, main_career.max_stage),
                            stage_progress=0
                        )
                        db.add(char_career)
                        
                        # 更新Character冗余字段
                        character.main_career_id = main_career.id
                        character.main_career_stage = char_career.current_stage
                        
                        careers_assigned += 1
                        logger.info(f"  ✅ 分配主职业：{character.name} -> {main_career.name} (阶段{char_career.current_stage})")
                    else:
                        if main_career_name:
                            logger.warning(f"  ⚠️ 主职业不存在：{character.name} -> {main_career_name}")
                    
                    # 分配副职业
                    sub_career_assignments = career_assignment.get("sub_careers", [])
                    sub_career_list = []
                    
                    for sub_assign in sub_career_assignments[:2]:  # 最多2个副职业
                        sub_career_name = sub_assign.get("career")
                        sub_career_stage = sub_assign.get("stage", 1)
                        
                        if sub_career_name and sub_career_name in career_name_to_obj:
                            sub_career = career_name_to_obj[sub_career_name]
                            
                            # 创建CharacterCareer关联
                            char_career = CharacterCareer(
                                character_id=character.id,
                                career_id=sub_career.id,
                                career_type="sub",
                                current_stage=min(sub_career_stage, sub_career.max_stage),
                                stage_progress=0
                            )
                            db.add(char_career)
                            
                            # 添加到副职业列表
                            sub_career_list.append({
                                "career_id": sub_career.id,
                                "stage": char_career.current_stage
                            })
                            
                            careers_assigned += 1
                            logger.info(f"  ✅ 分配副职业：{character.name} -> {sub_career.name} (阶段{char_career.current_stage})")
                        else:
                            if sub_career_name:
                                logger.warning(f"  ⚠️ 副职业不存在：{character.name} -> {sub_career_name}")
                    
                    # 更新Character冗余字段
                    if sub_career_list:
                        character.sub_careers = json.dumps(sub_career_list, ensure_ascii=False)
                    
                except Exception as e:
                    logger.warning(f"  ❌ 分配职业失败：{character.name} - {str(e)}")
                    continue
            
            await db.flush()
            logger.info(f"💼 职业分配完成：共分配{careers_assigned}个职业")
            yield await tracker.saving(f"已分配{careers_assigned}个职业", 0.4)
        
        # 刷新并建立名称映射
        for character, _ in created_characters:
            await db.refresh(character)
            character_name_to_obj[character.name] = character
            logger.info(f"向导创建角色：{character.name} (ID: {character.id}, 是否组织: {getattr(character, 'is_organization', False)})")
        
        # 第三阶段：为is_organization=True的角色创建Organization记录
        yield await tracker.saving("创建组织记录...", 0.5)
        organization_name_to_obj = {}  # 组织名称到Organization对象的映射
        
        for character, char_data in created_characters:
            if getattr(character, "is_organization", False):
                # 检查是否已存在Organization记录
                org_check = await db.execute(
                    select(Organization).where(Organization.character_id == character.id)
                )
                existing_org = org_check.scalar_one_or_none()
                
                if not existing_org:
                    # 创建Organization记录
                    org = Organization(
                        character_id=character.id,
                        project_id=project_id,
                        member_count=0,  # 初始为0，后续添加成员时会更新
                        power_level=char_data.get("power_level", 50),
                        location=char_data.get("location"),
                        motto=char_data.get("motto"),
                        color=char_data.get("color")
                    )
                    db.add(org)
                    logger.info(f"向导创建组织记录：{character.name}")
                else:
                    org = existing_org
                
                # 建立组织名称映射（无论是新建还是已存在）
                organization_name_to_obj[character.name] = org
        
        await db.flush()  # 确保Organization记录有ID
        
        # 刷新角色以获取ID
        for character, _ in created_characters:
            await db.refresh(character)
        
        # 第四阶段：创建角色间的关系
        yield await tracker.saving("创建角色关系...", 0.7)
        relationships_created = 0
        
        for character, char_data in created_characters:
            # 跳过组织实体的角色关系处理（组织通过成员关系关联）
            if getattr(character, "is_organization", False):
                continue
            
            # 处理relationships数组
            relationships_data = char_data.get("relationships_array", [])
            if not relationships_data and isinstance(char_data.get("relationships"), list):
                relationships_data = char_data.get("relationships")
            
            if relationships_data and isinstance(relationships_data, list):
                for rel in relationships_data:
                    try:
                        target_name = rel.get("target_character_name")
                        if not target_name:
                            logger.debug(f"  ⚠️  {character.name}的关系缺少target_character_name，跳过")
                            continue
                        
                        # 使用名称映射快速查找
                        target_char = character_name_to_obj.get(target_name)
                        
                        if target_char:
                            # 避免创建重复关系
                            existing_rel = await db.execute(
                                select(CharacterRelationship).where(
                                    CharacterRelationship.project_id == project_id,
                                    CharacterRelationship.character_from_id == character.id,
                                    CharacterRelationship.character_to_id == target_char.id
                                )
                            )
                            if existing_rel.scalar_one_or_none():
                                logger.debug(f"  ℹ️  关系已存在：{character.name} -> {target_name}")
                                continue
                            
                            relationship = CharacterRelationship(
                                project_id=project_id,
                                character_from_id=character.id,
                                character_to_id=target_char.id,
                                relationship_name=rel.get("relationship_type", "未知关系"),
                                intimacy_level=rel.get("intimacy_level", 50),
                                description=rel.get("description", ""),
                                started_at=rel.get("started_at"),
                                source="ai"
                            )
                            
                            # 匹配预定义关系类型
                            rel_type_result = await db.execute(
                                select(RelationshipType).where(
                                    RelationshipType.name == rel.get("relationship_type")
                                )
                            )
                            rel_type = rel_type_result.scalar_one_or_none()
                            if rel_type:
                                relationship.relationship_type_id = rel_type.id
                            
                            db.add(relationship)
                            relationships_created += 1
                            logger.info(f"  ✅ 向导创建关系：{character.name} -> {target_name} ({rel.get('relationship_type')})")
                        else:
                            logger.warning(f"  ⚠️  目标角色不存在：{character.name} -> {target_name}（可能是AI幻觉）")
                    except Exception as e:
                        logger.warning(f"  ❌ 向导创建关系失败：{character.name} - {str(e)}")
                        continue
            
        # 第五阶段：创建组织成员关系
        yield await tracker.saving("创建组织成员关系...", 0.9)
        members_created = 0
        
        for character, char_data in created_characters:
            # 跳过组织实体本身
            if getattr(character, "is_organization", False):
                continue
            
            # 处理组织成员关系
            org_memberships = char_data.get("organization_memberships", [])
            if org_memberships and isinstance(org_memberships, list):
                for membership in org_memberships:
                    try:
                        org_name = membership.get("organization_name")
                        if not org_name:
                            logger.debug(f"  ⚠️  {character.name}的组织成员关系缺少organization_name，跳过")
                            continue
                        
                        # 使用映射快速查找组织
                        org = organization_name_to_obj.get(org_name)
                        
                        if org:
                            # 检查是否已存在成员关系
                            existing_member = await db.execute(
                                select(OrganizationMember).where(
                                    OrganizationMember.organization_id == org.id,
                                    OrganizationMember.character_id == character.id
                                )
                            )
                            if existing_member.scalar_one_or_none():
                                logger.debug(f"  ℹ️  成员关系已存在：{character.name} -> {org_name}")
                                continue
                            
                            # 创建成员关系
                            member = OrganizationMember(
                                organization_id=org.id,
                                character_id=character.id,
                                position=membership.get("position", "成员"),
                                rank=membership.get("rank", 0),
                                loyalty=membership.get("loyalty", 50),
                                joined_at=membership.get("joined_at"),
                                status=membership.get("status", "active"),
                                source="ai"
                            )
                            db.add(member)
                            
                            # 更新组织成员计数
                            org.member_count += 1
                            
                            members_created += 1
                            logger.info(f"  ✅ 向导添加成员：{character.name} -> {org_name} ({membership.get('position')})")
                        else:
                            # 这种情况理论上已经被预处理清理了，但保留日志以防万一
                            logger.debug(f"  ℹ️  组织引用已被清理：{character.name} -> {org_name}")
                    except Exception as e:
                        logger.warning(f"  ❌ 向导添加组织成员失败：{character.name} - {str(e)}")
                        continue
        
        logger.info(f"📊 向导数据统计：")
        logger.info(f"  - 创建角色/组织：{len(created_characters)} 个")
        logger.info(f"  - 创建组织详情：{len(organization_name_to_obj)} 个")
        logger.info(f"  - 创建角色关系：{relationships_created} 条")
        logger.info(f"  - 创建组织成员：{members_created} 条")
        
        # 更新项目的角色数量和向导步骤状态为3（角色已完成）
        # wizard_step: 0=未开始, 1=世界观已完成, 2=职业体系已完成, 3=角色已完成, 4=大纲已完成
        project.character_count = len(created_characters)  # type: ignore[reportAttributeAccessIssue]
        project.wizard_step = 3  # type: ignore[reportAttributeAccessIssue]
        logger.info(f"✅ 更新项目角色数量: {project.character_count}")
        
        await db.commit()
        db_committed = True
        
        # 重新提取character对象
        created_characters = [char for char, _ in created_characters]
        
        yield await tracker.complete()
        
        # 发送结果
        yield await tracker.result({
            "message": f"成功生成{len(created_characters)}个角色/组织（分{total_batches}批完成）",
            "count": len(created_characters),
            "batches": total_batches,
            "characters": [
                {
                    "id": char.id,
                    "project_id": char.project_id,
                    "name": char.name,
                    "age": char.age,
                    "gender": char.gender,
                    "is_organization": getattr(char, "is_organization", False),
                    "role_type": char.role_type,
                    "personality": char.personality,
                    "background": char.background,
                    "appearance": char.appearance,
                    "relationships": "",
                    "organization_type": char.organization_type,
                    "organization_purpose": char.organization_purpose,
                    "organization_members": "",
                    "traits": char.traits,
                    "created_at": char.created_at.isoformat() if char.created_at else None,
                    "updated_at": char.updated_at.isoformat() if char.updated_at else None
                } for char in created_characters
            ]
        })
        
        yield await tracker.done()
        
    except GeneratorExit:
        logger.warning("角色生成器被提前关闭")
        if not db_committed and db.in_transaction():
            await db.rollback()
            logger.info("角色生成事务已回滚（GeneratorExit）")
    except Exception as e:
        logger.error(f"角色生成失败: {str(e)}")
        if not db_committed and db.in_transaction():
            await db.rollback()
            logger.info("角色生成事务已回滚（异常）")
        yield await tracker.error(f"生成失败: {str(e)}")


@router.post("/characters", summary="流式批量生成角色")
async def generate_characters_stream(
    request: Request,
    data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    user_ai_service: AIService = Depends(get_user_ai_service)
):
    """
    使用SSE流式批量生成角色，避免超时
    支持MCP工具增强
    """
    # 从中间件注入user_id到data中
    if hasattr(request.state, 'user_id'):
        data['user_id'] = request.state.user_id
    
    return create_sse_response(characters_generator(data, db, user_ai_service))


async def outline_generator(
    data: Dict[str, Any],
    db: AsyncSession,
    user_ai_service: AIService
) -> AsyncGenerator[str, None]:
    """大纲生成流式生成器 - 向导仅生成大纲节点，不展开章节（避免等待过久）"""
    db_committed = False
    # 初始化标准进度追踪器
    tracker = WizardProgressTracker("大纲")
    
    try:
        yield await tracker.start()
        
        project_id = data.get("project_id")
        # 向导固定生成3个大纲节点（不展开）
        outline_count = data.get("chapter_count", 3)
        narrative_perspective = data.get("narrative_perspective")
        target_words = data.get("target_words", 100000)
        requirements = data.get("requirements", "")
        provider = data.get("provider")
        model = data.get("model")
        enable_mcp = data.get("enable_mcp", True)  # 默认启用MCP
        user_id = data.get("user_id")  # 从中间件注入
        
        # 获取项目信息
        yield await tracker.loading("加载项目信息...", 0.3)
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            yield await tracker.error("项目不存在", 404)
            return
        
        # 获取角色信息
        yield await tracker.loading("加载角色信息...", 0.8)
        result = await db.execute(
            select(Character).where(Character.project_id == project_id)
        )
        characters = result.scalars().all()
        
        characters_info = "\n".join([
            f"- {char.name} ({'组织' if getattr(char, 'is_organization', False) else '角色'}, {getattr(char, 'role_type', '')}): {getattr(char, 'personality', '')[:100] if getattr(char, 'personality', None) else '暂无描述'}"
            for char in characters
        ])
        
        # 准备提示词
        yield await tracker.preparing(f"准备生成{outline_count}个大纲节点...")
        
        outline_requirements = f"{requirements}\n\n【重要说明】这是小说的开局部分，请生成{outline_count}个大纲节点，重点关注：\n"
        outline_requirements += "1. 引入主要角色和世界观设定\n"
        outline_requirements += "2. 建立主线冲突和故事钩子\n"
        outline_requirements += "3. 展开初期情节，为后续发展埋下伏笔\n"
        outline_requirements += "4. 不要试图完结故事，这只是开始部分\n"
        outline_requirements += "5. 不要在JSON字符串值中使用中文引号（""''），请使用【】或《》标记\n"
        
        # 获取自定义提示词模板
        template = await PromptService.get_template_with_fallback("OUTLINE_CREATE", user_id, db)
        if not template:
            yield await tracker.error("大纲生成模板未找到", 500)
            return

        # 构建 world_setting - 使用 world_setting_markdown
        world_setting = project.world_setting_markdown or ""
        if not world_setting:
            # 兜底：如果没有 world_setting_markdown，拼接分散字段
            world_setting = f"时间背景：{project.world_time_period or '未设定'}\n地理位置：{project.world_location or '未设定'}\n氛围基调：{project.world_atmosphere or '未设定'}\n世界规则：{project.world_rules or '未设定'}"

        outline_prompt = PromptService.format_prompt(
            template,
            title=project.title,
            theme=project.theme or "未设定",
            genre=project.genre or "通用",
            chapter_count=outline_count,
            narrative_perspective=narrative_perspective,
            target_words=target_words // 10,  # 开局约占总字数的1/10
            world_setting=world_setting,
            characters_info=characters_info or "暂无角色信息",
            mcp_references="",
            requirements=outline_requirements
        )
        
        # 流式生成大纲 - 设置足够大的 max_tokens 避免截断
        estimated_total = 1000
        accumulated_text = ""
        chunk_count = 0

        yield await tracker.generating(current_chars=0, estimated_total=estimated_total)

        async for chunk in user_ai_service.generate_text_stream(
            prompt=outline_prompt,
            provider=provider,
            model=model,
            max_tokens=8000,  # 增加max_tokens避免JSON被截断
        ):
            chunk_count += 1
            accumulated_text += chunk
            
            # 发送内容块
            yield await tracker.generating_chunk(chunk)
            
            # 定期更新进度
            current_len = len(accumulated_text)
            if chunk_count % 10 == 0:
                yield await tracker.generating(
                    current_chars=current_len,
                    estimated_total=estimated_total
                )
            
            # 每20个块发送心跳
            if chunk_count % 20 == 0:
                yield await tracker.heartbeat()
        
        # 解析大纲结果 - 使用统一的JSON清洗方法，添加重试机制
        yield await tracker.parsing("解析大纲数据...")

        MAX_RETRIES = 2
        outline_data = None

        for retry in range(MAX_RETRIES):
            try:
                cleaned_text = user_ai_service._clean_json_response(accumulated_text)
                outline_data = json.loads(cleaned_text)
                if not isinstance(outline_data, list):
                    outline_data = [outline_data]
                logger.info(f"✅ 大纲JSON解析成功（尝试{retry+1}/{MAX_RETRIES}）")
                break
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ 大纲JSON解析失败（尝试{retry+1}/{MAX_RETRIES}): {e}")
                if retry < MAX_RETRIES - 1:
                    # 重试：重新生成大纲
                    yield await tracker.generating(message="重新生成大纲...")
                    accumulated_text = ""
                    async for chunk in user_ai_service.generate_text_stream(
                        prompt=outline_prompt,
                        provider=provider,
                        model=model,
                        max_tokens=8000,
                    ):
                        accumulated_text += chunk
                        yield await tracker.generating_chunk(chunk)
                else:
                    logger.error(f"大纲JSON解析失败，已重试{MAX_RETRIES}次: {e}")
                    yield await tracker.error("大纲生成失败，请重试")
                    return
        
        # 保存大纲到数据库
        yield await tracker.saving("保存大纲到数据库...")
        created_outlines = []
        for index, outline_item in enumerate(outline_data[:outline_count], 1):
            outline = Outline(
                project_id=project_id,
                title=outline_item.get("title", f"第{index}节"),
                content=outline_item.get("summary", outline_item.get("content", "")),
                structure=json.dumps(outline_item, ensure_ascii=False),
                order_index=index
            )
            db.add(outline)
            created_outlines.append(outline)
        
        await db.flush()  # 获取大纲ID
        for outline in created_outlines:
            await db.refresh(outline)
        
        logger.info(f"✅ 成功创建{len(created_outlines)}个大纲节点")
        
        # 🎭 角色校验：检查大纲structure中的characters是否存在对应角色
        yield await tracker.saving("🎭 校验角色信息...", 0.5)
        try:
            from app.services.auto_character_service import get_auto_character_service
            
            auto_char_service = get_auto_character_service(user_ai_service)
            proj_id = str(project_id)
            uid = str(user_id) if user_id is not None else None
            char_check_result = await auto_char_service.check_and_create_missing_characters(
                project_id=proj_id,
                outline_data_list=outline_data[:outline_count],
                db=db,
                user_id=uid,  # type: ignore[reportArgumentType]
                enable_mcp=enable_mcp
            )
            if char_check_result["created_count"] > 0:
                created_names = [c.name for c in char_check_result["created_characters"]]
                logger.info(f"🎭 向导大纲：自动创建了 {char_check_result['created_count']} 个角色: {', '.join(created_names)}")
                yield await tracker.saving(
                    f"🎭 自动创建了 {char_check_result['created_count']} 个角色: {', '.join(created_names)}",
                    0.6
                )
        except Exception as e:
            logger.error(f"⚠️ 向导大纲角色校验失败（不影响主流程）: {e}")
        
        # 🏛️ 组织校验：检查大纲structure中的characters（type=organization）是否存在对应组织
        yield await tracker.saving("🏛️ 校验组织信息...", 0.55)
        try:
            from app.services.auto_organization_service import get_auto_organization_service
            
            auto_org_service = get_auto_organization_service(user_ai_service)
            proj_id = str(project_id)
            uid = str(user_id) if user_id is not None else None
            org_check_result = await auto_org_service.check_and_create_missing_organizations(
                project_id=proj_id,
                outline_data_list=outline_data[:outline_count],
                db=db,
                user_id=uid,  # type: ignore[reportArgumentType]
                enable_mcp=enable_mcp
            )
            if org_check_result["created_count"] > 0:
                created_names = [c.name for c in org_check_result["created_organizations"]]
                logger.info(f"🏛️ 向导大纲：自动创建了 {org_check_result['created_count']} 个组织: {', '.join(created_names)}")
                yield await tracker.saving(
                    f"🏛️ 自动创建了 {org_check_result['created_count']} 个组织: {', '.join(created_names)}",
                    0.65
                )
        except Exception as e:
            logger.error(f"⚠️ 向导大纲组织校验失败（不影响主流程）: {e}")
        
        # 根据项目的大纲模式决定是否自动创建章节
        created_chapters = []
        if getattr(project, "outline_mode", None) == 'one-to-one':
            # 一对一模式：自动为每个大纲创建对应的章节
            yield await tracker.saving("一对一模式：自动创建章节...", 0.7)
            
            for outline in created_outlines:
                chapter = Chapter(
                    project_id=project_id,
                    title=outline.title,
                    content="",  # 空内容，等待用户生成
                    outline_id=None,  # 一对一模式下不关联outline_id
                    chapter_number=outline.order_index,  # 使用chapter_number而不是order_index
                    status="pending"
                )
                db.add(chapter)
                created_chapters.append(chapter)
            
            await db.flush()
            for chapter in created_chapters:
                await db.refresh(chapter)
            
            logger.info(f"✅ 一对一模式：自动创建了{len(created_chapters)}个章节")
            yield await tracker.saving(f"已自动创建{len(created_chapters)}个章节", 0.9)
        else:
            # 一对多模式：跳过自动创建，用户可手动展开
            yield await tracker.saving("细化模式：跳过自动创建章节", 0.9)
            logger.info(f"📝 细化模式：跳过章节创建，用户可在大纲页面手动展开")
        
        # 更新项目信息
        # wizard_step: 0=未开始, 1=世界观已完成, 2=职业体系已完成, 3=角色已完成, 4=大纲已完成
        project.chapter_count = len(created_chapters)  # type: ignore[reportAttributeAccessIssue]  # 记录实际创建的章节数
        project.narrative_perspective = narrative_perspective  # type: ignore[reportAttributeAccessIssue]
        project.target_words = target_words
        project.status = "writing"  # type: ignore[reportAttributeAccessIssue]
        project.wizard_status = "completed"  # type: ignore[reportAttributeAccessIssue]
        project.wizard_step = 4  # type: ignore[reportAttributeAccessIssue]
        
        await db.commit()
        db_committed = True
        
        logger.info(f"📊 向导大纲生成完成：")
        logger.info(f"  - 创建大纲节点：{len(created_outlines)} 个")
        logger.info(f"  - 创建章节：{len(created_chapters)} 个")
        logger.info(f"  - 大纲模式：{getattr(project, 'outline_mode', None)}")
        
        # 构建结果消息
        if getattr(project, "outline_mode", None) == 'one-to-one':
            result_message = f"成功生成{len(created_outlines)}个大纲节点并自动创建{len(created_chapters)}个章节（传统模式）"
            result_note = "已自动创建章节，可直接生成内容"
        else:
            result_message = f"成功生成{len(created_outlines)}个大纲节点（细化模式，可在大纲页面手动展开）"
            result_note = "可在大纲页面展开为多个章节"
        
        yield await tracker.complete()
        
        # 发送结果
        yield await tracker.result({
            "message": result_message,
            "outline_count": len(created_outlines),
            "chapter_count": len(created_chapters),
            "outline_mode": getattr(project, "outline_mode", None),
            "outlines": [
                {
                    "id": outline.id,
                    "order_index": outline.order_index,
                    "title": outline.title,
                    "content": outline.content[:100] + "..." if len(outline.content) > 100 else outline.content,
                    "note": result_note
                } for outline in created_outlines
            ],
            "chapters": [
                {
                    "id": chapter.id,
                    "chapter_number": chapter.chapter_number,
                    "title": chapter.title,
                    "status": chapter.status
                } for chapter in created_chapters
            ] if created_chapters else []
        })
        
        yield await tracker.done()
        
    except GeneratorExit:
        logger.warning("大纲生成器被提前关闭")
        if not db_committed and db.in_transaction():
            await db.rollback()
            logger.info("大纲生成事务已回滚（GeneratorExit）")
    except Exception as e:
        logger.error(f"大纲生成失败: {str(e)}")
        if not db_committed and db.in_transaction():
            await db.rollback()
            logger.info("大纲生成事务已回滚（异常）")
        yield await tracker.error(f"生成失败: {str(e)}")

@router.post("/outline", summary="流式生成完整大纲")
async def generate_outline_stream(
    data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    user_ai_service: AIService = Depends(get_user_ai_service)
):
    """
    使用SSE流式生成完整大纲，避免超时
    """
    return create_sse_response(outline_generator(data, db, user_ai_service))


async def world_building_regenerate_generator_v3(
    project_id: str,
    data: Dict[str, Any],
    db: AsyncSession,
    user_ai_service: AIService
) -> AsyncGenerator[str, None]:
    """世界观重新生成流式生成器 - V3三阶段渐进生成"""
    tracker = WizardProgressTracker("世界观")

    STAGE_CORE_START, STAGE_CORE_END = 20, 40
    STAGE_EXTENDED_START, STAGE_EXTENDED_END = 40, 60
    STAGE_FULL_START, STAGE_FULL_END = 60, 85
    MAX_RETRIES = 3

    try:
        yield await tracker.start("开始重新生成世界观...")
        yield await tracker.loading("加载项目信息...")
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            yield await tracker.error("项目不存在", 404)
            return

        provider = data.get("provider")
        model = data.get("model")
        user_id = data.get("user_id")
        if user_id:
            user_ai_service.user_id = user_id
            user_ai_service.db_session = db

        # ===== 阶段1：核心维度 =====
        yield await SSEResponse.send_progress("【阶段1/3】生成核心维度（物理+社会）...", STAGE_CORE_START, "processing")
        template_core = await PromptService.get_template_with_fallback("WORLD_BUILDING_V3_CORE", user_id, db)
        if not template_core:
            yield await tracker.error("核心阶段模板未找到", 500)
            return
        prompt_core = PromptService.format_prompt(template_core, title=project.title, theme=project.theme or "未设定", genre=project.genre or "通用", description=project.description or "暂无简介", chapter_count=project.chapter_count or 10, narrative_perspective=project.narrative_perspective or "第三人称")

        core_json = None
        for retry in range(MAX_RETRIES):
            try:
                accumulated = ""
                count = 0
                async for chunk in user_ai_service.generate_text_stream(prompt=prompt_core, provider=provider, model=model, tool_choice="required"):
                    count += 1
                    accumulated += chunk
                    if count % 20 == 0:
                        yield await tracker.heartbeat()
                    if count % 40 == 0:
                        progress = min(STAGE_CORE_START + int((STAGE_CORE_END - STAGE_CORE_START) * len(accumulated) / 2000), STAGE_CORE_END - 5)
                        yield await SSEResponse.send_progress(f"【阶段1】生成核心... ({len(accumulated)}字)", progress, "processing")

                if accumulated.strip():
                    core_json = safe_parse_json_v3_world_setting(accumulated)
                    if core_json and core_json.get("legacy"):
                        logger.info(f"✅ 核心阶段解析成功")
                        break
                    else:
                        logger.warning("⚠️ 核心阶段部分成功，继续重试")
                        if retry < MAX_RETRIES - 1:
                            continue
                        else:
                            # 最终降级
                            core_json = safe_parse_json_v3_world_setting("")
                            break
            except Exception as e:
                logger.error(f"❌ 核心阶段异常(retry {retry+1}): {e}")
                if retry < MAX_RETRIES - 1:
                    yield await tracker.retry(retry + 1, MAX_RETRIES, str(e)[:50])
                    continue

        if not core_json:
            # 最终降级：使用默认结构
            core_json = safe_parse_json_v3_world_setting("")
            yield await tracker.retry(MAX_RETRIES, MAX_RETRIES, "使用降级数据继续")
            logger.warning("⚠️ 核心阶段最终降级")

        # ===== 阶段1完成：发送核心维度数据 =====
        if core_json:
            from app.utils.world_setting_helper import normalize_world_setting_data
            core_json_normalized = normalize_world_setting_data(core_json)
            legacy = core_json_normalized.get("legacy", {})
            physical = core_json_normalized.get("physical", {})
            social = core_json_normalized.get("social", {})
            stage1_data = {
                "time_period": legacy.get("time_period", ""),
                "location": legacy.get("location", ""),
                "atmosphere": legacy.get("atmosphere", ""),
                "rules": legacy.get("rules", ""),
                "physical": physical,
                "social": social,
            }
            yield await tracker.stage_data("核心维度", stage1_data, STAGE_CORE_END)
            logger.info("📤 已发送核心维度数据用于前端实时显示")
            core_json = core_json_normalized

        # ===== 阶段2：扩展维度 =====
        yield await SSEResponse.send_progress("【阶段2/3】生成扩展维度（隐喻+交互）...", STAGE_EXTENDED_START, "processing")
        template_extended = await PromptService.get_template_with_fallback("WORLD_BUILDING_V3_EXTENDED", user_id, db)
        if not template_extended:
            yield await tracker.error("扩展阶段模板未找到", 500)
            return
        prompt_extended = PromptService.format_prompt(template_extended, core_json=json.dumps(core_json, ensure_ascii=False), title=project.title, theme=project.theme or "未设定", genre=project.genre or "通用")

        extended_json = None
        for retry in range(MAX_RETRIES):
            try:
                accumulated = ""
                count = 0
                async for chunk in user_ai_service.generate_text_stream(prompt=prompt_extended, provider=provider, model=model, tool_choice="required"):
                    count += 1
                    accumulated += chunk
                    if count % 20 == 0:
                        yield await tracker.heartbeat()
                    if count % 40 == 0:
                        progress = min(STAGE_EXTENDED_START + int((STAGE_EXTENDED_END - STAGE_EXTENDED_START) * len(accumulated) / 1500), STAGE_EXTENDED_END - 5)
                        yield await SSEResponse.send_progress(f"【阶段2】生成扩展... ({len(accumulated)}字)", progress, "processing")

                if accumulated.strip():
                    extended_json = safe_parse_json_v3_world_setting(accumulated)
                    # 检查是否有有效的隐喻/交互数据（非空对象）
                    has_metaphor = extended_json.get("metaphor") and (
                        extended_json.get("metaphor", {}).get("themes", {}).get("core_theme") or
                        extended_json.get("metaphor", {}).get("symbols", {}).get("visual") or
                        extended_json.get("metaphor", {}).get("core_philosophies")
                    )
                    has_interaction = extended_json.get("interaction") and (
                        extended_json.get("interaction", {}).get("cross_rules", {}).get("physical_social") or
                        extended_json.get("interaction", {}).get("evolution", {}).get("time_driven") or
                        extended_json.get("interaction", {}).get("disruption_points")
                    )
                    if extended_json and (has_metaphor or has_interaction):
                        logger.info(f"✅ 扩展阶段解析成功，有隐喻或交互数据")
                        break
                    else:
                        # 合并核心数据
                        if core_json:
                            for key in ["physical", "social", "legacy"]:
                                if key in core_json and key not in extended_json:
                                    extended_json[key] = core_json[key]
                        logger.warning("⚠️ 扩展阶段部分成功，合并核心数据")
                        break
                else:
                    extended_json = core_json
                    logger.warning("⚠️ 扩展阶段返回空，降级使用核心数据")
                    break
            except Exception as e:
                logger.error(f"❌ 扩展阶段异常(retry {retry+1}): {e}")
                if retry < MAX_RETRIES - 1:
                    continue
                extended_json = core_json
                break

        # ===== 阶段2完成：发送扩展维度数据 =====
        if extended_json:
            from app.utils.world_setting_helper import normalize_world_setting_data
            extended_json_normalized = normalize_world_setting_data(extended_json)
            metaphor = extended_json_normalized.get("metaphor", {})
            interaction = extended_json_normalized.get("interaction", {})
            stage2_data = {
                "metaphor": metaphor,
                "interaction": interaction,
            }
            yield await tracker.stage_data("扩展维度", stage2_data, STAGE_EXTENDED_END)
            logger.info("📤 已发送扩展维度数据用于前端实时显示")
            extended_json = extended_json_normalized

        # ===== 阶段3：完整校验 =====
        yield await SSEResponse.send_progress("【阶段3/3】校验一致性并完善...", STAGE_FULL_START, "processing")
        template_full = await PromptService.get_template_with_fallback("WORLD_BUILDING_V3_FULL", user_id, db)
        if not template_full:
            yield await tracker.error("完整阶段模板未找到", 500)
            return
        prompt_full = PromptService.format_prompt(template_full, extended_json=json.dumps(extended_json, ensure_ascii=False), title=project.title, theme=project.theme or "未设定", genre=project.genre or "通用")

        final_json = None
        for retry in range(MAX_RETRIES):
            try:
                accumulated = ""
                count = 0
                async for chunk in user_ai_service.generate_text_stream(prompt=prompt_full, provider=provider, model=model, tool_choice="required"):
                    count += 1
                    accumulated += chunk
                    if count % 20 == 0:
                        yield await tracker.heartbeat()
                    if count % 40 == 0:
                        progress = min(STAGE_FULL_START + int((STAGE_FULL_END - STAGE_FULL_START) * len(accumulated) / 1000), STAGE_FULL_END - 5)
                        yield await SSEResponse.send_progress(f"【阶段3】校验一致性... ({len(accumulated)}字)", progress, "processing")

                if accumulated.strip():
                    final_json = safe_parse_json_v3_world_setting(accumulated)
                    if final_json:
                        # 合并扩展数据（改进：检查是否有有效内容）
                        if extended_json:
                            for key in ["physical", "social"]:
                                if key in extended_json and key not in final_json:
                                    final_json[key] = extended_json[key]
                            # 隐喻维度：如果final为空对象，用extended的值替换
                            if "metaphor" in extended_json:
                                extended_metaphor = extended_json["metaphor"]
                                final_metaphor = final_json.get("metaphor", {})
                                # 检查extended是否有有效内容
                                has_extended_metaphor = (
                                    extended_metaphor.get("themes", {}).get("core_theme") or
                                    extended_metaphor.get("symbols", {}).get("visual") or
                                    extended_metaphor.get("core_philosophies")
                                )
                                # 检查final是否有有效内容
                                has_final_metaphor = (
                                    final_metaphor.get("themes", {}).get("core_theme") or
                                    final_metaphor.get("symbols", {}).get("visual") or
                                    final_metaphor.get("core_philosophies")
                                )
                                if has_extended_metaphor and not has_final_metaphor:
                                    final_json["metaphor"] = extended_metaphor
                                    logger.info("✅ 合并隐喻维度数据")
                            # 交互维度：同样检查是否有有效内容
                            if "interaction" in extended_json:
                                extended_interaction = extended_json["interaction"]
                                final_interaction = final_json.get("interaction", {})
                                has_extended_interaction = (
                                    extended_interaction.get("cross_rules", {}).get("physical_social") or
                                    extended_interaction.get("evolution", {}).get("time_driven") or
                                    extended_interaction.get("disruption_points")
                                )
                                has_final_interaction = (
                                    final_interaction.get("cross_rules", {}).get("physical_social") or
                                    final_interaction.get("evolution", {}).get("time_driven") or
                                    final_interaction.get("disruption_points")
                                )
                                if has_extended_interaction and not has_final_interaction:
                                    final_json["interaction"] = extended_interaction
                                    logger.info("✅ 合并交互维度数据")
                            if "legacy" in extended_json and "legacy" in final_json:
                                for legacy_key in ["time_period", "location", "atmosphere", "rules"]:
                                    if final_json["legacy"].get(legacy_key) == "未设定":
                                        final_json["legacy"][legacy_key] = extended_json["legacy"].get(legacy_key, "未设定")
                        if "meta" in final_json:
                            final_json["meta"]["creation_stage"] = "full"
                        logger.info(f"✅ 完整阶段解析成功")
                        break
                else:
                    final_json = extended_json
                    if final_json and "meta" in final_json:
                        final_json["meta"]["creation_stage"] = "extended"
                    break
            except Exception as e:
                logger.error(f"❌ 完整阶段异常(retry {retry+1}): {e}")
                if retry < MAX_RETRIES - 1:
                    continue
                final_json = extended_json
                if final_json and "meta" in final_json:
                    final_json["meta"]["creation_stage"] = "extended"
                break

        if not final_json:
            final_json = extended_json if extended_json else core_json
            if final_json and "meta" in final_json:
                final_json["meta"]["creation_stage"] = "core"
            else:
                final_json = safe_parse_json_v3_world_setting("")

        # 规范化数据，确保所有字段都存在
        final_json = normalize_world_setting_data(final_json)

        yield await tracker.saving("生成完成...", 0.5)
        yield await tracker.complete()

        legacy = final_json.get("legacy", {})
        physical = final_json.get("physical", {})
        social = final_json.get("social", {})
        yield await tracker.result({
            "time_period": legacy.get("time_period"), "location": legacy.get("location"),
            "atmosphere": legacy.get("atmosphere"), "rules": legacy.get("rules"),
            "world_setting_data": json.dumps(final_json, ensure_ascii=False),
            "key_locations": physical.get("space", {}).get("key_locations", []),
            "key_organizations": social.get("power_structure", {}).get("key_organizations", []),
            "creation_stage": final_json.get("meta", {}).get("creation_stage", "full")
        })
        yield await tracker.done()
        logger.info(f"✅ 世界观V3重新生成完成")
    except Exception as e:
        logger.error(f"重新生成失败: {e}")
        yield await tracker.error(f"生成失败: {str(e)}")


async def world_building_regenerate_generator_md(
    project_id: str,
    data: Dict[str, Any],
    db: AsyncSession,
    user_ai_service: AIService
) -> AsyncGenerator[str, None]:
    """
    世界观重新生成流式生成器 - Markdown单阶段版本

    支持自动续写机制，直接生成Markdown格式
    """
    from app.utils.markdown_helper import (
        check_markdown_complete,
        get_last_complete_section,
        get_section_outline,
        extract_legacy_from_markdown,
        clean_ai_markdown_output,
        REQUIRED_SECTIONS,
    )

    tracker = WizardProgressTracker("世界观")
    MAX_CONTINUE_RETRIES = 3

    try:
        yield await tracker.start("开始重新生成世界观...")
        yield await tracker.loading("加载项目信息...")

        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            yield await tracker.error("项目不存在", 404)
            return

        provider = data.get("provider")
        model = data.get("model")
        user_id = data.get("user_id")

        if user_id:
            user_ai_service.user_id = user_id
            user_ai_service.db_session = db

        # ===== Markdown单阶段生成 =====
        yield await SSEResponse.send_progress(
            "正在重新生成世界观设定...",
            20,
            "processing"
        )

        template = await PromptService.get_template_with_fallback(
            "WORLD_BUILDING_MARKDOWN", user_id, db
        )
        if not template:
            yield await tracker.error("Markdown模板未找到", 500)
            return

        prompt = PromptService.format_prompt(
            template,
            title=project.title,
            theme=project.theme or "未设定",
            genre=project.genre or "通用类型",
            description=project.description or "暂无简介",
            chapter_count=project.chapter_count or 10,
            narrative_perspective=project.narrative_perspective or "第三人称"
        )

        accumulated_markdown = ""
        continue_count = 0

        while continue_count <= MAX_CONTINUE_RETRIES:
            if continue_count == 0:
                current_prompt = prompt
            else:
                # 续写提示词
                continue_template = await PromptService.get_template_with_fallback(
                    "WORLD_BUILDING_MARKDOWN_CONTINUE", user_id, db
                )
                if not continue_template:
                    logger.warning("续写模板未找到，停止续写")
                    break

                is_complete, missing = check_markdown_complete(accumulated_markdown)
                last_section = get_last_complete_section(accumulated_markdown)
                section_outline = get_section_outline(accumulated_markdown)

                current_prompt = PromptService.format_prompt(
                    continue_template,
                    title=project.title,
                    previous_content_tail=accumulated_markdown[-3000:] if len(accumulated_markdown) > 3000 else accumulated_markdown,
                    last_section=last_section,
                    missing_sections="\n".join(missing),
                    section_outline=section_outline
                )

                yield await SSEResponse.send_progress(
                    f"续写中（第{continue_count}次）...",
                    70 + continue_count * 5,
                    "processing"
                )
                yield await tracker.retry(continue_count, MAX_CONTINUE_RETRIES, "内容不完整，自动续写")

            chunk_count = 0
            try:
                async for chunk in user_ai_service.generate_text_stream(
                    prompt=current_prompt,
                    provider=provider,
                    model=model,
                ):
                    chunk_count += 1
                    if continue_count == 0 and chunk_count == 1:
                        chunk = clean_ai_markdown_output(chunk)
                    accumulated_markdown += chunk
                    yield await tracker.generating_chunk(chunk)

                    is_complete, missing = check_markdown_complete(accumulated_markdown)
                    completed_count = len([s for s in REQUIRED_SECTIONS if s in accumulated_markdown])
                    progress = 20 + int(65 * completed_count / len(REQUIRED_SECTIONS))

                    if chunk_count % 20 == 0:
                        yield await SSEResponse.send_progress(
                            f"生成中（{len(accumulated_markdown)}字）...",
                            min(progress, 80),
                            "processing"
                        )
                    if chunk_count % 30 == 0:
                        yield await tracker.heartbeat()

            except Exception as e:
                logger.error(f"重新生成异常: {e}")
                if continue_count < MAX_CONTINUE_RETRIES:
                    continue_count += 1
                    continue
                else:
                    yield await tracker.error(f"生成失败: {str(e)}")
                    return

            is_complete, missing = check_markdown_complete(accumulated_markdown)
            logger.info(f"重新生成状态: 完整={is_complete}, 缺失={missing}")

            if is_complete:
                break

            continue_count += 1
            if continue_count > MAX_CONTINUE_RETRIES:
                logger.warning(f"达到最大续写次数({MAX_CONTINUE_RETRIES})")
                yield await SSEResponse.send_progress(
                    "生成完成（部分内容可能不完整）",
                    80,
                    "processing"
                )
                break

        # ===== 提取legacy字段 =====
        legacy = extract_legacy_from_markdown(accumulated_markdown)

        # ===== 更新项目 =====
        yield await tracker.saving("更新世界观...")

        project.world_time_period = legacy.get("time_period", "")
        project.world_location = legacy.get("location", "")
        project.world_atmosphere = legacy.get("atmosphere", "")
        project.world_rules = legacy.get("rules", "")
        project.world_setting_markdown = accumulated_markdown
        project.world_setting_format = "markdown"
        project.wizard_step = 1
        await db.commit()

        yield await tracker.complete()

        yield await tracker.result({
            "time_period": legacy.get("time_period"),
            "location": legacy.get("location"),
            "atmosphere": legacy.get("atmosphere"),
            "rules": legacy.get("rules"),
            "world_setting_markdown": accumulated_markdown,
            "world_setting_format": "markdown",
            "continue_count": continue_count,
        })
        yield await tracker.done()
        logger.info(f"✅ 世界观Markdown重新生成完成，项目ID: {project_id}")

    except Exception as e:
        logger.error(f"Markdown重新生成失败: {e}")
        yield await tracker.error(f"生成失败: {str(e)}")


@router.post("/world-building/{project_id}/regenerate", summary="流式重新生成世界观")
async def regenerate_world_building_stream(
    project_id: str,
    request: Request,
    data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    user_ai_service: AIService = Depends(get_user_ai_service)
):
    """
    使用SSE流式重新生成世界观，避免超时
    前端使用EventSource接收实时进度和结果
    默认使用Markdown生成
    """
    if hasattr(request.state, 'user_id'):
        data['user_id'] = request.state.user_id
    return create_sse_response(world_building_regenerate_generator_md(project_id, data, db, user_ai_service))
