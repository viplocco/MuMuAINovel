"""大纲管理API"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from typing import List, AsyncGenerator, Dict, Any, Optional
import json

from app.database import get_db
from app.api.common import verify_project_access
from app.models.outline import Outline
from app.models.project import Project
from app.models.chapter import Chapter
from app.models.character import Character
from app.models.relationship import CharacterRelationship, Organization, OrganizationMember
from app.models.generation_history import GenerationHistory
from app.schemas.outline import (
    OutlineCreate,
    OutlineUpdate,
    OutlineResponse,
    OutlineListResponse,
    OutlineGenerateRequest,
    OutlineExpansionRequest,
    OutlineExpansionResponse,
    BatchOutlineExpansionRequest,
    BatchOutlineExpansionResponse,
    CreateChaptersFromPlansRequest,
    CreateChaptersFromPlansResponse
)
from app.services.ai_service import AIService
from app.services.prompt_service import prompt_service, PromptService
from app.services.memory_service import memory_service
from app.services.plot_expansion_service import PlotExpansionService
from app.services.foreshadow_service import foreshadow_service
from app.services.memory_service import memory_service
from app.logger import get_logger
from app.api.settings import get_user_ai_service
from app.utils.sse_response import SSEResponse, create_sse_response, WizardProgressTracker

router = APIRouter(prefix="/outlines", tags=["大纲管理"])
logger = get_logger(__name__)


def calculate_chapter_type_distribution(outlines: List[Outline]) -> Dict[str, Any]:
    """计算已有大纲的章节类型分布统计（细粒度场景分类）

    Args:
        outlines: 大纲列表

    Returns:
        包含 counts、percentages、total 的字典
    """
    # 扩展场景类型：细粒度分类
    type_counts = {
        # 原有基础类型
        '主线推进': 0, '支线展开': 0, '过渡': 0,
        '小高潮': 0, '大高潮': 0,
        # 细粒度扩展类型
        '人物关系': 0, '感情线': 0, '奇遇事件': 0, '秘境副本': 0,
        '反派视角': 0, '日常互动': 0, '战斗': 0, '修炼成长': 0,
        '势力冲突': 0, '伏笔埋设': 0, '伏笔回收': 0
    }

    for outline in outlines:
        structure = json.loads(outline.structure or '{}')
        types = structure.get('chapter_types', ['主线推进'])
        for type_str in types:
            # 解析类型名称（去除占比部分）
            type_name = type_str.split('(')[0] if '(' in type_str else type_str
            # 类型映射：兼容旧数据并细化
            mapped_type = _map_chapter_type(type_name)
            if mapped_type in type_counts:
                type_counts[mapped_type] += 1

    total = len(outlines)
    return {
        'counts': type_counts,
        'percentages': {k: round(v/total*100, 1) if total > 0 else 0 for k, v in type_counts.items()},
        'total': total
    }


def _map_chapter_type(type_name: str) -> str:
    """将原始类型映射到细粒度类型

    Args:
        type_name: 原始章节类型名称

    Returns:
        映射后的细粒度类型名称
    """
    # 精确匹配映射表
    type_mapping = {
        # 基础类型
        '主线推进': '主线推进',
        '支线展开': '支线展开',
        '过渡': '过渡',
        '小高潮': '小高潮',
        '大高潮': '大高潮',
        # 细粒度类型（直接匹配）
        '人物关系': '人物关系',
        '感情线': '感情线',
        '奇遇事件': '奇遇事件',
        '秘境副本': '秘境副本',
        '反派视角': '反派视角',
        '日常互动': '日常互动',
        '战斗': '战斗',
        '修炼成长': '修炼成长',
        '势力冲突': '势力冲突',
        '伏笔埋设': '伏笔埋设',
        '伏笔回收': '伏笔回收',
    }

    # 模糊匹配：关键词识别
    if type_name in type_mapping:
        return type_mapping[type_name]

    # 关键词匹配（处理 AI 生成的非标准类型）
    keywords_map = [
        (['感情', '恋爱', '情侣', '暧昧', '表白', '分手'], '感情线'),
        (['关系', '人际', '友情', '矛盾', '和解'], '人物关系'),
        (['奇遇', '意外', '偶遇', '惊喜', '机缘'], '奇遇事件'),
        (['秘境', '副本', '探险', '遗迹', '秘洞'], '秘境副本'),
        (['反派', '敌人', '对手', '阴谋', '暗算'], '反派视角'),
        (['日常', '生活', '轻松', '幽默', '温馨'], '日常互动'),
        (['战斗', '打斗', '对决', '比武', '交锋'], '战斗'),
        (['修炼', '成长', '突破', '升级', '变强'], '修炼成长'),
        (['势力', '门派', '组织', '阵营', '帮派'], '势力冲突'),
        (['伏笔埋', '铺垫', '暗示', '埋下'], '伏笔埋设'),
        (['伏笔回', '揭示', '揭晓', '回收'], '伏笔回收'),
        (['高潮', '爆发', '决战', '终局'], '小高潮'),  # 默认归为小高潮
        (['主线', '核心', '主要'], '主线推进'),
    ]

    for keywords, mapped in keywords_map:
        if any(kw in type_name for kw in keywords):
            return mapped

    return '主线推进'  # 默认类型


def generate_rhythm_suggestions(
    current_progress: int,
    total_chapters: int,
    plot_stage: str,
    distribution: Dict[str, Any],
    rhythm_curve: Optional[List[Dict[str, Any]]] = None
) -> str:
    """根据进度和已有分布生成续写节奏建议（基于热门网文节奏规律）

    Args:
        current_progress: 当前已完成的章节数
        total_chapters: 预估总章节数
        plot_stage: 当前情节阶段（development/climax/ending）
        distribution: calculate_chapter_type_distribution 返回的分布统计
        rhythm_curve: 节奏强度曲线数据（用于分析近期节奏变化）

    Returns:
        节奏建议字符串，包含具体策略指导
    """
    suggestions = []
    progress_pct = round(current_progress / total_chapters * 100, 1) if total_chapters > 0 else 0

    # === 热门网文核心节奏规律 ===

    # 1. 黄金三章原则（开头三章必须有吸引点）
    if current_progress < 3:
        suggestions.append("【黄金三章】前三章必须设置悬念或冲突吸引读者")
        suggestions.append("  • 第1章：主角登场+核心冲突/危机引入")
        suggestions.append("  • 第2章：冲突升级+主角决策/行动")
        suggestions.append("  • 第3章：小高潮/转折点+悬念钩子")
    elif current_progress >= 3 and current_progress <= 5:
        # 检查前三章是否有小高潮
        first_three_climax = sum(1 for i in range(min(3, len(rhythm_curve or [])))
                                 if (rhythm_curve or [])[i].get('intensity', 5) >= 7)
        if first_three_climax < 1:
            suggestions.append("【开头优化】前三章缺少高潮点，建议调整增加冲突张力")

    # 2. 波浪式节奏检测（每5-10章应有节奏波）
    if rhythm_curve and len(rhythm_curve) >= 10:
        # 分析最近10章的节奏变化
        recent_10 = rhythm_curve[-10:]
        intensities = [item.get('intensity', 5) for item in recent_10]

        # 检测是否有明显的"波浪"（峰值+低谷交替）
        peaks = sum(1 for i in range(1, len(intensities)-1)
                   if intensities[i] > intensities[i-1] and intensities[i] > intensities[i+1] and intensities[i] >= 7)

        if peaks < 2:
            suggestions.append("【波浪节奏】最近10章缺少节奏起伏，建议规划'铺垫→发展→小高潮→缓冲'波浪")
            suggestions.append("  • 当前节奏过于平缓，读者容易疲劳")
            suggestions.append("  • 建议：下一章设置为过渡/铺垫，后续2章逐步升温至小高潮")

        # 检测节奏是否过于密集（连续高强度）
        high_intensity_streak = 0
        for intensity in intensities:
            if intensity >= 8:
                high_intensity_streak += 1
            else:
                high_intensity_streak = 0
            if high_intensity_streak >= 3:
                suggestions.append("【节奏过密】连续3章以上高强度，建议插入过渡章节调节")
                break

    # 3. 高潮前置铺垫检测
    expected_minor_climax = max(3, total_chapters // 15)  # 每15章一个小高潮（提高密度）
    expected_major_climax = max(2, total_chapters // 40)  # 每40章一个大高潮（提高密度）

    minor_climax_count = distribution['counts'].get('小高潮', 0)
    major_climax_count = distribution['counts'].get('大高潮', 0)

    # 小高潮缺口分析
    if minor_climax_count < expected_minor_climax:
        remaining = expected_minor_climax - minor_climax_count
        remaining_chapters = total_chapters - current_progress
        if remaining > remaining_chapters * 0.3:  # 缺口超过剩余章节30%
            suggestions.append(f"【小高潮缺口】需补充{remaining}个小高潮，建议每3-5章设置一个小高潮节点")
            suggestions.append("  • 小高潮不一定是战斗，可以是：突破、收获、打脸、解谜、关系转折")

    # 大高潮位置检测
    if major_climax_count < expected_major_climax:
        # 根据进度给出具体建议
        if progress_pct < 30:
            suggestions.append(f"【大高潮规划】全书需{expected_major_climax}个大高潮")
            suggestions.append("  • 第一个大高潮建议安排在35%-45%进度")
            suggestions.append("  • 提前3-5章铺垫：引入强敌/危机/资源不足等压力")
        elif 30 <= progress_pct < 50:
            suggestions.append(f"【大高潮时机】当前进度{progress_pct}%，第一个大高潮应在此区间")
            suggestions.append("  • 若尚未设置，建议立即规划：铺垫→冲突升级→高潮爆发")
        elif 50 <= progress_pct < 70:
            suggestions.append(f"【中段大高潮】进度{progress_pct}%，建议设置第二个大高潮")
            suggestions.append("  • 中段大高潮通常是全书最激烈节点，主角面临最大挑战")
        elif progress_pct >= 80:
            suggestions.append(f"【终局大高潮】进度{progress_pct}%，进入最终高潮区间")
            suggestions.append("  • 最终高潮需收束主线+回收核心伏笔+解决终极矛盾")

    # 4. 过渡章节平衡检测
    transition_count = distribution['counts'].get('过渡', 0)
    expected_transition = max(8, total_chapters // 8)  # 每8章一个过渡（调整节奏）

    if transition_count < expected_transition * 0.6:
        suggestions.append(f"【过渡不足】当前过渡章节{transition_count}章，建议增加至{expected_transition}章左右")
        suggestions.append("  • 过渡章节用途：调节节奏、铺垫伏笔、发展支线、角色互动")

    # 5. 支线穿插建议
    side_count = distribution['counts'].get('支线展开', 0)
    expected_side = max(5, total_chapters // 12)

    if side_count < expected_side * 0.5:
        suggestions.append(f"【支线穿插】建议增加支线章节丰富剧情层次")
        suggestions.append("  • 支线类型：感情线、修炼线、友情线、反派视角、世界观探索")

    # 6. 奇遇/秘境分布建议
    encounter_count = distribution['counts'].get('奇遇事件', 0)
    secret_count = distribution['counts'].get('秘境副本', 0)

    # 根据进度给出奇遇建议
    if progress_pct < 20 and (encounter_count + secret_count) < 2:
        suggestions.append("【开局增益】建议在开局阶段安排1-2次奇遇/秘境")
        suggestions.append("  • 作用：快速提升主角实力、引入关键物品/技能")
    elif 20 <= progress_pct < 60 and (encounter_count + secret_count) < 4:
        suggestions.append("【中段奇遇】发展阶段建议安排2-3次奇遇/秘境")
        suggestions.append("  • 作用：获取新能力、推进支线、转换场景节奏")

    # 7. 根据情节阶段给出针对性建议
    if plot_stage == 'climax':
        suggestions.append("【高潮阶段策略】")
        suggestions.append("  • 高潮密度提升：每2-3章一个小高潮节点")
        suggestions.append("  • 高潮前必有铺垫：设置压力/危机/期待感")
        suggestions.append("  • 高潮爆发要点：冲突解决+代价+收获+新悬念")
    elif plot_stage == 'ending':
        suggestions.append("【结局阶段策略】")
        suggestions.append("  • 节奏回落：从高强度过渡到平稳收束")
        suggestions.append("  • 伏笔回收：优先处理核心伏笔，次要伏笔可留悬念")
        suggestions.append("  • 人物归宿：重要角色结局交代")
        suggestions.append("  • 避免仓促：收束要完整，不要急促完结")
    elif plot_stage == 'development':
        # 主线推进占比检测
        main_pct = distribution['percentages'].get('主线推进', 0)
        if main_pct < 35:
            suggestions.append(f"【主线推进】当前占比{main_pct}%偏低，主线推进应占35%-50%")
            suggestions.append("  • 主线推进包括：主角成长、核心矛盾发展、主要目标推进")

        # 检查节奏曲线是否有明显的上升趋势
        if rhythm_curve and len(rhythm_curve) >= 5:
            recent_5_intensities = [item.get('intensity', 5) for item in rhythm_curve[-5:]]
            avg_recent = sum(recent_5_intensities) / len(recent_5_intensities)
            if avg_recent < 5.5:
                suggestions.append("【节奏激活】近期节奏强度偏低，建议设置悬念钩子激活读者期待")

    # 8. 生成综合策略建议（始终添加）
    if not suggestions:
        suggestions.append("【当前节奏良好】保持波浪式节奏继续推进")
        suggestions.append("  • 继续'铺垫→发展→小高潮→缓冲'的波浪模式")
        suggestions.append("  • 注意高潮前铺垫、高潮后缓冲的节奏调节")

    # === 9. 后续5章具体节奏规划（核心新增功能） ===
    next_5_plan = generate_next_5_chapters_plan(
        current_progress, total_chapters, plot_stage, distribution, rhythm_curve
    )
    suggestions.append("")
    suggestions.append("=" * 50)
    suggestions.append("【后续5章节奏规划建议】")
    suggestions.append("=" * 50)
    suggestions.append(f"📊 当前进度：第{current_progress}章 / 预计共{total_chapters}章（{progress_pct}%）")
    suggestions.append("")
    for i, chapter_plan in enumerate(next_5_plan, 1):
        chapter_num = current_progress + i
        suggestions.append(f"📖 第{chapter_num}章：{chapter_plan['title']}")
        suggestions.append(f"   类型：{chapter_plan['types']}")
        suggestions.append(f"   节奏强度：{chapter_plan['intensity']}/10")
        suggestions.append(f"   建议内容：{chapter_plan['content']}")
        suggestions.append(f"   目的：{chapter_plan['purpose']}")
        suggestions.append("")

    return '\n'.join(suggestions)


def generate_next_5_chapters_plan(
    current_progress: int,
    total_chapters: int,
    plot_stage: str,
    distribution: Dict[str, Any],
    rhythm_curve: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """生成后续5章的具体节奏规划（优化版：细粒度场景+优先级修复）

    Args:
        current_progress: 当前已完成的章节数
        total_chapters: 预估总章节数
        plot_stage: 当前情节阶段
        distribution: 章节类型分布统计（含细粒度类型）
        rhythm_curve: 节奏强度曲线数据

    Returns:
        后续5章的规划列表，每章包含 title, types, intensity, content, purpose
    """
    plan = []
    progress_pct = round(current_progress / total_chapters * 100, 1) if total_chapters > 0 else 0

    # === 优化1：增强趋势分析（多维度） ===
    recent_intensity = 5
    recent_type = '主线推进'
    intensity_trend = 'stable'
    volatility = 0  # 波动幅度
    peak_count = 0  # 近期峰值数量

    if rhythm_curve and len(rhythm_curve) >= 3:
        recent = rhythm_curve[-min(10, len(rhythm_curve)):]  # 取最近10章（或更少）
        intensities = [item.get('intensity', 5) for item in recent]

        recent_intensity = intensities[-1]
        recent_type = recent[-1].get('main_type', '主线推进')

        # 计算波动幅度（标准差）
        if len(intensities) > 1:
            avg = sum(intensities) / len(intensities)
            variance = sum((x - avg) ** 2 for x in intensities) / len(intensities)
            volatility = round(variance ** 0.5, 2)

        # 计算峰值数量（局部极大值）
        peak_count = sum(1 for i in range(1, len(intensities)-1)
                        if intensities[i] > intensities[i-1] and intensities[i] > intensities[i+1] and intensities[i] >= 7)

        # 趋势判断：使用最近5章而非3章
        if len(intensities) >= 5:
            last_5 = intensities[-5:]
            # 判断上升/下降趋势（至少3章连续）
            if last_5[-1] > last_5[-2] > last_5[-3]:
                intensity_trend = 'rising'
            elif last_5[-1] < last_5[-2] < last_5[-3]:
                intensity_trend = 'falling'
            else:
                # 检测波动趋势
                if volatility > 2:
                    intensity_trend = 'volatile'  # 高波动
                elif last_5[-1] > last_5[0]:
                    intensity_trend = 'rising_slow'  # 缓慢上升
                elif last_5[-1] < last_5[0]:
                    intensity_trend = 'falling_slow'  # 缓慢下降

    # === 优化2：获取所有统计数据 ===
    counts = distribution['counts']
    minor_climax_count = counts.get('小高潮', 0)
    major_climax_count = counts.get('大高潮', 0)
    transition_count = counts.get('过渡', 0)
    side_count = counts.get('支线展开', 0)
    # 新增：细粒度类型统计
    relationship_count = counts.get('人物关系', 0)
    romance_count = counts.get('感情线', 0)
    adventure_count = counts.get('奇遇事件', 0)
    dungeon_count = counts.get('秘境副本', 0)
    villain_count = counts.get('反派视角', 0)
    daily_count = counts.get('日常互动', 0)
    battle_count = counts.get('战斗', 0)
    growth_count = counts.get('修炼成长', 0)
    foreshadow_plant = counts.get('伏笔埋设', 0)
    foreshadow_resolve = counts.get('伏笔回收', 0)

    # 计算目标数量
    target_minor_climax = max(3, total_chapters // 15)
    target_major_climax = max(2, total_chapters // 40)
    target_transition = max(8, total_chapters // 8)
    target_romance = max(2, total_chapters // 25) if romance_count > 0 else 0  # 有感情线才需要
    target_adventure = max(2, total_chapters // 20)
    target_dungeon = max(1, total_chapters // 30)
    target_villain = max(2, total_chapters // 15)  # 反派视角丰富剧情

    # === 优化3：修复场景判断优先级（按优先级从高到低） ===

    # 【最高优先级】场景0：开局阶段（黄金三章）
    if current_progress < 3:
        plan = [
            {
                'title': '开局定调·主角登场',
                'types': '主线推进',
                'intensity': 6,
                'content': '主角登场+核心设定展示，引入主要矛盾或目标',
                'purpose': '黄金三章第1章：吸引读者，建立期待'
            },
            {
                'title': '冲突引入·矛盾升级',
                'types': '主线推进',
                'intensity': 6,
                'content': '核心冲突具体化，主角面临第一个挑战',
                'purpose': '黄金三章第2章：矛盾升级'
            },
            {
                'title': '开局小高潮',
                'types': '小高潮',
                'intensity': 7,
                'content': '主角应对挑战，展现特质，获得初步收获',
                'purpose': '黄金三章第3章：给读者满足感+悬念'
            },
            {
                'title': '缓冲过渡',
                'types': '过渡 / 主线推进',
                'intensity': 4,
                'content': '消化收获，展开世界观，引入新线索',
                'purpose': '调节节奏，铺垫后续'
            },
            {
                'title': '新悬念钩子',
                'types': '主线推进 / 奇遇事件',
                'intensity': 5,
                'content': '引入新目标或奇遇，设置中长期悬念',
                'purpose': '激活读者期待，开启主线发展'
            }
        ]

    # 【次高优先级】场景1：结局阶段
    elif plot_stage == 'ending' or progress_pct >= 85:
        plan = [
            {
                'title': '收束准备',
                'types': '主线推进',
                'intensity': 5,
                'content': '回顾核心矛盾，准备最终解决，收束次要线索',
                'purpose': '结局阶段铺垫'
            },
            {
                'title': '伏笔回收',
                'types': '主线推进',
                'intensity': 5,
                'content': '回收核心伏笔，揭示关键真相',
                'purpose': '完成故事闭环'
            },
            {
                'title': '最终高潮',
                'types': '大高潮',
                'intensity': 9,
                'content': '最终决战/解决：核心矛盾终结，主角完成蜕变',
                'purpose': '全书最高潮点'
            },
            {
                'title': '收尾过渡',
                'types': '过渡',
                'intensity': 4,
                'content': '战后收尾，人物归宿交代',
                'purpose': '节奏回落'
            },
            {
                'title': '结局收束',
                'types': '过渡',
                'intensity': 3,
                'content': '全书收尾，留白或暗示后续',
                'purpose': '完整结局'
            }
        ]

    # 场景5：高潮阶段
    elif plot_stage == 'climax':
        plan = [
            {
                'title': '高潮铺垫',
                'types': '主线推进',
                'intensity': 6,
                'content': '强化紧张感，矛盾激化，压力叠加',
                'purpose': '高潮阶段前奏'
            },
            {
                'title': '节奏急升',
                'types': '主线推进',
                'intensity': 7,
                'content': '冲突全面爆发，主角被迫应对',
                'purpose': '进入高潮区间'
            },
            {
                'title': '高潮节点',
                'types': '小高潮',
                'intensity': 8,
                'content': '阶段性突破或转折',
                'purpose': '高潮阶段波峰'
            },
            {
                'title': '短暂缓冲',
                'types': '过渡',
                'intensity': 5,
                'content': '短暂喘息，处理紧急事宜',
                'purpose': '调节节奏'
            },
            {
                'title': '继续高潮',
                'types': '小高潮 / 主线推进',
                'intensity': 7,
                'content': '高潮延续，向大高潮推进',
                'purpose': '维持高潮区间'
            }
        ]

    # 【细粒度场景】场景2：刚刚经历高潮，需要回落缓冲
    elif recent_intensity >= 8 or intensity_trend == 'falling':
        plan = [
            {
                'title': '节奏回落·缓冲过渡',
                'types': '过渡 / 日常互动',
                'intensity': 3,
                'content': '主角消化高潮收获，处理后续事宜，与伙伴交流反思',
                'purpose': '调节节奏，让读者喘息，为下波铺垫'
            },
            {
                'title': '伏笔收束·支线展开',
                'types': '支线展开 / 人物关系',
                'intensity': 4,
                'content': '展开未处理的支线，发展人物关系，埋下新伏笔',
                'purpose': '丰富剧情层次，利用缓冲期发展次要线索'
            },
            {
                'title': '新压力酝酿',
                'types': '主线推进',
                'intensity': 5,
                'content': '引入新的压力源：敌人动向、资源短缺、新任务',
                'purpose': '开始新一轮节奏波，设置悬念钩子'
            },
            {
                'title': '压力升级',
                'types': '主线推进 / 战斗',
                'intensity': 6,
                'content': '压力逐步升级，主角开始行动应对，小冲突爆发',
                'purpose': '节奏上升，制造紧张感'
            },
            {
                'title': '小高潮节点',
                'types': '小高潮',
                'intensity': 7,
                'content': '阶段性突破或收获，解决当前小矛盾，留下新悬念',
                'purpose': '完成节奏波峰，给读者满足感'
            }
        ]

    # 【细粒度场景】场景3：感情线缺口明显时
    elif romance_count > 0 and romance_count < target_romance * 0.6 and progress_pct >= 15:
        plan = [
            {
                'title': '感情线铺垫',
                'types': '感情线 / 人物关系',
                'intensity': 4,
                'content': '增加主角与重要角色的互动场景，展现情感张力',
                'purpose': '铺垫感情发展，丰富人物关系'
            },
            {
                'title': '日常互动',
                'types': '日常互动 / 感情线',
                'intensity': 3,
                'content': '轻松的日常场景，展现角色性格和互动方式',
                'purpose': '调节节奏，增加感情线厚度'
            },
            {
                'title': '情感冲突',
                'types': '感情线 / 人物关系',
                'intensity': 5,
                'content': '引入情感矛盾或误会，推动感情线发展',
                'purpose': '感情线小高潮，制造期待'
            },
            {
                'title': '主线推进',
                'types': '主线推进',
                'intensity': 6,
                'content': '回归主线，引入新挑战',
                'purpose': '节奏回升'
            },
            {
                'title': '小高潮',
                'types': '小高潮',
                'intensity': 7,
                'content': '主线突破+感情线收获双线小高潮',
                'purpose': '节奏波峰，双线满足'
            }
        ]

    # 【细粒度场景】场景4：反派视角缺失时
    elif villain_count < target_villain * 0.4 and progress_pct >= 20:
        plan = [
            {
                'title': '反派视角',
                'types': '反派视角',
                'intensity': 4,
                'content': '切换视角展示反派动向，揭示其阴谋或动机',
                'purpose': '丰富叙事视角，增加悬念和威胁感'
            },
            {
                'title': '反派行动',
                'types': '反派视角 / 势力冲突',
                'intensity': 5,
                'content': '反派势力采取行动，制造新压力',
                'purpose': '为后续高潮铺垫'
            },
            {
                'title': '主角应对',
                'types': '主线推进',
                'intensity': 6,
                'content': '主角察觉威胁，开始应对准备',
                'purpose': '节奏升温'
            },
            {
                'title': '小冲突',
                'types': '战斗 / 小高潮',
                'intensity': 7,
                'content': '主角与反派势力小规模交锋',
                'purpose': '小高潮，展示实力差距'
            },
            {
                'title': '缓冲过渡',
                'types': '过渡',
                'intensity': 4,
                'content': '战后反思，情报分析，准备下一波',
                'purpose': '节奏回落'
            }
        ]

    # 【细粒度场景】场景5：奇遇事件不足时（增加惊喜感）
    elif adventure_count < target_adventure * 0.5 and progress_pct >= 10:
        plan = [
            {
                'title': '奇遇触发',
                'types': '奇遇事件',
                'intensity': 5,
                'content': '意外事件触发：发现遗迹、偶遇关键人物、获得线索',
                'purpose': '增加惊喜元素，打破节奏单调'
            },
            {
                'title': '奇遇探索',
                'types': '奇遇事件 / 主线推进',
                'intensity': 6,
                'content': '主角探索奇遇带来的新机遇，获得收获',
                'purpose': '小高潮，给读者满足感'
            },
            {
                'title': '收获消化',
                'types': '修炼成长 / 过渡',
                'intensity': 4,
                'content': '主角消化奇遇收获，实力提升或获得新能力',
                'purpose': '成长阶段，调节节奏'
            },
            {
                'title': '新压力引入',
                'types': '主线推进',
                'intensity': 5,
                'content': '奇遇带来新麻烦，引发新矛盾',
                'purpose': '开始新节奏波'
            },
            {
                'title': '节奏升温',
                'types': '主线推进',
                'intensity': 6,
                'content': '矛盾发展，主角行动应对',
                'purpose': '节奏上升'
            }
        ]

    # 【细粒度场景】场景6：秘境副本不足时
    elif dungeon_count < target_dungeon * 0.5 and progress_pct >= 25:
        plan = [
            {
                'title': '秘境开启',
                'types': '秘境副本',
                'intensity': 5,
                'content': '秘境/副本入口开启，主角进入探险',
                'purpose': '切换场景，增加探险元素'
            },
            {
                'title': '秘境探索',
                'types': '秘境副本 / 战斗',
                'intensity': 6,
                'content': '秘境内部探索，遭遇怪物或机关',
                'purpose': '节奏升温'
            },
            {
                'title': '秘境高潮',
                'types': '战斗 / 小高潮',
                'intensity': 7,
                'content': '秘境核心挑战，主角突破难关获得收获',
                'purpose': '小高潮，探险满足感'
            },
            {
                'title': '秘境收尾',
                'types': '过渡 / 修炼成长',
                'intensity': 4,
                'content': '离开秘境，消化收获，分析情报',
                'purpose': '节奏回落'
            },
            {
                'title': '回归主线',
                'types': '主线推进',
                'intensity': 5,
                'content': '秘境收获带来主线变化',
                'purpose': '开启新节奏'
            }
        ]

    # 【细粒度场景】场景7：处于铺垫阶段，需要升温（大高潮或小高潮）
    elif recent_intensity <= 5 and intensity_trend in ['stable', 'rising', 'rising_slow']:
        # 判断是否需要大高潮
        need_major_climax = False
        if progress_pct >= 30 and progress_pct <= 50 and major_climax_count == 0:
            need_major_climax = True
        elif progress_pct >= 55 and progress_pct <= 70 and major_climax_count < 2:
            need_major_climax = True

        if need_major_climax:
            plan = [
                {
                    'title': '危机酝酿·铺垫',
                    'types': '过渡 / 主线推进',
                    'intensity': 5,
                    'content': '引入重大威胁：强敌出现、核心矛盾激化、资源危机',
                    'purpose': '大高潮前铺垫，制造强烈期待感'
                },
                {
                    'title': '压力叠加',
                    'types': '主线推进',
                    'intensity': 6,
                    'content': '多线压力汇聚，主角陷入困境，决策困难',
                    'purpose': '升级紧张感，为大高潮蓄势'
                },
                {
                    'title': '冲突爆发',
                    'types': '主线推进 / 小高潮',
                    'intensity': 7,
                    'content': '核心冲突爆发，主角被迫应对，局势失控',
                    'purpose': '节奏急升，进入高潮区间'
                },
                {
                    'title': '大高潮',
                    'types': '大高潮',
                    'intensity': 9,
                    'content': '全书最激烈节点：生死决战、重大突破、核心矛盾解决',
                    'purpose': '给读者最大满足感，完成节奏波峰'
                },
                {
                    'title': '高潮收尾',
                    'types': '主线推进',
                    'intensity': 6,
                    'content': '处理战后事宜，收获总结，揭示新目标',
                    'purpose': '大高潮收束，开启下阶段'
                }
            ]
        else:
            # 普通小高潮节奏波
            plan = [
                {
                    'title': '继续铺垫',
                    'types': '主线推进',
                    'intensity': 5,
                    'content': '稳步推进主线，可穿插小事件或人物互动',
                    'purpose': '维持当前节奏，积累张力'
                },
                {
                    'title': '压力引入',
                    'types': '主线推进',
                    'intensity': 5,
                    'content': '引入新压力或矛盾点，设置悬念钩子',
                    'purpose': '开始升温，制造期待感'
                },
                {
                    'title': '节奏上升',
                    'types': '主线推进',
                    'intensity': 6,
                    'content': '矛盾发展，主角行动，局势变化',
                    'purpose': '节奏上升阶段'
                },
                {
                    'title': '小高潮',
                    'types': '小高潮',
                    'intensity': 7,
                    'content': '阶段性突破：获得收获、解决小矛盾、打脸反转',
                    'purpose': '节奏波峰，给读者满足感'
                },
                {
                    'title': '缓冲回落',
                    'types': '过渡',
                    'intensity': 4,
                    'content': '处理后续，消化收获，准备下一波',
                    'purpose': '节奏回落，调节节奏'
                }
            ]

    # 场景8：过渡章节不足时
    elif transition_count < target_transition * 0.5:
        plan = [
            {
                'title': '过渡缓冲',
                'types': '过渡',
                'intensity': 3,
                'content': '节奏调节章节：日常互动、反思沉淀、世界观展示',
                'purpose': '补充过渡章节，调节节奏'
            },
            {
                'title': '支线发展',
                'types': '支线展开',
                'intensity': 4,
                'content': '发展次要线索：人物关系、支线任务',
                'purpose': '利用缓冲期丰富剧情'
            },
            {
                'title': '铺垫回升',
                'types': '主线推进',
                'intensity': 5,
                'content': '引入新压力，设置悬念',
                'purpose': '开始新节奏波'
            },
            {
                'title': '节奏上升',
                'types': '主线推进',
                'intensity': 6,
                'content': '矛盾发展，主角行动',
                'purpose': '节奏升温'
            },
            {
                'title': '小高潮',
                'types': '小高潮',
                'intensity': 7,
                'content': '阶段性突破或收获',
                'purpose': '节奏波峰'
            }
        ]

    # 场景9：小高潮缺口明显时
    elif minor_climax_count < target_minor_climax * 0.7:
        plan = [
            {
                'title': '压力引入',
                'types': '主线推进',
                'intensity': 5,
                'content': '引入新矛盾或挑战',
                'purpose': '为小高潮铺垫'
            },
            {
                'title': '压力升级',
                'types': '主线推进',
                'intensity': 6,
                'content': '矛盾激化，主角开始应对',
                'purpose': '节奏升温'
            },
            {
                'title': '小高潮',
                'types': '小高潮',
                'intensity': 7,
                'content': '阶段性突破：战斗胜利、获得收获、解决矛盾',
                'purpose': '补充小高潮节点'
            },
            {
                'title': '缓冲过渡',
                'types': '过渡',
                'intensity': 4,
                'content': '消化收获，处理后续',
                'purpose': '节奏回落'
            },
            {
                'title': '新悬念',
                'types': '主线推进',
                'intensity': 5,
                'content': '引入新目标或线索',
                'purpose': '开启下一波'
            }
        ]

    # 默认场景：标准波浪节奏
    else:
        plan = [
            {
                'title': '稳健推进',
                'types': '主线推进',
                'intensity': 5,
                'content': '稳步推进主线，可穿插人物互动或世界观展示',
                'purpose': '维持节奏'
            },
            {
                'title': '铺垫升温',
                'types': '主线推进',
                'intensity': 5,
                'content': '引入新压力或矛盾，设置悬念钩子',
                'purpose': '开始升温'
            },
            {
                'title': '节奏上升',
                'types': '主线推进',
                'intensity': 6,
                'content': '矛盾发展，主角行动，局势变化',
                'purpose': '节奏上升'
            },
            {
                'title': '小高潮',
                'types': '小高潮',
                'intensity': 7,
                'content': '阶段性突破或收获',
                'purpose': '节奏波峰'
            },
            {
                'title': '缓冲回落',
                'types': '过渡',
                'intensity': 4,
                'content': '处理后续，消化收获',
                'purpose': '节奏回落'
            }
        ]

    return plan


def format_distribution_for_prompt(distribution: Dict[str, Any]) -> str:
    """将分布统计格式化为提示词中的字符串

    Args:
        distribution: calculate_chapter_type_distribution 返回的分布统计

    Returns:
        格式化的字符串，用于插入提示词
    """
    lines = []
    for type_name, count in distribution['counts'].items():
        pct = distribution['percentages'].get(type_name, 0)
        lines.append(f"- {type_name}: {count}章 ({pct}%)")
    return '\n'.join(lines)


def get_rhythm_curve_data(outlines: List[Outline]) -> List[Dict[str, Any]]:
    """从大纲列表提取节奏强度曲线数据

    Args:
        outlines: 按 order_index 排序的大纲列表

    Returns:
        节奏强度曲线数据列表，每项包含 {index, title, intensity, types}
    """
    curve_data = []
    for outline in outlines:
        structure = json.loads(outline.structure or '{}')
        intensity = structure.get('rhythm_intensity', 5)  # 默认中等强度
        types = structure.get('chapter_types', ['主线推进'])
        # 解析主类型（取第一个或占比最大的）
        main_type = types[0] if types else '主线推进'
        if '(' in main_type:
            main_type = main_type.split('(')[0]

        curve_data.append({
            'index': outline.order_index,
            'title': outline.title,
            'intensity': intensity,
            'main_type': main_type,
            'all_types': types
        })
    return curve_data


def calculate_distribution_from_chapters(chapters: List[Chapter]) -> Dict[str, Any]:
    """从已展开章节计算章节类型分布统计（细粒度场景分类）

    Args:
        chapters: 章节列表（已按 chapter_number 排序）

    Returns:
        包含 counts、percentages、total 的字典
    """
    # 扩展场景类型：细粒度分类（与大纲版本保持一致）
    type_counts = {
        # 原有基础类型
        '主线推进': 0, '支线展开': 0, '过渡': 0,
        '小高潮': 0, '大高潮': 0,
        # 细粒度扩展类型
        '人物关系': 0, '感情线': 0, '奇遇事件': 0, '秘境副本': 0,
        '反派视角': 0, '日常互动': 0, '战斗': 0, '修炼成长': 0,
        '势力冲突': 0, '伏笔埋设': 0, '伏笔回收': 0
    }

    for chapter in chapters:
        # 从 expansion_plan 解析章节类型
        expansion_plan = json.loads(chapter.expansion_plan or '{}')
        types = expansion_plan.get('chapter_types', ['主线推进'])
        for type_str in types:
            # 解析类型名称（去除占比部分）
            type_name = type_str.split('(')[0] if '(' in type_str else type_str
            # 类型映射：兼容旧数据并细化
            mapped_type = _map_chapter_type(type_name)
            if mapped_type in type_counts:
                type_counts[mapped_type] += 1

    total = len(chapters)
    return {
        'counts': type_counts,
        'percentages': {k: round(v/total*100, 1) if total > 0 else 0 for k, v in type_counts.items()},
        'total': total
    }


def get_rhythm_curve_from_chapters(chapters: List[Chapter], outlines_by_id: Dict[str, str] = None) -> List[Dict[str, Any]]:
    """从已展开章节提取节奏强度曲线数据

    Args:
        chapters: 章节列表（已按 chapter_number 排序）
        outlines_by_id: 大纲ID到标题的映射字典，用于获取 outline_title

    Returns:
        节奏强度曲线数据列表，每项包含 {index, title, intensity, main_type, all_types}
    """
    curve_data = []
    for chapter in chapters:
        # 从 expansion_plan 解析节奏强度和章节类型
        expansion_plan = json.loads(chapter.expansion_plan or '{}')
        intensity = expansion_plan.get('rhythm_intensity', 5)  # 默认中等强度
        types = expansion_plan.get('chapter_types', ['主线推进'])

        # 解析主类型（取第一个或占比最大的）
        main_type = types[0] if types else '主线推进'
        if '(' in main_type:
            main_type = main_type.split('(')[0]

        # 从 outlines_by_id 获取关联的大纲标题
        outline_title = None
        if chapter.outline_id and outlines_by_id:
            outline_title = outlines_by_id.get(chapter.outline_id)

        curve_data.append({
            'index': chapter.chapter_number,
            'title': chapter.title,
            'intensity': intensity,
            'main_type': main_type,
            'all_types': types,
            'outline_title': outline_title,  # 关联的大纲标题
            'sub_index': chapter.sub_index    # 大纲下的子序号
        })
    return curve_data


@router.get("/rhythm-analysis/{project_id}", summary="获取项目节奏分析数据")
async def get_rhythm_analysis(
    project_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """获取项目的章节类型分布和节奏强度曲线数据，用于前端图表展示

    细化模式(one-to-many)时，如果已有展开章节，则基于章节数据计算；
    否则基于大纲数据计算（用于预览）。

    Returns:
        {
            "distribution": {"counts": {...}, "percentages": {...}, "total": N},
            "rhythm_curve": [{index, title, intensity, main_type, all_types}, ...],
            "suggestions": "节奏建议文本",
            "data_level": "chapter" | "outline",  # 数据维度标识
            "total_outlines": N,  # 大纲总数
            "total_chapters": N   # 章节总数（细化模式）
        }
    """
    user_id = getattr(request.state, 'user_id', None)
    project = await verify_project_access(project_id, user_id, db)

    # 获取所有大纲
    result = await db.execute(
        select(Outline)
        .where(Outline.project_id == project_id)
        .order_by(Outline.order_index)
    )
    outlines = result.scalars().all()

    if not outlines:
        return {
            "distribution": {"counts": {}, "percentages": {}, "total": 0},
            "rhythm_curve": [],
            "suggestions": "暂无大纲数据",
            "data_level": "outline",
            "total_outlines": 0,
            "total_chapters": 0
        }

    # 判断是否细化模式且有已展开章节
    outline_mode = project.outline_mode or 'one-to-many'
    total_outlines = len(outlines)

    if outline_mode == 'one-to-many':
        # 查询已创建的章节（有 expansion_plan 的才算真正展开）
        chapters_result = await db.execute(
            select(Chapter)
            .where(Chapter.project_id == project_id)
            .order_by(Chapter.chapter_number)
        )
        all_chapters = chapters_result.scalars().all()
        # 过滤有 expansion_plan 的章节（真正展开的）
        chapters_list = [ch for ch in all_chapters if ch.expansion_plan]
        total_chapters = len(chapters_list)

        if total_chapters > 0:
            # 构建 outline_id -> title 的映射，用于获取章节关联的大纲标题
            outlines_by_id = {o.id: o.title for o in outlines}

            # 有已展开章节：基于章节数据计算
            distribution = calculate_distribution_from_chapters(chapters_list)
            rhythm_curve = get_rhythm_curve_from_chapters(chapters_list, outlines_by_id)
            data_level = "chapter"

            # 章节级别的进度计算
            current_progress = total_chapters
            plot_stage = 'development'
            suggestions = generate_rhythm_suggestions(current_progress, total_chapters * 3 if total_chapters else 50, plot_stage, distribution, rhythm_curve)
        else:
            # 无已展开章节：回退到大纲数据（用于预览）
            distribution = calculate_chapter_type_distribution(outlines)
            rhythm_curve = get_rhythm_curve_data(outlines)
            data_level = "outline"

            total_chapters = 0
            current_progress = total_outlines
            plot_stage = 'development'
            suggestions = generate_rhythm_suggestions(current_progress, total_outlines * 3, plot_stage, distribution, rhythm_curve)
    else:
        # one-to-one 模式：继续使用大纲数据
        distribution = calculate_chapter_type_distribution(outlines)
        rhythm_curve = get_rhythm_curve_data(outlines)
        data_level = "outline"
        total_chapters = total_outlines  # 一对一模式下章节数等于大纲数

        current_progress = total_outlines
        plot_stage = 'development'
        suggestions = generate_rhythm_suggestions(current_progress, project.target_words // 3000 if project.target_words else 50, plot_stage, distribution, rhythm_curve)

    return {
        "distribution": distribution,
        "rhythm_curve": rhythm_curve,
        "suggestions": suggestions,
        "data_level": data_level,
        "total_outlines": total_outlines,
        "total_chapters": total_chapters
    }


def _build_chapters_brief(outlines: List[Outline], max_recent: int = 20) -> str:
    """构建章节概览字符串"""
    target = outlines[-max_recent:] if len(outlines) > max_recent else outlines
    return "\n".join([f"第{o.order_index}章《{o.title}》" for o in target])


def _build_characters_info(characters: List[Character]) -> str:
    """构建角色信息字符串"""
    return "\n".join([
        f"- {char.name} ({'组织' if char.is_organization else '角色'}, {char.role_type}): "
        f"{char.personality[:100] if char.personality else '暂无描述'}"
        for char in characters
    ])


@router.post("", response_model=OutlineResponse, summary="创建大纲")
async def create_outline(
    outline: OutlineCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """创建新的章节大纲（one-to-one模式会自动创建对应章节）"""
    # 验证用户权限
    user_id = getattr(request.state, 'user_id', None)
    project = await verify_project_access(outline.project_id, user_id, db)
    
    # 创建大纲
    db_outline = Outline(**outline.model_dump())
    db.add(db_outline)
    await db.flush()  # 确保大纲有ID
    
    # 如果是one-to-one模式，自动创建对应的章节
    if project.outline_mode == 'one-to-one':
        chapter = Chapter(
            project_id=outline.project_id,
            title=db_outline.title,
            summary=db_outline.content,
            chapter_number=db_outline.order_index,
            sub_index=1,
            outline_id=None,  # one-to-one模式不关联outline_id
            status='pending',
            content=""
        )
        db.add(chapter)
        logger.info(f"一对一模式：为手动创建的大纲 {db_outline.title} (序号{db_outline.order_index}) 自动创建了对应章节")
    
    await db.commit()
    await db.refresh(db_outline)
    return db_outline


@router.get("", response_model=OutlineListResponse, summary="获取大纲列表")
async def get_outlines(
    project_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """获取指定项目的所有大纲（优化版：后端完全解析structure，构建标准JSON返回）"""
    # 验证用户权限
    user_id = getattr(request.state, 'user_id', None)
    await verify_project_access(project_id, user_id, db)
    
    # 获取总数
    count_result = await db.execute(
        select(func.count(Outline.id)).where(Outline.project_id == project_id)
    )
    total = count_result.scalar_one()
    
    # 获取大纲列表
    result = await db.execute(
        select(Outline)
        .where(Outline.project_id == project_id)
        .order_by(Outline.order_index)
    )
    outlines = result.scalars().all()

    # 批量查询是否已展开章节（避免前端 N+1 请求）
    outline_ids = [outline.id for outline in outlines]
    outline_has_chapters_map: Dict[str, bool] = {}
    if outline_ids:
        chapters_count_result = await db.execute(
            select(Chapter.outline_id, func.count(Chapter.id))
            .where(Chapter.outline_id.in_(outline_ids))
            .group_by(Chapter.outline_id)
        )
        outline_has_chapters_map = {
            str(outline_id): count > 0
            for outline_id, count in chapters_count_result.all()
            if outline_id
        }

    # 🔧 优化：后端完全解析structure，提取所有字段填充到outline对象
    for outline in outlines:
        # 动态附加是否已有章节展开状态，供前端直接使用
        setattr(outline, "has_chapters", outline_has_chapters_map.get(outline.id, False))

        if outline.structure:
            try:
                structure_data = json.loads(outline.structure)

                # 从structure中提取所有字段填充到outline对象
                outline.title = structure_data.get("title", f"第{outline.order_index}章")
                outline.content = structure_data.get("summary") or structure_data.get("content", "")

                # structure字段保持不变，供前端使用其他字段（如characters、scenes等）

            except json.JSONDecodeError:
                logger.warning(f"解析大纲 {outline.id} 的structure失败")
                outline.title = f"第{outline.order_index}章"
                outline.content = "解析失败"
        else:
            # 没有structure的异常情况
            outline.title = f"第{outline.order_index}章"
            outline.content = "暂无内容"

    return OutlineListResponse(total=total, items=outlines)


@router.get("/project/{project_id}", response_model=OutlineListResponse, summary="获取项目的所有大纲")
async def get_project_outlines(
    project_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """获取指定项目的所有大纲（路径参数版本，兼容旧API）"""
    return await get_outlines(project_id, request, db)


@router.get("/{outline_id}", response_model=OutlineResponse, summary="获取大纲详情")
async def get_outline(
    outline_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """根据ID获取大纲详情"""
    result = await db.execute(
        select(Outline).where(Outline.id == outline_id)
    )
    outline = result.scalar_one_or_none()
    
    if not outline:
        raise HTTPException(status_code=404, detail="大纲不存在")
    
    # 验证用户权限
    user_id = getattr(request.state, 'user_id', None)
    await verify_project_access(outline.project_id, user_id, db)
    
    return outline


@router.put("/{outline_id}", response_model=OutlineResponse, summary="更新大纲")
async def update_outline(
    outline_id: str,
    outline_update: OutlineUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """更新大纲信息并同步更新structure字段和关联章节"""
    result = await db.execute(
        select(Outline).where(Outline.id == outline_id)
    )
    outline = result.scalar_one_or_none()
    
    if not outline:
        raise HTTPException(status_code=404, detail="大纲不存在")
    
    # 验证用户权限
    user_id = getattr(request.state, 'user_id', None)
    project = await verify_project_access(outline.project_id, user_id, db)
    
    # 更新字段
    update_data = outline_update.model_dump(exclude_unset=True)
    
    # 🔧 特殊处理：如果直接传递了structure字段，优先使用它
    if 'structure' in update_data:
        # 直接使用前端传递的structure（前端已经处理好了完整的JSON）
        outline.structure = update_data['structure']
        logger.info(f"直接更新大纲 {outline_id} 的structure字段")
        # 从update_data中移除structure，避免后续重复处理
        structure_updated = True
        del update_data['structure']
    else:
        structure_updated = False
    
    # 更新其他字段
    for field, value in update_data.items():
        setattr(outline, field, value)
    
    # 如果没有直接更新structure，但修改了content或title，则同步更新structure字段
    if not structure_updated and ('content' in update_data or 'title' in update_data):
        try:
            # 尝试解析现有的structure
            if outline.structure:
                structure_data = json.loads(outline.structure)
            else:
                structure_data = {}
            
            # 更新structure中的对应字段
            if 'title' in update_data:
                structure_data['title'] = outline.title
            if 'content' in update_data:
                structure_data['summary'] = outline.content
                structure_data['content'] = outline.content
            
            # 保存更新后的structure
            outline.structure = json.dumps(structure_data, ensure_ascii=False)
            logger.info(f"同步更新大纲 {outline_id} 的structure字段")
        except json.JSONDecodeError:
            logger.warning(f"大纲 {outline_id} 的structure字段格式错误，跳过更新")
    
    # 🔧 传统模式（one-to-one）：同步更新关联章节的标题
    if 'title' in update_data and project.outline_mode == 'one-to-one':
        try:
            # 查找对应的章节（通过chapter_number匹配order_index）
            chapter_result = await db.execute(
                select(Chapter).where(
                    Chapter.project_id == outline.project_id,
                    Chapter.chapter_number == outline.order_index
                )
            )
            chapter = chapter_result.scalar_one_or_none()
            
            if chapter:
                # 同步更新章节标题
                chapter.title = outline.title
                logger.info(f"一对一模式：同步更新章节 {chapter.id} 的标题为 '{outline.title}'")
            else:
                logger.debug(f"一对一模式：未找到对应的章节（chapter_number={outline.order_index}）")
        except Exception as e:
            logger.error(f"同步更新章节标题失败: {str(e)}")
            # 不阻断大纲更新流程，仅记录错误
    
    await db.commit()
    await db.refresh(outline)
    return outline


@router.delete("/{outline_id}", summary="删除大纲")
async def delete_outline(
    outline_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """删除大纲，同时删除该大纲对应的所有章节和相关的伏笔数据"""
    result = await db.execute(
        select(Outline).where(Outline.id == outline_id)
    )
    outline = result.scalar_one_or_none()
    
    if not outline:
        raise HTTPException(status_code=404, detail="大纲不存在")
    
    # 验证用户权限
    user_id = getattr(request.state, 'user_id', None)
    project = await verify_project_access(outline.project_id, user_id, db)
    
    project_id = outline.project_id
    deleted_order = outline.order_index
    
    # 获取要删除的章节并计算总字数
    deleted_word_count = 0
    deleted_foreshadow_count = 0
    if project.outline_mode == 'one-to-one':
        # one-to-one模式：通过chapter_number获取对应章节
        chapters_result = await db.execute(
            select(Chapter).where(
                Chapter.project_id == project_id,
                Chapter.chapter_number == outline.order_index
            )
        )
        chapters_to_delete = chapters_result.scalars().all()
        deleted_word_count = sum(ch.word_count or 0 for ch in chapters_to_delete)
        
        # 🔮 清理章节相关的伏笔数据和向量记忆
        for chapter in chapters_to_delete:
            try:
                # 清理向量数据库中的记忆数据
                await memory_service.delete_chapter_memories(
                    user_id=user_id,
                    project_id=project_id,
                    chapter_id=chapter.id
                )
                logger.info(f"✅ 已清理章节 {chapter.id[:8]} 的向量记忆数据")
            except Exception as e:
                logger.warning(f"⚠️ 清理章节 {chapter.id[:8]} 向量记忆失败: {str(e)}")
            
            try:
                # 清理伏笔数据（分析来源的伏笔）
                foreshadow_result = await foreshadow_service.delete_chapter_foreshadows(
                    db=db,
                    project_id=project_id,
                    chapter_id=chapter.id,
                    only_analysis_source=True
                )
                deleted_foreshadow_count += foreshadow_result.get('deleted_count', 0)
                if foreshadow_result.get('deleted_count', 0) > 0:
                    logger.info(f"🔮 已清理章节 {chapter.id[:8]} 的 {foreshadow_result['deleted_count']} 个伏笔数据")
            except Exception as e:
                logger.warning(f"⚠️ 清理章节 {chapter.id[:8]} 伏笔数据失败: {str(e)}")
        
        # 删除章节
        delete_result = await db.execute(
            delete(Chapter).where(
                Chapter.project_id == project_id,
                Chapter.chapter_number == outline.order_index
            )
        )
        deleted_chapters_count = delete_result.rowcount
        logger.info(f"一对一模式：删除大纲 {outline_id}（序号{outline.order_index}），同时删除了第{outline.order_index}章（{deleted_chapters_count}个章节，{deleted_word_count}字，{deleted_foreshadow_count}个伏笔）")
    else:
        # one-to-many模式：通过outline_id获取关联章节
        chapters_result = await db.execute(
            select(Chapter).where(Chapter.outline_id == outline_id)
        )
        chapters_to_delete = chapters_result.scalars().all()
        deleted_word_count = sum(ch.word_count or 0 for ch in chapters_to_delete)
        
        # 🔮 清理章节相关的伏笔数据和向量记忆
        for chapter in chapters_to_delete:
            try:
                # 清理向量数据库中的记忆数据
                await memory_service.delete_chapter_memories(
                    user_id=user_id,
                    project_id=project_id,
                    chapter_id=chapter.id
                )
                logger.info(f"✅ 已清理章节 {chapter.id[:8]} 的向量记忆数据")
            except Exception as e:
                logger.warning(f"⚠️ 清理章节 {chapter.id[:8]} 向量记忆失败: {str(e)}")
            
            try:
                # 清理伏笔数据（分析来源的伏笔）
                foreshadow_result = await foreshadow_service.delete_chapter_foreshadows(
                    db=db,
                    project_id=project_id,
                    chapter_id=chapter.id,
                    only_analysis_source=True
                )
                deleted_foreshadow_count += foreshadow_result.get('deleted_count', 0)
                if foreshadow_result.get('deleted_count', 0) > 0:
                    logger.info(f"🔮 已清理章节 {chapter.id[:8]} 的 {foreshadow_result['deleted_count']} 个伏笔数据")
            except Exception as e:
                logger.warning(f"⚠️ 清理章节 {chapter.id[:8]} 伏笔数据失败: {str(e)}")
        
        # 删除章节
        delete_result = await db.execute(
            delete(Chapter).where(Chapter.outline_id == outline_id)
        )
        deleted_chapters_count = delete_result.rowcount
        logger.info(f"一对多模式：删除大纲 {outline_id}，同时删除了 {deleted_chapters_count} 个关联章节（{deleted_word_count}字，{deleted_foreshadow_count}个伏笔）")
    
    # 更新项目字数
    if deleted_word_count > 0:
        project.current_words = max(0, project.current_words - deleted_word_count)
        logger.info(f"更新项目字数：减少 {deleted_word_count} 字")
    
    # 删除大纲
    await db.delete(outline)
    
    # 重新排序后续的大纲（序号-1）
    result = await db.execute(
        select(Outline).where(
            Outline.project_id == project_id,
            Outline.order_index > deleted_order
        )
    )
    subsequent_outlines = result.scalars().all()
    
    for o in subsequent_outlines:
        o.order_index -= 1
    
    # 如果是one-to-one模式，还需要重新排序后续章节的chapter_number
    if project.outline_mode == 'one-to-one':
        chapters_result = await db.execute(
            select(Chapter).where(
                Chapter.project_id == project_id,
                Chapter.chapter_number > deleted_order
            ).order_by(Chapter.chapter_number)
        )
        subsequent_chapters = chapters_result.scalars().all()
        
        for ch in subsequent_chapters:
            ch.chapter_number -= 1
        
        logger.info(f"一对一模式：重新排序了 {len(subsequent_chapters)} 个后续章节")
    
    await db.commit()
    
    return {
        "message": "大纲删除成功",
        "deleted_chapters": deleted_chapters_count,
        "deleted_foreshadows": deleted_foreshadow_count
    }




async def _build_outline_continue_context(
    project: Project,
    latest_outlines: List[Outline],
    characters: List[Character],
    chapter_count: int,
    plot_stage: str,
    story_direction: str,
    requirements: str,
    db: AsyncSession,
    user_id: str = None,
    current_chapter_number: int = 0
) -> dict:
    """
    构建大纲续写上下文（增强版）

    包含内容：
    1. 项目基础信息：title, theme, genre, world_time_period, world_location,
       world_atmosphere, world_rules, narrative_perspective
    2. 最近10章的完整大纲structure（解析JSON转化为文本）
    3. 所有角色的全部信息
    4. 用户输入：chapter_count, plot_stage, story_direction, requirements
    5. 【新增】伏笔提醒：已埋入但未回收的伏笔
    6. 【新增】相关记忆：关键故事记忆

    Args:
        project: 项目对象
        latest_outlines: 所有已有大纲列表
        characters: 所有角色列表
        chapter_count: 要生成的章节数
        plot_stage: 情节阶段
        story_direction: 故事发展方向
        requirements: 其他要求
        user_id: 用户ID（用于记忆查询）
        current_chapter_number: 当前最大章节号（用于伏笔查询）

    Returns:
        包含上下文信息的字典
    """
    context = {
        'project_info': '',
        'recent_outlines': '',
        'characters_info': '',
        'foreshadow_reminders': '',  # 新增
        'memory_context': '',        # 新增
        'user_input': '',
        'stats': {
            'total_outlines': len(latest_outlines),
            'recent_outlines_count': 0,
            'characters_count': len(characters),
            'foreshadow_count': 0,
            'memory_count': 0
        }
    }
    
    try:
        # 构建 world_setting - 使用 world_setting_markdown
        world_setting = project.world_setting_markdown or ""
        if not world_setting:
            # 兜底：如果没有 world_setting_markdown，拼接分散字段
            world_setting = f"时间背景：{project.world_time_period or '未设定'}\n地理位置：{project.world_location or '未设定'}\n氛围基调：{project.world_atmosphere or '未设定'}\n世界规则：{project.world_rules or '未设定'}"

        # 1. 项目基础信息
        project_info_parts = [
            f"【项目基础信息】",
            f"标题：{project.title}",
            f"主题：{project.theme or '未设定'}",
            f"类型：{project.genre or '未设定'}",
            f"世界观设定：",
            world_setting,
            f"叙事视角：{project.narrative_perspective or '第三人称'}"
        ]
        context['project_info'] = "\n".join(project_info_parts)
        
        # 2. 最近10章的完整大纲structure（解析JSON转化为文本）
        recent_count = min(10, len(latest_outlines))
        if recent_count > 0:
            recent_outlines = latest_outlines[-recent_count:]
            context['stats']['recent_outlines_count'] = recent_count
            
            outline_texts = []
            outline_texts.append(f"【最近{recent_count}章大纲详情】")
            
            for outline in recent_outlines:
                outline_text = f"\n第{outline.order_index}章《{outline.title}》"
                
                # 尝试解析structure字段
                if outline.structure:
                    try:
                        structure_data = json.loads(outline.structure)
                        
                        # 提取各个字段（使用实际存储的字段名）
                        if structure_data.get('summary'):
                            outline_text += f"\n  概要：{structure_data['summary']}"
                        
                        # key_points 对应 关键事件
                        if structure_data.get('key_points'):
                            events = structure_data['key_points']
                            if isinstance(events, list):
                                outline_text += f"\n  关键事件：{', '.join(events)}"
                            else:
                                outline_text += f"\n  关键事件：{events}"
                        
                        # characters 对应 重点角色/组织（兼容新旧格式）
                        if structure_data.get('characters'):
                            chars = structure_data['characters']
                            if isinstance(chars, list):
                                # 新格式：[{"name": "xxx", "type": "character"/"organization"}]
                                # 旧格式：["角色名1", "角色名2"]
                                char_names = []
                                org_names = []
                                for c in chars:
                                    if isinstance(c, dict):
                                        name = c.get('name', '')
                                        if c.get('type') == 'organization':
                                            org_names.append(name)
                                        else:
                                            char_names.append(name)
                                    elif isinstance(c, str):
                                        char_names.append(c)
                                if char_names:
                                    outline_text += f"\n  重点角色：{', '.join(char_names)}"
                                if org_names:
                                    outline_text += f"\n  涉及组织：{', '.join(org_names)}"
                            else:
                                outline_text += f"\n  重点角色：{chars}"
                        
                        # emotion 对应 情感基调
                        if structure_data.get('emotion'):
                            outline_text += f"\n  情感基调：{structure_data['emotion']}"
                        
                        # goal 对应 叙事目标
                        if structure_data.get('goal'):
                            outline_text += f"\n  叙事目标：{structure_data['goal']}"
                        
                        # scenes 场景信息（可选显示）
                        if structure_data.get('scenes'):
                            scenes = structure_data['scenes']
                            if isinstance(scenes, list) and scenes:
                                outline_text += f"\n  场景：{', '.join(scenes)}"
                            
                    except json.JSONDecodeError:
                        # 如果解析失败，使用content字段
                        outline_text += f"\n  内容：{outline.content}"
                else:
                    # 没有structure，使用content
                    outline_text += f"\n  内容：{outline.content}"
                
                outline_texts.append(outline_text)
            
            context['recent_outlines'] = "\n".join(outline_texts)
            logger.info(f"  ✅ 最近大纲：{recent_count}章")
        
        # 3. 所有角色的全部信息(包括职业信息)
        if characters:
            from app.models.career import Career, CharacterCareer
            
            char_texts = []
            char_texts.append("【角色信息】")
            
            for char in characters:
                char_text = f"\n{char.name}（{'组织' if char.is_organization else '角色'}，{char.role_type}）"
                
                if char.personality:
                    char_text += f"\n  性格特点：{char.personality}"
                
                if char.background:
                    char_text += f"\n  背景故事：{char.background}"
                
                if char.appearance:
                    char_text += f"\n  外貌描述：{char.appearance}"
                
                if char.traits:
                    char_text += f"\n  特征标签：{char.traits}"
                
                # 从 character_relationships 表查询关系
                from sqlalchemy import or_
                rels_result = await db.execute(
                    select(CharacterRelationship).where(
                        CharacterRelationship.project_id == project.id,
                        or_(
                            CharacterRelationship.character_from_id == char.id,
                            CharacterRelationship.character_to_id == char.id
                        )
                    )
                )
                rels = rels_result.scalars().all()
                if rels:
                    # 收集相关角色名称
                    related_ids = set()
                    for r in rels:
                        related_ids.add(r.character_from_id)
                        related_ids.add(r.character_to_id)
                    related_ids.discard(char.id)
                    if related_ids:
                        names_result = await db.execute(
                            select(Character.id, Character.name).where(Character.id.in_(related_ids))
                        )
                        name_map = {row.id: row.name for row in names_result}
                        rel_parts = []
                        for r in rels:
                            if r.character_from_id == char.id:
                                target_name = name_map.get(r.character_to_id, "未知")
                            else:
                                target_name = name_map.get(r.character_from_id, "未知")
                            rel_name = r.relationship_name or "相关"
                            rel_parts.append(f"与{target_name}：{rel_name}")
                        char_text += f"\n  关系网络：{'；'.join(rel_parts)}"
                
                # 组织特有字段
                if char.is_organization:
                    if char.organization_type:
                        char_text += f"\n  组织类型：{char.organization_type}"
                    if char.organization_purpose:
                        char_text += f"\n  组织宗旨：{char.organization_purpose}"
                    # 从 OrganizationMember 表动态查询组织成员
                    org_result = await db.execute(
                        select(Organization).where(Organization.character_id == char.id)
                    )
                    org = org_result.scalar_one_or_none()
                    if org:
                        members_result = await db.execute(
                            select(OrganizationMember, Character.name).join(
                                Character, OrganizationMember.character_id == Character.id
                            ).where(OrganizationMember.organization_id == org.id)
                        )
                        members = members_result.all()
                        if members:
                            member_parts = [f"{name}（{m.position}）" for m, name in members]
                            char_text += f"\n  组织成员：{'、'.join(member_parts)}"
                
                # 查询角色的职业信息
                if not char.is_organization:
                    try:
                        career_result = await db.execute(
                            select(Career, CharacterCareer)
                            .join(CharacterCareer, Career.id == CharacterCareer.career_id)
                            .where(CharacterCareer.character_id == char.id)
                        )
                        career_data = career_result.first()
                        
                        if career_data:
                            career, char_career = career_data
                            char_text += f"\n  职业：{career.name}"
                            if char_career.current_stage:
                                char_text += f"（{char_career.current_stage}阶段）"
                            if char_career.career_type:
                                char_text += f"\n  职业类型：{char_career.career_type}"
                    except Exception as e:
                        logger.warning(f"查询角色 {char.name} 的职业信息失败: {str(e)}")
                
                char_texts.append(char_text)
            
            context['characters_info'] = "\n".join(char_texts)
            logger.info(f"  ✅ 角色信息：{len(characters)}个角色")
        else:
            context['characters_info'] = "【角色信息】\n暂无角色信息"

        # 4. 用户输入
        user_input_parts = [
            "【用户输入】",
            f"要生成章节数：{chapter_count}章",
            f"情节阶段：{plot_stage}",
            f"故事发展方向：{story_direction}",
        ]
        if requirements:
            user_input_parts.append(f"其他要求：{requirements}")

        context['user_input'] = "\n".join(user_input_parts)

        # 5. 【新增】伏笔提醒：已埋入但未回收的伏笔
        foreshadow_reminders = ""
        try:
            from app.services.foreshadow_service import foreshadow_service

            # 获取未回收的伏笔（供AI规划参考）
            pending_foreshadows = await foreshadow_service.get_pending_resolve_foreshadows(
                db=db,
                project_id=project.id,
                current_chapter=current_chapter_number,
                lookahead=20  # 查看未来20章的伏笔规划
            )
            if pending_foreshadows:
                foreshadow_parts = ["【已埋入伏笔（需规划回收）】"]
                for f in pending_foreshadows[:10]:
                    plant_ch = f.plant_chapter_number or 0
                    target_ch = f.target_resolve_chapter_number or 0
                    foreshadow_parts.append(
                        f"- {f.title}（埋入第{plant_ch}章，计划第{target_ch}章回收）"
                    )
                    if f.content:
                        foreshadow_parts.append(f"  内容：{f.content[:80]}...")
                foreshadow_reminders = "\n".join(foreshadow_parts)
                context['stats']['foreshadow_count'] = len(pending_foreshadows)
                logger.info(f"  ✅ 伏笔提醒：{len(pending_foreshadows)}个待回收伏笔")
        except Exception as e:
            logger.warning(f"获取伏笔提醒失败: {str(e)}")

        context['foreshadow_reminders'] = foreshadow_reminders

        # 6. 【新增】相关记忆：关键故事记忆
        memory_context = ""
        if user_id:
            try:
                from app.services.memory_service import memory_service

                # 使用最近大纲作为查询基础
                query_text = context['recent_outlines'][:500].replace('\n', ' ') if context['recent_outlines'] else ""

                if query_text:
                    relevant_memories = await memory_service.search_memories(
                        user_id=user_id,
                        project_id=project.id,
                        query=query_text,
                        limit=10,
                        min_importance=0.5
                    )

                    if relevant_memories:
                        memory_parts = ["【关键故事记忆】"]
                        for mem in relevant_memories:
                            content = mem.get('content', '')
                            if content:
                                memory_parts.append(f"- {content[:100]}")
                        memory_context = "\n".join(memory_parts)
                        context['stats']['memory_count'] = len(relevant_memories)
                        logger.info(f"  ✅ 故事记忆：{len(relevant_memories)}条相关记忆")
            except Exception as e:
                logger.warning(f"获取故事记忆失败: {str(e)}")

        context['memory_context'] = memory_context

        # 计算总长度
        total_length = sum([
            len(context['project_info']),
            len(context['recent_outlines']),
            len(context['characters_info']),
            len(context['foreshadow_reminders']),
            len(context['memory_context']),
            len(context['user_input'])
        ])
        context['stats']['total_length'] = total_length
        logger.info(f"📊 大纲续写上下文总长度: {total_length} 字符")
        
    except Exception as e:
        logger.error(f"❌ 构建大纲续写上下文失败: {str(e)}", exc_info=True)
    
    return context


async def _check_and_create_missing_characters_from_outlines(
    outline_data: list,
    project_id: str,
    db: AsyncSession,
    user_ai_service: AIService,
    user_id: str = None,
    enable_mcp: bool = True,
    tracker = None
) -> dict:
    """
    大纲生成/续写后，校验structure中的characters是否存在对应角色，
    不存在的自动根据大纲摘要生成角色信息。
    
    Args:
        outline_data: 大纲数据列表（原始JSON解析后的数据，包含characters、summary等字段）
        project_id: 项目ID
        db: 数据库会话
        user_ai_service: AI服务实例
        user_id: 用户ID
        enable_mcp: 是否启用MCP
        tracker: 可选，WizardProgressTracker用于发送进度
        
    Returns:
        {"created_count": int, "created_characters": list}
    """
    try:
        from app.services.auto_character_service import get_auto_character_service
        
        auto_char_service = get_auto_character_service(user_ai_service)
        
        # 定义进度回调
        async def progress_cb(message: str):
            if tracker:
                # 注意：这里不能直接yield，需要通过其他方式处理
                logger.info(f"  📌 {message}")
        
        result = await auto_char_service.check_and_create_missing_characters(
            project_id=project_id,
            outline_data_list=outline_data,
            db=db,
            user_id=user_id,
            enable_mcp=enable_mcp,
            progress_callback=progress_cb
        )
        
        if result["created_count"] > 0:
            logger.info(
                f"🎭 【角色校验完成】自动创建了 {result['created_count']} 个缺失角色: "
                f"{', '.join(c.name for c in result['created_characters'])}"
            )
        
        return result
        
    except Exception as e:
        logger.error(f"⚠️ 【角色校验】校验失败（不影响主流程）: {e}", exc_info=True)
        return {"created_count": 0, "created_characters": []}


async def _check_and_create_missing_organizations_from_outlines(
    outline_data: list,
    project_id: str,
    db: AsyncSession,
    user_ai_service: AIService,
    user_id: str = None,
    enable_mcp: bool = True,
    tracker = None
) -> dict:
    """
    大纲生成/续写后，校验structure中的characters（type=organization）是否存在对应组织，
    不存在的自动根据大纲摘要生成组织信息。
    
    Args:
        outline_data: 大纲数据列表（原始JSON解析后的数据，包含characters、summary等字段）
        project_id: 项目ID
        db: 数据库会话
        user_ai_service: AI服务实例
        user_id: 用户ID
        enable_mcp: 是否启用MCP
        tracker: 可选，WizardProgressTracker用于发送进度
        
    Returns:
        {"created_count": int, "created_organizations": list}
    """
    try:
        from app.services.auto_organization_service import get_auto_organization_service
        
        auto_org_service = get_auto_organization_service(user_ai_service)
        
        # 定义进度回调
        async def progress_cb(message: str):
            if tracker:
                logger.info(f"  📌 {message}")
        
        result = await auto_org_service.check_and_create_missing_organizations(
            project_id=project_id,
            outline_data_list=outline_data,
            db=db,
            user_id=user_id,
            enable_mcp=enable_mcp,
            progress_callback=progress_cb
        )
        
        if result["created_count"] > 0:
            logger.info(
                f"🏛️ 【组织校验完成】自动创建了 {result['created_count']} 个缺失组织: "
                f"{', '.join(c.name for c in result['created_organizations'])}"
            )
        
        return result
        
    except Exception as e:
        logger.error(f"⚠️ 【组织校验】校验失败（不影响主流程）: {e}", exc_info=True)
        return {"created_count": 0, "created_organizations": []}


class JSONParseError(Exception):
    """JSON解析失败异常，用于触发重试"""
    def __init__(self, message: str, original_content: str = ""):
        super().__init__(message)
        self.original_content = original_content


def _parse_ai_response(ai_response: str, raise_on_error: bool = False) -> list:
    """
    解析AI响应为章节数据列表（使用统一的JSON清洗方法）
    
    Args:
        ai_response: AI返回的原始文本
        raise_on_error: 如果为True，解析失败时抛出异常而不是返回fallback数据
        
    Returns:
        解析后的章节数据列表
        
    Raises:
        JSONParseError: 当raise_on_error=True且解析失败时抛出
    """
    try:
        # 使用统一的JSON清洗方法（从AIService导入）
        from app.services.ai_service import AIService
        ai_service_temp = AIService()
        cleaned_text = ai_service_temp._clean_json_response(ai_response)
        
        outline_data = json.loads(cleaned_text)
        
        # 确保是列表格式
        if not isinstance(outline_data, list):
            # 如果是对象，尝试提取chapters字段
            if isinstance(outline_data, dict):
                outline_data = outline_data.get("chapters", [outline_data])
            else:
                outline_data = [outline_data]
        
        # 验证解析结果是否有效（至少有一个有效章节）
        valid_chapters = [
            ch for ch in outline_data
            if isinstance(ch, dict) and (ch.get("title") or ch.get("summary") or ch.get("content"))
        ]
        
        if not valid_chapters:
            error_msg = "解析结果无效：未找到有效的章节数据"
            logger.error(f"❌ {error_msg}")
            if raise_on_error:
                raise JSONParseError(error_msg, ai_response)
            return [{
                "title": "AI生成的大纲",
                "content": ai_response[:1000],
                "summary": ai_response[:1000]
            }]
        
        logger.info(f"✅ 成功解析 {len(valid_chapters)} 个章节数据")
        return valid_chapters
        
    except json.JSONDecodeError as e:
        error_msg = f"JSON解析失败: {e}"
        logger.error(f"❌ AI响应解析失败: {e}")
        
        if raise_on_error:
            raise JSONParseError(error_msg, ai_response)
        
        # 返回一个包含原始内容的章节
        return [{
            "title": "AI生成的大纲",
            "content": ai_response[:1000],
            "summary": ai_response[:1000]
        }]
    except JSONParseError:
        # 重新抛出JSONParseError
        raise
    except Exception as e:
        error_msg = f"解析异常: {str(e)}"
        logger.error(f"❌ {error_msg}")
        
        if raise_on_error:
            raise JSONParseError(error_msg, ai_response)
        
        return [{
            "title": "解析异常的大纲",
            "content": "系统错误",
            "summary": "系统错误"
        }]


async def _save_outlines(
    project_id: str,
    outline_data: list,
    db: AsyncSession,
    start_index: int = 1
) -> List[Outline]:
    """
    保存大纲到数据库（修复版：从structure中提取title和content保存到数据库）
    
    如果项目为one-to-one模式，同时自动创建对应的章节
    """
    # 获取项目信息以确定outline_mode
    project_result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = project_result.scalar_one_or_none()
    
    outlines = []
    
    for idx, chapter_data in enumerate(outline_data):
        order_idx = chapter_data.get("chapter_number", start_index + idx)
        
        # 🔧 修复：从structure中提取title和summary/content保存到数据库
        chapter_title = chapter_data.get("title", f"第{order_idx}章")
        chapter_content = chapter_data.get("summary") or chapter_data.get("content", "")
        
        outline = Outline(
            project_id=project_id,
            title=chapter_title,  # 从JSON中提取title
            content=chapter_content,  # 从JSON中提取summary或content
            structure=json.dumps(chapter_data, ensure_ascii=False),
            order_index=order_idx
        )
        db.add(outline)
        outlines.append(outline)
    
    # 如果是one-to-one模式，自动创建章节
    if project and project.outline_mode == 'one-to-one':
        await db.flush()  # 确保大纲有ID
        
        for outline in outlines:
            await db.refresh(outline)
            
            # 🔧 从structure中提取title和summary用于创建章节
            try:
                structure_data = json.loads(outline.structure) if outline.structure else {}
                chapter_title = structure_data.get("title", f"第{outline.order_index}章")
                chapter_summary = structure_data.get("summary") or structure_data.get("content", "")
            except json.JSONDecodeError:
                logger.warning(f"解析大纲 {outline.id} 的structure失败，使用默认值")
                chapter_title = f"第{outline.order_index}章"
                chapter_summary = ""
            
            # 为每个大纲创建对应的章节
            chapter = Chapter(
                project_id=project_id,
                title=chapter_title,
                summary=chapter_summary,
                chapter_number=outline.order_index,
                sub_index=1,
                outline_id=None,  # one-to-one模式不关联outline_id
                status='pending',
                content=""
            )
            db.add(chapter)
        
        logger.info(f"一对一模式：为{len(outlines)}个大纲自动创建了对应的章节")
    
    return outlines


async def new_outline_generator(
    data: Dict[str, Any],
    db: AsyncSession,
    user_ai_service: AIService
) -> AsyncGenerator[str, None]:
    """全新生成大纲SSE生成器（MCP增强版）"""
    db_committed = False
    # 初始化标准进度追踪器
    tracker = WizardProgressTracker("大纲")
    
    try:
        yield await tracker.start()
        
        project_id = data.get("project_id")
        # 确保chapter_count是整数（前端可能传字符串）
        chapter_count = int(data.get("chapter_count", 10))
        enable_mcp = data.get("enable_mcp", True)
        
        # 验证项目
        yield await tracker.loading("加载项目信息...", 0.3)
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            yield await tracker.error("项目不存在", 404)
            return
        
        yield await tracker.loading(f"准备生成{chapter_count}章大纲...", 0.6)
        
        # 获取角色信息
        characters_result = await db.execute(
            select(Character).where(Character.project_id == project_id)
        )
        characters = characters_result.scalars().all()
        characters_info = _build_characters_info(characters)
        
        # 设置用户信息以启用MCP
        user_id_for_mcp = data.get("user_id")
        if user_id_for_mcp:
            user_ai_service.user_id = user_id_for_mcp
            user_ai_service.db_session = db
        
        # 使用提示词模板
        yield await tracker.preparing("准备AI提示词...")
        template = await PromptService.get_template("OUTLINE_CREATE", user_id_for_mcp or "", db)

        # 构建 world_setting - 使用 world_setting_markdown
        world_setting = project.world_setting_markdown or ""
        if not world_setting:
            # 兜底：如果没有 world_setting_markdown，拼接分散字段
            world_setting = f"时间背景：{project.world_time_period or '未设定'}\n地理位置：{project.world_location or '未设定'}\n氛围基调：{project.world_atmosphere or '未设定'}\n世界规则：{project.world_rules or '未设定'}"

        prompt = PromptService.format_prompt(
            template,
            title=project.title,
            theme=data.get("theme") or project.theme or "未设定",
            genre=data.get("genre") or project.genre or "通用",
            chapter_count=chapter_count,
            narrative_perspective=data.get("narrative_perspective") or "第三人称",
            world_setting=world_setting,
            characters_info=characters_info or "暂无角色信息",
            requirements=data.get("requirements") or "",
            mcp_references="",
            # 新增：节奏规划参数
            target_words=project.target_words or 100000,
            estimated_total_chapters=max(chapter_count, (project.target_words or 100000) // 3000),
            progress_percent=round(chapter_count / max(1, (project.target_words or 100000) // 3000) * 100, 1)
        )
        logger.debug(f"NEW提示词: {prompt}")
        # 添加调试日志
        model_param = data.get("model")
        provider_param = data.get("provider")
        logger.info(f"=== 大纲生成AI调用参数 ===")
        logger.info(f"  provider参数: {provider_param}")
        logger.info(f"  model参数: {model_param}")
        
        # ✅ 流式生成（带字数统计和进度）
        estimated_total = chapter_count * 1000
        accumulated_text = ""
        chunk_count = 0
        
        yield await tracker.generating(current_chars=0, estimated_total=estimated_total)
        
        async for chunk in user_ai_service.generate_text_stream(
            prompt=prompt,
            provider=provider_param,
            model=model_param
        ):
            chunk_count += 1
            accumulated_text += chunk
            
            # 发送内容块
            yield await tracker.generating_chunk(chunk)
            
            # 定期更新进度
            if chunk_count % 10 == 0:
                yield await tracker.generating(
                    current_chars=len(accumulated_text),
                    estimated_total=estimated_total
                )
            
            # 每20个块发送心跳
            if chunk_count % 20 == 0:
                yield await tracker.heartbeat()
        
        yield await tracker.parsing("解析大纲数据...")
        
        ai_content = accumulated_text
        ai_response = {"content": ai_content}
        
        # 解析响应（带重试机制）
        max_retries = 2
        retry_count = 0
        outline_data = None
        
        while retry_count <= max_retries:
            try:
                # 使用 raise_on_error=True，解析失败时抛出异常
                outline_data = _parse_ai_response(ai_content, raise_on_error=True)
                break  # 解析成功，跳出循环
                
            except JSONParseError as e:
                retry_count += 1
                if retry_count > max_retries:
                    # 超过最大重试次数，使用fallback数据
                    logger.error(f"❌ 大纲解析失败，已达最大重试次数({max_retries})，使用fallback数据")
                    yield await tracker.warning("解析失败，使用备用数据")
                    outline_data = _parse_ai_response(ai_content, raise_on_error=False)
                    break
                
                logger.warning(f"⚠️ JSON解析失败（第{retry_count}次），正在重试...")
                yield await tracker.retry(retry_count, max_retries, "JSON解析失败")
                
                # 重试时重置生成进度
                tracker.reset_generating_progress()
                
                # 重新调用AI生成
                accumulated_text = ""
                chunk_count = 0
                
                # 在prompt中添加格式强调
                retry_prompt = prompt + "\n\n【重要提醒】请确保返回完整的JSON数组，不要截断。每个章节对象必须包含完整的title、summary等字段。"
                
                async for chunk in user_ai_service.generate_text_stream(
                    prompt=retry_prompt,
                    provider=provider_param,
                    model=model_param
                ):
                    chunk_count += 1
                    accumulated_text += chunk
                    
                    # 发送内容块
                    yield await tracker.generating_chunk(chunk)
                    
                    # 每20个块发送心跳
                    if chunk_count % 20 == 0:
                        yield await tracker.heartbeat()
                
                ai_content = accumulated_text
                ai_response = {"content": ai_content}
                logger.info(f"🔄 重试生成完成，累计{len(ai_content)}字符")
        
        # 全新生成模式：删除旧大纲和关联的所有章节、伏笔、分析数据
        yield await tracker.saving("清理旧数据（大纲、章节、伏笔、分析）...", 0.2)
        logger.info(f"🧹 全新生成：开始清理项目 {project_id} 的所有旧数据（outline_mode: {project.outline_mode}）")
        
        from sqlalchemy import delete as sql_delete
        
        # 1. 先获取所有旧章节ID（用于后续清理）
        old_chapters_result = await db.execute(
            select(Chapter).where(Chapter.project_id == project_id)
        )
        old_chapters = old_chapters_result.scalars().all()
        old_chapter_ids = [ch.id for ch in old_chapters]
        deleted_word_count = sum(ch.word_count or 0 for ch in old_chapters)
        
        # 2. 清理伏笔数据（删除分析伏笔，重置手动伏笔）
        try:
            foreshadow_result = await foreshadow_service.clear_project_foreshadows_for_reset(db, project_id)
            logger.info(f"✅ 伏笔清理: 删除 {foreshadow_result['deleted_count']} 个分析伏笔, 重置 {foreshadow_result['reset_count']} 个手动伏笔")
        except Exception as e:
            logger.error(f"❌ 清理伏笔数据失败: {str(e)}")
            # 继续流程，但记录错误
        
        # 3. 清理章节分析数据（PlotAnalysis）
        try:
            # 虽然有CASCADE删除，但显式删除更可控
            from app.models.memory import PlotAnalysis
            delete_analysis_result = await db.execute(
                sql_delete(PlotAnalysis).where(PlotAnalysis.project_id == project_id)
            )
            deleted_analysis_count = delete_analysis_result.rowcount
            logger.info(f"✅ 章节分析清理: 删除 {deleted_analysis_count} 个分析记录")
        except Exception as e:
            logger.error(f"❌ 清理章节分析数据失败: {str(e)}")
        
        # 4. 清理向量记忆数据（StoryMemory）
        try:
            from app.models.memory import StoryMemory
            delete_memory_result = await db.execute(
                sql_delete(StoryMemory).where(StoryMemory.project_id == project_id)
            )
            deleted_memory_count = delete_memory_result.rowcount
            if deleted_memory_count > 0:
                logger.info(f"✅ 向量记忆清理: 删除 {deleted_memory_count} 条记忆数据")
        except Exception as e:
            logger.error(f"❌ 清理向量记忆数据失败: {str(e)}")
        
        # 5. 删除向量数据库中的记忆（如果有章节）
        if old_chapter_ids:
            try:
                user_id_for_memory = data.get("user_id")
                if user_id_for_memory:
                    for chapter_id in old_chapter_ids:
                        try:
                            await memory_service.delete_chapter_memories(
                                user_id=user_id_for_memory,
                                project_id=project_id,
                                chapter_id=chapter_id
                            )
                        except Exception as mem_err:
                            logger.debug(f"清理章节 {chapter_id[:8]} 向量记忆失败: {str(mem_err)}")
                    logger.info(f"✅ 向量数据库清理: 已清理 {len(old_chapter_ids)} 个章节的向量记忆")
            except Exception as e:
                logger.warning(f"⚠️ 清理向量数据库失败（不影响主流程）: {str(e)}")
        
        # 6. 删除所有旧章节
        delete_chapters_result = await db.execute(
            sql_delete(Chapter).where(Chapter.project_id == project_id)
        )
        deleted_chapters_count = delete_chapters_result.rowcount
        logger.info(f"✅ 章节清理: 删除 {deleted_chapters_count} 个章节（{deleted_word_count}字）")
        
        # 更新项目字数
        if deleted_word_count > 0:
            project.current_words = max(0, project.current_words - deleted_word_count)
            logger.info(f"更新项目字数：减少 {deleted_word_count} 字")
        
        # 再删除所有旧大纲
        delete_outlines_result = await db.execute(
            sql_delete(Outline).where(Outline.project_id == project_id)
        )
        deleted_outlines_count = delete_outlines_result.rowcount
        logger.info(f"✅ 全新生成：删除了 {deleted_outlines_count} 个旧大纲")
        
        # 保存新大纲
        yield await tracker.saving("保存大纲到数据库...", 0.6)
        outlines = await _save_outlines(
            project_id, outline_data, db, start_index=1
        )
        
        # 🎭 角色校验：检查大纲structure中的characters是否存在对应角色
        yield await tracker.saving("🎭 校验角色信息...", 0.7)
        try:
            char_check_result = await _check_and_create_missing_characters_from_outlines(
                outline_data=outline_data,
                project_id=project_id,
                db=db,
                user_ai_service=user_ai_service,
                user_id=data.get("user_id"),
                enable_mcp=data.get("enable_mcp", True),
                tracker=tracker
            )
            if char_check_result["created_count"] > 0:
                created_names = [c.name for c in char_check_result["created_characters"]]
                yield await tracker.saving(
                    f"🎭 自动创建了 {char_check_result['created_count']} 个角色: {', '.join(created_names)}",
                    0.8
                )
        except Exception as e:
            logger.error(f"⚠️ 角色校验失败（不影响主流程）: {e}")
        
        # 🏛️ 组织校验：检查大纲structure中的characters（type=organization）是否存在对应组织
        yield await tracker.saving("🏛️ 校验组织信息...", 0.75)
        try:
            org_check_result = await _check_and_create_missing_organizations_from_outlines(
                outline_data=outline_data,
                project_id=project_id,
                db=db,
                user_ai_service=user_ai_service,
                user_id=data.get("user_id"),
                enable_mcp=data.get("enable_mcp", True),
                tracker=tracker
            )
            if org_check_result["created_count"] > 0:
                created_names = [c.name for c in org_check_result["created_organizations"]]
                yield await tracker.saving(
                    f"🏛️ 自动创建了 {org_check_result['created_count']} 个组织: {', '.join(created_names)}",
                    0.85
                )
        except Exception as e:
            logger.error(f"⚠️ 组织校验失败（不影响主流程）: {e}")
        
        # 记录历史
        history = GenerationHistory(
            project_id=project_id,
            prompt=prompt,
            generated_content=json.dumps(ai_response, ensure_ascii=False) if isinstance(ai_response, dict) else ai_response,
            model=data.get("model") or "default"
        )
        db.add(history)
        
        await db.commit()
        db_committed = True
        
        for outline in outlines:
            await db.refresh(outline)
        
        logger.info(f"全新生成完成 - {len(outlines)} 章")
        
        yield await tracker.complete()
        
        # 发送最终结果
        yield await tracker.result({
            "message": f"成功生成{len(outlines)}章大纲",
            "total_chapters": len(outlines),
            "outlines": [
                {
                    "id": outline.id,
                    "project_id": outline.project_id,
                    "title": outline.title,
                    "content": outline.content,
                    "order_index": outline.order_index,
                    "structure": outline.structure,
                    "created_at": outline.created_at.isoformat() if outline.created_at else None,
                    "updated_at": outline.updated_at.isoformat() if outline.updated_at else None
                } for outline in outlines
            ]
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


async def continue_outline_generator(
    data: Dict[str, Any],
    db: AsyncSession,
    user_ai_service: AIService,
    user_id: str = "system"
) -> AsyncGenerator[str, None]:
    """大纲续写SSE生成器 - 分批生成，推送进度（记忆+MCP增强版）"""
    db_committed = False
    # 初始化标准进度追踪器
    tracker = WizardProgressTracker("大纲续写")
    
    try:
        # === 初始化阶段 ===
        yield await tracker.start("开始续写大纲...")
        
        project_id = data.get("project_id")
        # 确保chapter_count是整数（前端可能传字符串）
        total_chapters_to_generate = int(data.get("chapter_count", 5))
        
        # 验证项目
        yield await tracker.loading("加载项目信息...", 0.2)
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            yield await tracker.error("项目不存在", 404)
            return
        
        # 获取现有大纲
        yield await tracker.loading("分析已有大纲...", 0.5)
        existing_result = await db.execute(
            select(Outline)
            .where(Outline.project_id == project_id)
            .order_by(Outline.order_index)
        )
        existing_outlines = existing_result.scalars().all()
        
        if not existing_outlines:
            yield await tracker.error("续写模式需要已有大纲，当前项目没有大纲", 400)
            return
        
        current_chapter_count = len(existing_outlines)
        last_chapter_number = existing_outlines[-1].order_index
        
        yield await tracker.loading(
            f"当前已有{str(current_chapter_count)}章，将续写{str(total_chapters_to_generate)}章",
            0.8
        )
        
        # 获取角色信息
        characters_result = await db.execute(
            select(Character).where(Character.project_id == project_id)
        )
        characters = characters_result.scalars().all()
        characters_info = _build_characters_info(characters)

        # 分批配置
        batch_size = 5
        total_batches = (total_chapters_to_generate + batch_size - 1) // batch_size
        
        # 情节阶段指导
        stage_instructions = {
            "development": "继续展开情节，深化角色关系，推进主线冲突",
            "climax": "进入故事高潮，矛盾激化，关键冲突爆发",
            "ending": "解决主要冲突，收束伏笔，给出结局"
        }
        stage_instruction = stage_instructions.get(data.get("plot_stage", "development"), "")
        
        # === 批次生成阶段 ===
        all_new_outlines = []
        current_start_chapter = last_chapter_number + 1
        
        for batch_num in range(total_batches):
            # 计算当前批次的章节数
            remaining_chapters = int(total_chapters_to_generate) - len(all_new_outlines)
            current_batch_size = min(batch_size, remaining_chapters)
            
            # 每批使用的进度预估
            estimated_chars_per_batch = current_batch_size * 1000
            
            # 重置生成进度以便于每批独立计算
            tracker.reset_generating_progress()
            
            yield await tracker.generating(
                current_chars=0,
                estimated_total=estimated_chars_per_batch,
                message=f"📝 第{str(batch_num + 1)}/{str(total_batches)}批: 生成第{str(current_start_chapter)}-{str(current_start_chapter + current_batch_size - 1)}章"
            )
            
            # 获取最新的大纲列表（包括之前批次生成的）
            latest_result = await db.execute(
                select(Outline)
                .where(Outline.project_id == project_id)
                .order_by(Outline.order_index)
            )
            latest_outlines = latest_result.scalars().all()

            # 获取当前最大章节号（用于伏笔查询）
            current_max_chapter = latest_outlines[-1].order_index if latest_outlines else 0

            # 🚀 使用增强的上下文构建（新增伏笔提醒和故事记忆）
            context = await _build_outline_continue_context(
                project=project,
                latest_outlines=latest_outlines,
                characters=characters,
                chapter_count=current_batch_size,
                plot_stage=data.get("plot_stage", "development"),
                story_direction=data.get("story_direction", "自然延续"),
                requirements=data.get("requirements", ""),
                db=db,
                user_id=user_id,  # 新增：用于记忆查询
                current_chapter_number=current_max_chapter  # 新增：用于伏笔查询
            )

            # 日志统计
            stats = context['stats']
            logger.info(f"📊 批次{batch_num + 1}大纲上下文: 总大纲{stats['total_outlines']}, "
                       f"最近{stats['recent_outlines_count']}章, "
                       f"角色{stats['characters_count']}个, "
                       f"伏笔{stats.get('foreshadow_count', 0)}个, "
                       f"记忆{stats.get('memory_count', 0)}条, "
                       f"长度{stats['total_length']}字符")
            
            # 设置用户信息以启用MCP
            if user_id:
                user_ai_service.user_id = user_id
                user_ai_service.db_session = db
            
            yield await tracker.generating(
                current_chars=0,
                estimated_total=estimated_chars_per_batch,
                message=f"🤖 调用AI生成第{str(batch_num + 1)}批..."
            )
            
            # 使用标准续写提示词模板（增强版）
            template = await PromptService.get_template("OUTLINE_CONTINUE", user_id or "", db)

            # 构建 world_setting - 使用 world_setting_markdown
            world_setting = project.world_setting_markdown or ""
            if not world_setting:
                # 兜底：如果没有 world_setting_markdown，拼接分散字段
                world_setting = f"时间背景：{project.world_time_period or '未设定'}\n地理位置：{project.world_location or '未设定'}\n氛围基调：{project.world_atmosphere or '未设定'}\n世界规则：{project.world_rules or '未设定'}"

            # 新增：计算章节类型分布统计和节奏建议
            distribution = calculate_chapter_type_distribution(latest_outlines)
            distribution_text = format_distribution_for_prompt(distribution)
            # 获取节奏曲线数据
            rhythm_curve = get_rhythm_curve_data(latest_outlines)
            estimated_total = max(len(latest_outlines) + total_chapters_to_generate, (project.target_words or 100000) // 3000)
            rhythm_suggestions = generate_rhythm_suggestions(
                current_progress=len(latest_outlines),
                total_chapters=estimated_total,
                plot_stage=data.get("plot_stage", "development"),
                distribution=distribution,
                rhythm_curve=rhythm_curve
            )
            progress_percent = round(len(latest_outlines) / max(1, estimated_total) * 100, 1)

            prompt = PromptService.format_prompt(
                template,
                # 基础信息
                title=project.title,
                theme=project.theme or "未设定",
                genre=project.genre or "通用",
                narrative_perspective=project.narrative_perspective or "第三人称",
                world_setting=world_setting,
                # 上下文信息
                recent_outlines=context['recent_outlines'],
                characters_info=context['characters_info'],
                # 新增：伏笔提醒和故事记忆
                foreshadow_reminders=context.get('foreshadow_reminders', ''),
                memory_context=context.get('memory_context', ''),
                # 续写参数
                chapter_count=current_batch_size,
                start_chapter=current_start_chapter,
                end_chapter=current_start_chapter + current_batch_size - 1,
                current_chapter_count=len(latest_outlines),
                plot_stage_instruction=stage_instruction,
                story_direction=data.get("story_direction", "自然延续"),
                requirements=data.get("requirements", ""),
                mcp_references="",
                # 新增：节奏规划参数
                estimated_total_chapters=estimated_total,
                progress_percent=progress_percent,
                plot_stage=data.get("plot_stage", "development"),
                chapter_type_distribution=distribution_text,
                rhythm_suggestions=rhythm_suggestions
            )
            logger.debug(f" 续写提示词: {prompt}")
            # 调用AI生成当前批次
            model_param = data.get("model")
            provider_param = data.get("provider")
            logger.info(f"=== 续写批次{batch_num + 1} AI调用参数 ===")
            logger.info(f"  provider参数: {provider_param}")
            logger.info(f"  model参数: {model_param}")
            
            # 流式生成并累积文本
            accumulated_text = ""
            chunk_count = 0
            
            async for chunk in user_ai_service.generate_text_stream(
                prompt=prompt,
                provider=provider_param,
                model=model_param
            ):
                chunk_count += 1
                accumulated_text += chunk
                
                # 发送内容块
                yield await tracker.generating_chunk(chunk)
                
                # 定期更新进度
                if chunk_count % 10 == 0:
                    yield await tracker.generating(
                        current_chars=len(accumulated_text),
                        estimated_total=estimated_chars_per_batch,
                        message=f"📝 第{str(batch_num + 1)}/{str(total_batches)}批生成中"
                    )
                
                # 每20个块发送心跳
                if chunk_count % 20 == 0:
                    yield await tracker.heartbeat()
            
            yield await tracker.parsing(f"✅ 第{str(batch_num + 1)}批AI生成完成，正在解析...")
            
            # 提取内容
            ai_content = accumulated_text
            ai_response = {"content": ai_content}
            
            # 解析响应（带重试机制）
            max_retries = 2
            retry_count = 0
            outline_data = None
            
            while retry_count <= max_retries:
                try:
                    # 使用 raise_on_error=True，解析失败时抛出异常
                    outline_data = _parse_ai_response(ai_content, raise_on_error=True)
                    break  # 解析成功，跳出循环
                    
                except JSONParseError as e:
                    retry_count += 1
                    if retry_count > max_retries:
                        # 超过最大重试次数，使用fallback数据
                        logger.error(f"❌ 第{batch_num + 1}批解析失败，已达最大重试次数({max_retries})，使用fallback数据")
                        yield await tracker.warning(f"第{str(batch_num + 1)}批解析失败，使用备用数据")
                        outline_data = _parse_ai_response(ai_content, raise_on_error=False)
                        break
                    
                    logger.warning(f"⚠️ 第{batch_num + 1}批JSON解析失败（第{retry_count}次），正在重试...")
                    yield await tracker.retry(retry_count, max_retries, f"第{str(batch_num + 1)}批解析失败")
                    
                    # 重试时重置生成进度
                    tracker.reset_generating_progress()
                    
                    # 重新调用AI生成
                    accumulated_text = ""
                    chunk_count = 0
                    
                    # 在prompt中添加格式强调
                    retry_prompt = prompt + "\n\n【重要提醒】请确保返回完整的JSON数组，不要截断。每个章节对象必须包含完整的title、summary等字段。"
                    
                    async for chunk in user_ai_service.generate_text_stream(
                        prompt=retry_prompt,
                        provider=provider_param,
                        model=model_param
                    ):
                        chunk_count += 1
                        accumulated_text += chunk
                        
                        # 发送内容块
                        yield await tracker.generating_chunk(chunk)
                        
                        # 每20个块发送心跳
                        if chunk_count % 20 == 0:
                            yield await tracker.heartbeat()
                    
                    ai_content = accumulated_text
                    ai_response = {"content": ai_content}
                    logger.info(f"🔄 第{batch_num + 1}批重试生成完成，累计{len(ai_content)}字符")
            
            # 保存当前批次的大纲
            batch_outlines = await _save_outlines(
                project_id, outline_data, db, start_index=current_start_chapter
            )
            
            # 🎭 角色校验：检查本批大纲structure中的characters是否存在对应角色
            try:
                char_check_result = await _check_and_create_missing_characters_from_outlines(
                    outline_data=outline_data,
                    project_id=project_id,
                    db=db,
                    user_ai_service=user_ai_service,
                    user_id=user_id,
                    enable_mcp=data.get("enable_mcp", True),
                    tracker=tracker
                )
                if char_check_result["created_count"] > 0:
                    created_names = [c.name for c in char_check_result["created_characters"]]
                    yield await tracker.saving(
                        f"🎭 第{str(batch_num + 1)}批：自动创建了 {char_check_result['created_count']} 个角色: {', '.join(created_names)}",
                        (batch_num + 1) / total_batches * 0.5
                    )
                    # 更新角色列表（供后续批次使用）
                    characters.extend(char_check_result["created_characters"])
                    characters_info = _build_characters_info(characters)
            except Exception as e:
                logger.error(f"⚠️ 第{batch_num + 1}批角色校验失败（不影响主流程）: {e}")
            
            # 🏛️ 组织校验：检查本批大纲structure中的characters（type=organization）是否存在对应组织
            try:
                org_check_result = await _check_and_create_missing_organizations_from_outlines(
                    outline_data=outline_data,
                    project_id=project_id,
                    db=db,
                    user_ai_service=user_ai_service,
                    user_id=user_id,
                    enable_mcp=data.get("enable_mcp", True),
                    tracker=tracker
                )
                if org_check_result["created_count"] > 0:
                    created_names = [c.name for c in org_check_result["created_organizations"]]
                    yield await tracker.saving(
                        f"🏛️ 第{str(batch_num + 1)}批：自动创建了 {org_check_result['created_count']} 个组织: {', '.join(created_names)}",
                        (batch_num + 1) / total_batches * 0.55
                    )
                    # 更新角色列表（组织也是Character，供后续批次使用）
                    characters.extend(org_check_result["created_organizations"])
                    characters_info = _build_characters_info(characters)
            except Exception as e:
                logger.error(f"⚠️ 第{batch_num + 1}批组织校验失败（不影响主流程）: {e}")
            
            # 记录历史
            history = GenerationHistory(
                project_id=project_id,
                prompt=f"[续写批次{batch_num + 1}/{total_batches}] {str(prompt)[:500]}",
                generated_content=json.dumps(ai_response, ensure_ascii=False) if isinstance(ai_response, dict) else ai_response,
                model=data.get("model") or "default"
            )
            db.add(history)
            
            # 提交当前批次
            await db.commit()
            
            for outline in batch_outlines:
                await db.refresh(outline)
            
            all_new_outlines.extend(batch_outlines)
            current_start_chapter += current_batch_size
            
            yield await tracker.saving(
                f"💾 第{str(batch_num + 1)}批保存成功！本批生成{str(len(batch_outlines))}章，累计新增{str(len(all_new_outlines))}章",
                (batch_num + 1) / total_batches
            )
            
            logger.info(f"第{str(batch_num + 1)}批生成完成，本批生成{str(len(batch_outlines))}章")
        
        db_committed = True
        
        # 返回所有大纲（包括旧的和新的）
        final_result = await db.execute(
            select(Outline)
            .where(Outline.project_id == project_id)
            .order_by(Outline.order_index)
        )
        all_outlines = final_result.scalars().all()
        
        yield await tracker.complete()
        
        # 发送最终结果
        yield await tracker.result({
            "message": f"续写完成！共{str(total_batches)}批，新增{str(len(all_new_outlines))}章，总计{str(len(all_outlines))}章",
            "total_batches": total_batches,
            "new_chapters": len(all_new_outlines),
            "total_chapters": len(all_outlines),
            "outlines": [
                {
                    "id": outline.id,
                    "project_id": outline.project_id,
                    "title": outline.title,
                    "content": outline.content,
                    "order_index": outline.order_index,
                    "structure": outline.structure,
                    "created_at": outline.created_at.isoformat() if outline.created_at else None,
                    "updated_at": outline.updated_at.isoformat() if outline.updated_at else None
                } for outline in all_outlines
            ]
        })
        
        yield await tracker.done()
        
    except GeneratorExit:
        logger.warning("大纲续写生成器被提前关闭")
        if not db_committed and db.in_transaction():
            await db.rollback()
            logger.info("大纲续写事务已回滚（GeneratorExit）")
    except Exception as e:
        logger.error(f"大纲续写失败: {str(e)}")
        if not db_committed and db.in_transaction():
            await db.rollback()
            logger.info("大纲续写事务已回滚（异常）")
        yield await tracker.error(f"续写失败: {str(e)}")


@router.post("/generate-stream", summary="AI生成/续写大纲(SSE流式)")
async def generate_outline_stream(
    data: Dict[str, Any],
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_ai_service: AIService = Depends(get_user_ai_service)
):
    """
    使用SSE流式生成或续写小说大纲，实时推送批次进度
    
    支持模式：
    - auto: 自动判断（无大纲→新建，有大纲→续写）
    - new: 全新生成
    - continue: 续写模式
    
    请求体示例：
    {
        "project_id": "项目ID",
        "chapter_count": 5,  // 章节数
        "mode": "auto",  // auto/new/continue
        "theme": "故事主题",  // new模式必需
        "story_direction": "故事发展方向",  // continue模式可选
        "plot_stage": "development",  // continue模式：development/climax/ending
        "narrative_perspective": "第三人称",
        "requirements": "其他要求",
        "provider": "openai",  // 可选
        "model": "gpt-4"  // 可选
    }
    """
    # 验证用户权限
    user_id = getattr(request.state, 'user_id', None)
    project = await verify_project_access(data.get("project_id"), user_id, db)
    
    # 判断模式
    mode = data.get("mode", "auto")
    
    # 获取现有大纲
    existing_result = await db.execute(
        select(Outline)
        .where(Outline.project_id == data.get("project_id"))
        .order_by(Outline.order_index)
    )
    existing_outlines = existing_result.scalars().all()
    
    # 自动判断模式
    if mode == "auto":
        mode = "continue" if existing_outlines else "new"
        logger.info(f"自动判断模式：{'续写' if existing_outlines else '新建'}")
    
    # 获取用户ID
    user_id = getattr(request.state, "user_id", "system")
    
    # 根据模式选择生成器
    if mode == "new":
        return create_sse_response(new_outline_generator(data, db, user_ai_service))
    elif mode == "continue":
        if not existing_outlines:
            raise HTTPException(
                status_code=400,
                detail="续写模式需要已有大纲，当前项目没有大纲"
            )
        return create_sse_response(continue_outline_generator(data, db, user_ai_service, user_id))
    else:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的模式: {mode}"
        )


async def expand_outline_generator(
    outline_id: str,
    data: Dict[str, Any],
    db: AsyncSession,
    user_ai_service: AIService
) -> AsyncGenerator[str, None]:
    """单个大纲展开SSE生成器 - 实时推送进度（支持分批生成）"""
    db_committed = False
    # 初始化标准进度追踪器
    tracker = WizardProgressTracker("大纲展开")
    
    try:
        yield await tracker.start()
        
        target_chapter_count = int(data.get("target_chapter_count", 3))
        expansion_strategy = data.get("expansion_strategy", "balanced")
        enable_scene_analysis = data.get("enable_scene_analysis", True)
        auto_create_chapters = data.get("auto_create_chapters", False)
        batch_size = int(data.get("batch_size", 5))  # 支持自定义批次大小
        
        # 获取大纲
        yield await tracker.loading("加载大纲信息...", 0.3)
        result = await db.execute(
            select(Outline).where(Outline.id == outline_id)
        )
        outline = result.scalar_one_or_none()
        
        if not outline:
            yield await tracker.error("大纲不存在", 404)
            return
        
        # 获取项目信息
        yield await tracker.loading("加载项目信息...", 0.7)
        project_result = await db.execute(
            select(Project).where(Project.id == outline.project_id)
        )
        project = project_result.scalar_one_or_none()
        if not project:
            yield await tracker.error("项目不存在", 404)
            return
        
        yield await tracker.preparing(
            f"准备展开《{outline.title}》为 {target_chapter_count} 章..."
        )
        
        # 创建展开服务实例
        expansion_service = PlotExpansionService(user_ai_service)
        
        # 分析大纲并生成章节规划（支持分批）
        if target_chapter_count > batch_size:
            yield await tracker.generating(
                current_chars=0,
                estimated_total=target_chapter_count * 500,
                message=f"🤖 AI分批生成章节规划（每批{batch_size}章）..."
            )
        else:
            yield await tracker.generating(
                current_chars=0,
                estimated_total=target_chapter_count * 500,
                message="🤖 AI分析大纲，生成章节规划..."
            )
        
        chapter_plans = await expansion_service.analyze_outline_for_chapters(
            outline=outline,
            project=project,
            db=db,
            target_chapter_count=target_chapter_count,
            expansion_strategy=expansion_strategy,
            enable_scene_analysis=enable_scene_analysis,
            provider=data.get("provider"),
            model=data.get("model"),
            batch_size=batch_size,
            progress_callback=None  # SSE中暂不支持嵌套回调
        )
        
        if not chapter_plans:
            yield await tracker.error("AI分析失败，未能生成章节规划", 500)
            return
        
        yield await tracker.parsing(
            f"✅ 规划生成完成！共 {len(chapter_plans)} 个章节"
        )
        
        # 根据配置决定是否创建章节记录
        created_chapters = None
        if auto_create_chapters:
            yield await tracker.saving("💾 创建章节记录...", 0.3)
            
            created_chapters = await expansion_service.create_chapters_from_plans(
                outline_id=outline_id,
                chapter_plans=chapter_plans,
                project_id=outline.project_id,
                db=db,
                start_chapter_number=None  # 自动计算章节序号
            )
            
            await db.commit()
            db_committed = True
            
            # 刷新章节数据
            for chapter in created_chapters:
                await db.refresh(chapter)
            
            yield await tracker.saving(
                f"✅ 成功创建 {len(created_chapters)} 个章节记录",
                0.8
            )
        
        yield await tracker.complete()
        
        # 构建响应数据
        result_data = {
            "outline_id": outline_id,
            "outline_title": outline.title,
            "target_chapter_count": target_chapter_count,
            "actual_chapter_count": len(chapter_plans),
            "expansion_strategy": expansion_strategy,
            "chapter_plans": chapter_plans,
            "created_chapters": [
                {
                    "id": ch.id,
                    "chapter_number": ch.chapter_number,
                    "title": ch.title,
                    "summary": ch.summary,
                    "outline_id": ch.outline_id,
                    "sub_index": ch.sub_index,
                    "status": ch.status
                }
                for ch in created_chapters
            ] if created_chapters else None
        }
        
        yield await tracker.result(result_data)
        yield await tracker.done()
        
    except GeneratorExit:
        logger.warning("大纲展开生成器被提前关闭")
        if not db_committed and db.in_transaction():
            await db.rollback()
            logger.info("大纲展开事务已回滚（GeneratorExit）")
    except Exception as e:
        logger.error(f"大纲展开失败: {str(e)}")
        if not db_committed and db.in_transaction():
            await db.rollback()
            logger.info("大纲展开事务已回滚（异常）")
        yield await tracker.error(f"展开失败: {str(e)}")


@router.post("/{outline_id}/create-single-chapter", summary="一对一创建章节(传统模式)")
async def create_single_chapter_from_outline(
    outline_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    传统模式：一个大纲对应创建一个章节
    
    适用场景：
    - 项目的outline_mode为'one-to-one'
    - 直接将大纲内容作为章节摘要
    - 不调用AI，不展开
    
    流程：
    1. 验证项目模式为one-to-one
    2. 检查该大纲是否已创建章节
    3. 创建章节记录（outline_id=NULL，chapter_number=outline.order_index）
    
    返回：创建的章节信息
    """
    # 验证用户权限
    user_id = getattr(request.state, 'user_id', None)
    
    # 获取大纲
    result = await db.execute(
        select(Outline).where(Outline.id == outline_id)
    )
    outline = result.scalar_one_or_none()
    
    if not outline:
        raise HTTPException(status_code=404, detail="大纲不存在")
    
    # 验证项目权限并获取项目信息
    project = await verify_project_access(outline.project_id, user_id, db)
    
    # 验证项目模式
    if project.outline_mode != 'one-to-one':
        raise HTTPException(
            status_code=400,
            detail=f"当前项目为{project.outline_mode}模式，不支持一对一创建。请使用展开功能。"
        )
    
    # 检查该大纲对应的章节是否已存在
    existing_chapter_result = await db.execute(
        select(Chapter).where(
            Chapter.project_id == outline.project_id,
            Chapter.chapter_number == outline.order_index,
            Chapter.sub_index == 1
        )
    )
    existing_chapter = existing_chapter_result.scalar_one_or_none()
    
    if existing_chapter:
        raise HTTPException(
            status_code=400,
            detail=f"第{outline.order_index}章已存在，不能重复创建"
        )
    
    try:
        # 创建章节（outline_id=NULL表示一对一模式）
        new_chapter = Chapter(
            project_id=outline.project_id,
            title=outline.title,
            summary=outline.content,  # 使用大纲内容作为摘要
            chapter_number=outline.order_index,
            sub_index=1,  # 一对一模式固定为1
            outline_id=None,  # 传统模式不关联outline_id
            status='pending'
        )
        
        db.add(new_chapter)
        await db.commit()
        await db.refresh(new_chapter)
        
        logger.info(f"一对一模式：为大纲 {outline.title} 创建章节 {new_chapter.chapter_number}")
        
        return {
            "message": "章节创建成功",
            "chapter": {
                "id": new_chapter.id,
                "project_id": new_chapter.project_id,
                "title": new_chapter.title,
                "summary": new_chapter.summary,
                "chapter_number": new_chapter.chapter_number,
                "sub_index": new_chapter.sub_index,
                "outline_id": new_chapter.outline_id,
                "status": new_chapter.status,
                "created_at": new_chapter.created_at.isoformat() if new_chapter.created_at else None
            }
        }
        
    except Exception as e:
        logger.error(f"一对一创建章节失败: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"创建章节失败: {str(e)}")


@router.post("/{outline_id}/expand-stream", summary="展开单个大纲为多章(SSE流式)")
async def expand_outline_to_chapters_stream(
    outline_id: str,
    data: Dict[str, Any],
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_ai_service: AIService = Depends(get_user_ai_service)
):
    """
    使用SSE流式展开单个大纲，实时推送进度
    
    请求体示例：
    {
        "target_chapter_count": 3,  // 目标章节数
        "expansion_strategy": "balanced",  // balanced/climax/detail
        "auto_create_chapters": false,  // 是否自动创建章节
        "enable_scene_analysis": true,  // 是否启用场景分析
        "provider": "openai",  // 可选
        "model": "gpt-4"  // 可选
    }
    
    进度阶段：
    - 5% - 开始展开
    - 10% - 加载大纲信息
    - 15% - 加载项目信息
    - 20% - 准备展开参数
    - 30% - AI分析大纲（耗时）
    - 70% - 规划生成完成
    - 80% - 创建章节记录（如果auto_create_chapters=True）
    - 90% - 创建完成
    - 95% - 整理结果数据
    - 100% - 全部完成
    """
    # 获取大纲并验证权限
    result = await db.execute(
        select(Outline).where(Outline.id == outline_id)
    )
    outline = result.scalar_one_or_none()
    
    if not outline:
        raise HTTPException(status_code=404, detail="大纲不存在")
    
    # 验证用户权限
    user_id = getattr(request.state, 'user_id', None)
    await verify_project_access(outline.project_id, user_id, db)
    
    return create_sse_response(expand_outline_generator(outline_id, data, db, user_ai_service))


@router.get("/{outline_id}/chapters", summary="获取大纲关联的章节")
async def get_outline_chapters(
    outline_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    获取指定大纲已展开的章节列表
    
    用于检查大纲是否已经展开过,如果有则返回章节信息
    """
    # 获取大纲
    result = await db.execute(
        select(Outline).where(Outline.id == outline_id)
    )
    outline = result.scalar_one_or_none()
    
    if not outline:
        raise HTTPException(status_code=404, detail="大纲不存在")
    
    # 验证用户权限
    user_id = getattr(request.state, 'user_id', None)
    await verify_project_access(outline.project_id, user_id, db)
    
    # 查询该大纲关联的章节
    chapters_result = await db.execute(
        select(Chapter)
        .where(Chapter.outline_id == outline_id)
        .order_by(Chapter.sub_index)
    )
    chapters = chapters_result.scalars().all()
    
    # 如果有章节,解析展开规划
    expansion_plans = []
    if chapters:
        for chapter in chapters:
            plan_data = None
            if chapter.expansion_plan:
                try:
                    plan_data = json.loads(chapter.expansion_plan)
                except json.JSONDecodeError:
                    logger.warning(f"章节 {chapter.id} 的expansion_plan解析失败")
                    plan_data = None

            expansion_plans.append({
                "sub_index": chapter.sub_index,
                "title": chapter.title,
                "plot_summary": chapter.summary or "",
                "key_events": plan_data.get("key_events", []) if plan_data else [],
                "character_focus": plan_data.get("character_focus", []) if plan_data else [],
                "emotional_tone": plan_data.get("emotional_tone", "") if plan_data else "",
                "narrative_goal": plan_data.get("narrative_goal", "") if plan_data else "",
                "conflict_type": plan_data.get("conflict_type", "") if plan_data else "",
                "estimated_words": plan_data.get("estimated_words", 0) if plan_data else 0,
                "scenes": plan_data.get("scenes") if plan_data else None,
                "rhythm_intensity": plan_data.get("rhythm_intensity") if plan_data else None,
                "chapter_types": plan_data.get("chapter_types") if plan_data else None,
                "story_lines": plan_data.get("story_lines") if plan_data else None
            })
    
    return {
        "has_chapters": len(chapters) > 0,
        "outline_id": outline_id,
        "outline_title": outline.title,
        "chapter_count": len(chapters),
        "chapters": [
            {
                "id": ch.id,
                "chapter_number": ch.chapter_number,
                "title": ch.title,
                "summary": ch.summary,
                "sub_index": ch.sub_index,
                "status": ch.status,
                "word_count": ch.word_count
            }
            for ch in chapters
        ],
        "expansion_plans": expansion_plans if expansion_plans else None
    }


async def batch_expand_outlines_generator(
    data: Dict[str, Any],
    db: AsyncSession,
    user_ai_service: AIService
) -> AsyncGenerator[str, None]:
    """批量展开大纲SSE生成器 - 实时推送进度"""
    db_committed = False
    # 初始化标准进度追踪器
    tracker = WizardProgressTracker("批量大纲展开")
    
    try:
        yield await tracker.start()
        
        project_id = data.get("project_id")
        chapters_per_outline = int(data.get("chapters_per_outline", 3))
        expansion_strategy = data.get("expansion_strategy", "balanced")
        auto_create_chapters = data.get("auto_create_chapters", False)
        outline_ids = data.get("outline_ids")
        
        # 获取项目信息
        yield await tracker.loading("加载项目信息...", 0.5)
        project_result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = project_result.scalar_one_or_none()
        if not project:
            yield await tracker.error("项目不存在", 404)
            return
        
        # 获取要展开的大纲列表
        yield await tracker.loading("获取大纲列表...", 0.8)
        if outline_ids:
            outlines_result = await db.execute(
                select(Outline)
                .where(
                    Outline.project_id == project_id,
                    Outline.id.in_(outline_ids)
                )
                .order_by(Outline.order_index)
            )
        else:
            outlines_result = await db.execute(
                select(Outline)
                .where(Outline.project_id == project_id)
                .order_by(Outline.order_index)
            )
        
        outlines = outlines_result.scalars().all()
        
        if not outlines:
            yield await tracker.error("没有找到要展开的大纲", 404)
            return
        
        total_outlines = len(outlines)
        yield await tracker.preparing(
            f"共找到 {total_outlines} 个大纲，开始批量展开..."
        )
        
        # 创建展开服务实例
        expansion_service = PlotExpansionService(user_ai_service)
        
        expansion_results = []
        total_chapters_created = 0
        skipped_outlines = []
        
        for idx, outline in enumerate(outlines):
            try:
                # 计算当前子进度 (0.0-1.0)，用于generating阶段
                sub_progress = idx / max(total_outlines, 1)
                
                yield await tracker.generating(
                    current_chars=idx * chapters_per_outline * 500,
                    estimated_total=total_outlines * chapters_per_outline * 500,
                    message=f"📝 处理第 {idx + 1}/{total_outlines} 个大纲: {outline.title}"
                )
                
                # 检查大纲是否已经展开过
                existing_chapters_result = await db.execute(
                    select(Chapter)
                    .where(Chapter.outline_id == outline.id)
                    .limit(1)
                )
                existing_chapter = existing_chapters_result.scalar_one_or_none()
                
                if existing_chapter:
                    logger.info(f"大纲 {outline.title} (ID: {outline.id}) 已经展开过，跳过")
                    skipped_outlines.append({
                        "outline_id": outline.id,
                        "outline_title": outline.title,
                        "reason": "已展开"
                    })
                    yield await tracker.generating(
                        current_chars=(idx + 1) * chapters_per_outline * 500,
                        estimated_total=total_outlines * chapters_per_outline * 500,
                        message=f"⏭️ {outline.title} 已展开过，跳过"
                    )
                    continue
                
                # 分析大纲生成章节规划
                yield await tracker.generating(
                    current_chars=idx * chapters_per_outline * 500,
                    estimated_total=total_outlines * chapters_per_outline * 500,
                    message=f"🤖 AI分析大纲: {outline.title}"
                )
                
                chapter_plans = await expansion_service.analyze_outline_for_chapters(
                    outline=outline,
                    project=project,
                    db=db,
                    target_chapter_count=chapters_per_outline,
                    expansion_strategy=expansion_strategy,
                    enable_scene_analysis=data.get("enable_scene_analysis", True),
                    provider=data.get("provider"),
                    model=data.get("model")
                )
                
                yield await tracker.generating(
                    current_chars=(idx + 0.5) * chapters_per_outline * 500,
                    estimated_total=total_outlines * chapters_per_outline * 500,
                    message=f"✅ {outline.title} 规划生成完成 ({len(chapter_plans)} 章)"
                )
                
                created_chapters = None
                if auto_create_chapters:
                    # 创建章节记录
                    chapters = await expansion_service.create_chapters_from_plans(
                        outline_id=outline.id,
                        chapter_plans=chapter_plans,
                        project_id=outline.project_id,
                        db=db,
                        start_chapter_number=None  # 自动计算章节序号
                    )
                    created_chapters = [
                        {
                            "id": ch.id,
                            "chapter_number": ch.chapter_number,
                            "title": ch.title,
                            "summary": ch.summary,
                            "outline_id": ch.outline_id,
                            "sub_index": ch.sub_index,
                            "status": ch.status
                        }
                        for ch in chapters
                    ]
                    total_chapters_created += len(chapters)
                    
                    yield await tracker.generating(
                        current_chars=(idx + 1) * chapters_per_outline * 500,
                        estimated_total=total_outlines * chapters_per_outline * 500,
                        message=f"💾 {outline.title} 章节创建完成 ({len(chapters)} 章)"
                    )
                
                expansion_results.append({
                    "outline_id": outline.id,
                    "outline_title": outline.title,
                    "target_chapter_count": chapters_per_outline,
                    "actual_chapter_count": len(chapter_plans),
                    "expansion_strategy": expansion_strategy,
                    "chapter_plans": chapter_plans,
                    "created_chapters": created_chapters
                })
                
                logger.info(f"大纲 {outline.title} 展开完成，生成 {len(chapter_plans)} 个章节规划")
                
            except Exception as e:
                logger.error(f"展开大纲 {outline.id} 失败: {str(e)}", exc_info=True)
                yield await tracker.warning(
                    f"❌ {outline.title} 展开失败: {str(e)}"
                )
                expansion_results.append({
                    "outline_id": outline.id,
                    "outline_title": outline.title,
                    "target_chapter_count": chapters_per_outline,
                    "actual_chapter_count": 0,
                    "expansion_strategy": expansion_strategy,
                    "chapter_plans": [],
                    "created_chapters": None,
                    "error": str(e)
                })
        
        yield await tracker.parsing("整理结果数据...")
        
        db_committed = True
        
        logger.info(f"批量展开完成: {len(expansion_results)} 个大纲，跳过 {len(skipped_outlines)} 个，共生成 {total_chapters_created} 个章节")
        
        yield await tracker.complete()
        
        # 发送最终结果
        result_data = {
            "project_id": project_id,
            "total_outlines_expanded": len(expansion_results),
            "total_chapters_created": total_chapters_created,
            "skipped_count": len(skipped_outlines),
            "skipped_outlines": skipped_outlines,
            "expansion_results": [
                {
                    "outline_id": result["outline_id"],
                    "outline_title": result["outline_title"],
                    "target_chapter_count": result["target_chapter_count"],
                    "actual_chapter_count": result["actual_chapter_count"],
                    "expansion_strategy": result["expansion_strategy"],
                    "chapter_plans": result["chapter_plans"],
                    "created_chapters": result.get("created_chapters")
                }
                for result in expansion_results
            ]
        }
        
        yield await tracker.result(result_data)
        yield await tracker.done()
        
    except GeneratorExit:
        logger.warning("批量展开生成器被提前关闭")
        if not db_committed and db.in_transaction():
            await db.rollback()
            logger.info("批量展开事务已回滚（GeneratorExit）")
    except Exception as e:
        logger.error(f"批量展开失败: {str(e)}")
        if not db_committed and db.in_transaction():
            await db.rollback()
            logger.info("批量展开事务已回滚（异常）")
        yield await SSEResponse.send_error(f"批量展开失败: {str(e)}")


@router.post("/batch-expand-stream", summary="批量展开大纲为多章(SSE流式)")
async def batch_expand_outlines_stream(
    data: Dict[str, Any],
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_ai_service: AIService = Depends(get_user_ai_service)
):
    """
    使用SSE流式批量展开大纲，实时推送每个大纲的处理进度
    
    请求体示例：
    {
        "project_id": "项目ID",
        "outline_ids": ["大纲ID1", "大纲ID2"],  // 可选，不传则展开所有大纲
        "chapters_per_outline": 3,  // 每个大纲展开几章
        "expansion_strategy": "balanced",  // balanced/climax/detail
        "auto_create_chapters": false,  // 是否自动创建章节
        "enable_scene_analysis": true,  // 是否启用场景分析
        "provider": "openai",  // 可选
        "model": "gpt-4"  // 可选
    }
    """
    # 验证用户权限
    user_id = getattr(request.state, 'user_id', None)
    await verify_project_access(data.get("project_id"), user_id, db)
    
    return create_sse_response(batch_expand_outlines_generator(data, db, user_ai_service))


@router.post("/{outline_id}/create-chapters-from-plans", response_model=CreateChaptersFromPlansResponse, summary="根据已有规划创建章节")
async def create_chapters_from_existing_plans(
    outline_id: str,
    plans_request: CreateChaptersFromPlansRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_ai_service: AIService = Depends(get_user_ai_service)
):
    """
    根据前端缓存的章节规划直接创建章节记录，避免重复调用AI
    
    使用场景：
    1. 用户第一次调用 /outlines/{outline_id}/expand?auto_create_chapters=false 获取规划预览
    2. 前端展示规划给用户确认
    3. 用户确认后，前端调用此接口，传递缓存的规划数据，直接创建章节
    
    优势：
    - 避免重复的AI调用，节省Token和时间
    - 确保用户看到的预览和实际创建的章节完全一致
    - 提升用户体验
    
    参数：
    - outline_id: 要展开的大纲ID
    - plans_request: 包含之前AI生成的章节规划列表
    
    返回：
    - 创建的章节列表和统计信息
    """
    # 验证用户权限
    user_id = getattr(request.state, 'user_id', None)
    
    # 获取大纲
    result = await db.execute(
        select(Outline).where(Outline.id == outline_id)
    )
    outline = result.scalar_one_or_none()
    
    if not outline:
        raise HTTPException(status_code=404, detail="大纲不存在")
    
    # 验证项目权限
    await verify_project_access(outline.project_id, user_id, db)
    
    try:
        # 验证规划数据
        if not plans_request.chapter_plans:
            raise HTTPException(status_code=400, detail="章节规划列表不能为空")
        
        logger.info(f"根据已有规划为大纲 {outline_id} 创建 {len(plans_request.chapter_plans)} 个章节")
        
        # 创建展开服务实例
        expansion_service = PlotExpansionService(user_ai_service)
        
        # 将Pydantic模型转换为字典列表
        chapter_plans_dict = [plan.model_dump() for plan in plans_request.chapter_plans]
        
        # 直接使用传入的规划创建章节记录（不调用AI）
        created_chapters = await expansion_service.create_chapters_from_plans(
            outline_id=outline_id,
            chapter_plans=chapter_plans_dict,
            project_id=outline.project_id,
            db=db,
            start_chapter_number=None  # 自动计算章节序号
        )
        
        await db.commit()
        
        # 刷新章节数据
        for chapter in created_chapters:
            await db.refresh(chapter)
        
        logger.info(f"成功根据已有规划创建 {len(created_chapters)} 个章节记录")
        
        # 构建响应
        return CreateChaptersFromPlansResponse(
            outline_id=outline_id,
            outline_title=outline.title,
            chapters_created=len(created_chapters),
            created_chapters=[
                {
                    "id": ch.id,
                    "chapter_number": ch.chapter_number,
                    "title": ch.title,
                    "summary": ch.summary,
                    "outline_id": ch.outline_id,
                    "sub_index": ch.sub_index,
                    "status": ch.status
                }
                for ch in created_chapters
            ]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"根据已有规划创建章节失败: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"创建章节失败: {str(e)}")