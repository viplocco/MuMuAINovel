/**
 * 动态能力属性编辑器
 * 根据项目的 attribute_schema 动态渲染不同类型的属性编辑控件
 */
import React from 'react';
import { Form, InputNumber, Select, Tag, Space, Typography } from 'antd';

const { Text } = Typography;

// 属性值类型定义
export interface AttributeValue {
  type: 'numeric' | 'stage' | 'combo_select';
  value?: number;
  name?: string;
  elements?: string[];
  quality?: string;
  rank?: string;
  growth_rate?: number;
}

// 属性配置类型定义
export interface AttributeConfig {
  type: 'numeric' | 'stage' | 'combo_select';
  name: string;
  min?: number;
  max?: number;
  default?: number | string[];
  stages?: string[];
  elements?: Record<string, { name?: string; color?: string; traits?: string }>;
  max_select?: number;
  quality_config?: Record<number, { name: string; rank: string; growth_rate: number }>;
  hidden?: boolean;
  optional?: boolean;
  unit?: string;
}

// Schema 类型定义
export interface AttributeSchema {
  attributes: Record<string, AttributeConfig>;
  display_order: string[];
  primary_attribute?: string;
}

interface Props {
  attributeSchema: AttributeSchema | null;
  values: Record<string, AttributeValue> | null;
  onChange: (values: Record<string, AttributeValue>) => void;
  disabled?: boolean;
}

/**
 * 数值型属性编辑器
 */
const NumericAttributeEditor: React.FC<{
  attrName: string;
  config: AttributeConfig;
  value: AttributeValue;
  onChange: (value: AttributeValue) => void;
  disabled?: boolean;
}> = ({ attrName, config, value, onChange, disabled }) => {
  const numericValue = typeof value?.value === 'number' ? value.value : (typeof config.default === 'number' ? config.default : 50);

  const inputNumber = (
    <InputNumber
      min={config.min ?? 0}
      max={config.max ?? 100}
      value={numericValue}
      onChange={(val) => onChange({ type: 'numeric', value: val ?? 0 })}
      disabled={disabled}
      style={{ width: config.unit ? 'calc(100% - 40px)' : '100%' }}
    />
  );

  return (
    <Form.Item label={config.name || attrName}>
      {config.unit ? (
        <Space.Compact style={{ width: '100%' }}>
          {inputNumber}
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            padding: '0 11px',
            backgroundColor: 'var(--ant-color-fill-alter)',
            border: '1px solid var(--ant-color-border)',
            borderLeft: 'none',
            borderRadius: '0 6px 6px 0',
            height: 32,
            fontSize: 14,
            color: 'var(--ant-color-text-secondary)'
          }}>
            {config.unit}
          </span>
        </Space.Compact>
      ) : inputNumber}
    </Form.Item>
  );
};

/**
 * 阶段型属性编辑器
 */
const StageAttributeEditor: React.FC<{
  attrName: string;
  config: AttributeConfig;
  value: AttributeValue;
  onChange: (value: AttributeValue) => void;
  disabled?: boolean;
}> = ({ attrName, config, value, onChange, disabled }) => {
  const stages = config.stages || [];
  const defaultStage = typeof config.default === 'number' ? config.default : 1;

  return (
    <Form.Item label={config.name || attrName}>
      <Select
        value={value?.value ?? defaultStage}
        onChange={(val: number) => {
          const stageName = stages[val - 1] || `第${val}阶`;
          onChange({ type: 'stage', value: val, name: stageName });
        }}
        disabled={disabled}
        style={{ width: '100%' }}
      >
        {stages.map((stage, index) => (
          <Select.Option key={index + 1} value={index + 1}>
            {index + 1}阶 - {stage}
          </Select.Option>
        ))}
      </Select>
    </Form.Item>
  );
};

/**
 * 组合选择型属性编辑器（灵根、血脉等）
 */
const ComboSelectAttributeEditor: React.FC<{
  attrName: string;
  config: AttributeConfig;
  value: AttributeValue;
  onChange: (value: AttributeValue) => void;
  disabled?: boolean;
}> = ({ attrName, config, value, onChange, disabled }) => {
  const elements = config.elements || {};
  const maxSelect = config.max_select || 9;
  const qualityConfig = config.quality_config;

  const selectedElements = value?.elements || [];
  const quality = value?.quality;

  const toggleElement = (elementKey: string) => {
    let newElements: string[];
    if (selectedElements.includes(elementKey)) {
      // 取消选择
      newElements = selectedElements.filter((e) => e !== elementKey);
    } else {
      // 添加选择
      if (selectedElements.length >= maxSelect) {
        return; // 已达最大数量
      }
      newElements = [...selectedElements, elementKey];
    }

    // 计算品质
    let newQuality = '';
    let newRank = '';
    let newGrowthRate = 1;

    if (qualityConfig && newElements.length > 0) {
      const qualityInfo = qualityConfig[newElements.length];
      if (qualityInfo) {
        newQuality = qualityInfo.name;
        newRank = qualityInfo.rank;
        newGrowthRate = qualityInfo.growth_rate;
      }
    }

    onChange({
      type: 'combo_select',
      elements: newElements,
      quality: newQuality,
      rank: newRank,
      growth_rate: newGrowthRate,
    });
  };

  return (
    <Form.Item
      label={
        <Space>
          {config.name || attrName}
          {quality && <Tag color="blue">{quality}</Tag>}
          {value?.growth_rate && value.growth_rate > 1 && (
            <Tag color="gold">修炼速度 {value.growth_rate}x</Tag>
          )}
        </Space>
      }
    >
      <div>
        <div style={{ marginBottom: 8 }}>
          <Text type="secondary">
            已选择: {selectedElements.length > 0 ? selectedElements.join(' + ') : '无'}
            {selectedElements.length > 0 && ` (最多${maxSelect}种)`}
          </Text>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          {Object.entries(elements).map(([key, elem]) => {
            const isSelected = selectedElements.includes(key);
            return (
              <Tag
                key={key}
                color={isSelected ? (elem.color || 'blue') : 'default'}
                style={{
                  cursor: disabled ? 'not-allowed' : 'pointer',
                  opacity: disabled ? 0.5 : 1,
                  borderWidth: isSelected ? 2 : 1,
                }}
                onClick={() => !disabled && toggleElement(key)}
              >
                {elem.name || key}
              </Tag>
            );
          })}
        </div>
      </div>
    </Form.Item>
  );
};

/**
 * 动态能力属性编辑器主组件
 */
const DynamicAttributesEditor: React.FC<Props> = ({
  attributeSchema,
  values,
  onChange,
  disabled = false,
}) => {
  if (!attributeSchema) {
    return (
      <Text type="secondary">该项目尚未配置能力属性体系</Text>
    );
  }

  const { attributes: attributesConfig, display_order } = attributeSchema;

  // 按display_order排序
  const sortedAttrNames = display_order || Object.keys(attributesConfig);

  const handleAttrChange = (attrName: string, newValue: AttributeValue) => {
    const newValues = {
      ...(values || {}),
      [attrName]: newValue,
    };
    onChange(newValues);
  };

  return (
    <div>
      {sortedAttrNames.map((attrName) => {
        const config = attributesConfig[attrName];
        if (!config) return null;

        // 跳过隐藏属性
        if (config.hidden) return null;

        // 根据类型构建正确的默认值
        let currentValue: AttributeValue;
        if (values?.[attrName]) {
          currentValue = values[attrName];
        } else {
          // 创建类型正确的默认值
          if (config.type === 'numeric') {
            currentValue = {
              type: 'numeric',
              value: typeof config.default === 'number' ? config.default : 50,
            };
          } else if (config.type === 'stage') {
            currentValue = {
              type: 'stage',
              value: typeof config.default === 'number' ? config.default : 1,
              name: config.stages?.[(typeof config.default === 'number' ? config.default : 1) - 1] || '第一阶段',
            };
          } else if (config.type === 'combo_select') {
            const defaultElements = Array.isArray(config.default) ? config.default : [];
            currentValue = {
              type: 'combo_select',
              elements: defaultElements,
            };
          } else {
            currentValue = { type: config.type, value: undefined };
          }
        }

        switch (config.type) {
          case 'numeric':
            return (
              <NumericAttributeEditor
                key={attrName}
                attrName={attrName}
                config={config}
                value={currentValue}
                onChange={(val) => handleAttrChange(attrName, val)}
                disabled={disabled}
              />
            );

          case 'stage':
            return (
              <StageAttributeEditor
                key={attrName}
                attrName={attrName}
                config={config}
                value={currentValue}
                onChange={(val) => handleAttrChange(attrName, val)}
                disabled={disabled}
              />
            );

          case 'combo_select':
            return (
              <ComboSelectAttributeEditor
                key={attrName}
                attrName={attrName}
                config={config}
                value={currentValue}
                onChange={(val) => handleAttrChange(attrName, val)}
                disabled={disabled}
              />
            );

          default:
            return null;
        }
      })}
    </div>
  );
};

export default DynamicAttributesEditor;