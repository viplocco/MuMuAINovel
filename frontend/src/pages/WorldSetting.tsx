import { Card, Descriptions, Empty, Typography, Button, Modal, Form, Input, App, Flex, InputNumber, Select, theme, Collapse, Tabs, Divider } from 'antd';
import { GlobalOutlined, EditOutlined, SyncOutlined, FormOutlined, TeamOutlined, ThunderboltOutlined, CompassOutlined, ClockCircleOutlined, EnvironmentOutlined, SmileOutlined, BookOutlined, BulbOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { useState } from 'react';
import { useStore } from '../store';
import { worldSettingCardStyles } from '../components/CardStyles';
import { projectApi, wizardStreamApi } from '../services/api';
import { SSELoadingOverlay } from '../components/SSELoadingOverlay';
import DynamicArrayEditor from '../components/DynamicArrayEditor';
import type { WorldSettingV3Data } from '../types';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const { Title, Paragraph } = Typography;
const { TextArea } = Input;

// ==================== Markdown 渲染组件 ====================

// 章节图标映射
const sectionIcons: Record<string, React.ReactNode> = {
  '世界观设定': <GlobalOutlined />,
  '基本信息': <InfoCircleOutlined />,
  '物理维度': <ThunderboltOutlined />,
  '社会维度': <TeamOutlined />,
  '隐喻维度': <BulbOutlined />,
  '交互维度': <SyncOutlined />,
  '世界概述': <BookOutlined />,
  '空间架构': <CompassOutlined />,
  '时间架构': <ClockCircleOutlined />,
  '力量体系': <ThunderboltOutlined />,
  '物品体系': <CompassOutlined />,
  '权力结构': <TeamOutlined />,
  '经济体系': <TeamOutlined />,
  '文化体系': <TeamOutlined />,
  '组织体系': <TeamOutlined />,
  '时间背景': <ClockCircleOutlined />,
  '地理环境': <EnvironmentOutlined />,
  '氛围基调': <SmileOutlined />,
  '世界法则': <ThunderboltOutlined />,
};

// 章节编号映射
const sectionNumbers: Record<string, string> = {
  '世界观设定': '',
  '基本信息': '一、',
  '物理维度': '二、',
  '空间架构': '2.1',
  '时间架构': '2.2',
  '力量体系': '2.3',
  '物品体系': '2.4',
  '社会维度': '三、',
  '权力结构': '3.1',
  '经济体系': '3.2',
  '文化体系': '3.3',
  '组织体系': '3.4',
  '隐喻维度': '四、',
  '交互维度': '五、',
  '世界概述': '六、',
  '时间背景': '6.1',
  '地理环境': '6.2',
  '氛围基调': '6.3',
  '世界法则': '6.4',
};

// Markdown 标题渲染组件
const MarkdownTitle: React.FC<{ level: number; children: React.ReactNode }> = ({ level, children }) => {
  const text = String(children);
  const cleanText = text.replace(/^[#\s]+/, '').trim();
  const icon = sectionIcons[cleanText];
  const number = sectionNumbers[cleanText];

  const style: React.CSSProperties = {
    margin: level === 1 ? '0 0 16px 0' : level === 2 ? '16px 0 12px 0' : '12px 0 8px 0',
    color: 'var(--color-text-primary)',
    fontWeight: level === 1 ? 700 : level === 2 ? 600 : 500,
    fontSize: level === 1 ? 20 : level === 2 ? 18 : level === 3 ? 16 : 14,
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  };

  if (level === 1) {
    return (
      <>
        <Title level={4} style={style}>
          {icon} {cleanText}
        </Title>
        <Divider style={{ margin: '0 0 16px 0' }} />
      </>
    );
  }

  return (
    <div style={style}>
      {icon && <span style={{ color: 'var(--color-primary)' }}>{icon}</span>}
      {number && <span style={{ color: 'var(--color-primary)', fontWeight: 600 }}>{number}</span>}
      <span>{cleanText}</span>
    </div>
  );
};

// Markdown 段落渲染组件
const MarkdownParagraph: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <Paragraph style={{ margin: '0 0 12px 0', lineHeight: 1.6 }}>
    {children}
  </Paragraph>
);

// Markdown 列表渲染组件
const MarkdownList: React.FC<{ children: React.ReactNode; ordered?: boolean }> = ({ children }) => (
  <div style={{
    margin: '0 0 12px 0',
    paddingLeft: 20,
    lineHeight: 1.6,
  }}>
    {children}
  </div>
);

// Markdown 列表项渲染组件
const MarkdownListItem: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ margin: '4px 0', position: 'relative' }}>
    <span style={{ position: 'absolute', left: -16, color: 'var(--color-primary)' }}>•</span>
    {children}
  </div>
);

// Markdown 表格渲染组件
const MarkdownTable: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{
    margin: '16px 0',
    overflowX: 'auto',
    border: '1px solid var(--color-border)',
    borderRadius: 8,
  }}>
    <table style={{
      width: '100%',
      borderCollapse: 'collapse',
      fontSize: 13,
    }}>
      {children}
    </table>
  </div>
);

// Markdown 表格行渲染组件
const MarkdownTableRow: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <tr style={{
    borderBottom: '1px solid var(--color-border)',
  }}>
    {children}
  </tr>
);

// Markdown 表格头渲染组件
const MarkdownTableHead: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <thead style={{
    background: 'var(--color-primary-bg)',
  }}>
    {children}
  </thead>
);

// Markdown 表格体渲染组件
const MarkdownTableBody: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <tbody>
    {children}
  </tbody>
);

// Markdown 表格单元格渲染组件
const MarkdownTableCell: React.FC<{ children: React.ReactNode; isHeader?: boolean }> = ({ children, isHeader }) => (
  <td style={{
    padding: '10px 14px',
    borderBottom: isHeader ? '2px solid var(--color-primary)' : '1px solid var(--color-border)',
    borderLeft: '1px solid var(--color-border)',
    borderRight: '1px solid var(--color-border)',
    textAlign: 'left',
    fontWeight: isHeader ? 600 : 400,
    whiteSpace: 'normal',
    wordBreak: 'break-word',
    lineHeight: 1.5,
    color: isHeader ? 'var(--color-text-primary)' : 'inherit',
  }}>
    {children}
  </td>
);

// Markdown 代码渲染组件
const MarkdownCode: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <code style={{
    background: 'var(--color-bg-layout)',
    padding: '2px 6px',
    borderRadius: 4,
    fontFamily: 'ui-monospace, monospace',
    fontSize: 13,
  }}>
    {children}
  </code>
);

// Markdown 引用块渲染组件
const MarkdownBlockquote: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{
    margin: '12px 0',
    padding: '8px 16px',
    borderLeft: '4px solid var(--color-primary)',
    background: 'var(--color-bg-layout)',
    borderRadius: '0 8px 8px 0',
  }}>
    {children}
  </div>
);

// 世界设定 Markdown 渲染器组件
const WorldSettingMarkdownRenderer: React.FC<{ content: string }> = ({ content }) => {
  // 预处理内容：修复表格格式问题
  const fixTableFormat = (text: string): string => {
    let result = text;
    // 将压缩的表格行展开
    result = result.replace(/\|\s+\|/g, '|\n|');
    // 在表格开始前添加空行
    result = result.replace(/([^\n|])\n(\|[^\n])/g, '$1\n\n$2');
    // 在表格结束后添加空行
    result = result.replace(/(\|[^\n]*\|)\n([^\n|])/g, '$1\n\n$2');
    // 清理多余换行
    result = result.replace(/\n{3,}/g, '\n\n');
    return result;
  };

  const processedContent = fixTableFormat(content);

  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: ({ children }) => <MarkdownTitle level={1}>{children}</MarkdownTitle>,
        h2: ({ children }) => <MarkdownTitle level={2}>{children}</MarkdownTitle>,
        h3: ({ children }) => <MarkdownTitle level={3}>{children}</MarkdownTitle>,
        h4: ({ children }) => <MarkdownTitle level={4}>{children}</MarkdownTitle>,
        p: ({ children }) => <MarkdownParagraph>{children}</MarkdownParagraph>,
        ul: ({ children }) => <MarkdownList>{children}</MarkdownList>,
        ol: ({ children }) => <MarkdownList ordered>{children}</MarkdownList>,
        li: ({ children }) => <MarkdownListItem>{children}</MarkdownListItem>,
        table: ({ children }) => <MarkdownTable>{children}</MarkdownTable>,
        thead: ({ children }) => <MarkdownTableHead>{children}</MarkdownTableHead>,
        tbody: ({ children }) => <MarkdownTableBody>{children}</MarkdownTableBody>,
        tr: ({ children }) => <MarkdownTableRow>{children}</MarkdownTableRow>,
        th: ({ children }) => <MarkdownTableCell isHeader>{children}</MarkdownTableCell>,
        td: ({ children }) => <MarkdownTableCell>{children}</MarkdownTableCell>,
        code: ({ children }) => <MarkdownCode>{children}</MarkdownCode>,
        blockquote: ({ children }) => <MarkdownBlockquote>{children}</MarkdownBlockquote>,
      }}
    >
      {processedContent || '未设定'}
    </ReactMarkdown>
  );
};

// ==================== 世界设定页面组件 ====================

// 判断是否有隐喻维度数据
const hasMetaphorData = (data: WorldSettingV3Data): boolean => {
  const metaphor = data.metaphor;
  if (!metaphor) return false;

  // 检查是否是完整结构（有 core_philosophies）
  const hasCorePhilosophies = metaphor.core_philosophies && metaphor.core_philosophies.length > 0;

  // 检查是否是兼容结构（philosophy 是数组）
  const hasLegacyPhilosophy = Array.isArray(metaphor.philosophy) && metaphor.philosophy.length > 0;

  return !!(
    metaphor.themes?.core_theme ||
    (metaphor.symbols?.visual && metaphor.symbols.visual.length > 0) ||
    (metaphor.symbols?.colors && metaphor.symbols.colors.length > 0) ||
    (metaphor.symbols?.animal_symbols && metaphor.symbols.animal_symbols.length > 0) ||
    (metaphor.symbols?.nature_symbols && metaphor.symbols.nature_symbols.length > 0) ||
    (metaphor.themes?.theme_mappings && metaphor.themes.theme_mappings.length > 0) ||
    hasCorePhilosophies ||
    hasLegacyPhilosophy
  );
};

// 判断是否有交互维度数据
const hasInteractionData = (data: WorldSettingV3Data): boolean => {
  return !!(
    data.interaction?.cross_rules?.physical_social ||
    data.interaction?.cross_rules?.social_metaphor ||
    data.interaction?.cross_rules?.metaphor_physical ||
    data.interaction?.evolution?.time_driven ||
    data.interaction?.evolution?.event_driven ||
    data.interaction?.evolution?.character_driven ||
    (data.interaction?.evolution?.faction_evolution && data.interaction.evolution.faction_evolution.length > 0) ||
    (data.interaction?.evolution?.resource_evolution && data.interaction.evolution.resource_evolution.length > 0) ||
    (data.interaction?.disruption_points && data.interaction.disruption_points.length > 0) ||
    (data.interaction?.disruption_consequences && data.interaction.disruption_consequences.length > 0) ||
    (data.interaction?.repair_mechanisms && data.interaction.repair_mechanisms.length > 0)
  );
};

export default function WorldSetting() {
  const { currentProject, setCurrentProject } = useStore();
  const { message, modal: appModal } = App.useApp();
  const [isEditModalVisible, setIsEditModalVisible] = useState(false);
  const [editForm] = Form.useForm();
  const [isSaving, setIsSaving] = useState(false);
  const [isEditProjectModalVisible, setIsEditProjectModalVisible] = useState(false);
  const [editProjectForm] = Form.useForm();
  const [isSavingProject, setIsSavingProject] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [regenerateProgress, setRegenerateProgress] = useState(0);
  const [regenerateMessage, setRegenerateMessage] = useState('');
  const [isPreviewModalVisible, setIsPreviewModalVisible] = useState(false);
  const [newWorldData, setNewWorldData] = useState<{
    time_period: string;
    location: string;
    atmosphere: string;
    rules: string;
    world_setting_data?: string;  // JSON格式数据（向后兼容）
    world_setting_markdown?: string;  // Markdown格式数据
    world_setting_format?: 'json' | 'markdown';  // 数据格式标识
  } | null>(null);
  const [isSavingPreview, setIsSavingPreview] = useState(false);
  // Markdown编辑器状态
  const [isMarkdownEditModalVisible, setIsMarkdownEditModalVisible] = useState(false);
  const [editMarkdownContent, setEditMarkdownContent] = useState('');
  const { token } = theme.useToken();

  // 检查项目是否使用Markdown格式
  const isMarkdownFormat = currentProject?.world_setting_format === 'markdown' && currentProject?.world_setting_markdown;

  // AI重新生成世界观
  const handleRegenerate = async () => {
    if (!currentProject) return;

    appModal.confirm({
      title: '确认重新生成',
      content: '确定要使用AI重新生成世界观设定吗？这将替换当前的世界观内容。',
      centered: true,
      okText: '确认重新生成',
      cancelText: '取消',
      onOk: async () => {
        setIsRegenerating(true);
        setRegenerateProgress(0);
        setRegenerateMessage('准备重新生成世界观...');

        try {
          await wizardStreamApi.regenerateWorldBuildingStream(
            currentProject.id,
            {},
            {
              onProgress: (msg: string, progress: number) => {
                setRegenerateProgress(progress);
                setRegenerateMessage(msg);
              },
              onChunk: (chunk: string) => {
                // 可以在这里显示生成的内容片段（可选）
                console.log('生成片段:', chunk);
              },
              onResult: (result: { time_period: string; location: string; atmosphere: string; rules: string; world_setting_data?: string; world_setting_markdown?: string; world_setting_format?: 'json' | 'markdown' }) => {
                // 保存新生成的数据（包含Markdown或JSON格式数据）
                const newData = {
                  time_period: result.time_period,
                  location: result.location,
                  atmosphere: result.atmosphere,
                  rules: result.rules,
                  world_setting_data: result.world_setting_data,
                  world_setting_markdown: result.world_setting_markdown,
                  world_setting_format: result.world_setting_format || 'json',
                };
                setNewWorldData(newData);
              },
              onError: (errorMsg: string) => {
                console.error('重新生成失败:', errorMsg);
                message.error(errorMsg || '重新生成失败，请重试');
              },
              onComplete: () => {
                setIsRegenerating(false);
                setRegenerateProgress(0);
                setRegenerateMessage('');
                // 显示预览对话框
                setIsPreviewModalVisible(true);
              }
            }
          );
        } catch (error) {
          console.error('重新生成出错:', error);
          message.error('重新生成出错，请重试');
          setIsRegenerating(false);
          setRegenerateProgress(0);
          setRegenerateMessage('');
        }
      }
    });
  };

  // 确认保存重新生成的内容
  const handleConfirmSave = async () => {
    if (!currentProject || !newWorldData) return;

    setIsSavingPreview(true);
    try {
      const updatedProject = await projectApi.updateProject(currentProject.id, {
        world_time_period: newWorldData.time_period,
        world_location: newWorldData.location,
        world_atmosphere: newWorldData.atmosphere,
        world_rules: newWorldData.rules,
        world_setting_data: newWorldData.world_setting_data,
        world_setting_markdown: newWorldData.world_setting_markdown,
        world_setting_format: newWorldData.world_setting_format || 'json',
      });

      setCurrentProject(updatedProject);
      message.success('世界观已更新！');
      setIsPreviewModalVisible(false);
      setNewWorldData(null);
    } catch (error) {
      console.error('保存失败:', error);
      message.error('保存失败，请重试');
    } finally {
      setIsSavingPreview(false);
    }
  };

  // 取消保存，关闭预览
  const handleCancelSave = () => {
    setIsPreviewModalVisible(false);
    setNewWorldData(null);
    message.info('已取消，保持原有内容');
  };

  if (!currentProject) return null;

  // 检查是否有世界设定信息（兼容新旧格式）
  const hasWorldSetting = currentProject.world_setting_markdown ||
    currentProject.world_setting_data ||
    currentProject.world_time_period ||
    currentProject.world_location ||
    currentProject.world_atmosphere ||
    currentProject.world_rules;

  // 解析结构化数据（如果存在且是JSON格式）
  let worldSettingData: any = null;
  // 优先检查Markdown格式
  if (isMarkdownFormat) {
    // Markdown格式不需要解析JSON
    worldSettingData = null;
  } else if (currentProject.world_setting_data) {
    try {
      worldSettingData = JSON.parse(currentProject.world_setting_data);
    } catch (e) {
      console.error('解析世界设定数据失败:', e);
    }
  }

  if (!hasWorldSetting) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        {/* 固定头部 */}
        <div style={{
          position: 'sticky',
          top: 0,
          zIndex: 10,
          backgroundColor: token.colorBgContainer,
          padding: '16px 0',
          marginBottom: 16,
          borderBottom: `1px solid ${token.colorBorderSecondary}`,
          display: 'flex',
          alignItems: 'center'
        }}>
          <GlobalOutlined style={{ fontSize: 24, marginRight: 12, color: token.colorPrimary }} />
          <h2 style={{ margin: 0 }}>世界设定</h2>
        </div>

        {/* 可滚动内容区域 */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          <Empty
            description="暂无世界设定信息"
            style={{ marginTop: 60 }}
          >
            <Paragraph type="secondary">
              世界设定信息在创建项目向导中生成，用于构建小说的世界观背景。
            </Paragraph>
          </Empty>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* 固定头部 */}
      <div style={{
        position: 'sticky',
        top: 0,
        zIndex: 10,
        backgroundColor: token.colorBgContainer,
        padding: '16px 0',
        marginBottom: 24,
        borderBottom: `1px solid ${token.colorBorderSecondary}`
      }}>
        <Flex
          justify="space-between"
          align="flex-start"
          gap={12}
          wrap="wrap"
        >
          <div style={{ display: 'flex', alignItems: 'center', minWidth: 'fit-content' }}>
            <GlobalOutlined style={{ fontSize: 24, marginRight: 12, color: token.colorPrimary }} />
            <h2 style={{ margin: 0, whiteSpace: 'nowrap' }}>世界设定</h2>
          </div>
          <Flex gap={8} wrap="wrap" style={{ flex: '0 1 auto' }}>
            <Button
              icon={<SyncOutlined />}
              onClick={handleRegenerate}
              disabled={isRegenerating}
              style={{
                minWidth: 'fit-content',
                flex: '1 1 auto'
              }}
            >
              <span className="button-text-mobile">AI重新生成</span>
            </Button>
            <Button
              type="primary"
              icon={<FormOutlined />}
              onClick={() => {
                editProjectForm.setFieldsValue({
                  title: currentProject.title || '',
                  description: currentProject.description || '',
                  theme: currentProject.theme || '',
                  genre: currentProject.genre || '',
                  narrative_perspective: currentProject.narrative_perspective || '',
                  target_words: currentProject.target_words || 0,
                });
                setIsEditProjectModalVisible(true);
              }}
              style={{
                minWidth: 'fit-content',
                flex: '1 1 auto'
              }}
            >
              <span className="button-text-mobile">编辑基础信息</span>
            </Button>
            <Button
              type="primary"
              icon={<EditOutlined />}
              onClick={() => {
                setEditMarkdownContent(currentProject?.world_setting_markdown || '');
                setIsMarkdownEditModalVisible(true);
              }}
              style={{
                minWidth: 'fit-content',
                flex: '1 1 auto'
              }}
            >
              <span className="button-text-mobile">编辑世界观</span>
            </Button>
          </Flex>
        </Flex>
      </div>

      {/* 可滚动内容区域 */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        <Card
          style={{
            ...worldSettingCardStyles.sectionCard,
            marginBottom: 16
          }}
          title={
            <span style={{ fontSize: 18, fontWeight: 500 }}>
              基础信息
            </span>
          }
        >
          <Descriptions bordered column={1} styles={{ label: { width: 120, fontWeight: 500 } }}>
            <Descriptions.Item label="小说名称">{currentProject.title}</Descriptions.Item>
            {currentProject.description && (
              <Descriptions.Item label="小说简介">{currentProject.description}</Descriptions.Item>
            )}
            <Descriptions.Item label="小说主题">{currentProject.theme || '未设定'}</Descriptions.Item>
            <Descriptions.Item label="小说类型">{currentProject.genre || '未设定'}</Descriptions.Item>
            <Descriptions.Item label="叙事视角">{currentProject.narrative_perspective || '未设定'}</Descriptions.Item>
            <Descriptions.Item label="目标字数">
              {currentProject.target_words ? `${currentProject.target_words.toLocaleString()} 字` : '未设定'}
            </Descriptions.Item>
          </Descriptions>
        </Card>

        <Card
          style={{
            ...worldSettingCardStyles.sectionCard,
            marginBottom: 16
          }}
          title={
            <span style={{ fontSize: 18, fontWeight: 500 }}>
              <GlobalOutlined style={{ marginRight: 8 }} />
              小说世界观
            </span>
          }
        >
          <div style={{ padding: '16px 0' }}>
            {/* Markdown格式显示 */}
            {isMarkdownFormat ? (
              <div
                className="markdown-content"
                style={{
                  padding: 16,
                  background: token.colorBgContainer,
                  borderRadius: 8,
                  border: `1px solid ${token.colorBorder}`,
                }}
              >
                <WorldSettingMarkdownRenderer content={currentProject?.world_setting_markdown || ''} />
              </div>
            ) : worldSettingData ? (
              // JSON格式：分层展示（向后兼容）
              <Collapse
                defaultActiveKey={worldSettingData.version === 2 ? ['physical', 'social', 'legacy'] : ['core', 'summary']}
                items={
                  worldSettingData.version === 2
                    ? [
                        // V3 四维度展示
                        {
                          key: 'physical',
                          label: <span style={{ fontWeight: 500 }}>🌍 物理维度</span>,
                          children: (
                            <div>
                              {/* 空间架构 */}
                              {worldSettingData.physical?.space?.key_locations?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>关键地点</Title>
                                  {worldSettingData.physical.space.key_locations.map((loc: any, idx: number) => (
                                    <Card key={idx} size="small" style={{ marginBottom: 8 }}>
                                      <Descriptions column={2} size="small">
                                        <Descriptions.Item label="名称">{loc.name}</Descriptions.Item>
                                        <Descriptions.Item label="类型">{loc.type}</Descriptions.Item>
                                      </Descriptions>
                                      <Paragraph style={{ marginTop: 8, fontSize: 13 }}>{loc.brief}</Paragraph>
                                    </Card>
                                  ))}
                                </div>
                              )}
                              {/* 空间节点 */}
                              {worldSettingData.physical?.space?.space_nodes?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>空间节点</Title>
                                  {worldSettingData.physical.space.space_nodes.map((node: any, idx: number) => (
                                    <Card key={idx} size="small" style={{ marginBottom: 8 }}>
                                      <Descriptions column={2} size="small">
                                        <Descriptions.Item label="名称">{node.name}</Descriptions.Item>
                                        <Descriptions.Item label="类型">{node.type}</Descriptions.Item>
                                        <Descriptions.Item label="所属区域">{node.location}</Descriptions.Item>
                                      </Descriptions>
                                      {node.properties?.length > 0 && <Paragraph style={{ marginTop: 8, fontSize: 13 }}>特性：{node.properties.join('、')}</Paragraph>}
                                    </Card>
                                  ))}
                                </div>
                              )}
                              {/* 空间通道 */}
                              {worldSettingData.physical?.space?.space_channels?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>空间通道</Title>
                                  {worldSettingData.physical.space.space_channels.map((channel: any, idx: number) => (
                                    <Card key={idx} size="small" style={{ marginBottom: 8 }}>
                                      <Descriptions column={2} size="small">
                                        <Descriptions.Item label="名称">{channel.name}</Descriptions.Item>
                                        <Descriptions.Item label="类型">{channel.type}</Descriptions.Item>
                                        <Descriptions.Item label="起点">{channel.source}</Descriptions.Item>
                                        <Descriptions.Item label="终点">{channel.destination}</Descriptions.Item>
                                      </Descriptions>
                                      {channel.conditions && <Paragraph style={{ marginTop: 8, fontSize: 13 }}>使用条件：{channel.conditions}</Paragraph>}
                                    </Card>
                                  ))}
                                </div>
                              )}
                              {/* 空间特性 */}
                              {worldSettingData.physical?.space?.space_features?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>空间特性</Title>
                                  {worldSettingData.physical.space.space_features.map((feature: any, idx: number) => (
                                    <Card key={idx} size="small" style={{ marginBottom: 8 }}>
                                      <Descriptions column={2} size="small">
                                        <Descriptions.Item label="名称">{feature.name}</Descriptions.Item>
                                        <Descriptions.Item label="类型">{feature.type}</Descriptions.Item>
                                      </Descriptions>
                                      <Paragraph style={{ marginTop: 8, fontSize: 13 }}>影响：{feature.effect}</Paragraph>
                                    </Card>
                                  ))}
                                </div>
                              )}
                              {/* 移动规则 */}
                              {worldSettingData.physical?.space?.movement_rules && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>移动规则</Title>
                                  <Paragraph style={{ fontSize: 14 }}>{worldSettingData.physical.space.movement_rules}</Paragraph>
                                </div>
                              )}
                              {/* 时代背景 */}
                              {worldSettingData.physical?.time?.current_period && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>时代背景</Title>
                                  <Paragraph style={{ fontSize: 14, lineHeight: 1.8, background: token.colorBgLayout, padding: 12, borderRadius: 8 }}>
                                    {worldSettingData.physical.time.current_period}
                                  </Paragraph>
                                </div>
                              )}
                              {/* 历史纪元 */}
                              {worldSettingData.physical?.time?.history_epochs?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>历史纪元</Title>
                                  {worldSettingData.physical.time.history_epochs.map((epoch: any, idx: number) => (
                                    <Card key={idx} size="small" style={{ marginBottom: 8 }}>
                                      <Descriptions column={2} size="small">
                                        <Descriptions.Item label="纪元">{epoch.name}</Descriptions.Item>
                                        <Descriptions.Item label="时间跨度">{epoch.period}</Descriptions.Item>
                                      </Descriptions>
                                      {epoch.major_events?.length > 0 && <Paragraph style={{ marginTop: 8, fontSize: 13 }}>主要事件：{epoch.major_events.join('、')}</Paragraph>}
                                      <Paragraph style={{ fontSize: 13 }}>影响：{epoch.impact}</Paragraph>
                                    </Card>
                                  ))}
                                </div>
                              )}
                              {/* 关键事件年表 */}
                              {worldSettingData.physical?.time?.history_events?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>关键事件年表</Title>
                                  {worldSettingData.physical.time.history_events.map((event: any, idx: number) => (
                                    <Card key={idx} size="small" style={{ marginBottom: 8 }}>
                                      <Descriptions column={2} size="small">
                                        <Descriptions.Item label="年份">{event.year}</Descriptions.Item>
                                        <Descriptions.Item label="事件">{event.event_name}</Descriptions.Item>
                                        <Descriptions.Item label="所属纪元">{event.epoch}</Descriptions.Item>
                                      </Descriptions>
                                      <Paragraph style={{ marginTop: 8, fontSize: 13 }}>{event.description}</Paragraph>
                                    </Card>
                                  ))}
                                </div>
                              )}
                              {/* 时间节点 */}
                              {worldSettingData.physical?.time?.time_nodes?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>时间节点</Title>
                                  {worldSettingData.physical.time.time_nodes.map((node: any, idx: number) => (
                                    <Card key={idx} size="small" style={{ marginBottom: 8 }}>
                                      <Descriptions column={2} size="small">
                                        <Descriptions.Item label="节点">{node.name}</Descriptions.Item>
                                        <Descriptions.Item label="纪元">{node.epoch}</Descriptions.Item>
                                      </Descriptions>
                                      {node.event && <Paragraph style={{ marginTop: 8, fontSize: 13 }}>关联事件：{node.event}</Paragraph>}
                                    </Card>
                                  ))}
                                </div>
                              )}
                              {/* 时间流速 */}
                              {worldSettingData.physical?.time?.timeflow && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>时间流速</Title>
                                  <Paragraph style={{ fontSize: 14 }}>{worldSettingData.physical.time.timeflow}</Paragraph>
                                </div>
                              )}
                              {/* 力量体系 */}
                              {worldSettingData.physical?.power?.system_name && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>力量体系</Title>
                                  <Descriptions bordered column={1} size="small" style={{ marginBottom: 8 }}>
                                    <Descriptions.Item label="体系名称">{worldSettingData.physical.power.system_name}</Descriptions.Item>
                                    {worldSettingData.physical.power.levels?.length > 0 && (
                                      <Descriptions.Item label="等级划分">{worldSettingData.physical.power.levels.join(' → ')}</Descriptions.Item>
                                    )}
                                    {worldSettingData.physical.power.cultivation_method && (
                                      <Descriptions.Item label="获取方式">{worldSettingData.physical.power.cultivation_method}</Descriptions.Item>
                                    )}
                                    {worldSettingData.physical.power.limitations && (
                                      <Descriptions.Item label="限制">{worldSettingData.physical.power.limitations}</Descriptions.Item>
                                    )}
                                  </Descriptions>
                                </div>
                              )}
                              {/* 能力分支 */}
                              {worldSettingData.physical?.power?.ability_branches?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>能力分支</Title>
                                  {worldSettingData.physical.power.ability_branches.map((branch: any, idx: number) => (
                                    <Card key={idx} size="small" style={{ marginBottom: 8 }}>
                                      <Descriptions column={1} size="small">
                                        <Descriptions.Item label="名称">{branch.name}</Descriptions.Item>
                                      </Descriptions>
                                      <Paragraph style={{ marginTop: 8, fontSize: 13 }}>{branch.description}</Paragraph>
                                      {branch.key_skills?.length > 0 && <Paragraph style={{ fontSize: 13 }}>核心技能：{branch.key_skills.join('、')}</Paragraph>}
                                      {branch.advantages?.length > 0 && <Paragraph style={{ fontSize: 13 }}>优势：{branch.advantages.join('、')}</Paragraph>}
                                    </Card>
                                  ))}
                                </div>
                              )}
                              {/* 力量来源 */}
                              {worldSettingData.physical?.power?.power_sources?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>力量来源</Title>
                                  {worldSettingData.physical.power.power_sources.map((source: any, idx: number) => (
                                    <Card key={idx} size="small" style={{ marginBottom: 8 }}>
                                      <Descriptions column={2} size="small">
                                        <Descriptions.Item label="名称">{source.name}</Descriptions.Item>
                                        <Descriptions.Item label="类型">{source.type}</Descriptions.Item>
                                      </Descriptions>
                                      <Paragraph style={{ marginTop: 8, fontSize: 13 }}>获取方式：{source.acquisition}</Paragraph>
                                    </Card>
                                  ))}
                                </div>
                              )}
                              {/* 等级晋升规则 */}
                              {worldSettingData.physical?.power?.level_advances?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>等级晋升规则</Title>
                                  {worldSettingData.physical.power.level_advances.map((advance: any, idx: number) => (
                                    <Card key={idx} size="small" style={{ marginBottom: 8 }}>
                                      <Descriptions column={1} size="small">
                                        <Descriptions.Item label="等级">{advance.level_name}</Descriptions.Item>
                                      </Descriptions>
                                      <Paragraph style={{ marginTop: 8, fontSize: 13 }}>晋升条件：{advance.requirements}</Paragraph>
                                      {advance.risks && <Paragraph style={{ fontSize: 13 }}>风险：{advance.risks}</Paragraph>}
                                    </Card>
                                  ))}
                                </div>
                              )}
                              {/* 物品体系 */}
                              {worldSettingData.physical?.items?.equipment_system && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>装备体系</Title>
                                  <Descriptions bordered column={1} size="small">
                                    {worldSettingData.physical.items.equipment_system.tiers?.length > 0 && (
                                      <Descriptions.Item label="品阶等级">{worldSettingData.physical.items.equipment_system.tiers.join(' → ')}</Descriptions.Item>
                                    )}
                                    {worldSettingData.physical.items.equipment_system.crafting_rules && (
                                      <Descriptions.Item label="制作规则">{worldSettingData.physical.items.equipment_system.crafting_rules}</Descriptions.Item>
                                    )}
                                  </Descriptions>
                                  {worldSettingData.physical.items.equipment_system.famous_items?.length > 0 && (
                                    <div style={{ marginTop: 8 }}>
                                      {worldSettingData.physical.items.equipment_system.famous_items.map((item: any, idx: number) => (
                                        <Paragraph key={idx} style={{ fontSize: 13 }}>• {item.name} ({item.rarity || '未知品阶'}): {item.effect}</Paragraph>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              )}
                              {/* 消耗品体系 */}
                              {worldSettingData.physical?.items?.consumable_system && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>消耗品体系</Title>
                                  <Descriptions bordered column={1} size="small">
                                    {worldSettingData.physical.items.consumable_system.tiers?.length > 0 && (
                                      <Descriptions.Item label="品阶等级">{worldSettingData.physical.items.consumable_system.tiers.join(' → ')}</Descriptions.Item>
                                    )}
                                  </Descriptions>
                                </div>
                              )}
                              {/* 工具体系 */}
                              {worldSettingData.physical?.items?.tool_system && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>工具体系</Title>
                                  <Paragraph style={{ fontSize: 14 }}>{worldSettingData.physical.items.tool_system.crafting_rules || '暂无详细描述'}</Paragraph>
                                </div>
                              )}
                              {/* 结构体系 */}
                              {worldSettingData.physical?.items?.structure_system && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>结构体系</Title>
                                  <Paragraph style={{ fontSize: 14 }}>{worldSettingData.physical.items.structure_system.crafting_rules || '暂无详细描述'}</Paragraph>
                                </div>
                              )}
                              {/* 生物体系 */}
                              {worldSettingData.physical?.items?.creature_system && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>生物体系</Title>
                                  <Paragraph style={{ fontSize: 14 }}>{worldSettingData.physical.items.creature_system.crafting_rules || '暂无详细描述'}</Paragraph>
                                </div>
                              )}
                              {/* 稀有物品 */}
                              {worldSettingData.physical?.items?.rare_items?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>稀有物品</Title>
                                  <Paragraph style={{ fontSize: 14 }}>{worldSettingData.physical.items.rare_items.join('、')}</Paragraph>
                                </div>
                              )}
                              {/* 兜底：当物理维度所有内容块都没有数据时显示提示 */}
                              {!worldSettingData.physical?.space?.key_locations?.length &&
                               !worldSettingData.physical?.space?.space_nodes?.length &&
                               !worldSettingData.physical?.time?.current_period &&
                               !worldSettingData.physical?.power?.system_name &&
                               !worldSettingData.physical?.items?.rare_items?.length &&
                                <Empty description="暂无物理维度数据" style={{ padding: 20 }} />}
                            </div>
                          ),
                        },
                        {
                          key: 'social',
                          label: <span style={{ fontWeight: 500 }}>🏛️ 社会维度</span>,
                          children: (
                            <div>
                              {/* 权力结构 */}
                              {worldSettingData.social?.power_structure?.hierarchy_rule && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>等级制度</Title>
                                  <Paragraph style={{ fontSize: 14, lineHeight: 1.8, background: token.colorBgLayout, padding: 12, borderRadius: 8 }}>
                                    {worldSettingData.social.power_structure.hierarchy_rule}
                                  </Paragraph>
                                </div>
                              )}
                              {/* 主要势力 */}
                              {worldSettingData.social?.power_structure?.key_organizations?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>主要势力</Title>
                                  {worldSettingData.social.power_structure.key_organizations.map((org: any, idx: number) => (
                                    <Card key={idx} size="small" style={{ marginBottom: 8 }}>
                                      <Descriptions column={2} size="small">
                                        <Descriptions.Item label="名称">{org.name}</Descriptions.Item>
                                        <Descriptions.Item label="类型">{org.type}</Descriptions.Item>
                                        {org.power_level && <Descriptions.Item label="势力等级">{org.power_level}</Descriptions.Item>}
                                      </Descriptions>
                                      <Paragraph style={{ marginTop: 8, fontSize: 13 }}>{org.brief}</Paragraph>
                                    </Card>
                                  ))}
                                </div>
                              )}
                              {/* 阵营分类 */}
                              {worldSettingData.social?.power_structure?.faction_classification?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>阵营分类</Title>
                                  {worldSettingData.social.power_structure.faction_classification.map((faction: any, idx: number) => (
                                    <Card key={idx} size="small" style={{ marginBottom: 8 }}>
                                      <Descriptions column={1} size="small">
                                        <Descriptions.Item label="类别">{faction.category}</Descriptions.Item>
                                      </Descriptions>
                                      <Paragraph style={{ marginTop: 8, fontSize: 13 }}>{faction.characteristics}</Paragraph>
                                    </Card>
                                  ))}
                                </div>
                              )}
                              {/* 权力断层线 */}
                              {worldSettingData.social?.power_structure?.power_fault_lines?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>权力断层线</Title>
                                  {worldSettingData.social.power_structure.power_fault_lines.map((line: any, idx: number) => (
                                    <Card key={idx} size="small" style={{ marginBottom: 8 }}>
                                      <Descriptions column={2} size="small">
                                        <Descriptions.Item label="名称">{line.name}</Descriptions.Item>
                                        <Descriptions.Item label="类型">{line.type}</Descriptions.Item>
                                        <Descriptions.Item label="强度">{line.intensity}</Descriptions.Item>
                                      </Descriptions>
                                      {line.consequences && <Paragraph style={{ marginTop: 8, fontSize: 13 }}>后果：{line.consequences}</Paragraph>}
                                    </Card>
                                  ))}
                                </div>
                              )}
                              {/* 权力制衡 */}
                              {worldSettingData.social?.power_structure?.power_balance?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>权力制衡</Title>
                                  {worldSettingData.social.power_structure.power_balance.map((balance: any, idx: number) => (
                                    <Card key={idx} size="small" style={{ marginBottom: 8 }}>
                                      <Descriptions column={2} size="small">
                                        <Descriptions.Item label="机制">{balance.mechanism_name}</Descriptions.Item>
                                        <Descriptions.Item label="类型">{balance.type}</Descriptions.Item>
                                      </Descriptions>
                                      {balance.effectiveness && <Paragraph style={{ marginTop: 8, fontSize: 13 }}>有效性：{balance.effectiveness}</Paragraph>}
                                    </Card>
                                  ))}
                                </div>
                              )}
                              {/* 冲突规则 */}
                              {worldSettingData.social?.power_structure?.conflict_rules && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>冲突规则</Title>
                                  <Paragraph style={{ fontSize: 14 }}>{worldSettingData.social.power_structure.conflict_rules}</Paragraph>
                                </div>
                              )}
                              {/* 经济体系 */}
                              {worldSettingData.social?.economy?.currency_system?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>货币体系</Title>
                                  <Paragraph style={{ fontSize: 14 }}>{worldSettingData.social.economy.currency_system.join(' → ')}</Paragraph>
                                </div>
                              )}
                              {/* 资源分布 */}
                              {worldSettingData.social?.economy?.resource_distribution && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>资源分布</Title>
                                  <Paragraph style={{ fontSize: 14 }}>{worldSettingData.social.economy.resource_distribution}</Paragraph>
                                </div>
                              )}
                              {/* 贸易网络 */}
                              {worldSettingData.social?.economy?.trade_networks?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>贸易网络</Title>
                                  {worldSettingData.social.economy.trade_networks.map((trade: any, idx: number) => (
                                    <Card key={idx} size="small" style={{ marginBottom: 8 }}>
                                      <Descriptions column={2} size="small">
                                        <Descriptions.Item label="名称">{trade.name}</Descriptions.Item>
                                        <Descriptions.Item label="类型">{trade.type}</Descriptions.Item>
                                      </Descriptions>
                                      {trade.main_goods?.length > 0 && <Paragraph style={{ marginTop: 8, fontSize: 13 }}>主要商品：{trade.main_goods.join('、')}</Paragraph>}
                                    </Card>
                                  ))}
                                </div>
                              )}
                              {/* 经济命脉 */}
                              {worldSettingData.social?.economy?.economic_lifelines?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>经济命脉</Title>
                                  {worldSettingData.social.economy.economic_lifelines.map((lifeline: any, idx: number) => (
                                    <Card key={idx} size="small" style={{ marginBottom: 8 }}>
                                      <Descriptions column={2} size="small">
                                        <Descriptions.Item label="名称">{lifeline.name}</Descriptions.Item>
                                        <Descriptions.Item label="类型">{lifeline.type}</Descriptions.Item>
                                      </Descriptions>
                                      {lifeline.importance && <Paragraph style={{ marginTop: 8, fontSize: 13 }}>重要程度：{lifeline.importance}</Paragraph>}
                                    </Card>
                                  ))}
                                </div>
                              )}
                              {/* 贸易规则 */}
                              {worldSettingData.social?.economy?.trade_rules && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>贸易规则</Title>
                                  <Paragraph style={{ fontSize: 14 }}>{worldSettingData.social.economy.trade_rules}</Paragraph>
                                </div>
                              )}
                              {/* 核心文化 */}
                              {worldSettingData.social?.culture?.core_culture?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>核心文化</Title>
                                  {worldSettingData.social.culture.core_culture.map((culture: any, idx: number) => (
                                    <Card key={idx} size="small" style={{ marginBottom: 8 }}>
                                      <Descriptions column={2} size="small">
                                        <Descriptions.Item label="名称">{culture.name}</Descriptions.Item>
                                        <Descriptions.Item label="类型">{culture.type}</Descriptions.Item>
                                      </Descriptions>
                                      <Paragraph style={{ marginTop: 8, fontSize: 13 }}>{culture.description}</Paragraph>
                                    </Card>
                                  ))}
                                </div>
                              )}
                              {/* 宗教信仰 */}
                              {worldSettingData.social?.culture?.religious_beliefs?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>宗教信仰</Title>
                                  {worldSettingData.social.culture.religious_beliefs.map((belief: any, idx: number) => (
                                    <Card key={idx} size="small" style={{ marginBottom: 8 }}>
                                      <Descriptions column={2} size="small">
                                        <Descriptions.Item label="信仰">{belief.name}</Descriptions.Item>
                                        <Descriptions.Item label="类型">{belief.type}</Descriptions.Item>
                                      </Descriptions>
                                      {belief.core_beliefs?.length > 0 && <Paragraph style={{ marginTop: 8, fontSize: 13 }}>核心教义：{belief.core_beliefs.join('、')}</Paragraph>}
                                    </Card>
                                  ))}
                                </div>
                              )}
                              {/* 文化传承 */}
                              {worldSettingData.social?.culture?.cultural_heritage?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>文化传承</Title>
                                  {worldSettingData.social.culture.cultural_heritage.map((heritage: any, idx: number) => (
                                    <Card key={idx} size="small" style={{ marginBottom: 8 }}>
                                      <Descriptions column={2} size="small">
                                        <Descriptions.Item label="传承">{heritage.name}</Descriptions.Item>
                                        <Descriptions.Item label="起源">{heritage.origin}</Descriptions.Item>
                                      </Descriptions>
                                      <Paragraph style={{ marginTop: 8, fontSize: 13 }}>现状：{heritage.current_status}</Paragraph>
                                    </Card>
                                  ))}
                                </div>
                              )}
                              {/* 语言风格 */}
                              {worldSettingData.social?.culture?.language_style && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>语言风格</Title>
                                  <Paragraph style={{ fontSize: 14 }}>{worldSettingData.social.culture.language_style}</Paragraph>
                                </div>
                              )}
                              {/* 文化设定 */}
                              {worldSettingData.social?.culture?.values?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>核心价值观</Title>
                                  <Paragraph style={{ fontSize: 14 }}>{worldSettingData.social.culture.values.join('、')}</Paragraph>
                                </div>
                              )}
                              {/* 禁忌设定 */}
                              {worldSettingData.social?.culture?.taboos?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>社会禁忌</Title>
                                  <Paragraph style={{ fontSize: 14, color: token.colorError }}>{worldSettingData.social.culture.taboos.join('、')}</Paragraph>
                                </div>
                              )}
                              {/* 阵营势力 */}
                              {(worldSettingData.social?.organizations?.protagonist_factions?.length > 0 ||
                                worldSettingData.social?.organizations?.antagonist_factions?.length > 0 ||
                                worldSettingData.social?.organizations?.neutral_factions?.length > 0 ||
                                worldSettingData.social?.organizations?.special_factions?.length > 0) && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>阵营势力</Title>
                                  {worldSettingData.social.organizations.protagonist_factions?.length > 0 && (
                                    <div style={{ marginBottom: 8 }}>
                                      <Paragraph style={{ fontSize: 14, fontWeight: 500 }}>主角阵营</Paragraph>
                                      {worldSettingData.social.organizations.protagonist_factions.map((faction: any, idx: number) => (
                                        <Card key={idx} size="small" style={{ marginBottom: 4 }}>
                                          <Descriptions column={2} size="small">
                                            <Descriptions.Item label="名称">{faction.name}</Descriptions.Item>
                                            <Descriptions.Item label="类型">{faction.type}</Descriptions.Item>
                                          </Descriptions>
                                          <Paragraph style={{ marginTop: 8, fontSize: 13 }}>{faction.brief}</Paragraph>
                                        </Card>
                                      ))}
                                    </div>
                                  )}
                                  {worldSettingData.social.organizations.antagonist_factions?.length > 0 && (
                                    <div style={{ marginBottom: 8 }}>
                                      <Paragraph style={{ fontSize: 14, fontWeight: 500, color: token.colorError }}>反派阵营</Paragraph>
                                      {worldSettingData.social.organizations.antagonist_factions.map((faction: any, idx: number) => (
                                        <Card key={idx} size="small" style={{ marginBottom: 4 }}>
                                          <Descriptions column={2} size="small">
                                            <Descriptions.Item label="名称">{faction.name}</Descriptions.Item>
                                            <Descriptions.Item label="类型">{faction.type}</Descriptions.Item>
                                          </Descriptions>
                                          <Paragraph style={{ marginTop: 8, fontSize: 13 }}>{faction.brief}</Paragraph>
                                        </Card>
                                      ))}
                                    </div>
                                  )}
                                  {worldSettingData.social.organizations.neutral_factions?.length > 0 && (
                                    <div style={{ marginBottom: 8 }}>
                                      <Paragraph style={{ fontSize: 14, fontWeight: 500, color: token.colorTextSecondary }}>中立阵营</Paragraph>
                                      {worldSettingData.social.organizations.neutral_factions.map((faction: any, idx: number) => (
                                        <Card key={idx} size="small" style={{ marginBottom: 4 }}>
                                          <Descriptions column={2} size="small">
                                            <Descriptions.Item label="名称">{faction.name}</Descriptions.Item>
                                            <Descriptions.Item label="类型">{faction.type}</Descriptions.Item>
                                          </Descriptions>
                                          <Paragraph style={{ marginTop: 8, fontSize: 13 }}>{faction.brief}</Paragraph>
                                        </Card>
                                      ))}
                                    </div>
                                  )}
                                  {worldSettingData.social.organizations.special_factions?.length > 0 && (
                                    <div>
                                      <Paragraph style={{ fontSize: 14, fontWeight: 500, color: token.colorWarning }}>特殊阵营</Paragraph>
                                      {worldSettingData.social.organizations.special_factions.map((faction: any, idx: number) => (
                                        <Card key={idx} size="small" style={{ marginBottom: 4 }}>
                                          <Descriptions column={2} size="small">
                                            <Descriptions.Item label="名称">{faction.name}</Descriptions.Item>
                                            <Descriptions.Item label="类型">{faction.type}</Descriptions.Item>
                                          </Descriptions>
                                          <Paragraph style={{ marginTop: 8, fontSize: 13 }}>{faction.brief}</Paragraph>
                                        </Card>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              )}
                              {/* 传统习俗 */}
                              {worldSettingData.social?.culture?.traditions?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>传统习俗</Title>
                                  <Paragraph style={{ fontSize: 14 }}>{worldSettingData.social.culture.traditions.join('、')}</Paragraph>
                                </div>
                              )}
                              {/* 组织关系 */}
                              {worldSettingData.social?.relations?.organization_relations?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>组织关系</Title>
                                  {worldSettingData.social.relations.organization_relations.map((relation: any, idx: number) => (
                                    <Card key={idx} size="small" style={{ marginBottom: 8 }}>
                                      <Descriptions column={2} size="small">
                                        <Descriptions.Item label="组织A">{relation.org_a || relation.from}</Descriptions.Item>
                                        <Descriptions.Item label="组织B">{relation.org_b || relation.to}</Descriptions.Item>
                                      </Descriptions>
                                      <Paragraph style={{ marginTop: 8, fontSize: 13 }}>{relation.type || relation.relation_type}：{relation.description}</Paragraph>
                                    </Card>
                                  ))}
                                </div>
                              )}
                              {/* 人际规则 */}
                              {worldSettingData.social?.relations?.inter_personal_rules && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>人际规则</Title>
                                  <Paragraph style={{ fontSize: 14 }}>{worldSettingData.social.relations.inter_personal_rules}</Paragraph>
                                </div>
                              )}
                              {/* 兜底：当社会维度所有内容块都没有数据时显示提示 */}
                              {!worldSettingData.social?.power_structure?.hierarchy_rule &&
                               !worldSettingData.social?.power_structure?.key_organizations?.length &&
                               !worldSettingData.social?.economy?.currency_system?.length &&
                               !worldSettingData.social?.culture?.values?.length &&
                               !worldSettingData.social?.organizations?.protagonist_factions?.length &&
                                <Empty description="暂无社会维度数据" style={{ padding: 20 }} />}
                            </div>
                          ),
                        },
                        // 隐喻维度（如果有有效数据）
                        ...(hasMetaphorData(worldSettingData) ? [{
                          key: 'metaphor',
                          label: <span style={{ fontWeight: 500 }}>🎭 隐喻维度</span>,
                          children: (
                            <div>
                              {/* 核心主题 */}
                              {worldSettingData.metaphor?.themes?.core_theme && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>核心主题</Title>
                                  <Paragraph style={{ fontSize: 14, lineHeight: 1.8, background: token.colorBgLayout, padding: 12, borderRadius: 8 }}>
                                    {worldSettingData.metaphor.themes.core_theme}
                                  </Paragraph>
                                </div>
                              )}
                              {/* 子主题 */}
                              {worldSettingData.metaphor?.themes?.sub_themes?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>子主题</Title>
                                  <Paragraph style={{ fontSize: 14 }}>{worldSettingData.metaphor.themes.sub_themes.join('、')}</Paragraph>
                                </div>
                              )}
                              {/* 主题演化 */}
                              {worldSettingData.metaphor?.themes?.theme_evolution && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>主题演化</Title>
                                  <Paragraph style={{ fontSize: 14 }}>{worldSettingData.metaphor.themes.theme_evolution}</Paragraph>
                                </div>
                              )}
                              {/* 主题映射 */}
                              {worldSettingData.metaphor?.themes?.theme_mappings?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>主题映射</Title>
                                  {worldSettingData.metaphor.themes.theme_mappings.map((mapping: any, idx: number) => (
                                    <Card key={idx} size="small" style={{ marginBottom: 8 }}>
                                      <Descriptions column={1} size="small">
                                        <Descriptions.Item label="映射类型">{mapping.mapping_type}</Descriptions.Item>
                                      </Descriptions>
                                      <Paragraph style={{ marginTop: 8, fontSize: 13 }}>物理体现：{mapping.physical_manifestation}</Paragraph>
                                      <Paragraph style={{ fontSize: 13 }}>隐喻含义：{mapping.metaphor_meaning}</Paragraph>
                                    </Card>
                                  ))}
                                </div>
                              )}
                              {/* 视觉象征 */}
                              {worldSettingData.metaphor?.symbols?.visual?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>视觉象征</Title>
                                  <Paragraph style={{ fontSize: 14 }}>{worldSettingData.metaphor.symbols.visual.join('、')}</Paragraph>
                                </div>
                              )}
                              {/* 颜色象征 */}
                              {worldSettingData.metaphor?.symbols?.colors?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>颜色象征</Title>
                                  <Paragraph style={{ fontSize: 14 }}>{worldSettingData.metaphor.symbols.colors.join('、')}</Paragraph>
                                </div>
                              )}
                              {/* 动物符号 */}
                              {worldSettingData.metaphor?.symbols?.animal_symbols?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>动物符号</Title>
                                  {worldSettingData.metaphor.symbols.animal_symbols.map((symbol: any, idx: number) => (
                                    <Card key={idx} size="small" style={{ marginBottom: 8 }}>
                                      <Descriptions column={2} size="small">
                                        <Descriptions.Item label="动物">{symbol.animal}</Descriptions.Item>
                                        <Descriptions.Item label="象征">{symbol.symbolism}</Descriptions.Item>
                                      </Descriptions>
                                      {symbol.usage_context && <Paragraph style={{ marginTop: 8, fontSize: 13 }}>使用场景：{symbol.usage_context}</Paragraph>}
                                    </Card>
                                  ))}
                                </div>
                              )}
                              {/* 自然符号 */}
                              {worldSettingData.metaphor?.symbols?.nature_symbols?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>自然符号</Title>
                                  {worldSettingData.metaphor.symbols.nature_symbols.map((symbol: any, idx: number) => (
                                    <Card key={idx} size="small" style={{ marginBottom: 8 }}>
                                      <Descriptions column={2} size="small">
                                        <Descriptions.Item label="元素">{symbol.element}</Descriptions.Item>
                                        <Descriptions.Item label="象征">{symbol.symbolism}</Descriptions.Item>
                                      </Descriptions>
                                      {symbol.manifestation && <Paragraph style={{ marginTop: 8, fontSize: 13 }}>体现：{symbol.manifestation}</Paragraph>}
                                    </Card>
                                  ))}
                                </div>
                              )}
                              {/* 物品象征 */}
                              {worldSettingData.metaphor?.symbols?.objects?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>物品象征</Title>
                                  <Paragraph style={{ fontSize: 14 }}>{worldSettingData.metaphor.symbols.objects.join('、')}</Paragraph>
                                </div>
                              )}
                              {/* 哲学内核 */}
                              {worldSettingData.metaphor?.core_philosophies?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>哲学内核</Title>
                                  {worldSettingData.metaphor.core_philosophies.map((phil: any, idx: number) => (
                                    <Card key={idx} size="small" style={{ marginBottom: 8 }}>
                                      <Descriptions column={1} size="small">
                                        <Descriptions.Item label="哲学">{phil.philosophy_name}</Descriptions.Item>
                                      </Descriptions>
                                      <Paragraph style={{ marginTop: 8, fontSize: 13 }}>核心概念：{phil.core_concept}</Paragraph>
                                      {phil.world_manifestation && <Paragraph style={{ fontSize: 13 }}>世界观体现：{phil.world_manifestation}</Paragraph>}
                                    </Card>
                                  ))}
                                </div>
                              )}
                              {/* 哲学观念（兼容旧格式） */}
                              {worldSettingData.metaphor?.philosophy?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>哲学观念</Title>
                                  {worldSettingData.metaphor.philosophy.map((phil: any, idx: number) => (
                                    <Card key={idx} size="small" style={{ marginBottom: 8 }}>
                                      <Descriptions column={2} size="small">
                                        <Descriptions.Item label="观念">{phil.name}</Descriptions.Item>
                                        {phil.school && <Descriptions.Item label="流派">{phil.school}</Descriptions.Item>}
                                      </Descriptions>
                                      {phil.influence && <Paragraph style={{ marginTop: 8, fontSize: 13 }}>影响：{phil.influence}</Paragraph>}
                                    </Card>
                                  ))}
                                </div>
                              )}
                            </div>
                          ),
                        }] : []),
                        // 交互维度（如果有有效数据）
                        ...(hasInteractionData(worldSettingData) ? [{
                          key: 'interaction',
                          label: <span style={{ fontWeight: 500 }}>🔗 交互维度</span>,
                          children: (
                            <div>
                              {/* 维度交叉规则 */}
                              {(worldSettingData.interaction?.cross_rules?.physical_social ||
                                worldSettingData.interaction?.cross_rules?.social_metaphor ||
                                worldSettingData.interaction?.cross_rules?.metaphor_physical) && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>维度交叉规则</Title>
                                  <Descriptions bordered column={1} size="small">
                                    {worldSettingData.interaction.cross_rules.physical_social && (
                                      <Descriptions.Item label="物理与社会">{worldSettingData.interaction.cross_rules.physical_social}</Descriptions.Item>
                                    )}
                                    {worldSettingData.interaction.cross_rules.social_metaphor && (
                                      <Descriptions.Item label="社会与隐喻">{worldSettingData.interaction.cross_rules.social_metaphor}</Descriptions.Item>
                                    )}
                                    {worldSettingData.interaction.cross_rules.metaphor_physical && (
                                      <Descriptions.Item label="隐喻与物理">{worldSettingData.interaction.cross_rules.metaphor_physical}</Descriptions.Item>
                                    )}
                                  </Descriptions>
                                </div>
                              )}
                              {/* 演化机制 */}
                              {(worldSettingData.interaction?.evolution?.time_driven ||
                                worldSettingData.interaction?.evolution?.event_driven ||
                                worldSettingData.interaction?.evolution?.character_driven) && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>演化机制</Title>
                                  <Descriptions bordered column={1} size="small">
                                    {worldSettingData.interaction.evolution.time_driven && (
                                      <Descriptions.Item label="时间驱动">{worldSettingData.interaction.evolution.time_driven}</Descriptions.Item>
                                    )}
                                    {worldSettingData.interaction.evolution.event_driven && (
                                      <Descriptions.Item label="事件驱动">{worldSettingData.interaction.evolution.event_driven}</Descriptions.Item>
                                    )}
                                    {worldSettingData.interaction.evolution.character_driven && (
                                      <Descriptions.Item label="角色驱动">{worldSettingData.interaction.evolution.character_driven}</Descriptions.Item>
                                    )}
                                  </Descriptions>
                                </div>
                              )}
                              {/* 势力演化 */}
                              {worldSettingData.interaction?.evolution?.faction_evolution?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>势力演化</Title>
                                  {worldSettingData.interaction.evolution.faction_evolution.map((evolution: any, idx: number) => (
                                    <Card key={idx} size="small" style={{ marginBottom: 8 }}>
                                      <Descriptions column={2} size="small">
                                        <Descriptions.Item label="势力">{evolution.faction_name}</Descriptions.Item>
                                        <Descriptions.Item label="类型">{evolution.evolution_type}</Descriptions.Item>
                                      </Descriptions>
                                      <Paragraph style={{ marginTop: 8, fontSize: 13 }}>触发原因：{evolution.trigger}</Paragraph>
                                      <Paragraph style={{ fontSize: 13 }}>当前状态：{evolution.current_state}</Paragraph>
                                    </Card>
                                  ))}
                                </div>
                              )}
                              {/* 资源演化 */}
                              {worldSettingData.interaction?.evolution?.resource_evolution?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>资源演化</Title>
                                  {worldSettingData.interaction.evolution.resource_evolution.map((evolution: any, idx: number) => (
                                    <Card key={idx} size="small" style={{ marginBottom: 8 }}>
                                      <Descriptions column={2} size="small">
                                        <Descriptions.Item label="资源">{evolution.resource_name}</Descriptions.Item>
                                        <Descriptions.Item label="类型">{evolution.evolution_type}</Descriptions.Item>
                                      </Descriptions>
                                      <Paragraph style={{ marginTop: 8, fontSize: 13 }}>原因：{evolution.cause}</Paragraph>
                                      <Paragraph style={{ fontSize: 13 }}>影响：{evolution.impact}</Paragraph>
                                    </Card>
                                  ))}
                                </div>
                              )}
                              {/* 可打破的规则点 */}
                              {worldSettingData.interaction?.disruption_points?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>可打破的规则点</Title>
                                  <Paragraph style={{ fontSize: 14 }}>{worldSettingData.interaction.disruption_points.join('、')}</Paragraph>
                                </div>
                              )}
                              {/* 破坏后果 */}
                              {worldSettingData.interaction?.disruption_consequences?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>破坏后果</Title>
                                  {worldSettingData.interaction.disruption_consequences.map((consequence: any, idx: number) => (
                                    <Card key={idx} size="small" style={{ marginBottom: 8 }}>
                                      <Descriptions column={1} size="small">
                                        <Descriptions.Item label="类型">{consequence.disruption_type}</Descriptions.Item>
                                      </Descriptions>
                                      <Paragraph style={{ marginTop: 8, fontSize: 13 }}>直接后果：{consequence.immediate_effect}</Paragraph>
                                      {consequence.long_term_effect && <Paragraph style={{ fontSize: 13 }}>长期影响：{consequence.long_term_effect}</Paragraph>}
                                    </Card>
                                  ))}
                                </div>
                              )}
                              {/* 规则修复机制 */}
                              {worldSettingData.interaction?.repair_mechanisms?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>规则修复机制</Title>
                                  <Paragraph style={{ fontSize: 14 }}>{worldSettingData.interaction.repair_mechanisms.join('、')}</Paragraph>
                                </div>
                              )}
                            </div>
                          ),
                        }] : []),
                        {
                          key: 'legacy',
                          label: <span style={{ fontWeight: 500 }}>📝 详细描述（概述）</span>,
                          children: (
                            <div>
                              {/* 世界观概述 */}
                              {worldSettingData.meta && (
                                <Card size="small" style={{ marginBottom: 24, background: token.colorBgContainer }}>
                                  <Descriptions column={3} size="small">
                                    <Descriptions.Item label="世界名称">{worldSettingData.meta.world_name || currentProject?.title || '未设定'}</Descriptions.Item>
                                    <Descriptions.Item label="作品规模">{worldSettingData.meta.genre_scale || '未设定'}</Descriptions.Item>
                                    <Descriptions.Item label="创作阶段">{worldSettingData.meta.creation_stage === 'full' ? '完整版' : worldSettingData.meta.creation_stage === 'extended' ? '扩展版' : '核心版'}</Descriptions.Item>
                                  </Descriptions>
                                </Card>
                              )}
                              {/* Legacy 四大详细描述 */}
                              {worldSettingData.legacy?.time_period && (
                                <div style={{ marginBottom: 24 }}>
                                  <Title level={5} style={{ color: token.colorPrimary, marginBottom: 12 }}>⏰ 时间设定</Title>
                                  <Paragraph style={{ fontSize: 15, lineHeight: 1.8, padding: 16, background: token.colorBgLayout, borderRadius: 8, borderLeft: `4px solid ${token.colorPrimary}` }}>
                                    {worldSettingData.legacy.time_period}
                                  </Paragraph>
                                </div>
                              )}
                              {worldSettingData.legacy?.location && (
                                <div style={{ marginBottom: 24 }}>
                                  <Title level={5} style={{ color: token.colorSuccess, marginBottom: 12 }}>🌍 地点设定</Title>
                                  <Paragraph style={{ fontSize: 15, lineHeight: 1.8, padding: 16, background: token.colorBgLayout, borderRadius: 8, borderLeft: `4px solid ${token.colorSuccess}` }}>
                                    {worldSettingData.legacy.location}
                                  </Paragraph>
                                </div>
                              )}
                              {worldSettingData.legacy?.atmosphere && (
                                <div style={{ marginBottom: 24 }}>
                                  <Title level={5} style={{ color: token.colorWarning, marginBottom: 12 }}>✨ 氛围设定</Title>
                                  <Paragraph style={{ fontSize: 15, lineHeight: 1.8, padding: 16, background: token.colorBgLayout, borderRadius: 8, borderLeft: `4px solid ${token.colorWarning}` }}>
                                    {worldSettingData.legacy.atmosphere}
                                  </Paragraph>
                                </div>
                              )}
                              {worldSettingData.legacy?.rules && (
                                <div style={{ marginBottom: 24 }}>
                                  <Title level={5} style={{ color: token.colorError, marginBottom: 12 }}>📜 规则设定</Title>
                                  <Paragraph style={{ fontSize: 15, lineHeight: 1.8, padding: 16, background: token.colorBgLayout, borderRadius: 8, borderLeft: `4px solid ${token.colorError}` }}>
                                    {worldSettingData.legacy.rules}
                                  </Paragraph>
                                </div>
                              )}
                              {/* 核心要素摘要 */}
                              <Card title="📊 核心要素摘要" size="small" style={{ marginTop: 16 }}>
                                <Descriptions bordered column={2} size="small">
                                  {/* 物理维度摘要 */}
                                  {worldSettingData.physical?.power?.system_name && (
                                    <Descriptions.Item label="力量体系">{worldSettingData.physical.power.system_name}</Descriptions.Item>
                                  )}
                                  {worldSettingData.physical?.power?.levels?.length > 0 && (
                                    <Descriptions.Item label="等级划分">{worldSettingData.physical.power.levels.join(' → ')}</Descriptions.Item>
                                  )}
                                  {worldSettingData.physical?.time?.current_period && (
                                    <Descriptions.Item label="时代背景">{worldSettingData.physical.time.current_period}</Descriptions.Item>
                                  )}
                                  {worldSettingData.physical?.space?.key_locations?.length > 0 && (
                                    <Descriptions.Item label="关键地点">{worldSettingData.physical.space.key_locations.map((l: any) => l.name).join('、')}</Descriptions.Item>
                                  )}
                                  {/* 社会维度摘要 */}
                                  {worldSettingData.social?.power_structure?.key_organizations?.length > 0 && (
                                    <Descriptions.Item label="主要势力">{worldSettingData.social.power_structure.key_organizations.map((o: any) => o.name).join('、')}</Descriptions.Item>
                                  )}
                                  {worldSettingData.social?.economy?.currency_system?.length > 0 && (
                                    <Descriptions.Item label="货币体系">{worldSettingData.social.economy.currency_system.join('、')}</Descriptions.Item>
                                  )}
                                  {worldSettingData.social?.culture?.values?.length > 0 && (
                                    <Descriptions.Item label="核心价值观">{worldSettingData.social.culture.values.join('、')}</Descriptions.Item>
                                  )}
                                  {worldSettingData.social?.culture?.taboos?.length > 0 && (
                                    <Descriptions.Item label="社会禁忌">{worldSettingData.social.culture.taboos.join('、')}</Descriptions.Item>
                                  )}
                                  {/* 阵营摘要 */}
                                  {worldSettingData.social?.organizations?.protagonist_factions?.length > 0 && (
                                    <Descriptions.Item label="主角阵营">{worldSettingData.social.organizations.protagonist_factions.map((f: any) => f.name).join('、')}</Descriptions.Item>
                                  )}
                                  {worldSettingData.social?.organizations?.antagonist_factions?.length > 0 && (
                                    <Descriptions.Item label="反派阵营">{worldSettingData.social.organizations.antagonist_factions.map((f: any) => f.name).join('、')}</Descriptions.Item>
                                  )}
                                  {/* 隐喻维度摘要 */}
                                  {worldSettingData.metaphor?.themes?.core_theme && (
                                    <Descriptions.Item label="核心主题">{worldSettingData.metaphor.themes.core_theme}</Descriptions.Item>
                                  )}
                                  {worldSettingData.metaphor?.themes?.sub_themes?.length > 0 && (
                                    <Descriptions.Item label="子主题">{worldSettingData.metaphor.themes.sub_themes.join('、')}</Descriptions.Item>
                                  )}
                                </Descriptions>
                              </Card>
                            </div>
                          ),
                        },
                      ]
                    : [
                        // V2 兼容展示
                        {
                          key: 'core',
                          label: <span style={{ fontWeight: 500 }}>核心设定</span>,
                          children: (
                            <div>
                              {worldSettingData.core?.world_name && (
                                <Descriptions bordered column={1} size="small" style={{ marginBottom: 16 }}>
                                  <Descriptions.Item label="世界名称">{worldSettingData.core.world_name}</Descriptions.Item>
                                </Descriptions>
                              )}
                              {worldSettingData.core?.power_system && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>力量体系</Title>
                                  <Paragraph style={{ fontSize: 14, lineHeight: 1.8, background: token.colorBgLayout, padding: 12, borderRadius: 8 }}>
                                    {worldSettingData.core.power_system}
                                  </Paragraph>
                                </div>
                              )}
                              {worldSettingData.core?.key_locations?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>关键地点</Title>
                                  {worldSettingData.core.key_locations.map((loc: any, idx: number) => (
                                    <Card key={idx} size="small" style={{ marginBottom: 8 }}>
                                      <Descriptions column={2} size="small">
                                        <Descriptions.Item label="名称">{loc.name}</Descriptions.Item>
                                        <Descriptions.Item label="类型">{loc.type}</Descriptions.Item>
                                      </Descriptions>
                                      <Paragraph style={{ marginTop: 8, fontSize: 13 }}>{loc.brief}</Paragraph>
                                    </Card>
                                  ))}
                                </div>
                              )}
                              {worldSettingData.core?.key_organizations?.length > 0 && (
                                <div style={{ marginBottom: 16 }}>
                                  <Title level={5} style={{ marginBottom: 8 }}>主要势力</Title>
                                  {worldSettingData.core.key_organizations.map((org: any, idx: number) => (
                                    <Card key={idx} size="small" style={{ marginBottom: 8 }}>
                                      <Descriptions column={2} size="small">
                                        <Descriptions.Item label="名称">{org.name}</Descriptions.Item>
                                        <Descriptions.Item label="类型">{org.type}</Descriptions.Item>
                                      </Descriptions>
                                      <Paragraph style={{ marginTop: 8, fontSize: 13 }}>{org.brief}</Paragraph>
                                    </Card>
                                  ))}
                                </div>
                              )}
                              {worldSettingData.core?.core_rules && (
                                <div>
                                  <Title level={5} style={{ marginBottom: 8 }}>核心规则</Title>
                                  <Paragraph style={{ fontSize: 14, lineHeight: 1.8, background: token.colorBgLayout, padding: 12, borderRadius: 8 }}>
                                    {worldSettingData.core.core_rules}
                                  </Paragraph>
                                </div>
                              )}
                            </div>
                          ),
                        },
                        {
                          key: 'summary',
                          label: <span style={{ fontWeight: 500 }}>详细描述</span>,
                          children: (
                            <div>
                              {worldSettingData.summary?.time_period && (
                                <div style={{ marginBottom: 24 }}>
                                  <Title level={5} style={{ color: token.colorPrimary, marginBottom: 12 }}>时间设定</Title>
                                  <Paragraph style={{ fontSize: 15, lineHeight: 1.8, padding: 16, background: token.colorBgLayout, borderRadius: 8, borderLeft: `4px solid ${token.colorPrimary}` }}>
                                    {worldSettingData.summary.time_period}
                                  </Paragraph>
                                </div>
                              )}
                              {worldSettingData.summary?.location && (
                                <div style={{ marginBottom: 24 }}>
                                  <Title level={5} style={{ color: token.colorSuccess, marginBottom: 12 }}>地点设定</Title>
                                  <Paragraph style={{ fontSize: 15, lineHeight: 1.8, padding: 16, background: token.colorBgLayout, borderRadius: 8, borderLeft: `4px solid ${token.colorSuccess}` }}>
                                    {worldSettingData.summary.location}
                                  </Paragraph>
                                </div>
                              )}
                              {worldSettingData.summary?.atmosphere && (
                                <div style={{ marginBottom: 24 }}>
                                  <Title level={5} style={{ color: token.colorWarning, marginBottom: 12 }}>氛围设定</Title>
                                  <Paragraph style={{ fontSize: 15, lineHeight: 1.8, padding: 16, background: token.colorBgLayout, borderRadius: 8, borderLeft: `4px solid ${token.colorWarning}` }}>
                                    {worldSettingData.summary.atmosphere}
                                  </Paragraph>
                                </div>
                              )}
                              {worldSettingData.summary?.rules && (
                                <div>
                                  <Title level={5} style={{ color: token.colorError, marginBottom: 12 }}>规则设定</Title>
                                  <Paragraph style={{ fontSize: 15, lineHeight: 1.8, padding: 16, background: token.colorBgLayout, borderRadius: 8, borderLeft: `4px solid ${token.colorError}` }}>
                                    {worldSettingData.summary.rules}
                                  </Paragraph>
                                </div>
                              )}
                            </div>
                          ),
                        },
                      ]
                }
              />
            ) : (
              // 旧格式：原有4卡片展示
              <>
                {currentProject.world_time_period && (
                  <div style={{ marginBottom: 24 }}>
                    <Title level={5} style={{ color: token.colorPrimary, marginBottom: 12 }}>
                      时间设定
                    </Title>
                    <Paragraph style={{
                      fontSize: 15,
                      lineHeight: 1.8,
                      padding: 16,
                      background: token.colorBgLayout,
                      borderRadius: 8,
                      borderLeft: `4px solid ${token.colorPrimary}`
                    }}>
                      {currentProject.world_time_period}
                    </Paragraph>
                  </div>
                )}

                {currentProject.world_location && (
                  <div style={{ marginBottom: 24 }}>
                    <Title level={5} style={{ color: token.colorSuccess, marginBottom: 12 }}>
                      地点设定
                    </Title>
                    <Paragraph style={{
                      fontSize: 15,
                      lineHeight: 1.8,
                      padding: 16,
                      background: token.colorBgLayout,
                      borderRadius: 8,
                      borderLeft: `4px solid ${token.colorSuccess}`
                    }}>
                      {currentProject.world_location}
                    </Paragraph>
                  </div>
                )}

                {currentProject.world_atmosphere && (
                  <div style={{ marginBottom: 24 }}>
                    <Title level={5} style={{ color: token.colorWarning, marginBottom: 12 }}>
                      氛围设定
                    </Title>
                    <Paragraph style={{
                      fontSize: 15,
                      lineHeight: 1.8,
                      padding: 16,
                      background: token.colorBgLayout,
                      borderRadius: 8,
                      borderLeft: `4px solid ${token.colorWarning}`
                    }}>
                      {currentProject.world_atmosphere}
                    </Paragraph>
                  </div>
                )}

                {currentProject.world_rules && (
                  <div style={{ marginBottom: 0 }}>
                    <Title level={5} style={{ color: token.colorError, marginBottom: 12 }}>
                      规则设定
                    </Title>
                    <Paragraph style={{
                      fontSize: 15,
                      lineHeight: 1.8,
                      padding: 16,
                      background: token.colorBgLayout,
                      borderRadius: 8,
                      borderLeft: `4px solid ${token.colorError}`
                    }}>
                      {currentProject.world_rules}
                    </Paragraph>
                  </div>
                )}
              </>
            )}
          </div>
        </Card>
      </div>

      {/* 编辑世界观模态框 - V3 版本 */}
      <Modal
        title="编辑世界观"
        open={isEditModalVisible}
        centered
        onCancel={() => {
          setIsEditModalVisible(false);
          editForm.resetFields();
        }}
        onOk={async () => {
          try {
            const values = await editForm.validateFields();
            setIsSaving(true);

            // 构建 V3 结构
            const worldSettingData: WorldSettingV3Data = {
              version: 2,
              meta: {
                world_name: values.meta?.world_name || currentProject.title || '',
                genre_scale: values.meta?.genre_scale,
                creation_stage: hasMetaphorData(values) && hasInteractionData(values) ? 'full' : hasMetaphorData(values) ? 'extended' : 'core',
              },
              physical: {
                space: {
                  world_map: values.physical?.space?.world_map,
                  key_locations: values.physical?.space?.key_locations || [],
                  space_nodes: values.physical?.space?.space_nodes || [],
                  space_channels: values.physical?.space?.space_channels || [],
                  space_features: values.physical?.space?.space_features || [],
                  movement_rules: values.physical?.space?.movement_rules || '',
                },
                time: {
                  current_period: values.physical?.time?.current_period || '',
                  history_epochs: values.physical?.time?.history_epochs || [],
                  history_events: values.physical?.time?.history_events || [],
                  time_nodes: values.physical?.time?.time_nodes || [],
                  timeflow: values.physical?.time?.timeflow || '',
                },
                power: {
                  system_name: values.physical?.power?.system_name || '',
                  levels: values.physical?.power?.levels || [],
                  cultivation_method: values.physical?.power?.cultivation_method || '',
                  limitations: values.physical?.power?.limitations || '',
                  ability_branches: values.physical?.power?.ability_branches || [],
                  power_sources: values.physical?.power?.power_sources || [],
                  level_advances: values.physical?.power?.level_advances || [],
                },
                items: {
                  equipment_system: values.physical?.items?.equipment_system,
                  consumable_system: values.physical?.items?.consumable_system,
                  tool_system: values.physical?.items?.tool_system,
                  structure_system: values.physical?.items?.structure_system,
                  creature_system: values.physical?.items?.creature_system,
                  rare_items: values.physical?.items?.rare_items || [],
                  common_items: values.physical?.items?.common_items || [],
                  creation_rules: values.physical?.items?.creation_rules || '',
                },
              },
              social: {
                power_structure: {
                  hierarchy_rule: values.social?.power_structure?.hierarchy_rule || '',
                  key_organizations: values.social?.power_structure?.key_organizations || [],
                  faction_classification: values.social?.power_structure?.faction_classification || [],
                  power_fault_lines: values.social?.power_structure?.power_fault_lines || [],
                  power_balance: values.social?.power_structure?.power_balance || [],
                  conflict_rules: values.social?.power_structure?.conflict_rules || '',
                },
                economy: {
                  currency_system: values.social?.economy?.currency_system || [],
                  resource_distribution: values.social?.economy?.resource_distribution || '',
                  trade_networks: values.social?.economy?.trade_networks || [],
                  economic_lifelines: values.social?.economy?.economic_lifelines || [],
                  trade_rules: values.social?.economy?.trade_rules || '',
                },
                culture: {
                  values: values.social?.culture?.values || [],
                  taboos: values.social?.culture?.taboos || [],
                  traditions: values.social?.culture?.traditions || [],
                  language_style: values.social?.culture?.language_style || '',
                  core_culture: values.social?.culture?.core_culture || [],
                  religious_beliefs: values.social?.culture?.religious_beliefs || [],
                  cultural_heritage: values.social?.culture?.cultural_heritage || [],
                },
                organizations: {
                  protagonist_factions: values.social?.organizations?.protagonist_factions || [],
                  antagonist_factions: values.social?.organizations?.antagonist_factions || [],
                  neutral_factions: values.social?.organizations?.neutral_factions || [],
                  special_factions: values.social?.organizations?.special_factions || [],
                },
                relations: {
                  organization_relations: values.social?.relations?.organization_relations || [],
                  inter_personal_rules: values.social?.relations?.inter_personal_rules || '',
                },
              },
              metaphor: hasMetaphorData(values) ? {
                themes: {
                  core_theme: values.metaphor?.themes?.core_theme || '',
                  sub_themes: values.metaphor?.themes?.sub_themes,
                  theme_evolution: values.metaphor?.themes?.theme_evolution,
                  theme_mappings: values.metaphor?.themes?.theme_mappings || [],
                },
                symbols: {
                  visual: values.metaphor?.symbols?.visual || [],
                  colors: values.metaphor?.symbols?.colors || [],
                  animal_symbols: values.metaphor?.symbols?.animal_symbols || [],
                  nature_symbols: values.metaphor?.symbols?.nature_symbols || [],
                  objects: values.metaphor?.symbols?.objects || [],
                },
                core_philosophies: values.metaphor?.core_philosophies || [],
                philosophy: values.metaphor?.philosophy || [],
              } : null,
              interaction: hasInteractionData(values) ? {
                cross_rules: {
                  physical_social: values.interaction?.cross_rules?.physical_social || '',
                  social_metaphor: values.interaction?.cross_rules?.social_metaphor || '',
                  metaphor_physical: values.interaction?.cross_rules?.metaphor_physical || '',
                },
                evolution: {
                  time_driven: values.interaction?.evolution?.time_driven || '',
                  event_driven: values.interaction?.evolution?.event_driven || '',
                  character_driven: values.interaction?.evolution?.character_driven || '',
                  faction_evolution: values.interaction?.evolution?.faction_evolution || [],
                  resource_evolution: values.interaction?.evolution?.resource_evolution || [],
                },
                disruption_points: values.interaction?.disruption_points || [],
                disruption_consequences: values.interaction?.disruption_consequences || [],
                repair_mechanisms: values.interaction?.repair_mechanisms || [],
              } : null,
              legacy: {
                time_period: values.legacy?.time_period || '',
                location: values.legacy?.location || '',
                atmosphere: values.legacy?.atmosphere || '',
                rules: values.legacy?.rules || '',
              },
            };

            const updatedProject = await projectApi.updateProject(currentProject.id, {
              world_time_period: worldSettingData.legacy.time_period,
              world_location: worldSettingData.legacy.location,
              world_atmosphere: worldSettingData.legacy.atmosphere,
              world_rules: worldSettingData.legacy.rules,
              world_setting_data: JSON.stringify(worldSettingData),
            });

            setCurrentProject(updatedProject);
            message.success('世界观更新成功');
            setIsEditModalVisible(false);
            editForm.resetFields();
          } catch (error) {
            console.error('更新世界观失败:', error);
            message.error('更新失败，请重试');
          } finally {
            setIsSaving(false);
          }
        }}
        confirmLoading={isSaving}
        width={900}
        okText="保存"
        cancelText="取消"
        style={{ top: 20 }}
        styles={{
          body: {
            maxHeight: 'calc(100vh - 140px)',
            overflowY: 'auto',
            padding: '16px 24px'
          }
        }}
      >
        <Form form={editForm} layout="vertical">
          {/* 元信息 */}
          <Form.Item name={['meta', 'world_name']} label="世界名称">
            <Input placeholder="世界的名称" />
          </Form.Item>

          <Tabs
            defaultActiveKey="physical"
            items={[
              {
                key: 'physical',
                label: '🌍 物理维度',
                children: (
                  <Collapse
                    defaultActiveKey={['space', 'power']}
                    items={[
                      {
                        key: 'space',
                        label: '空间设定',
                        children: (
                          <>
                            <DynamicArrayEditor
                              name={['physical', 'space', 'key_locations']}
                              label="关键地点"
                              maxCount={5}
                              fields={[
                                { name: 'name', label: '名称', type: 'text', required: true, placeholder: '地点名称', width: 150 },
                                { name: 'type', label: '类型', type: 'text', placeholder: '如：城市、山脉、海域', width: 120 },
                                { name: 'brief', label: '简介', type: 'textarea', rows: 2, placeholder: '简要描述...', width: 200 },
                                { name: 'power_level', label: '势力等级', type: 'select', options: [
                                  { label: '高', value: '高' },
                                  { label: '中', value: '中' },
                                  { label: '低', value: '低' },
                                ], width: 80 },
                              ]}
                              defaultItem={{ name: '', type: '', brief: '', power_level: '' }}
                              itemTitle={(item, idx) => (item.name as string) || `地点 ${idx + 1}`}
                            />
                            <DynamicArrayEditor
                              name={['physical', 'space', 'space_nodes']}
                              label="空间节点"
                              maxCount={3}
                              compact
                              fields={[
                                { name: 'name', label: '名称', type: 'text', required: true, width: 120 },
                                { name: 'type', label: '类型', type: 'text', placeholder: '入口/核心区域/禁区', width: 100 },
                                { name: 'location', label: '所属区域', type: 'text', width: 100 },
                              ]}
                              defaultItem={{ name: '', type: '', location: '' }}
                            />
                            <DynamicArrayEditor
                              name={['physical', 'space', 'space_channels']}
                              label="空间通道"
                              maxCount={3}
                              compact
                              fields={[
                                { name: 'name', label: '名称', type: 'text', required: true, width: 120 },
                                { name: 'type', label: '类型', type: 'text', placeholder: '固定/临时/秘密', width: 100 },
                                { name: 'source', label: '起点', type: 'text', width: 80 },
                                { name: 'destination', label: '终点', type: 'text', width: 80 },
                              ]}
                              defaultItem={{ name: '', type: '', source: '', destination: '' }}
                            />
                            <DynamicArrayEditor
                              name={['physical', 'space', 'space_features']}
                              label="空间特性"
                              maxCount={3}
                              compact
                              fields={[
                                { name: 'name', label: '名称', type: 'text', required: true, width: 120 },
                                { name: 'type', label: '类型', type: 'text', placeholder: '环境/规则/物理', width: 100 },
                                { name: 'effect', label: '影响', type: 'text', width: 120 },
                              ]}
                              defaultItem={{ name: '', type: '', effect: '' }}
                            />
                            <Form.Item name={['physical', 'space', 'movement_rules']} label="移动规则">
                              <Input placeholder="描述在这个世界中的移动方式和限制..." />
                            </Form.Item>
                          </>
                        ),
                      },
                      {
                        key: 'time',
                        label: '时间设定',
                        children: (
                          <>
                            <Form.Item name={['physical', 'time', 'current_period']} label="时代背景">
                              <TextArea rows={3} placeholder="描述当前的时代背景..." />
                            </Form.Item>
                            <DynamicArrayEditor
                              name={['physical', 'time', 'history_epochs']}
                              label="历史纪元"
                              maxCount={3}
                              compact
                              fields={[
                                { name: 'name', label: '纪元名称', type: 'text', required: true, width: 120 },
                                { name: 'period', label: '时间跨度', type: 'text', width: 100 },
                                { name: 'impact', label: '影响', type: 'textarea', rows: 1, width: 150 },
                              ]}
                              defaultItem={{ name: '', period: '', impact: '' }}
                            />
                            <DynamicArrayEditor
                              name={['physical', 'time', 'history_events']}
                              label="关键事件年表"
                              maxCount={5}
                              compact
                              fields={[
                                { name: 'year', label: '年份', type: 'text', width: 80 },
                                { name: 'event_name', label: '事件名称', type: 'text', required: true, width: 120 },
                                { name: 'description', label: '描述', type: 'textarea', rows: 1, width: 150 },
                              ]}
                              defaultItem={{ year: '', event_name: '', description: '' }}
                            />
                            <DynamicArrayEditor
                              name={['physical', 'time', 'time_nodes']}
                              label="时间节点"
                              maxCount={3}
                              compact
                              fields={[
                                { name: 'name', label: '节点名称', type: 'text', required: true, width: 100 },
                                { name: 'epoch', label: '所属纪元', type: 'text', width: 100 },
                                { name: 'event', label: '关联事件', type: 'text', width: 120 },
                              ]}
                              defaultItem={{ name: '', epoch: '', event: '' }}
                            />
                            <Form.Item name={['physical', 'time', 'timeflow']} label="时间流速">
                              <Input placeholder="描述时间的特殊流动特性..." />
                            </Form.Item>
                          </>
                        ),
                      },
                      {
                        key: 'power',
                        label: '力量体系',
                        children: (
                          <>
                            <Form.Item name={['physical', 'power', 'system_name']} label="体系名称">
                              <Input placeholder="如：修仙体系、科技等级、社会阶层" />
                            </Form.Item>
                            <Form.Item name={['physical', 'power', 'levels']} label="等级划分">
                              <Select
                                mode="tags"
                                placeholder="输入等级名称，按回车添加（按从低到高顺序）"
                                style={{ width: '100%' }}
                              />
                            </Form.Item>
                            <Form.Item name={['physical', 'power', 'cultivation_method']} label="获取方式">
                              <TextArea rows={2} placeholder="描述如何获得力量/晋升..." />
                            </Form.Item>
                            <Form.Item name={['physical', 'power', 'limitations']} label="限制">
                              <TextArea rows={2} placeholder="描述力量的限制或约束..." />
                            </Form.Item>
                            <DynamicArrayEditor
                              name={['physical', 'power', 'ability_branches']}
                              label="能力分支"
                              maxCount={3}
                              fields={[
                                { name: 'name', label: '分支名称', type: 'text', required: true, width: 120 },
                                { name: 'description', label: '描述', type: 'textarea', rows: 2, width: 200 },
                              ]}
                              defaultItem={{ name: '', description: '' }}
                              itemTitle={(item, idx) => (item.name as string) || `分支 ${idx + 1}`}
                            />
                            <DynamicArrayEditor
                              name={['physical', 'power', 'power_sources']}
                              label="力量来源"
                              maxCount={3}
                              compact
                              fields={[
                                { name: 'name', label: '名称', type: 'text', required: true, width: 120 },
                                { name: 'type', label: '类型', type: 'text', placeholder: '自然/人工/血脉', width: 100 },
                                { name: 'acquisition', label: '获取方式', type: 'text', width: 120 },
                              ]}
                              defaultItem={{ name: '', type: '', acquisition: '' }}
                            />
                            <DynamicArrayEditor
                              name={['physical', 'power', 'level_advances']}
                              label="等级晋升规则"
                              maxCount={3}
                              fields={[
                                { name: 'level_name', label: '等级名称', type: 'text', required: true, width: 120 },
                                { name: 'requirements', label: '晋升条件', type: 'textarea', rows: 2, width: 200 },
                              ]}
                              defaultItem={{ level_name: '', requirements: '' }}
                              itemTitle={(item, idx) => (item.level_name as string) || `晋升 ${idx + 1}`}
                            />
                          </>
                        ),
                      },
                      {
                        key: 'items',
                        label: '物品设定',
                        children: (
                          <>
                            <Form.Item name={['physical', 'items', 'creation_rules']} label="制作规则">
                              <TextArea rows={2} placeholder="描述物品的制作/获取规则..." />
                            </Form.Item>
                            <Form.Item name={['physical', 'items', 'rare_items']} label="稀有物品">
                              <Select
                                mode="tags"
                                placeholder="输入物品名称，按回车添加"
                                style={{ width: '100%' }}
                              />
                            </Form.Item>
                            <Form.Item name={['physical', 'items', 'common_items']} label="常见物品">
                              <Select
                                mode="tags"
                                placeholder="输入常见物品名称，按回车添加"
                                style={{ width: '100%' }}
                              />
                            </Form.Item>
                            <Collapse
                              items={[
                                {
                                  key: 'item_systems',
                                  label: '物品体系详细设置',
                                  children: (
                                    <>
                                      <Form.Item name={['physical', 'items', 'equipment_system', 'crafting_rules']} label="装备体系制作规则">
                                        <TextArea rows={2} placeholder="描述装备制作规则..." />
                                      </Form.Item>
                                      <Form.Item name={['physical', 'items', 'consumable_system', 'crafting_rules']} label="消耗品体系制作规则">
                                        <TextArea rows={2} placeholder="描述消耗品制作规则..." />
                                      </Form.Item>
                                      <Form.Item name={['physical', 'items', 'tool_system', 'crafting_rules']} label="工具体系制作规则">
                                        <TextArea rows={2} placeholder="描述工具制作规则..." />
                                      </Form.Item>
                                      <Form.Item name={['physical', 'items', 'structure_system', 'crafting_rules']} label="结构体系制作规则">
                                        <TextArea rows={2} placeholder="描述结构（阵法/建筑）制作规则..." />
                                      </Form.Item>
                                      <Form.Item name={['physical', 'items', 'creature_system', 'crafting_rules']} label="生物体系制作规则">
                                        <TextArea rows={2} placeholder="描述生物（宠物/坐骑）获取规则..." />
                                      </Form.Item>
                                    </>
                                  ),
                                },
                              ]}
                            />
                          </>
                        ),
                      },
                    ]}
                  />
                ),
              },

              {
                key: 'social',
                label: '🏛️ 社会维度',
                children: (
                  <Collapse
                    defaultActiveKey={['power_structure']}
                    items={[
                      {
                        key: 'power_structure',
                        label: '权力结构',
                        children: (
                          <>
                            <Form.Item name={['social', 'power_structure', 'hierarchy_rule']} label="等级制度">
                              <TextArea rows={3} placeholder="描述社会的等级制度..." />
                            </Form.Item>
                            <DynamicArrayEditor
                              name={['social', 'power_structure', 'key_organizations']}
                              label="主要势力"
                              maxCount={5}
                              fields={[
                                { name: 'name', label: '名称', type: 'text', required: true, width: 150 },
                                { name: 'type', label: '类型', type: 'text', placeholder: '如：门派、帝国', width: 120 },
                                { name: 'brief', label: '简介', type: 'textarea', rows: 2, width: 200 },
                                { name: 'power_level', label: '势力等级', type: 'select', options: [
                                  { label: '高', value: '高' },
                                  { label: '中', value: '中' },
                                  { label: '低', value: '低' },
                                ], width: 80 },
                              ]}
                              defaultItem={{ name: '', type: '', brief: '', power_level: '' }}
                            />
                            <DynamicArrayEditor
                              name={['social', 'power_structure', 'power_fault_lines']}
                              label="权力断层线"
                              maxCount={3}
                              compact
                              fields={[
                                { name: 'name', label: '名称', type: 'text', required: true, width: 120 },
                                { name: 'type', label: '类型', type: 'text', placeholder: '冲突/争夺/分歧', width: 100 },
                                { name: 'intensity', label: '强度', type: 'select', options: [
                                  { label: '高', value: '高' },
                                  { label: '中', value: '中' },
                                  { label: '低', value: '低' },
                                ], width: 80 },
                              ]}
                              defaultItem={{ name: '', type: '', intensity: '' }}
                            />
                            <DynamicArrayEditor
                              name={['social', 'power_structure', 'power_balance']}
                              label="权力制衡"
                              maxCount={3}
                              compact
                              fields={[
                                { name: 'mechanism_name', label: '机制', type: 'text', required: true, width: 120 },
                                { name: 'type', label: '类型', type: 'text', placeholder: '联盟/法律/武力', width: 100 },
                              ]}
                              defaultItem={{ mechanism_name: '', type: '' }}
                            />
                            <Form.Item name={['social', 'power_structure', 'conflict_rules']} label="冲突规则">
                              <TextArea rows={2} placeholder="描述势力间的冲突规则..." />
                            </Form.Item>
                          </>
                        ),
                      },
                      {
                        key: 'economy',
                        label: '经济体系',
                        children: (
                          <>
                            <Form.Item name={['social', 'economy', 'currency_system']} label="货币体系">
                              <Select mode="tags" placeholder="输入货币类型，按回车添加" style={{ width: '100%' }} />
                            </Form.Item>
                            <Form.Item name={['social', 'economy', 'resource_distribution']} label="资源分布">
                              <TextArea rows={2} placeholder="描述资源的分布情况..." />
                            </Form.Item>
                            <DynamicArrayEditor
                              name={['social', 'economy', 'trade_networks']}
                              label="贸易网络"
                              maxCount={3}
                              compact
                              fields={[
                                { name: 'name', label: '名称', type: 'text', required: true, width: 120 },
                                { name: 'type', label: '类型', type: 'text', placeholder: '市场/拍卖/黑市', width: 100 },
                              ]}
                              defaultItem={{ name: '', type: '' }}
                            />
                            <DynamicArrayEditor
                              name={['social', 'economy', 'economic_lifelines']}
                              label="经济命脉"
                              maxCount={3}
                              compact
                              fields={[
                                { name: 'name', label: '名称', type: 'text', required: true, width: 120 },
                                { name: 'type', label: '类型', type: 'text', placeholder: '资源/产业', width: 100 },
                              ]}
                              defaultItem={{ name: '', type: '' }}
                            />
                            <Form.Item name={['social', 'economy', 'trade_rules']} label="贸易规则">
                              <TextArea rows={2} placeholder="描述贸易的规则和限制..." />
                            </Form.Item>
                          </>
                        ),
                      },
                      {
                        key: 'culture',
                        label: '文化设定',
                        children: (
                          <>
                            <Form.Item name={['social', 'culture', 'values']} label="核心价值观">
                              <Select
                                mode="tags"
                                placeholder="输入价值观，按回车添加"
                                style={{ width: '100%' }}
                              />
                            </Form.Item>
                            <Form.Item name={['social', 'culture', 'taboos']} label="社会禁忌">
                              <Select
                                mode="tags"
                                placeholder="输入禁忌，按回车添加"
                                style={{ width: '100%' }}
                              />
                            </Form.Item>
                            <Form.Item name={['social', 'culture', 'traditions']} label="传统习俗">
                              <Select mode="tags" placeholder="输入传统习俗，按回车添加" style={{ width: '100%' }} />
                            </Form.Item>
                            <DynamicArrayEditor
                              name={['social', 'culture', 'core_culture']}
                              label="核心文化"
                              maxCount={3}
                              compact
                              fields={[
                                { name: 'name', label: '名称', type: 'text', required: true, width: 120 },
                                { name: 'type', label: '类型', type: 'text', placeholder: '能力/商业/学术文化', width: 100 },
                              ]}
                              defaultItem={{ name: '', type: '' }}
                            />
                            <DynamicArrayEditor
                              name={['social', 'culture', 'religious_beliefs']}
                              label="宗教信仰"
                              maxCount={3}
                              compact
                              fields={[
                                { name: 'name', label: '信仰', type: 'text', required: true, width: 120 },
                                { name: 'type', label: '类型', type: 'text', placeholder: '主流/边缘/禁忌', width: 100 },
                              ]}
                              defaultItem={{ name: '', type: '' }}
                            />
                            <DynamicArrayEditor
                              name={['social', 'culture', 'cultural_heritage']}
                              label="文化传承"
                              maxCount={3}
                              compact
                              fields={[
                                { name: 'name', label: '传承', type: 'text', required: true, width: 120 },
                                { name: 'origin', label: '起源', type: 'text', width: 100 },
                              ]}
                              defaultItem={{ name: '', origin: '' }}
                            />
                            <Form.Item name={['social', 'culture', 'language_style']} label="语言风格">
                              <Input placeholder="描述世界的语言风格特点..." />
                            </Form.Item>
                          </>
                        ),
                      },
                      {
                        key: 'organizations',
                        label: '阵营势力',
                        children: (
                          <>
                            <DynamicArrayEditor
                              name={['social', 'organizations', 'protagonist_factions']}
                              label="主角阵营"
                              maxCount={3}
                              fields={[
                                { name: 'name', label: '名称', type: 'text', required: true, width: 120 },
                                { name: 'type', label: '类型', type: 'text', placeholder: '组织类型', width: 100 },
                                { name: 'brief', label: '简介', type: 'textarea', rows: 2, width: 180 },
                              ]}
                              defaultItem={{ name: '', type: '', brief: '' }}
                              itemTitle={(item, idx) => (item.name as string) || `主角阵营 ${idx + 1}`}
                            />
                            <DynamicArrayEditor
                              name={['social', 'organizations', 'antagonist_factions']}
                              label="反派阵营"
                              maxCount={3}
                              fields={[
                                { name: 'name', label: '名称', type: 'text', required: true, width: 120 },
                                { name: 'type', label: '类型', type: 'text', placeholder: '组织类型', width: 100 },
                                { name: 'brief', label: '简介', type: 'textarea', rows: 2, width: 180 },
                              ]}
                              defaultItem={{ name: '', type: '', brief: '' }}
                              itemTitle={(item, idx) => (item.name as string) || `反派阵营 ${idx + 1}`}
                            />
                            <DynamicArrayEditor
                              name={['social', 'organizations', 'neutral_factions']}
                              label="中立阵营"
                              maxCount={3}
                              compact
                              fields={[
                                { name: 'name', label: '名称', type: 'text', required: true, width: 120 },
                                { name: 'type', label: '类型', type: 'text', width: 100 },
                              ]}
                              defaultItem={{ name: '', type: '' }}
                            />
                            <DynamicArrayEditor
                              name={['social', 'organizations', 'special_factions']}
                              label="特殊阵营"
                              maxCount={2}
                              compact
                              fields={[
                                { name: 'name', label: '名称', type: 'text', required: true, width: 120 },
                                { name: 'type', label: '类型', type: 'text', width: 100 },
                              ]}
                              defaultItem={{ name: '', type: '' }}
                            />
                          </>
                        ),
                      },
                      {
                        key: 'relations',
                        label: '关系设置',
                        children: (
                          <>
                            <DynamicArrayEditor
                              name={['social', 'relations', 'organization_relations']}
                              label="组织关系"
                              maxCount={5}
                              compact
                              fields={[
                                { name: 'org_a', label: '组织A', type: 'text', required: true, width: 100 },
                                { name: 'org_b', label: '组织B', type: 'text', required: true, width: 100 },
                                { name: 'type', label: '关系类型', type: 'text', width: 100 },
                                { name: 'description', label: '描述', type: 'text', width: 120 },
                              ]}
                              defaultItem={{ org_a: '', org_b: '', type: '', description: '' }}
                            />
                            <Form.Item name={['social', 'relations', 'inter_personal_rules']} label="人际规则">
                              <TextArea rows={2} placeholder="描述人际交往的一般规则..." />
                            </Form.Item>
                          </>
                        ),
                      },
                    ]}
                  />
                ),
              },

              {
                key: 'metaphor',
                label: '🎭 隐喻维度',
                children: (
                  <Collapse
                    items={[
                      {
                        key: 'themes',
                        label: '核心主题',
                        children: (
                          <>
                            <Form.Item name={['metaphor', 'themes', 'core_theme']} label="核心主题">
                              <TextArea rows={3} placeholder="描述作品的核心主题..." />
                            </Form.Item>
                            <Form.Item name={['metaphor', 'themes', 'sub_themes']} label="子主题">
                              <Select mode="tags" placeholder="输入子主题，按回车添加" style={{ width: '100%' }} />
                            </Form.Item>
                            <Form.Item name={['metaphor', 'themes', 'theme_evolution']} label="主题演化">
                              <TextArea rows={2} placeholder="描述主题的演化路径..." />
                            </Form.Item>
                            <DynamicArrayEditor
                              name={['metaphor', 'themes', 'theme_mappings']}
                              label="主题映射"
                              maxCount={4}
                              compact
                              fields={[
                                { name: 'mapping_type', label: '映射类型', type: 'text', required: true, width: 120 },
                                { name: 'physical_manifestation', label: '物理体现', type: 'text', width: 120 },
                                { name: 'metaphor_meaning', label: '隐喻含义', type: 'text', width: 120 },
                              ]}
                              defaultItem={{ mapping_type: '', physical_manifestation: '', metaphor_meaning: '' }}
                            />
                          </>
                        ),
                      },
                      {
                        key: 'symbols',
                        label: '象征符号',
                        children: (
                          <>
                            <Form.Item name={['metaphor', 'symbols', 'visual']} label="视觉象征">
                              <Select mode="tags" placeholder="输入视觉象征，按回车添加" style={{ width: '100%' }} />
                            </Form.Item>
                            <Form.Item name={['metaphor', 'symbols', 'colors']} label="颜色象征">
                              <Select mode="tags" placeholder="输入颜色象征，按回车添加" style={{ width: '100%' }} />
                            </Form.Item>
                            <Form.Item name={['metaphor', 'symbols', 'objects']} label="物品象征">
                              <Select mode="tags" placeholder="输入物品象征，按回车添加" style={{ width: '100%' }} />
                            </Form.Item>
                            <DynamicArrayEditor
                              name={['metaphor', 'symbols', 'animal_symbols']}
                              label="动物符号"
                              maxCount={3}
                              compact
                              fields={[
                                { name: 'animal', label: '动物', type: 'text', required: true, width: 100 },
                                { name: 'symbolism', label: '象征', type: 'text', width: 120 },
                              ]}
                              defaultItem={{ animal: '', symbolism: '' }}
                            />
                            <DynamicArrayEditor
                              name={['metaphor', 'symbols', 'nature_symbols']}
                              label="自然符号"
                              maxCount={3}
                              compact
                              fields={[
                                { name: 'element', label: '元素', type: 'text', required: true, width: 100 },
                                { name: 'symbolism', label: '象征', type: 'text', width: 120 },
                              ]}
                              defaultItem={{ element: '', symbolism: '' }}
                            />
                          </>
                        ),
                      },
                      {
                        key: 'philosophy',
                        label: '哲学内核',
                        children: (
                          <>
                            <DynamicArrayEditor
                              name={['metaphor', 'core_philosophies']}
                              label="哲学内核"
                              maxCount={5}
                              fields={[
                                { name: 'philosophy_name', label: '哲学名称', type: 'text', required: true, width: 120 },
                                { name: 'core_concept', label: '核心概念', type: 'textarea', rows: 2, width: 200 },
                              ]}
                              defaultItem={{ philosophy_name: '', core_concept: '' }}
                              itemTitle={(item, idx) => (item.philosophy_name as string) || `哲学 ${idx + 1}`}
                            />
                            <DynamicArrayEditor
                              name={['metaphor', 'philosophy']}
                              label="哲学观念（兼容格式）"
                              maxCount={2}
                              fields={[
                                { name: 'name', label: '观念名称', type: 'text', required: true },
                                { name: 'school', label: '流派', type: 'text' },
                                { name: 'influence', label: '影响', type: 'textarea', rows: 2 },
                              ]}
                              defaultItem={{ name: '', school: '', influence: '' }}
                              compact
                            />
                          </>
                        ),
                      },
                    ]}
                  />
                ),
              },

              {
                key: 'interaction',
                label: '🔗 交互维度',
                children: (
                  <Collapse
                    items={[
                      {
                        key: 'cross_rules',
                        label: '维度交叉规则',
                        children: (
                          <>
                            <Form.Item name={['interaction', 'cross_rules', 'physical_social']} label="物理与社会">
                              <TextArea rows={2} placeholder="物理设定如何影响社会结构..." />
                            </Form.Item>
                            <Form.Item name={['interaction', 'cross_rules', 'social_metaphor']} label="社会与隐喻">
                              <TextArea rows={2} placeholder="社会结构如何体现主题..." />
                            </Form.Item>
                            <Form.Item name={['interaction', 'cross_rules', 'metaphor_physical']} label="隐喻与物理">
                              <TextArea rows={2} placeholder="隐喻如何影响物理设定..." />
                            </Form.Item>
                          </>
                        ),
                      },
                      {
                        key: 'evolution',
                        label: '演化机制',
                        children: (
                          <>
                            <Form.Item name={['interaction', 'evolution', 'time_driven']} label="时间驱动">
                              <TextArea rows={2} placeholder="随时间推移发生的变化..." />
                            </Form.Item>
                            <Form.Item name={['interaction', 'evolution', 'event_driven']} label="事件驱动">
                              <TextArea rows={2} placeholder="关键事件引发的变革..." />
                            </Form.Item>
                            <Form.Item name={['interaction', 'evolution', 'character_driven']} label="角色驱动">
                              <TextArea rows={2} placeholder="角色行为引发的变革..." />
                            </Form.Item>
                            <DynamicArrayEditor
                              name={['interaction', 'evolution', 'faction_evolution']}
                              label="势力演化"
                              maxCount={3}
                              compact
                              fields={[
                                { name: 'faction_name', label: '势力', type: 'text', required: true, width: 120 },
                                { name: 'evolution_type', label: '类型', type: 'text', placeholder: '增强/衰退/分裂', width: 100 },
                                { name: 'trigger', label: '触发原因', type: 'text', width: 120 },
                              ]}
                              defaultItem={{ faction_name: '', evolution_type: '', trigger: '' }}
                            />
                            <DynamicArrayEditor
                              name={['interaction', 'evolution', 'resource_evolution']}
                              label="资源演化"
                              maxCount={3}
                              compact
                              fields={[
                                { name: 'resource_name', label: '资源', type: 'text', required: true, width: 120 },
                                { name: 'evolution_type', label: '类型', type: 'text', placeholder: '增加/减少/枯竭', width: 100 },
                                { name: 'cause', label: '原因', type: 'text', width: 120 },
                              ]}
                              defaultItem={{ resource_name: '', evolution_type: '', cause: '' }}
                            />
                          </>
                        ),
                      },
                      {
                        key: 'disruption',
                        label: '破坏点与修复',
                        children: (
                          <>
                            <Form.Item name={['interaction', 'disruption_points']} label="可打破的规则点">
                              <Select mode="tags" placeholder="输入可打破的规则点，按回车添加" style={{ width: '100%' }} />
                            </Form.Item>
                            <DynamicArrayEditor
                              name={['interaction', 'disruption_consequences']}
                              label="破坏后果"
                              maxCount={3}
                              compact
                              fields={[
                                { name: 'disruption_type', label: '类型', type: 'text', required: true, width: 120 },
                                { name: 'immediate_effect', label: '直接后果', type: 'text', width: 150 },
                              ]}
                              defaultItem={{ disruption_type: '', immediate_effect: '' }}
                            />
                            <Form.Item name={['interaction', 'repair_mechanisms']} label="规则修复机制">
                              <Select mode="tags" placeholder="输入修复机制，按回车添加" style={{ width: '100%' }} />
                            </Form.Item>
                          </>
                        ),
                      },
                    ]}
                  />
                ),
              },

              {
                key: 'legacy',
                label: '📝 详细描述',
                children: (
                  <>
                    <Form.Item name={['legacy', 'time_period']} label="时间设定" rules={[{ required: true, message: '请输入时间设定' }]}>
                      <TextArea rows={4} placeholder="描述故事发生的时代背景..." showCount maxLength={1000} />
                    </Form.Item>
                    <Form.Item name={['legacy', 'location']} label="地点设定" rules={[{ required: true, message: '请输入地点设定' }]}>
                      <TextArea rows={4} placeholder="描述故事发生的地理位置和环境..." showCount maxLength={1000} />
                    </Form.Item>
                    <Form.Item name={['legacy', 'atmosphere']} label="氛围设定" rules={[{ required: true, message: '请输入氛围设定' }]}>
                      <TextArea rows={4} placeholder="描述故事的整体氛围和基调..." showCount maxLength={1000} />
                    </Form.Item>
                    <Form.Item name={['legacy', 'rules']} label="规则设定" rules={[{ required: true, message: '请输入规则设定' }]}>
                      <TextArea rows={4} placeholder="描述这个世界的特殊规则和设定..." showCount maxLength={1000} />
                    </Form.Item>
                  </>
                ),
              },
            ]}
          />
        </Form>
      </Modal>

      {/* 编辑项目基础信息模态框 */}
      <Modal
        title="编辑项目基础信息"
        open={isEditProjectModalVisible}
        centered
        onCancel={() => {
          setIsEditProjectModalVisible(false);
          editProjectForm.resetFields();
        }}
        onOk={async () => {
          try {
            const values = await editProjectForm.validateFields();
            setIsSavingProject(true);

            const updatedProject = await projectApi.updateProject(currentProject.id, {
              title: values.title,
              description: values.description,
              theme: values.theme,
              genre: values.genre,
              narrative_perspective: values.narrative_perspective,
              target_words: values.target_words,
            });

            setCurrentProject(updatedProject);
            message.success('项目基础信息更新成功');
            setIsEditProjectModalVisible(false);
            editProjectForm.resetFields();
          } catch (error) {
            console.error('更新项目基础信息失败:', error);
            message.error('更新失败，请重试');
          } finally {
            setIsSavingProject(false);
          }
        }}
        confirmLoading={isSavingProject}
        width={800}
        okText="保存"
        cancelText="取消"
      >
        <Form
          form={editProjectForm}
          layout="vertical"
          style={{ marginTop: 16 }}
        >
          <Form.Item
            label="小说名称"
            name="title"
            rules={[
              { required: true, message: '请输入小说名称' },
              { max: 200, message: '名称不能超过200字' }
            ]}
          >
            <Input
              placeholder="请输入小说名称"
              showCount
              maxLength={200}
            />
          </Form.Item>

          <Form.Item
            label="小说简介"
            name="description"
            rules={[
              { max: 1000, message: '简介不能超过1000字' }
            ]}
          >
            <TextArea
              rows={4}
              placeholder="请输入小说简介（选填）"
              showCount
              maxLength={1000}
            />
          </Form.Item>

          <Form.Item
            label="小说主题"
            name="theme"
            rules={[
              { max: 500, message: '主题不能超过500字' }
            ]}
          >
            <TextArea
              rows={3}
              placeholder="请输入小说主题（选填）"
              showCount
              maxLength={500}
            />
          </Form.Item>

          <Form.Item
            label="小说类型"
            name="genre"
            rules={[
              { max: 100, message: '类型不能超过100字' }
            ]}
          >
            <Input
              placeholder="请输入小说类型，如：玄幻、都市、科幻等（选填）"
              showCount
              maxLength={100}
            />
          </Form.Item>

          <Form.Item
            label="叙事视角"
            name="narrative_perspective"
          >
            <Select
              placeholder="请选择叙事视角（选填）"
              allowClear
              options={[
                { label: '第一人称', value: '第一人称' },
                { label: '第三人称', value: '第三人称' },
                { label: '全知视角', value: '全知视角' }
              ]}
            />
          </Form.Item>

          <Form.Item
            label="目标字数"
            name="target_words"
            rules={[
              { type: 'number', min: 0, message: '目标字数不能为负数' },
              { type: 'number', max: 2147483647, message: '目标字数超出范围' }
            ]}
          >
            <InputNumber
              style={{ width: '100%' }}
              placeholder="请输入目标字数（选填，最大21亿字）"
              min={0}
              max={2147483647}
              step={1000}
              suffix="字"
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* AI重新生成加载遮罩 */}
      <SSELoadingOverlay
        loading={isRegenerating}
        progress={regenerateProgress}
        message={regenerateMessage}
      />

      {/* 预览重新生成的内容模态框 */}
      <Modal
        title="预览重新生成的世界观"
        open={isPreviewModalVisible}
        centered
        width={900}
        onOk={handleConfirmSave}
        onCancel={handleCancelSave}
        confirmLoading={isSavingPreview}
        okText="确认替换"
        cancelText="取消"
        okButtonProps={{ danger: true }}
      >
        {newWorldData && (() => {
          // 检查是否是Markdown格式
          if (newWorldData.world_setting_format === 'markdown' && newWorldData.world_setting_markdown) {
            // Markdown格式直接显示
            return (
              <div className="markdown-content" style={{
                maxHeight: '400px',
                overflowY: 'auto',
                padding: 16,
                background: token.colorBgLayout,
                borderRadius: 8,
              }}>
                <WorldSettingMarkdownRenderer content={newWorldData.world_setting_markdown} />
              </div>
            );
          }

          // JSON格式：解析 V3 结构化数据
          let v3Data: WorldSettingV3Data | null = null;
          if (newWorldData.world_setting_data) {
            try {
              const parsed = JSON.parse(newWorldData.world_setting_data);
              if (parsed.version === 2) {
                v3Data = parsed as WorldSettingV3Data;
              }
            } catch (e) {
              console.error('解析预览数据失败:', e);
            }
          }

          // 构建 Collapse items
          const collapseItems: Array<{ key: string; label: string; children: React.ReactNode }> = [];

          // 物理维度
          if (v3Data?.physical) {
            const physicalChildren = [];

            // 关键地点
            if (v3Data.physical.space?.key_locations?.length > 0) {
              physicalChildren.push(
                <div key="locations" style={{ marginBottom: 16 }}>
                  <Title level={5}>关键地点</Title>
                  {v3Data.physical.space.key_locations.map((loc, idx) => (
                    <Paragraph key={idx} style={{ padding: 12, background: token.colorBgLayout, borderRadius: 6, marginBottom: 8 }}>
                      <strong>{loc.name}</strong> ({loc.type})：{loc.brief}
                    </Paragraph>
                  ))}
                </div>
              );
            }

            // 时代背景
            if (v3Data.physical.time?.current_period) {
              physicalChildren.push(
                <div key="time" style={{ marginBottom: 16 }}>
                  <Title level={5}>时代背景</Title>
                  <Paragraph style={{ padding: 12, background: token.colorBgLayout, borderRadius: 6 }}>
                    {v3Data.physical.time.current_period}
                  </Paragraph>
                </div>
              );
            }

            // 力量体系
            if (v3Data.physical.power?.system_name || v3Data.physical.power?.levels?.length > 0) {
              physicalChildren.push(
                <div key="power" style={{ marginBottom: 16 }}>
                  <Title level={5}>力量体系</Title>
                  <Paragraph style={{ padding: 12, background: token.colorBgLayout, borderRadius: 6 }}>
                    <strong>体系名称：</strong>{v3Data.physical.power.system_name || '未设定'}
                    {v3Data.physical.power.levels?.length > 0 && (
                      <><br /><strong>等级划分：</strong>{v3Data.physical.power.levels.join(' → ')}</>
                    )}
                    {v3Data.physical.power.cultivation_method && (
                      <><br /><strong>修炼方式：</strong>{v3Data.physical.power.cultivation_method}</>
                    )}
                  </Paragraph>
                </div>
              );
            }

            // 稀有物品
            const rareItems = v3Data.physical.items?.rare_items;
            if (rareItems && rareItems.length > 0) {
              physicalChildren.push(
                <div key="items" style={{ marginBottom: 16 }}>
                  <Title level={5}>稀有物品</Title>
                  {rareItems.map((item, idx) => (
                    <Paragraph key={idx} style={{ padding: 12, background: token.colorBgLayout, borderRadius: 6, marginBottom: 8 }}>
                      {typeof item === 'string' ? item : `${item}`}
                    </Paragraph>
                  ))}
                </div>
              );
            }

            if (physicalChildren.length > 0) {
              collapseItems.push({
                key: 'physical',
                label: '物理维度',
                children: physicalChildren
              });
            }
          }

          // 社会维度
          if (v3Data?.social) {
            const socialChildren = [];

            // 等级制度
            if (v3Data.social.power_structure?.hierarchy_rule) {
              socialChildren.push(
                <div key="hierarchy" style={{ marginBottom: 16 }}>
                  <Title level={5}>等级制度</Title>
                  <Paragraph style={{ padding: 12, background: token.colorBgLayout, borderRadius: 6 }}>
                    {v3Data.social.power_structure.hierarchy_rule}
                  </Paragraph>
                </div>
              );
            }

            // 主要势力
            if (v3Data.social.power_structure?.key_organizations?.length > 0) {
              socialChildren.push(
                <div key="organizations" style={{ marginBottom: 16 }}>
                  <Title level={5}>主要势力</Title>
                  {v3Data.social.power_structure.key_organizations.map((org, idx) => (
                    <Paragraph key={idx} style={{ padding: 12, background: token.colorBgLayout, borderRadius: 6, marginBottom: 8 }}>
                      <strong>{org.name}</strong> ({org.type})：{org.brief}
                      {org.power_level && <><br /><strong>势力等级：</strong>{org.power_level}</>}
                    </Paragraph>
                  ))}
                </div>
              );
            }

            // 文化设定
            if (v3Data.social.culture?.values?.length > 0 || v3Data.social.culture?.taboos?.length > 0) {
              socialChildren.push(
                <div key="culture" style={{ marginBottom: 16 }}>
                  <Title level={5}>文化设定</Title>
                  <Paragraph style={{ padding: 12, background: token.colorBgLayout, borderRadius: 6 }}>
                    {v3Data.social.culture.values?.length > 0 && (
                      <><strong>核心价值观：</strong>{v3Data.social.culture.values.join('、')}<br /></>
                    )}
                    {v3Data.social.culture.taboos?.length > 0 && (
                      <><strong>社会禁忌：</strong>{v3Data.social.culture.taboos.join('、')}</>
                    )}
                  </Paragraph>
                </div>
              );
            }

            if (socialChildren.length > 0) {
              collapseItems.push({
                key: 'social',
                label: '社会维度',
                children: socialChildren
              });
            }
          }

          // Legacy 维度（始终显示）
          collapseItems.push({
            key: 'legacy',
            label: '基础设定',
            children: [
              <div key="legacy" style={{ marginBottom: 16 }}>
                <Paragraph style={{ padding: 12, background: token.colorBgLayout, borderRadius: 6, marginBottom: 8 }}>
                  <strong>时间背景：</strong>{newWorldData.time_period}
                </Paragraph>
                <Paragraph style={{ padding: 12, background: token.colorBgLayout, borderRadius: 6, marginBottom: 8 }}>
                  <strong>地点设定：</strong>{newWorldData.location}
                </Paragraph>
                <Paragraph style={{ padding: 12, background: token.colorBgLayout, borderRadius: 6, marginBottom: 8 }}>
                  <strong>氛围基调：</strong>{newWorldData.atmosphere}
                </Paragraph>
                <Paragraph style={{ padding: 12, background: token.colorBgLayout, borderRadius: 6 }}>
                  <strong>世界规则：</strong>{newWorldData.rules}
                </Paragraph>
              </div>
            ]
          });

          return (
            <div style={{ maxHeight: '60vh', overflowY: 'auto' }}>
              <div style={{ marginBottom: 16, padding: 12, background: token.colorWarningBg, border: `1px solid ${token.colorWarningBorder}`, borderRadius: 8 }}>
                <Typography.Text type="warning">
                  ⚠️ 注意：点击"确认替换"将会用新内容替换当前的世界观设定
                </Typography.Text>
              </div>

              <Collapse items={collapseItems} defaultActiveKey={['physical', 'social', 'legacy']} />
            </div>
          );
        })()}
      </Modal>

      {/* Markdown编辑模态框 */}
      <Modal
        title="编辑世界设定（Markdown格式）"
        open={isMarkdownEditModalVisible}
        onCancel={() => setIsMarkdownEditModalVisible(false)}
        width={800}
        footer={[
          <Button key="cancel" onClick={() => setIsMarkdownEditModalVisible(false)}>
            取消
          </Button>,
          <Button key="save" type="primary" loading={isSavingPreview} onClick={async () => {
            if (!currentProject) return;
            setIsSavingPreview(true);
            try {
              await projectApi.updateProject(currentProject.id, {
                world_setting_markdown: editMarkdownContent,
                world_setting_format: 'markdown',
              });
              message.success('保存成功');
              setIsMarkdownEditModalVisible(false);
              // 刷新项目数据
              const updatedProject = await projectApi.getProject(currentProject.id);
              setCurrentProject(updatedProject);
            } catch (error) {
              message.error('保存失败');
            } finally {
              setIsSavingPreview(false);
            }
          }}>
            保存
          </Button>,
        ]}
      >
        <div style={{ marginBottom: 16 }}>
          <Typography.Text type="secondary">
            使用Markdown语法编辑世界设定内容。支持标题、表格、列表等格式。
          </Typography.Text>
        </div>
        <TextArea
          value={editMarkdownContent}
          onChange={(e) => setEditMarkdownContent(e.target.value)}
          rows={20}
          style={{ fontFamily: 'monospace', fontSize: 14 }}
          placeholder="# 世界观设定
## 基本信息
- 世界名称：xxx
- 作品规模：xxx

## 物理维度
### 空间架构
..."
        />
      </Modal>
    </div>
  );
}