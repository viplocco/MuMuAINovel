import React, { useState, useEffect } from 'react';
import {
  Modal,
  Form,
  Input,
  Button,
  Checkbox,
  InputNumber,
  Space,
  Alert,
  Divider,
  Tag,
  App,
  Collapse,
  Card,
  Radio,
  Tooltip,
  List,
  Empty
} from 'antd';
import {
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  PlusOutlined,
  BookOutlined,
  DownOutlined,
  UpOutlined
} from '@ant-design/icons';
import { ssePost } from '../utils/sseClient';
import { SSEProgressModal } from './SSEProgressModal';
import { writingStyleApi } from '../services/api';
import type { WritingStyle } from '../types';

const { TextArea } = Input;

// localStorage 缓存键名（与 Chapters.tsx 共用）
const WORD_COUNT_CACHE_KEY = 'chapter_default_word_count';
const DEFAULT_WORD_COUNT = 3000;

// 从 localStorage 读取缓存的字数
const getCachedWordCount = (): number => {
  try {
    const cached = localStorage.getItem(WORD_COUNT_CACHE_KEY);
    if (cached) {
      const value = parseInt(cached, 10);
      if (value >= 500 && value <= 10000) {
        return value;
      }
    }
  } catch (error) {
    console.warn('读取字数缓存失败:', error);
  }
  return DEFAULT_WORD_COUNT;
};

interface Suggestion {
  category: string;
  content: string;
  priority: string;
}

// 分析分数接口
interface AnalysisScores {
  pacing_score?: number;
  engagement_score?: number;
  coherence_score?: number;
  overall_quality_score?: number;
  // 新增指标用于更精确推荐
  emotional_intensity?: number;
  conflict_level?: number;
  dialogue_ratio?: number;
  description_ratio?: number;
  ai_flavor_score?: number; // AI味评分
  emotional_curve?: {
    start: number;
    middle: number;
    end: number;
  };
  suggestions?: string[];  // 分析建议内容用于辅助推荐
}

interface ChapterRegenerationModalProps {
  visible: boolean;
  onCancel: () => void;
  onSuccess: (newContent: string, wordCount: number) => void;
  chapterId: string;
  projectId: string; // 新增：用于获取写作风格
  chapterTitle: string;
  chapterNumber: number;
  suggestions?: Suggestion[];
  hasAnalysis: boolean;
  analysisScores?: AnalysisScores; // 新增：分析分数用于智能推荐
}


const ChapterRegenerationModal: React.FC<ChapterRegenerationModalProps> = ({
  visible,
  onCancel,
  onSuccess,
  chapterId,
  projectId,
  chapterTitle,
  chapterNumber,
  suggestions = [],
  hasAnalysis,
  analysisScores
}) => {
  const [form] = Form.useForm();
  const { modal, message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<'idle' | 'generating' | 'success' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const [wordCount, setWordCount] = useState(0);
  const [selectedSuggestions, setSelectedSuggestions] = useState<number[]>([]);
  const [modificationSource, setModificationSource] = useState<'custom' | 'analysis_suggestions' | 'mixed'>('custom');

  // 写作风格相关状态
  const [writingStyles, setWritingStyles] = useState<WritingStyle[]>([]);
  const [styleSelectorVisible, setStyleSelectorVisible] = useState(false);

  // "更多"按钮状态
  const [showMoreSuggestions, setShowMoreSuggestions] = useState(false);
  const DEFAULT_VISIBLE_COUNT = 5; // 默认显示条数

  // 根据分析分数智能推荐重点优化方向
  const getRecommendedFocusAreas = (): string[] => {
    if (!analysisScores) return ['emotion', 'dialogue']; // 默认推荐

    const recommendations: { area: string; priority: number; reason: string }[] = [];

    // ========== 1. 分数维度分析（按差距程度排序）==========
    const scores: { name: string; value: number; threshold: number }[] = [
      { name: 'pacing_score', value: analysisScores.pacing_score || 7, threshold: 7 },
      { name: 'engagement_score', value: analysisScores.engagement_score || 7, threshold: 7 },
      { name: 'coherence_score', value: analysisScores.coherence_score || 7, threshold: 7 },
      { name: 'overall_quality_score', value: analysisScores.overall_quality_score || 7, threshold: 7 },
    ];

    // 计算各分数差距并排序
    const scoreGaps = scores.map(s => ({
      name: s.name,
      gap: s.threshold - s.value,
      value: s.value
    })).filter(s => s.gap > 0).sort((a, b) => b.gap - a.gap);

    // 根据分数差距推荐
    for (const score of scoreGaps) {
      const gap = score.gap;
      const priority = gap >= 2 ? 3 : gap >= 1 ? 2 : 1; // 差距越大优先级越高

      if (score.name === 'pacing_score') {
        recommendations.push({ area: 'pacing', priority, reason: `节奏分数${score.value.toFixed(1)}分，差距${gap.toFixed(1)}` });
      } else if (score.name === 'engagement_score') {
        // 吸引力低可能涉及多个维度，根据其他指标辅助判断
        if (analysisScores.emotional_intensity && analysisScores.emotional_intensity < 0.5) {
          recommendations.push({ area: 'emotion', priority, reason: `吸引力分数低且情感强度${(analysisScores.emotional_intensity * 10).toFixed(1)}分` });
        } else if (analysisScores.conflict_level && analysisScores.conflict_level < 5) {
          recommendations.push({ area: 'conflict', priority, reason: `吸引力分数低且冲突强度${analysisScores.conflict_level.toFixed(1)}分` });
        } else {
          recommendations.push({ area: 'emotion', priority, reason: `吸引力分数${score.value.toFixed(1)}分` });
        }
      } else if (score.name === 'coherence_score') {
        // 连贯性低，检查描述比例
        if (analysisScores.description_ratio && analysisScores.description_ratio < 0.15) {
          recommendations.push({ area: 'description', priority: priority + 1, reason: `连贯性低且描写占比仅${(analysisScores.description_ratio * 100).toFixed(1)}%` });
        } else {
          recommendations.push({ area: 'description', priority, reason: `连贯性分数${score.value.toFixed(1)}分` });
        }
      }
    }

    // ========== 2. 情感曲线分析 ==========
    if (analysisScores.emotional_curve) {
      const { start, middle, end } = analysisScores.emotional_curve;
      // 计算情感曲线波动幅度
      const curveRange = Math.max(start, middle, end) - Math.min(start, middle, end);
      // 曲线过于平缓（波动小于0.2）需要增强情感渲染
      if (curveRange < 0.2 && !recommendations.some(r => r.area === 'emotion')) {
        recommendations.push({
          area: 'emotion',
          priority: 2,
          reason: `情感曲线平缓（波动${(curveRange * 10).toFixed(1)}分），需增强起伏`
        });
      }
    }

    // ========== 3. 对话/描写比例分析 ==========
    if (analysisScores.dialogue_ratio !== undefined) {
      // 对话比例过低（<15%）或过高（>60%）都可能需要优化
      const dialoguePercent = analysisScores.dialogue_ratio * 100;
      if (dialoguePercent < 15 && !recommendations.some(r => r.area === 'dialogue')) {
        recommendations.push({
          area: 'dialogue',
          priority: 2,
          reason: `对话占比${dialoguePercent.toFixed(1)}%过低，可增加对话互动`
        });
      } else if (dialoguePercent > 60 && !recommendations.some(r => r.area === 'description')) {
        recommendations.push({
          area: 'description',
          priority: 2,
          reason: `对话占比${dialoguePercent.toFixed(1)}%过高，可增加场景描写`
        });
      }
    }

    if (analysisScores.description_ratio !== undefined) {
      const descPercent = analysisScores.description_ratio * 100;
      if (descPercent < 10 && !recommendations.some(r => r.area === 'description')) {
        recommendations.push({
          area: 'description',
          priority: 2,
          reason: `描写占比${descPercent.toFixed(1)}%过低`
        });
      }
    }

    // ========== 4. 冲突强度分析 ==========
    if (analysisScores.conflict_level !== undefined) {
      if (analysisScores.conflict_level < 4 && !recommendations.some(r => r.area === 'conflict')) {
        recommendations.push({
          area: 'conflict',
          priority: 2,
          reason: `冲突强度${analysisScores.conflict_level.toFixed(1)}分偏弱`
        });
      }
    }

    // ========== 5. 分析建议内容辅助推荐 ==========
    if (analysisScores.suggestions && analysisScores.suggestions.length > 0) {
      const suggestionKeywords: { keyword: string; area: string }[] = [
        { keyword: '节奏', area: 'pacing' },
        { keyword: '情感', area: 'emotion' },
        { keyword: '情绪', area: 'emotion' },
        { keyword: '场景', area: 'description' },
        { keyword: '描写', area: 'description' },
        { keyword: '对话', area: 'dialogue' },
        { keyword: '冲突', area: 'conflict' },
        { keyword: '矛盾', area: 'conflict' },
      ];

      for (const suggestion of analysisScores.suggestions.slice(0, 5)) {
        for (const { keyword, area } of suggestionKeywords) {
          if (suggestion.includes(keyword) && !recommendations.some(r => r.area === area)) {
            recommendations.push({
              area,
              priority: 1,
              reason: `分析建议提及"${keyword}"`
            });
            break;
          }
        }
      }
    }

    // ========== 6. AI味评分分析 ==========
    if (analysisScores.ai_flavor_score !== undefined) {
      if (analysisScores.ai_flavor_score >= 7) {
        // 高AI味推荐对话和场景描写优化
        if (!recommendations.some(r => r.area === 'dialogue')) {
          recommendations.push({
            area: 'dialogue',
            priority: 3,
            reason: `AI味评分${analysisScores.ai_flavor_score.toFixed(1)}分偏高，增加真实对话可降低AI味`
          });
        }
        if (!recommendations.some(r => r.area === 'description')) {
          recommendations.push({
            area: 'description',
            priority: 2,
            reason: `AI味评分高，增加具体感官描写可降低AI味`
          });
        }
      }
    }

    // ========== 7. 综合排序与输出 ==========
    // 按优先级排序，取前3个
    const sortedRecommendations = recommendations
      .sort((a, b) => b.priority - a.priority)
      .slice(0, 3);

    // 如果没有任何推荐，默认推荐情感渲染和对话质量
    if (sortedRecommendations.length === 0) {
      return ['emotion', 'dialogue'];
    }

    console.log('🎯 智能推荐分析:', sortedRecommendations.map(r => `${r.area}(${r.reason})`));

    return sortedRecommendations.map(r => r.area);
  };

  useEffect(() => {
    if (visible) {
      // 重置状态
      setStatus('idle');
      setProgress(0);
      setErrorMessage('');
      setWordCount(0);
      setSelectedSuggestions([]);
      setShowMoreSuggestions(false); // 重置更多按钮状态

      // 如果有分析建议，默认选择混合模式
      if (hasAnalysis && suggestions.length > 0) {
        setModificationSource('mixed');
      } else {
        setModificationSource('custom');
      }

      // 设置默认值
      form.setFieldsValue({
        modification_source: hasAnalysis && suggestions.length > 0 ? 'mixed' : 'custom',
        target_word_count: getCachedWordCount(), // 使用缓存的字数
        preserve_structure: false,
        preserve_character_traits: true,
        focus_areas: getRecommendedFocusAreas() // 智能推荐重点优化方向
      });
    }
  }, [visible, hasAnalysis, suggestions.length, form, analysisScores]);

  // 加载写作风格列表
  useEffect(() => {
    if (visible && projectId) {
      writingStyleApi.getProjectStyles(projectId).then(result => {
        setWritingStyles(result.styles || []);
      }).catch(error => {
        console.warn('获取写作风格失败:', error);
      });
    }
  }, [visible, projectId]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      // 验证至少提供一种修改指令
      if (values.modification_source === 'custom' && !values.custom_instructions?.trim()) {
        message.error('请输入自定义修改要求');
        return;
      }
      
      if (values.modification_source === 'analysis_suggestions' && selectedSuggestions.length === 0) {
        message.error('请选择至少一条分析建议');
        return;
      }
      
      if (values.modification_source === 'mixed' && 
          selectedSuggestions.length === 0 && 
          !values.custom_instructions?.trim()) {
        message.error('请至少选择一条建议或输入自定义要求');
        return;
      }

      setLoading(true);
      setStatus('generating');
      setProgress(0);
      setWordCount(0);

      // 构建请求数据
      interface RegenerationRequest {
        modification_source: string;
        custom_instructions?: string;
        selected_suggestion_indices: number[];
        preserve_elements: {
          preserve_structure: boolean;
          preserve_dialogues: string[];
          preserve_plot_points: string[];
          preserve_character_traits: boolean;
        };
        style_id?: string;
        target_word_count: number;
        focus_areas: string[];
      }

      const requestData: RegenerationRequest = {
        modification_source: values.modification_source,
        custom_instructions: values.custom_instructions,
        selected_suggestion_indices: selectedSuggestions,
        preserve_elements: {
          preserve_structure: values.preserve_structure,
          preserve_dialogues: values.preserve_dialogues || [],
          preserve_plot_points: values.preserve_plot_points || [],
          preserve_character_traits: values.preserve_character_traits
        },
        style_id: values.style_id,
        target_word_count: values.target_word_count,
        focus_areas: values.focus_areas || []
      };

      let accumulatedContent = '';
      let currentWordCount = 0;

      // 使用SSE流式生成
      await ssePost(
        `/api/chapters/${chapterId}/regenerate-stream`,
        requestData,
        {
          onProgress: (_msg: string, prog: number, _status: string, wordCount?: number) => {
            console.log('📊 SSE Progress:', prog, 'word_count:', wordCount);
            // 后端发送的进度消息
            setProgress(prog);
            // 如果后端提供了word_count，使用它；否则使用累积的字数
            if (wordCount !== undefined) {
              setWordCount(wordCount);
              currentWordCount = wordCount;
            }
          },
          onChunk: (content: string) => {
            // 累积内容块
            accumulatedContent += content;
            console.log('📝 SSE Chunk received, total length:', accumulatedContent.length);
            // 仅作为备用字数统计
            currentWordCount = accumulatedContent.length;
            // 不再自己计算进度，完全依赖后端发送的progress消息
          },
          onResult: (data: { word_count?: number }) => {
            // 生成完成，确保使用最新的累积内容
            const finalWordCount = data.word_count || currentWordCount;
            const finalContent = accumulatedContent;

            // 验证：如果没有生成内容，视为失败
            if (!finalContent || finalContent.length === 0) {
              console.error('SSE 生成内容为空');
              setStatus('error');
              setErrorMessage('生成失败：未产生任何内容，请检查 AI 服务是否正常');
              message.error('重新生成失败：未产生任何内容');
              return;
            }

            setProgress(100);
            setStatus('success');
            setWordCount(finalWordCount);
            message.success('重新生成完成！');

            // 延迟调用 onSuccess 打开对比界面
            setTimeout(() => {
              onSuccess(finalContent, finalWordCount);
            }, 500);
          },
          onComplete: () => {
            // SSE完成
          },
          onError: (error: string, code?: number) => {
            console.error('SSE Error:', error, code);
            setStatus('error');
            setErrorMessage(error || '生成失败');
            message.error('重新生成失败: ' + (error || '未知错误'));
          }
        }
      );

    } catch (error: unknown) {
      console.error('提交失败:', error);
      setStatus('error');
      const err = error as Error;
      setErrorMessage(err.message || '提交失败');
      message.error('操作失败: ' + (err.message || '未知错误'));
    } finally {
      setLoading(false);
    }
  };

  const handleSuggestionSelect = (index: number, checked: boolean) => {
    if (checked) {
      setSelectedSuggestions([...selectedSuggestions, index]);
    } else {
      setSelectedSuggestions(selectedSuggestions.filter(i => i !== index));
    }
  };

  const handleCancel = () => {
    if (loading) {
      modal.confirm({
        title: '确认取消',
        content: '生成正在进行中，确定要取消吗？',
        centered: true,
        onOk: () => {
          setLoading(false);
          setStatus('idle');
          onCancel();
        }
      });
    } else {
      onCancel();
    }
  };

  // 插入写作风格提示词
  const handleStyleInsert = (style: WritingStyle) => {
    const currentInstructions = form.getFieldValue('custom_instructions') || '';
    const promptContent = style.prompt_content || '';

    if (!promptContent.trim()) {
      message.warning('该写作风格没有设置提示词内容');
      return;
    }

    // 追加提示词到现有内容
    const newInstructions = currentInstructions.trim()
      ? `${currentInstructions}\n\n【写作风格：${style.name}】\n${promptContent}`
      : `【写作风格：${style.name}】\n${promptContent}`;

    form.setFieldValue('custom_instructions', newInstructions);
    setStyleSelectorVisible(false);
    message.success(`已插入「${style.name}」写作风格`);
  };

  return (
    <Modal
      title={`重新生成章节 - 第${chapterNumber}章：${chapterTitle}`}
      open={visible}
      onCancel={handleCancel}
      width={800}
      centered
      footer={
        status === 'success' ? null : (
          [
            <Button key="cancel" onClick={handleCancel} disabled={loading}>
              取消
            </Button>,
            <Button
              key="submit"
              type="primary"
              onClick={handleSubmit}
              loading={loading}
              icon={<ReloadOutlined />}
            >
              开始重新生成
            </Button>
          ]
        )
      }
    >

      {status === 'success' && (
        <Alert
          message="重新生成成功！"
          description={`共生成 ${wordCount} 字`}
          type="success"
          showIcon
          icon={<CheckCircleOutlined />}
          style={{ marginBottom: 16 }}
        />
      )}

      {status === 'error' && (
        <Alert
          message="生成失败"
          description={errorMessage}
          type="error"
          showIcon
          icon={<CloseCircleOutlined />}
          style={{ marginBottom: 16 }}
        />
      )}

      <Form
        form={form}
        layout="vertical"
        disabled={loading || status === 'success'}
      >
        {/* 修改来源 */}
        <Form.Item
          name="modification_source"
          label="修改来源"
          rules={[{ required: true, message: '请选择修改来源' }]}
        >
          <Radio.Group onChange={(e) => setModificationSource(e.target.value)}>
            <Radio value="custom">仅自定义修改</Radio>
            {hasAnalysis && suggestions.length > 0 && (
              <>
                <Radio value="analysis_suggestions">仅分析建议</Radio>
                <Radio value="mixed">混合模式</Radio>
              </>
            )}
          </Radio.Group>
        </Form.Item>

        {/* 分析建议选择 */}
        {hasAnalysis && suggestions.length > 0 &&
         (modificationSource === 'analysis_suggestions' || modificationSource === 'mixed') && (
          <Form.Item
            label={
              <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                <span>选择分析建议 ({selectedSuggestions.length}/{suggestions.length})</span>
                {suggestions.length > DEFAULT_VISIBLE_COUNT && (
                  <Button
                    type="link"
                    size="small"
                    icon={showMoreSuggestions ? <UpOutlined /> : <DownOutlined />}
                    onClick={() => setShowMoreSuggestions(!showMoreSuggestions)}
                  >
                    {showMoreSuggestions ? '收起' : `更多 (${suggestions.length - DEFAULT_VISIBLE_COUNT}条)`}
                  </Button>
                )}
              </Space>
            }
          >
            <Card size="small" style={{ maxHeight: showMoreSuggestions ? 400 : 300, overflow: 'auto' }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                {(showMoreSuggestions ? suggestions : suggestions.slice(0, DEFAULT_VISIBLE_COUNT)).map((suggestion, displayIndex) => {
                  // 计算原始索引
                  const originalIndex = showMoreSuggestions ? displayIndex : displayIndex;
                  return (
                    <Checkbox
                      key={originalIndex}
                      checked={selectedSuggestions.includes(originalIndex)}
                      onChange={(e) => handleSuggestionSelect(originalIndex, e.target.checked)}
                    >
                      <Space>
                        <Tag color={
                          suggestion.priority === 'high' ? 'red' :
                          suggestion.priority === 'medium' ? 'orange' : 'blue'
                        }>
                          {suggestion.category}
                        </Tag>
                        <span style={{ fontSize: 13 }}>{suggestion.content}</span>
                      </Space>
                    </Checkbox>
                  );
                })}
              </Space>
            </Card>
          </Form.Item>
        )}

        {/* 自定义修改要求 */}
        {(modificationSource === 'custom' || modificationSource === 'mixed') && (
          <Form.Item
            name="custom_instructions"
            label={
              <Space>
                <span>自定义修改要求</span>
                {writingStyles.length > 0 && (
                  <Tooltip title="快速插入写作风格提示词">
                    <Button
                      type="text"
                      size="small"
                      icon={<PlusOutlined />}
                      onClick={() => setStyleSelectorVisible(true)}
                    />
                  </Tooltip>
                )}
              </Space>
            }
            tooltip="描述你希望如何改进这个章节"
          >
            <TextArea
              rows={4}
              placeholder="例如：增强情感渲染，让主角的内心戏更加细腻..."
              showCount
              maxLength={1000}
            />
          </Form.Item>
        )}

        {/* 高级选项 */}
        <Collapse
          ghost
          items={[
            {
              key: 'advanced',
              label: '高级选项',
              children: (
                <>
                  {/* 重点优化方向 */}
                  <Form.Item
                    name="focus_areas"
                    label={<span>重点优化方向 <Tag color="purple" style={{ marginLeft: 4 }}>智能推荐</Tag></span>}
                    tooltip="根据分析分数智能推荐需要优化的方向，分数低于6.5分的维度会自动选中"
                  >
                    <Checkbox.Group>
                      <Space direction="vertical">
                        <Checkbox value="pacing">节奏把控</Checkbox>
                        <Checkbox value="emotion">情感渲染</Checkbox>
                        <Checkbox value="description">场景描写</Checkbox>
                        <Checkbox value="dialogue">对话质量</Checkbox>
                        <Checkbox value="conflict">冲突强度</Checkbox>
                      </Space>
                    </Checkbox.Group>
                  </Form.Item>

                  <Divider />

                  {/* 保留元素 */}
                  <Form.Item label="保留元素">
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Form.Item name="preserve_structure" valuePropName="checked" noStyle>
                        <Checkbox>保留整体结构和情节框架</Checkbox>
                      </Form.Item>
                      <Form.Item name="preserve_character_traits" valuePropName="checked" noStyle>
                        <Checkbox>保持角色性格一致</Checkbox>
                      </Form.Item>
                    </Space>
                  </Form.Item>

                  <Divider />

                  {/* 生成参数 */}
                  <Form.Item
                    name="target_word_count"
                    label="目标字数"
                    tooltip="与章节编辑弹窗同步，修改后自动记住。实际字数可能有±20%的浮动"
                  >
                    <InputNumber
                      min={500}
                      max={10000}
                      step={500}
                      style={{ width: '100%' }}
                      onChange={(value) => {
                        // 同步保存到 localStorage
                        if (value) {
                          localStorage.setItem(WORD_COUNT_CACHE_KEY, String(value));
                        }
                      }}
                    />
                  </Form.Item>
                </>
              )
            }
          ]}
        />
      </Form>

      {/* 使用统一的进度显示组件 */}
      <SSEProgressModal
        visible={status === 'generating'}
        progress={progress}
        message={`正在重新生成中... (已生成 ${wordCount} 字)`}
        title="重新生成章节"
      />

      {/* 写作风格选择弹窗 */}
      <Modal
        title={
          <Space>
            <BookOutlined />
            <span>选择写作风格</span>
          </Space>
        }
        open={styleSelectorVisible}
        onCancel={() => setStyleSelectorVisible(false)}
        footer={null}
        width={500}
        centered
      >
        {writingStyles.length === 0 ? (
          <Empty
            description="暂无写作风格，请先在「写作风格」页面创建"
            style={{ margin: '20px 0' }}
          />
        ) : (
          <List
            dataSource={writingStyles}
            renderItem={(style) => (
              <List.Item
                actions={[
                  <Button
                    type="link"
                    size="small"
                    onClick={() => handleStyleInsert(style)}
                  >
                    插入
                  </Button>
                ]}
              >
                <List.Item.Meta
                  title={style.name}
                  description={style.prompt_content ? (
                    <span style={{ color: '#666', fontSize: 12 }}>
                      {style.prompt_content.length > 100
                        ? `${style.prompt_content.slice(0, 100)}...`
                        : style.prompt_content}
                    </span>
                  ) : (
                    <span style={{ color: '#999' }}>无提示词内容</span>
                  )}
                />
              </List.Item>
            )}
            style={{ maxHeight: 400, overflow: 'auto' }}
          />
        )}
      </Modal>
    </Modal>
  );
};

export default ChapterRegenerationModal;