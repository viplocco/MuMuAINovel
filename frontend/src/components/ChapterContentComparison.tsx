import React, { useState } from 'react';
import { Modal, Button, Card, Statistic, Row, Col, message, theme } from 'antd';
import { CheckOutlined, CloseOutlined, SwapOutlined } from '@ant-design/icons';
import ReactDiffViewer from 'react-diff-viewer-continued';

interface ChapterContentComparisonProps {
  visible: boolean;
  onClose: () => void;
  chapterId: string;
  chapterTitle: string;
  originalContent: string;
  newContent: string;
  wordCount: number;
  onApply: () => void;
  onDiscard: () => void;
}

const ChapterContentComparison: React.FC<ChapterContentComparisonProps> = ({
  visible,
  onClose,
  chapterId,
  chapterTitle,
  originalContent,
  newContent,
  wordCount,
  onApply,
  onDiscard
}) => {
  const { token } = theme.useToken();
  const [applying, setApplying] = useState(false);
  const [viewMode, setViewMode] = useState<'split' | 'unified'>('split');
  const [modal, contextHolder] = Modal.useModal();

  // 检测是否为暗色主题
  const isDarkTheme = token.colorBgContainer === token.colorBgElevated ||
    token.colorBgContainer.toLowerCase().includes('1') ||
    token.colorText.startsWith('#fff') ||
    token.colorText.startsWith('rgba(255');

  // 判断背景色亮度
  const isLightColor = (color: string) => {
    const hex = color.replace('#', '');
    if (hex.length === 3) {
      const r = parseInt(hex[0] + hex[0], 16);
      const g = parseInt(hex[1] + hex[1], 16);
      const b = parseInt(hex[2] + hex[2], 16);
      return (r * 299 + g * 587 + b * 114) / 1000 > 128;
    }
    if (hex.length === 6) {
      const r = parseInt(hex.slice(0, 2), 16);
      const g = parseInt(hex.slice(2, 4), 16);
      const b = parseInt(hex.slice(4, 6), 16);
      return (r * 299 + g * 587 + b * 114) / 1000 > 128;
    }
    return true;
  };

  const isDark = !isLightColor(token.colorBgContainer);

  const originalWordCount = originalContent.length;
  const wordCountDiff = wordCount - originalWordCount;
  const wordCountDiffPercent = ((wordCountDiff / originalWordCount) * 100).toFixed(1);

  const handleApply = async () => {
    setApplying(true);
    try {
      const response = await fetch(`/api/chapters/${chapterId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content: newContent
        })
      });

      if (!response.ok) {
        throw new Error('应用新内容失败');
      }

      message.success('新内容已应用！');

      // 先调用 onApply 通知父组件刷新
      onApply();

      // 延迟触发章节分析，给父组件时间刷新
      setTimeout(async () => {
        try {
          const analysisResponse = await fetch(`/api/chapters/${chapterId}/analyze`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            }
          });

          if (analysisResponse.ok) {
            message.success('章节分析已开始，请稍后查看结果');
          } else {
            message.warning('章节分析触发失败，您可以手动触发分析');
          }
        } catch (analysisError) {
          console.error('触发分析失败:', analysisError);
          message.warning('章节分析触发失败，您可以手动触发分析');
        }
      }, 500);

      onClose();
    } catch (error: unknown) {
      const err = error as Error;
      message.error(err.message || '应用失败');
    } finally {
      setApplying(false);
    }
  };

  const handleDiscard = () => {
    modal.confirm({
      title: '确认放弃',
      content: '确定要放弃新生成的内容吗？此操作不可恢复。',
      centered: true,
      okText: '确定放弃',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: () => {
        onDiscard();
        onClose();
        message.info('已放弃新内容');
      }
    });
  };

  return (
    <>
      {contextHolder}
      <Modal
      title={`内容对比 - ${chapterTitle}`}
      open={visible}
      onCancel={onClose}
      width="95%"
      centered
      style={{ maxWidth: 1600 }}
      footer={[
        <Button
          key="discard"
          danger
          icon={<CloseOutlined />}
          onClick={handleDiscard}
        >
          放弃新内容
        </Button>,
        <Button
          key="toggle"
          icon={<SwapOutlined />}
          onClick={() => setViewMode(viewMode === 'split' ? 'unified' : 'split')}
        >
          切换视图
        </Button>,
        <Button
          key="apply"
          type="primary"
          icon={<CheckOutlined />}
          loading={applying}
          onClick={handleApply}
        >
          应用新内容
        </Button>
      ]}
    >
      {/* 统计信息 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col span={6}>
            <Statistic
              title="原内容字数"
              value={originalWordCount}
              suffix="字"
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="新内容字数"
              value={wordCount}
              suffix="字"
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="字数变化"
              value={wordCountDiff}
              suffix="字"
              valueStyle={{ color: wordCountDiff > 0 ? token.colorSuccess : token.colorError }}
              prefix={wordCountDiff > 0 ? '+' : ''}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="变化比例"
              value={wordCountDiffPercent}
              suffix="%"
              valueStyle={{ color: Math.abs(parseFloat(wordCountDiffPercent)) < 10 ? token.colorPrimary : token.colorWarning }}
              prefix={wordCountDiff > 0 ? '+' : ''}
            />
          </Col>
        </Row>
      </Card>

      {/* 内容对比 */}
      <div style={{
        maxHeight: 'calc(90vh - 300px)',
        overflow: 'auto',
        border: `1px solid ${token.colorBorder}`,
        borderRadius: token.borderRadius
      }}>
        <ReactDiffViewer
          oldValue={originalContent}
          newValue={newContent}
          splitView={viewMode === 'split'}
          leftTitle="原内容"
          rightTitle="新内容"
          showDiffOnly={false}
          useDarkTheme={isDark}
          styles={{
            variables: {
              light: {
                diffViewerBackground: token.colorBgContainer,
                addedBackground: token.colorSuccessBg,
                addedColor: token.colorText,
                removedBackground: token.colorErrorBg,
                removedColor: token.colorText,
                wordAddedBackground: token.colorSuccessBorder,
                wordRemovedBackground: token.colorErrorBorder,
                addedGutterBackground: token.colorSuccessBg,
                removedGutterBackground: token.colorErrorBg,
                gutterBackground: token.colorBgLayout,
                gutterBackgroundDark: token.colorBgContainer,
                highlightBackground: token.colorWarningBg,
                highlightGutterBackground: token.colorWarningBorder,
              },
              dark: {
                diffViewerBackground: token.colorBgContainer,
                addedBackground: token.colorSuccessBg,
                addedColor: token.colorText,
                removedBackground: token.colorErrorBg,
                removedColor: token.colorText,
                wordAddedBackground: token.colorSuccessBorder,
                wordRemovedBackground: token.colorErrorBorder,
                addedGutterBackground: token.colorSuccessBg,
                removedGutterBackground: token.colorErrorBg,
                gutterBackground: token.colorBgElevated,
                gutterBackgroundDark: token.colorBgContainer,
                highlightBackground: token.colorWarningBg,
                highlightGutterBackground: token.colorWarningBorder,
              },
            },
            line: {
              padding: '10px 2px',
              fontSize: '14px',
              lineHeight: '20px',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word'
            }
          }}
        />
      </div>
      </Modal>
    </>
  );
};

export default ChapterContentComparison;