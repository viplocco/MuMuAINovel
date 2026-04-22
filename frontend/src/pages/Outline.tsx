import { useState, useEffect, useMemo } from 'react';
import { Button, List, Modal, Form, Input, Empty, Space, Popconfirm, Card, Select, Radio, Tag, InputNumber, Tabs, Pagination, theme, App, Progress, Collapse, Tooltip } from 'antd';
import { EditOutlined, DeleteOutlined, ThunderboltOutlined, BranchesOutlined, AppstoreAddOutlined, CheckCircleOutlined, ExclamationCircleOutlined, PlusOutlined, FileTextOutlined, DownOutlined, UpOutlined, BarChartOutlined, LineChartOutlined } from '@ant-design/icons';
import { useStore } from '../store';
import { useOutlineSync } from '../store/hooks';
import { SSEPostClient } from '../utils/sseClient';
import { SSEProgressModal } from '../components/SSEProgressModal';
import { outlineApi, chapterApi, projectApi, characterApi } from '../services/api';
import type { OutlineExpansionResponse, BatchOutlineExpansionResponse, ChapterPlanItem, ApiError, Character, RhythmAnalysisResponse } from '../types';

// 大纲生成请求数据类型
interface OutlineGenerateRequestData {
  project_id: string;
  genre: string;
  theme: string;
  chapter_count: number;
  narrative_perspective: string;
  target_words: number;
  requirements?: string;
  mode: 'auto' | 'new' | 'continue';
  story_direction?: string;
  plot_stage: 'development' | 'climax' | 'ending';
  model?: string;
  provider?: string;
}

// 跳过的大纲信息类型
interface SkippedOutlineInfo {
  outline_id: string;
  outline_title: string;
  reason: string;
}

// 场景类型
interface SceneInfo {
  location: string;
  characters: string[];
  purpose: string;
}

// 角色/组织条目类型（新格式）
interface CharacterEntry {
  name: string;
  type: 'character' | 'organization';
}

/**
 * 解析 characters 字段，兼容新旧格式
 * 旧格式: string[] -> 全部当作 character
 * 新格式: {name: string, type: "character"|"organization"}[]
 */
function parseCharacterEntries(characters: unknown): CharacterEntry[] {
  if (!Array.isArray(characters) || characters.length === 0) return [];
  
  return characters.map((entry) => {
    if (typeof entry === 'string') {
      // 旧格式：纯字符串，默认为 character
      return { name: entry, type: 'character' as const };
    }
    if (typeof entry === 'object' && entry !== null && 'name' in entry) {
      // 新格式：带类型标识的对象
      return {
        name: (entry as { name: string }).name,
        type: ((entry as { type?: string }).type === 'organization' ? 'organization' : 'character') as 'character' | 'organization'
      };
    }
    return null;
  }).filter((e): e is CharacterEntry => e !== null);
}

/** 从 entries 中提取角色名称列表 */
function getCharacterNames(entries: CharacterEntry[]): string[] {
  return entries.filter(e => e.type === 'character').map(e => e.name);
}

/** 从 entries 中提取组织名称列表 */
function getOrganizationNames(entries: CharacterEntry[]): string[] {
  return entries.filter(e => e.type === 'organization').map(e => e.name);
}

interface OutlineStructureData {
  key_events?: string[];
  key_points?: string[];
  characters_involved?: string[];
  characters?: unknown[];
  scenes?: string[] | Array<{
    location: string;
    characters: string[];
    purpose: string;
  }>;
  emotion?: string;
  goal?: string;
  title?: string;
  summary?: string;
  content?: string;
  // 新增：故事线分布相关字段
  chapter_types?: string[];
  story_lines?: string[];
  rhythm_intensity?: number;
  rhythm_range?: string;
}

function parseOutlineStructure(structure?: string): OutlineStructureData {
  if (!structure) return {};
  try {
    return JSON.parse(structure) as OutlineStructureData;
  } catch (e) {
    console.error('解析structure失败:', e);
    return {};
  }
}

const { TextArea } = Input;

/** 节奏建议展示组件 - 结构化渲染节奏分析和后续5章规划 */
function RhythmSuggestionsDisplay({ suggestions, token }: { suggestions: string; token: any }) {
  // 解析建议文本，分为三个部分：策略建议、进度统计、后续5章规划
  const lines = suggestions.split('\n');

  // 找到分隔线位置
  const dividerIndex = lines.findIndex(line => line.startsWith('====='));
  const chapterPlanStart = lines.findIndex(line => line.includes('【后续5章节奏规划建议】'));

  // 策略建议部分
  const strategyLines = dividerIndex >= 0 ? lines.slice(0, dividerIndex) : lines;

  // 后续5章规划部分
  const planLines = chapterPlanStart >= 0 ? lines.slice(chapterPlanStart + 1) : [];

  // 解析章节规划数据
  const chapterPlans: Array<{
    chapterNum: string;
    title: string;
    types: string;
    intensity: string;
    content: string;
    purpose: string;
  }> = [];

  let currentChapter: any = null;
  for (const line of planLines) {
    if (line.startsWith('📖 第')) {
      // 新章节开始
      if (currentChapter) chapterPlans.push(currentChapter);
      const match = line.match(/📖 第(\d+)章：(.+)/);
      if (match) {
        currentChapter = { chapterNum: match[1], title: match[2], types: '', intensity: '', content: '', purpose: '' };
      }
    } else if (currentChapter) {
      if (line.startsWith('   类型：')) {
        currentChapter.types = line.replace('   类型：', '');
      } else if (line.startsWith('   节奏强度：')) {
        currentChapter.intensity = line.replace('   节奏强度：', '');
      } else if (line.startsWith('   建议内容：')) {
        currentChapter.content = line.replace('   建议内容：', '');
      } else if (line.startsWith('   目的：')) {
        currentChapter.purpose = line.replace('   目的：', '');
      }
    }
  }
  if (currentChapter) chapterPlans.push(currentChapter);

  // 根据节奏强度选择颜色
  const getIntensityColor = (intensity: string) => {
    const value = parseInt(intensity.replace('/10', '')) || 5;
    if (value >= 8) return '#ff4d4f'; // 高潮 - 红
    if (value >= 6) return '#faad14'; // 上升 - 黄
    if (value >= 4) return '#1890ff'; // 中等 - 蓝
    return '#52c41a'; // 低 - 绿
  };

  // 根据类型选择颜色
  const getTypeColor = (types: string) => {
    if (types.includes('大高潮')) return 'red';
    if (types.includes('小高潮')) return 'orange';
    if (types.includes('过渡')) return 'green';
    if (types.includes('支线')) return 'cyan';
    if (types.includes('奇遇') || types.includes('秘境')) return 'purple';
    return 'blue';
  };

  return (
    <div>
      {/* 策略建议部分 */}
      {strategyLines.map((line, idx) => {
        const isTitle = line.startsWith('【') && line.includes('】');
        const isListItem = line.trim().startsWith('•');
        const isEmphasis = line.trim().startsWith('⚠️') || line.trim().startsWith('✅');

        if (!line.trim()) return null;

        return (
          <div key={idx} style={{
            fontWeight: isTitle ? 600 : 400,
            color: isTitle ? token.colorPrimary : isEmphasis ? token.colorInfoText : token.colorTextSecondary,
            marginTop: isTitle && idx > 0 ? 8 : 0,
            marginBottom: isListItem ? 2 : 0,
            paddingLeft: isListItem ? 8 : 0,
          }}>
            {line}
          </div>
        );
      })}

      {/* 进度统计 */}
      {planLines.filter(line => line.startsWith('📊')).map((line, idx) => (
        <div key={`progress-${idx}`} style={{
          fontWeight: 500,
          color: token.colorPrimary,
          marginTop: 16,
          marginBottom: 12,
          fontSize: 14
        }}>
          {line}
        </div>
      ))}

      {/* 后续5章规划卡片 */}
      {chapterPlans.length > 0 && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: 12,
          marginTop: 12
        }}>
          {chapterPlans.map((plan, idx) => (
            <div key={idx} style={{
              background: token.colorBgContainer,
              borderRadius: token.borderRadius,
              border: `1px solid ${getIntensityColor(plan.intensity)}30`,
              padding: '12px 14px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.08)'
            }}>
              {/* 章节号和标题 */}
              <div style={{
                fontWeight: 600,
                color: getIntensityColor(plan.intensity),
                marginBottom: 8,
                display: 'flex',
                alignItems: 'center',
                gap: 6
              }}>
                <span style={{
                  background: getIntensityColor(plan.intensity),
                  color: '#fff',
                  padding: '2px 8px',
                  borderRadius: 4,
                  fontSize: 12
                }}>
                  第{plan.chapterNum}章
                </span>
                <span style={{ fontSize: 13 }}>{plan.title}</span>
              </div>

              {/* 类型标签 */}
              <div style={{ marginBottom: 6 }}>
                <Tag color={getTypeColor(plan.types)} style={{ margin: 0 }}>
                  {plan.types.split('/')[0].trim()}
                </Tag>
              </div>

              {/* 节奏强度 */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                marginBottom: 6
              }}>
                <Progress
                  percent={parseInt(plan.intensity.replace('/10', '')) * 10 || 50}
                  strokeColor={getIntensityColor(plan.intensity)}
                  trailColor={getIntensityColor(plan.intensity) + '20'}
                  showInfo={false}
                  size="small"
                  style={{ flex: 1 }}
                />
                <span style={{
                  color: getIntensityColor(plan.intensity),
                  fontWeight: 500,
                  fontSize: 12
                }}>
                  {plan.intensity}
                </span>
              </div>

              {/* 建议内容 */}
              <div style={{
                color: token.colorTextSecondary,
                fontSize: 12,
                lineHeight: 1.6,
                marginBottom: 4
              }}>
                📝 {plan.content}
              </div>

              {/* 目的 */}
              <div style={{
                color: token.colorTextTertiary,
                fontSize: 11
              }}>
                🎯 {plan.purpose}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Outline() {
  const { message } = App.useApp();
  const { currentProject, outlines, setCurrentProject } = useStore();
  const [isGenerating, setIsGenerating] = useState(false);
  const [editForm] = Form.useForm();
  const [generateForm] = Form.useForm();
  const [expansionForm] = Form.useForm();
  const [modalApi, contextHolder] = Modal.useModal();
  const [batchExpansionForm] = Form.useForm();
  const [manualCreateForm] = Form.useForm();
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);
  const [isExpanding, setIsExpanding] = useState(false);
  const [projectCharacters, setProjectCharacters] = useState<Array<{ label: string; value: string }>>([]);
  const { token } = theme.useToken();
  const alphaColor = (color: string, alpha: number) =>
    `color-mix(in srgb, ${color} ${(alpha * 100).toFixed(0)}%, transparent)`;

  // ✅ 新增：记录场景区域的展开/折叠状态
  const [scenesExpandStatus, setScenesExpandStatus] = useState<Record<string, boolean>>({});

  // ✅ 新增：记录大纲卡片内容区域的展开/折叠状态
  const [outlineCardExpanded, setOutlineCardExpanded] = useState<Record<string, boolean>>({});

  // 缓存批量展开的规划数据，避免重复AI调用
  const [cachedBatchExpansionResponse, setCachedBatchExpansionResponse] = useState<BatchOutlineExpansionResponse | null>(null);

  // 批量展开预览的状态
  const [batchPreviewVisible, setBatchPreviewVisible] = useState(false);
  const [batchPreviewData, setBatchPreviewData] = useState<BatchOutlineExpansionResponse | null>(null);
  const [selectedOutlineIdx, setSelectedOutlineIdx] = useState(0);
  const [selectedChapterIdx, setSelectedChapterIdx] = useState(0);

  // 节奏分析数据状态
  const [rhythmAnalysis, setRhythmAnalysis] = useState<RhythmAnalysisResponse | null>(null);
  const [rhythmLoading, setRhythmLoading] = useState(false);

  // SSE进度状态
  const [sseProgress, setSSEProgress] = useState(0);
  const [sseMessage, setSSEMessage] = useState('');
  const [sseModalVisible, setSSEModalVisible] = useState(false);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768);
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // 大纲查询与分页状态
  const [outlineSearchKeyword, setOutlineSearchKeyword] = useState('');
  const [outlinePage, setOutlinePage] = useState(1);
  const [outlinePageSize, setOutlinePageSize] = useState(20);

  // 使用同步 hooks
  const {
    refreshOutlines,
    updateOutline,
    deleteOutline
  } = useOutlineSync();

  // 初始加载大纲列表和角色列表
  useEffect(() => {
    if (currentProject?.id) {
      refreshOutlines();
      // 加载项目角色列表
      loadProjectCharacters();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentProject?.id]); // 只依赖 ID，不依赖函数

  // 加载项目角色列表
  const loadProjectCharacters = async () => {
    if (!currentProject?.id) return;
    try {
      const characters = await characterApi.getCharacters(currentProject.id);
      setProjectCharacters(
        characters.map((char: Character) => ({
          label: char.name,
          value: char.name
        }))
      );
    } catch (error) {
      console.error('加载角色列表失败:', error);
    }
  };

  // 加载节奏分析数据
  const loadRhythmAnalysis = async () => {
    if (!currentProject?.id || outlines.length === 0) return;
    setRhythmLoading(true);
    try {
      const data = await outlineApi.getRhythmAnalysis(currentProject.id);
      setRhythmAnalysis(data);
    } catch (error) {
      console.error('加载节奏分析失败:', error);
    } finally {
      setRhythmLoading(false);
    }
  };

  // 当大纲数据变化时加载节奏分析
  useEffect(() => {
    if (currentProject?.id && outlines.length > 0) {
      loadRhythmAnalysis();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentProject?.id, outlines.length]);

  // 从后端返回字段直接构建展开状态，避免前端 N+1 请求
  const outlineExpandStatus = useMemo(() => {
    const statusMap: Record<string, boolean> = {};
    outlines.forEach((outline) => {
      statusMap[outline.id] = Boolean(outline.has_chapters);
    });
    return statusMap;
  }, [outlines]);

  // 统一预解析 structure，避免 render 阶段重复 JSON.parse
  const outlineStructureMap = useMemo(() => {
    const parsedMap: Record<string, OutlineStructureData> = {};
    outlines.forEach((outline) => {
      parsedMap[outline.id] = parseOutlineStructure(outline.structure);
    });
    return parsedMap;
  }, [outlines]);

  // 当角色确认数据变化时，初始化选中状态（默认全选）
  // 当组织确认数据变化时，初始化选中状态（默认全选）
  // 移除事件监听，避免无限循环
  // Hook 内部已经更新了 store，不需要再次刷新

  // 确保大纲按 order_index 排序
  const sortedOutlines = [...outlines].sort((a, b) => a.order_index - b.order_index);

  // 前端查询过滤
  const filteredOutlines = useMemo(() => {
    const keyword = outlineSearchKeyword.trim().toLowerCase();
    if (!keyword) return sortedOutlines;

    return sortedOutlines.filter((outline) => {
      return (
        String(outline.order_index).includes(keyword) ||
        outline.title.toLowerCase().includes(keyword) ||
        outline.content.toLowerCase().includes(keyword)
      );
    });
  }, [sortedOutlines, outlineSearchKeyword]);

  // 当前分页数据
  const pagedOutlines = useMemo(() => {
    const start = (outlinePage - 1) * outlinePageSize;
    return filteredOutlines.slice(start, start + outlinePageSize);
  }, [filteredOutlines, outlinePage, outlinePageSize]);

  // 搜索词或页大小变化时，回到第一页
  useEffect(() => {
    setOutlinePage(1);
  }, [outlineSearchKeyword, outlinePageSize]);

  // 数据变化导致页码越界时自动纠正
  useEffect(() => {
    const maxPage = Math.max(1, Math.ceil(filteredOutlines.length / outlinePageSize));
    if (outlinePage > maxPage) {
      setOutlinePage(maxPage);
    }
  }, [filteredOutlines.length, outlinePage, outlinePageSize]);

  if (!currentProject) return null;

  const handleOpenEditModal = (id: string) => {
    const outline = outlines.find(o => o.id === id);
    if (outline) {
      const structureData = outlineStructureMap[outline.id] || {};
      
      // 解析角色/组织条目（兼容新旧格式）
      const editEntries = parseCharacterEntries(structureData.characters);
      const editCharNames = getCharacterNames(editEntries);
      const editOrgNames = getOrganizationNames(editEntries);
      
      // 处理场景数据 - 可能是字符串数组或对象数组
      let scenesText = '';
      if (structureData.scenes) {
        if (typeof structureData.scenes[0] === 'string') {
          // 字符串数组格式
          scenesText = (structureData.scenes as string[]).join('\n');
        } else {
          // 对象数组格式
          scenesText = (structureData.scenes as Array<{location: string; characters: string[]; purpose: string}>)
            .map(s => `${s.location}|${(s.characters || []).join('、')}|${s.purpose}`)
            .join('\n');
        }
      }
      
      // 处理情节要点数据
      const keyPointsText = structureData.key_points ? structureData.key_points.join('\n') : '';
      
      // 设置表单初始值
      editForm.setFieldsValue({
        title: outline.title,
        content: outline.content,
        characters: editCharNames,
        organizations: editOrgNames,
        scenes: scenesText,
        key_points: keyPointsText,
        emotion: structureData.emotion || '',
        goal: structureData.goal || ''
      });
      
      modalApi.confirm({
        title: '编辑大纲',
        width: 800,
        centered: true,
        closable: true,
        maskClosable: false,
        rootClassName: 'modal-fixed-header-footer',
        content: (
          <Form
            form={editForm}
            layout="vertical"
            style={{ marginTop: 12 }}
          >
            <Form.Item
              label="标题"
              name="title"
              rules={[{ required: true, message: '请输入标题' }]}
              style={{ marginBottom: 12 }}
            >
              <Input placeholder="输入大纲标题" />
            </Form.Item>

            <Form.Item
              label="内容"
              name="content"
              rules={[{ required: true, message: '请输入内容' }]}
              style={{ marginBottom: 12 }}
            >
              <TextArea rows={4} placeholder="输入大纲内容..." />
            </Form.Item>
            
            <Form.Item
              label="涉及角色"
              name="characters"
              tooltip="从项目角色中选择，也可以手动输入新角色名"
              style={{ marginBottom: 12 }}
            >
              <Select
                mode="tags"
                style={{ width: '100%' }}
                placeholder="选择或输入角色名"
                options={projectCharacters}
                tokenSeparators={[',', '，']}
                maxTagCount="responsive"
              />
            </Form.Item>
            
            <Form.Item
              label="涉及组织"
              name="organizations"
              tooltip="从项目组织中选择，也可以手动输入新组织名"
              style={{ marginBottom: 12 }}
            >
              <Select
                mode="tags"
                style={{ width: '100%' }}
                placeholder="选择或输入组织/势力名"
                tokenSeparators={[',', '，']}
                maxTagCount="responsive"
              />
            </Form.Item>
            
            <Form.Item
              label="场景信息"
              name="scenes"
              tooltip="支持两种格式：简单描述（每行一个场景）或详细格式（地点|角色|目的）"
              style={{ marginBottom: 12 }}
            >
              <TextArea
                rows={3}
                placeholder="每行一个场景&#10;详细格式：地点|角色1、角色2|目的"
              />
            </Form.Item>
            
            <Form.Item
              label="情节要点"
              name="key_points"
              tooltip="每行一个情节要点"
              style={{ marginBottom: 12 }}
            >
              <TextArea
                rows={2}
                placeholder="每行一个情节要点"
              />
            </Form.Item>
            
            <Form.Item
              label="情感基调"
              name="emotion"
              tooltip="描述本章的情感氛围"
              style={{ marginBottom: 12 }}
            >
              <Input placeholder="例如：冷冽与躁动并存" />
            </Form.Item>
            
            <Form.Item
              label="叙事目标"
              name="goal"
              tooltip="本章要达成的叙事目的"
              style={{ marginBottom: 0 }}
            >
              <Input placeholder="例如：建立世界观对比并完成主角初遇" />
            </Form.Item>
          </Form>
        ),
        okText: '保存',
        cancelText: '取消',
        onOk: async () => {
          const values = await editForm.validateFields();
          try {
            // 解析并重构structure数据（使用预解析缓存，避免重复 JSON.parse）
            const originalStructure = outlineStructureMap[outline.id] || {};
            
            // 处理角色和组织数据 - 合并为带类型标识的新格式
            const charNames = Array.isArray(values.characters)
              ? values.characters.filter((c: string) => c && c.trim())
              : [];
            const orgNames = Array.isArray(values.organizations)
              ? values.organizations.filter((c: string) => c && c.trim())
              : [];
            const characters: CharacterEntry[] = [
              ...charNames.map((name: string) => ({ name: name.trim(), type: 'character' as const })),
              ...orgNames.map((name: string) => ({ name: name.trim(), type: 'organization' as const }))
            ];
            
            // 处理场景数据 - 检测原始格式
            let scenes: string[] | Array<{location: string; characters: string[]; purpose: string}> | undefined;
            if (values.scenes) {
              const lines = values.scenes.split('\n')
                .map((line: string) => line.trim())
                .filter((line: string) => line);
              
              // 检查是否包含管道符，判断格式
              const hasStructuredFormat = lines.some((line: string) => line.includes('|'));
              
              if (hasStructuredFormat) {
                // 尝试解析为对象数组格式
                scenes = lines
                  .map((line: string) => {
                    const parts = line.split('|');
                    if (parts.length >= 3) {
                      return {
                        location: parts[0].trim(),
                        characters: parts[1].split('、').map(c => c.trim()).filter(c => c),
                        purpose: parts[2].trim()
                      };
                    }
                    return null;
                  })
                  .filter((s: { location: string; characters: string[]; purpose: string } | null): s is { location: string; characters: string[]; purpose: string } => s !== null);
              } else {
                // 保持字符串数组格式
                scenes = lines;
              }
            }
            
            // 处理情节要点数据
            const keyPoints = values.key_points
              ? values.key_points.split('\n')
                  .map((line: string) => line.trim())
                  .filter((line: string) => line)
              : undefined;
            
            // 合并structure数据，只包含AI实际生成的字段
            const newStructure = {
              ...originalStructure,
              title: values.title,
              summary: values.content,
              characters: characters.length > 0 ? characters : undefined,
              scenes: scenes && scenes.length > 0 ? scenes : undefined,
              key_points: keyPoints && keyPoints.length > 0 ? keyPoints : undefined,
              emotion: values.emotion || undefined,
              goal: values.goal || undefined
            };
            
            // 更新大纲
            await updateOutline(id, {
              title: values.title,
              content: values.content,
              structure: JSON.stringify(newStructure, null, 2)
            });
            
            message.success('大纲更新成功');
          } catch (error) {
            console.error('更新失败:', error);
            message.error('更新失败');
          }
        },
      });
    }
  };

  const handleDeleteOutline = async (id: string) => {
    try {
      await deleteOutline(id);
      message.success('删除成功');
      // 删除后刷新大纲列表和项目信息，更新字数显示
      await refreshOutlines();
      if (currentProject?.id) {
        const updatedProject = await projectApi.getProject(currentProject.id);
        setCurrentProject(updatedProject);
      }
    } catch {
      message.error('删除失败');
    }
  };

  interface GenerateFormValues {
    theme?: string;
    chapter_count?: number;
    narrative_perspective?: string;
    requirements?: string;
    provider?: string;
    model?: string;
    mode?: 'auto' | 'new' | 'continue';
    story_direction?: string;
    plot_stage?: 'development' | 'climax' | 'ending';
    keep_existing?: boolean;
  }

  const handleGenerate = async (values: GenerateFormValues) => {
    try {
      setIsGenerating(true);

      // 添加详细的调试日志
      console.log('=== 大纲生成调试信息 ===');
      console.log('1. Form values 原始数据:', values);
      console.log('2. values.model:', values.model);
      console.log('3. values.provider:', values.provider);

      // 关闭生成表单Modal
      Modal.destroyAll();

      // 显示进度Modal
      setSSEProgress(0);
      setSSEMessage('正在连接AI服务...');
      setSSEModalVisible(true);

      // 准备请求数据
      const requestData: OutlineGenerateRequestData = {
        project_id: currentProject.id,
        genre: currentProject.genre || '通用',
        theme: values.theme || currentProject.theme || '',
        chapter_count: values.chapter_count || 5,
        narrative_perspective: values.narrative_perspective || currentProject.narrative_perspective || '第三人称',
        target_words: currentProject.target_words || 100000,
        requirements: values.requirements,
        mode: values.mode || 'auto',
        story_direction: values.story_direction,
        plot_stage: values.plot_stage || 'development'
      };

      // 只有在用户选择了模型时才添加model参数
      if (values.model) {
        requestData.model = values.model;
        console.log('4. 添加model到请求:', values.model);
      } else {
        console.log('4. values.model为空，不添加到请求');
      }

      // 添加provider参数（如果有）
      if (values.provider) {
        requestData.provider = values.provider;
        console.log('5. 添加provider到请求:', values.provider);
      }

      console.log('6. 最终请求数据:', JSON.stringify(requestData, null, 2));
      console.log('=========================');

      // 使用SSE客户端
      const apiUrl = `/api/outlines/generate-stream`;
      const client = new SSEPostClient(apiUrl, requestData, {
        onProgress: (msg: string, progress: number) => {
          setSSEMessage(msg);
          setSSEProgress(progress);
        },
        onResult: (data: unknown) => {
          console.log('生成完成，结果:', data);
        },
        onError: (error: string) => {
          // 现在只处理真正的错误
          message.error(`生成失败: ${error}`);
          setSSEModalVisible(false);
          setIsGenerating(false);
        },
        onComplete: () => {
          message.success('大纲生成完成！');
          setSSEModalVisible(false);
          setIsGenerating(false);
          // 刷新大纲列表
          refreshOutlines();
        }
      });

      // 开始连接
      client.connect();

    } catch (error) {
      console.error('AI生成失败:', error);
      message.error('AI生成失败');
      setSSEModalVisible(false);
      setIsGenerating(false);
    }
  };

  const showGenerateModal = async () => {
    const hasOutlines = outlines.length > 0;
    const initialMode = hasOutlines ? 'continue' : 'new';

    // 直接加载可用模型列表
    const settingsResponse = await fetch('/api/settings');
    const settings = await settingsResponse.json();
    const { api_key, api_base_url, api_provider } = settings;

    let loadedModels: Array<{ value: string, label: string }> = [];
    let defaultModel: string | undefined = undefined;

    if (api_key && api_base_url) {
      try {
        const modelsResponse = await fetch(
          `/api/settings/models?api_key=${encodeURIComponent(api_key)}&api_base_url=${encodeURIComponent(api_base_url)}&provider=${api_provider}`
        );
        if (modelsResponse.ok) {
          const data = await modelsResponse.json();
          if (data.models && data.models.length > 0) {
            loadedModels = data.models;
            defaultModel = settings.llm_model;
          }
        }
      } catch {
        console.log('获取模型列表失败，将使用默认模型');
      }
    }

    modalApi.confirm({
      title: hasOutlines ? (
        <Space>
          <span>AI生成/续写大纲</span>
          <Tag color="blue">当前已有 {outlines.length} 卷</Tag>
        </Space>
      ) : 'AI生成大纲',
      width: 700,
      centered: true,
      content: (
        <Form
          form={generateForm}
          layout="vertical"
          style={{ marginTop: 16 }}
          initialValues={{
            mode: initialMode,
            chapter_count: 5,
            narrative_perspective: currentProject.narrative_perspective || '第三人称',
            plot_stage: 'development',
            keep_existing: true,
            theme: currentProject.theme || '',
            model: defaultModel,
          }}
        >
          {hasOutlines && (
            <Form.Item
              label="生成模式"
              name="mode"
              tooltip="自动判断：根据是否有大纲自动选择；全新生成：删除旧大纲重新生成；续写模式：基于已有大纲继续创作"
            >
              <Radio.Group buttonStyle="solid">
                <Radio.Button value="auto">自动判断</Radio.Button>
                <Radio.Button value="new">全新生成</Radio.Button>
                <Radio.Button value="continue">续写模式</Radio.Button>
              </Radio.Group>
            </Form.Item>
          )}

          <Form.Item
            noStyle
            shouldUpdate={(prevValues, currentValues) => prevValues.mode !== currentValues.mode}
          >
            {({ getFieldValue }) => {
              const mode = getFieldValue('mode');
              const isContinue = mode === 'continue' || (mode === 'auto' && hasOutlines);

              // 续写模式不显示主题输入，使用项目原有主题
              if (isContinue) {
                return null;
              }

              // 全新生成模式需要输入主题
              return (
                <Form.Item
                  label="故事主题"
                  name="theme"
                  rules={[{ required: true, message: '请输入故事主题' }]}
                >
                  <TextArea rows={3} placeholder="描述你的故事主题、核心设定和主要情节..." />
                </Form.Item>
              );
            }}
          </Form.Item>

          <Form.Item
            noStyle
            shouldUpdate={(prevValues, currentValues) => prevValues.mode !== currentValues.mode}
          >
            {({ getFieldValue }) => {
              const mode = getFieldValue('mode');
              const isContinue = mode === 'continue' || (mode === 'auto' && hasOutlines);

              return (
                <>
                  {isContinue && (
                    <>
                      <Form.Item
                        label="故事发展方向"
                        name="story_direction"
                        tooltip="告诉AI你希望故事接下来如何发展"
                      >
                        <TextArea
                          rows={3}
                          placeholder="例如：主角遇到新的挑战、引入新角色、揭示关键秘密等..."
                        />
                      </Form.Item>

                      <Form.Item
                        label="情节阶段"
                        name="plot_stage"
                        tooltip="帮助AI理解当前故事所处的阶段"
                      >
                        <Select>
                          <Select.Option value="development">发展阶段 - 继续展开情节</Select.Option>
                          <Select.Option value="climax">高潮阶段 - 矛盾激化</Select.Option>
                          <Select.Option value="ending">结局阶段 - 收束伏笔</Select.Option>
                        </Select>
                      </Form.Item>
                    </>
                  )}

                  <Form.Item
                    label={isContinue ? "续写章节数" : "章节数量"}
                    name="chapter_count"
                    rules={[{ required: true, message: '请输入章节数量' }]}
                  >
                    <Input
                      type="number"
                      min={1}
                      max={50}
                      placeholder={isContinue ? "建议5-10章" : "如：30"}
                    />
                  </Form.Item>

                  <Form.Item
                    label="叙事视角"
                    name="narrative_perspective"
                    rules={[{ required: true, message: '请选择叙事视角' }]}
                  >
                    <Select>
                      <Select.Option value="第一人称">第一人称</Select.Option>
                      <Select.Option value="第三人称">第三人称</Select.Option>
                      <Select.Option value="全知视角">全知视角</Select.Option>
                    </Select>
                  </Form.Item>

                  <Form.Item label="其他要求" name="requirements">
                    <TextArea rows={2} placeholder="其他特殊要求（可选）" />
                  </Form.Item>

                </>
              );
            }}
          </Form.Item>

          {/* 自定义模型选择 - 移到外层，所有模式都显示 */}
          {loadedModels.length > 0 && (
            <Form.Item
              label="AI模型"
              tooltip="选择用于生成的AI模型，不选则使用系统默认模型"
            >
              <Form.Item name="model" noStyle>
                <Select
                  placeholder={defaultModel ? `默认: ${loadedModels.find(m => m.value === defaultModel)?.label || defaultModel}` : "使用默认模型"}
                  allowClear
                  showSearch
                  optionFilterProp="label"
                  options={loadedModels}
                  onChange={(value) => {
                    console.log('用户在下拉框中选择了模型:', value);
                    // 手动同步到Form
                    generateForm.setFieldsValue({ model: value });
                    console.log('已同步到Form，当前Form值:', generateForm.getFieldsValue());
                  }}
                />
              </Form.Item>
              <div style={{ color: token.colorTextTertiary, fontSize: 12, marginTop: 4 }}>
                {defaultModel ? `当前默认模型: ${loadedModels.find(m => m.value === defaultModel)?.label || defaultModel}` : '未配置默认模型'}
              </div>
            </Form.Item>
          )}
        </Form>
      ),
      okText: hasOutlines ? '开始续写' : '开始生成',
      cancelText: '取消',
      onOk: async () => {
        const values = await generateForm.validateFields();
        await handleGenerate(values);
      },
    });
  };

  // 手动创建大纲
  const showManualCreateOutlineModal = () => {
    const nextOrderIndex = outlines.length > 0
      ? Math.max(...outlines.map(o => o.order_index)) + 1
      : 1;

    modalApi.confirm({
      title: '手动创建大纲',
      width: 600,
      centered: true,
      content: (
        <Form
          form={manualCreateForm}
          layout="vertical"
          initialValues={{ order_index: nextOrderIndex }}
          style={{ marginTop: 16 }}
        >
          <Form.Item
            label="大纲序号"
            name="order_index"
            rules={[{ required: true, message: '请输入序号' }]}
            tooltip={currentProject?.outline_mode === 'one-to-one' ? '在传统模式下，序号即章节编号' : '在细化模式下，序号为卷数'}
          >
            <InputNumber min={1} style={{ width: '100%' }} placeholder="自动计算的下一个序号" />
          </Form.Item>

          <Form.Item
            label="大纲标题"
            name="title"
            rules={[{ required: true, message: '请输入标题' }]}
          >
            <Input placeholder={currentProject?.outline_mode === 'one-to-one' ? '例如：第一章 初入江湖' : '例如：第一卷 初入江湖'} />
          </Form.Item>

          <Form.Item
            label="大纲内容"
            name="content"
            rules={[{ required: true, message: '请输入内容' }]}
          >
            <TextArea
              rows={6}
              placeholder="描述本章/卷的主要情节和发展方向..."
            />
          </Form.Item>
        </Form>
      ),
      okText: '创建',
      cancelText: '取消',
      onOk: async () => {
        const values = await manualCreateForm.validateFields();

        // 校验序号是否重复
        const existingOutline = outlines.find(o => o.order_index === values.order_index);
        if (existingOutline) {
          modalApi.warning({
            title: '序号冲突',
            content: (
              <div>
                <p>序号 <strong>{values.order_index}</strong> 已被使用：</p>
                <div style={{
                  padding: 12,
                  background: token.colorWarningBg,
                  borderRadius: token.borderRadius,
                  border: `1px solid ${token.colorWarningBorder}`,
                  marginTop: 8
                }}>
                  <div style={{ fontWeight: 500, color: token.colorWarning }}>
                    {currentProject?.outline_mode === 'one-to-one'
                      ? `第${existingOutline.order_index}章`
                      : `第${existingOutline.order_index}卷`
                    }：{existingOutline.title}
                  </div>
                </div>
                <p style={{ marginTop: 12, color: token.colorTextSecondary }}>
                  💡 建议使用序号 <strong>{nextOrderIndex}</strong>，或选择其他未使用的序号
                </p>
              </div>
            ),
            okText: '我知道了',
            centered: true
          });
          throw new Error('序号重复');
        }

        try {
          await outlineApi.createOutline({
            project_id: currentProject.id,
            ...values
          });
          message.success('大纲创建成功');
          await refreshOutlines();
          manualCreateForm.resetFields();
        } catch (error: unknown) {
          const err = error as Error;
          if (err.message === '序号重复') {
            // 序号重复错误已经显示了Modal，不需要再显示message
            throw error;
          }
          message.error('创建失败：' + (err.message || '未知错误'));
          throw error;
        }
      }
    });
  };

  // 展开单个大纲为多章 - 使用SSE显示进度
  const handleExpandOutline = async (outlineId: string, outlineTitle: string) => {
    try {
      setIsExpanding(true);

      // ✅ 新增：检查是否需要按顺序展开
      const currentOutline = sortedOutlines.find(o => o.id === outlineId);
      if (currentOutline) {
        // 获取所有在当前大纲之前的大纲
        const previousOutlines = sortedOutlines.filter(
          o => o.order_index < currentOutline.order_index
        );

        // 检查前面的大纲是否都已展开
        for (const prevOutline of previousOutlines) {
          try {
            const prevChapters = await outlineApi.getOutlineChapters(prevOutline.id);
            if (!prevChapters.has_chapters) {
              // 如果前面有未展开的大纲，显示提示并阻止操作
              setIsExpanding(false);
              modalApi.warning({
                title: '请按顺序展开大纲',
                width: 600,
                centered: true,
                content: (
                  <div>
                    <p style={{ marginBottom: 12 }}>
                      为了保持章节编号的连续性和内容的连贯性，请先展开前面的大纲。
                    </p>
                    <div style={{
                      padding: 12,
                      background: token.colorWarningBg,
                      borderRadius: token.borderRadius,
                      border: `1px solid ${token.colorWarningBorder}`
                    }}>
                      <div style={{ fontWeight: 500, marginBottom: 8, color: token.colorWarning }}>
                        ⚠️ 需要先展开：
                      </div>
                      <div style={{ color: token.colorTextSecondary }}>
                        第{prevOutline.order_index}卷：《{prevOutline.title}》
                      </div>
                    </div>
                    <p style={{ marginTop: 12, color: token.colorTextSecondary, fontSize: 13 }}>
                      💡 提示：您也可以使用「批量展开」功能，系统会自动按顺序处理所有大纲。
                    </p>
                  </div>
                ),
                okText: '我知道了'
              });
              return;
            }
          } catch (error) {
            console.error(`检查大纲 ${prevOutline.id} 失败:`, error);
            // 如果检查失败，继续处理（避免因网络问题阻塞）
          }
        }
      }

      // 第一步：检查是否已有展开的章节
      const existingChapters = await outlineApi.getOutlineChapters(outlineId);

      if (existingChapters.has_chapters && existingChapters.expansion_plans && existingChapters.expansion_plans.length > 0) {
        // 如果已有章节，显示已有的展开规划信息
        setIsExpanding(false);
        showExistingExpansionPreview(outlineTitle, existingChapters);
        return;
      }

      // 如果没有章节，显示展开表单
      setIsExpanding(false);
      modalApi.confirm({
        title: (
          <Space>
            <BranchesOutlined />
            <span>展开大纲为多章</span>
          </Space>
        ),
        width: 600,
        centered: true,
        content: (
          <div>
            <div style={{ marginBottom: 16, padding: 12, background: token.colorBgLayout, borderRadius: token.borderRadius }}>
              <div style={{ fontWeight: 500, marginBottom: 4 }}>大纲标题</div>
              <div style={{ color: token.colorTextSecondary }}>{outlineTitle}</div>
            </div>
            <Form
              form={expansionForm}
              layout="vertical"
              initialValues={{
                target_chapter_count: 3,
                expansion_strategy: 'auto',
              }}
            >
              <Form.Item
                label="目标章节数"
                name="target_chapter_count"
                rules={[{ required: true, message: '请输入目标章节数' }]}
                tooltip="将这个大纲展开为几章内容"
              >
                <InputNumber
                  min={2}
                  max={10}
                  style={{ width: '100%' }}
                  placeholder="建议2-5章"
                />
              </Form.Item>

              <Form.Item
                label="展开策略"
                name="expansion_strategy"
                tooltip={{
                  title: (
                    <div>
                      <div><strong>AI推荐</strong>：由AI根据大纲内容自动选择最合适的策略</div>
                      <div><strong>均衡分配</strong>：章节篇幅均匀，适合平稳推进的情节</div>
                      <div><strong>高潮重点</strong>：在关键节点增加篇幅，适合冲突激烈的情节</div>
                      <div><strong>细节丰富</strong>：注重场景描写和心理刻画，适合细腻叙事</div>
                    </div>
                  ),
                  styles: { root: { maxWidth: 320 } }
                }}
              >
                <Radio.Group>
                  <Radio.Button value="auto">AI推荐</Radio.Button>
                  <Radio.Button value="balanced">均衡分配</Radio.Button>
                  <Radio.Button value="climax">高潮重点</Radio.Button>
                  <Radio.Button value="detail">细节丰富</Radio.Button>
                </Radio.Group>
              </Form.Item>
            </Form>
          </div>
        ),
        okText: '生成规划预览',
        cancelText: '取消',
        onOk: async () => {
          try {
            const values = await expansionForm.validateFields();

            // 关闭配置表单
            Modal.destroyAll();

            // 显示SSE进度Modal
            setSSEProgress(0);
            setSSEMessage('正在准备展开大纲...');
            setSSEModalVisible(true);
            setIsExpanding(true);

            // 准备请求数据
            const requestData = {
              ...values,
              auto_create_chapters: false, // 第一步：仅生成规划
              enable_scene_analysis: true
            };

            // 使用SSE客户端调用新的流式端点
            const apiUrl = `/api/outlines/${outlineId}/expand-stream`;
            const client = new SSEPostClient(apiUrl, requestData, {
              onProgress: (msg: string, progress: number) => {
                setSSEMessage(msg);
                setSSEProgress(progress);
              },
              onResult: (data: OutlineExpansionResponse) => {
                console.log('展开完成，结果:', data);
                // 关闭SSE进度Modal
                setSSEModalVisible(false);
                // 显示规划预览
                showExpansionPreview(outlineId, data);
              },
              onError: (error: string) => {
                message.error(`展开失败: ${error}`);
                setSSEModalVisible(false);
                setIsExpanding(false);
              },
              onComplete: () => {
                setSSEModalVisible(false);
                setIsExpanding(false);
              }
            });

            // 开始连接
            client.connect();

          } catch (error) {
            console.error('展开失败:', error);
            message.error('展开失败');
            setSSEModalVisible(false);
            setIsExpanding(false);
          }
        },
      });
    } catch (error) {
      console.error('检查章节失败:', error);
      message.error('检查章节失败');
      setIsExpanding(false);
    }
  };

  // 删除展开的章节内容（保留大纲）
  const handleDeleteExpandedChapters = async (outlineTitle: string, chapters: Array<{ id: string }>) => {
    try {
      // 使用顺序删除避免并发导致的字数计算竞态条件
      // 并发删除会导致多个请求同时读取项目字数并各自减去章节字数，造成计算错误
      for (const chapter of chapters) {
        await chapterApi.deleteChapter(chapter.id);
      }

      message.success(`已删除《${outlineTitle}》展开的所有 ${chapters.length} 个章节`);
      await refreshOutlines();
      // 刷新项目信息以更新字数显示
      if (currentProject?.id) {
        const updatedProject = await projectApi.getProject(currentProject.id);
        setCurrentProject(updatedProject);
      }
    } catch (error: unknown) {
      const apiError = error as ApiError;
      message.error(apiError.response?.data?.detail || '删除章节失败');
    }
  };

  // 显示已存在章节的展开规划
  const showExistingExpansionPreview = (
    outlineTitle: string,
    data: {
      chapter_count: number;
      chapters: Array<{ id: string; chapter_number: number; title: string }>;
      expansion_plans: Array<{
        sub_index: number;
        title: string;
        plot_summary: string;
        key_events: string[];
        character_focus: string[];
        emotional_tone: string;
        narrative_goal: string;
        conflict_type: string;
        estimated_words: number;
        rhythm_intensity?: number;
        chapter_types?: string[];
        story_lines?: string[];
        scenes?: Array<{
          location: string;
          characters: string[];
          purpose: string;
        }> | null;
      }> | null;
    }
  ) => {
    modalApi.info({
      title: (
        <Space style={{ flexWrap: 'wrap' }}>
          <CheckCircleOutlined style={{ color: token.colorSuccess }} />
          <span>《{outlineTitle}》展开信息</span>
        </Space>
      ),
      width: isMobile ? '95%' : 900,
      centered: true,
      closable: true,
      style: isMobile ? {
        top: 20,
        maxWidth: 'calc(100vw - 16px)',
        margin: '0 8px'
      } : undefined,
      styles: {
        body: {
          maxHeight: isMobile ? 'calc(100vh - 200px)' : 'calc(80vh - 60px)',
          overflowY: 'auto',
          overflowX: 'hidden'
        }
      },
      footer: (
        <Space wrap style={{ width: '100%', justifyContent: isMobile ? 'center' : 'flex-end' }}>
          <Button
            danger
            icon={<DeleteOutlined />}
            onClick={() => {
              Modal.destroyAll();
              modalApi.confirm({
                title: '确认删除',
                icon: <ExclamationCircleOutlined />,
                centered: true,
                content: (
                  <div>
                    <p>此操作将删除大纲《{outlineTitle}》展开的所有 <strong>{data.chapter_count}</strong> 个章节。</p>
                    <p style={{ color: token.colorPrimary, marginTop: 8 }}>
                      📝 注意：大纲本身会保留，您可以重新展开
                    </p>
                    <p style={{ color: token.colorError, marginTop: 8 }}>
                      ⚠️ 警告：章节内容将永久删除且无法恢复！
                    </p>
                  </div>
                ),
                okText: '确认删除',
                okType: 'danger',
                cancelText: '取消',
                onOk: () => handleDeleteExpandedChapters(outlineTitle, data.chapters || []),
              });
            }}
            block={isMobile}
            size={isMobile ? 'middle' : undefined}
          >
            删除所有展开的章节 ({data.chapter_count}章)
          </Button>
          <Button onClick={() => Modal.destroyAll()}>
            关闭
          </Button>
        </Space>
      ),
      content: (
        <div>
          <div style={{ marginBottom: 16 }}>
            <Space wrap style={{ maxWidth: '100%' }}>
              <Tag
                color="blue"
                style={{
                  whiteSpace: 'normal',
                  wordBreak: 'break-word',
                  height: 'auto',
                  lineHeight: '1.5',
                  padding: '4px 8px'
                }}
              >
                大纲: {outlineTitle}
              </Tag>
              <Tag color="green">章节数: {data.chapter_count}</Tag>
              <Tag color="orange">已创建章节</Tag>
            </Space>
          </div>
          <Tabs
            defaultActiveKey="0"
            type="card"
            items={data.expansion_plans?.map((plan, idx) => ({
              key: idx.toString(),
              label: (
                <Space size="small" style={{ maxWidth: isMobile ? '150px' : 'none' }}>
                  <span
                    style={{
                      fontWeight: 500,
                      whiteSpace: isMobile ? 'normal' : 'nowrap',
                      wordBreak: isMobile ? 'break-word' : 'normal',
                      fontSize: isMobile ? 12 : 14
                    }}
                  >
                    {plan.sub_index}. {plan.title}
                  </span>
                </Space>
              ),
              children: (
                <div style={{ maxHeight: '500px', overflowY: 'auto', padding: '8px 0' }}>
                  <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                    <Card size="small" title="基本信息">
                      <Space wrap style={{ maxWidth: '100%' }}>
                        <Tag
                          color="blue"
                          style={{
                            whiteSpace: 'normal',
                            wordBreak: 'break-word',
                            height: 'auto',
                            lineHeight: '1.5',
                            padding: '4px 8px'
                          }}
                        >
                          {plan.emotional_tone}
                        </Tag>
                        <Tag
                          color="orange"
                          style={{
                            whiteSpace: 'normal',
                            wordBreak: 'break-word',
                            height: 'auto',
                            lineHeight: '1.5',
                            padding: '4px 8px'
                          }}
                        >
                          {plan.conflict_type}
                        </Tag>
                        <Tag color="green">约{plan.estimated_words}字</Tag>
                        {plan.rhythm_intensity && (
                          <Tag
                            color={
                              plan.rhythm_intensity >= 8 ? 'red' :
                              plan.rhythm_intensity >= 6 ? 'orange' :
                              plan.rhythm_intensity >= 4 ? 'blue' : 'default'
                            }
                          >
                            强度 {plan.rhythm_intensity}/10
                          </Tag>
                        )}
                      </Space>
                    </Card>

                    <Card size="small" title="情节概要">
                      <div style={{
                        wordBreak: 'break-word',
                        whiteSpace: 'normal',
                        overflowWrap: 'break-word'
                      }}>
                        {plan.plot_summary}
                      </div>
                    </Card>

                    <Card size="small" title="叙事目标">
                      <div style={{
                        wordBreak: 'break-word',
                        whiteSpace: 'normal',
                        overflowWrap: 'break-word'
                      }}>
                        {plan.narrative_goal}
                      </div>
                    </Card>

                    <Card size="small" title="关键事件">
                      <Space direction="vertical" size="small" style={{ width: '100%' }}>
                        {plan.key_events.map((event, eventIdx) => (
                          <div
                            key={eventIdx}
                            style={{
                              wordBreak: 'break-word',
                              whiteSpace: 'normal',
                              overflowWrap: 'break-word'
                            }}
                          >
                            • {event}
                          </div>
                        ))}
                      </Space>
                    </Card>

                    <Card size="small" title="涉及角色">
                      <Space wrap style={{ maxWidth: '100%' }}>
                        {plan.character_focus.map((char, charIdx) => (
                          <Tag
                            key={charIdx}
                            color="purple"
                            style={{
                              whiteSpace: 'normal',
                              wordBreak: 'break-word',
                              height: 'auto',
                              lineHeight: '1.5'
                            }}
                          >
                            {char}
                          </Tag>
                        ))}
                      </Space>
                    </Card>

                    {plan.scenes && plan.scenes.length > 0 && (
                      <Card size="small" title="场景">
                        <Space direction="vertical" size="small" style={{ width: '100%' }}>
                          {plan.scenes.map((scene, sceneIdx) => (
                            <Card
                              key={sceneIdx}
                              size="small"
                              style={{
                                backgroundColor: token.colorFillQuaternary,
                                maxWidth: '100%',
                                overflow: 'hidden'
                              }}
                            >
                              <div style={{
                                wordBreak: 'break-word',
                                whiteSpace: 'normal',
                                overflowWrap: 'break-word'
                              }}>
                                <strong>地点：</strong>{scene.location}
                              </div>
                              <div style={{
                                wordBreak: 'break-word',
                                whiteSpace: 'normal',
                                overflowWrap: 'break-word'
                              }}>
                                <strong>角色：</strong>{scene.characters.join('、')}
                              </div>
                              <div style={{
                                wordBreak: 'break-word',
                                whiteSpace: 'normal',
                                overflowWrap: 'break-word'
                              }}>
                                <strong>目的：</strong>{scene.purpose}
                              </div>
                            </Card>
                          ))}
                        </Space>
                      </Card>
                    )}

                    {plan.chapter_types && plan.chapter_types.length > 0 && (
                      <Card size="small" title="章节类型">
                        <Space wrap style={{ maxWidth: '100%' }}>
                          {plan.chapter_types.map((type, typeIdx) => {
                            const typeName = type.includes('(') ? type.split('(')[0].trim() : type;
                            let tagColor = 'blue';
                            if (typeName.includes('高潮')) tagColor = 'red';
                            else if (typeName.includes('主线')) tagColor = 'blue';
                            else if (typeName.includes('支线')) tagColor = 'cyan';
                            else if (typeName.includes('奇遇')) tagColor = 'gold';
                            else if (typeName.includes('秘境') || typeName.includes('副本')) tagColor = 'purple';
                            else if (typeName.includes('人物') || typeName.includes('关系')) tagColor = 'pink';
                            else if (typeName.includes('过渡')) tagColor = 'default';
                            return (
                              <Tag key={typeIdx} color={tagColor} style={{ whiteSpace: 'normal', height: 'auto', lineHeight: '1.5' }}>
                                {type}
                              </Tag>
                            );
                          })}
                        </Space>
                      </Card>
                    )}

                    {plan.story_lines && plan.story_lines.length > 0 && (
                      <Card size="small" title="故事线">
                        <Space wrap style={{ maxWidth: '100%' }}>
                          {plan.story_lines.map((line, lineIdx) => (
                            <Tag key={lineIdx} color="green" style={{ whiteSpace: 'normal', height: 'auto', lineHeight: '1.5' }}>
                              {line}
                            </Tag>
                          ))}
                        </Space>
                      </Card>
                    )}
                  </Space>
                </div >
              )
            }))}
          />
        </div >
      ),
    });
  };

  // 显示展开规划预览，并提供确认创建章节的选项
  const showExpansionPreview = (outlineId: string, response: OutlineExpansionResponse) => {
    // 缓存AI生成的规划数据
    const cachedPlans = response.chapter_plans;

    modalApi.confirm({
      title: (
        <Space>
          <CheckCircleOutlined style={{ color: token.colorSuccess }} />
          <span>展开规划预览</span>
        </Space>
      ),
      width: 900,
      centered: true,
      okText: '确认并创建章节',
      cancelText: '暂不创建',
      content: (
        <div>
          <div style={{ marginBottom: 16 }}>
            <Tag color="blue">策略: {response.expansion_strategy}</Tag>
            <Tag color="green">章节数: {response.actual_chapter_count}</Tag>
            <Tag color="orange">预览模式（未创建章节）</Tag>
          </div>
          <Tabs
            defaultActiveKey="0"
            type="card"
            items={response.chapter_plans.map((plan, idx) => ({
              key: idx.toString(),
              label: (
                <Space size="small">
                  <span style={{ fontWeight: 500 }}>{idx + 1}. {plan.title}</span>
                </Space>
              ),
              children: (
                <div style={{ maxHeight: '500px', overflowY: 'auto', padding: '8px 0' }}>
                  <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                    <Card size="small" title="基本信息">
                      <Space wrap>
                        <Tag color="blue">{plan.emotional_tone}</Tag>
                        <Tag color="orange">{plan.conflict_type}</Tag>
                        <Tag color="green">约{plan.estimated_words}字</Tag>
                        {plan.rhythm_intensity && (
                          <Tag color={
                            plan.rhythm_intensity >= 8 ? 'red' :
                            plan.rhythm_intensity >= 6 ? 'orange' :
                            plan.rhythm_intensity >= 4 ? 'blue' : 'default'
                          }>
                            强度 {plan.rhythm_intensity}/10
                          </Tag>
                        )}
                      </Space>
                    </Card>

                    <Card size="small" title="情节概要">
                      {plan.plot_summary}
                    </Card>

                    <Card size="small" title="叙事目标">
                      {plan.narrative_goal}
                    </Card>

                    <Card size="small" title="关键事件">
                      <Space direction="vertical" size="small" style={{ width: '100%' }}>
                        {plan.key_events.map((event, eventIdx) => (
                          <div key={eventIdx}>• {event}</div>
                        ))}
                      </Space>
                    </Card>

                    <Card size="small" title="涉及角色">
                      <Space wrap>
                        {plan.character_focus.map((char, charIdx) => (
                          <Tag key={charIdx} color="purple">{char}</Tag>
                        ))}
                      </Space>
                    </Card>

                    {plan.chapter_types && plan.chapter_types.length > 0 && (
                      <Card size="small" title="章节类型">
                        <Space wrap>
                          {plan.chapter_types.map((type, typeIdx) => {
                            const typeName = type.includes('(') ? type.split('(')[0].trim() : type;
                            const pct = type.includes('(') ? type.match(/\((\d+%?)\)/)?.[1] : '';
                            let tagColor = 'blue';
                            if (typeName.includes('高潮')) tagColor = 'red';
                            else if (typeName.includes('主线')) tagColor = 'blue';
                            else if (typeName.includes('支线')) tagColor = 'cyan';
                            else if (typeName.includes('奇遇')) tagColor = 'gold';
                            else if (typeName.includes('秘境') || typeName.includes('副本')) tagColor = 'purple';
                            else if (typeName.includes('人物') || typeName.includes('关系')) tagColor = 'pink';
                            else if (typeName.includes('过渡')) tagColor = 'default';
                            return (
                              <Tag key={typeIdx} color={tagColor}>
                                {typeName}{pct && ` (${pct})`}
                              </Tag>
                            );
                          })}
                        </Space>
                      </Card>
                    )}

                    {plan.story_lines && plan.story_lines.length > 0 && (
                      <Card size="small" title="故事线">
                        <Space wrap>
                          {plan.story_lines.map((line, lineIdx) => (
                            <Tag key={lineIdx} color="green">{line}</Tag>
                          ))}
                        </Space>
                      </Card>
                    )}

                    {plan.scenes && plan.scenes.length > 0 && (
                      <Card size="small" title="场景">
                        <Space direction="vertical" size="small" style={{ width: '100%' }}>
                          {plan.scenes.map((scene, sceneIdx) => (
                            <Card key={sceneIdx} size="small" style={{ backgroundColor: token.colorFillQuaternary }}>
                              <div><strong>地点：</strong>{scene.location}</div>
                              <div><strong>角色：</strong>{scene.characters.join('、')}</div>
                              <div><strong>目的：</strong>{scene.purpose}</div>
                            </Card>
                          ))}
                        </Space>
                      </Card>
                    )}
                  </Space>
                </div>
              )
            }))}
          />
        </div>
      ),
      onOk: async () => {
        // 第二步：用户确认后，直接使用缓存的规划创建章节（避免重复调用AI）
        await handleConfirmCreateChapters(outlineId, cachedPlans);
      },
      onCancel: () => {
        message.info('已取消创建章节');
      }
    });
  };

  // 确认创建章节 - 使用缓存的规划数据，避免重复AI调用
  const handleConfirmCreateChapters = async (
    outlineId: string,
    cachedPlans: ChapterPlanItem[]
  ) => {
    try {
      setIsExpanding(true);

      // 使用新的API端点，直接传递缓存的规划数据
      const response = await outlineApi.createChaptersFromPlans(outlineId, cachedPlans);

      message.success(
        `成功创建${response.chapters_created}个章节！`,
        3
      );

      console.log('✅ 使用缓存的规划创建章节，避免了重复的AI调用');

      // 刷新大纲和章节列表
      refreshOutlines();

    } catch (error) {
      console.error('创建章节失败:', error);
      message.error('创建章节失败');
    } finally {
      setIsExpanding(false);
    }
  };

  // 批量展开所有大纲 - 使用SSE流式显示进度
  const handleBatchExpandOutlines = () => {
    if (!currentProject?.id || outlines.length === 0) {
      message.warning('没有可展开的大纲');
      return;
    }

    // 统计已展开和未展开的大纲数量
    const expandedCount = outlines.filter(o => o.has_chapters).length;
    const unexpandedCount = outlines.length - expandedCount;
    const unexpandedOutlines = outlines.filter(o => !o.has_chapters);

    // 如果所有大纲都已展开，提示用户
    if (unexpandedCount === 0) {
      modalApi.info({
        title: '所有大纲已展开',
        content: '当前项目的所有大纲都已展开为章节，无需再次展开。',
        centered: true,
      });
      return;
    }

    modalApi.confirm({
      title: (
        <Space>
          <AppstoreAddOutlined />
          <span>批量展开大纲</span>
        </Space>
      ),
      width: 600,
      centered: true,
      content: (
        <div>
          <div
            style={{
              marginBottom: 16,
              padding: 12,
              background: token.colorInfoBg,
              borderRadius: token.borderRadius,
              border: `1px solid ${token.colorInfoBorder}`,
            }}
          >
            <div style={{ color: token.colorInfoText }}>
              <div>📊 当前项目大纲统计：</div>
              <div style={{ marginTop: 8 }}>
                <Tag color="success">已展开: {expandedCount} 个</Tag>
                <Tag color="processing">未展开: {unexpandedCount} 个</Tag>
              </div>
            </div>
          </div>
          <Form
            form={batchExpansionForm}
            layout="vertical"
            initialValues={{
              chapters_per_outline: 3,
              expansion_strategy: 'auto',
              expand_scope: 'unexpanded',
            }}
          >
            <Form.Item
              label="展开范围"
              name="expand_scope"
              tooltip="选择要展开的大纲范围"
            >
              <Radio.Group>
                <Radio value="unexpanded">
                  仅未展开 ({unexpandedCount} 个)
                </Radio>
                <Radio value="all">
                  全部大纲 ({outlines.length} 个)
                </Radio>
              </Radio.Group>
            </Form.Item>

            <Form.Item
              label="每个大纲展开章节数"
              name="chapters_per_outline"
              rules={[{ required: true, message: '请输入章节数' }]}
              tooltip="每个大纲将被展开为几章"
            >
              <InputNumber
                min={2}
                max={10}
                style={{ width: '100%' }}
                placeholder="建议2-5章"
              />
            </Form.Item>

            <Form.Item
              label="展开策略"
              name="expansion_strategy"
              tooltip={{
                title: (
                  <div>
                    <div><strong>AI推荐</strong>：由AI根据大纲内容自动选择最合适的策略</div>
                    <div><strong>均衡分配</strong>：章节篇幅均匀，适合平稳推进的情节</div>
                    <div><strong>高潮重点</strong>：在关键节点增加篇幅，适合冲突激烈的情节</div>
                    <div><strong>细节丰富</strong>：注重场景描写和心理刻画，适合细腻叙事</div>
                  </div>
                ),
                styles: { root: { maxWidth: 320 } }
              }}
            >
              <Radio.Group>
                <Radio.Button value="auto">AI推荐</Radio.Button>
                <Radio.Button value="balanced">均衡分配</Radio.Button>
                <Radio.Button value="climax">高潮重点</Radio.Button>
                <Radio.Button value="detail">细节丰富</Radio.Button>
              </Radio.Group>
            </Form.Item>
          </Form>
        </div>
      ),
      okText: '开始展开',
      cancelText: '取消',
      okButtonProps: { type: 'primary' },
      onOk: async () => {
        try {
          const values = await batchExpansionForm.validateFields();

          // 根据展开范围确定要展开的大纲ID列表
          let outlineIds: string[] | undefined;
          if (values.expand_scope === 'unexpanded') {
            outlineIds = unexpandedOutlines.map(o => o.id);
          }

          // 关闭配置表单
          Modal.destroyAll();

          // 显示SSE进度Modal
          setSSEProgress(0);
          setSSEMessage('正在准备批量展开...');
          setSSEModalVisible(true);
          setIsExpanding(true);

          // 准备请求数据
          const requestData = {
            project_id: currentProject.id,
            outline_ids: outlineIds,
            chapters_per_outline: values.chapters_per_outline,
            expansion_strategy: values.expansion_strategy,
            auto_create_chapters: false // 第一步：仅生成规划
          };

          // 使用SSE客户端
          const apiUrl = `/api/outlines/batch-expand-stream`;
          const client = new SSEPostClient(apiUrl, requestData, {
            onProgress: (msg: string, progress: number) => {
              setSSEMessage(msg);
              setSSEProgress(progress);
            },
            onResult: (data: BatchOutlineExpansionResponse) => {
              console.log('批量展开完成，结果:', data);
              // 缓存AI生成的规划数据
              setCachedBatchExpansionResponse(data);
              setBatchPreviewData(data);
              // 关闭SSE进度Modal
              setSSEModalVisible(false);
              // 重置选择状态
              setSelectedOutlineIdx(0);
              setSelectedChapterIdx(0);
              // 显示批量预览Modal
              setBatchPreviewVisible(true);
            },
            onError: (error: string) => {
              message.error(`批量展开失败: ${error}`);
              setSSEModalVisible(false);
              setIsExpanding(false);
            },
            onComplete: () => {
              setSSEModalVisible(false);
              setIsExpanding(false);
            }
          });

          // 开始连接
          client.connect();

        } catch (error) {
          console.error('批量展开失败:', error);
          message.error('批量展开失败');
          setSSEModalVisible(false);
          setIsExpanding(false);
        }
      },
    });
  };

  // 渲染批量展开预览 Modal 内容
  const renderBatchPreviewContent = () => {
    if (!batchPreviewData) return null;

    return (
      <div>
        {/* 顶部统计信息 */}
        <div style={{ marginBottom: 16 }}>
          <Tag color="blue">已处理: {batchPreviewData.total_outlines_expanded} 个大纲</Tag>
          <Tag color="green">总章节数: {batchPreviewData.expansion_results.reduce((sum: number, r: OutlineExpansionResponse) => sum + r.actual_chapter_count, 0)}</Tag>
          <Tag color="orange">预览模式（未创建章节）</Tag>
          {batchPreviewData.skipped_outlines && batchPreviewData.skipped_outlines.length > 0 && (
            <Tag color="warning">跳过: {batchPreviewData.skipped_outlines.length} 个大纲</Tag>
          )}
        </div>

        {/* 显示跳过的大纲信息 */}
        {batchPreviewData.skipped_outlines && batchPreviewData.skipped_outlines.length > 0 && (
          <div style={{
            marginBottom: 16,
            padding: 12,
            background: token.colorWarningBg,
            borderRadius: token.borderRadius,
            border: `1px solid ${token.colorWarningBorder}`
          }}>
            <div style={{ fontWeight: 500, marginBottom: 8, color: token.colorWarning }}>
              ⚠️ 以下大纲已展开过，已自动跳过：
            </div>
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              {batchPreviewData.skipped_outlines.map((skipped: SkippedOutlineInfo, idx: number) => (
                <div key={idx} style={{ fontSize: 13, color: token.colorTextSecondary }}>
                  • {skipped.outline_title} <Tag color="default" style={{ fontSize: 11 }}>{skipped.reason}</Tag>
                </div>
              ))}
            </Space>
          </div>
        )}

        {/* 水平三栏布局 */}
        <div style={{ display: 'flex', gap: 16, height: 500 }}>
          {/* 左栏：大纲列表 */}
          <div style={{
            width: 280,
            borderRight: `1px solid ${token.colorBorderSecondary}`,
            paddingRight: 12,
            overflowY: 'auto'
          }}>
            <div style={{ fontWeight: 500, marginBottom: 8, color: token.colorTextSecondary }}>大纲列表</div>
            <List
              size="small"
              dataSource={batchPreviewData.expansion_results}
              renderItem={(result: OutlineExpansionResponse, idx: number) => (
                <List.Item
                  key={idx}
                  onClick={() => {
                    setSelectedOutlineIdx(idx);
                    setSelectedChapterIdx(0);
                  }}
                  style={{
                    cursor: 'pointer',
                    padding: '8px 12px',
                    background: selectedOutlineIdx === idx ? token.colorPrimaryBg : 'transparent',
                    borderRadius: token.borderRadius,
                    marginBottom: 4,
                    border: selectedOutlineIdx === idx ? `1px solid ${token.colorPrimary}` : '1px solid transparent'
                  }}
                >
                  <div style={{ width: '100%' }}>
                    <div style={{ fontWeight: 500, fontSize: 13, marginBottom: 4 }}>
                      {idx + 1}. {result.outline_title}
                    </div>
                    <Space size={4}>
                      <Tag color="blue" style={{ fontSize: 11, margin: 0 }}>{result.expansion_strategy}</Tag>
                      <Tag color="green" style={{ fontSize: 11, margin: 0 }}>{result.actual_chapter_count} 章</Tag>
                    </Space>
                  </div>
                </List.Item>
              )}
            />
          </div>

          {/* 中栏：章节列表 */}
          <div style={{
            width: 320,
            borderRight: `1px solid ${token.colorBorderSecondary}`,
            paddingRight: 12,
            overflowY: 'auto'
          }}>
            <div style={{ fontWeight: 500, marginBottom: 8, color: token.colorTextSecondary }}>
              章节列表 ({batchPreviewData.expansion_results[selectedOutlineIdx]?.actual_chapter_count || 0} 章)
            </div>
            {batchPreviewData.expansion_results[selectedOutlineIdx] && (
              <List
                size="small"
                dataSource={batchPreviewData.expansion_results[selectedOutlineIdx].chapter_plans}
                renderItem={(plan: ChapterPlanItem, idx: number) => (
                  <List.Item
                    key={idx}
                    onClick={() => setSelectedChapterIdx(idx)}
                    style={{
                      cursor: 'pointer',
                      padding: '8px 12px',
                      background: selectedChapterIdx === idx ? token.colorPrimaryBg : 'transparent',
                      borderRadius: token.borderRadius,
                      marginBottom: 4,
                      border: selectedChapterIdx === idx ? `1px solid ${token.colorPrimary}` : '1px solid transparent'
                    }}
                  >
                    <div style={{ width: '100%' }}>
                      <div style={{ fontWeight: 500, fontSize: 13, marginBottom: 4 }}>
                        {idx + 1}. {plan.title}
                      </div>
                      <Space size={4} wrap>
                        <Tag color="blue" style={{ fontSize: 11, margin: 0 }}>{plan.emotional_tone}</Tag>
                        <Tag color="orange" style={{ fontSize: 11, margin: 0 }}>{plan.conflict_type}</Tag>
                        <Tag color="green" style={{ fontSize: 11, margin: 0 }}>约{plan.estimated_words}字</Tag>
                      </Space>
                    </div>
                  </List.Item>
                )}
              />
            )}
          </div>

          {/* 右栏：章节详情 */}
          <div style={{ flex: 1, overflowY: 'auto', paddingLeft: 12 }}>
            <div style={{ fontWeight: 500, marginBottom: 12, color: token.colorTextSecondary }}>章节详情</div>
            {batchPreviewData.expansion_results[selectedOutlineIdx]?.chapter_plans[selectedChapterIdx] ? (
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                <Card size="small" title="情节概要" variant="borderless">
                  {batchPreviewData.expansion_results[selectedOutlineIdx].chapter_plans[selectedChapterIdx].plot_summary}
                </Card>

                <Card size="small" title="叙事目标" variant="borderless">
                  {batchPreviewData.expansion_results[selectedOutlineIdx].chapter_plans[selectedChapterIdx].narrative_goal}
                </Card>

                <Card size="small" title="关键事件" variant="borderless">
                  <Space direction="vertical" size="small" style={{ width: '100%' }}>
                    {(batchPreviewData.expansion_results[selectedOutlineIdx].chapter_plans[selectedChapterIdx].key_events as string[]).map((event: string, eventIdx: number) => (
                      <div key={eventIdx}>• {event}</div>
                    ))}
                  </Space>
                </Card>

                <Card size="small" title="涉及角色" variant="borderless">
                  <Space wrap>
                    {(batchPreviewData.expansion_results[selectedOutlineIdx].chapter_plans[selectedChapterIdx].character_focus as string[]).map((char: string, charIdx: number) => (
                      <Tag key={charIdx} color="purple">{char}</Tag>
                    ))}
                  </Space>
                </Card>

                {batchPreviewData.expansion_results[selectedOutlineIdx].chapter_plans[selectedChapterIdx].scenes && batchPreviewData.expansion_results[selectedOutlineIdx].chapter_plans[selectedChapterIdx].scenes!.length > 0 && (
                  <Card size="small" title="场景" variant="borderless">
                    <Space direction="vertical" size="small" style={{ width: '100%' }}>
                      {batchPreviewData.expansion_results[selectedOutlineIdx].chapter_plans[selectedChapterIdx].scenes!.map((scene: SceneInfo, sceneIdx: number) => (
                        <Card key={sceneIdx} size="small" style={{ backgroundColor: token.colorFillQuaternary }}>
                          <div><strong>地点：</strong>{scene.location}</div>
                          <div><strong>角色：</strong>{scene.characters.join('、')}</div>
                          <div><strong>目的：</strong>{scene.purpose}</div>
                        </Card>
                      ))}
                    </Space>
                  </Card>
                )}

                {batchPreviewData.expansion_results[selectedOutlineIdx].chapter_plans[selectedChapterIdx].rhythm_intensity && (
                  <Card size="small" title="节奏强度" variant="borderless">
                    <Tag
                      color={
                        batchPreviewData.expansion_results[selectedOutlineIdx].chapter_plans[selectedChapterIdx].rhythm_intensity! >= 8 ? 'red' :
                        batchPreviewData.expansion_results[selectedOutlineIdx].chapter_plans[selectedChapterIdx].rhythm_intensity! >= 6 ? 'orange' :
                        batchPreviewData.expansion_results[selectedOutlineIdx].chapter_plans[selectedChapterIdx].rhythm_intensity! >= 4 ? 'blue' : 'default'
                      }
                    >
                      {batchPreviewData.expansion_results[selectedOutlineIdx].chapter_plans[selectedChapterIdx].rhythm_intensity}/10
                    </Tag>
                  </Card>
                )}

                {batchPreviewData.expansion_results[selectedOutlineIdx].chapter_plans[selectedChapterIdx].chapter_types && batchPreviewData.expansion_results[selectedOutlineIdx].chapter_plans[selectedChapterIdx].chapter_types!.length > 0 && (
                  <Card size="small" title="章节类型" variant="borderless">
                    <Space wrap>
                      {batchPreviewData.expansion_results[selectedOutlineIdx].chapter_plans[selectedChapterIdx].chapter_types!.map((type: string, typeIdx: number) => {
                        const typeName = type.includes('(') ? type.split('(')[0].trim() : type;
                        let tagColor = 'blue';
                        if (typeName.includes('高潮')) tagColor = 'red';
                        else if (typeName.includes('主线')) tagColor = 'blue';
                        else if (typeName.includes('支线')) tagColor = 'cyan';
                        else if (typeName.includes('奇遇')) tagColor = 'gold';
                        else if (typeName.includes('秘境') || typeName.includes('副本')) tagColor = 'purple';
                        else if (typeName.includes('人物') || typeName.includes('关系')) tagColor = 'pink';
                        else if (typeName.includes('过渡')) tagColor = 'default';
                        return <Tag key={typeIdx} color={tagColor}>{type}</Tag>;
                      })}
                    </Space>
                  </Card>
                )}

                {batchPreviewData.expansion_results[selectedOutlineIdx].chapter_plans[selectedChapterIdx].story_lines && batchPreviewData.expansion_results[selectedOutlineIdx].chapter_plans[selectedChapterIdx].story_lines!.length > 0 && (
                  <Card size="small" title="故事线" variant="borderless">
                    <Space wrap>
                      {batchPreviewData.expansion_results[selectedOutlineIdx].chapter_plans[selectedChapterIdx].story_lines!.map((line: string, lineIdx: number) => (
                        <Tag key={lineIdx} color="green">{line}</Tag>
                      ))}
                    </Space>
                  </Card>
                )}
              </Space>
            ) : (
              <Empty description="请选择章节查看详情" />
            )}
          </div>
        </div>
      </div>
    );
  };

  // 处理批量预览确认
  const handleBatchPreviewOk = async () => {
    setBatchPreviewVisible(false);
    await handleConfirmBatchCreateChapters();
  };

  // 处理批量预览取消
  const handleBatchPreviewCancel = () => {
    setBatchPreviewVisible(false);
    message.info('已取消创建章节，规划已保存');
  };


  // 确认批量创建章节 - 使用缓存的规划数据
  const handleConfirmBatchCreateChapters = async () => {
    try {
      setIsExpanding(true);

      // 使用缓存的规划数据，避免重复调用AI
      if (!cachedBatchExpansionResponse) {
        message.error('规划数据丢失，请重新展开');
        return;
      }

      console.log('✅ 使用缓存的批量规划数据创建章节，避免重复AI调用');

      // 逐个大纲创建章节
      let totalCreated = 0;
      const errors: string[] = [];

      for (const result of cachedBatchExpansionResponse.expansion_results) {
        try {
          // 使用create-chapters-from-plans接口，直接传递缓存的规划
          const response = await outlineApi.createChaptersFromPlans(
            result.outline_id,
            result.chapter_plans
          );
          totalCreated += response.chapters_created;
        } catch (error: unknown) {
          const apiError = error as ApiError;
          const err = error as Error;
          const errorMsg = apiError.response?.data?.detail || err.message || '未知错误';
          errors.push(`${result.outline_title}: ${errorMsg}`);
          console.error(`创建大纲 ${result.outline_title} 的章节失败:`, error);
        }
      }

      // 显示结果
      if (errors.length === 0) {
        message.success(
          `批量创建完成！共创建 ${totalCreated} 个章节`,
          3
        );
      } else {
        message.warning(
          `部分完成：成功创建 ${totalCreated} 个章节，${errors.length} 个失败`,
          5
        );
        console.error('失败详情:', errors);
      }

      // 清除缓存
      setCachedBatchExpansionResponse(null);

      // 刷新列表
      refreshOutlines();

    } catch (error) {
      console.error('批量创建章节失败:', error);
      message.error('批量创建章节失败');
    } finally {
      setIsExpanding(false);
    }
  };


  return (
    <>
      {/* 批量展开预览 Modal */}
      <Modal
        title={
          <Space>
            <CheckCircleOutlined style={{ color: token.colorSuccess }} />
            <span>批量展开规划预览</span>
          </Space>
        }
        open={batchPreviewVisible}
        onOk={handleBatchPreviewOk}
        onCancel={handleBatchPreviewCancel}
        width={1200}
        centered
        okText="确认并批量创建章节"
        cancelText="暂不创建"
        okButtonProps={{ danger: true }}
      >
        {renderBatchPreviewContent()}
      </Modal>

      {contextHolder}
      {/* SSE进度Modal - 使用统一组件 */}
      <SSEProgressModal
        visible={sseModalVisible}
        progress={sseProgress}
        message={sseMessage}
        title="AI生成中..."
      />

      <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        {/* 固定头部 */}
        <div style={{
          position: 'sticky',
          top: 0,
          zIndex: 10,
          backgroundColor: token.colorBgContainer,
          padding: isMobile ? '12px 0' : '16px 0',
          marginBottom: isMobile ? 12 : 16,
          borderBottom: `1px solid ${token.colorBorderSecondary}`,
          display: 'flex',
          flexDirection: isMobile ? 'column' : 'row',
          gap: isMobile ? 12 : 0,
          justifyContent: 'space-between',
          alignItems: isMobile ? 'stretch' : 'center'
        }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <h2 style={{ margin: 0, fontSize: isMobile ? 18 : 24 }}>
              <FileTextOutlined style={{ marginRight: 8 }} />
              故事大纲
            </h2>
            {currentProject?.outline_mode && (
              <Tag color={currentProject.outline_mode === 'one-to-one' ? 'blue' : 'green'} style={{ width: 'fit-content' }}>
                {currentProject.outline_mode === 'one-to-one' ? '传统模式 (1→1)' : '细化模式 (1→N)'}
              </Tag>
            )}
          </div>
          <Space size="small" wrap={isMobile}>
            <Input.Search
              allowClear
              placeholder="搜索大纲（序号/标题/内容）"
              value={outlineSearchKeyword}
              onChange={(e) => setOutlineSearchKeyword(e.target.value)}
              style={{ width: isMobile ? '100%' : 280 }}
            />
            <Button
              icon={<PlusOutlined />}
              onClick={showManualCreateOutlineModal}
              block={isMobile}
            >
              手动创建
            </Button>
            <Button
              type="primary"
              icon={<ThunderboltOutlined />}
              onClick={showGenerateModal}
              loading={isGenerating}
              block={isMobile}
            >
              {isMobile ? 'AI生成/续写' : 'AI生成/续写大纲'}
            </Button>
            {outlines.length > 0 && currentProject?.outline_mode === 'one-to-many' && (
              <Button
                icon={<AppstoreAddOutlined />}
                onClick={handleBatchExpandOutlines}
                loading={isExpanding}
                disabled={isGenerating}
                title="将所有大纲展开为多章，实现从大纲到章节的一对多关系"
              >
                {isMobile ? '批量展开' : '批量展开为多章'}
              </Button>
            )}
          </Space>
        </div>

        {/* 可滚动内容区域 */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {/* 节奏分布图表区域 */}
          {outlines.length > 0 && rhythmAnalysis && (
            <Collapse
              defaultActiveKey={['curve']}
              style={{ marginBottom: 16 }}
              items={[
                {
                  key: 'distribution',
                  label: (
                    <Space>
                      <BarChartOutlined style={{ color: token.colorPrimary }} />
                      <span style={{ fontWeight: 500 }}>章节类型分布</span>
                      <Tag color="blue">
                        {rhythmAnalysis.data_level === 'chapter'
                          ? `${rhythmAnalysis.distribution.total} 章（来自 ${rhythmAnalysis.total_outlines || 0} 个大纲）`
                          : `${rhythmAnalysis.distribution.total} 个大纲`}
                      </Tag>
                    </Space>
                  ),
                  children: (
                    <div style={{ padding: '8px 0' }}>
                      {/* 分布柱状图 */}
                      <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(4, 1fr)', gap: 8 }}>
                        {Object.entries(rhythmAnalysis.distribution.counts)
                          .filter(([, count]) => count > 0)
                          .sort((a, b) => b[1] - a[1])
                          .map(([type, count]) => {
                            const pct = rhythmAnalysis.distribution.percentages[type] || 0;
                            // 根据类型选择颜色（细粒度场景类型）
                            let barColor = token.colorPrimary;
                            let bgColor = token.colorPrimaryBg;
                            // 高潮类型
                            if (type.includes('高潮')) { barColor = '#ff4d4f'; bgColor = '#fff1f0'; }
                            // 主线类型
                            else if (type.includes('主线')) { barColor = '#1890ff'; bgColor = '#e6f7ff'; }
                            // 支线类型
                            else if (type.includes('支线')) { barColor = '#13c2c2'; bgColor = '#e6fffb'; }
                            // 感情线类型
                            else if (type.includes('感情') || type.includes('恋爱')) { barColor = '#f5222d'; bgColor = '#fff1f0'; }
                            // 人物关系类型
                            else if (type.includes('人物') || type.includes('关系')) { barColor = '#eb2f96'; bgColor = '#fff0f6'; }
                            // 奇遇类型
                            else if (type.includes('奇遇') || type.includes('机缘')) { barColor = '#faad14'; bgColor = '#fffbe6'; }
                            // 秘境副本类型
                            else if (type.includes('秘境') || type.includes('副本') || type.includes('探险')) { barColor = '#722ed1'; bgColor = '#f9f0ff'; }
                            // 反派视角类型
                            else if (type.includes('反派') || type.includes('敌人') || type.includes('对手')) { barColor = '#595959'; bgColor = '#fafafa'; }
                            // 日常互动类型
                            else if (type.includes('日常') || type.includes('生活')) { barColor = '#52c41a'; bgColor = '#f6ffed'; }
                            // 战斗类型
                            else if (type.includes('战斗') || type.includes('打斗') || type.includes('对决')) { barColor = '#fa8c16'; bgColor = '#fff2e8'; }
                            // 修炼成长类型
                            else if (type.includes('修炼') || type.includes('成长') || type.includes('突破')) { barColor = '#2f54eb'; bgColor = '#f0f5ff'; }
                            // 势力冲突类型
                            else if (type.includes('势力') || type.includes('门派') || type.includes('阵营')) { barColor = '#13c2c2'; bgColor = '#e6fffb'; }
                            // 伏笔类型
                            else if (type.includes('伏笔') || type.includes('铺垫')) { barColor = '#faad14'; bgColor = '#fffbe6'; }
                            // 过渡类型
                            else if (type.includes('过渡')) { barColor = '#8c8c8c'; bgColor = '#f5f5f5'; }

                            return (
                              <Tooltip key={type} title={`${count} ${rhythmAnalysis.data_level === 'chapter' ? '章' : '个大纲'}，占比 ${pct}%`}>
                                <div style={{
                                  padding: '8px 12px',
                                  background: bgColor,
                                  borderRadius: token.borderRadius,
                                  border: `1px solid ${barColor}20`
                                }}>
                                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, fontSize: 12 }}>
                                    <span style={{ fontWeight: 500, color: barColor }}>{type}</span>
                                    <span style={{ color: token.colorTextSecondary }}>{count} ({pct}%)</span>
                                  </div>
                                  <Progress
                                    percent={pct}
                                    strokeColor={barColor}
                                    trailColor={barColor + '20'}
                                    showInfo={false}
                                    size="small"
                                  />
                                </div>
                              </Tooltip>
                            );
                          })}
                      </div>
                      {/* 节奏建议 */}
                      {rhythmAnalysis.suggestions && (
                        <div style={{
                          marginTop: 12,
                          padding: '12px 16px',
                          background: token.colorInfoBg,
                          borderLeft: `3px solid ${token.colorInfo}`,
                          borderRadius: token.borderRadius,
                          fontSize: 13,
                          lineHeight: '1.8'
                        }}>
                          <RhythmSuggestionsDisplay suggestions={rhythmAnalysis.suggestions} token={token} />
                        </div>
                      )}
                    </div>
                  )
                },
                {
                  key: 'curve',
                  label: (
                    <Space>
                      <LineChartOutlined style={{ color: token.colorSuccess }} />
                      <span style={{ fontWeight: 500 }}>节奏强度曲线</span>
                      <Tag color="green">
                        {rhythmAnalysis.data_level === 'chapter'
                          ? `${rhythmAnalysis.rhythm_curve.length} 章`
                          : `${rhythmAnalysis.rhythm_curve.length} 个大纲单元`}
                      </Tag>
                    </Space>
                  ),
                  children: (
                    <div style={{ padding: '8px 0' }}>
                      {/* 横向滚动柱状图容器 */}
                      <div style={{
                        position: 'relative',
                        width: '100%'
                      }}>
                        {/* 滚动提示 */}
                        {rhythmAnalysis.rhythm_curve.length > 20 && (
                          <div style={{
                            marginBottom: 8,
                            padding: '6px 12px',
                            background: token.colorInfoBg,
                            borderRadius: token.borderRadius,
                            fontSize: 12,
                            color: token.colorInfoText,
                            display: 'flex',
                            alignItems: 'center',
                            gap: 8
                          }}>
                            <span>💡</span>
                            <span>
                              {rhythmAnalysis.data_level === 'chapter'
                                ? `共有 ${rhythmAnalysis.rhythm_curve.length} 章，可左右滑动查看完整曲线`
                                : `共有 ${rhythmAnalysis.rhythm_curve.length} 个大纲，可左右滑动查看完整曲线`}
                            </span>
                          </div>
                        )}

                        {/* 横向柱状图 */}
                        <div style={{
                          display: 'flex',
                          flexDirection: 'row',
                          alignItems: 'flex-end',
                          gap: 2,
                          overflowX: 'auto',
                          overflowY: 'hidden',
                          padding: '10px 4px',
                          minHeight: 140,
                          maxHeight: 180,
                          background: token.colorFillQuaternary,
                          borderRadius: token.borderRadius,
                          scrollbarWidth: 'thin'
                        }}>
                          {rhythmAnalysis.rhythm_curve.map((item, idx) => {
                            // 根据强度选择颜色和标签
                            let intensityColor = '#8c8c8c';
                            let intensityLabel = '过渡';
                            if (item.intensity >= 8) {
                              intensityColor = '#ff4d4f'; intensityLabel = '高潮';
                            } else if (item.intensity >= 6) {
                              intensityColor = '#faad14'; intensityLabel = '紧张';
                            } else if (item.intensity >= 4) {
                              intensityColor = '#1890ff'; intensityLabel = '平稳';
                            }

                            // 柱状条高度：强度 * 12px（最小12px，最大120px）
                            const barHeight = Math.max(12, item.intensity * 12);

                            return (
                              <Tooltip
                                key={idx}
                                title={
                                  <div style={{ fontSize: 12 }}>
                                    <div><strong>#{item.index} {item.title}</strong></div>
                                    {rhythmAnalysis.data_level === 'chapter' && item.outline_title && (
                                      <div style={{ color: '#999', fontSize: 11 }}>
                                        大纲: {item.outline_title} ({item.sub_index ?? 1})
                                      </div>
                                    )}
                                    <div>类型: {item.all_types?.join(', ') || item.main_type}</div>
                                    <div>强度: {item.intensity}/10 ({intensityLabel})</div>
                                  </div>
                                }
                                placement="top"
                              >
                                <div
                                  style={{
                                    display: 'flex',
                                    flexDirection: 'column',
                                    alignItems: 'center',
                                    minWidth: isMobile ? 16 : 20,
                                    maxWidth: isMobile ? 16 : 20,
                                    cursor: 'pointer',
                                    transition: 'transform 0.2s ease'
                                  }}
                                  onMouseEnter={(e) => {
                                    e.currentTarget.style.transform = 'scaleY(1.1)';
                                  }}
                                  onMouseLeave={(e) => {
                                    e.currentTarget.style.transform = 'scaleY(1)';
                                  }}
                                >
                                  {/* 柱状条 */}
                                  <div
                                    style={{
                                      width: isMobile ? 12 : 16,
                                      height: barHeight,
                                      background: intensityColor,
                                      borderRadius: '2px 2px 0 0',
                                      transition: 'background 0.2s ease',
                                      position: 'relative'
                                    }}
                                  />
                                  {/* 序号标签 */}
                                  <span style={{
                                    fontSize: isMobile ? 9 : 10,
                                    color: token.colorTextSecondary,
                                    marginTop: 2,
                                    textAlign: 'center',
                                    minWidth: isMobile ? 16 : 20
                                  }}>
                                    {item.index > 99 ? '···' : item.index}
                                  </span>
                                </div>
                              </Tooltip>
                            );
                          })}
                        </div>

                        {/* 图例说明 */}
                        <div style={{
                          marginTop: 10,
                          display: 'flex',
                          flexWrap: 'wrap',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          gap: 8,
                          fontSize: 11
                        }}>
                          <div style={{ display: 'flex', gap: 6 }}>
                            <span style={{ color: token.colorTextSecondary }}>强度说明：</span>
                            <Tag color="red" style={{ margin: 0, fontSize: 10, padding: '0 6px' }}>8-10 高潮</Tag>
                            <Tag color="orange" style={{ margin: 0, fontSize: 10, padding: '0 6px' }}>6-7 紧张</Tag>
                            <Tag color="blue" style={{ margin: 0, fontSize: 10, padding: '0 6px' }}>4-5 平稳</Tag>
                            <Tag color="default" style={{ margin: 0, fontSize: 10, padding: '0 6px' }}>1-3 过渡</Tag>
                          </div>
                          <span style={{ color: token.colorTextTertiary, fontSize: 10 }}>
                            悬停查看详情
                          </span>
                        </div>
                      </div>
                    </div>
                  )
                }
              ]}
            />
          )}

          {/* 加载状态 */}
          {outlines.length > 0 && rhythmLoading && (
            <Card style={{ marginBottom: 16 }} styles={{ body: { textAlign: 'center', padding: 20 } }}>
              <Space>
                <BarChartOutlined spin style={{ color: token.colorPrimary }} />
                <span style={{ color: token.colorTextSecondary }}>正在加载节奏分析...</span>
              </Space>
            </Card>
          )}

          {outlines.length === 0 ? (
            <Empty description="还没有大纲，开始创建吧！" />
          ) : filteredOutlines.length === 0 ? (
            <Empty description="未找到匹配大纲" />
          ) : (
            <List
              dataSource={pagedOutlines}
              renderItem={(item) => {
                  const structureData = outlineStructureMap[item.id] || {};

                  // 解析角色/组织条目（兼容新旧格式）
                  const characterEntries = parseCharacterEntries(structureData.characters);
                  const characterNames = getCharacterNames(characterEntries);
                  const organizationNames = getOrganizationNames(characterEntries);
                  
                  return (
                    <List.Item
                      style={{
                        marginBottom: 16,
                        padding: 0,
                        border: 'none'
                      }}
                    >
                      <Card
                        style={{
                          width: '100%',
                          borderRadius: isMobile ? 6 : 8,
                          border: `1px solid ${token.colorBorderSecondary}`,
                          boxShadow: `0 1px 2px ${alphaColor(token.colorTextBase, 0.08)}`,
                          transition: 'all 0.3s ease'
                        }}
                        styles={{ body: { padding: isMobile ? '10px 12px' : 16 } }}
                        onMouseEnter={(e) => {
                          if (!isMobile) {
                            e.currentTarget.style.boxShadow = `0 4px 12px ${alphaColor(token.colorTextBase, 0.16)}`;
                            e.currentTarget.style.borderColor = token.colorPrimary;
                          }
                        }}
                        onMouseLeave={(e) => {
                          if (!isMobile) {
                            e.currentTarget.style.boxShadow = `0 1px 2px ${alphaColor(token.colorTextBase, 0.08)}`;
                            e.currentTarget.style.borderColor = token.colorBorderSecondary;
                          }
                        }}
                      >
                        <List.Item.Meta
                          style={{ width: '100%' }}
                          title={
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                              <Space size="small" style={{ fontSize: isMobile ? 13 : 16, flexWrap: 'wrap', lineHeight: isMobile ? '1.4' : '1.5' }}>
                                <span style={{ color: token.colorPrimary, fontWeight: 'bold', fontSize: isMobile ? 13 : 16 }}>
                                  {currentProject?.outline_mode === 'one-to-one'
                                    ? `第${item.order_index || '?'}章`
                                    : `第${item.order_index || '?'}卷`
                                  }
                                </span>
                                <span style={{ fontSize: isMobile ? 13 : 16 }}>{item.title}</span>
                                {/* ✅ 新增：展开状态标识 - 仅在一对多模式显示 */}
                                {currentProject?.outline_mode === 'one-to-many' && (
                                  outlineExpandStatus[item.id] ? (
                                    <Tag color="success" icon={<CheckCircleOutlined />} style={{ fontSize: isMobile ? 11 : 12 }}>已展开</Tag>
                                  ) : (
                                    <Tag color="default" style={{ fontSize: isMobile ? 11 : 12 }}>未展开</Tag>
                                  )
                                )}
                              </Space>
                              {/* ✅ 新增：卡片内容展开/收起按钮 */}
                              <Button
                                type="text"
                                size="small"
                                icon={outlineCardExpanded[item.id] ? <UpOutlined /> : <DownOutlined />}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setOutlineCardExpanded(prev => ({
                                    ...prev,
                                    [item.id]: !prev[item.id]
                                  }));
                                }}
                                style={{ marginLeft: 8 }}
                              />
                            </div>
                          }
                          description={
                            <div style={{ fontSize: isMobile ? 12 : 14, lineHeight: isMobile ? '1.5' : '1.6' }}>
                              {/* 收起时只显示大纲内容摘要 */}
                              {!outlineCardExpanded[item.id] && (
                                <div style={{
                                  padding: isMobile ? '6px 8px' : '6px 10px',
                                  background: token.colorBgContainer,
                                  border: `1px solid ${token.colorBorder}`,
                                  borderRadius: token.borderRadiusSM,
                                  fontSize: isMobile ? 12 : 13,
                                  color: token.colorText,
                                  lineHeight: '1.6',
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  whiteSpace: 'nowrap'
                                }}>
                                  {item.content}
                                </div>
                              )}
                              {/* 展开时显示完整内容 */}
                              {outlineCardExpanded[item.id] && (
                                <>
                              {/* 大纲内容 */}
                              <div style={{
                                marginBottom: isMobile ? 10 : 12,
                                padding: isMobile ? '8px 10px' : '10px 12px',
                                background: token.colorFillQuaternary,
                                borderLeft: `3px solid ${token.colorBorderSecondary}`,
                                borderRadius: token.borderRadius,
                                fontSize: isMobile ? 12 : 13,
                                color: token.colorText,
                                lineHeight: '1.6'
                              }}>
                                <div style={{
                                  fontWeight: 600,
                                  color: token.colorTextSecondary,
                                  marginBottom: isMobile ? 4 : 6,
                                  fontSize: isMobile ? 12 : 13
                                }}>
                                  📝 大纲内容
                                </div>
                                <div style={{
                                  padding: isMobile ? '6px 8px' : '6px 10px',
                                  background: token.colorBgContainer,
                                  border: `1px solid ${token.colorBorder}`,
                                  borderRadius: token.borderRadiusSM,
                                  fontSize: isMobile ? 12 : 13,
                                  color: token.colorText,
                                  lineHeight: '1.6'
                                }}>
                                  {item.content}
                                </div>
                              </div>
                              
                              {/* ✨ 涉及角色展示 - 优化版（支持角色/组织分类显示） */}
                              {characterNames.length > 0 && (
                                <div style={{
                                  marginTop: isMobile ? 10 : 12,
                                  padding: isMobile ? '8px 10px' : '10px 12px',
                                  background: token.colorPrimaryBg,
                                  borderLeft: `3px solid ${token.colorPrimary}`,
                                  borderRadius: token.borderRadius
                                }}>
                                  <div style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: isMobile ? 6 : 8,
                                    marginBottom: isMobile ? 6 : 8
                                  }}>
                                    <span style={{
                                      fontSize: isMobile ? 12 : 13,
                                      fontWeight: 600,
                                      color: token.colorPrimary,
                                      display: 'flex',
                                      alignItems: 'center',
                                      gap: 4
                                    }}>
                                      👥 涉及角色
                                      <Tag
                                        color="purple"
                                        style={{
                                          margin: 0,
                                          fontSize: 10,
                                          borderRadius: 10,
                                          padding: '0 6px'
                                        }}
                                      >
                                        {characterNames.length}
                                      </Tag>
                                    </span>
                                  </div>
                                  <Space wrap size={[4, 4]}>
                                    {characterNames.map((name, idx) => (
                                      <Tag
                                        key={idx}
                                        color="purple"
                                        style={{
                                          margin: 0,
                                          borderRadius: 4,
                                          padding: isMobile ? '2px 8px' : '3px 10px',
                                          fontSize: isMobile ? 11 : 12,
                                          fontWeight: 500,
                                          border: `1px solid ${token.colorPrimaryBorder}`,
                                          background: token.colorBgContainer,
                                          color: token.colorPrimary,
                                          whiteSpace: 'normal',
                                          wordBreak: 'break-word',
                                          height: 'auto',
                                          lineHeight: '1.5'
                                        }}
                                      >
                                        {name}
                                      </Tag>
                                    ))}
                                  </Space>
                                </div>
                              )}
                              
                              {/* 🏛️ 涉及组织展示 */}
                              {organizationNames.length > 0 && (
                                <div style={{
                                  marginTop: isMobile ? 10 : 12,
                                  padding: isMobile ? '8px 10px' : '10px 12px',
                                  background: token.colorWarningBg,
                                  borderLeft: `3px solid ${token.colorWarning}`,
                                  borderRadius: token.borderRadius
                                }}>
                                  <div style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: isMobile ? 6 : 8,
                                    marginBottom: isMobile ? 6 : 8
                                  }}>
                                    <span style={{
                                      fontSize: isMobile ? 12 : 13,
                                      fontWeight: 600,
                                      color: token.colorWarning,
                                      display: 'flex',
                                      alignItems: 'center',
                                      gap: 4
                                    }}>
                                      🏛️ 涉及组织
                                      <Tag
                                        color="orange"
                                        style={{
                                          margin: 0,
                                          fontSize: 10,
                                          borderRadius: 10,
                                          padding: '0 6px'
                                        }}
                                      >
                                        {organizationNames.length}
                                      </Tag>
                                    </span>
                                  </div>
                                  <Space wrap size={[4, 4]}>
                                    {organizationNames.map((name, idx) => (
                                      <Tag
                                        key={idx}
                                        color="orange"
                                        style={{
                                          margin: 0,
                                          borderRadius: 4,
                                          padding: isMobile ? '2px 8px' : '3px 10px',
                                          fontSize: isMobile ? 11 : 12,
                                          fontWeight: 500,
                                          border: `1px solid ${token.colorWarningBorder}`,
                                          background: token.colorBgContainer,
                                          color: token.colorWarning,
                                          whiteSpace: 'normal',
                                          wordBreak: 'break-word',
                                          height: 'auto',
                                          lineHeight: '1.5'
                                        }}
                                      >
                                        {name}
                                      </Tag>
                                    ))}
                                  </Space>
                                </div>
                              )}
                              
                              {/* ✨ 场景信息展示 - 优化版（支持折叠，最多显示3个） */}
                              {structureData.scenes && structureData.scenes.length > 0 ? (() => {
                                const isExpanded = scenesExpandStatus[item.id] || false;
                                const maxVisibleScenes = 4;
                                const hasMoreScenes = structureData.scenes!.length > maxVisibleScenes;
                                const visibleScenes = isExpanded ? structureData.scenes : structureData.scenes!.slice(0, maxVisibleScenes);
                                
                                return (
                                  <div style={{
                                    marginTop: isMobile ? 10 : 12,
                                    padding: isMobile ? '8px 10px' : '10px 12px',
                                    background: token.colorInfoBg,
                                    borderLeft: `3px solid ${token.colorInfo}`,
                                    borderRadius: token.borderRadius
                                  }}>
                                    <div style={{
                                      display: 'flex',
                                      alignItems: 'center',
                                      justifyContent: 'space-between',
                                      marginBottom: isMobile ? 6 : 8,
                                      flexWrap: isMobile ? 'wrap' : 'nowrap',
                                      gap: isMobile ? 4 : 0
                                    }}>
                                      <span style={{
                                        fontSize: isMobile ? 12 : 13,
                                        fontWeight: 600,
                                        color: token.colorInfo,
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: 4
                                      }}>
                                        🎬 场景设定
                                        <Tag
                                          color="cyan"
                                          style={{
                                            margin: 0,
                                            fontSize: 10,
                                            borderRadius: 10,
                                            padding: '0 6px'
                                          }}
                                        >
                                          {structureData.scenes!.length}
                                        </Tag>
                                      </span>
                                      {hasMoreScenes && (
                                        <Button
                                          type="text"
                                          size="small"
                                          onClick={() => setScenesExpandStatus(prev => ({
                                            ...prev,
                                            [item.id]: !isExpanded
                                          }))}
                                          style={{
                                            fontSize: isMobile ? 10 : 11,
                                            height: isMobile ? 20 : 22,
                                            padding: isMobile ? '0 6px' : '0 8px',
                                            color: token.colorInfo
                                          }}
                                        >
                                          {isExpanded ? '收起 ▲' : `展开 (${structureData.scenes!.length - maxVisibleScenes}+) ▼`}
                                        </Button>
                                      )}
                                    </div>
                                    {/* 使用grid布局，移动端一列，桌面端两列 */}
                                    <div style={{
                                      display: 'grid',
                                      gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fill, minmax(280px, 1fr))',
                                      gap: isMobile ? 6 : 8,
                                      width: '100%',
                                      minWidth: 0  // 防止grid子元素溢出
                                    }}>
                                      {visibleScenes!.map((scene, idx) => {
                                      // 判断是字符串还是对象
                                      if (typeof scene === 'string') {
                                        // 字符串格式：简洁卡片
                                        return (
                                          <div
                                            key={idx}
                                            style={{
                                              padding: isMobile ? '6px 8px' : '8px 10px',
                                              background: token.colorBgContainer,
                                              border: `1px solid ${token.colorInfoBorder}`,
                                              borderRadius: token.borderRadius,
                                              fontSize: isMobile ? 11 : 12,
                                              color: token.colorText,
                                              display: 'flex',
                                              alignItems: 'flex-start',
                                              gap: isMobile ? 6 : 8,
                                              transition: 'all 0.2s ease',
                                              cursor: 'default',
                                              width: '100%',
                                              minWidth: 0,
                                              boxSizing: 'border-box'
                                            }}
                                            onMouseEnter={(e) => {
                                              if (!isMobile) {
                                                e.currentTarget.style.borderColor = token.colorInfo;
                                                e.currentTarget.style.boxShadow = `0 2px 8px ${alphaColor(token.colorInfo, 0.25)}`;
                                              }
                                            }}
                                            onMouseLeave={(e) => {
                                              if (!isMobile) {
                                                e.currentTarget.style.borderColor = token.colorInfoBorder;
                                                e.currentTarget.style.boxShadow = 'none';
                                              }
                                            }}
                                          >
                                            <Tag
                                              color="cyan"
                                              style={{
                                                margin: 0,
                                                fontSize: 10,
                                                borderRadius: 4,
                                                flexShrink: 0
                                              }}
                                            >
                                              {idx + 1}
                                            </Tag>
                                            <span style={{
                                              flex: 1,
                                              lineHeight: '1.6',
                                              overflow: 'hidden',
                                              textOverflow: 'ellipsis',
                                              whiteSpace: 'nowrap'
                                            }}>{scene}</span>
                                          </div>
                                        );
                                      } else {
                                        // 对象格式：详细卡片
                                        return (
                                          <div
                                            key={idx}
                                            style={{
                                              padding: isMobile ? '8px 10px' : '10px 12px',
                                              background: token.colorBgContainer,
                                              border: `1px solid ${token.colorInfoBorder}`,
                                              borderRadius: token.borderRadius,
                                              fontSize: isMobile ? 11 : 12,
                                              transition: 'all 0.2s ease',
                                              cursor: 'default',
                                              width: '100%',
                                              minWidth: 0,
                                              boxSizing: 'border-box'
                                            }}
                                            onMouseEnter={(e) => {
                                              if (!isMobile) {
                                                e.currentTarget.style.borderColor = token.colorInfo;
                                                e.currentTarget.style.boxShadow = `0 2px 8px ${alphaColor(token.colorInfo, 0.25)}`;
                                              }
                                            }}
                                            onMouseLeave={(e) => {
                                              if (!isMobile) {
                                                e.currentTarget.style.borderColor = token.colorInfoBorder;
                                                e.currentTarget.style.boxShadow = 'none';
                                              }
                                            }}
                                          >
                                            <div style={{
                                              display: 'flex',
                                              alignItems: 'center',
                                              gap: isMobile ? 6 : 8,
                                              marginBottom: isMobile ? 4 : 6,
                                              flexWrap: 'wrap'
                                            }}>
                                              <Tag
                                                color="cyan"
                                                style={{
                                                  margin: 0,
                                                  fontSize: 10,
                                                  borderRadius: 4
                                                }}
                                              >
                                                场景{idx + 1}
                                              </Tag>
                                              <span style={{
                                                fontWeight: 600,
                                                color: token.colorText,
                                                fontSize: isMobile ? 12 : 13,
                                                flex: 1,
                                                overflow: 'hidden',
                                                textOverflow: 'ellipsis',
                                                whiteSpace: 'nowrap'
                                              }}>
                                                📍 {scene.location}
                                              </span>
                                            </div>
                                            {scene.characters && scene.characters.length > 0 && (
                                              <div style={{
                                                fontSize: isMobile ? 10 : 11,
                                                color: token.colorTextSecondary,
                                                marginBottom: 4,
                                                paddingLeft: isMobile ? 2 : 4,
                                                overflow: 'hidden',
                                                textOverflow: 'ellipsis',
                                                whiteSpace: 'nowrap'
                                              }}>
                                                <span style={{ fontWeight: 500 }}>👤 角色：</span>
                                                {scene.characters.join(' · ')}
                                              </div>
                                            )}
                                            {scene.purpose && (
                                              <div style={{
                                                fontSize: isMobile ? 10 : 11,
                                                color: token.colorTextSecondary,
                                                paddingLeft: isMobile ? 2 : 4,
                                                lineHeight: '1.5',
                                                overflow: 'hidden',
                                                textOverflow: 'ellipsis',
                                                whiteSpace: 'nowrap'
                                              }}>
                                                <span style={{ fontWeight: 500 }}>🎯 目的：</span>
                                                {scene.purpose}
                                              </div>
                                            )}
                                          </div>
                                        );
                                      }
                                      })}
                                    </div>
                                  </div>
                                );
                              })() : null}
                            
                            {/* ✨ 关键事件展示 */}
                            {structureData.key_events && structureData.key_events.length > 0 && (
                              <div style={{
                                marginTop: 12,
                                padding: '10px 12px',
                                background: token.colorWarningBg,
                                borderLeft: `3px solid ${token.colorWarning}`,
                                borderRadius: token.borderRadius
                              }}>
                                <div style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: 8,
                                  marginBottom: 8
                                }}>
                                  <span style={{
                                    fontSize: 13,
                                    fontWeight: 600,
                                    color: token.colorWarning,
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 4
                                  }}>
                                    ⚡ 关键事件
                                    <Tag
                                      color="orange"
                                      style={{
                                        margin: 0,
                                        fontSize: 11,
                                        borderRadius: 10,
                                        padding: '0 6px'
                                      }}
                                    >
                                      {structureData.key_events.length}
                                    </Tag>
                                  </span>
                                </div>
                                <Space direction="vertical" size={6} style={{ width: '100%' }}>
                                  {structureData.key_events.map((event, idx) => (
                                    <div
                                      key={idx}
                                      style={{
                                        padding: '6px 10px',
                                        background: token.colorBgContainer,
                                        border: `1px solid ${token.colorWarningBorder}`,
                                        borderRadius: token.borderRadiusSM,
                                        fontSize: 12,
                                        color: token.colorWarningText,
                                        display: 'flex',
                                        alignItems: 'flex-start',
                                        gap: 8
                                      }}
                                    >
                                      <Tag
                                        color="orange"
                                        style={{
                                          margin: 0,
                                          fontSize: 11,
                                          borderRadius: 4,
                                          flexShrink: 0
                                        }}
                                      >
                                        {idx + 1}
                                      </Tag>
                                      <span style={{
                                        flex: 1,
                                        lineHeight: '1.6',
                                        overflow: 'hidden',
                                        textOverflow: 'ellipsis',
                                        whiteSpace: 'nowrap'
                                      }}>{event}</span>
                                    </div>
                                  ))}
                                </Space>
                              </div>
                            )}
                            
                            {/* ✨ 情节要点展示 (key_points) */}
                            {structureData.key_points && structureData.key_points.length > 0 && (
                              <div style={{
                                marginTop: 12,
                                padding: '10px 12px',
                                background: token.colorSuccessBg,
                                borderLeft: `3px solid ${token.colorSuccess}`,
                                borderRadius: token.borderRadius
                              }}>
                                <div style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: 8,
                                  marginBottom: 8
                                }}>
                                  <span style={{
                                    fontSize: 13,
                                    fontWeight: 600,
                                    color: token.colorSuccess,
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 4
                                  }}>
                                    💡 情节要点
                                    <Tag
                                      color="green"
                                      style={{
                                        margin: 0,
                                        fontSize: 11,
                                        borderRadius: 10,
                                        padding: '0 6px'
                                      }}
                                    >
                                      {structureData.key_points.length}
                                    </Tag>
                                  </span>
                                </div>
                                {/* 使用grid布局，移动端一列，桌面端两列 */}
                                <div style={{
                                  display: 'grid',
                                  gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fill, minmax(280px, 1fr))',
                                  gap: isMobile ? 6 : 8,
                                  width: '100%',
                                  minWidth: 0
                                }}>
                                  {structureData.key_points.map((point, idx) => (
                                    <div
                                      key={idx}
                                      style={{
                                        padding: isMobile ? '6px 8px' : '8px 10px',
                                        background: token.colorBgContainer,
                                        border: `1px solid ${token.colorSuccessBorder}`,
                                        borderRadius: token.borderRadius,
                                        fontSize: isMobile ? 11 : 12,
                                        color: token.colorText,
                                        display: 'flex',
                                        alignItems: 'flex-start',
                                        gap: isMobile ? 6 : 8,
                                        transition: 'all 0.2s ease',
                                        cursor: 'default',
                                        width: '100%',
                                        minWidth: 0,
                                        boxSizing: 'border-box'
                                      }}
                                      onMouseEnter={(e) => {
                                        if (!isMobile) {
                                          e.currentTarget.style.borderColor = token.colorSuccess;
                                          e.currentTarget.style.boxShadow = `0 2px 8px ${alphaColor(token.colorSuccess, 0.25)}`;
                                        }
                                      }}
                                      onMouseLeave={(e) => {
                                        if (!isMobile) {
                                          e.currentTarget.style.borderColor = token.colorSuccessBorder;
                                          e.currentTarget.style.boxShadow = 'none';
                                        }
                                      }}
                                    >
                                      <Tag
                                        color="green"
                                        style={{
                                          margin: 0,
                                          fontSize: 10,
                                          borderRadius: 4,
                                          flexShrink: 0
                                        }}
                                      >
                                        {idx + 1}
                                      </Tag>
                                      <span style={{
                                        flex: 1,
                                        lineHeight: '1.6',
                                        overflow: 'hidden',
                                        textOverflow: 'ellipsis',
                                        whiteSpace: 'nowrap'
                                      }}>{point}</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            
                            {/* ✨ 情感基调展示 (emotion) */}
                            {structureData.emotion && (
                              <div style={{
                                marginTop: 12,
                                padding: '10px 12px',
                                background: token.colorWarningBg,
                                borderLeft: `3px solid ${token.colorWarning}`,
                                borderRadius: token.borderRadius,
                                display: 'flex',
                                alignItems: 'center',
                                gap: 8
                              }}>
                                <span style={{
                                  fontSize: 13,
                                  fontWeight: 600,
                                  color: token.colorWarning
                                }}>
                                  💫 情感基调：
                                </span>
                                <Tag
                                  color="gold"
                                  style={{
                                    margin: 0,
                                    fontSize: 12,
                                    padding: '2px 12px',
                                    borderRadius: 12,
                                    background: token.colorBgContainer,
                                    border: `1px solid ${token.colorWarningBorder}`,
                                    color: token.colorWarningText
                                  }}
                                >
                                  {structureData.emotion}
                                </Tag>
                              </div>
                            )}
                            
                            {/* ✨ 叙事目标展示 (goal) */}
                            {structureData.goal && (
                              <div style={{
                                marginTop: 12,
                                padding: '10px 12px',
                                background: token.colorInfoBg,
                                borderLeft: `3px solid ${token.colorInfo}`,
                                borderRadius: token.borderRadius
                              }}>
                                <div style={{
                                  fontSize: 13,
                                  fontWeight: 600,
                                  color: token.colorInfo,
                                  marginBottom: 6
                                }}>
                                  🎯 叙事目标
                                </div>
                                <div style={{
                                  fontSize: 12,
                                  color: token.colorText,
                                  lineHeight: '1.6',
                                  padding: '6px 10px',
                                  background: token.colorBgContainer,
                                  border: `1px solid ${token.colorInfoBorder}`,
                                  borderRadius: token.borderRadiusSM,
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  whiteSpace: 'nowrap'
                                }}>
                                  {structureData.goal}
                                </div>
                              </div>
                            )}

                            {/* ✨ 章节类型展示 (chapter_types) */}
                            {structureData.chapter_types && structureData.chapter_types.length > 0 && (
                              <div style={{
                                marginTop: 12,
                                padding: '10px 12px',
                                background: token.colorPrimaryBg,
                                borderLeft: `3px solid ${token.colorPrimary}`,
                                borderRadius: token.borderRadius
                              }}>
                                <div style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: 8,
                                  marginBottom: 8
                                }}>
                                  <span style={{
                                    fontSize: 13,
                                    fontWeight: 600,
                                    color: token.colorPrimary,
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 4
                                  }}>
                                    📊 章节类型
                                    <Tag
                                      color="blue"
                                      style={{
                                        margin: 0,
                                        fontSize: 11,
                                        borderRadius: 10,
                                        padding: '0 6px'
                                      }}
                                    >
                                      {structureData.chapter_types.length}
                                    </Tag>
                                  </span>
                                </div>
                                <Space wrap size={[4, 4]}>
                                  {structureData.chapter_types.map((type, idx) => {
                                    // 解析类型名称和占比
                                    const typeMatch = type.match(/^([^(]+)\(?(\d*%?)?\)?$/);
                                    const typeName = typeMatch ? typeMatch[1].trim() : type;
                                    const percentage = typeMatch && typeMatch[2] ? typeMatch[2] : '';
                                    // 根据类型名称选择颜色
                                    let tagColor = 'blue';
                                    if (typeName.includes('高潮')) tagColor = 'red';
                                    else if (typeName.includes('主线')) tagColor = 'blue';
                                    else if (typeName.includes('支线')) tagColor = 'cyan';
                                    else if (typeName.includes('奇遇')) tagColor = 'gold';
                                    else if (typeName.includes('秘境') || typeName.includes('副本')) tagColor = 'purple';
                                    else if (typeName.includes('人物') || typeName.includes('关系')) tagColor = 'pink';
                                    else if (typeName.includes('过渡')) tagColor = 'default';

                                    return (
                                      <Tag
                                        key={idx}
                                        color={tagColor}
                                        style={{
                                          margin: 0,
                                          borderRadius: 4,
                                          padding: isMobile ? '2px 8px' : '3px 10px',
                                          fontSize: isMobile ? 11 : 12,
                                          fontWeight: 500,
                                          whiteSpace: 'normal',
                                          wordBreak: 'break-word',
                                          height: 'auto',
                                          lineHeight: '1.5'
                                        }}
                                      >
                                        {typeName}{percentage && ` (${percentage})`}
                                      </Tag>
                                    );
                                  })}
                                </Space>
                              </div>
                            )}

                            {/* ✨ 故事线展示 (story_lines) */}
                            {structureData.story_lines && structureData.story_lines.length > 0 && (
                              <div style={{
                                marginTop: 12,
                                padding: '10px 12px',
                                background: token.colorSuccessBg,
                                borderLeft: `3px solid ${token.colorSuccess}`,
                                borderRadius: token.borderRadius
                              }}>
                                <div style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: 8,
                                  marginBottom: 8
                                }}>
                                  <span style={{
                                    fontSize: 13,
                                    fontWeight: 600,
                                    color: token.colorSuccess,
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 4
                                  }}>
                                    🔗 故事线
                                    <Tag
                                      color="green"
                                      style={{
                                        margin: 0,
                                        fontSize: 11,
                                        borderRadius: 10,
                                        padding: '0 6px'
                                      }}
                                    >
                                      {structureData.story_lines.length}
                                    </Tag>
                                  </span>
                                </div>
                                <Space wrap size={[4, 4]}>
                                  {structureData.story_lines.map((line, idx) => (
                                    <Tag
                                      key={idx}
                                      color="green"
                                      style={{
                                        margin: 0,
                                        borderRadius: 4,
                                        padding: isMobile ? '2px 8px' : '3px 10px',
                                        fontSize: isMobile ? 11 : 12,
                                        fontWeight: 500,
                                        whiteSpace: 'normal',
                                        wordBreak: 'break-word',
                                        height: 'auto',
                                        lineHeight: '1.5'
                                      }}
                                    >
                                      {line}
                                    </Tag>
                                  ))}
                                </Space>
                              </div>
                            )}

                            {/* ✨ 节奏强度展示 (rhythm_intensity & rhythm_range) */}
                            {(structureData.rhythm_intensity || structureData.rhythm_range) && (
                              <div style={{
                                marginTop: 12,
                                padding: '10px 12px',
                                background: token.colorWarningBg,
                                borderLeft: `3px solid ${token.colorWarning}`,
                                borderRadius: token.borderRadius
                              }}>
                                <div style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'space-between',
                                  flexWrap: 'wrap',
                                  gap: 8
                                }}>
                                  <span style={{
                                    fontSize: 13,
                                    fontWeight: 600,
                                    color: token.colorWarning,
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 4
                                  }}>
                                    ⚡ 节奏强度
                                  </span>
                                  <Space size={8} wrap>
                                    {structureData.rhythm_intensity && (
                                      <Tag
                                        color={
                                          structureData.rhythm_intensity >= 8 ? 'red' :
                                          structureData.rhythm_intensity >= 6 ? 'orange' :
                                          structureData.rhythm_intensity >= 4 ? 'blue' : 'default'
                                        }
                                        style={{
                                          margin: 0,
                                          borderRadius: 12,
                                          padding: '2px 12px',
                                          fontSize: 12,
                                          fontWeight: 500
                                        }}
                                      >
                                        {structureData.rhythm_intensity}/10
                                        {structureData.rhythm_intensity >= 8 && ' (高潮)'}
                                        {structureData.rhythm_intensity >= 6 && structureData.rhythm_intensity < 8 && ' (紧张)'}
                                        {structureData.rhythm_intensity >= 4 && structureData.rhythm_intensity < 6 && ' (平稳)'}
                                        {structureData.rhythm_intensity < 4 && ' (过渡)'}
                                      </Tag>
                                    )}
                                    {structureData.rhythm_range && (
                                      <Tag
                                        color="gold"
                                        style={{
                                          margin: 0,
                                          borderRadius: 12,
                                          padding: '2px 12px',
                                          fontSize: 12
                                        }}
                                      >
                                        范围: {structureData.rhythm_range}
                                      </Tag>
                                    )}
                                  </Space>
                                </div>
                              </div>
                            )}

                            {/* ✨ 时间信息展示 */}
                            {(item.created_at || item.updated_at) && (
                              <div style={{
                                marginTop: 12,
                                padding: '8px 12px',
                                background: token.colorFillQuaternary,
                                borderRadius: token.borderRadius,
                                fontSize: isMobile ? 11 : 12,
                                color: token.colorTextSecondary,
                                display: 'flex',
                                flexWrap: 'wrap',
                                gap: isMobile ? 4 : 12
                              }}>
                                {item.created_at && (
                                  <span>
                                    📅 创建于：{new Date(item.created_at).toLocaleString('zh-CN', {
                                      year: 'numeric',
                                      month: '2-digit',
                                      day: '2-digit',
                                      hour: '2-digit',
                                      minute: '2-digit'
                                    })}
                                  </span>
                                )}
                                {item.updated_at && item.updated_at !== item.created_at && (
                                  <span>
                                    🕐 更新于：{new Date(item.updated_at).toLocaleString('zh-CN', {
                                      year: 'numeric',
                                      month: '2-digit',
                                      day: '2-digit',
                                      hour: '2-digit',
                                      minute: '2-digit'
                                    })}
                                  </span>
                                )}
                              </div>
                            )}
                                </>
                              )}
                            </div>
                          }
                      />
                        
                        {/* 操作按钮区域 - 在卡片内部 */}
                        <div style={{
                          marginTop: 16,
                          paddingTop: 12,
                          borderTop: `1px solid ${token.colorBorderSecondary}`,
                          display: 'flex',
                          justifyContent: 'flex-end',
                          gap: 8
                        }}>
                          {currentProject?.outline_mode === 'one-to-many' && (
                            <Button
                              icon={<BranchesOutlined />}
                              onClick={() => handleExpandOutline(item.id, item.title)}
                              loading={isExpanding}
                              size={isMobile ? 'middle' : 'small'}
                            >
                              拆分
                            </Button>
                          )}
                          <Button
                            icon={<EditOutlined />}
                            onClick={() => handleOpenEditModal(item.id)}
                            size={isMobile ? 'middle' : 'small'}
                          >
                            编辑
                          </Button>
                          <Popconfirm
                            title="确定删除这条大纲吗？"
                            onConfirm={() => handleDeleteOutline(item.id)}
                            okText="确定"
                            cancelText="取消"
                          >
                            <Button
                              danger
                              icon={<DeleteOutlined />}
                              size={isMobile ? 'middle' : 'small'}
                            >
                              删除
                            </Button>
                          </Popconfirm>
                        </div>
                      </Card>
                    </List.Item>
                  );
                }}
              />
          )}

        </div>

        {/* 固定底部分页栏 */}
        {outlines.length > 0 && (
          <div
            style={{
              position: 'sticky',
              bottom: 0,
              zIndex: 10,
              backgroundColor: token.colorBgContainer,
              borderTop: `1px solid ${token.colorBorderSecondary}`,
              padding: isMobile ? '8px 0' : '10px 0',
              display: 'flex',
              justifyContent: 'flex-end'
            }}
          >
            <Pagination
              current={outlinePage}
              pageSize={outlinePageSize}
              total={filteredOutlines.length}
              showSizeChanger
              pageSizeOptions={['10', '20', '50', '100']}
              onChange={(page, size) => {
                setOutlinePage(page);
                if (size !== outlinePageSize) {
                  setOutlinePageSize(size);
                  setOutlinePage(1);
                }
              }}
              showTotal={(total) => `共 ${total} 条`}
              size={isMobile ? 'small' : 'default'}
            />
          </div>
        )}
      </div>
    </>
  );
}
