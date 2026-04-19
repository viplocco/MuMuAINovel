/**
 * 动态数组元素编辑器
 * 用于编辑 PowerLevelElement、PhilosophyElement 等结构化数组字段
 */
import React from 'react';
import { Form, Input, Select, Button, Space, Card, Typography } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';

interface ArrayFieldConfig {
  name: string;           // 字段名
  label: string;          // 显示标签
  type: 'text' | 'textarea' | 'select';
  required?: boolean;
  placeholder?: string;
  options?: { label: string; value: string }[];
  rows?: number;          // textarea 行数
  width?: string | number;
}

interface DynamicArrayEditorProps {
  name: string[];         // Form.List 路径，如 ['physical', 'space', 'key_locations']
  label: string;          // 面板标题
  maxCount?: number;      // 最大数量，默认不限
  fields: ArrayFieldConfig[];
  defaultItem: Record<string, unknown>;
  itemTitle?: (item: any, index: number) => string;  // 每项的标题生成函数
  compact?: boolean;      // 紧凑模式（无卡片包装）
}

const DynamicArrayEditor: React.FC<DynamicArrayEditorProps> = ({
  name,
  label,
  maxCount,
  fields,
  defaultItem,
  itemTitle,
  compact = false,
}) => {
  return (
    <Form.List name={name}>
      {(fieldsList, { add, remove }) => (
        <div>
          <Typography.Title level={5} style={{ marginBottom: 12 }}>
            {label}
          </Typography.Title>

          {fieldsList.map((field, index) => (
            compact ? (
              // 紧凑模式：直接渲染字段
              <div key={field.key} style={{ marginBottom: 8 }}>
                <Space align="start" style={{ width: '100%', flexWrap: 'wrap' }}>
                  {fields.map((f) => (
                    <Form.Item
                      key={`${field.key}-${f.name}`}
                      name={[field.name, f.name]}
                      label={f.label}
                      rules={f.required ? [{ required: true, message: `请输入${f.label}` }] : []}
                      style={{ marginBottom: 0, minWidth: f.width || 120 }}
                    >
                      {f.type === 'text' ? (
                        <Input placeholder={f.placeholder} style={{ width: f.width || 'auto' }} />
                      ) : f.type === 'textarea' ? (
                        <Input.TextArea rows={f.rows || 2} placeholder={f.placeholder} style={{ width: f.width || 'auto' }} />
                      ) : (
                        <Select placeholder={f.placeholder} options={f.options} style={{ width: f.width || 'auto' }} />
                      )}
                    </Form.Item>
                  ))}
                  <Button
                    type="text"
                    danger
                    icon={<DeleteOutlined />}
                    onClick={() => remove(field.name)}
                    style={{ marginTop: 4 }}
                  />
                </Space>
              </div>
            ) : (
              // 卡片模式：包装每项
              <Card
                key={field.key}
                size="small"
                title={itemTitle ? itemTitle(field as any, index) : `第 ${index + 1} 项`}
                extra={
                  <Button
                    type="text"
                    danger
                    size="small"
                    icon={<DeleteOutlined />}
                    onClick={() => remove(field.name)}
                  />
                }
                style={{ marginBottom: 12 }}
              >
                {fields.map((f) => (
                  <Form.Item
                    key={`${field.key}-${f.name}`}
                    name={[field.name, f.name]}
                    label={f.label}
                    rules={f.required ? [{ required: true, message: `请输入${f.label}` }] : []}
                  >
                    {f.type === 'text' ? (
                      <Input placeholder={f.placeholder} />
                    ) : f.type === 'textarea' ? (
                      <Input.TextArea rows={f.rows || 2} placeholder={f.placeholder} />
                    ) : (
                      <Select placeholder={f.placeholder} options={f.options} />
                    )}
                  </Form.Item>
                ))}
              </Card>
            )
          ))}

          {(!maxCount || fieldsList.length < maxCount) && (
            <Button
              type="dashed"
              onClick={() => add(defaultItem)}
              block
              icon={<PlusOutlined />}
            >
              添加{label}
            </Button>
          )}

          {maxCount && fieldsList.length >= maxCount && (
            <Typography.Text type="secondary">
              已达到最大数量限制（{maxCount}个）
            </Typography.Text>
          )}
        </div>
      )}
    </Form.List>
  );
};

export default DynamicArrayEditor;