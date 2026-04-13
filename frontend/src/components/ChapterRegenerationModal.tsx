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
  Radio
} from 'antd';
import {
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined
} from '@ant-design/icons';
import { ssePost } from '../utils/sseClient';
import { SSEProgressModal } from './SSEProgressModal';

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
}

interface ChapterRegenerationModalProps {
  visible: boolean;
  onCancel: () => void;
  onSuccess: (newContent: string, wordCount: number) => void;
  chapterId: string;
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

  // 根据分析分数智能推荐重点优化方向
  const getRecommendedFocusAreas = (): string[] => {
    if (!analysisScores) return ['emotion', 'dialogue']; // 默认推荐

    const recommended: string[] = [];
    const threshold = 6.5; // 分数低于6.5时推荐优化

    // 节奏分数低时推荐节奏把控
    if (analysisScores.pacing_score && analysisScores.pacing_score < threshold) {
      recommended.push('pacing');
    }

    // 吸引力分数低时推荐情感渲染和冲突强度
    if (analysisScores.engagement_score && analysisScores.engagement_score < threshold) {
      recommended.push('emotion');
      if (!recommended.includes('conflict')) {
        recommended.push('conflict');
      }
    }

    // 连贯性分数低时推荐场景描写
    if (analysisScores.coherence_score && analysisScores.coherence_score < threshold) {
      recommended.push('description');
    }

    // 如果没有低分项，但整体分数低，推荐综合优化
    if (recommended.length === 0 && analysisScores.overall_quality_score && analysisScores.overall_quality_score < threshold) {
      recommended.push('pacing', 'emotion');
    }

    // 如果没有任何推荐，默认推荐情感渲染和对话质量
    if (recommended.length === 0) {
      recommended.push('emotion', 'dialogue');
    }

    return recommended;
  };

  useEffect(() => {
    if (visible) {
      // 重置状态
      setStatus('idle');
      setProgress(0);
      setErrorMessage('');
      setWordCount(0);
      setSelectedSuggestions([]);

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
          <Form.Item label={`选择分析建议 (${selectedSuggestions.length}/${suggestions.length})`}>
            <Card size="small" style={{ maxHeight: 300, overflow: 'auto' }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                {suggestions.map((suggestion, index) => (
                  <Checkbox
                    key={index}
                    checked={selectedSuggestions.includes(index)}
                    onChange={(e) => handleSuggestionSelect(index, e.target.checked)}
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
                ))}
              </Space>
            </Card>
          </Form.Item>
        )}

        {/* 自定义修改要求 */}
        {(modificationSource === 'custom' || modificationSource === 'mixed') && (
          <Form.Item
            name="custom_instructions"
            label="自定义修改要求"
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
    </Modal>
  );
};

export default ChapterRegenerationModal;