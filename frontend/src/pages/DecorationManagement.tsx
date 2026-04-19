import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card, Button, Form, Select, Switch, Input, Space, Typography,
  Divider, Row, Col, theme, App, Spin
} from 'antd';
import {
  ArrowLeftOutlined, SaveOutlined, BgColorsOutlined,
  GlobalOutlined, LockOutlined
} from '@ant-design/icons';
import { decorationApi, authApi } from '../services/api';
import type { User } from '../types';
import UserMenu from '../components/UserMenu';

const { Title, Text, Paragraph } = Typography;

// 装饰类型选项
const DECORATION_OPTIONS = [
  { value: 'auto', label: '自动（根据日期）', icon: '📅' },
  { value: 'spring-festival', label: '春节', icon: '🧨' },
  { value: 'spring', label: '春天', icon: '🌸' },
  { value: 'summer', label: '夏天', icon: '☀️' },
  { value: 'autumn', label: '秋天', icon: '🍂' },
  { value: 'winter', label: '冬天', icon: '❄️' },
  { value: 'none', label: '无装饰', icon: '✨' },
];

export default function DecorationManagement() {
  const navigate = useNavigate();
  const { token } = theme.useToken();
  const { message: msg } = App.useApp();
  // currentUser 用于验证管理员权限（loadCurrentUser 中检查 is_admin）
  const [, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  // 颜色混合函数
  const alphaColor = (color: string, alpha: number) =>
    `color-mix(in srgb, ${color} ${(alpha * 100).toFixed(0)}%, transparent)`;

  const isMobile = window.innerWidth <= 768;

  useEffect(() => {
    loadCurrentUser();
    loadConfig();
  }, []);

  const loadCurrentUser = async () => {
    try {
      const user = await authApi.getCurrentUser();
      setCurrentUser(user);
      if (!user.is_admin) {
        msg.warning('只有管理员可以访问装饰管理');
        navigate('/');
      }
    } catch {
      navigate('/login');
    }
  };

  const loadConfig = async () => {
    setLoading(true);
    try {
      const config = await decorationApi.getAdminConfig();
      form.setFieldsValue({
        decoration_type: config.decoration_type,
        force_enabled: config.force_enabled,
        description: config.description,
      });
    } catch {
      msg.error('加载装饰配置失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (values: {
    decoration_type: string;
    force_enabled: boolean;
    description?: string;
  }) => {
    setSaving(true);
    try {
      await decorationApi.updateConfig(values);
      msg.success('装饰配置已保存，所有用户将在刷新页面后生效');
    } catch {
      msg.error('保存装饰配置失败');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{
      height: '100vh',
      background: `linear-gradient(180deg, ${token.colorBgLayout} 0%, ${alphaColor(token.colorPrimary, 0.08)} 100%)`,
      padding: isMobile ? '20px 16px' : '40px 24px',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
    }}>
      <div style={{
        maxWidth: 1400,
        margin: '0 auto',
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}>
        {/* 顶部导航卡片 */}
        <Card
          variant="borderless"
          style={{
            background: `linear-gradient(135deg, ${token.colorPrimary} 0%, ${alphaColor(token.colorPrimary, 0.8)} 50%, ${token.colorPrimaryHover} 100%)`,
            borderRadius: isMobile ? 16 : 24,
            boxShadow: `0 12px 40px ${alphaColor(token.colorPrimary, 0.25)}, 0 4px 12px ${alphaColor(token.colorText, 0.08)}`,
            marginBottom: isMobile ? 20 : 24,
            border: 'none',
            position: 'relative',
            overflow: 'hidden'
          }}
        >
          {/* 装饰性背景元素 */}
          <div style={{ position: 'absolute', top: -60, right: -60, width: 200, height: 200, borderRadius: '50%', background: alphaColor(token.colorWhite, 0.08), pointerEvents: 'none' }} />
          <div style={{ position: 'absolute', bottom: -40, left: '30%', width: 120, height: 120, borderRadius: '50%', background: alphaColor(token.colorWhite, 0.05), pointerEvents: 'none' }} />
          <div style={{ position: 'absolute', top: '50%', right: '15%', width: 80, height: 80, borderRadius: '50%', background: alphaColor(token.colorWhite, 0.06), pointerEvents: 'none' }} />

          <Row align="middle" justify="space-between" gutter={[16, 16]} style={{ position: 'relative', zIndex: 1 }}>
            <Col xs={24} sm={12}>
              <Space direction="vertical" size={4}>
                <Title level={isMobile ? 3 : 2} style={{ margin: 0, color: token.colorWhite, textShadow: `0 2px 4px ${alphaColor(token.colorText, 0.2)}` }}>
                  <BgColorsOutlined style={{ color: alphaColor(token.colorWhite, 0.9), marginRight: 12 }} />
                  装饰管理
                </Title>
                <Text style={{ fontSize: isMobile ? 12 : 14, color: alphaColor(token.colorWhite, 0.85) }}>
                  管理系统季节装饰和主题外观
                </Text>
              </Space>
            </Col>
            <Col xs={24} sm={12}>
              <Space size={12} style={{ display: 'flex', justifyContent: isMobile ? 'flex-start' : 'flex-end', width: '100%' }}>
                <Button
                  icon={<ArrowLeftOutlined />}
                  onClick={() => navigate('/')}
                  style={{
                    borderRadius: 12,
                    background: alphaColor(token.colorWhite, 0.15),
                    border: `1px solid ${alphaColor(token.colorWhite, 0.3)}`,
                    boxShadow: `0 2px 8px ${alphaColor(token.colorText, 0.15)}`,
                    color: token.colorWhite,
                    backdropFilter: 'blur(10px)',
                    transition: 'all 0.3s ease'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = alphaColor(token.colorWhite, 0.25);
                    e.currentTarget.style.transform = 'translateY(-1px)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = alphaColor(token.colorWhite, 0.15);
                    e.currentTarget.style.transform = 'none';
                  }}
                >
                  返回主页
                </Button>
                <UserMenu />
              </Space>
            </Col>
          </Row>
        </Card>

        {/* 主内容卡片 */}
        <Card
          variant="borderless"
          style={{
            background: alphaColor(token.colorBgContainer, 0.72),
            borderRadius: isMobile ? 16 : 24,
            border: `1px solid ${alphaColor(token.colorWhite, 0.45)}`,
            backdropFilter: 'blur(20px)',
            boxShadow: `0 4px 24px ${alphaColor(token.colorText, 0.06)}`,
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'auto',
          }}
          styles={{
            body: {
              padding: isMobile ? 16 : 24,
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
            }
          }}
        >
          <Spin spinning={loading}>
            <Form form={form} layout="vertical" onFinish={handleSave}>
              {/* 装饰类型选择 */}
              <Form.Item
                name="decoration_type"
                label={<Text strong style={{ fontSize: 16 }}>装饰类型</Text>}
                rules={[{ required: true, message: '请选择装饰类型' }]}
              >
                <Select
                  size="large"
                  options={DECORATION_OPTIONS.map(opt => ({
                    value: opt.value,
                    label: (
                      <Space>
                        <span style={{ fontSize: 18 }}>{opt.icon}</span>
                        <span>{opt.label}</span>
                      </Space>
                    )
                  }))}
                  style={{ borderRadius: 12 }}
                />
              </Form.Item>

              <Divider style={{ margin: '24px 0', borderColor: alphaColor(token.colorText, 0.1) }} />

              {/* 强制启用开关 */}
              <Form.Item
                name="force_enabled"
                label={<Text strong style={{ fontSize: 16 }}>强制启用</Text>}
                valuePropName="checked"
                extra={
                  <Paragraph type="secondary" style={{ marginBottom: 0, marginTop: 8 }}>
                    <LockOutlined style={{ marginRight: 8 }} />
                    启用后，所有用户的装饰显示状态将被强制锁定，无法通过本地开关按钮关闭
                  </Paragraph>
                }
              >
                <Switch
                  checkedChildren="强制"
                  unCheckedChildren="可选"
                  style={{
                    flexShrink: 0,
                    height: isMobile ? 16 : 22,
                    minHeight: isMobile ? 16 : 22,
                    lineHeight: isMobile ? '16px' : '22px'
                  }}
                />
              </Form.Item>

              <Divider style={{ margin: '24px 0', borderColor: alphaColor(token.colorText, 0.1) }} />

              {/* 装饰说明 */}
              <Form.Item
                name="description"
                label={<Text strong style={{ fontSize: 16 }}>装饰说明</Text>}
                extra="可选的管理员备注，仅管理员可见"
              >
                <Input.TextArea
                  rows={4}
                  placeholder="例如：春节期间展示春节装饰"
                  style={{ borderRadius: 12 }}
                />
              </Form.Item>

              <Divider style={{ margin: '24px 0', borderColor: alphaColor(token.colorText, 0.1) }} />

              {/* 保存按钮 */}
              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={saving}
                  icon={<SaveOutlined />}
                  size="large"
                  style={{
                    borderRadius: 12,
                    minWidth: 120,
                    boxShadow: `0 4px 12px ${alphaColor(token.colorPrimary, 0.3)}`,
                  }}
                >
                  保存配置
                </Button>
              </Form.Item>
            </Form>

            {/* 配置生效说明卡片 */}
            <Card
              variant="borderless"
              style={{
                marginTop: 24,
                background: alphaColor(token.colorInfoBg, 0.5),
                borderRadius: 16,
                border: `1px solid ${alphaColor(token.colorInfoBorder, 0.3)}`,
              }}
              styles={{
                body: { padding: isMobile ? 12 : 16 }
              }}
            >
              <Title level={5} style={{ color: token.colorInfoText, marginBottom: 12 }}>
                <GlobalOutlined style={{ marginRight: 8 }} />
                配置生效说明
              </Title>
              <ul style={{ margin: 0, paddingLeft: 20, color: token.colorTextSecondary }}>
                <li style={{ marginBottom: 8 }}>配置保存后，所有用户在下次刷新页面时生效</li>
                <li style={{ marginBottom: 8 }}>"自动"模式下，系统根据日期自动切换季节装饰</li>
                <li style={{ marginBottom: 8 }}>"强制启用"模式下，用户无法关闭装饰显示</li>
                <li style={{ marginBottom: 8 }}>用户本地设置仅在不强制启用时生效</li>
                <li>选择未实现的季节（夏天/秋天/冬天）时，装饰和按钮都不会显示</li>
              </ul>
            </Card>
          </Spin>
        </Card>
      </div>
    </div>
  );
}