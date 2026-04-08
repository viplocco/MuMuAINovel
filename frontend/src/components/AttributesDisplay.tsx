/**
 * 能力值可视化展示组件
 * 用于在角色卡片、角色详情等地方展示能力值
 */
import React from 'react';
import { Tag, Space, Typography, Progress } from 'antd';
import type { AttributeValue, AttributeSchema, AttributeConfig } from './DynamicAttributesEditor';

const { Text } = Typography;

interface Props {
  attributeSchema: AttributeSchema | null;
  values: Record<string, AttributeValue> | null;
  compact?: boolean; // 紧凑模式，只显示主要属性
  maxItems?: number; // 最多显示多少个属性
}

/**
 * 单个能力值展示
 */
const AttributeDisplay: React.FC<{
  attrName: string;
  config: AttributeConfig;
  value: AttributeValue;
}> = ({ attrName, config, value }) => {
  if (!value) return null;

  switch (value.type) {
    case 'numeric':
      return (
        <Tag key={attrName}>
          {config.name || attrName}: {value.value}
          {config.unit && config.unit}
        </Tag>
      );

    case 'stage':
      return (
        <Tag key={attrName} color="blue">
          {config.name || attrName}: {value.name || `第${value.value}阶`}
        </Tag>
      );

    case 'combo_select': {
      const elements = value.elements || [];
      return (
        <Tag key={attrName} color="purple">
          {config.name || attrName}: {elements.join('+')}
          {value.quality && ` (${value.quality})`}
        </Tag>
      );
    }

    default:
      return null;
  }
};

/**
 * 能力值展示主组件
 */
const AttributesDisplay: React.FC<Props> = ({
  attributeSchema,
  values,
  compact = false,
  maxItems = 5,
}) => {
  if (!attributeSchema || !values) {
    return <Text type="secondary">暂无能力值</Text>;
  }

  const { attributes: attributesConfig, display_order } = attributeSchema;
  const sortedAttrNames = display_order || Object.keys(attributesConfig);

  // 过滤隐藏属性
  const visibleAttrs = sortedAttrNames.filter((name) => {
    const config = attributesConfig[name];
    return config && !config.hidden;
  });

  // 限制显示数量
  const displayAttrs = compact ? visibleAttrs.slice(0, maxItems) : visibleAttrs;

  return (
    <Space wrap size={[4, 4]}>
      {displayAttrs.map((attrName) => {
        const config = attributesConfig[attrName];
        const value = values[attrName];
        if (!config || !value) return null;

        return (
          <AttributeDisplay
            key={attrName}
            attrName={attrName}
            config={config}
            value={value}
          />
        );
      })}
      {compact && visibleAttrs.length > maxItems && (
        <Text type="secondary">+{visibleAttrs.length - maxItems}项</Text>
      )}
    </Space>
  );
};

/**
 * 能力值详情展示（带进度条）
 */
export const AttributesDetailDisplay: React.FC<{
  attributeSchema: AttributeSchema | null;
  values: Record<string, AttributeValue> | null;
}> = ({ attributeSchema, values }) => {
  if (!attributeSchema || !values) {
    return <Text type="secondary">暂无能力值</Text>;
  }

  const { attributes: attributesConfig, display_order } = attributeSchema;
  const sortedAttrNames = display_order || Object.keys(attributesConfig);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {sortedAttrNames.map((attrName) => {
        const config = attributesConfig[attrName];
        const value = values[attrName];
        if (!config || !value || config.hidden) return null;

        if (value.type === 'numeric') {
          const percent = Math.round(
            ((value.value || 0) / (config.max || 100)) * 100
          );
          return (
            <div key={attrName}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text>{config.name || attrName}</Text>
                <Text>
                  {value.value}
                  {config.unit && config.unit}
                </Text>
              </div>
              <Progress percent={percent} size="small" showInfo={false} />
            </div>
          );
        }

        if (value.type === 'stage') {
          const percent = Math.round(
            ((value.value || 1) / (config.stages?.length || 10)) * 100
          );
          return (
            <div key={attrName}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text>{config.name || attrName}</Text>
                <Text type="success">{value.name || `第${value.value}阶`}</Text>
              </div>
              <Progress percent={percent} size="small" showInfo={false} strokeColor="#1890ff" />
            </div>
          );
        }

        if (value.type === 'combo_select') {
          const elements = value.elements || [];
          return (
            <div key={attrName}>
              <Text>{config.name || attrName}: </Text>
              <Space wrap size={[4, 4]}>
                {elements.map((el) => {
                  const elemConfig = config.elements?.[el];
                  return (
                    <Tag key={el} color={elemConfig?.color || 'blue'}>
                      {elemConfig?.name || el}
                    </Tag>
                  );
                })}
              </Space>
              {value.quality && (
                <Tag color="gold" style={{ marginLeft: 4 }}>
                  {value.quality}
                </Tag>
              )}
              {value.growth_rate && value.growth_rate > 1 && (
                <Text type="secondary" style={{ marginLeft: 8 }}>
                  修炼速度 {value.growth_rate}x
                </Text>
              )}
            </div>
          );
        }

        return null;
      })}
    </div>
  );
};

export default AttributesDisplay;