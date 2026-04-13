import { useState, useEffect } from 'react';
import { Modal, Spin, Alert, Tabs, Card, Tag, List, Empty, Statistic, Row, Col, Button, theme, Table, Space } from 'antd';
import {
  ThunderboltOutlined,
  BulbOutlined,
  FireOutlined,
  HeartOutlined,
  TeamOutlined,
  TrophyOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
  EditOutlined,
  GiftOutlined
} from '@ant-design/icons';
import type { AnalysisTask, ChapterAnalysisResponse } from '../types';
import ChapterRegenerationModal from './ChapterRegenerationModal';
import ChapterContentComparison from './ChapterContentComparison';
import { itemApi } from '../services/api';

// 判断是否为移动设备
const isMobileDevice = () => window.innerWidth < 768;

interface ChapterAnalysisProps {
  chapterId: string;
  visible: boolean;
  onClose: () => void;
}

export default function ChapterAnalysis({ chapterId, visible, onClose }: ChapterAnalysisProps) {
  const { token } = theme.useToken();
  const [task, setTask] = useState<AnalysisTask | null>(null);
  const [analysis, setAnalysis] = useState<ChapterAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isMobile, setIsMobile] = useState(isMobileDevice());
  const [regenerationModalVisible, setRegenerationModalVisible] = useState(false);
  const [comparisonModalVisible, setComparisonModalVisible] = useState(false);
  const [chapterInfo, setChapterInfo] = useState<{ title: string; chapter_number: number; content: string } | null>(null);
  const [newGeneratedContent, setNewGeneratedContent] = useState('');
  const [newContentWordCount, setNewContentWordCount] = useState(0);

  // 章节物品相关状态
  const [chapterItems, setChapterItems] = useState<{
    items: any[];
    total: number;
    stats: {
      appeared_count: number;
      transfer_count: number;
      quantity_change_count: number;
      attribute_change_count: number;
    };
  } | null>(null);

  useEffect(() => {
    if (visible && chapterId) {
      fetchAnalysisStatus();
    }

    // 监听窗口大小变化
    const handleResize = () => {
      setIsMobile(isMobileDevice());
    };

    window.addEventListener('resize', handleResize);

    // 清理函数：组件卸载或关闭时清除轮询
    return () => {
      window.removeEventListener('resize', handleResize);
      // 清除可能存在的轮询
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible, chapterId]);

  // 🔧 新增：独立的章节信息加载函数
  const loadChapterInfo = async () => {
    try {
      const chapterResponse = await fetch(`/api/chapters/${chapterId}`);
      if (chapterResponse.ok) {
        const chapterData = await chapterResponse.json();
        setChapterInfo({
          title: chapterData.title,
          chapter_number: chapterData.chapter_number,
          content: chapterData.content || ''
        });
        console.log('✅ 已刷新章节内容，字数:', chapterData.content?.length || 0);
      }
    } catch (error) {
      console.error('❌ 加载章节信息失败:', error);
    }
  };

  const fetchAnalysisStatus = async () => {
    try {
      setLoading(true);
      setError(null);

      // 🔧 使用独立的章节加载函数
      await loadChapterInfo();

      const response = await fetch(`/api/chapters/${chapterId}/analysis/status`);

      if (response.status === 404) {
        setTask(null);
        setError('该章节还未进行分析');
        return;
      }

      if (!response.ok) {
        throw new Error('获取分析状态失败');
      }

      const taskData: AnalysisTask = await response.json();

      // 如果状态为 none（无任务），设置 task 为 null，让前端显示"开始分析"按钮
      if (taskData.status === 'none' || !taskData.has_task) {
        setTask(null);
        setError(null); // 清除错误，这不是错误状态
        return;
      }

      setTask(taskData);

      if (taskData.status === 'completed') {
        await fetchAnalysisResult();
      } else if (taskData.status === 'running' || taskData.status === 'pending') {
        // 开始轮询
        startPolling();
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const fetchAnalysisResult = async () => {
    try {
      const response = await fetch(`/api/chapters/${chapterId}/analysis`);
      if (!response.ok) {
        throw new Error('获取分析结果失败');
      }
      const data: ChapterAnalysisResponse = await response.json();
      setAnalysis(data);

      // 同时获取章节物品
      await fetchChapterItems();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const fetchChapterItems = async () => {
    try {
      const result = await itemApi.getChapterItems(chapterId);
      setChapterItems(result);
    } catch (err) {
      console.error('获取章节物品失败:', err);
      setChapterItems(null);
    }
  };

  const startPolling = () => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/chapters/${chapterId}/analysis/status`);
        if (!response.ok) return;

        const taskData: AnalysisTask = await response.json();
        setTask(taskData);

        if (taskData.status === 'completed') {
          clearInterval(pollInterval);
          await fetchAnalysisResult();
          // 🔧 分析完成后刷新章节内容，确保显示最新内容
          await loadChapterInfo();
        } else if (taskData.status === 'failed') {
          clearInterval(pollInterval);
          setError(taskData.error_message || '分析失败');
        }
      } catch (err) {
        console.error('轮询错误:', err);
      }
    }, 2000);

    // 5分钟超时
    setTimeout(() => clearInterval(pollInterval), 300000);
  };

  const triggerAnalysis = async () => {
    try {
      setLoading(true);
      setError(null);

      // 🔧 触发分析前先刷新章节内容，确保分析的是最新内容
      await loadChapterInfo();

      const response = await fetch(`/api/chapters/${chapterId}/analyze`, {
        method: 'POST'
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '触发分析失败');
      }

      // 触发成功后立即关闭Modal，让父组件的状态管理接管
      onClose();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };


  const renderStatusIcon = () => {
    if (!task) return null;

    switch (task.status) {
      case 'pending':
        return <ClockCircleOutlined style={{ color: 'var(--color-warning)' }} />;
      case 'running':
        return <Spin />;
      case 'completed':
        return <CheckCircleOutlined style={{ color: 'var(--color-success)' }} />;
      case 'failed':
        return <CloseCircleOutlined style={{ color: 'var(--color-error)' }} />;
      default:
        return null;
    }
  };

  const renderProgress = () => {
    if (!task || task.status === 'completed') return null;

    return (
      <div style={{
        padding: '40px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '300px'
      }}>
        {/* 标题和图标 */}
        <div style={{
          textAlign: 'center',
          marginBottom: 32
        }}>
          {renderStatusIcon()}
          <div style={{
            fontSize: 20,
            fontWeight: 'bold',
            marginTop: 16,
            color: task.status === 'failed' ? 'var(--color-error)' : 'var(--color-text-primary)'
          }}>
            {task.status === 'pending' && '等待分析...'}
            {task.status === 'running' && 'AI正在分析中...'}
            {task.status === 'failed' && '分析失败'}
          </div>
        </div>

        {/* 进度条 */}
        <div style={{
          width: '100%',
          maxWidth: '500px',
          marginBottom: 16
        }}>
          <div style={{
            height: 12,
            background: 'var(--color-bg-layout)',
            borderRadius: 6,
            overflow: 'hidden',
            marginBottom: 12
          }}>
            <div style={{
              height: '100%',
              background: task.status === 'failed'
                ? 'var(--color-error)'
                : task.progress === 100
                  ? 'var(--color-success)'
                  : 'var(--color-primary)',
              width: `${task.progress}%`,
              transition: 'all 0.3s ease',
              borderRadius: 6,
              boxShadow: task.progress > 0 && task.status !== 'failed'
                ? `0 0 10px color-mix(in srgb, ${token.colorPrimary} 30%, transparent)`
                : 'none'
            }} />
          </div>

          {/* 进度百分比 */}
          <div style={{
            textAlign: 'center',
            fontSize: 32,
            fontWeight: 'bold',
            color: task.status === 'failed' ? 'var(--color-error)' :
              task.progress === 100 ? 'var(--color-success)' : 'var(--color-primary)',
            marginBottom: 8
          }}>
            {task.progress}%
          </div>
        </div>

        {/* 状态消息 */}
        <div style={{
          textAlign: 'center',
          fontSize: 16,
          color: 'var(--color-text-secondary)',
          minHeight: 24,
          marginBottom: 16
        }}>
          {task.status === 'pending' && '分析任务已创建，正在队列中...'}
          {task.status === 'running' && '正在提取关键信息和记忆片段...'}
        </div>

        {/* 错误信息 */}
        {task.status === 'failed' && task.error_message && (
          <Alert
            message="分析失败"
            description={task.error_message}
            type="error"
            showIcon
            style={{
              marginTop: 16,
              maxWidth: '500px',
              width: '100%'
            }}
          />
        )}

        {/* 提示文字 */}
        {task.status !== 'failed' && (
          <div style={{
            textAlign: 'center',
            fontSize: 13,
            color: 'var(--color-text-tertiary)',
            marginTop: 16
          }}>
            分析过程需要一定时间，请耐心等待
          </div>
        )}
      </div>
    );
  };

  // 将分析建议转换为重新生成组件需要的格式
  // 包括：常规改进建议 + 字数超标的建议（从 consistency_issues 中提取）
  const convertSuggestionsForRegeneration = () => {
    const result: Array<{ category: string; content: string; priority: string }> = [];

    // 1. 添加常规改进建议
    if (analysis?.analysis?.suggestions) {
      analysis.analysis.suggestions.forEach((suggestion, index) => {
        result.push({
          category: '改进建议',
          content: suggestion,
          priority: index < 3 ? 'high' : 'medium'
        });
      });
    }

    // 2. 添加字数超标的建议（从 consistency_issues 提取）
    if (analysis?.analysis?.consistency_issues) {
      analysis.analysis.consistency_issues.forEach((issue) => {
        if (issue.type === 'word_count_overflow' && issue.suggestion) {
          result.push({
            category: '字数超标',
            content: issue.suggestion,
            priority: issue.severity
          });
        }
      });
    }

    return result;
  };

  const renderAnalysisResult = () => {
    if (!analysis) return null;

    const { analysis: analysis_data, memories } = analysis;

    return (
      <Tabs
        defaultActiveKey="overview"
        style={{ height: '100%' }}
        items={[
          {
            key: 'overview',
            label: '概览',
            icon: <TrophyOutlined />,
            children: (
              <div style={{ height: isMobile ? 'calc(80vh - 180px)' : 'calc(90vh - 220px)', overflowY: 'auto', paddingRight: '8px' }}>
                {/* 根据建议重新生成按钮 */}
                {(analysis_data.suggestions?.length > 0 ||
                  (analysis_data.consistency_issues?.some(i => i.type === 'word_count_overflow' && i.suggestion))) && (
                  <Alert
                    message="发现改进建议"
                    description={
                      <div>
                        <p style={{ marginBottom: 12 }}>
                          AI已分析出 {analysis_data.suggestions?.length || 0} 条改进建议，
                          {analysis_data.consistency_issues?.filter(i => i.type === 'word_count_overflow' && i.suggestion).length > 0 &&
                            ` 以及 ${analysis_data.consistency_issues.filter(i => i.type === 'word_count_overflow' && i.suggestion).length} 条字数超标建议`}
                          ，您可以根据这些建议重新生成章节内容。
                        </p>
                        <Button
                          type="primary"
                          icon={<EditOutlined />}
                          onClick={() => setRegenerationModalVisible(true)}
                          size={isMobile ? 'small' : 'middle'}
                        >
                          根据建议重新生成
                        </Button>
                      </div>
                    }
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                )}

                <Card title="整体评分" style={{ marginBottom: 16 }} size={isMobile ? 'small' : 'default'}>
                  <Row gutter={isMobile ? 8 : 16}>
                    <Col span={isMobile ? 12 : 6}>
                      <Statistic
                        title="整体质量"
                        value={analysis_data.overall_quality_score || 0}
                        suffix="/ 10"
                        valueStyle={{ color: 'var(--color-success)' }}
                      />
                    </Col>
                    <Col span={isMobile ? 12 : 6}>
                      <Statistic
                        title="节奏把控"
                        value={analysis_data.pacing_score || 0}
                        suffix="/ 10"
                      />
                    </Col>
                    <Col span={isMobile ? 12 : 6}>
                      <Statistic
                        title="吸引力"
                        value={analysis_data.engagement_score || 0}
                        suffix="/ 10"
                      />
                    </Col>
                    <Col span={isMobile ? 12 : 6}>
                      <Statistic
                        title="连贯性"
                        value={analysis_data.coherence_score || 0}
                        suffix="/ 10"
                      />
                    </Col>
                  </Row>
                  {/* 内容占比统计 */}
                  <Row gutter={isMobile ? 8 : 16} style={{ marginTop: 16 }}>
                    <Col span={isMobile ? 12 : 6}>
                      <Statistic
                        title="对话占比"
                        value={analysis_data.dialogue_ratio ? (analysis_data.dialogue_ratio * 100).toFixed(1) : 0}
                        suffix="%"
                      />
                    </Col>
                    <Col span={isMobile ? 12 : 6}>
                      <Statistic
                        title="描写占比"
                        value={analysis_data.description_ratio ? (analysis_data.description_ratio * 100).toFixed(1) : 0}
                        suffix="%"
                      />
                    </Col>
                    <Col span={isMobile ? 12 : 6}>
                      <Statistic
                        title="节奏类型"
                        value={
                          analysis_data.pacing === 'slow' ? '缓慢' :
                          analysis_data.pacing === 'moderate' ? '中速' :
                          analysis_data.pacing === 'fast' ? '快速' :
                          analysis_data.pacing === 'varied' ? '变化多样' :
                          '未知'
                        }
                      />
                    </Col>
                    <Col span={isMobile ? 12 : 6}>
                      <Statistic
                        title="情节点"
                        value={analysis_data.plot_points_count || 0}
                        suffix="个"
                      />
                    </Col>
                  </Row>
                </Card>

                {analysis_data.analysis_report && (
                  <Card title="分析摘要" style={{ marginBottom: 16 }} size={isMobile ? 'small' : 'default'}>
                    <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', fontSize: isMobile ? 13 : 14 }}>
                      {analysis_data.analysis_report}
                    </pre>
                  </Card>
                )}

                {(analysis_data.suggestions?.length > 0 ||
                  (analysis_data.consistency_issues?.some(i => i.type === 'word_count_overflow' && i.suggestion))) && (
                  <Card title={<><BulbOutlined /> 改进建议</>} size={isMobile ? 'small' : 'default'}>
                    <List
                      dataSource={[
                        // 常规建议
                        ...(analysis_data.suggestions || []).map((item, index) => ({
                          type: 'suggestion',
                          content: item,
                          index: index + 1
                        })),
                        // 字数超标建议
                        ...(analysis_data.consistency_issues || [])
                          .filter(i => i.type === 'word_count_overflow' && i.suggestion)
                          .map((issue, index) => ({
                            type: 'word_count_overflow',
                            content: issue.suggestion,
                            severity: issue.severity,
                            overflow_percent: issue.overflow_percent,
                            expected_value: issue.expected_value,
                            described_value: issue.described_value,
                            index: (analysis_data.suggestions?.length || 0) + index + 1
                          }))
                      ]}
                      renderItem={(item) => (
                        <List.Item>
                          <Space>
                            {item.type === 'word_count_overflow' ? (
                              <Tag color={item.severity === 'high' ? 'red' : item.severity === 'medium' ? 'orange' : 'blue'}>
                                字数超标 {item.overflow_percent && `+${item.overflow_percent}%`}
                              </Tag>
                            ) : (
                              <Tag color="green">建议</Tag>
                            )}
                            <span>{item.index}. {item.content}</span>
                          </Space>
                        </List.Item>
                      )}
                    />
                  </Card>
                )}
              </div>
            )
          },
          {
            key: 'hooks',
            label: `钩子 (${analysis_data.hooks?.length || 0})`,
            icon: <ThunderboltOutlined />,
            children: (
              <div style={{ height: isMobile ? 'calc(80vh - 180px)' : 'calc(90vh - 220px)', overflowY: 'auto', paddingRight: '8px' }}>
                <Card size={isMobile ? 'small' : 'default'}>
                  {analysis_data.hooks && analysis_data.hooks.length > 0 ? (
                    <List
                      dataSource={analysis_data.hooks}
                      renderItem={(hook) => (
                        <List.Item>
                          <List.Item.Meta
                            title={
                              <div>
                                <Tag color="blue">{hook.type}</Tag>
                                <Tag color="orange">{hook.position}</Tag>
                                <Tag color="red">强度: {hook.strength}/10</Tag>
                              </div>
                            }
                            description={hook.content}
                          />
                        </List.Item>
                      )}
                    />
                  ) : (
                    <Empty description="暂无钩子" />
                  )}
                </Card>
              </div>
            )
          },
          {
            key: 'foreshadows',
            label: `伏笔 (${analysis_data.foreshadows?.length || 0})`,
            icon: <FireOutlined />,
            children: (
              <div style={{ height: isMobile ? 'calc(80vh - 180px)' : 'calc(90vh - 220px)', overflowY: 'auto', paddingRight: '8px' }}>
                <Card size={isMobile ? 'small' : 'default'}>
                  {analysis_data.foreshadows && analysis_data.foreshadows.length > 0 ? (
                    <List
                      dataSource={analysis_data.foreshadows}
                      renderItem={(foreshadow) => (
                        <List.Item>
                          <List.Item.Meta
                            title={
                              <div>
                                <Tag color={foreshadow.type === 'planted' ? 'green' : 'purple'}>
                                  {foreshadow.type === 'planted' ? '已埋下' : '已回收'}
                                </Tag>
                                <Tag>强度: {foreshadow.strength}/10</Tag>
                                <Tag>隐藏度: {foreshadow.subtlety}/10</Tag>
                                {foreshadow.reference_chapter && (
                                  <Tag color="cyan">呼应第{foreshadow.reference_chapter}章</Tag>
                                )}
                              </div>
                            }
                            description={foreshadow.content}
                          />
                        </List.Item>
                      )}
                    />
                  ) : (
                    <Empty description="暂无伏笔" />
                  )}
                </Card>
              </div>
            )
          },
          {
            key: 'items',
            label: `物品 (${chapterItems?.total || 0})`,
            icon: <GiftOutlined />,
            children: (
              <div style={{ height: isMobile ? 'calc(80vh - 180px)' : 'calc(90vh - 220px)', overflowY: 'auto', paddingRight: '8px' }}>
                <Card size={isMobile ? 'small' : 'default'}>
                  {chapterItems && chapterItems.items.length > 0 ? (
                    <>
                      {/* 统计信息 */}
                      <Row gutter={isMobile ? 8 : 16} style={{ marginBottom: 16 }}>
                        <Col span={6}>
                          <Statistic
                            title="首次出现"
                            value={chapterItems.stats?.appeared_count || 0}
                            valueStyle={{ fontSize: 16 }}
                          />
                        </Col>
                        <Col span={6}>
                          <Statistic
                            title="流转事件"
                            value={chapterItems.stats?.transfer_count || 0}
                            valueStyle={{ fontSize: 16 }}
                          />
                        </Col>
                        <Col span={6}>
                          <Statistic
                            title="数量变更"
                            value={chapterItems.stats?.quantity_change_count || 0}
                            valueStyle={{ fontSize: 16 }}
                          />
                        </Col>
                        <Col span={6}>
                          <Statistic
                            title="属性变更"
                            value={chapterItems.stats?.attribute_change_count || 0}
                            valueStyle={{ fontSize: 16 }}
                          />
                        </Col>
                      </Row>

                      {/* 物品列表 */}
                      <Table
                        size="small"
                        dataSource={chapterItems.items}
                        rowKey="id"
                        pagination={chapterItems.items.length > 10 ? { pageSize: 10 } : false}
                        columns={[
                          {
                            title: '物品名称',
                            dataIndex: 'name',
                            key: 'name',
                            width: 150,
                            render: (name: string, record: any) => (
                              <span>
                                {name}
                                {record.is_plot_critical && (
                                  <Tag color="red" style={{ marginLeft: 4 }}>关键</Tag>
                                )}
                              </span>
                            )
                          },
                          {
                            title: '关联类型',
                            dataIndex: 'relation_type',
                            key: 'relation_type',
                            width: 100,
                            render: (type: string) => {
                              const colorMap: Record<string, string> = {
                                '首次出现': 'green',
                                '流转': 'blue',
                                '数量变更': 'orange',
                                '属性变更': 'purple',
                                '多次事件': 'cyan'
                              };
                              return <Tag color={colorMap[type] || 'default'}>{type}</Tag>;
                            }
                          },
                          {
                            title: '事件描述',
                            dataIndex: 'event_description',
                            key: 'event_description',
                            ellipsis: true
                          },
                          {
                            title: '稀有度',
                            dataIndex: 'rarity',
                            key: 'rarity',
                            width: 80,
                            render: (rarity: string) => {
                              const rarityMap: Record<string, { text: string; color: string }> = {
                                common: { text: '普通', color: 'default' },
                                uncommon: { text: '优秀', color: 'green' },
                                rare: { text: '稀有', color: 'blue' },
                                epic: { text: '史诗', color: 'purple' },
                                legendary: { text: '传说', color: 'gold' },
                                artifact: { text: '神器', color: 'red' },
                              };
                              const config = rarityMap[rarity];
                              return config ? <Tag color={config.color}>{config.text}</Tag> : '-';
                            }
                          },
                          {
                            title: '持有者',
                            dataIndex: 'owner_character_name',
                            key: 'owner_character_name',
                            width: 100,
                            render: (name: string) => name || '-'
                          },
                          {
                            title: '数量',
                            dataIndex: 'quantity',
                            key: 'quantity',
                            width: 80,
                            render: (qty: number, record: any) => `${qty} ${record.unit || '个'}`
                          },
                          {
                            title: '上下文优先级',
                            dataIndex: 'context_priority',
                            key: 'context_priority',
                            width: 100,
                            render: (priority: number) => {
                              // 注意：priority 可能是 0，不能用 !priority 判断
                              if (priority === undefined || priority === null) return '-';
                              const displayValue = priority.toFixed(1);
                              let color = 'green';
                              let text = '高';
                              // 优先级为 0 表示已消耗/销毁
                              if (priority === 0) {
                                color = 'red';
                                text = '已排除';
                              } else if (priority < 0.3) {
                                color = 'default';
                                text = '忽略';
                              } else if (priority < 0.5) {
                                color = 'orange';
                                text = '低';
                              } else if (priority < 0.8) {
                                color = 'blue';
                                text = '中';
                              }
                              return <Tag color={color}>{text} ({displayValue})</Tag>;
                            }
                          }
                        ]}
                      />
                    </>
                  ) : (
                    <Empty description="本章未发现相关物品" />
                  )}
                </Card>
              </div>
            )
          },
          {
            key: 'plotpoints',
            label: `情节点 (${analysis_data.plot_points?.length || 0})`,
            icon: <TrophyOutlined />,
            children: (
              <div style={{ height: isMobile ? 'calc(80vh - 180px)' : 'calc(90vh - 220px)', overflowY: 'auto', paddingRight: '8px' }}>
                <Card size={isMobile ? 'small' : 'default'}>
                  {analysis_data.plot_points && analysis_data.plot_points.length > 0 ? (
                    <List
                      dataSource={analysis_data.plot_points}
                      renderItem={(point) => (
                        <List.Item>
                          <List.Item.Meta
                            title={
                              <div>
                                <Tag color={
                                  point.type === 'revelation' ? 'purple' :
                                  point.type === 'conflict' ? 'red' :
                                  point.type === 'resolution' ? 'green' :
                                  'blue'
                                }>
                                  {point.type === 'revelation' ? '揭示' :
                                   point.type === 'conflict' ? '冲突' :
                                   point.type === 'resolution' ? '解决' :
                                   '过渡'}
                                </Tag>
                                <Tag color="orange">重要性: {(point.importance * 10).toFixed(1)}</Tag>
                              </div>
                            }
                            description={
                              <div>
                                <p style={{ marginBottom: 8 }}>{point.content}</p>
                                {point.impact && (
                                  <p style={{ color: token.colorTextSecondary, fontSize: 13 }}>
                                    <strong>影响：</strong>{point.impact}
                                  </p>
                                )}
                              </div>
                            }
                          />
                        </List.Item>
                      )}
                    />
                  ) : (
                    <Empty description="暂无情节点分析" />
                  )}
                </Card>
              </div>
            )
          },
          {
            key: 'scenes',
            label: `场景 (${analysis_data.scenes?.length || 0})`,
            icon: <GiftOutlined />,
            children: (
              <div style={{ height: isMobile ? 'calc(80vh - 180px)' : 'calc(90vh - 220px)', overflowY: 'auto', paddingRight: '8px' }}>
                <Card size={isMobile ? 'small' : 'default'}>
                  {analysis_data.scenes && analysis_data.scenes.length > 0 ? (
                    <List
                      dataSource={analysis_data.scenes}
                      renderItem={(scene) => (
                        <List.Item>
                          <Card type="inner" size="small" style={{ width: '100%' }}>
                            <Row gutter={16}>
                              <Col span={8}>
                                <Statistic title="地点" value={scene.location || '未知'} valueStyle={{ fontSize: 14 }} />
                              </Col>
                              <Col span={8}>
                                <Statistic title="氛围" value={scene.atmosphere || '未知'} valueStyle={{ fontSize: 14 }} />
                              </Col>
                              <Col span={8}>
                                <Statistic title="时长" value={scene.duration || '未知'} valueStyle={{ fontSize: 14 }} />
                              </Col>
                            </Row>
                          </Card>
                        </List.Item>
                      )}
                    />
                  ) : (
                    <Empty description="暂无场景分析" />
                  )}
                </Card>
              </div>
            )
          },
          {
            key: 'emotion',
            label: '情感曲线',
            icon: <HeartOutlined />,
            children: (
              <div style={{ height: isMobile ? 'calc(80vh - 180px)' : 'calc(90vh - 220px)', overflowY: 'auto', paddingRight: '8px' }}>
                <Card size={isMobile ? 'small' : 'default'}>
                  {analysis_data.emotional_tone ? (
                    <div>
                      <Row gutter={isMobile ? 8 : 16} style={{ marginBottom: isMobile ? 16 : 24 }}>
                        <Col span={isMobile ? 24 : 12}>
                          <Statistic
                            title="主导情绪"
                            value={analysis_data.emotional_tone}
                          />
                        </Col>
                        <Col span={isMobile ? 24 : 12}>
                          <Statistic
                            title="情感强度"
                            value={(analysis_data.emotional_intensity * 10).toFixed(1)}
                            suffix="/ 10"
                          />
                        </Col>
                      </Row>
                      <Card type="inner" title="剧情阶段" size="small">
                        <p><strong>阶段：</strong>{analysis_data.plot_stage}</p>
                        <p><strong>冲突等级：</strong>{analysis_data.conflict_level} / 10</p>
                        {analysis_data.conflict_types && analysis_data.conflict_types.length > 0 && (
                          <div style={{ marginTop: 8 }}>
                            <strong>冲突类型：</strong>
                            {analysis_data.conflict_types.map((type, idx) => (
                              <Tag key={idx} color="red" style={{ margin: 4 }}>
                                {type}
                              </Tag>
                            ))}
                          </div>
                        )}
                      </Card>
                      {/* 情感曲线 */}
                      {analysis_data.emotional_curve && (
                        <Card type="inner" title="情感曲线" size="small" style={{ marginTop: 16 }}>
                          <Row gutter={16}>
                            <Col span={8}>
                              <Statistic
                                title="开头"
                                value={analysis_data.emotional_curve.start ? (analysis_data.emotional_curve.start * 10).toFixed(1) : '-'}
                                suffix="/ 10"
                              />
                            </Col>
                            <Col span={8}>
                              <Statistic
                                title="中段"
                                value={analysis_data.emotional_curve.middle ? (analysis_data.emotional_curve.middle * 10).toFixed(1) : '-'}
                                suffix="/ 10"
                              />
                            </Col>
                            <Col span={8}>
                              <Statistic
                                title="结尾"
                                value={analysis_data.emotional_curve.end ? (analysis_data.emotional_curve.end * 10).toFixed(1) : '-'}
                                suffix="/ 10"
                              />
                            </Col>
                          </Row>
                          <div style={{ marginTop: 12, fontSize: 13, color: token.colorTextSecondary }}>
                            💡 情感曲线反映了章节从开头到结尾的情感强度变化趋势
                          </div>
                        </Card>
                      )}
                    </div>
                  ) : (
                    <Empty description="暂无情感分析" />
                  )}
                </Card>
              </div>
            )
          },
          {
            key: 'characters',
            label: `角色 (${analysis_data.character_states?.length || 0})`,
            icon: <TeamOutlined />,
            children: (
              <div style={{ height: isMobile ? 'calc(80vh - 180px)' : 'calc(90vh - 220px)', overflowY: 'auto', paddingRight: '8px' }}>
                <Card size={isMobile ? 'small' : 'default'}>
                  {analysis_data.character_states && analysis_data.character_states.length > 0 ? (
                    <List
                      dataSource={analysis_data.character_states}
                      renderItem={(char) => (
                        <List.Item>
                          <Card
                            type="inner"
                            title={char.character_name}
                            size="small"
                            style={{ width: '100%' }}
                          >
                            <p><strong>状态变化：</strong>{char.state_before} → {char.state_after}</p>
                            <p><strong>心理变化：</strong>{char.psychological_change}</p>
                            <p><strong>关键事件：</strong>{char.key_event}</p>
                            {char.relationship_changes && Object.keys(char.relationship_changes).length > 0 && (
                              <div>
                                <strong>关系变化：</strong>
                                {Object.entries(char.relationship_changes).map(([name, change]) => (
                                  <Tag key={name} color="blue" style={{ margin: 4 }}>
                                    与{name}: {change}
                                  </Tag>
                                ))}
                              </div>
                            )}
                          </Card>
                        </List.Item>
                      )}
                    />
                  ) : (
                    <Empty description="暂无角色分析" />
                  )}
                </Card>
              </div>
            )
          },
          {
            key: 'memories',
            label: `记忆 (${memories?.length || 0})`,
            icon: <FireOutlined />,
            children: (
              <div style={{ height: isMobile ? 'calc(80vh - 180px)' : 'calc(90vh - 220px)', overflowY: 'auto', paddingRight: '8px' }}>
                <Card size={isMobile ? 'small' : 'default'}>
                  {memories && memories.length > 0 ? (
                    <List
                      dataSource={memories}
                      renderItem={(memory) => (
                        <List.Item>
                          <List.Item.Meta
                            title={
                              <div>
                                <Tag color="blue">{memory.type}</Tag>
                                <Tag color="orange">重要性: {memory.importance.toFixed(1)}</Tag>
                                {memory.is_foreshadow === 1 && <Tag color="green">已埋下伏笔</Tag>}
                                {memory.is_foreshadow === 2 && <Tag color="purple">已回收伏笔</Tag>}
                                <span style={{ marginLeft: 8 }}>{memory.title}</span>
                              </div>
                            }
                            description={
                              <div>
                                <p>{memory.content}</p>
                                <div>
                                  {memory.tags.map((tag, idx) => (
                                    <Tag key={idx} style={{ margin: 2 }}>{tag}</Tag>
                                  ))}
                                </div>
                              </div>
                            }
                          />
                        </List.Item>
                      )}
                    />
                  ) : (
                    <Empty description="暂无记忆片段" />
                  )}
                </Card>
              </div>
            )
          }
        ]}
      />
    );
  };

  return (
    <Modal
      title="章节分析"
      open={visible}
      onCancel={onClose}
      width={isMobile ? 'calc(100vw - 32px)' : '90%'}
      centered
      style={{
        maxWidth: isMobile ? 'calc(100vw - 32px)' : '1400px',
        margin: isMobile ? '0 auto' : undefined,
        padding: isMobile ? '0 16px' : undefined
      }}
      styles={{
        body: {
          padding: isMobile ? '12px' : '24px',
          paddingBottom: 0
        }
      }}
      footer={[
        <Button key="close" onClick={onClose} size={isMobile ? 'small' : 'middle'}>
          关闭
        </Button>,
        !task && !loading && (
          <Button
            key="analyze"
            type="primary"
            icon={<ReloadOutlined />}
            onClick={triggerAnalysis}
            loading={loading}
            size={isMobile ? 'small' : 'middle'}
          >
            开始分析
          </Button>
        ),
        task && (task.status === 'failed') && (
          <Button
            key="reanalyze"
            type="primary"
            icon={<ReloadOutlined />}
            onClick={triggerAnalysis}
            loading={loading}
            danger
            size={isMobile ? 'small' : 'middle'}
          >
            重新分析
          </Button>
        ),
        task && task.status === 'completed' && (
          <Button
            key="reanalyze"
            type="default"
            icon={<ReloadOutlined />}
            onClick={triggerAnalysis}
            loading={loading}
            size={isMobile ? 'small' : 'middle'}
          >
            重新分析
          </Button>
        )
      ].filter(Boolean)}
    >
      {loading && !task && (
        <div style={{ textAlign: 'center', padding: '48px' }}>
          <Spin size="large" />
          <p style={{ marginTop: 16 }}>加载中...</p>
        </div>
      )}

      {error && (
        <Alert
          message="错误"
          description={error}
          type="error"
          showIcon
        />
      )}

      {task && task.status !== 'completed' && renderProgress()}
      {task && task.status === 'completed' && analysis && renderAnalysisResult()}

      {/* 重新生成Modal */}
      {chapterInfo && (
        <ChapterRegenerationModal
          visible={regenerationModalVisible}
          onCancel={() => setRegenerationModalVisible(false)}
          onSuccess={(newContent: string, wordCount: number) => {
            // 保存新生成的内容
            setNewGeneratedContent(newContent);
            setNewContentWordCount(wordCount);
            // 关闭重新生成对话框
            setRegenerationModalVisible(false);
            // 打开对比界面
            setComparisonModalVisible(true);
          }}
          chapterId={chapterId}
          chapterTitle={chapterInfo.title}
          chapterNumber={chapterInfo.chapter_number}
          suggestions={convertSuggestionsForRegeneration()}
          hasAnalysis={true}
          analysisScores={analysis?.analysis ? {
            pacing_score: analysis.analysis.pacing_score,
            engagement_score: analysis.analysis.engagement_score,
            coherence_score: analysis.analysis.coherence_score,
            overall_quality_score: analysis.analysis.overall_quality_score
          } : undefined}
        />
      )}

      {/* 内容对比组件 */}
      {chapterInfo && comparisonModalVisible && (
        <ChapterContentComparison
          visible={comparisonModalVisible}
          onClose={() => setComparisonModalVisible(false)}
          chapterId={chapterId}
          chapterTitle={chapterInfo.title}
          originalContent={chapterInfo.content}
          newContent={newGeneratedContent}
          wordCount={newContentWordCount}
          onApply={async () => {
            // 应用新内容后刷新章节信息和分析
            setChapterInfo(null);
            setAnalysis(null);

            // 重新加载章节内容
            try {
              const chapterResponse = await fetch(`/api/chapters/${chapterId}`);
              if (chapterResponse.ok) {
                const chapterData = await chapterResponse.json();
                setChapterInfo({
                  title: chapterData.title,
                  chapter_number: chapterData.chapter_number,
                  content: chapterData.content || ''
                });
              }
            } catch (error) {
              console.error('重新加载章节失败:', error);
            }

            // 刷新分析状态
            await fetchAnalysisStatus();
          }}
          onDiscard={() => {
            // 放弃新内容，清空状态
            setNewGeneratedContent('');
            setNewContentWordCount(0);
          }}
        />
      )}
    </Modal>
  );
}