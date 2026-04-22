import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Button, Space, Typography, Progress, App, Tag, Input, Divider, Collapse, theme } from 'antd';
import { CheckCircleOutlined, LoadingOutlined, EditOutlined, SaveOutlined, ExpandOutlined, CompressOutlined, UndoOutlined, GlobalOutlined, CompassOutlined, ThunderboltOutlined, TeamOutlined, BulbOutlined, SyncOutlined, InfoCircleOutlined, EnvironmentOutlined, ClockCircleOutlined, SmileOutlined, BookOutlined, CrownOutlined, UserOutlined, StarOutlined, ToolOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { wizardStreamApi } from '../services/api';
import type { ApiError } from '../types';

const { Title, Paragraph, Text } = Typography;
const { TextArea } = Input;

// 章节标题图标映射（同层级使用相同图标）
const sectionIcons: Record<string, React.ReactNode> = {
  // 总标题
  '世界观设定': <GlobalOutlined />,
  // 一级标题（各维度）
  '基本信息': <InfoCircleOutlined />,       // 一、基本信息
  '物理维度': <ThunderboltOutlined />,      // 二、物理维度
  '社会维度': <TeamOutlined />,             // 三、社会维度
  '隐喻维度': <BulbOutlined />,             // 四、隐喻维度
  '交互维度': <SyncOutlined />,             // 五、交互维度
  '世界概述': <BookOutlined />,             // 六、世界概述
  // 二级标题 - 物理维度下（统一使用 CompassOutlined）
  '空间架构': <CompassOutlined />,          // 2.1
  '时间架构': <CompassOutlined />,          // 2.2
  '力量体系': <CompassOutlined />,          // 2.3
  '物品体系': <CompassOutlined />,          // 2.4
  // 二级标题 - 社会维度下（统一使用 TeamOutlined）
  '权力结构': <TeamOutlined />,             // 3.1
  '经济体系': <TeamOutlined />,             // 3.2
  '文化体系': <TeamOutlined />,             // 3.3
  '组织体系': <TeamOutlined />,             // 3.4
  // 二级标题 - 世界概述下（统一使用 EnvironmentOutlined）
  '时间背景': <ClockCircleOutlined />,      // 6.1
  '地理环境': <EnvironmentOutlined />,      // 6.2
  '氛围基调': <SmileOutlined />,            // 6.3
  '世界法则': <ThunderboltOutlined />,      // 6.4
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

// 自定义Markdown渲染组件
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

const MarkdownParagraph: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <Paragraph style={{ margin: '0 0 12px 0', lineHeight: 1.6 }}>
    {children}
  </Paragraph>
);

const MarkdownList: React.FC<{ children: React.ReactNode; ordered?: boolean }> = ({ children }) => (
  <div style={{
    margin: '0 0 12px 0',
    paddingLeft: 20,
    lineHeight: 1.6,
  }}>
    {children}
  </div>
);

const MarkdownListItem: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ margin: '4px 0', position: 'relative' }}>
    <span style={{ position: 'absolute', left: -16, color: 'var(--color-primary)' }}>•</span>
    {children}
  </div>
);

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

const MarkdownTableRow: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <tr style={{
    borderBottom: '1px solid var(--color-border)',
  }}>
    {children}
  </tr>
);

const MarkdownTableHead: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <thead style={{
    background: 'var(--color-primary-bg)',
  }}>
    {children}
  </thead>
);

const MarkdownTableBody: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <tbody>
    {children}
  </tbody>
);

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

// ==================== 职业体系渲染组件 ====================

// 职业阶段接口
interface CareerStage {
  level: number;
  name: string;
  description: string;
}

// 职业接口
interface CareerData {
  name: string;
  description: string;
  category?: string;
  stages?: CareerStage[];
  max_stage?: number;
  requirements?: string;
  special_abilities?: string;
  worldview_rules?: string;
  base_attributes?: Record<string, number>;
  per_stage_bonus?: Record<string, { per_stage?: number }>;
}

// 职业体系数据接口
interface CareerSystemData {
  main_careers?: CareerData[];
  sub_careers?: CareerData[];
  main_careers_created?: CareerData[];
  sub_careers_created?: CareerData[];
  main_careers_count?: number;
  sub_careers_count?: number;
}

// 单个职业卡片渲染组件
const CareerCard: React.FC<{ career: CareerData; type: 'main' | 'sub' }> = ({ career, type }) => {
  const [stagesExpanded, setStagesExpanded] = useState(false);
  const { token } = theme.useToken();

  const categoryColors: Record<string, string> = {
    '生存发展型': 'blue',
    '智慧机缘型': 'purple',
    '战斗攻坚型': 'red',
    '智慧探索型': 'cyan',
    '极致战斗型': 'volcano',
    '特殊成长型': 'gold',
    '生产系': 'green',
    '辅助系': 'orange',
    '资源获取系': 'lime',
    '情报策略系': 'geekblue',
  };

  const getCategoryColor = (category?: string): string => {
    if (!category) return 'default';
    for (const [key, color] of Object.entries(categoryColors)) {
      if (category.includes(key)) return color;
    }
    return 'default';
  };

  return (
    <Card
      size="small"
      style={{
        marginBottom: 16,
        border: type === 'main'
          ? `2px solid ${token.colorPrimary}`
          : `1px solid ${token.colorBorder}`,
        background: type === 'main' ? token.colorPrimaryBg : 'transparent',
      }}
      styles={{ body: { padding: '12px 16px' } }}
    >
      {/* 职业标题 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        {type === 'main' ? (
          <CrownOutlined style={{ color: token.colorPrimary, fontSize: 18 }} />
        ) : (
          <ToolOutlined style={{ color: token.colorTextSecondary, fontSize: 16 }} />
        )}
        <Text strong style={{ fontSize: 16 }}>{career.name}</Text>
        {career.category && (
          <Tag color={getCategoryColor(career.category)} style={{ marginLeft: 8 }}>
            {career.category}
          </Tag>
        )}
      </div>

      {/* 职业描述 */}
      {career.description && (
        <Paragraph style={{ marginBottom: 12, color: token.colorTextSecondary, lineHeight: 1.6 }}>
          {career.description}
        </Paragraph>
      )}

      {/* 基础属性 */}
      {career.base_attributes && Object.keys(career.base_attributes).length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <Text type="secondary" style={{ fontSize: 13, marginBottom: 4, display: 'block' }}>
            <StarOutlined style={{ marginRight: 4 }} />基础属性
          </Text>
          <Space wrap size={[4, 4]}>
            {Object.entries(career.base_attributes).map(([attr, value]) => (
              <Tag key={attr} style={{ margin: 0 }}>
                {attr}: {value}
              </Tag>
            ))}
            {career.per_stage_bonus && Object.entries(career.per_stage_bonus).map(([attr, bonus]) => (
              bonus.per_stage && (
                <Tag key={`${attr}-bonus`} color="green" style={{ margin: 0 }}>
                  {attr}每阶段+{bonus.per_stage}
                </Tag>
              )
            ))}
          </Space>
        </div>
      )}

      {/* 入门要求 */}
      {career.requirements && (
        <div style={{ marginBottom: 12, padding: '8px 12px', background: token.colorBgLayout, borderRadius: 6 }}>
          <Text type="secondary" style={{ fontSize: 13 }}>
            <InfoCircleOutlined style={{ marginRight: 4 }} />入门要求：
          </Text>
          <Text style={{ marginLeft: 8 }}>{career.requirements}</Text>
        </div>
      )}

      {/* 特殊能力 */}
      {career.special_abilities && (
        <div style={{ marginBottom: 12 }}>
          <Text type="secondary" style={{ fontSize: 13, marginBottom: 4, display: 'block' }}>
            <ThunderboltOutlined style={{ marginRight: 4 }} />特殊能力
          </Text>
          <div style={{
            padding: '8px 12px',
            background: token.colorInfoBg,
            borderRadius: 6,
            border: `1px solid ${token.colorInfoBorder}`,
            whiteSpace: 'pre-wrap',
            lineHeight: 1.6,
          }}>
            {career.special_abilities}
          </div>
        </div>
      )}

      {/* 世界观规则 */}
      {career.worldview_rules && (
        <div style={{ marginBottom: 12 }}>
          <Text type="secondary" style={{ fontSize: 13, marginBottom: 4, display: 'block' }}>
            <GlobalOutlined style={{ marginRight: 4 }} />世界观关联
          </Text>
          <div style={{
            padding: '8px 12px',
            background: token.colorWarningBg,
            borderRadius: 6,
            border: `1px solid ${token.colorWarningBorder}`,
            whiteSpace: 'pre-wrap',
            lineHeight: 1.6,
            fontSize: 13,
          }}>
            {career.worldview_rules}
          </div>
        </div>
      )}

      {/* 阶段列表 */}
      {career.stages && career.stages.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <Button
            type="link"
            size="small"
            onClick={() => setStagesExpanded(!stagesExpanded)}
            icon={stagesExpanded ? <CompressOutlined /> : <ExpandOutlined />}
            style={{ marginBottom: 8 }}
          >
            {stagesExpanded ? '收起阶段详情' : `展开 ${career.stages.length} 个阶段`}
          </Button>

          {stagesExpanded && (
            <Collapse
              size="small"
              items={career.stages.map((stage, index) => ({
                key: index.toString(),
                label: (
                  <Space>
                    <Tag color={token.colorPrimary}>{stage.level}</Tag>
                    <Text strong>{stage.name}</Text>
                  </Space>
                ),
                children: (
                  <Text style={{ lineHeight: 1.6 }}>{stage.description}</Text>
                ),
              }))}
              style={{ background: token.colorBgLayout }}
            />
          )}
        </div>
      )}
    </Card>
  );
};

// 职业体系渲染组件
const CareerSystemRenderer: React.FC<{ content: string; incrementalData?: any[]; isProcessing?: boolean }> = ({ content, incrementalData, isProcessing }) => {
  const { token } = theme.useToken();

  // 清洗并解析 JSON
  const parseCareerData = (text: string): CareerSystemData | null => {
    try {
      // 如果是占位符文本或空内容，直接返回 null
      if (!text || text.trim() === '' || text.includes('等待生成') || text.includes('正在生成')) {
        return null;
      }

      // 清洗 JSON
      let cleanContent = text;

      // 去除 markdown 代码块标记
      cleanContent = cleanContent.replace(/^```json\s*\n?/gi, '');
      cleanContent = cleanContent.replace(/^```\s*\n?/g, '');
      cleanContent = cleanContent.replace(/\n?```\s*$/g, '');
      cleanContent = cleanContent.trim();

      // 如果清洗后不是以 { 开头，说明不是有效 JSON
      if (!cleanContent.startsWith('{')) {
        return null;
      }

      // 规范化中文引号
      cleanContent = cleanContent.replace(/[""]([^""]+)[""]\s*:/g, '"$1":');
      cleanContent = cleanContent.replace(/:\s*[""]([^""]*)[""]/g, ': "$1"');
      cleanContent = cleanContent.replace(/\[\s*[""]([^""]*)[""]/g, '[ "$1"');
      cleanContent = cleanContent.replace(/[""]([^""]*)[""]\s*\]/g, '"$1" ]');
      cleanContent = cleanContent.replace(/[""]/g, '"');

      return JSON.parse(cleanContent);
    } catch (e) {
      // 不打印错误日志，避免控制台污染
      return null;
    }
  };

  // 如果有增量数据，渲染职业列表（使用 _careerType 区分主/副）
  if (incrementalData && incrementalData.length > 0) {
    const mainCareersFromIncremental = incrementalData.filter(c => c._careerType === 'main');
    const subCareersFromIncremental = incrementalData.filter(c => c._careerType === 'sub');
    const unknownCareers = incrementalData.filter(c => !c._careerType);

    return (
      <div>
        {/* 主职业 */}
        {mainCareersFromIncremental.length > 0 && (
          <div style={{ marginBottom: 24 }}>
            <Divider orientation="left" style={{ marginBottom: 16 }}>
              <Space>
                <CrownOutlined style={{ color: token.colorPrimary }} />
                <Text strong style={{ fontSize: 16 }}>主职业体系</Text>
                <Tag color="processing">{mainCareersFromIncremental.length} 个（正在生成...）</Tag>
              </Space>
            </Divider>
            {mainCareersFromIncremental.map((career, index) => (
              <CareerCard key={`main-${index}`} career={career} type="main" />
            ))}
          </div>
        )}

        {/* 副职业 */}
        {subCareersFromIncremental.length > 0 && (
          <div style={{ marginBottom: 24 }}>
            <Divider orientation="left" style={{ marginBottom: 16 }}>
              <Space>
                <UserOutlined style={{ color: token.colorTextSecondary }} />
                <Text strong style={{ fontSize: 16 }}>副职业体系</Text>
                <Tag color="processing">{subCareersFromIncremental.length} 个（正在生成...）</Tag>
              </Space>
            </Divider>
            {subCareersFromIncremental.map((career, index) => (
              <CareerCard key={`sub-${index}`} career={career} type="sub" />
            ))}
          </div>
        )}

        {/* 未分类职业（fallback） */}
        {unknownCareers.length > 0 && (
          <div style={{ marginBottom: 24 }}>
            <Divider orientation="left" style={{ marginBottom: 16 }}>
              <Space>
                <CrownOutlined style={{ color: token.colorPrimary }} />
                <Text strong style={{ fontSize: 16 }}>职业体系</Text>
                <Tag color="processing">{unknownCareers.length} 个（正在生成...）</Tag>
              </Space>
            </Divider>
            {unknownCareers.map((career, index) => (
              <CareerCard key={`unknown-${index}`} career={career} type="main" />
            ))}
          </div>
        )}
      </div>
    );
  }

  // 没有增量数据时，解析完整内容
  const careerData = parseCareerData(content);

  // 处理中状态但没有增量数据时，显示解析提示
  if (isProcessing && !careerData) {
    return (
      <div style={{ textAlign: 'center', padding: 20 }}>
        <LoadingOutlined style={{ fontSize: 24, color: token.colorPrimary }} />
        <Paragraph style={{ marginTop: 12, color: token.colorTextSecondary }}>
          正在解析职业体系数据...
        </Paragraph>
      </div>
    );
  }

  if (!careerData) {
    // 解析失败，显示原始内容
    return (
      <div style={{
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
        fontFamily: 'ui-monospace, monospace',
        fontSize: 14,
        lineHeight: 1.6,
      }}>
        {content || '等待生成...'}
      </div>
    );
  }

  // 获取职业列表
  const mainCareers = careerData.main_careers || careerData.main_careers_created || [];
  const subCareers = careerData.sub_careers || careerData.sub_careers_created || [];

  return (
    <div>
      {/* 主职业 */}
      {mainCareers.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <Divider orientation="left" style={{ marginBottom: 16 }}>
            <Space>
              <CrownOutlined style={{ color: token.colorPrimary }} />
              <Text strong style={{ fontSize: 16 }}>主职业体系</Text>
              <Tag color="blue">{mainCareers.length} 个</Tag>
            </Space>
          </Divider>
          {mainCareers.map((career, index) => (
            <CareerCard key={index} career={career} type="main" />
          ))}
        </div>
      )}

      {/* 副职业 */}
      {subCareers.length > 0 && (
        <div>
          <Divider orientation="left" style={{ marginBottom: 16 }}>
            <Space>
              <UserOutlined style={{ color: token.colorTextSecondary }} />
              <Text strong style={{ fontSize: 16 }}>副职业体系</Text>
              <Tag color="orange">{subCareers.length} 个</Tag>
            </Space>
          </Divider>
          {subCareers.map((career, index) => (
            <CareerCard key={index} career={career} type="sub" />
          ))}
        </div>
      )}

      {/* 没有职业数据时显示统计 */}
      {mainCareers.length === 0 && subCareers.length === 0 && (careerData.main_careers_count || careerData.sub_careers_count) && (
        <div style={{ textAlign: 'center', padding: 20 }}>
          <CheckCircleOutlined style={{ fontSize: 32, color: token.colorSuccess }} />
          <Paragraph style={{ marginTop: 12 }}>
            职业体系生成完成
          </Paragraph>
          <Space>
            {careerData.main_careers_count && (
              <Tag color="blue">主职业 {careerData.main_careers_count} 个</Tag>
            )}
            {careerData.sub_careers_count && (
              <Tag color="orange">副职业 {careerData.sub_careers_count} 个</Tag>
            )}
          </Space>
        </div>
      )}
    </div>
  );
};

// ==================== 角色渲染组件 ====================

// 角色类型翻译映射（组件外部定义）
const roleTypeMap: Record<string, string> = {
  protagonist: '主角',
  antagonist: '反派',
  supporting: '配角',
  minor: '次要角色',
};

// 角色数据接口
interface CharacterData {
  name: string;
  role_type?: string;
  personality?: string;
  background?: string;
  appearance?: string;
}

// 角色体系渲染组件
const CharacterSystemRenderer: React.FC<{ content: string; incrementalData?: any[]; isProcessing?: boolean }> = ({ content, incrementalData, isProcessing }) => {
  const { token } = theme.useToken();

  // 清洗并解析 JSON
  const parseCharacterData = (text: string): CharacterData[] | null => {
    try {
      // 清洗 JSON
      let cleanContent = text;

      // 去除 markdown 代码块标记
      cleanContent = cleanContent.replace(/^```json\s*\n?/gi, '');
      cleanContent = cleanContent.replace(/^```\s*\n?/g, '');
      cleanContent = cleanContent.replace(/\n?```\s*$/g, '');
      cleanContent = cleanContent.trim();

      // 规范化中文引号
      cleanContent = cleanContent.replace(/[""]([^""]+)[""]\s*:/g, '"$1":');
      cleanContent = cleanContent.replace(/:\s*[""]([^""]*)[""]/g, ': "$1"');
      cleanContent = cleanContent.replace(/\[\s*[""]([^""]*)[""]/g, '[ "$1"');
      cleanContent = cleanContent.replace(/[""]([^""]*)[""]\s*\]/g, '"$1" ]');
      cleanContent = cleanContent.replace(/[""]/g, '"');

      const parsed = JSON.parse(cleanContent);
      // 处理不同的数据结构
      if (Array.isArray(parsed)) return parsed;
      if (parsed.characters) return parsed.characters;
      if (parsed.created_characters) return parsed.created_characters;
      return null;
    } catch (e) {
      console.error('角色 JSON 解析失败:', e);
      return null;
    }
  };

  const roleTypeColors: Record<string, string> = {
    protagonist: 'blue',
    antagonist: 'red',
    supporting: 'green',
    minor: 'default',
  };

  // 优先使用增量数据渲染
  if (incrementalData && incrementalData.length > 0) {
    return (
      <div>
        <Divider orientation="left" style={{ marginBottom: 16 }}>
          <Space>
            <TeamOutlined style={{ color: token.colorPrimary }} />
            <Text strong style={{ fontSize: 16 }}>角色设定</Text>
            <Tag color="processing">{incrementalData.length} 个（正在生成...）</Tag>
          </Space>
        </Divider>
        {incrementalData.map((char, index) => (
          <Card
            key={index}
            size="small"
            style={{ marginBottom: 12 }}
            styles={{ body: { padding: '12px 16px' } }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <UserOutlined style={{ color: token.colorPrimary }} />
              <Text strong style={{ fontSize: 15 }}>{char.name}</Text>
              {char.role_type && (
                <Tag color={roleTypeColors[char.role_type] || 'default'}>
                  {roleTypeMap[char.role_type] || char.role_type}
                </Tag>
              )}
              {char.is_organization && (
                <Tag color="orange">组织</Tag>
              )}
            </div>

            {char.appearance && (
              <Paragraph style={{ marginBottom: 8, color: token.colorTextSecondary }}>
                👤 外貌：{char.appearance}
              </Paragraph>
            )}

            {char.personality && (
              <Paragraph style={{ marginBottom: 8, color: token.colorTextSecondary }}>
                💭 性格：{char.personality}
              </Paragraph>
            )}

            {char.background && (
              <Paragraph style={{ marginBottom: 0, color: token.colorTextSecondary }}>
                📖 背景：{char.background}
              </Paragraph>
            )}
          </Card>
        ))}
      </div>
    );
  }

  // 处理中状态但没有增量数据时，显示解析提示
  if (isProcessing) {
    return (
      <div style={{ textAlign: 'center', padding: 20 }}>
        <LoadingOutlined style={{ fontSize: 24, color: token.colorPrimary }} />
        <Paragraph style={{ marginTop: 12, color: token.colorTextSecondary }}>
          正在解析角色数据...
        </Paragraph>
      </div>
    );
  }

  // 没有增量数据时，解析完整内容
  const characters = parseCharacterData(content);

  if (!characters || characters.length === 0) {
    return (
      <div style={{
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
        fontFamily: 'ui-monospace, monospace',
        fontSize: 14,
        lineHeight: 1.6,
      }}>
        {content || '等待生成...'}
      </div>
    );
  }

  return (
    <div>
      {characters.map((char, index) => (
        <Card
          key={index}
          size="small"
          style={{ marginBottom: 12 }}
          styles={{ body: { padding: '12px 16px' } }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <UserOutlined style={{ color: token.colorPrimary }} />
            <Text strong style={{ fontSize: 15 }}>{char.name}</Text>
            {char.role_type && (
              <Tag color={roleTypeColors[char.role_type] || 'default'}>
                {roleTypeMap[char.role_type] || char.role_type}
              </Tag>
            )}
          </div>

          {char.appearance && (
            <Paragraph style={{ marginBottom: 8, color: token.colorTextSecondary }}>
              👤 外貌：{char.appearance}
            </Paragraph>
          )}

          {char.personality && (
            <Paragraph style={{ marginBottom: 8, color: token.colorTextSecondary }}>
              💭 性格：{char.personality}
            </Paragraph>
          )}

          {char.background && (
            <Paragraph style={{ marginBottom: 0, color: token.colorTextSecondary }}>
              📖 背景：{char.background}
            </Paragraph>
          )}
        </Card>
      ))}
    </div>
  );
};

// ==================== 大纲渲染组件 ====================

// 大纲数据接口
interface OutlineData {
  chapter_number?: number;
  title?: string;
  summary?: string;
  content?: string;
  emotion?: string;
  goal?: string;
  scenes?: string[];
  key_points?: string[];
  characters?: (string | { name: string; type?: string })[];
}

// 大纲体系渲染组件
const OutlineSystemRenderer: React.FC<{ content: string; incrementalData?: any[]; isProcessing?: boolean }> = ({ content, incrementalData, isProcessing }) => {
  const { token } = theme.useToken();

  // 清洗并解析 JSON
  const parseOutlineData = (text: string): OutlineData[] | null => {
    try {
      // 如果是占位符文本或空内容，直接返回 null
      if (!text || text.trim() === '' || text.includes('等待生成') || text.includes('正在生成')) {
        return null;
      }

      // 清洗 JSON
      let cleanContent = text;

      // 去除 markdown 代码块标记
      cleanContent = cleanContent.replace(/^```json\s*\n?/gi, '');
      cleanContent = cleanContent.replace(/^```\s*\n?/g, '');
      cleanContent = cleanContent.replace(/\n?```\s*$/g, '');
      cleanContent = cleanContent.trim();

      // 如果清洗后不是以 { 或 [ 开头，说明不是有效 JSON
      if (!cleanContent.startsWith('{') && !cleanContent.startsWith('[')) {
        return null;
      }

      // 规范化中文引号
      cleanContent = cleanContent.replace(/[""]([^""]+)[""]\s*:/g, '"$1":');
      cleanContent = cleanContent.replace(/:\s*[""]([^""]*)[""]/g, ': "$1"');
      cleanContent = cleanContent.replace(/\[\s*[""]([^""]*)[""]/g, '[ "$1"');
      cleanContent = cleanContent.replace(/[""]([^""]*)[""]\s*\]/g, '"$1" ]');
      cleanContent = cleanContent.replace(/[""]/g, '"');

      const parsed = JSON.parse(cleanContent);
      // 处理不同的数据结构
      if (Array.isArray(parsed)) return parsed;
      if (parsed.outlines) return parsed.outlines;
      if (parsed.created_outlines) return parsed.created_outlines;
      return null;
    } catch (e) {
      // 不打印错误日志，避免控制台污染
      return null;
    }
  };

  // 渲染单个大纲卡片（复用逻辑）
  const renderOutlineCard = (outline: OutlineData, index: number) => {
    const chapterNum = outline.chapter_number || index + 1;

    return (
      <Card
        key={index}
        size="small"
        style={{ marginBottom: 12 }}
        styles={{ body: { padding: '12px 16px' } }}
      >
        {/* 章节标题 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <Tag color={token.colorPrimary} style={{ fontSize: 13 }}>
            第{chapterNum}章
          </Tag>
          <Text strong style={{ fontSize: 15 }}>
            {outline.title || '未命名章节'}
          </Text>
        </div>

        {/* 章节概要 */}
        {(outline.summary || outline.content) && (
          <Paragraph style={{ marginBottom: 12, lineHeight: 1.6 }}>
            📝 {outline.summary || outline.content}
          </Paragraph>
        )}

        {/* 情感基调 */}
        {outline.emotion && (
          <div style={{ marginBottom: 8 }}>
            <Tag color="purple">💭 {outline.emotion}</Tag>
          </div>
        )}

        {/* 叙事目标 */}
        {outline.goal && (
          <div style={{ marginBottom: 8 }}>
            <Tag color="cyan">🎯 {outline.goal}</Tag>
          </div>
        )}

        {/* 场景列表 */}
        {outline.scenes && outline.scenes.length > 0 && (
          <div style={{ marginBottom: 8 }}>
            <Text type="secondary" style={{ fontSize: 13 }}>🎬 场景：</Text>
            <Space wrap size={[4, 4]} style={{ marginLeft: 8 }}>
              {outline.scenes.map((scene, i) => (
                <Tag key={i}>{scene}</Tag>
              ))}
            </Space>
          </div>
        )}

        {/* 关键要点 */}
        {outline.key_points && outline.key_points.length > 0 && (
          <div style={{ marginBottom: 8 }}>
            <Text type="secondary" style={{ fontSize: 13 }}>🔑 关键要点：</Text>
            <div style={{ marginTop: 4, paddingLeft: 12 }}>
              {outline.key_points.map((point, i) => (
                <div key={i} style={{ marginBottom: 4 }}>
                  • {point}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 涉及角色 */}
        {outline.characters && outline.characters.length > 0 && (
          <div>
            <Text type="secondary" style={{ fontSize: 13 }}>👥 涉及角色：</Text>
            <Space wrap size={[4, 4]} style={{ marginLeft: 8 }}>
              {outline.characters.map((char, i) => {
                const charName = typeof char === 'string' ? char : char.name;
                const isOrg = typeof char === 'object' && char.type === 'organization';
                return (
                  <Tag key={i} color={isOrg ? 'orange' : 'blue'}>
                    {charName}{isOrg ? '[组织]' : ''}
                  </Tag>
                );
              })}
            </Space>
          </div>
        )}
      </Card>
    );
  };

  // 优先使用增量数据渲染
  if (incrementalData && incrementalData.length > 0) {
    return (
      <div>
        <Divider orientation="left" style={{ marginBottom: 16 }}>
          <Space>
            <BookOutlined style={{ color: token.colorPrimary }} />
            <Text strong style={{ fontSize: 16 }}>章节大纲</Text>
            <Tag color="processing">{incrementalData.length} 个（正在生成...）</Tag>
          </Space>
        </Divider>
        {incrementalData.map((outline, index) => renderOutlineCard(outline, index))}
      </div>
    );
  }

  // 没有增量数据时，解析完整内容
  const outlines = parseOutlineData(content);

  // 处理中状态但没有增量数据时，显示解析提示
  if (isProcessing && (!outlines || outlines.length === 0)) {
    return (
      <div style={{ textAlign: 'center', padding: 20 }}>
        <LoadingOutlined style={{ fontSize: 24, color: token.colorPrimary }} />
        <Paragraph style={{ marginTop: 12, color: token.colorTextSecondary }}>
          正在解析大纲数据...
        </Paragraph>
      </div>
    );
  }

  if (!outlines || outlines.length === 0) {
    return (
      <div style={{
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
        fontFamily: 'ui-monospace, monospace',
        fontSize: 14,
        lineHeight: 1.6,
      }}>
        {content || '等待生成...'}
      </div>
    );
  }

  return (
    <div>
      {outlines.map((outline, index) => renderOutlineCard(outline, index))}
    </div>
  );
};

// 格式化流式生成中的内容（实时显示累积的内容）
const formatStreamingContent = (stepName: string, content: string): string => {
  if (!content || content.trim() === '') {
    return '等待生成...';
  }

  // 基本的转义字符处理
  const processedContent = content
    .replace(/\\n/g, '\n')
    .replace(/\\t/g, '  ')
    .replace(/\\"/g, '"');

  // 尝试解析完整JSON，如果成功则格式化显示
  const trimmed = processedContent.trim();
  if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
    try {
      const jsonContent = JSON.parse(processedContent);
      // JSON完整，格式化显示
      return formatParsedJson(stepName, jsonContent);
    } catch {
      // JSON不完整，直接显示原始累积内容（让用户看到实时进度）
    }
  }

  // 直接返回累积的内容，用户可以实时看到内容在增加
  return processedContent;
};

// 格式化已解析的JSON对象（完成时显示）
const formatParsedJson = (stepName: string, json: any): string => {
  let output = '';

  if (stepName === '职业体系') {
    // 处理多种可能的数据结构
    const mainCareers = json.main_careers || json.main_careers_created || [];
    const subCareers = json.sub_careers || json.sub_careers_created || [];

    if (Array.isArray(mainCareers) && mainCareers.length > 0) {
      output += '📌 主职业:\n';
      mainCareers.forEach((career: any, i: number) => {
        if (typeof career === 'string') {
          output += `  ${i + 1}. ${career}\n`;
        } else if (career && career.name) {
          output += `  ${i + 1}. ${career.name}\n`;
          if (career.description) output += `     📝 ${career.description}\n`;
          if (career.max_stage) output += `     📊 最高阶段: ${career.max_stage}\n`;
          // 显示阶段信息
          if (career.stages && Array.isArray(career.stages) && career.stages.length > 0) {
            career.stages.forEach((stage: any, j: number) => {
              if (stage && stage.name) {
                output += `     📈 阶段${j + 1}: ${stage.name}`;
                if (stage.description) output += ` - ${stage.description}`;
                output += '\n';
              }
            });
          }
        }
      });
      output += '\n';
    }

    if (Array.isArray(subCareers) && subCareers.length > 0) {
      output += '📌 副职业:\n';
      subCareers.forEach((career: any, i: number) => {
        if (typeof career === 'string') {
          output += `  ${i + 1}. ${career}\n`;
        } else if (career && career.name) {
          output += `  ${i + 1}. ${career.name}\n`;
          if (career.description) output += `     📝 ${career.description}\n`;
          if (career.max_stage) output += `     📊 最高阶段: ${career.max_stage}\n`;
          // 显示阶段信息
          if (career.stages && Array.isArray(career.stages) && career.stages.length > 0) {
            career.stages.forEach((stage: any, j: number) => {
              if (stage && stage.name) {
                output += `     📈 阶段${j + 1}: ${stage.name}`;
                if (stage.description) output += ` - ${stage.description}`;
                output += '\n';
              }
            });
          }
        }
      });
    }

    // Fallback：如果没有数组数据但有 count 信息
    if (output === '' && (json.main_careers_count || json.sub_careers_count)) {
      output = `✅ 职业体系生成完成\n`;
      if (json.main_careers_count) output += `   📊 主职业数量: ${json.main_careers_count}\n`;
      if (json.sub_careers_count) output += `   📊 副职业数量: ${json.sub_careers_count}\n`;
    }
  } else if (stepName === '角色') {
    const characters = json.characters || json.created_characters || json;

    if (Array.isArray(characters) && characters.length > 0) {
      characters.forEach((char: any, i: number) => {
        if (!char) return;
        output += `${i + 1}. ${char.name || '未知角色'}\n`;
        if (char.role_type) {
          const roleCN = roleTypeMap[char.role_type] || char.role_type;
          output += `   🎭 类型: ${roleCN}\n`;
        }
        // 显示完整内容，不截断
        if (char.personality) output += `   💭 性格: ${char.personality}\n`;
        if (char.background) output += `   📖 背景: ${char.background}\n`;
        if (char.appearance) output += `   👤 外貌: ${char.appearance}\n`;
        output += '\n';
      });
    }

    // Fallback：如果没有数组数据但有 count 信息
    if (output === '' && (json.count || json.message)) {
      output = `✅ 角色生成完成\n`;
      if (json.count) output += `   📊 生成数量: ${json.count}\n`;
      if (json.message) output += `   📝 ${json.message}\n`;
    }
  } else if (stepName === '大纲') {
    const outlines = json.outlines || json.created_outlines || json;

    if (Array.isArray(outlines) && outlines.length > 0) {
      outlines.forEach((outline: any, i: number) => {
        if (!outline) return;

        // 章节号和标题
        const chapterNum = outline.chapter_number || i + 1;
        output += `${chapterNum}. ${outline.title || '未知章节'}\n`;

        // 章节概要（完整显示）
        if (outline.summary) {
          output += `   📝 概要: ${outline.summary}\n`;
        } else if (outline.content) {
          output += `   📝 概要: ${outline.content}\n`;
        }

        // 情感基调
        if (outline.emotion) {
          output += `   💭 情感基调: ${outline.emotion}\n`;
        }

        // 叙事目标
        if (outline.goal) {
          output += `   🎯 叙事目标: ${outline.goal}\n`;
        }

        // 场景列表
        if (outline.scenes && Array.isArray(outline.scenes) && outline.scenes.length > 0) {
          output += `   🎬 场景:\n`;
          outline.scenes.forEach((scene: any, j: number) => {
            output += `      ${j + 1}. ${scene}\n`;
          });
        }

        // 情节要点
        if (outline.key_points && Array.isArray(outline.key_points) && outline.key_points.length > 0) {
          output += `   🔑 关键要点:\n`;
          outline.key_points.forEach((point: any) => {
            output += `      • ${point}\n`;
          });
        }

        // 涉及角色
        if (outline.characters && Array.isArray(outline.characters) && outline.characters.length > 0) {
          output += `   👥 涉及角色: `;
          const charNames = outline.characters.map((char: any) => {
            if (typeof char === 'string') return char;
            const name = char.name || char;
            const type = char.type === 'organization' ? '[组织]' : '';
            return `${name}${type}`;
          });
          output += charNames.join('、') + '\n';
        }

        output += '\n';
      });
    }

    // Fallback：如果没有数组数据但有 count 信息
    if (output === '' && (json.outline_count || json.chapter_count || json.message)) {
      output = `✅ 大纲生成完成\n`;
      if (json.outline_count) output += `   📊 大纲数量: ${json.outline_count}\n`;
      if (json.chapter_count) output += `   📊 章节数量: ${json.chapter_count}\n`;
      if (json.message) output += `   📝 ${json.message}\n`;
    }
  }

  // 默认：如果 output 为空，显示完整的 JSON
  if (output === '' && json) {
    output = JSON.stringify(json, null, 2);
  }

  return output;
};

// Markdown渲染器组件
const WorldSettingRenderer: React.FC<{ content: string }> = ({ content }) => {
  // 预处理内容：修复表格格式问题
  // ReactMarkdown 解析表格的要求：
  // 1. 每行必须独立（用换行分隔）
  // 2. 表格前后需要空行（前后没有非表格文本紧贴）
  const fixTableFormat = (text: string): string => {
    let result = text;

    // 1. 将压缩的表格行展开：| 表头 | |------| | 数据 | -> 每行独立
    // "|空格|" 模式表示两个表格行相邻，替换为 "|\n|" 即可分隔所有行
    result = result.replace(/\|\s+\|/g, '|\n|');

    // 2. 在表格开始前添加空行（如果前面是非表格内容）
    // 查找模式：非表格行（不以 | 开头）后面紧跟表格行（以 | 开头）
    // 注意：需要在换行符后面添加空行
    result = result.replace(/([^\n|])\n(\|[^\n])/g, '$1\n\n$2');

    // 3. 在表格结束后添加空行（如果后面是非表格内容）
    // 查找模式：表格行（以 | 结尾）后面紧跟非表格行（不以 | 开头）
    result = result.replace(/(\|[^\n]*\|)\n([^\n|])/g, '$1\n\n$2');

    // 4. 清理多余换行（最多保留两个换行，即一个空行）
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
      {processedContent || '等待生成...'}
    </ReactMarkdown>
  );
};

export interface GenerationConfig {
  title: string;
  description: string;
  theme: string;
  genre: string | string[];
  narrative_perspective: string;
  target_words: number;
  chapter_count: number;
  character_count: number;
  outline_mode?: 'one-to-one' | 'one-to-many';  // 大纲章节模式
}

interface AIProjectGeneratorProps {
  config: GenerationConfig;
  storagePrefix: 'wizard' | 'inspiration';
  onComplete: (projectId: string) => void;
  onBack?: () => void;
  isMobile?: boolean;
  resumeProjectId?: string;
}

type GenerationStep = 'pending' | 'processing' | 'completed' | 'error';

// 步骤内容窗口接口
interface StepContent {
  stepName: string;  // 步骤名称：世界观、职业体系、角色、大纲
  content: string;   // 该步骤的累积内容
  editedContent?: string;  // 编辑后的内容
  status: GenerationStep;
  isCollapsed: boolean;
  startTime: number;
  isEditing?: boolean;  // 是否正在编辑
}

// 增量解析 JSON，提取已完整的对象（用于流式渲染）
// 支持两种格式：
// 1. 数组格式：[{...}, {...}] - 用于角色、大纲
// 2. 对象格式：{main_careers: [...], sub_careers: [...]} - 用于职业体系
const parseIncrementalJson = (text: string, stepName: string): { completeItems: any[], isComplete: boolean } => {
  // 去除 markdown 代码块标记
  let cleanContent = text.replace(/^```json\s*\n?/gi, '').replace(/^```\s*\n?/g, '').replace(/\n?```\s*$/g, '').trim();

  // 规范化中文引号
  cleanContent = cleanContent.replace(/[""]/g, '"');

  const completeItems: any[] = [];

  // 辅助函数：检查引号是否被转义（考虑连续反斜杠）
  const isEscapedQuote = (content: string, pos: number): boolean => {
    let backslashCount = 0;
    let checkPos = pos - 1;
    while (checkPos >= 0 && content[checkPos] === '\\') {
      backslashCount++;
      checkPos--;
    }
    return backslashCount % 2 === 1;
  };

  // 辅助函数：解析 JSON 字符串中的数组元素（提取完整的 {...} 对象）
  const extractArrayItems = (arrayContent: string): any[] => {
    const items: any[] = [];
    let pos = 0;
    let depth = 0;
    let itemStart = -1;
    let inString = false;

    while (pos < arrayContent.length) {
      const char = arrayContent[pos];

      if (char === '"' && !isEscapedQuote(arrayContent, pos)) {
        inString = !inString;
        pos++;
        continue;
      }

      if (inString) {
        pos++;
        continue;
      }

      if (char === '{') {
        if (depth === 0) itemStart = pos;
        depth++;
      } else if (char === '}') {
        depth--;
        if (depth === 0 && itemStart >= 0) {
          const itemText = arrayContent.substring(itemStart, pos + 1);
          try {
            items.push(JSON.parse(itemText));
          } catch { }
          itemStart = -1;
        }
      }
      pos++;
    }
    return items;
  };

  // 根据格式类型选择解析策略
  if (stepName === '职业体系') {
    // 职业体系：对象格式 {main_careers: [...], sub_careers: [...]}
    // 尝试提取 main_careers 和 sub_careers 数组中的元素

    // 查找 main_careers 数组
    const mainCareersMatch = cleanContent.match(/"main_careers"\s*:\s*\[/);
    if (mainCareersMatch) {
      const startIdx = mainCareersMatch.index! + mainCareersMatch[0].length;
      // 找到数组结束位置（简单匹配，可能不完整）
      let endIdx = startIdx;
      let depth = 1;
      let inString = false;
      while (endIdx < cleanContent.length && depth > 0) {
        const char = cleanContent[endIdx];
        if (char === '"' && !isEscapedQuote(cleanContent, endIdx)) inString = !inString;
        else if (!inString) {
          if (char === '[') depth++;
          else if (char === ']') depth--;
        }
        endIdx++;
      }
      const arrayContent = cleanContent.substring(startIdx, endIdx);
      const items = extractArrayItems(arrayContent);
      items.forEach(item => {
        if (!completeItems.some(existing => JSON.stringify(existing) === JSON.stringify(item))) {
          completeItems.push({ ...item, _careerType: 'main' });
        }
      });
    }

    // 查找 sub_careers 数组
    const subCareersMatch = cleanContent.match(/"sub_careers"\s*:\s*\[/);
    if (subCareersMatch) {
      const startIdx = subCareersMatch.index! + subCareersMatch[0].length;
      let endIdx = startIdx;
      let depth = 1;
      let inString = false;
      while (endIdx < cleanContent.length && depth > 0) {
        const char = cleanContent[endIdx];
        if (char === '"' && !isEscapedQuote(cleanContent, endIdx)) inString = !inString;
        else if (!inString) {
          if (char === '[') depth++;
          else if (char === ']') depth--;
        }
        endIdx++;
      }
      const arrayContent = cleanContent.substring(startIdx, endIdx);
      const items = extractArrayItems(arrayContent);
      items.forEach(item => {
        if (!completeItems.some(existing => JSON.stringify(existing) === JSON.stringify(item))) {
          completeItems.push({ ...item, _careerType: 'sub' });
        }
      });
    }

    // 检查是否完整（对象闭合）
    const isComplete = cleanContent.endsWith('}');
    return { completeItems, isComplete };
  } else {
    // 角色、大纲：数组格式 [{...}, {...}]
    if (!cleanContent.startsWith('[')) {
      return { completeItems: [], isComplete: false };
    }

    // 直接解析数组
    const arrayContent = cleanContent.substring(1); // 跳过开头的 [
    const items = extractArrayItems(arrayContent);
    items.forEach(item => {
      if (!completeItems.some(existing => JSON.stringify(existing) === JSON.stringify(item))) {
        completeItems.push(item);
      }
    });

    const isComplete = cleanContent.endsWith(']');
    return { completeItems, isComplete };
  }
};

// 智能滚动的内容窗口组件
const StreamingContentWindow: React.FC<{
  stepItem: StepContent;
  displayContent: string;
  isMobile: boolean;
  startEdit: () => void;
  cancelEdit: () => void;
  saveEdit: () => void;
  updateEditContent: (content: string) => void;
  incrementalData?: any[];  // 增量渲染数据
}> = ({ stepItem, displayContent, isMobile, startEdit, cancelEdit, saveEdit, updateEditContent, incrementalData }) => {
  const contentRef = useRef<HTMLDivElement>(null);
  const [userIsScrolling, setUserIsScrolling] = useState(false);

  // 是否处于处理中状态
  const isProcessing = stepItem.status === 'processing';

  // 检测用户是否滚动到底部附近
  const checkIsAtBottom = useCallback(() => {
    if (!contentRef.current) return true;
    const { scrollHeight, scrollTop, clientHeight } = contentRef.current;
    return scrollHeight - scrollTop - clientHeight < 50;
  }, []);

  // 处理滚动事件
  const handleScroll = useCallback(() => {
    const isAtBottom = checkIsAtBottom();
    setUserIsScrolling(!isAtBottom);
  }, [checkIsAtBottom]);

  // 内容更新时自动滚动（仅当用户没有手动滚动时）
  useEffect(() => {
    if (!userIsScrolling && stepItem.status === 'processing' && contentRef.current) {
      contentRef.current.scrollTo({
        top: contentRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [stepItem.content, userIsScrolling, stepItem.status]);

  // 步骤开始时重置滚动状态
  useEffect(() => {
    if (stepItem.status === 'processing') {
      setUserIsScrolling(false);
    }
  }, [stepItem.status]);

  return (
    <>
      {/* 内容区域 - 折叠时隐藏 */}
      {!stepItem.isCollapsed && (
        <>
          {stepItem.isEditing ? (
            /* 编辑模式 */
            <div style={{ padding: '12px 16px' }}>
              <TextArea
                value={stepItem.editedContent || stepItem.content}
                onChange={(e) => updateEditContent(e.target.value)}
                autoSize={{ minRows: 10, maxRows: 30 }}
                style={{ marginBottom: 12 }}
              />
              <Space>
                <Button
                  icon={<UndoOutlined />}
                  onClick={cancelEdit}
                >
                  取消
                </Button>
                <Button
                  type="primary"
                  icon={<SaveOutlined />}
                  onClick={saveEdit}
                >
                  保存修改
                </Button>
              </Space>
            </div>
          ) : (
            /* 显示模式 */
            <div
              ref={contentRef}
              onScroll={handleScroll}
              style={{
                maxHeight: isMobile ? '200px' : '500px',
                overflowY: 'auto',
                padding: '12px 16px',
                background: 'var(--color-bg-layout)'
              }}
            >
              {stepItem.stepName === '世界观' ? (
                <div className="markdown-content">
                  <WorldSettingRenderer content={displayContent} />
                </div>
              ) : stepItem.stepName === '职业体系' ? (
                <div className="career-system-content">
                  <CareerSystemRenderer content={displayContent} incrementalData={incrementalData} isProcessing={isProcessing} />
                </div>
              ) : stepItem.stepName === '角色' ? (
                <div className="character-system-content">
                  <CharacterSystemRenderer content={displayContent} incrementalData={incrementalData} isProcessing={isProcessing} />
                </div>
              ) : stepItem.stepName === '大纲' ? (
                <div className="outline-system-content">
                  <OutlineSystemRenderer content={displayContent} incrementalData={incrementalData} isProcessing={isProcessing} />
                </div>
              ) : (
                <div style={{
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  fontFamily: 'ui-monospace, monospace',
                  fontSize: 14,
                  lineHeight: 1.6,
                }}>
                  {displayContent}
                </div>
              )}
            </div>
          )}

          {/* 编辑按钮区域 - 仅在完成状态显示 */}
          {stepItem.status === 'completed' && !stepItem.isEditing && (
            <div style={{ padding: '8px 16px', borderTop: '1px solid var(--color-border)' }}>
              <Button
                size="small"
                icon={<EditOutlined />}
                onClick={startEdit}
              >
                编辑内容
              </Button>
            </div>
          )}
        </>
      )}
    </>
  );
};

interface GenerationSteps {
  worldBuilding: GenerationStep;
  careers: GenerationStep;
  characters: GenerationStep;
  outline: GenerationStep;
}

interface WorldBuildingResult {
  project_id: string;
  time_period: string;
  location: string;
  atmosphere: string;
  rules: string;
}

export const AIProjectGenerator: React.FC<AIProjectGeneratorProps> = ({
  config,
  storagePrefix,
  onComplete,
  isMobile = false,
  resumeProjectId
}) => {
  const navigate = useNavigate();
  const { message } = App.useApp();

  // 状态管理
  const [loading, setLoading] = useState(false);
  const [projectId, setProjectId] = useState<string>('');

  // SSE流式进度状态
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState('');
  const [errorDetails, setErrorDetails] = useState<string>('');
  const [generationSteps, setGenerationSteps] = useState<GenerationSteps>({
    worldBuilding: 'pending',
    careers: 'pending',
    characters: 'pending',
    outline: 'pending'
  });

  // 多步骤独立窗口内容
  const [stepContents, setStepContents] = useState<StepContent[]>([]);
  const [allCompleted, setAllCompleted] = useState(false);
  const currentStreamingStepRef = useRef<string>('');
  const lastProgressMessageRef = useRef<string>('');  // 用于过滤重复消息

  // 使用 ref 同步跟踪累积的内容（解决 React 状态更新异步问题）
  // 当 onResult 调用时，状态更新可能还没生效，但 ref 是同步的
  const stepContentMapRef = useRef<Record<string, string>>({});

  // 增量渲染数据状态（用于流式渲染时显示已解析的完整对象）
  const [incrementalRenderData, setIncrementalRenderData] = useState<Record<string, any[]>>({
    '职业体系': [],
    '角色': [],
    '大纲': []
  });

  // 防止重复生成的标记
  const hasStartedGeneration = useRef(false);

  // 保存生成数据，用于重试
  const [generationData, setGenerationData] = useState<GenerationConfig | null>(null);
  // 保存世界观生成结果，用于后续步骤
  const [worldBuildingResult, setWorldBuildingResult] = useState<WorldBuildingResult | null>(null);

  // LocalStorage 键名
  const storageKeys = {
    projectId: `${storagePrefix}_project_id`,
    generationData: `${storagePrefix}_generation_data`,
    currentStep: `${storagePrefix}_current_step`
  };

  // 保存进度到localStorage
  const saveProgress = (projectId: string, data: GenerationConfig, step: string) => {
    try {
      localStorage.setItem(storageKeys.projectId, projectId);
      localStorage.setItem(storageKeys.generationData, JSON.stringify(data));
      localStorage.setItem(storageKeys.currentStep, step);
    } catch (error) {
      console.error('保存进度失败:', error);
    }
  };

  // 清理localStorage
  const clearStorage = () => {
    localStorage.removeItem(storageKeys.projectId);
    localStorage.removeItem(storageKeys.generationData);
    localStorage.removeItem(storageKeys.currentStep);
  };

  // 步骤名称到显示名称的映射
  const stepDisplayNames: Record<string, string> = {
    '世界观': '🌍 世界观设定',
    '职业体系': '⚔️ 职业体系',
    '角色': '👥 角色设定',
    '大纲': '📖 章节大纲'
  };

  // 添加新步骤到stepContents
  const addNewStep = useCallback((stepName: string) => {
    currentStreamingStepRef.current = stepName;
    lastProgressMessageRef.current = '';  // 重置进度消息过滤
    // 重置该步骤的 ref 内容（确保从空开始累积）
    stepContentMapRef.current[stepName] = '';

    // 重置该步骤的增量渲染数据（避免重试时残留旧数据）
    setIncrementalRenderData(prev => {
      if (prev[stepName] && prev[stepName].length > 0) {
        return { ...prev, [stepName]: [] };
      }
      return prev;
    });

    setStepContents(prev => {
      // 如果步骤已存在
      const existing = prev.find(s => s.stepName === stepName);
      if (existing) {
        // 如果步骤已经完成，不重新开始
        if (existing.status === 'completed') {
          console.log(`步骤 ${stepName} 已完成，跳过重复生成`);
          return prev;
        }
        // 如果步骤正在处理或出错，更新其状态为processing并展开
        return prev.map(s =>
          s.stepName === stepName
            ? { ...s, status: 'processing', isCollapsed: false, content: '' }  // 重置内容
            : { ...s, isCollapsed: true }  // 其他步骤折叠
        );
      }
      // 新增步骤，之前的步骤折叠
      return [
        ...prev.map(s => ({ ...s, isCollapsed: true })),
        { stepName, content: '', status: 'processing', isCollapsed: false, startTime: Date.now() }
      ];
    });
  }, []);

  // 更新步骤内容（追加chunk）
  // 同时更新 ref（同步）和状态（异步），确保 completeStepWithResult 能获取完整内容
  const appendStepContent = useCallback((stepName: string, chunk: string) => {
    // 同步更新 ref（解决 React 状态更新异步问题）
    stepContentMapRef.current[stepName] = (stepContentMapRef.current[stepName] || '') + chunk;

    // 异步更新状态（用于 UI 显示）
    setStepContents(prev =>
      prev.map(s =>
        s.stepName === stepName
          ? { ...s, content: s.content + chunk }
          : s
      )
    );

    // 增量解析（仅对职业体系、角色、大纲）
    if (['职业体系', '角色', '大纲'].includes(stepName)) {
      const accumulated = stepContentMapRef.current[stepName];
      const { completeItems } = parseIncrementalJson(accumulated, stepName);

      if (completeItems.length > 0) {
        setIncrementalRenderData(prev => {
          // 使用 JSON 内容作为唯一标识符（更可靠的去重）
          const existingJsonSet = new Set(
            (prev[stepName] || []).map(item => JSON.stringify(item))
          );
          const newItems = completeItems.filter(item => {
            const itemJson = JSON.stringify(item);
            return !existingJsonSet.has(itemJson);
          });
          if (newItems.length > 0) {
            return { ...prev, [stepName]: [...(prev[stepName] || []), ...newItems] };
          }
          return prev;
        });
      }
    }
  }, []);

  // 更新步骤状态为完成，保留原始 JSON 内容供渲染组件解析
  // 使用 ref 获取内容（确保能获取到完整累积内容）
  const completeStepWithResult = useCallback((stepName: string, _result: any) => {
    // 从 ref 获取同步累积的内容
    const accumulatedContent = stepContentMapRef.current[stepName] || '';

    setStepContents(prev =>
      prev.map(s => {
        if (s.stepName !== stepName) return s;

        // 对于职业体系、角色、大纲，保留原始 JSON 内容（渲染组件会自己解析渲染卡片）
        if (stepName !== '世界观' && accumulatedContent) {
          // 清洗 JSON：去除 markdown 代码块标记和规范化中文引号
          let cleanContent = accumulatedContent;

          // 1. 去除开头的 ```json 或 ```
          cleanContent = cleanContent.replace(/^```json\s*\n?/gi, '');
          cleanContent = cleanContent.replace(/^```\s*\n?/g, '');
          // 2. 去除结尾的 ```
          cleanContent = cleanContent.replace(/\n?```\s*$/g, '');
          // 3. 去除前后空白
          cleanContent = cleanContent.trim();

          // 4. 规范化中文引号为英文引号（AI 可能使用中文引号）
          // 中文引号：左引号 "\u201c"，右引号 "\u201d"
          // 模式1：中文引号作为键名 "key": -> "key":
          cleanContent = cleanContent.replace(/[""]([^""]+)[""]\s*:/g, '"$1":');
          // 模式2：中文引号作为值 : "value" -> : "value"
          cleanContent = cleanContent.replace(/:\s*[""]([^""]*)[""]/g, ': "$1"');
          // 模式3：中文引号作为数组元素 ["item"] -> ["item"]
          cleanContent = cleanContent.replace(/\[\s*[""]([^""]*)[""]/g, '[ "$1"');
          cleanContent = cleanContent.replace(/[""]([^""]*)[""]\s*\]/g, '"$1" ]');
          // 模式4：直接替换所有剩余的中文引号（更激进的处理）
          cleanContent = cleanContent.replace(/[""]/g, '"');

          // 保留原始 JSON 内容，渲染组件会解析并渲染卡片
          return { ...s, status: 'completed', content: cleanContent };
        }

        // 世界观保持原始Markdown内容
        return { ...s, status: 'completed', content: accumulatedContent || s.content };
      })
    );

    // 清理增量渲染状态（完成后使用完整数据）
    setIncrementalRenderData(prev => ({ ...prev, [stepName]: [] }));
  }, []);

  // 更新步骤状态为错误
  const errorStep = useCallback((stepName: string) => {
    setStepContents(prev =>
      prev.map(s =>
        s.stepName === stepName
          ? { ...s, status: 'error' }
          : s
      )
    );

    // 清理增量渲染状态（错误时避免残留数据）
    setIncrementalRenderData(prev => {
      if (prev[stepName] && prev[stepName].length > 0) {
        return { ...prev, [stepName]: [] };
      }
      return prev;
    });
  }, []);

  // 折叠/展开步骤窗口
  const toggleStepCollapse = useCallback((stepName: string) => {
    setStepContents(prev =>
      prev.map(s =>
        s.stepName === stepName
          ? { ...s, isCollapsed: !s.isCollapsed }
          : s
      )
    );
  }, []);

  // 开始编辑步骤内容
  const startEditStep = useCallback((stepName: string) => {
    setStepContents(prev =>
      prev.map(s =>
        s.stepName === stepName
          ? { ...s, isEditing: true, editedContent: s.content }
          : s
      )
    );
  }, []);

  // 取消编辑
  const cancelEditStep = useCallback((stepName: string) => {
    setStepContents(prev =>
      prev.map(s =>
        s.stepName === stepName
          ? { ...s, isEditing: false, editedContent: undefined }
          : s
      )
    );
  }, []);

  // 更新编辑内容
  const updateEditContent = useCallback((stepName: string, newContent: string) => {
    setStepContents(prev =>
      prev.map(s =>
        s.stepName === stepName
          ? { ...s, editedContent: newContent }
          : s
      )
    );
  }, []);

  // 保存编辑内容
  const saveEditContent = useCallback((stepName: string) => {
    setStepContents(prev =>
      prev.map(s =>
        s.stepName === stepName && s.editedContent
          ? { ...s, content: s.editedContent, isEditing: false, editedContent: undefined }
          : s
      )
    );
  }, []);

  // 开始自动化生成流程
  useEffect(() => {
    // 防止重复调用（React StrictMode会双重调用useEffect）
    if (config && !loading && !hasStartedGeneration.current) {
      hasStartedGeneration.current = true;
      if (resumeProjectId) {
        // 恢复生成模式
        handleResumeGenerate(config, resumeProjectId);
      } else {
        // 新建项目模式
        handleAutoGenerate(config);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config, resumeProjectId]);

  // 恢复未完成项目的生成
  const handleResumeGenerate = async (data: GenerationConfig, projectIdParam: string) => {
    try {
      setLoading(true);
      setProgress(0);
      setProgressMessage('检查项目状态...');
      setErrorDetails('');
      setGenerationData(data);
      setProjectId(projectIdParam);

      // 获取项目信息,判断当前完成到哪一步
      const response = await fetch(`/api/projects/${projectIdParam}`, {
        credentials: 'include'
      });
      if (!response.ok) {
        throw new Error('获取项目信息失败');
      }
      const project = await response.json();
      const wizardStep = project.wizard_step || 0;

      // 根据wizard_step判断从哪里继续
      // wizard_step: 0=未开始, 1=世界观已完成, 2=职业体系已完成, 3=角色已完成, 4=大纲已完成
      // 获取世界观数据（用于后续步骤）
      const worldResult = {
        project_id: projectIdParam,
        time_period: project.world_time_period || '',
        location: project.world_location || '',
        atmosphere: project.world_atmosphere || '',
        rules: project.world_rules || ''
      };

      if (wizardStep === 0) {
        // 从世界观开始
        message.info('从世界观步骤开始生成...');
        setGenerationSteps({ worldBuilding: 'processing', careers: 'pending', characters: 'pending', outline: 'pending' });
        await resumeFromWorldBuilding(data);
      } else if (wizardStep === 1) {
        // 世界观已完成，从职业体系开始
        message.info('世界观已完成，从职业体系步骤继续...');
        setGenerationSteps({ worldBuilding: 'completed', careers: 'processing', characters: 'pending', outline: 'pending' });
        setWorldBuildingResult(worldResult);
        setProgress(20);
        await resumeFromCareers(data, worldResult);
      } else if (wizardStep === 2) {
        // 职业体系已完成，从角色开始
        message.info('职业体系已完成，从角色步骤继续...');
        setGenerationSteps({ worldBuilding: 'completed', careers: 'completed', characters: 'processing', outline: 'pending' });
        setWorldBuildingResult(worldResult);
        setProgress(40);
        await resumeFromCharacters(data, worldResult);
      } else if (wizardStep === 3) {
        // 角色已完成，从大纲开始
        message.info('角色已完成，从大纲步骤继续...');
        setGenerationSteps({ worldBuilding: 'completed', careers: 'completed', characters: 'completed', outline: 'processing' });
        setProgress(70);
        await resumeFromOutline(data, projectIdParam);
      } else {
        // 已全部完成
        message.success('项目已完成,正在跳转...');
        setProgress(100);
        onComplete(projectIdParam);
        setTimeout(() => {
          navigate(`/project/${projectIdParam}`);
        }, 1000);
      }
    } catch (error) {
      const apiError = error as ApiError;
      const errorMsg = apiError.response?.data?.detail || apiError.message || '未知错误';
      console.error('恢复生成失败:', errorMsg);
      setErrorDetails(errorMsg);
      message.error('恢复生成失败：' + errorMsg);
      setLoading(false);
    }
  };

  // 恢复:从世界观步骤开始
  const resumeFromWorldBuilding = async (data: GenerationConfig) => {
    const genreString = Array.isArray(data.genre) ? data.genre.join('、') : data.genre;
    addNewStep('世界观');

    const worldResult = await wizardStreamApi.generateWorldBuildingStream(
      {
        title: data.title,
        description: data.description,
        theme: data.theme,
        genre: genreString,
        narrative_perspective: data.narrative_perspective,
        target_words: data.target_words,
        chapter_count: data.chapter_count,
        character_count: data.character_count,
        outline_mode: data.outline_mode || 'one-to-many',  // 传递大纲模式
      },
      {
        onProgress: (msg, prog) => {
          // 过滤重复消息
          if (msg.includes('续写') && msg === lastProgressMessageRef.current) {
            return;
          }
          lastProgressMessageRef.current = msg;
          setProgress(prog);
          setProgressMessage(msg);
        },
        onChunk: (chunk) => {
          appendStepContent('世界观', chunk);
        },
        onResult: (result) => {
          setWorldBuildingResult(result);
          setGenerationSteps(prev => ({ ...prev, worldBuilding: 'completed' }));
          completeStepWithResult('世界观', result);
        },
        onError: (error) => {
          console.error('世界观生成失败:', error);
          setErrorDetails(`世界观生成失败: ${error}`);
          setGenerationSteps(prev => ({ ...prev, worldBuilding: 'error' }));
          errorStep('世界观');
          setLoading(false);
          throw new Error(error);
        },
        onComplete: () => {
          console.log('世界观生成完成');
        }
      }
    );

    await resumeFromCareers(data, worldResult);
  };

  // 恢复:从职业体系步骤继续
  const resumeFromCareers = async (data: GenerationConfig, worldResult: WorldBuildingResult) => {
    const pid = projectId || worldResult.project_id;

    setGenerationSteps(prev => ({ ...prev, careers: 'processing' }));
    setProgressMessage('正在生成职业体系...');
    addNewStep('职业体系');

    await wizardStreamApi.generateCareerSystemStream(
      {
        project_id: pid,
      },
      {
        onProgress: (msg, prog) => {
          if (msg.includes('续写') && msg === lastProgressMessageRef.current) {
            return;
          }
          lastProgressMessageRef.current = msg;
          setProgress(prog);
          setProgressMessage(msg);
        },
        onChunk: (chunk) => {
          appendStepContent('职业体系', chunk);
        },
        onResult: (result) => {
          console.log(`成功生成职业体系：主职业${result.main_careers_count}个，副职业${result.sub_careers_count}个`);
          setGenerationSteps(prev => ({ ...prev, careers: 'completed' }));
          completeStepWithResult('职业体系', result);
        },
        onError: (error) => {
          console.error('职业体系生成失败:', error);
          setErrorDetails(`职业体系生成失败: ${error}`);
          setGenerationSteps(prev => ({ ...prev, careers: 'error' }));
          errorStep('职业体系');
          setLoading(false);
          throw new Error(error);
        },
        onComplete: () => {
          console.log('职业体系生成完成');
        }
      }
    );

    await resumeFromCharacters(data, worldResult);
  };

  // 恢复:从角色步骤继续
  const resumeFromCharacters = async (data: GenerationConfig, worldResult: WorldBuildingResult) => {
    const genreString = Array.isArray(data.genre) ? data.genre.join('、') : data.genre;
    const pid = projectId || worldResult.project_id;

    setGenerationSteps(prev => ({ ...prev, characters: 'processing' }));
    setProgressMessage('正在生成角色...');
    addNewStep('角色');

    await wizardStreamApi.generateCharactersStream(
      {
        project_id: pid,
        count: data.character_count,
        world_context: {
          time_period: worldResult.time_period || '',
          location: worldResult.location || '',
          atmosphere: worldResult.atmosphere || '',
          rules: worldResult.rules || '',
        },
        theme: data.theme,
        genre: genreString,
      },
      {
        onProgress: (msg, prog) => {
          if (msg.includes('续写') && msg === lastProgressMessageRef.current) {
            return;
          }
          lastProgressMessageRef.current = msg;
          setProgress(prog);
          setProgressMessage(msg);
        },
        onChunk: (chunk) => {
          appendStepContent('角色', chunk);
        },
        onResult: (result) => {
          console.log(`成功生成${result.characters?.length || 0}个角色`);
          setGenerationSteps(prev => ({ ...prev, characters: 'completed' }));
          completeStepWithResult('角色', result);
        },
        onError: (error) => {
          console.error('角色生成失败:', error);
          setErrorDetails(`角色生成失败: ${error}`);
          setGenerationSteps(prev => ({ ...prev, characters: 'error' }));
          errorStep('角色');
          setLoading(false);
          throw new Error(error);
        },
        onComplete: () => {
          console.log('角色生成完成');
        }
      }
    );

    await resumeFromOutline(data, pid);
  };

  // 恢复:从大纲步骤继续
  const resumeFromOutline = async (data: GenerationConfig, pid: string) => {
    setGenerationSteps(prev => ({ ...prev, outline: 'processing' }));
    setProgressMessage('正在生成大纲...');
    addNewStep('大纲');

    await wizardStreamApi.generateCompleteOutlineStream(
      {
        project_id: pid,
        chapter_count: data.chapter_count,
        narrative_perspective: data.narrative_perspective,
        target_words: data.target_words,
      },
      {
        onProgress: (msg, prog) => {
          if (msg.includes('续写') && msg === lastProgressMessageRef.current) {
            return;
          }
          lastProgressMessageRef.current = msg;
          setProgress(prog);
          setProgressMessage(msg);
        },
        onChunk: (chunk) => {
          appendStepContent('大纲', chunk);
        },
        onResult: (result) => {
          console.log('大纲生成完成');
          setGenerationSteps(prev => ({ ...prev, outline: 'completed' }));
          completeStepWithResult('大纲', result);
        },
        onError: (error) => {
          console.error('大纲生成失败:', error);
          setErrorDetails(`大纲生成失败: ${error}`);
          setGenerationSteps(prev => ({ ...prev, outline: 'error' }));
          errorStep('大纲');
          setLoading(false);
          throw new Error(error);
        },
        onComplete: () => {
          console.log('大纲生成完成');
        }
      }
    );

    // 全部完成 - 不自动跳转
    setProgress(100);
    setProgressMessage('所有内容生成完成！');
    setAllCompleted(true);
    setLoading(false);
    clearStorage();
  };

  // 自动化生成流程
  const handleAutoGenerate = async (data: GenerationConfig) => {
    try {
      setLoading(true);
      setProgress(0);
      setProgressMessage('开始创建项目...');
      setErrorDetails('');
      setGenerationData(data);
      saveProgress('', data, 'generating');

      const genreString = Array.isArray(data.genre) ? data.genre.join('、') : data.genre;

      // 步骤1: 生成世界观并创建项目
      setGenerationSteps(prev => ({ ...prev, worldBuilding: 'processing' }));
      setProgressMessage('正在生成世界观...');
      addNewStep('世界观');

      const worldResult = await wizardStreamApi.generateWorldBuildingStream(
        {
          title: data.title,
          description: data.description,
          theme: data.theme,
          genre: genreString,
          narrative_perspective: data.narrative_perspective,
          target_words: data.target_words,
          chapter_count: data.chapter_count,
          character_count: data.character_count,
          outline_mode: data.outline_mode || 'one-to-many',  // 传递大纲模式
        },
        {
          onProgress: (msg, prog) => {
            // 过滤重复的"续写"消息
            if (msg.includes('续写') && msg === lastProgressMessageRef.current) {
              return;
            }
            lastProgressMessageRef.current = msg;
            setProgress(prog);
            setProgressMessage(msg);
          },
          onChunk: (chunk) => {
            appendStepContent('世界观', chunk);
          },
          onResult: (result) => {
            setProjectId(result.project_id);
            setWorldBuildingResult(result);
            setGenerationSteps(prev => ({ ...prev, worldBuilding: 'completed' }));
            completeStepWithResult('世界观', result);
          },
          onError: (error) => {
            console.error('世界观生成失败:', error);
            setErrorDetails(`世界观生成失败: ${error}`);
            setGenerationSteps(prev => ({ ...prev, worldBuilding: 'error' }));
            errorStep('世界观');
            setLoading(false);
            throw new Error(error);
          },
          onComplete: () => {
              // onResult 已打印完成日志，此处无需重复
            }
          }
      );

      if (!worldResult?.project_id) {
        throw new Error('项目创建失败：未获取到项目ID');
      }

      const createdProjectId = worldResult.project_id;
      setProjectId(createdProjectId);
      setWorldBuildingResult(worldResult);
      saveProgress(createdProjectId, data, 'generating');

      // 步骤2: 生成职业体系
      setGenerationSteps(prev => ({ ...prev, careers: 'processing' }));
      setProgressMessage('正在生成职业体系...');
      addNewStep('职业体系');

      await wizardStreamApi.generateCareerSystemStream(
        {
          project_id: createdProjectId,
        },
        {
          onProgress: (msg, prog) => {
            // 过滤重复消息
            if (msg.includes('续写') && msg === lastProgressMessageRef.current) {
              return;
            }
            lastProgressMessageRef.current = msg;
            setProgress(prog);
            setProgressMessage(msg);
          },
          onChunk: (chunk) => {
            appendStepContent('职业体系', chunk);
          },
          onResult: (result) => {
            console.log(`成功生成职业体系：主职业${result.main_careers_count}个，副职业${result.sub_careers_count}个`);
            setGenerationSteps(prev => ({ ...prev, careers: 'completed' }));
            completeStepWithResult('职业体系', result);
          },
          onError: (error) => {
            console.error('职业体系生成失败:', error);
            setErrorDetails(`职业体系生成失败: ${error}`);
            setGenerationSteps(prev => ({ ...prev, careers: 'error' }));
            errorStep('职业体系');
            setLoading(false);
            throw new Error(error);
          },
          onComplete: () => {
              // onResult 已打印完成日志
            }
          }
      );

      // 步骤3: 生成角色
      setGenerationSteps(prev => ({ ...prev, characters: 'processing' }));
      setProgressMessage('正在生成角色...');
      addNewStep('角色');

      await wizardStreamApi.generateCharactersStream(
        {
          project_id: createdProjectId,
          count: data.character_count,
          world_context: {
            time_period: worldResult.time_period || '',
            location: worldResult.location || '',
            atmosphere: worldResult.atmosphere || '',
            rules: worldResult.rules || '',
          },
          theme: data.theme,
          genre: genreString,
        },
        {
          onProgress: (msg, prog) => {
            // 过滤重复消息
            if (msg.includes('续写') && msg === lastProgressMessageRef.current) {
              return;
            }
            lastProgressMessageRef.current = msg;
            setProgress(prog);
            setProgressMessage(msg);
          },
          onChunk: (chunk) => {
            appendStepContent('角色', chunk);
          },
          onResult: (result) => {
            console.log(`成功生成${result.characters?.length || 0}个角色`);
            setGenerationSteps(prev => ({ ...prev, characters: 'completed' }));
            completeStepWithResult('角色', result);
          },
          onError: (error) => {
            console.error('角色生成失败:', error);
            setErrorDetails(`角色生成失败: ${error}`);
            setGenerationSteps(prev => ({ ...prev, characters: 'error' }));
            errorStep('角色');
            setLoading(false);
            throw new Error(error);
          },
          onComplete: () => {
              // onResult 已打印完成日志
            }
          }
      );

      // 步骤4: 生成大纲
      setGenerationSteps(prev => ({ ...prev, outline: 'processing' }));
      setProgressMessage('正在生成大纲...');
      addNewStep('大纲');

      await wizardStreamApi.generateCompleteOutlineStream(
        {
          project_id: createdProjectId,
          chapter_count: data.chapter_count,
          narrative_perspective: data.narrative_perspective,
          target_words: data.target_words,
        },
        {
          onProgress: (msg, prog) => {
            // 过滤重复消息
            if (msg.includes('续写') && msg === lastProgressMessageRef.current) {
              return;
            }
            lastProgressMessageRef.current = msg;
            setProgress(prog);
            setProgressMessage(msg);
          },
          onChunk: (chunk) => {
            appendStepContent('大纲', chunk);
          },
          onResult: (outlineResult) => {
            console.log('大纲生成完成');
            setGenerationSteps(prev => ({ ...prev, outline: 'completed' }));
            completeStepWithResult('大纲', outlineResult);
          },
          onError: (error) => {
            console.error('大纲生成失败:', error);
            setErrorDetails(`大纲生成失败: ${error}`);
            setGenerationSteps(prev => ({ ...prev, outline: 'error' }));
            errorStep('大纲');
            setLoading(false);
            throw new Error(error);
          },
          onComplete: () => {
              // onResult 已打印完成日志
            }
          }
      );

      // 全部完成 - 不自动跳转，显示保存按钮
      setProgress(100);
      setProgressMessage('所有内容生成完成！');
      setAllCompleted(true);
      setLoading(false);
      clearStorage();

    } catch (error) {
      const apiError = error as ApiError;
      const errorMsg = apiError.response?.data?.detail || apiError.message || '未知错误';
      console.error('创建项目失败:', errorMsg);
      setErrorDetails(errorMsg);
      message.error('创建项目失败：' + errorMsg);
      setLoading(false);
    }
  };

  // 智能重试：从失败的步骤继续生成
  const handleSmartRetry = async () => {
    if (!generationData) {
      message.warning('缺少生成数据');
      return;
    }

    setLoading(true);
    setErrorDetails('');

    try {
      if (generationSteps.worldBuilding === 'error') {
        message.info('从世界观步骤开始重新生成...');
        await retryFromWorldBuilding();
      } else if (generationSteps.careers === 'error') {
        message.info('从职业体系步骤继续生成...');
        await retryFromCareers();
      } else if (generationSteps.characters === 'error') {
        message.info('从角色步骤继续生成...');
        await retryFromCharacters();
      } else if (generationSteps.outline === 'error') {
        message.info('从大纲步骤继续生成...');
        await retryFromOutline();
      }
    } catch (error) {
      console.error('智能重试失败:', error);
      const errorMessage = error instanceof Error ? error.message : '未知错误';
      message.error('重试失败：' + errorMessage);
      setLoading(false);
    }
  };

  // 从世界观步骤重新开始
  const retryFromWorldBuilding = async () => {
    if (!generationData) return;

    setGenerationSteps(prev => ({ ...prev, worldBuilding: 'processing' }));
    setProgressMessage('重新生成世界观...');

    const genreString = Array.isArray(generationData.genre) ? generationData.genre.join('、') : generationData.genre;

    const worldResult = await wizardStreamApi.generateWorldBuildingStream(
      {
        title: generationData.title,
        description: generationData.description,
        theme: generationData.theme,
        genre: genreString,
        narrative_perspective: generationData.narrative_perspective,
        target_words: generationData.target_words,
        chapter_count: generationData.chapter_count,
        character_count: generationData.character_count,
        outline_mode: generationData.outline_mode || 'one-to-many',  // 传递大纲模式
      },
      {
        onProgress: (msg, prog) => {
          // 直接使用后端返回的进度值
          setProgress(prog);
          setProgressMessage(msg);
        },
        onResult: (result) => {
          setProjectId(result.project_id);
          setWorldBuildingResult(result);
          setGenerationSteps(prev => ({ ...prev, worldBuilding: 'completed' }));
        },
        onError: (error) => {
          console.error('世界观生成失败:', error);
          setErrorDetails(`世界观生成失败: ${error}`);
          setGenerationSteps(prev => ({ ...prev, worldBuilding: 'error' }));
          setLoading(false);
          throw new Error(error);
        },
        onComplete: () => {
          console.log('世界观重新生成完成');
        }
      }
    );

    if (!worldResult?.project_id) {
      throw new Error('项目创建失败：未获取到项目ID');
    }

    await continueFromCareers(worldResult);
  };

  // 从职业体系步骤继续
  const retryFromCareers = async () => {
    if (!worldBuildingResult) {
      message.warning('缺少必要数据，无法从职业体系步骤继续');
      setLoading(false);
      return;
    }

    const pid = worldBuildingResult.project_id || projectId;
    if (!pid) {
      message.warning('缺少项目ID，无法从职业体系步骤继续');
      setLoading(false);
      return;
    }

    setGenerationSteps(prev => ({ ...prev, careers: 'processing' }));
    setProgressMessage('重新生成职业体系...');

    await wizardStreamApi.generateCareerSystemStream(
      {
        project_id: pid,
      },
      {
        onProgress: (msg, prog) => {
          setProgress(prog);
          setProgressMessage(msg);
        },
        onResult: (result) => {
          console.log(`成功生成职业体系：主职业${result.main_careers_count}个，副职业${result.sub_careers_count}个`);
          setGenerationSteps(prev => ({ ...prev, careers: 'completed' }));
        },
        onError: (error) => {
          console.error('职业体系生成失败:', error);
          setErrorDetails(`职业体系生成失败: ${error}`);
          setGenerationSteps(prev => ({ ...prev, careers: 'error' }));
          setLoading(false);
          throw new Error(error);
        },
        onComplete: () => {
          console.log('职业体系重新生成完成');
        }
      }
    );

    await continueFromCharacters(worldBuildingResult);
  };

  // 从角色步骤继续
  const retryFromCharacters = async () => {
    if (!generationData || !worldBuildingResult) {
      message.warning('缺少必要数据，无法从角色步骤继续');
      setLoading(false);
      return;
    }

    // 优先使用 worldBuildingResult 中的 project_id，因为重试可能创建了新项目
    const pid = worldBuildingResult.project_id || projectId;
    if (!pid) {
      message.warning('缺少项目ID，无法从角色步骤继续');
      setLoading(false);
      return;
    }

    setGenerationSteps(prev => ({ ...prev, characters: 'processing' }));
    setProgressMessage('重新生成角色...');

    const genreString = Array.isArray(generationData.genre) ? generationData.genre.join('、') : generationData.genre;

    await wizardStreamApi.generateCharactersStream(
      {
        project_id: pid,
        count: generationData.character_count,
        world_context: {
          time_period: worldBuildingResult.time_period || '',
          location: worldBuildingResult.location || '',
          atmosphere: worldBuildingResult.atmosphere || '',
          rules: worldBuildingResult.rules || '',
        },
        theme: generationData.theme,
        genre: genreString,
      },
      {
        onProgress: (msg, prog) => {
          // 直接使用后端返回的进度值
          setProgress(prog);
          setProgressMessage(msg);
        },
        onResult: (result) => {
          console.log(`成功生成${result.characters?.length || 0}个角色`);
          setGenerationSteps(prev => ({ ...prev, characters: 'completed' }));
        },
        onError: (error) => {
          console.error('角色生成失败:', error);
          setErrorDetails(`角色生成失败: ${error}`);
          setGenerationSteps(prev => ({ ...prev, characters: 'error' }));
          setLoading(false);
          throw new Error(error);
        },
        onComplete: () => {
          console.log('角色重新生成完成');
        }
      }
    );

    await continueFromOutline(pid);
  };

  // 从大纲步骤继续
  const retryFromOutline = async () => {
    if (!generationData) {
      message.warning('缺少必要数据，无法从大纲步骤继续');
      setLoading(false);
      return;
    }

    // 优先使用 worldBuildingResult 中的 project_id，fallback 到状态中的 projectId
    const pid = (worldBuildingResult?.project_id) || projectId;
    if (!pid) {
      message.warning('缺少项目ID，无法从大纲步骤继续');
      setLoading(false);
      return;
    }

    setGenerationSteps(prev => ({ ...prev, outline: 'processing' }));
    setProgressMessage('重新生成大纲...');

    await wizardStreamApi.generateCompleteOutlineStream(
      {
        project_id: pid,
        chapter_count: generationData.chapter_count,
        narrative_perspective: generationData.narrative_perspective,
        target_words: generationData.target_words,
      },
      {
        onProgress: (msg, prog) => {
          // 直接使用后端返回的进度值
          setProgress(prog);
          setProgressMessage(msg);
        },
        onResult: () => {
          console.log('大纲生成完成');
          setGenerationSteps(prev => ({ ...prev, outline: 'completed' }));
        },
        onError: (error) => {
          console.error('大纲生成失败:', error);
          setErrorDetails(`大纲生成失败: ${error}`);
          setGenerationSteps(prev => ({ ...prev, outline: 'error' }));
          setLoading(false);
          throw new Error(error);
        },
        onComplete: () => {
          console.log('大纲重新生成完成');
        }
      }
    );

    setProgress(100);
    setProgressMessage('项目创建完成！正在跳转...');
    message.success('项目创建成功！正在进入项目...');
    setLoading(false);

    // 调用完成回调
    if (pid) {
      onComplete(pid);

      // 延迟1秒后自动跳转到项目详情页
      setTimeout(() => {
        navigate(`/project/${pid}`);
      }, 1000);
    }
  };

  // 从职业体系步骤开始的完整流程
  const continueFromCareers = async (worldResult: WorldBuildingResult) => {
    if (!generationData || !worldResult?.project_id) return;

    const pid = worldResult.project_id;

    setGenerationSteps(prev => ({ ...prev, careers: 'processing' }));
    setProgressMessage('正在生成职业体系...');

    await wizardStreamApi.generateCareerSystemStream(
      {
        project_id: pid,
      },
      {
        onProgress: (msg, prog) => {
          setProgress(prog);
          setProgressMessage(msg);
        },
        onResult: (result) => {
          console.log(`成功生成职业体系：主职业${result.main_careers_count}个，副职业${result.sub_careers_count}个`);
          setGenerationSteps(prev => ({ ...prev, careers: 'completed' }));
        },
        onError: (error) => {
          console.error('职业体系生成失败:', error);
          setErrorDetails(`职业体系生成失败: ${error}`);
          setGenerationSteps(prev => ({ ...prev, careers: 'error' }));
          setLoading(false);
          throw new Error(error);
        },
        onComplete: () => {
          console.log('职业体系生成完成');
        }
      }
    );

    await continueFromCharacters(worldResult);
  };

  // 从角色步骤开始的完整流程
  const continueFromCharacters = async (worldResult: WorldBuildingResult) => {
    if (!generationData || !worldResult?.project_id) return;

    const pid = worldResult.project_id;
    const genreString = Array.isArray(generationData.genre) ? generationData.genre.join('、') : generationData.genre;

    setGenerationSteps(prev => ({ ...prev, characters: 'processing' }));
    setProgressMessage('正在生成角色...');

    await wizardStreamApi.generateCharactersStream(
      {
        project_id: pid,
        count: generationData.character_count,
        world_context: {
          time_period: worldResult.time_period || '',
          location: worldResult.location || '',
          atmosphere: worldResult.atmosphere || '',
          rules: worldResult.rules || '',
        },
        theme: generationData.theme,
        genre: genreString,
      },
      {
        onProgress: (msg, prog) => {
          // 直接使用后端返回的进度值
          setProgress(prog);
          setProgressMessage(msg);
        },
        onResult: (result) => {
          console.log(`成功生成${result.characters?.length || 0}个角色`);
          setGenerationSteps(prev => ({ ...prev, characters: 'completed' }));
        },
        onError: (error) => {
          console.error('角色生成失败:', error);
          setErrorDetails(`角色生成失败: ${error}`);
          setGenerationSteps(prev => ({ ...prev, characters: 'error' }));
          setLoading(false);
          throw new Error(error);
        },
        onComplete: () => {
          console.log('角色生成完成');
        }
      }
    );

    await continueFromOutline(pid);
  };

  // 从大纲步骤开始的完整流程
  const continueFromOutline = async (pid: string) => {
    if (!generationData || !pid) return;

    setGenerationSteps(prev => ({ ...prev, outline: 'processing' }));
    setProgressMessage('正在生成大纲...');

    await wizardStreamApi.generateCompleteOutlineStream(
      {
        project_id: pid,
        chapter_count: generationData.chapter_count,
        narrative_perspective: generationData.narrative_perspective,
        target_words: generationData.target_words,
      },
      {
        onProgress: (msg, prog) => {
          // 直接使用后端返回的进度值
          setProgress(prog);
          setProgressMessage(msg);
        },
        onResult: () => {
          console.log('大纲生成完成');
          setGenerationSteps(prev => ({ ...prev, outline: 'completed' }));
        },
        onError: (error) => {
          console.error('大纲生成失败:', error);
          setErrorDetails(`大纲生成失败: ${error}`);
          setGenerationSteps(prev => ({ ...prev, outline: 'error' }));
          setLoading(false);
          throw new Error(error);
        },
        onComplete: () => {
          console.log('大纲生成完成');
        }
      }
    );

    setProgress(100);
    setProgressMessage('项目创建完成！正在跳转...');
    message.success('项目创建成功！正在进入项目...');
    setLoading(false);

    // 调用完成回调
    if (pid) {
      onComplete(pid);

      // 延迟1秒后自动跳转到项目详情页
      setTimeout(() => {
        navigate(`/project/${pid}`);
      }, 1000);
    }
  };


  // 获取步骤状态图标和颜色
  const getStepStatus = (step: GenerationStep) => {
    if (step === 'completed') return { icon: <CheckCircleOutlined />, color: 'var(--color-success)' };
    if (step === 'processing') return { icon: <LoadingOutlined />, color: 'var(--color-primary)' };
    if (step === 'error') return { icon: '✗', color: 'var(--color-error)' };
    return { icon: '○', color: 'var(--color-text-quaternary)' };
  };

  const hasError = generationSteps.worldBuilding === 'error' ||
    generationSteps.careers === 'error' ||
    generationSteps.characters === 'error' ||
    generationSteps.outline === 'error';

  // 渲染单个步骤内容窗口
  const renderStepContentWindow = (stepItem: StepContent, index: number) => {
    const displayName = stepDisplayNames[stepItem.stepName] || stepItem.stepName;
    const statusIcon = stepItem.status === 'completed' ? <CheckCircleOutlined style={{ color: 'var(--color-success)' }} />
      : stepItem.status === 'processing' ? <LoadingOutlined style={{ color: 'var(--color-primary)' }} />
      : stepItem.status === 'error' ? <Text style={{ color: 'var(--color-error)' }}>✗</Text>
      : <Text style={{ color: 'var(--color-text-quaternary)' }}>○</Text>;

    const collapseIcon = stepItem.isCollapsed ? <ExpandOutlined /> : <CompressOutlined />;

    // 格式化显示内容（根据步骤状态决定格式化方式）
    // 完成状态：直接显示已格式化的内容
    // 处理中状态：尝试解析JSON，否则显示友好提示
    const displayContent = stepItem.status === 'completed'
      ? (stepItem.content || '等待生成...')
      : formatStreamingContent(stepItem.stepName, stepItem.content);

    return (
      <Card
        key={index}
        size="small"
        style={{
          marginBottom: 12,
          border: stepItem.status === 'processing' ? '2px solid var(--color-primary)' : '1px solid var(--color-border)'
        }}
        styles={{ body: { padding: 0 } }}
      >
        {/* 标题栏 - 可点击折叠 */}
        <div
          onClick={() => toggleStepCollapse(stepItem.stepName)}
          style={{
            padding: '10px 16px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: stepItem.isCollapsed ? 'none' : '1px solid var(--color-border)',
            background: stepItem.status === 'completed' ? 'var(--color-success-bg)' : 'transparent'
          }}
        >
          <Space>
            <Text strong>{displayName}</Text>
            {statusIcon}
            {stepItem.status === 'completed' && (
              <Tag color="success" style={{ marginLeft: 8 }}>完成</Tag>
            )}
          </Space>
          <Space>
            {stepItem.status === 'processing' && <LoadingOutlined spin />}
            {collapseIcon}
          </Space>
        </div>

        {/* 使用智能滚动的内容窗口组件 */}
        <StreamingContentWindow
          stepItem={stepItem}
          displayContent={displayContent}
          isMobile={isMobile}
          startEdit={() => startEditStep(stepItem.stepName)}
          cancelEdit={() => cancelEditStep(stepItem.stepName)}
          saveEdit={() => saveEditContent(stepItem.stepName)}
          updateEditContent={(content) => updateEditContent(stepItem.stepName, content)}
          incrementalData={incrementalRenderData[stepItem.stepName]}
        />
      </Card>
    );
  };

  // 处理保存并跳转
  const handleSaveAndNavigate = () => {
    if (!projectId) {
      message.error('项目ID不存在');
      return;
    }
    message.success('项目创建成功！正在进入项目...');
    onComplete(projectId);
    setTimeout(() => {
      navigate(`/project/${projectId}`);
    }, 500);
  };

  // 渲染生成进度页面 - 左右分栏布局
  const renderGenerating = () => {
    // 移动端使用单栏布局
    if (isMobile) {
      return (
        <div style={{
          padding: '16px 12px',
          maxWidth: '100%',
        }}>
          <Title level={4} style={{ marginBottom: 16, textAlign: 'center' }}>
            {allCompleted ? '内容生成完成' : `正在为《${config.title}》生成内容`}
          </Title>

          {/* 进度条 */}
          <Card style={{ marginBottom: 16 }}>
            <Progress
              percent={progress}
              status={hasError ? 'exception' : (progress === 100 ? 'success' : 'active')}
              strokeColor={{
                '0%': 'var(--color-primary)',
                '100%': 'var(--color-primary-active)',
              }}
              style={{ marginBottom: 12 }}
            />
            <Paragraph style={{ fontSize: 14, color: hasError ? 'var(--color-error)' : 'var(--color-text-secondary)' }}>
              {progressMessage}
            </Paragraph>

            {/* 步骤状态 */}
            <Space direction="vertical" size={6} style={{ width: '100%' }}>
              {[
                { key: 'worldBuilding', label: '世界观', step: generationSteps.worldBuilding },
                { key: 'careers', label: '职业体系', step: generationSteps.careers },
                { key: 'characters', label: '角色', step: generationSteps.characters },
                { key: 'outline', label: '大纲', step: generationSteps.outline },
              ].map(({ key, label, step }) => {
                const status = getStepStatus(step);
                return (
                  <div key={key} style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    background: step === 'processing' ? 'var(--color-info-bg)' : (step === 'error' ? 'var(--color-error-bg)' : 'var(--color-bg-layout)'),
                    borderRadius: 6,
                    border: `1px solid ${step === 'processing' ? 'var(--color-info-border)' : (step === 'error' ? 'var(--color-error-border)' : 'var(--color-border-secondary)')}`,
                  }}>
                    <Text style={{ fontSize: 13, fontWeight: step === 'processing' ? 600 : 400 }}>{label}</Text>
                    <span style={{ fontSize: 16, color: status.color }}>{status.icon}</span>
                  </div>
                );
              })}
            </Space>
          </Card>

          {/* 流式内容窗口区域 */}
          {stepContents.length > 0 && (
            <Card style={{ marginBottom: 16 }} title={<Text strong>实时生成内容</Text>}>
              <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                {stepContents.map((stepItem, index) => renderStepContentWindow(stepItem, index))}
              </div>
            </Card>
          )}

          {/* 错误详情 */}
          {errorDetails && (
            <Card size="small" style={{ marginBottom: 16, background: 'var(--color-error-bg)', borderColor: 'var(--color-error-border)' }}>
              <Text strong style={{ color: 'var(--color-error)' }}>错误详情：</Text>
              <Text style={{ color: 'var(--color-text-secondary)', fontSize: 13 }}>{errorDetails}</Text>
            </Card>
          )}

          {/* 按钮区域 */}
          <Space size="middle" style={{ width: '100%', justifyContent: 'center' }}>
            {hasError && (
              <Button type="primary" onClick={handleSmartRetry} loading={loading} disabled={loading}>
                智能重试
              </Button>
            )}
            {allCompleted && (
              <Button type="primary" icon={<SaveOutlined />} onClick={handleSaveAndNavigate}>
                保存并进入项目
              </Button>
            )}
          </Space>
        </div>
      );
    }

    // 桌面端使用左右分栏布局
    return (
      <div style={{
        padding: '40px 24px',
        maxWidth: '100%',
        height: 'calc(100vh - 120px)',
      }}>
        <Title level={3} style={{ marginBottom: 24, textAlign: 'center' }}>
          {allCompleted ? '内容生成完成' : `正在为《${config.title}》生成内容`}
        </Title>

        {/* 左右分栏容器 */}
        <div style={{
          display: 'flex',
          gap: 24,
          height: 'calc(100% - 60px)',
        }}>
          {/* 左侧：进度和步骤状态 */}
          <Card
            style={{
              width: '320px',
              flexShrink: 0,
              display: 'flex',
              flexDirection: 'column',
            }}
            styles={{ body: { flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' } }}
          >
            {/* 进度条 */}
            <Progress
              percent={progress}
              status={hasError ? 'exception' : (progress === 100 ? 'success' : 'active')}
              strokeColor={{
                '0%': 'var(--color-primary)',
                '100%': 'var(--color-primary-active)',
              }}
              style={{ marginBottom: 16 }}
            />

            <Paragraph
              style={{
                fontSize: 15,
                marginBottom: 16,
                color: hasError ? 'var(--color-error)' : 'var(--color-text-secondary)',
                textAlign: 'center',
              }}
            >
              {progressMessage}
            </Paragraph>

            {/* 步骤状态指示器 */}
            <Space direction="vertical" size={8} style={{ width: '100%', flex: 1 }}>
              {[
                { key: 'worldBuilding', label: '世界观', step: generationSteps.worldBuilding },
                { key: 'careers', label: '职业体系', step: generationSteps.careers },
                { key: 'characters', label: '角色', step: generationSteps.characters },
                { key: 'outline', label: '大纲', step: generationSteps.outline },
              ].map(({ key, label, step }) => {
                const status = getStepStatus(step);
                return (
                  <div
                    key={key}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '10px 16px',
                      background: step === 'processing' ? 'var(--color-info-bg)' : (step === 'error' ? 'var(--color-error-bg)' : 'var(--color-bg-layout)'),
                      borderRadius: 6,
                      border: `1px solid ${step === 'processing' ? 'var(--color-info-border)' : (step === 'error' ? 'var(--color-error-border)' : 'var(--color-border-secondary)')}`,
                    }}
                  >
                    <Text style={{ fontSize: 15, fontWeight: step === 'processing' ? 600 : 400 }}>
                      {label}
                    </Text>
                    <span style={{ fontSize: 18, color: status.color }}>
                      {status.icon}
                    </span>
                  </div>
                );
              })}
            </Space>

            {/* 错误详情 */}
            {errorDetails && (
              <Card
                size="small"
                style={{
                  marginTop: 16,
                  background: 'var(--color-error-bg)',
                  borderColor: 'var(--color-error-border)',
                }}
              >
                <Text strong style={{ color: 'var(--color-error)' }}>错误详情：</Text>
                <br />
                <Text style={{ color: 'var(--color-text-secondary)', fontSize: 14 }}>
                  {errorDetails}
                </Text>
              </Card>
            )}

            {/* 按钮区域 */}
            <Space direction="vertical" style={{ width: '100%', marginTop: 16 }}>
              {hasError && (
                <Button
                  type="primary"
                  block
                  onClick={handleSmartRetry}
                  loading={loading}
                  disabled={loading}
                >
                  智能重试
                </Button>
              )}
              {allCompleted && (
                <Button
                  type="primary"
                  block
                  icon={<SaveOutlined />}
                  onClick={handleSaveAndNavigate}
                >
                  保存并进入项目
                </Button>
              )}
            </Space>
          </Card>

          {/* 右侧：实时生成内容窗口 */}
          <Card
            style={{
              flex: 1,
              minWidth: 0,
              display: 'flex',
              flexDirection: 'column',
            }}
            styles={{
              body: {
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
                padding: '12px 16px',
              }
            }}
            title={<Text strong>实时生成内容</Text>}
          >
            <div style={{ flex: 1, overflowY: 'auto', paddingRight: 8 }}>
              {stepContents.length === 0 ? (
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: '100%',
                  color: 'var(--color-text-quaternary)',
                }}>
                  <Text>等待开始生成...</Text>
                </div>
              ) : (
                stepContents.map((stepItem, index) => renderStepContentWindow(stepItem, index))
              )}
            </div>
          </Card>
        </div>
      </div>
    );
  };

  return renderGenerating();
};