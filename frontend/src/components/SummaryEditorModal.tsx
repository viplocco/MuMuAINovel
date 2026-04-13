/**章节摘要编辑弹窗组件 */
import { useState, useEffect } from 'react';
import { Modal, Spin, Alert, Input, Button, Space, message, theme, Typography, Descriptions, Divider, Tag } from 'antd';
import { EditOutlined, SyncOutlined, SaveOutlined, FileTextOutlined, InfoCircleOutlined, FileSearchOutlined, FormOutlined } from '@ant-design/icons';
import { summaryApi } from '../services/api';
import type { Chapter } from '../types';

const { TextArea } = Input;
const { Text } = Typography;

// 摘要来源标签配置
const SUMMARY_SOURCE_CONFIG = {
  none: { label: '无摘要', color: 'default', icon: <InfoCircleOutlined /> },
  planning: { label: '规划概要', color: 'orange', icon: <FormOutlined />, desc: '此摘要来自章节规划，是生成前的预期内容概要' },
  analysis: { label: '分析摘要', color: 'green', icon: <FileSearchOutlined />, desc: '此摘要来自AI章节分析，基于已生成的正文内容' },
  manual: { label: '手动输入', color: 'blue', icon: <EditOutlined />, desc: '此摘要是手动编辑输入的' },
};

interface SummaryEditorModalProps {
  projectId: string;
  chapter: Chapter | null;
  visible: boolean;
  onClose: () => void;
  onSummaryUpdated?: () => void;
}

export default function SummaryEditorModal({
  projectId,
  chapter,
  visible,
  onClose,
  onSummaryUpdated
}: SummaryEditorModalProps) {
  const { token } = theme.useToken();
  const [loading, setLoading] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [summary, setSummary] = useState<string>('');
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [summarySource, setSummarySource] = useState<'none' | 'planning' | 'analysis' | 'manual'>('none');
  const [hasContent, setHasContent] = useState(false);

  // 加载摘要
  useEffect(() => {
    if (visible && chapter && projectId) {
      loadSummary();
    }
  }, [visible, chapter, projectId]);

  const loadSummary = async () => {
    if (!chapter) return;

    setLoading(true);
    setError(null);

    try {
      const response = await summaryApi.getChapterSummary(projectId, chapter.id);
      if (response.success) {
        setSummary(response.summary || '');
        setEditContent(response.summary || '');
        setSummarySource(response.summary_source);
        setHasContent(response.has_content);
      } else {
        setError(response.message || '加载摘要失败');
        setSummary('');
        setEditContent('');
        setSummarySource('none');
        setHasContent(false);
      }
    } catch (err) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      setError(axiosError.response?.data?.detail || '加载摘要失败');
      setSummary('');
      setEditContent('');
      setSummarySource('none');
      setHasContent(false);
    } finally {
      setLoading(false);
    }
  };

  // 重新生成摘要
  const handleRegenerate = async () => {
    if (!chapter) return;

    setRegenerating(true);
    setError(null);

    try {
      const response = await summaryApi.regenerateSummary(projectId, chapter.id);
      if (response.success) {
        setSummary(response.summary || '');
        setEditContent(response.summary || '');
        setSummarySource('analysis');  // 重新生成后变成分析摘要
        message.success('摘要已重新生成');
        onSummaryUpdated?.();
      } else {
        setError(response.message || '重新生成失败');
        message.error(response.message || '重新生成失败');
      }
    } catch (err) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      setError(axiosError.response?.data?.detail || '重新生成失败');
      message.error(axiosError.response?.data?.detail || '重新生成失败');
    } finally {
      setRegenerating(false);
    }
  };

  // 保存编辑的摘要
  const handleSave = async () => {
    if (!chapter) return;

    // 验证长度
    if (editContent.length > 500) {
      message.warning('摘要长度不能超过500字');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const response = await summaryApi.updateSummary(projectId, chapter.id, {
        summary: editContent
      });
      if (response.success) {
        setSummary(editContent);
        setIsEditing(false);
        setSummarySource('manual');  // 手动编辑后变成手动输入
        message.success('摘要已保存');
        onSummaryUpdated?.();
      } else {
        setError(response.message || '保存失败');
        message.error(response.message || '保存失败');
      }
    } catch (err) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      setError(axiosError.response?.data?.detail || '保存失败');
      message.error(axiosError.response?.data?.detail || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  // 开始编辑
  const handleStartEdit = () => {
    setEditContent(summary);
    setIsEditing(true);
  };

  // 取消编辑
  const handleCancelEdit = () => {
    setEditContent(summary);
    setIsEditing(false);
  };

  const handleClose = () => {
    setIsEditing(false);
    setError(null);
    onClose();
  };

  if (!chapter) return null;

  return (
    <Modal
      title={
        <Space>
          <FileTextOutlined />
          <span>章节摘要</span>
        </Space>
      }
      open={visible}
      onCancel={handleClose}
      width={600}
      footer={null}
      destroyOnHidden
    >
      <Spin spinning={loading}>
        {/* 章节信息 */}
        <Descriptions column={2} size="small" style={{ marginBottom: 16 }}>
          <Descriptions.Item label="章节">
            第{chapter.chapter_number}章
          </Descriptions.Item>
          <Descriptions.Item label="标题">
            {chapter.title}
          </Descriptions.Item>
          <Descriptions.Item label="字数">
            {chapter.word_count || 0} 字
          </Descriptions.Item>
          <Descriptions.Item label="摘要来源">
            <Tag color={SUMMARY_SOURCE_CONFIG[summarySource].color} icon={SUMMARY_SOURCE_CONFIG[summarySource].icon}>
              {SUMMARY_SOURCE_CONFIG[summarySource].label}
            </Tag>
          </Descriptions.Item>
        </Descriptions>

        {/* 来源说明提示 */}
        {summarySource === 'planning' && (
          <Alert
            type="warning"
            message="此摘要来自章节规划（生成前概要）"
            description={`这是章节生成前设定的预期内容概要，并非基于实际生成的正文。章节生成后，可点击"重新生成"按钮获取基于正文的分析摘要。`}
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        <Divider />

        {/* 错误提示 */}
        {error && (
          <Alert
            type="error"
            message={error}
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        {/* 无摘要提示 */}
        {!loading && !summary && !isEditing && (
          <Alert
            type="info"
            message="该章节尚未生成摘要"
            description={
              hasContent
                ? `章节已有正文内容，请点击"重新生成"按钮通过AI分析生成摘要。`
                : `章节正文尚未生成，请先生成章节内容后再生成摘要。`
            }
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        {/* 摘要显示/编辑区域 */}
        {isEditing ? (
          <div>
            <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between' }}>
              <Text type="secondary">
                编辑摘要（最多500字）
              </Text>
              <Text type="secondary">
                {editContent.length}/500字
              </Text>
            </div>
            <TextArea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              placeholder="请输入章节摘要..."
              rows={8}
              maxLength={500}
              showCount
            />
            <Space style={{ marginTop: 16 }}>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                onClick={handleSave}
                loading={saving}
                disabled={!editContent.trim()}
              >
                保存
              </Button>
              <Button onClick={handleCancelEdit}>
                取消
              </Button>
            </Space>
          </div>
        ) : (
          <div>
            {/* 摘要内容 */}
            {summary && (
              <div style={{
                padding: 12,
                backgroundColor: token.colorBgContainerDisabled,
                borderRadius: 8,
                marginBottom: 16,
                lineHeight: 1.8
              }}>
                <Text>{summary}</Text>
              </div>
            )}

            {/* 操作按钮 */}
            <Space>
              <Button
                type="primary"
                icon={<SyncOutlined />}
                onClick={handleRegenerate}
                loading={regenerating}
                disabled={!chapter.content || chapter.content.trim() === ''}
              >
                重新生成
              </Button>
              <Button
                icon={<EditOutlined />}
                onClick={handleStartEdit}
              >
                编辑
              </Button>
            </Space>

            {/* 提示 */}
            {!chapter.content || chapter.content.trim() === '' ? (
              <Text type="secondary" style={{ marginTop: 16, display: 'block' }}>
                <InfoCircleOutlined style={{ marginRight: 4 }} />
                章节内容为空，无法重新生成摘要
              </Text>
            ) : null}
          </div>
        )}
      </Spin>
    </Modal>
  );
}