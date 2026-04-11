import { useState, useEffect, useCallback } from 'react';
import {
  Table, Button, Modal, Form, Input, Select, InputNumber, Space,
  Tag, Tabs, Card, Descriptions, Popconfirm,
  Tooltip, Typography, Spin, Alert, List, Pagination
} from 'antd';
import {
  PlusOutlined, HistoryOutlined, EyeOutlined, RobotOutlined, LoadingOutlined, SearchOutlined, ToolOutlined
} from '@ant-design/icons';
import { useStore } from '../store';
import { itemApi, chapterApi } from '../services/api';
import { getMessageInstance } from '../utils/antdStatic';
import type {
  Item, ItemCreate, ItemUpdate, ItemCategory, ItemRarity, ItemStatus, Chapter
} from '../types';

const { Text } = Typography;

// 状态显示配置
const STATUS_CONFIG: Record<ItemStatus, { text: string; color: string }> = {
  appeared: { text: '未归属', color: 'default' },
  owned: { text: '被持有', color: 'green' },
  equipped: { text: '已装备', color: 'blue' },
  consumed: { text: '已消耗', color: 'orange' },
  destroyed: { text: '已销毁', color: 'red' },
  lost: { text: '已丢失', color: 'default' },
  sealed: { text: '被封印', color: 'purple' },
};

// 稀有度显示配置
const RARITY_CONFIG: Record<ItemRarity, { text: string; color: string }> = {
  common: { text: '普通', color: 'default' },
  uncommon: { text: '优秀', color: 'green' },
  rare: { text: '稀有', color: 'blue' },
  epic: { text: '史诗', color: 'purple' },
  legendary: { text: '传说', color: 'gold' },
  artifact: { text: '神器', color: 'red' },
};

// 标签英文到中文映射
const TAG_DISPLAY_MAP: Record<string, string> = {
  weapon: '武器',
  armor: '防具',
  consumable: '消耗品',
  material: '材料',
  artifact: '法宝',
  treasure: '宝物',
  book: '典籍',
  currency: '货币',
  other: '其他',
  tool: '工具',
  accessory: '饰品',
  key: '关键物品',
};

// 流转类型中文映射
const TRANSFER_TYPE_MAP: Record<string, string> = {
  obtain: '获得',
  give: '赠送',
  trade: '交易',
  transfer: '转移',
  steal: '偷窃',
  loot: '掠夺',
  inherit: '继承',
  craft: '制作',
  find: '发现',
  buy: '购买',
  sell: '出售',
  lose: '丢失',
  equip: '装备',
  unequip: '卸下',
  seal: '封印',
  destroy: '销毁',
};

// 数量变更类型中文映射
const QUANTITY_CHANGE_TYPE_MAP: Record<string, string> = {
  obtain: '获得',
  consume: '消耗',
  use: '使用',
  sell: '出售',
  buy: '购买',
  craft: '制作',
  lose: '丢失',
  split: '分拆',
  merge: '合并',
};

// 格式化标签显示
const formatTag = (tag: string): string => {
  return TAG_DISPLAY_MAP[tag.toLowerCase()] || tag;
};

export default function Items() {
  const { currentProject } = useStore();

  // 状态
  const [items, setItems] = useState<Item[]>([]);
  const [categories, setCategories] = useState<ItemCategory[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<string>('all');
  const [stats, setStats] = useState<{ total: number; by_status: Record<string, number> }>({ total: 0, by_status: {} });
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<Item | null>(null);
  const [viewingItem, setViewingItem] = useState<Item | null>(null);
  const [historyData, setHistoryData] = useState<any>(null);
  const [form] = Form.useForm();

  // 分页状态
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 });

  // 搜索状态
  const [searchKeyword, setSearchKeyword] = useState<string>('');
  const [searchInput, setSearchInput] = useState<string>('');

  // AI分析相关状态
  const [isAnalyzeModalOpen, setIsAnalyzeModalOpen] = useState(false);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [chaptersLoading, setChaptersLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeResult, setAnalyzeResult] = useState<any>(null);
  const [analyzeForm] = Form.useForm();
  const [chapterSearchKeyword, setChapterSearchKeyword] = useState<string>('');

  // 修复不一致数据状态
  const [fixLoading, setFixLoading] = useState(false);

  // 获取物品列表
  const fetchItems = useCallback(async (page = 1, pageSize = 20, keyword = '') => {
    if (!currentProject?.id) return;
    setLoading(true);
    try {
      const response = await itemApi.getProjectItems(currentProject.id, {
        status: activeTab === 'all' ? undefined : activeTab,
        search: keyword || undefined,
        page,
        limit: pageSize,
      });
      console.log('📋 物品列表响应:', response);
      console.log('📋 物品列表:', response.items?.map((item: Item) => ({
        name: item.name,
        category_id: item.category_id,
        category_name: item.category_name,
        // 检查字段类型
        category_name_type: typeof item.category_name
      })));
      setItems(response.items || []);
      if (response.stats) {
        setStats(response.stats);
      }
      setPagination({
        current: page,
        pageSize: pageSize,
        total: response.total || 0
      });
    } catch (error) {
      console.error('获取物品列表失败:', error);
    } finally {
      setLoading(false);
    }
  }, [currentProject?.id, activeTab, searchKeyword]);

  // 获取分类树
  const fetchCategories = useCallback(async () => {
    if (!currentProject?.id) return;
    try {
      const response = await itemApi.getCategoryTree(currentProject.id);
      console.log('📦 分类数据:', response);
      // 打印每个分类的 id 和 name
      const printCategories = (cats: ItemCategory[], level = 0) => {
        cats.forEach(cat => {
          console.log(`${'  '.repeat(level)}📦 分类: id=${cat.id}, name=${cat.name}`);
          if (cat.children?.length) {
            printCategories(cat.children, level + 1);
          }
        });
      };
      printCategories(response || []);
      setCategories(response || []);
    } catch (error) {
      console.error('获取分类失败:', error);
    }
  }, [currentProject?.id]);

  // 初始化加载
  useEffect(() => {
    fetchItems(1, pagination.pageSize, searchKeyword);
    fetchCategories();
  }, [fetchItems, fetchCategories]);

  // Tab变化时重置分页和搜索
  useEffect(() => {
    setPagination(prev => ({ ...prev, current: 1 }));
  }, [activeTab]);

  // 搜索处理
  const handleSearch = () => {
    setSearchKeyword(searchInput);
    setPagination(prev => ({ ...prev, current: 1 }));
  };

  // 打开创建/编辑弹窗
  const handleOpenModal = (item?: Item) => {
    setEditingItem(item || null);
    if (item) {
      form.setFieldsValue({
        ...item,
        alias: item.alias?.join(', '),
        tags: item.tags || [],  // Select 组件使用数组
      });
    } else {
      form.resetFields();
      form.setFieldsValue({ unit: '个', quantity: 1, status: 'appeared' });
    }
    setIsModalOpen(true);
  };

  // 提交表单
  const handleSubmit = async (values: any) => {
    if (!currentProject?.id) return;

    console.log('📝 表单提交数据:', values);
    console.log('📝 category_id:', values.category_id);

    const data: ItemCreate | ItemUpdate = {
      ...values,
      alias: values.alias?.split(',').map((s: string) => s.trim()).filter(Boolean),
      tags: values.tags || [],  // Select 组件已经是数组
    };

    console.log('📤 发送数据:', data);

    try {
      if (editingItem) {
        await itemApi.updateItem(editingItem.id, data as ItemUpdate);
        getMessageInstance().success('更新成功');
      } else {
        await itemApi.createItem({ ...data, project_id: currentProject.id } as ItemCreate);
        getMessageInstance().success('创建成功');
      }
      setIsModalOpen(false);
      form.resetFields();
      fetchItems(pagination.current, pagination.pageSize, searchKeyword);
    } catch (error) {
      getMessageInstance().error('操作失败');
    }
  };

  // 删除物品
  const handleDelete = async (itemId: string) => {
    try {
      await itemApi.deleteItem(itemId);
      getMessageInstance().success('删除成功');
      fetchItems(pagination.current, pagination.pageSize, searchKeyword);
    } catch (error) {
      getMessageInstance().error('删除失败');
    }
  };

  // 查看详情
  const handleViewDetail = (item: Item) => {
    setViewingItem(item);
    setIsDetailOpen(true);
  };

  // 查看历史
  const handleViewHistory = async (item: Item) => {
    try {
      const history = await itemApi.getItemHistory(item.id);
      setHistoryData(history);
      setIsHistoryOpen(true);
    } catch (error) {
      getMessageInstance().error('获取历史失败');
    }
  };

  // 打开AI分析弹窗
  const handleOpenAnalyzeModal = async () => {
    setIsAnalyzeModalOpen(true);
    setAnalyzeResult(null);
    analyzeForm.resetFields();
    setChapterSearchKeyword(''); // 重置搜索关键词

    // 加载章节列表
    if (currentProject?.id) {
      setChaptersLoading(true);
      try {
        const chapterList = await chapterApi.getChapters(currentProject.id);
        // 只获取有内容的章节
        const chaptersWithContent = chapterList.filter(c => c.content && c.content.length > 100);
        // 按章节号降序排序（最新章节在前）
        chaptersWithContent.sort((a, b) => b.chapter_number - a.chapter_number);
        setChapters(chaptersWithContent);

        // 默认选择最近1章
        if (chaptersWithContent.length > 0) {
          analyzeForm.setFieldsValue({
            chapter_id: chaptersWithContent[0].id
          });
        }
      } catch (error) {
        getMessageInstance().error('获取章节列表失败');
      } finally {
        setChaptersLoading(false);
      }
    }
  };

  // 执行AI分析
  const handleAnalyze = async (values: any) => {
    if (!values.chapter_id) {
      getMessageInstance().error('请选择章节');
      return;
    }

    setAnalyzing(true);
    setAnalyzeResult(null);

    const hideLoading = getMessageInstance().loading('正在进行AI分析，这可能需要1-2分钟，请耐心等待...', 0);

    try {
      const result = await itemApi.analyzeChapterItems({
        chapter_id: values.chapter_id,
        analysis_requirements: values.analysis_requirements || undefined
      });

      setAnalyzeResult(result);
      getMessageInstance().success(`分析完成！识别到 ${result.analysis_result.items?.length || 0} 个物品事件`);

      // 刷新物品列表
      fetchItems(pagination.current, pagination.pageSize, searchKeyword);
    } catch (error: any) {
      const errorDetail = error?.response?.data?.detail || error?.message || '分析失败';
      console.error('物品分析失败:', error);
      getMessageInstance().error(`分析失败: ${errorDetail}`);
    } finally {
      hideLoading();
      setAnalyzing(false);
    }
  };

  // 修复不一致数据
  const handleFixInconsistent = async () => {
    setFixLoading(true);
    const hideLoading = getMessageInstance().loading('正在修复不一致数据...', 0);
    try {
      const result = await itemApi.fixInconsistentItems(currentProject?.id);
      hideLoading();
      if (result.success) {
        if (result.fixed_count > 0) {
          getMessageInstance().success(`修复完成！已修复 ${result.fixed_count} 个持有者不为空但状态为'未归属'的物品`);
          // 刷新物品列表
          fetchItems(pagination.current, pagination.pageSize, searchKeyword);
        } else {
          getMessageInstance().info('数据一致性良好，无需修复');
        }
      } else {
        getMessageInstance().warning(result.message);
      }
    } catch (error: any) {
      hideLoading();
      const errorDetail = error?.response?.data?.detail || error?.message || '修复失败';
      getMessageInstance().error(`修复失败: ${errorDetail}`);
    } finally {
      setFixLoading(false);
    }
  };

  // 表格列定义
  const columns = [
    {
      title: '物品名称',
      dataIndex: 'name',
      key: 'name',
      width: 180,
      fixed: 'left' as const,
      render: (name: string, record: Item) => (
        <Space>
          <Text strong>{name}</Text>
          {record.is_plot_critical && <Tag color="red">关键</Tag>}
        </Space>
      ),
    },
    {
      title: '分类',
      dataIndex: 'category_name',
      key: 'category_name',
      width: 100,
      render: (name: string) => <Tag color={name ? "blue" : "default"}>{name || '其他'}</Tag>,
    },
    {
      title: '描述/功能',
      key: 'description',
      width: 280,
      ellipsis: true,
      render: (_: any, record: Item) => {
        const desc = record.description || record.special_effects;
        if (!desc) return <Text type="secondary">暂无描述</Text>;
        return (
          <Tooltip title={desc} placement="topLeft">
            <Text type="secondary" style={{ fontSize: 13 }}>{desc}</Text>
          </Tooltip>
        );
      },
    },
    {
      title: '稀有度',
      dataIndex: 'rarity',
      key: 'rarity',
      width: 90,
      align: 'center' as const,
      render: (rarity: ItemRarity) =>
        rarity ? <Tag color={RARITY_CONFIG[rarity]?.color}>{RARITY_CONFIG[rarity]?.text || rarity}</Tag> : '-',
    },
    {
      title: '数量',
      dataIndex: 'quantity',
      key: 'quantity',
      width: 80,
      align: 'center' as const,
      render: (qty: number, record: Item) => `${qty} ${record.unit}`,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      align: 'center' as const,
      render: (status: ItemStatus) => (
        <Tag color={STATUS_CONFIG[status]?.color}>{STATUS_CONFIG[status]?.text || status}</Tag>
      ),
    },
    {
      title: '持有者',
      dataIndex: 'owner_character_name',
      key: 'owner_character_name',
      width: 100,
      render: (name: string) => name || '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      fixed: 'right' as const,
      render: (_: any, record: Item) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => handleViewDetail(record)}>
            详情
          </Button>
          <Button type="link" size="small" icon={<HistoryOutlined />} onClick={() => handleViewHistory(record)}>
            历史
          </Button>
          <Button type="link" size="small" onClick={() => handleOpenModal(record)}>
            编辑
          </Button>
          <Popconfirm
            title="确定删除此物品？"
            onConfirm={() => handleDelete(record.id)}
          >
            <Button type="link" size="small" danger>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // Tab 配置（显示数量）
  const getStatusCount = (status: string): number => {
    if (status === 'all') return stats.total;
    return stats.by_status[status] || 0;
  };

  const tabItems = [
    { key: 'all', label: `全部 (${getStatusCount('all')})` },
    { key: 'owned', label: `被持有 (${getStatusCount('owned')})` },
    { key: 'appeared', label: `未归属 (${getStatusCount('appeared')})` },
    { key: 'equipped', label: `已装备 (${getStatusCount('equipped')})` },
    { key: 'consumed', label: `已消耗 (${getStatusCount('consumed')})` },
    { key: 'destroyed', label: `已销毁 (${getStatusCount('destroyed')})` },
    { key: 'lost', label: `已丢失 (${getStatusCount('lost')})` },
    { key: 'sealed', label: `被封印 (${getStatusCount('sealed')})` },
  ];

  // 扁平化分类列表
  const flattenCategories = (cats: ItemCategory[], level = 0): { value: string; label: string }[] => {
    return cats.flatMap(cat => [
      { value: cat.id, label: `${'　'.repeat(level)}${cat.name}` },
      ...flattenCategories(cat.children || [], level + 1),
    ]);
  };

  return (
    <div style={{
      padding: 24,
      height: 'calc(100vh - 64px)',  // 减去顶部导航栏高度
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden'
    }}>
      {/* 页面头部 */}
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
        <h2 style={{ margin: 0 }}>物品管理</h2>
        <Space>
          {/* 搜索框 */}
          <Input.Search
            placeholder="搜索物品名称、描述..."
            allowClear
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onSearch={handleSearch}
            onPressEnter={handleSearch}
            style={{ width: 280 }}
            enterButton={<SearchOutlined />}
          />
          <Button icon={<RobotOutlined />} onClick={handleOpenAnalyzeModal}>
            AI分析
          </Button>
          <Button icon={<ToolOutlined />} onClick={handleFixInconsistent} loading={fixLoading}>
            修复数据
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => handleOpenModal()}>
            创建物品
          </Button>
        </Space>
      </div>

      {/* 状态筛选 Tab */}
      <div style={{ flexShrink: 0 }}>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems.map(item => ({ key: item.key, label: item.label }))}
        />
      </div>

      {/* 物品表格 - 自适应高度 */}
      <div style={{ flex: 1, overflow: 'auto', minHeight: 0 }}>
        <Table
          columns={columns}
          dataSource={items}
          rowKey="id"
          loading={loading}
          size="small"
          scroll={{ x: 1100 }}
          sticky={{ offsetHeader: 0 }}
          pagination={false}
        />
      </div>

      {/* 分页 - 固定在底部 */}
      <div style={{ flexShrink: 0, paddingTop: 16 }}>
        <Pagination
          current={pagination.current}
          pageSize={pagination.pageSize}
          total={pagination.total}
          showSizeChanger
          showQuickJumper
          showTotal={(total) => `共 ${total} 件物品`}
          pageSizeOptions={['10', '20', '50', '100']}
          onChange={(page, pageSize) => {
            fetchItems(page, pageSize, searchKeyword);
          }}
        />
      </div>

      {/* 创建/编辑弹窗 */}
      <Modal
        title={editingItem ? '编辑物品' : '创建物品'}
        open={isModalOpen}
        onCancel={() => setIsModalOpen(false)}
        footer={null}
        width={700}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item label="物品名称" name="name" rules={[{ required: true }]}>
            <Input placeholder="请输入物品名称" />
          </Form.Item>

          <Form.Item label="别名" name="alias" extra="多个别名用英文逗号分隔">
            <Input placeholder="如：玄铁重剑, 那把剑" />
          </Form.Item>

          <Form.Item label="分类" name="category_id">
            <Select placeholder="选择分类" allowClear>
              {flattenCategories(categories).map(cat => (
                <Select.Option key={cat.value} value={cat.value}>{cat.label}</Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Space size="large">
            <Form.Item label="单位" name="unit">
              <Input style={{ width: 80 }} placeholder="个" />
            </Form.Item>
            <Form.Item label="数量" name="quantity">
              <InputNumber min={0} style={{ width: 100 }} />
            </Form.Item>
            <Form.Item label="稀有度" name="rarity">
              <Select style={{ width: 120 }} allowClear>
                {Object.entries(RARITY_CONFIG).map(([key, val]) => (
                  <Select.Option key={key} value={key}>
                    <Tag color={val.color}>{val.text}</Tag>
                  </Select.Option>
                ))}
              </Select>
            </Form.Item>
            <Form.Item label="品质" name="quality">
              <Input style={{ width: 100 }} placeholder="如：上品" />
            </Form.Item>
          </Space>

          <Form.Item label="物品描述" name="description">
            <Input.TextArea rows={3} placeholder="物品的外观、功能、用途等详细描述" />
          </Form.Item>

          <Form.Item label="特殊效果" name="special_effects">
            <Input.TextArea rows={2} placeholder="物品的特殊能力或效果（如：附带冰属性伤害、增加防御力等）" />
          </Form.Item>

          <Form.Item label="背景故事" name="lore">
            <Input.TextArea rows={2} placeholder="物品的来历、传说、历史背景等" />
          </Form.Item>

          <Space size="large">
            <Form.Item label="价值" name="value">
              <InputNumber min={0} style={{ width: 120 }} placeholder="金币" />
            </Form.Item>
            <Form.Item label="首次出现章节" name="source_chapter_number">
              <InputNumber min={1} style={{ width: 100 }} placeholder="章节号" />
            </Form.Item>
          </Space>

          <Form.Item label="持有者" name="owner_character_name">
            <Input placeholder="当前持有者名称" />
          </Form.Item>

          <Form.Item label="状态" name="status">
            <Select style={{ width: 150 }}>
              {Object.entries(STATUS_CONFIG).map(([key, val]) => (
                <Select.Option key={key} value={key}>
                  <Tag color={val.color}>{val.text}</Tag>
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item label="标签" name="tags" extra="选择或输入物品标签">
            <Select
              mode="tags"
              placeholder="选择或输入标签"
              allowClear
              tokenSeparators={[',']}
              options={Object.entries(TAG_DISPLAY_MAP).map(([value, label]) => ({
                value,
                label
              }))}
              tagRender={(props) => {
                const { value, closable, onClose } = props;
                const displayText = TAG_DISPLAY_MAP[value as string] || value;
                return (
                  <Tag closable={closable} onClose={onClose} style={{ marginRight: 3 }}>
                    {displayText}
                  </Tag>
                );
              }}
            />
          </Form.Item>

          <Form.Item label="备注" name="notes">
            <Input.TextArea rows={2} placeholder="创作备注" />
          </Form.Item>

          <Form.Item label="物品重要性" name="is_plot_critical">
            <Select style={{ width: 150 }}>
              <Select.Option value={false}>普通物品</Select.Option>
              <Select.Option value={true}>剧情关键物品</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button onClick={() => setIsModalOpen(false)}>取消</Button>
              <Button type="primary" htmlType="submit">
                {editingItem ? '更新' : '创建'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 物品详情弹窗 */}
      <Modal
        title={
          <Space>
            <span>{viewingItem?.name}</span>
            {viewingItem?.is_plot_critical && <Tag color="red">剧情关键</Tag>}
          </Space>
        }
        open={isDetailOpen}
        onCancel={() => setIsDetailOpen(false)}
        footer={
          <Space>
            <Button onClick={() => setIsDetailOpen(false)}>关闭</Button>
            <Button onClick={() => {
              setIsDetailOpen(false);
              if (viewingItem) handleViewHistory(viewingItem);
            }}>
              查看历史
            </Button>
            <Button type="primary" onClick={() => {
              setIsDetailOpen(false);
              if (viewingItem) handleOpenModal(viewingItem);
            }}>
              编辑
            </Button>
          </Space>
        }
        width={800}
      >
        {viewingItem && (
          <div>
            {/* 基本信息 */}
            <Card title="基本信息" size="small" style={{ marginBottom: 16 }}>
              <Descriptions column={2} size="small">
                <Descriptions.Item label="名称">{viewingItem.name}</Descriptions.Item>
                <Descriptions.Item label="别名">
                  {viewingItem.alias?.length ? viewingItem.alias.join('、') : '-'}
                </Descriptions.Item>
                <Descriptions.Item label="分类">
                  {viewingItem.category_name ? (
                    <Tag color="blue">{viewingItem.category_name}</Tag>
                  ) : <Text type="secondary">其他</Text>}
                </Descriptions.Item>
                <Descriptions.Item label="稀有度">
                  {viewingItem.rarity ? (
                    <Tag color={RARITY_CONFIG[viewingItem.rarity]?.color}>
                      {RARITY_CONFIG[viewingItem.rarity]?.text}
                    </Tag>
                  ) : '-'}
                </Descriptions.Item>
                <Descriptions.Item label="品质">{viewingItem.quality || '-'}</Descriptions.Item>
                <Descriptions.Item label="数量">
                  {viewingItem.quantity} {viewingItem.unit}
                </Descriptions.Item>
                <Descriptions.Item label="状态">
                  <Tag color={STATUS_CONFIG[viewingItem.status]?.color}>
                    {STATUS_CONFIG[viewingItem.status]?.text}
                  </Tag>
                </Descriptions.Item>
              </Descriptions>
            </Card>

            {/* 描述与功能 */}
            <Card title="描述与功能" size="small" style={{ marginBottom: 16 }}>
              <Descriptions column={1} size="small">
                <Descriptions.Item label="物品描述">
                  {viewingItem.description || <Text type="secondary">暂无描述</Text>}
                </Descriptions.Item>
                <Descriptions.Item label="特殊效果">
                  {viewingItem.special_effects || <Text type="secondary">无</Text>}
                </Descriptions.Item>
                <Descriptions.Item label="背景故事">
                  {viewingItem.lore || <Text type="secondary">无</Text>}
                </Descriptions.Item>
              </Descriptions>
            </Card>

            {/* 属性信息 */}
            {viewingItem.attributes && Object.keys(viewingItem.attributes).length > 0 && (
              <Card title="物品属性" size="small" style={{ marginBottom: 16 }}>
                <Space wrap>
                  {Object.entries(viewingItem.attributes).map(([key, value]) => (
                    <Tag key={key} color="blue">{key}: {value as number}</Tag>
                  ))}
                </Space>
              </Card>
            )}

            {/* 关联信息 */}
            <Card title="关联信息" size="small" style={{ marginBottom: 16 }}>
              <Descriptions column={2} size="small">
                <Descriptions.Item label="持有者">
                  {viewingItem.owner_character_name || <Text type="secondary">无</Text>}
                </Descriptions.Item>
                <Descriptions.Item label="价值">
                  {viewingItem.value ? `${viewingItem.value} 金币` : '-'}
                </Descriptions.Item>
                <Descriptions.Item label="首次出现">
                  {viewingItem.source_chapter_number ? `第${viewingItem.source_chapter_number}章` : '-'}
                </Descriptions.Item>
                <Descriptions.Item label="来源类型">
                  {viewingItem.source_type || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="关联角色" span={2}>
                  {viewingItem.related_characters?.length
                    ? viewingItem.related_characters.join('、')
                    : <Text type="secondary">无</Text>}
                </Descriptions.Item>
                <Descriptions.Item label="关联章节" span={2}>
                  {viewingItem.related_chapters?.length
                    ? viewingItem.related_chapters.map(c => `第${c}章`).join('、')
                    : <Text type="secondary">无</Text>}
                </Descriptions.Item>
              </Descriptions>
            </Card>

            {/* 标签与备注 */}
            <Card title="标签与备注" size="small">
              <Descriptions column={1} size="small">
                <Descriptions.Item label="标签">
                  {viewingItem.tags?.length
                    ? viewingItem.tags.map(tag => <Tag key={tag}>{formatTag(tag)}</Tag>)
                    : <Text type="secondary">无</Text>}
                </Descriptions.Item>
                <Descriptions.Item label="创作备注">
                  {viewingItem.notes || <Text type="secondary">无</Text>}
                </Descriptions.Item>
              </Descriptions>
            </Card>
          </div>
        )}
      </Modal>

      {/* 历史记录弹窗 */}
      <Modal
        title={`物品历史 - ${historyData?.item?.name || ''}`}
        open={isHistoryOpen}
        onCancel={() => setIsHistoryOpen(false)}
        footer={null}
        width={900}
      >
        {historyData && (
          <div>
            <Descriptions bordered column={2} size="small" style={{ marginBottom: 16 }}>
              <Descriptions.Item label="名称">{historyData.item?.name}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={STATUS_CONFIG[historyData.item?.status as ItemStatus]?.color || 'default'}>
                  {STATUS_CONFIG[historyData.item?.status as ItemStatus]?.text || historyData.item?.status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="数量">{historyData.item?.quantity} {historyData.item?.unit}</Descriptions.Item>
              <Descriptions.Item label="持有者">{historyData.item?.owner_character_name || '-'}</Descriptions.Item>
            </Descriptions>

            <h4>流转记录 {historyData.transfers?.length ? `(${historyData.transfers.length}条)` : ''}</h4>
            <Table
              size="small"
              dataSource={historyData.transfers || []}
              rowKey="id"
              pagination={
                (historyData.transfers?.length || 0) > 5
                  ? { pageSize: 5, showSizeChanger: false, showTotal: (total) => `共 ${total} 条` }
                  : false
              }
              columns={[
                { title: '类型', dataIndex: 'transfer_type', width: 80, render: (v) => TRANSFER_TYPE_MAP[v] || v || '-' },
                { title: '从', dataIndex: 'from_character_name', render: (v) => v || '-' },
                { title: '到', dataIndex: 'to_character_name', render: (v) => v || '-' },
                { title: '章节', dataIndex: 'chapter_number', width: 90, render: (v) => v ? `第${v}章` : '-' },
                { title: '描述', dataIndex: 'description', ellipsis: true },
              ]}
            />

            <h4 style={{ marginTop: 16 }}>数量变更 {historyData.quantity_changes?.length ? `(${historyData.quantity_changes.length}条)` : ''}</h4>
            <Table
              size="small"
              dataSource={historyData.quantity_changes || []}
              rowKey="id"
              pagination={
                (historyData.quantity_changes?.length || 0) > 5
                  ? { pageSize: 5, showSizeChanger: false, showTotal: (total) => `共 ${total} 条` }
                  : false
              }
              columns={[
                { title: '类型', dataIndex: 'change_type', width: 80, render: (v) => QUANTITY_CHANGE_TYPE_MAP[v] || v || '-' },
                { title: '变化', dataIndex: 'quantity_change', width: 80, render: (v) => (v > 0 ? `+${v}` : v) },
                { title: '剩余', dataIndex: 'quantity_after', width: 80 },
                { title: '章节', dataIndex: 'chapter_number', width: 90, render: (v) => v ? `第${v}章` : '-' },
                { title: '原因', dataIndex: 'reason', ellipsis: true },
              ]}
            />
          </div>
        )}
      </Modal>

      {/* AI分析弹窗 */}
      <Modal
        title={
          <Space>
            <RobotOutlined />
            <span>AI物品分析</span>
          </Space>
        }
        open={isAnalyzeModalOpen}
        onCancel={() => setIsAnalyzeModalOpen(false)}
        footer={null}
        width={700}
      >
        <Spin spinning={chaptersLoading} indicator={<LoadingOutlined spin />} tip="加载章节列表...">
          {!analyzeResult ? (
            <Form form={analyzeForm} layout="vertical" onFinish={handleAnalyze}>
              <Alert
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
                message="选择章节后，AI将自动分析其中的物品信息，包括物品出现、流转、状态变化等"
              />

              <Form.Item label="选择章节" name="chapter_id" rules={[{ required: true, message: '请选择章节' }]}>
                <Select
                  placeholder="选择要分析的章节"
                  showSearch
                  loading={chaptersLoading}
                  disabled={analyzing}
                  onSearch={(value) => setChapterSearchKeyword(value)}
                  onSelect={() => setChapterSearchKeyword('')}
                  filterOption={(input, option) => {
                    const searchText = `${option?.data?.chapter_number || ''} ${option?.data?.title || ''}`;
                    return searchText.toLowerCase().includes(input.toLowerCase());
                  }}
                >
                  {(chapterSearchKeyword ? chapters : chapters.slice(0, 5)).map(chapter => (
                    <Select.Option
                      key={chapter.id}
                      value={chapter.id}
                      data={chapter}
                    >
                      第{chapter.chapter_number}章: {chapter.title || '未命名'}
                      {chapter.word_count && ` (${chapter.word_count}字)`}
                    </Select.Option>
                  ))}
                  {!chapterSearchKeyword && chapters.length > 5 && (
                    <Select.Option disabled key="more-hint" value="__hint__">
                      <Text type="secondary">共 {chapters.length} 章，输入关键词搜索更多...</Text>
                    </Select.Option>
                  )}
                </Select>
              </Form.Item>

              <Form.Item
                label="分析要求"
                name="analysis_requirements"
                extra="可选，指定分析重点（如：只关注法宝、只分析主角的物品等）"
              >
                <Input.TextArea
                  rows={3}
                  placeholder="如：重点分析本章节中新出现的法宝类物品及其流转..."
                  disabled={analyzing}
                />
              </Form.Item>

              <Form.Item>
                <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                  <Button onClick={() => setIsAnalyzeModalOpen(false)} disabled={analyzing}>
                    取消
                  </Button>
                  <Button type="primary" htmlType="submit" loading={analyzing} icon={<RobotOutlined />}>
                    {analyzing ? '正在分析...' : '开始分析'}
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          ) : (
            <div>
              {/* 分析结果 */}
              <Alert
                type="success"
                showIcon
                style={{ marginBottom: 16 }}
                message={`第${analyzeResult.chapter_number}章「${analyzeResult.chapter_title}」分析完成`}
                description={analyzeResult.analysis_result?.summary || '无概述'}
              />

              {/* 同步统计 */}
              {analyzeResult.sync_result && (
                <Card size="small" style={{ marginBottom: 16 }}>
                  <Descriptions column={4} size="small">
                    <Descriptions.Item label="新建物品">
                      <Tag color="green">{analyzeResult.sync_result.created_count}</Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label="更新物品">
                      <Tag color="blue">{analyzeResult.sync_result.updated_count}</Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label="匹配已有">
                      <Tag color="orange">{analyzeResult.sync_result.matched_count}</Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label="跳过">
                      <Tag color="default">{analyzeResult.sync_result.skipped_count}</Tag>
                    </Descriptions.Item>
                  </Descriptions>
                </Card>
              )}

              {/* 识别的物品列表 */}
              {analyzeResult.analysis_result?.items?.length > 0 && (
                <Card title="识别的物品事件" size="small">
                  <List
                    size="small"
                    dataSource={analyzeResult.analysis_result.items}
                    renderItem={(item: any) => (
                      <List.Item>
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <Space>
                            <Text strong>{item.item_name}</Text>
                            <Tag color="blue">{item.event_type}</Tag>
                            {item.item_type && <Tag>{item.item_type}</Tag>}
                            {item.rarity && <Tag color={RARITY_CONFIG[item.rarity as ItemRarity]?.color}>
                              {RARITY_CONFIG[item.rarity as ItemRarity]?.text}
                            </Tag>}
                          </Space>
                          <Text type="secondary">
                            {item.from_character && `从 ${item.from_character}`}
                            {item.to_character && ` → ${item.to_character}`}
                            {item.quantity_change && ` (${item.quantity_change > 0 ? '+' : ''}${item.quantity_change})`}
                          </Text>
                          {item.description && (
                            <Text type="secondary" style={{ fontSize: 12 }}>{item.description}</Text>
                          )}
                        </Space>
                      </List.Item>
                    )}
                  />
                </Card>
              )}

              {/* 操作按钮 */}
              <div style={{ marginTop: 16, textAlign: 'right' }}>
                <Space>
                  <Button onClick={() => {
                    setAnalyzeResult(null);
                    analyzeForm.resetFields();
                  }}>
                    重新分析
                  </Button>
                  <Button type="primary" onClick={() => setIsAnalyzeModalOpen(false)}>
                    完成
                  </Button>
                </Space>
              </div>
            </div>
          )}
        </Spin>
      </Modal>
    </div>
  );
}