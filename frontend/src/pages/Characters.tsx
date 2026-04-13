import { useState, useEffect, useRef } from 'react';
import { Button, Modal, Form, Input, Select, Row, Col, Empty, Tabs, Divider, Typography, Space, InputNumber, Checkbox, theme, App, Tag, Segmented, Pagination, List, Popconfirm } from 'antd';
import { ThunderboltOutlined, UserOutlined, TeamOutlined, PlusOutlined, ExportOutlined, ImportOutlined, DownloadOutlined, ReloadOutlined, DeleteOutlined, AppstoreOutlined, UnorderedListOutlined, EditOutlined, BankOutlined } from '@ant-design/icons';
import { useStore } from '../store';
import { useCharacterSync } from '../store/hooks';
import { charactersPageGridConfig } from '../components/CardStyles';
import { CharacterCard } from '../components/CharacterCard';
import { SSELoadingOverlay } from '../components/SSELoadingOverlay';
import DynamicAttributesEditor from '../components/DynamicAttributesEditor';
import type { Character, ApiError, AttributeValue, AttributeSchema } from '../types';
import { characterApi } from '../services/api';
import { SSEPostClient } from '../utils/sseClient';
import api from '../services/api';

const { Title, Text } = Typography;
const { TextArea } = Input;

interface Career {
  id: string;
  name: string;
  type: 'main' | 'sub';
  max_stage: number;
}

// 副职业数据类型
interface SubCareerData {
  career_id: string;
  stage: number;
}

// 角色创建表单值类型
interface CharacterFormValues {
  name: string;
  age?: string;
  gender?: string;
  role_type?: string;
  personality?: string;
  appearance?: string;
  background?: string;
  main_career_id?: string;
  main_career_stage?: number;
  sub_career_data?: SubCareerData[];
  // 组织字段
  organization_type?: string;
  organization_purpose?: string;
  organization_members?: string;
  power_level?: number;
  location?: string;
  motto?: string;
  color?: string;
}

// 角色创建数据类型
interface CharacterCreateData {
  project_id: string;
  name: string;
  is_organization: boolean;
  age?: string;
  gender?: string;
  role_type?: string;
  personality?: string;
  appearance?: string;
  background?: string;
  main_career_id?: string;
  main_career_stage?: number;
  sub_careers?: string;
  organization_type?: string;
  organization_purpose?: string;
  organization_members?: string;
  power_level?: number;
  location?: string;
  motto?: string;
  color?: string;
}

// 角色更新数据类型
interface CharacterUpdateData {
  name?: string;
  age?: string;
  gender?: string;
  role_type?: string;
  personality?: string;
  appearance?: string;
  background?: string;
  main_career_id?: string;
  main_career_stage?: number;
  sub_careers?: string;
  organization_type?: string;
  organization_purpose?: string;
  organization_members?: string;
  power_level?: number;
  location?: string;
  motto?: string;
  color?: string;
  attributes?: string; // 能力值 JSON
}

export default function Characters() {
  const { message } = App.useApp();
  const { token } = theme.useToken();
  const { currentProject, characters } = useStore();
  const [isGenerating, setIsGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState('');
  const [activeTab, setActiveTab] = useState<'all' | 'character' | 'organization'>('all');
  const [generateForm] = Form.useForm();
  const [generateOrgForm] = Form.useForm();
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  // 使用 useWatch 监听主职业ID，避免在 Form 未连接时调用 getFieldValue
  const watchedEditMainCareerId = Form.useWatch('main_career_id', editForm);
  // 监听副职业数据数组
  const watchedEditSubCareerData = Form.useWatch('sub_career_data', editForm);
  // 监听 createForm 的字段
  const watchedCreateMainCareerId = Form.useWatch('main_career_id', createForm);
  const watchedCreateSubCareerData = Form.useWatch('sub_career_data', createForm);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [createType, setCreateType] = useState<'character' | 'organization'>('character');
  const [editingCharacter, setEditingCharacter] = useState<Character | null>(null);
  const [mainCareers, setMainCareers] = useState<Career[]>([]);
  const [subCareers, setSubCareers] = useState<Career[]>([]);
  const [selectedCharacters, setSelectedCharacters] = useState<string[]>([]);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  // 能力属性 Schema 状态
  const [attributeSchema, setAttributeSchema] = useState<AttributeSchema | null>(null);
  // 当前编辑的能力值
  const [editingAttributes, setEditingAttributes] = useState<Record<string, AttributeValue> | null>(null);
  // 详情弹窗状态
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [detailCharacter, setDetailCharacter] = useState<Character | null>(null);
  // 视图切换状态
  const [viewMode, setViewMode] = useState<'card' | 'list'>('card');
  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const {
    refreshCharacters,
    deleteCharacter
  } = useCharacterSync();

  useEffect(() => {
    if (currentProject?.id) {
      refreshCharacters();
      fetchCareers();
      fetchAttributeSchema();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentProject?.id]);
  const [modal, contextHolder] = Modal.useModal();

  const fetchCareers = async () => {
    if (!currentProject?.id) return;
    try {
      const response = await api.get<unknown, { main_careers: Career[]; sub_careers: Career[] }>('/careers', {
        params: { project_id: currentProject.id }
      });
      setMainCareers(response.main_careers || []);
      setSubCareers(response.sub_careers || []);
    } catch (error) {
      console.error('获取职业列表失败:', error);
    }
  };

  // 获取项目的能力属性配置
  const fetchAttributeSchema = async () => {
    if (!currentProject?.id) return;
    try {
      const response = await api.get<unknown, { attribute_schema: string | null }>(`/projects/${currentProject.id}`);
      if (response.attribute_schema) {
        const schema = JSON.parse(response.attribute_schema) as AttributeSchema;
        setAttributeSchema(schema);
      } else {
        setAttributeSchema(null);
      }
    } catch (error) {
      console.error('获取能力属性配置失败:', error);
      setAttributeSchema(null);
    }
  };

  // 刷新项目的能力属性配置（使用最新默认配置）
  const refreshAttributeSchema = async () => {
    if (!currentProject?.id) return;
    try {
      const response = await api.post<unknown, { success: boolean; attribute_schema: AttributeSchema }>(
        `/projects/${currentProject.id}/refresh-attribute-schema`
      );
      if (response.success && response.attribute_schema) {
        setAttributeSchema(response.attribute_schema);
        message.success('能力属性配置已更新');
      }
    } catch (error) {
      console.error('刷新能力属性配置失败:', error);
      message.error('刷新能力属性配置失败');
    }
  };

  if (!currentProject) return null;

  const handleDeleteCharacter = async (id: string) => {
    try {
      await deleteCharacter(id);
      message.success('删除成功');
    } catch {
      message.error('删除失败');
    }
  };

  const handleGenerate = async (values: { name?: string; role_type: string; background?: string }) => {
    try {
      setIsGenerating(true);
      setProgress(0);
      setProgressMessage('准备生成角色...');

      const client = new SSEPostClient(
        '/api/characters/generate-stream',
        {
          project_id: currentProject.id,
          name: values.name,
          role_type: values.role_type,
          background: values.background,
        },
        {
          onProgress: (msg, prog) => {
            setProgress(prog);
            setProgressMessage(msg);
          },
          onResult: (data) => {
            console.log('角色生成完成:', data);
          },
          onError: (error) => {
            message.error(`生成失败: ${error}`);
          },
          onComplete: () => {
            setProgress(100);
            setProgressMessage('生成完成！');
          }
        }
      );

      await client.connect();
      message.success('AI生成角色成功');
      Modal.destroyAll();
      await refreshCharacters();
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'AI生成失败';
      message.error(errorMessage);
    } finally {
      setTimeout(() => {
        setIsGenerating(false);
        setProgress(0);
        setProgressMessage('');
      }, 500);
    }
  };

  const handleGenerateOrganization = async (values: {
    name?: string;
    organization_type?: string;
    background?: string;
    requirements?: string;
  }) => {
    try {
      setIsGenerating(true);
      setProgress(0);
      setProgressMessage('准备生成组织...');

      const client = new SSEPostClient(
        '/api/organizations/generate-stream',
        {
          project_id: currentProject.id,
          name: values.name,
          organization_type: values.organization_type,
          background: values.background,
          requirements: values.requirements,
        },
        {
          onProgress: (msg, prog) => {
            setProgress(prog);
            setProgressMessage(msg);
          },
          onResult: (data) => {
            console.log('组织生成完成:', data);
          },
          onError: (error) => {
            message.error(`生成失败: ${error}`);
          },
          onComplete: () => {
            setProgress(100);
            setProgressMessage('生成完成！');
          }
        }
      );

      await client.connect();
      message.success('AI生成组织成功');
      Modal.destroyAll();
      await refreshCharacters();
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'AI生成失败';
      message.error(errorMessage);
    } finally {
      setTimeout(() => {
        setIsGenerating(false);
        setProgress(0);
        setProgressMessage('');
      }, 500);
    }
  };

  const handleCreateCharacter = async (values: CharacterFormValues) => {
    try {
      const createData: CharacterCreateData = {
        project_id: currentProject.id,
        name: values.name,
        is_organization: createType === 'organization',
      };

      if (createType === 'character') {
        // 角色字段
        createData.age = values.age;
        createData.gender = values.gender;
        createData.role_type = values.role_type || 'supporting';
        createData.personality = values.personality;
        createData.appearance = values.appearance;
        createData.background = values.background;
        
        // 职业字段
        if (values.main_career_id) {
          createData.main_career_id = values.main_career_id;
          createData.main_career_stage = values.main_career_stage || 1;
        }
        
        // 处理副职业数据
        if (values.sub_career_data && Array.isArray(values.sub_career_data) && values.sub_career_data.length > 0) {
          createData.sub_careers = JSON.stringify(values.sub_career_data);
        }
      } else {
        // 组织字段
        createData.organization_type = values.organization_type;
        createData.organization_purpose = values.organization_purpose;
        createData.background = values.background;
        createData.power_level = values.power_level;
        createData.location = values.location;
        createData.motto = values.motto;
        createData.color = values.color;
        createData.role_type = 'supporting'; // 组织默认为配角
      }

      await characterApi.createCharacter(createData);
      message.success(`${createType === 'character' ? '角色' : '组织'}创建成功`);
      setIsCreateModalOpen(false);
      createForm.resetFields();
      await refreshCharacters();
    } catch {
      message.error('创建失败');
    }
  };

  // 查看角色/组织详情
  const handleViewDetail = (character: Character) => {
    setDetailCharacter(character);
    setDetailModalOpen(true);
  };

  const handleEditCharacter = (character: Character) => {
    setEditingCharacter(character);

    // 提取副职业数据（包含职业ID和阶段）
    const subCareerData: SubCareerData[] = character.sub_careers?.map((sc) => ({
      career_id: sc.career_id,
      stage: sc.stage || 1
    })) || [];

    // 设置能力值
    if (character.attributes) {
      setEditingAttributes(character.attributes);
    } else {
      setEditingAttributes(null);
    }

    editForm.setFieldsValue({
      ...character,
      sub_career_data: subCareerData
    });
    setIsEditModalOpen(true);
  };

  const handleUpdateCharacter = async (values: CharacterFormValues) => {
    if (!editingCharacter) return;

    try {
      // 提取副职业数据，剩余的作为更新数据
      const { sub_career_data: subCareerData, ...restValues } = values;
      const updateData: CharacterUpdateData = { ...restValues };

      // 转换为sub_careers格式
      if (subCareerData && Array.isArray(subCareerData) && subCareerData.length > 0) {
        updateData.sub_careers = JSON.stringify(subCareerData);
      } else {
        updateData.sub_careers = JSON.stringify([]);
      }

      // 处理能力值字段
      if (editingAttributes && !editingCharacter.is_organization) {
        updateData.attributes = JSON.stringify(editingAttributes);
      }

      await characterApi.updateCharacter(editingCharacter.id, updateData);
      message.success('更新成功');
      setIsEditModalOpen(false);
      editForm.resetFields();
      setEditingCharacter(null);
      setEditingAttributes(null);
      await refreshCharacters();
    } catch (error) {
      console.error('更新失败:', error);
      message.error('更新失败');
    }
  };

  const handleDeleteCharacterWrapper = (id: string) => {
    handleDeleteCharacter(id);
  };

  // 导出选中的角色/组织
  const handleExportSelected = async () => {
    if (selectedCharacters.length === 0) {
      message.warning('请至少选择一个角色或组织');
      return;
    }

    try {
      await characterApi.exportCharacters(selectedCharacters);
      message.success(`成功导出 ${selectedCharacters.length} 个角色/组织`);
      setSelectedCharacters([]);
    } catch (error) {
      message.error('导出失败');
      console.error('导出错误:', error);
    }
  };

  // 导出单个角色/组织
  const handleExportSingle = async (characterId: string) => {
    try {
      await characterApi.exportCharacters([characterId]);
      message.success('导出成功');
    } catch (error) {
      message.error('导出失败');
      console.error('导出错误:', error);
    }
  };

  // 处理文件选择
  const handleFileSelect = async (file: File) => {
    try {
      // 验证文件
      const validation = await characterApi.validateImportCharacters(file);
      
      if (!validation.valid) {
        modal.error({
          title: '文件验证失败',
          centered: true,
          content: (
            <div>
              {validation.errors.map((error, index) => (
                <div key={index} style={{ color: token.colorError }}>• {error}</div>
              ))}
            </div>
          ),
        });
        return;
      }

      // 显示预览对话框
      modal.confirm({
        title: '导入预览',
        width: 500,
        centered: true,
        content: (
          <div>
            <p><strong>文件版本:</strong> {validation.version}</p>
            <Divider style={{ margin: '12px 0' }} />
            <p><strong>将要导入:</strong></p>
            <ul style={{ marginLeft: 20 }}>
              <li>角色: {validation.statistics.characters} 个</li>
              <li>组织: {validation.statistics.organizations} 个</li>
            </ul>
            {validation.warnings.length > 0 && (
              <>
                <Divider style={{ margin: '12px 0' }} />
                <p style={{ color: token.colorWarning }}><strong>⚠️ 警告:</strong></p>
                <ul style={{ marginLeft: 20 }}>
                  {validation.warnings.map((warning, index) => (
                    <li key={index} style={{ color: token.colorWarning }}>{warning}</li>
                  ))}
                </ul>
              </>
            )}
          </div>
        ),
        okText: '确认导入',
        cancelText: '取消',
        onOk: async () => {
          try {
            const result = await characterApi.importCharacters(currentProject.id, file);
            
            if (result.success) {
              // 显示导入结果
              modal.success({
                title: '导入完成',
                width: 600,
                centered: true,
                content: (
                  <div>
                    <p><strong>✅ 成功导入: {result.statistics.imported} 个</strong></p>
                    {result.details.imported_characters.length > 0 && (
                      <>
                        <p style={{ marginTop: 12, marginBottom: 4 }}>角色:</p>
                        <ul style={{ marginLeft: 20 }}>
                          {result.details.imported_characters.map((name, index) => (
                            <li key={index}>{name}</li>
                          ))}
                        </ul>
                      </>
                    )}
                    {result.details.imported_organizations.length > 0 && (
                      <>
                        <p style={{ marginTop: 12, marginBottom: 4 }}>组织:</p>
                        <ul style={{ marginLeft: 20 }}>
                          {result.details.imported_organizations.map((name, index) => (
                            <li key={index}>{name}</li>
                          ))}
                        </ul>
                      </>
                    )}
                    {result.statistics.skipped > 0 && (
                      <>
                        <Divider style={{ margin: '12px 0' }} />
                        <p style={{ color: token.colorWarning }}>⚠️ 跳过: {result.statistics.skipped} 个</p>
                        <ul style={{ marginLeft: 20 }}>
                          {result.details.skipped.map((name, index) => (
                            <li key={index} style={{ color: token.colorWarning }}>{name}</li>
                          ))}
                        </ul>
                      </>
                    )}
                    {result.warnings.length > 0 && (
                      <>
                        <Divider style={{ margin: '12px 0' }} />
                        <p style={{ color: token.colorWarning }}>⚠️ 警告:</p>
                        <ul style={{ marginLeft: 20 }}>
                          {result.warnings.map((warning, index) => (
                            <li key={index} style={{ color: token.colorWarning }}>{warning}</li>
                          ))}
                        </ul>
                      </>
                    )}
                    {result.details.errors.length > 0 && (
                      <>
                        <Divider style={{ margin: '12px 0' }} />
                        <p style={{ color: token.colorError }}>❌ 失败: {result.statistics.errors} 个</p>
                        <ul style={{ marginLeft: 20 }}>
                          {result.details.errors.map((error, index) => (
                            <li key={index} style={{ color: token.colorError }}>{error}</li>
                          ))}
                        </ul>
                      </>
                    )}
                  </div>
                ),
              });
              
              // 刷新列表
              await refreshCharacters();
              setIsImportModalOpen(false);
            } else {
              message.error(result.message || '导入失败');
            }
          } catch (error: unknown) {
            const apiError = error as ApiError;
            message.error(apiError.response?.data?.detail || '导入失败');
            console.error('导入错误:', error);
          }
        },
      });
    } catch (error: unknown) {
      const apiError = error as ApiError;
      message.error(apiError.response?.data?.detail || '文件验证失败');
      console.error('验证错误:', error);
    }
  };

  // 切换选择
  const toggleSelectCharacter = (id: string) => {
    setSelectedCharacters(prev =>
      prev.includes(id) ? prev.filter(cid => cid !== id) : [...prev, id]
    );
  };

  const showGenerateModal = () => {
    modal.confirm({
      title: 'AI生成角色',
      width: 600,
      centered: true,
      content: (
        <Form form={generateForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            label="角色名称"
            name="name"
          >
            <Input placeholder="如：张三、李四（可选，AI会自动生成）" />
          </Form.Item>
          <Form.Item
            label="角色定位"
            name="role_type"
            rules={[{ required: true, message: '请选择角色定位' }]}
          >
            <Select placeholder="选择角色定位">
              <Select.Option value="protagonist">主角</Select.Option>
              <Select.Option value="supporting">配角</Select.Option>
              <Select.Option value="antagonist">反派</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item label="背景设定" name="background">
            <TextArea rows={3} placeholder="简要描述角色背景和故事环境..." />
          </Form.Item>
        </Form>
      ),
      okText: '生成',
      cancelText: '取消',
      onOk: async () => {
        const values = await generateForm.validateFields();
        await handleGenerate(values);
      },
    });
  };

  const showGenerateOrgModal = () => {
    modal.confirm({
      title: 'AI生成组织',
      width: 600,
      centered: true,
      content: (
        <Form form={generateOrgForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            label="组织名称"
            name="name"
          >
            <Input placeholder="如：天剑门、黑龙会（可选，AI会自动生成）" />
          </Form.Item>
          <Form.Item
            label="组织类型"
            name="organization_type"
          >
            <Input placeholder="如：门派、帮派、公司、学院（可选，AI会根据世界观生成）" />
          </Form.Item>
          <Form.Item label="背景设定" name="background">
            <TextArea rows={3} placeholder="简要描述组织的背景和环境..." />
          </Form.Item>
          <Form.Item label="其他要求" name="requirements">
            <TextArea rows={2} placeholder="其他特殊要求..." />
          </Form.Item>
        </Form>
      ),
      okText: '生成',
      cancelText: '取消',
      onOk: async () => {
        const values = await generateOrgForm.validateFields();
        await handleGenerateOrganization(values);
      },
    });
  };

  const characterList = characters.filter(c => !c.is_organization);
  const organizationList = characters.filter(c => c.is_organization);

  const getDisplayList = () => {
    if (activeTab === 'character') return characterList;
    if (activeTab === 'organization') return organizationList;
    return characters;
  };

  const displayList = getDisplayList();

  // 分页处理后的列表
  const paginatedList = displayList.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  // 切换Tab时重置分页
  useEffect(() => {
    setCurrentPage(1);
  }, [activeTab]);

  const isMobile = window.innerWidth <= 768;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {contextHolder}
      <div style={{
        position: 'sticky',
        top: 0,
        zIndex: 10,
        backgroundColor: 'var(--color-bg-container)',
        padding: isMobile ? '12px 0' : '16px 0',
        marginBottom: isMobile ? 12 : 16,
        borderBottom: '1px solid var(--color-border-secondary)',
        display: 'flex',
        flexDirection: isMobile ? 'column' : 'row',
        gap: isMobile ? 12 : 0,
        justifyContent: 'space-between',
        alignItems: isMobile ? 'stretch' : 'center'
      }}>
        <h2 style={{ margin: 0, fontSize: isMobile ? 18 : 24 }}>
          <TeamOutlined style={{ marginRight: 8 }} />
          角色与组织管理
        </h2>
        <Space wrap>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setCreateType('character');
              setIsCreateModalOpen(true);
            }}
            size={isMobile ? 'small' : 'middle'}
          >
            创建角色
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setCreateType('organization');
              setIsCreateModalOpen(true);
            }}
            size={isMobile ? 'small' : 'middle'}
          >
            创建组织
          </Button>
          <Button
            type="dashed"
            icon={<ThunderboltOutlined />}
            onClick={showGenerateModal}
            loading={isGenerating}
            size={isMobile ? 'small' : 'middle'}
          >
            AI生成角色
          </Button>
          <Button
            type="dashed"
            icon={<ThunderboltOutlined />}
            onClick={showGenerateOrgModal}
            loading={isGenerating}
            size={isMobile ? 'small' : 'middle'}
          >
            AI生成组织
          </Button>
          <Button
            icon={<ImportOutlined />}
            onClick={() => setIsImportModalOpen(true)}
            size={isMobile ? 'small' : 'middle'}
          >
            导入
          </Button>
          {selectedCharacters.length > 0 && (
            <>
              <Button
                icon={<ExportOutlined />}
                onClick={handleExportSelected}
                size={isMobile ? 'small' : 'middle'}
              >
                批量导出 ({selectedCharacters.length})
              </Button>
              <Button
                type="primary"
                danger
                icon={<DeleteOutlined />}
                onClick={() => {
                  modal.confirm({
                    title: '批量删除确认',
                    content: `确定删除选中的 ${selectedCharacters.length} 个角色/组织吗？此操作不可撤销。`,
                    okText: '确定删除',
                    cancelText: '取消',
                    onOk: async () => {
                      for (const id of selectedCharacters) {
                        await handleDeleteCharacter(id);
                      }
                      setSelectedCharacters([]);
                      message.success('批量删除成功');
                    },
                  });
                }}
                size={isMobile ? 'small' : 'middle'}
              >
                批量删除 ({selectedCharacters.length})
              </Button>
            </>
          )}
        </Space>
      </div>

      {characters.length > 0 && (
        <div style={{
          position: 'sticky',
          top: isMobile ? 60 : 72,
          zIndex: 9,
          backgroundColor: 'var(--color-bg-container)',
          paddingBottom: 8,
          borderBottom: '1px solid var(--color-border-secondary)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <Tabs
            activeKey={activeTab}
            onChange={(key) => setActiveTab(key as 'all' | 'character' | 'organization')}
            items={[
              {
                key: 'all',
                label: `全部 (${characters.length})`,
              },
              {
                key: 'character',
                label: (
                  <span>
                    <UserOutlined /> 角色 ({characterList.length})
                  </span>
                ),
              },
              {
                key: 'organization',
                label: (
                  <span>
                    <TeamOutlined /> 组织 ({organizationList.length})
                  </span>
                ),
              },
            ]}
            style={{ marginBottom: 0 }}
          />
          <Space>
            <Segmented
              value={viewMode}
              onChange={(value) => setViewMode(value as 'card' | 'list')}
              options={[
                { value: 'card', icon: <AppstoreOutlined />, label: '卡片' },
                { value: 'list', icon: <UnorderedListOutlined />, label: '列表' },
              ]}
              size="small"
              style={{
                '--segmented-item-selected-bg': token.colorPrimary,
                '--segmented-item-selected-color': token.colorBgContainer,
              } as React.CSSProperties}
            />
            <Checkbox
              checked={selectedCharacters.length === paginatedList.length && paginatedList.length > 0}
              indeterminate={selectedCharacters.length > 0 && selectedCharacters.length < paginatedList.length}
              onChange={() => {
                // 全选/取消全选当前页
                if (selectedCharacters.length === paginatedList.length) {
                  setSelectedCharacters([]);
                } else {
                  setSelectedCharacters(paginatedList.map(c => c.id));
                }
              }}
            >
              {selectedCharacters.length > 0 ? `已选 ${selectedCharacters.length} 个` : '全选'}
            </Checkbox>
            {selectedCharacters.length > 0 && (
              <Button
                type="link"
                size="small"
                onClick={() => setSelectedCharacters([])}
              >
                取消选择
              </Button>
            )}
          </Space>
        </div>
      )}

      <div style={{ flex: 1, overflowY: 'auto' }}>
        {characters.length === 0 ? (
          <Empty description="还没有角色或组织，开始创建吧！" />
        ) : (
          <>
            {/* 卡片视图 */}
            {viewMode === 'card' && (
              <Row gutter={isMobile ? [8, 8] : charactersPageGridConfig.gutter}>
                {activeTab === 'all' && (
                  <>
                    {characterList.length > 0 && (
                      <>
                        <Col span={24}>
                          <Divider orientation="left">
                            <Title level={5} style={{ margin: 0 }}>
                              <UserOutlined style={{ marginRight: 8 }} />
                              角色 ({characterList.length})
                            </Title>
                          </Divider>
                        </Col>
                        {paginatedList.filter(c => !c.is_organization).map((character) => (
                          <Col
                            xs={24}
                            sm={charactersPageGridConfig.sm}
                            md={charactersPageGridConfig.md}
                            lg={charactersPageGridConfig.lg}
                            xl={charactersPageGridConfig.xl}
                            key={character.id}
                            style={{ padding: isMobile ? '4px' : '8px' }}
                          >
                            <div style={{ position: 'relative' }}>
                              <Checkbox
                                checked={selectedCharacters.includes(character.id)}
                                onChange={() => toggleSelectCharacter(character.id)}
                                style={{ position: 'absolute', top: 8, left: 8, zIndex: 1 }}
                              />
                              <CharacterCard
                                character={character}
                                onEdit={handleEditCharacter}
                                onDelete={handleDeleteCharacterWrapper}
                                onExport={() => handleExportSingle(character.id)}
                                onClick={handleViewDetail}
                              />
                            </div>
                          </Col>
                        ))}
                      </>
                    )}

                    {organizationList.length > 0 && (
                      <>
                        <Col span={24}>
                          <Divider orientation="left">
                            <Title level={5} style={{ margin: 0 }}>
                              <TeamOutlined style={{ marginRight: 8 }} />
                              组织 ({organizationList.length})
                            </Title>
                          </Divider>
                        </Col>
                        {paginatedList.filter(c => c.is_organization).map((org) => (
                          <Col
                            xs={24}
                            sm={charactersPageGridConfig.sm}
                            md={charactersPageGridConfig.md}
                            lg={charactersPageGridConfig.lg}
                            xl={charactersPageGridConfig.xl}
                            key={org.id}
                            style={{ padding: isMobile ? '4px' : '8px' }}
                          >
                            <div style={{ position: 'relative' }}>
                              <Checkbox
                                checked={selectedCharacters.includes(org.id)}
                                onChange={() => toggleSelectCharacter(org.id)}
                                style={{ position: 'absolute', top: 8, left: 8, zIndex: 1 }}
                              />
                              <CharacterCard
                                character={org}
                                onEdit={handleEditCharacter}
                                onDelete={handleDeleteCharacterWrapper}
                                onExport={() => handleExportSingle(org.id)}
                                onClick={handleViewDetail}
                              />
                            </div>
                          </Col>
                        ))}
                      </>
                    )}
                  </>
                )}

                {activeTab !== 'all' && paginatedList.map((item) => (
                  <Col
                    xs={24}
                    sm={charactersPageGridConfig.sm}
                    md={charactersPageGridConfig.md}
                    lg={charactersPageGridConfig.lg}
                    xl={charactersPageGridConfig.xl}
                    key={item.id}
                    style={{ padding: isMobile ? '4px' : '8px' }}
                  >
                    <div style={{ position: 'relative' }}>
                      <Checkbox
                        checked={selectedCharacters.includes(item.id)}
                        onChange={() => toggleSelectCharacter(item.id)}
                        style={{ position: 'absolute', top: 8, left: 8, zIndex: 1 }}
                      />
                      <CharacterCard
                        character={item}
                        onEdit={handleEditCharacter}
                        onDelete={handleDeleteCharacterWrapper}
                        onExport={() => handleExportSingle(item.id)}
                        onClick={handleViewDetail}
                      />
                    </div>
                  </Col>
                ))}
              </Row>
            )}

            {/* 列表视图 */}
            {viewMode === 'list' && (
              <List
                itemLayout="horizontal"
                dataSource={paginatedList}
                renderItem={(item) => (
                  <List.Item
                    actions={[
                      <Button
                        key="edit"
                        type="link"
                        size="small"
                        icon={<EditOutlined />}
                        onClick={() => handleEditCharacter(item)}
                      />,
                      <Popconfirm
                        key="delete"
                        title={`确定删除这个${item.is_organization ? '组织' : '角色'}吗？`}
                        onConfirm={() => handleDeleteCharacterWrapper(item.id)}
                        okText="确定"
                        cancelText="取消"
                      >
                        <Button type="link" size="small" danger icon={<DeleteOutlined />} />
                      </Popconfirm>,
                    ]}
                    style={{ padding: '8px 16px', borderBottom: '1px solid var(--color-border-secondary)' }}
                  >
                    <List.Item.Meta
                      avatar={
                        <Space>
                          <Checkbox
                            checked={selectedCharacters.includes(item.id)}
                            onChange={() => toggleSelectCharacter(item.id)}
                          />
                          {item.is_organization ? (
                            <BankOutlined style={{ fontSize: 24, color: token.colorSuccess }} />
                          ) : (
                            <UserOutlined style={{ fontSize: 24, color: token.colorPrimary }} />
                          )}
                        </Space>
                      }
                      title={
                        <Space>
                          <span>{item.name}</span>
                          {item.is_organization ? (
                            <Tag color="green">组织</Tag>
                          ) : (
                            item.role_type && (
                              <Tag color={
                                item.role_type === 'protagonist' ? 'blue' :
                                item.role_type === 'supporting' ? 'green' :
                                item.role_type === 'antagonist' ? 'red' : 'default'
                              }>
                                {item.role_type === 'protagonist' ? '主角' :
                                 item.role_type === 'supporting' ? '配角' :
                                 item.role_type === 'antagonist' ? '反派' : '其他'}
                              </Tag>
                            )
                          )}
                        </Space>
                      }
                      description={
                        <Text type="secondary" ellipsis={{ tooltip: item.background }}>
                          {item.background || '暂无背景'}
                        </Text>
                      }
                    />
                  </List.Item>
                )}
              />
            )}

            {displayList.length === 0 && (
              <Empty
                description={
                  activeTab === 'character'
                    ? '暂无角色'
                    : activeTab === 'organization'
                      ? '暂无组织'
                      : '暂无数据'
                }
              />
            )}

            {/* 分页组件 - 列表视图始终显示，卡片视图超过pageSize时显示 */}
            {(viewMode === 'list' || displayList.length > pageSize) && (
              <div style={{
                display: 'flex',
                justifyContent: 'flex-end',
                padding: '16px 0',
                marginTop: 16,
                borderTop: '1px solid var(--color-border-secondary)'
              }}>
                <Pagination
                  current={currentPage}
                  pageSize={pageSize}
                  total={displayList.length}
                  onChange={(page, newPageSize) => {
                    setCurrentPage(page);
                    if (newPageSize !== pageSize) {
                      setPageSize(newPageSize);
                      setCurrentPage(1);
                    }
                  }}
                  showSizeChanger
                  showQuickJumper
                  showTotal={(total) => `共 ${total} 条`}
                  pageSizeOptions={['10', '20', '50', '100']}
                />
              </div>
            )}
          </>
        )}
      </div>

      <Modal
        title={editingCharacter?.is_organization ? '编辑组织' : '编辑角色'}
        open={isEditModalOpen}
        onCancel={() => {
          setIsEditModalOpen(false);
          editForm.resetFields();
          setEditingCharacter(null);
          setEditingAttributes(null);
        }}
        footer={
          <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
            <Button onClick={() => {
              setIsEditModalOpen(false);
              editForm.resetFields();
              setEditingCharacter(null);
              setEditingAttributes(null);
            }}>
              取消
            </Button>
            <Button type="primary" onClick={() => editForm.submit()}>
              保存
            </Button>
          </Space>
        }
        centered
        width={isMobile ? '100%' : 700}
        style={isMobile ? { top: 0, paddingBottom: 0, maxWidth: '100vw' } : undefined}
        styles={{
          body: {
            maxHeight: isMobile ? 'calc(100vh - 110px)' : 'calc(100vh - 200px)',
            overflowY: 'auto',
            overflowX: 'hidden'
          }
        }}
      >
        <Form form={editForm} layout="vertical" onFinish={handleUpdateCharacter} style={{ marginTop: 8 }}>
          {!editingCharacter?.is_organization ? (
            <>
              {/* 编辑角色 - 第一行：名称、定位、年龄、性别 */}
              <Row gutter={12}>
                <Col span={8}>
                  <Form.Item
                    label="角色名称"
                    name="name"
                    rules={[{ required: true, message: '请输入角色名称' }]}
                    style={{ marginBottom: 12 }}
                  >
                    <Input placeholder="角色名称" />
                  </Form.Item>
                </Col>
                <Col span={6}>
                  <Form.Item label="角色定位" name="role_type" style={{ marginBottom: 12 }}>
                    <Select>
                      <Select.Option value="protagonist">主角</Select.Option>
                      <Select.Option value="supporting">配角</Select.Option>
                      <Select.Option value="antagonist">反派</Select.Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={5}>
                  <Form.Item label="年龄" name="age" style={{ marginBottom: 12 }}>
                    <Input placeholder="如：25岁" />
                  </Form.Item>
                </Col>
                <Col span={5}>
                  <Form.Item label="性别" name="gender" style={{ marginBottom: 12 }}>
                    <Select placeholder="性别">
                      <Select.Option value="男">男</Select.Option>
                      <Select.Option value="女">女</Select.Option>
                      <Select.Option value="其他">其他</Select.Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              {/* 第二行：性格特点、外貌描写 */}
              <Row gutter={12}>
                <Col span={12}>
                  <Form.Item label="性格特点" name="personality" style={{ marginBottom: 12 }}>
                    <TextArea rows={2} placeholder="描述角色的性格特点..." />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="外貌描写" name="appearance" style={{ marginBottom: 12 }}>
                    <TextArea rows={2} placeholder="描述角色的外貌特征..." />
                  </Form.Item>
                </Col>
              </Row>

              {/* 人际关系（只读，由关系管理页面维护） */}
              {editingCharacter?.relationships && (
                <Form.Item label="人际关系（由关系管理维护）" style={{ marginBottom: 12 }}>
                  <Input.TextArea
                    value={editingCharacter.relationships}
                    readOnly
                    autoSize={{ minRows: 1, maxRows: 3 }}
                    style={{ backgroundColor: token.colorFillTertiary, cursor: 'default' }}
                  />
                </Form.Item>
              )}

              {/* 第四行：角色背景 */}
              <Form.Item label="角色背景" name="background" style={{ marginBottom: 12 }}>
                <TextArea rows={2} placeholder="描述角色的背景故事..." />
              </Form.Item>

              {/* 职业信息 */}
              {(mainCareers.length > 0 || subCareers.length > 0) && (
                <>
                  <Divider style={{ margin: '8px 0' }}>
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>职业信息</Typography.Text>
                  </Divider>
                  {mainCareers.length > 0 && (
                    <Row gutter={12}>
                      <Col span={16}>
                        <Form.Item label="主职业" name="main_career_id" tooltip="角色的主要修炼职业" style={{ marginBottom: 12 }}>
                          <Select placeholder="选择主职业" allowClear size="small">
                            {mainCareers.map(career => (
                              <Select.Option key={career.id} value={career.id}>
                                {career.name}（最高{career.max_stage}阶）
                              </Select.Option>
                            ))}
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Form.Item label="当前阶段" name="main_career_stage" tooltip="主职业当前修炼到的阶段" style={{ marginBottom: 12 }}>
                          <InputNumber
                            min={1}
                            max={watchedEditMainCareerId ?
                              mainCareers.find(c => c.id === watchedEditMainCareerId)?.max_stage || 10
                              : 10}
                            style={{ width: '100%' }}
                            placeholder="阶段"
                            size="small"
                          />
                        </Form.Item>
                      </Col>
                    </Row>
                  )}
                  {subCareers.length > 0 && (
                    <Form.List name="sub_career_data">
                      {(fields, { add, remove }) => (
                        <>
                          <div style={{ marginBottom: 4 }}>
                            <Typography.Text strong style={{ fontSize: 12 }}>副职业</Typography.Text>
                          </div>
                          <div style={{ maxHeight: '80px', overflowY: 'auto', overflowX: 'hidden', marginBottom: 8, paddingRight: 8 }}>
                            {fields.map((field) => (
                              <Row key={field.key} gutter={8} style={{ marginBottom: 4 }}>
                                <Col span={16}>
                                  <Form.Item
                                    key={field.key}
                                    name={[field.name, 'career_id']}
                                    rules={[{ required: true, message: '请选择副职业' }]}
                                    style={{ marginBottom: 0 }}
                                  >
                                    <Select placeholder="选择副职业" size="small">
                                      {subCareers.map(career => (
                                        <Select.Option key={career.id} value={career.id}>
                                          {career.name}（最高{career.max_stage}阶）
                                        </Select.Option>
                                      ))}
                                    </Select>
                                  </Form.Item>
                                </Col>
                                <Col span={5}>
                                  <Form.Item
                                    key={`${field.key}-stage`}
                                    name={[field.name, 'stage']}
                                    rules={[{ required: true, message: '阶段' }]}
                                    style={{ marginBottom: 0 }}
                                  >
                                    <InputNumber
                                      min={1}
                                      max={(() => {
                                        const careerId = watchedEditSubCareerData?.[field.name]?.career_id;
                                        const career = subCareers.find(c => c.id === careerId);
                                        return career?.max_stage || 10;
                                      })()}
                                      placeholder="阶段"
                                      style={{ width: '100%' }}
                                      size="small"
                                    />
                                  </Form.Item>
                                </Col>
                                <Col span={3}>
                                  <Button
                                    type="text"
                                    danger
                                    size="small"
                                    onClick={() => remove(field.name)}
                                  >
                                    删除
                                  </Button>
                                </Col>
                              </Row>
                            ))}
                          </div>
                          <Button
                            type="dashed"
                            onClick={() => add({ career_id: undefined, stage: 1 })}
                            block
                            size="small"
                          >
                            + 添加副职业
                          </Button>
                        </>
                      )}
                    </Form.List>
                  )}
                </>
              )}

              {/* 能力值编辑区域 */}
              {attributeSchema && !editingCharacter?.is_organization && (
                <>
                  <Divider style={{ margin: '8px 0' }}>
                    <Space>
                      <Typography.Text type="secondary" style={{ fontSize: 12 }}>能力值</Typography.Text>
                      <Button
                        type="text"
                        size="small"
                        icon={<ReloadOutlined />}
                        onClick={refreshAttributeSchema}
                        title="刷新属性配置（使用最新默认配置）"
                      />
                    </Space>
                  </Divider>
                  <DynamicAttributesEditor
                    attributeSchema={attributeSchema}
                    values={editingAttributes}
                    onChange={setEditingAttributes}
                  />
                </>
              )}
            </>
          ) : (
            <>
              {/* 编辑组织 - 第一行：名称、类型、势力等级 */}
              <Row gutter={12}>
                <Col span={10}>
                  <Form.Item
                    label="组织名称"
                    name="name"
                    rules={[{ required: true, message: '请输入组织名称' }]}
                    style={{ marginBottom: 12 }}
                  >
                    <Input placeholder="组织名称" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    label="组织类型"
                    name="organization_type"
                    rules={[{ required: true, message: '请输入组织类型' }]}
                    style={{ marginBottom: 12 }}
                  >
                    <Input placeholder="如：门派、帮派" />
                  </Form.Item>
                </Col>
                <Col span={6}>
                  <Form.Item
                    label="势力等级"
                    name="power_level"
                    tooltip="0-100的数值"
                    style={{ marginBottom: 12 }}
                  >
                    <InputNumber min={0} max={100} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              </Row>

              {/* 第二行：组织目的 */}
              <Form.Item
                label="组织目的"
                name="organization_purpose"
                rules={[{ required: true, message: '请输入组织目的' }]}
                style={{ marginBottom: 12 }}
              >
                <Input placeholder="描述组织的宗旨和目标..." />
              </Form.Item>

              {/* 第三行：主要成员（只读展示） */}
              <Form.Item
                label="主要成员"
                name="organization_members"
                style={{ marginBottom: 4 }}
                tooltip="成员信息由组织管理模块维护，此处仅展示"
              >
                <TextArea
                  disabled
                  autoSize={{ minRows: 1, maxRows: 4 }}
                  placeholder="暂无成员，请在组织管理中添加"
                  style={{ color: token.colorText, backgroundColor: token.colorFillAlter }}
                />
              </Form.Item>
              <div style={{ marginBottom: 12, fontSize: 12, color: token.colorTextTertiary }}>
                💡 请前往「组织管理」页面添加或管理组织成员
              </div>

              {/* 第四行：所在地、代表颜色 */}
              <Row gutter={12}>
                <Col span={12}>
                  <Form.Item label="所在地" name="location" style={{ marginBottom: 12 }}>
                    <Input placeholder="总部位置" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="代表颜色" name="color" style={{ marginBottom: 12 }}>
                    <Input placeholder="如：金色" />
                  </Form.Item>
                </Col>
              </Row>

              {/* 第四行：格言/口号 */}
              <Form.Item label="格言/口号" name="motto" style={{ marginBottom: 12 }}>
                <Input placeholder="组织的宗旨、格言或口号" />
              </Form.Item>

              {/* 第五行：组织背景 */}
              <Form.Item label="组织背景" name="background" style={{ marginBottom: 12 }}>
                <TextArea rows={2} placeholder="描述组织的背景故事..." />
              </Form.Item>
            </>
          )}
        </Form>
      </Modal>

      {/* 手动创建角色/组织模态框 */}
      <Modal
        title={createType === 'character' ? '创建角色' : '创建组织'}
        open={isCreateModalOpen}
        onCancel={() => {
          setIsCreateModalOpen(false);
          createForm.resetFields();
        }}
        footer={null}
        centered
        width={isMobile ? '100%' : 700}
        style={isMobile ? { top: 0, paddingBottom: 0, maxWidth: '100vw' } : undefined}
        styles={{
          body: {
            maxHeight: isMobile ? 'calc(100vh - 110px)' : 'calc(100vh - 200px)',
            overflowY: 'auto',
            overflowX: 'hidden'
          }
        }}
      >
        <Form form={createForm} layout="vertical" onFinish={handleCreateCharacter} style={{ marginTop: 8 }}>
          {createType === 'character' ? (
            <>
              {/* 角色基本信息 - 第一行：名称、定位、年龄、性别 */}
              <Row gutter={12}>
                <Col span={8}>
                  <Form.Item
                    label="角色名称"
                    name="name"
                    rules={[{ required: true, message: '请输入角色名称' }]}
                    style={{ marginBottom: 12 }}
                  >
                    <Input placeholder="角色名称" />
                  </Form.Item>
                </Col>
                <Col span={6}>
                  <Form.Item label="角色定位" name="role_type" initialValue="supporting" style={{ marginBottom: 12 }}>
                    <Select>
                      <Select.Option value="protagonist">主角</Select.Option>
                      <Select.Option value="supporting">配角</Select.Option>
                      <Select.Option value="antagonist">反派</Select.Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={5}>
                  <Form.Item label="年龄" name="age" style={{ marginBottom: 12 }}>
                    <Input placeholder="如：25岁" />
                  </Form.Item>
                </Col>
                <Col span={5}>
                  <Form.Item label="性别" name="gender" style={{ marginBottom: 12 }}>
                    <Select placeholder="性别">
                      <Select.Option value="男">男</Select.Option>
                      <Select.Option value="女">女</Select.Option>
                      <Select.Option value="其他">其他</Select.Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              {/* 第二行：性格特点、外貌描写 */}
              <Row gutter={12}>
                <Col span={12}>
                  <Form.Item label="性格特点" name="personality" style={{ marginBottom: 12 }}>
                    <TextArea rows={2} placeholder="描述角色的性格特点..." />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="外貌描写" name="appearance" style={{ marginBottom: 12 }}>
                    <TextArea rows={2} placeholder="描述角色的外貌特征..." />
                  </Form.Item>
                </Col>
              </Row>

              {/* 第三行：角色背景 */}
              <Form.Item label="角色背景" name="background" style={{ marginBottom: 12 }}>
                <TextArea rows={2} placeholder="描述角色的背景故事..." />
              </Form.Item>

              {/* 职业信息 - 折叠区域 */}
              {(mainCareers.length > 0 || subCareers.length > 0) && (
                <>
                  <Divider style={{ margin: '8px 0' }}>
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>职业信息（可选）</Typography.Text>
                  </Divider>
                  {mainCareers.length > 0 && (
                    <Row gutter={12}>
                      <Col span={16}>
                        <Form.Item label="主职业" name="main_career_id" tooltip="角色的主要修炼职业" style={{ marginBottom: 12 }}>
                          <Select placeholder="选择主职业" allowClear size="small">
                            {mainCareers.map(career => (
                              <Select.Option key={career.id} value={career.id}>
                                {career.name}（最高{career.max_stage}阶）
                              </Select.Option>
                            ))}
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Form.Item label="当前阶段" name="main_career_stage" tooltip="主职业当前修炼到的阶段" style={{ marginBottom: 12 }}>
                          <InputNumber
                            min={1}
                            max={watchedCreateMainCareerId ?
                              mainCareers.find(c => c.id === watchedCreateMainCareerId)?.max_stage || 10
                              : 10}
                            style={{ width: '100%' }}
                            placeholder="阶段"
                            size="small"
                          />
                        </Form.Item>
                      </Col>
                    </Row>
                  )}
                  {subCareers.length > 0 && (
                    <Form.List name="sub_career_data">
                      {(fields, { add, remove }) => (
                        <>
                          <div style={{ marginBottom: 4 }}>
                            <Typography.Text strong style={{ fontSize: 12 }}>副职业</Typography.Text>
                          </div>
                          <div style={{ maxHeight: '80px', overflowY: 'auto', overflowX: 'hidden', marginBottom: 8, paddingRight: 8 }}>
                            {fields.map((field) => (
                              <Row key={field.key} gutter={8} style={{ marginBottom: 4 }}>
                                <Col span={16}>
                                  <Form.Item
                                    key={field.key}
                                    name={[field.name, 'career_id']}
                                    rules={[{ required: true, message: '请选择副职业' }]}
                                    style={{ marginBottom: 0 }}
                                  >
                                    <Select placeholder="选择副职业" size="small">
                                      {subCareers.map(career => (
                                        <Select.Option key={career.id} value={career.id}>
                                          {career.name}（最高{career.max_stage}阶）
                                        </Select.Option>
                                      ))}
                                    </Select>
                                  </Form.Item>
                                </Col>
                                <Col span={5}>
                                  <Form.Item
                                    key={`${field.key}-stage`}
                                    name={[field.name, 'stage']}
                                    rules={[{ required: true, message: '阶段' }]}
                                    style={{ marginBottom: 0 }}
                                  >
                                    <InputNumber
                                      min={1}
                                      max={(() => {
                                        const careerId = watchedCreateSubCareerData?.[field.name]?.career_id;
                                        const career = subCareers.find(c => c.id === careerId);
                                        return career?.max_stage || 10;
                                      })()}
                                      placeholder="阶段"
                                      style={{ width: '100%' }}
                                      size="small"
                                    />
                                  </Form.Item>
                                </Col>
                                <Col span={3}>
                                  <Button
                                    type="text"
                                    danger
                                    size="small"
                                    onClick={() => remove(field.name)}
                                  >
                                    删除
                                  </Button>
                                </Col>
                              </Row>
                            ))}
                          </div>
                          <Button
                            type="dashed"
                            onClick={() => add({ career_id: undefined, stage: 1 })}
                            block
                            size="small"
                          >
                            + 添加副职业
                          </Button>
                        </>
                      )}
                    </Form.List>
                  )}
                </>
              )}
            </>
          ) : (
            <>
              {/* 组织基本信息 - 第一行：名称、类型、势力等级 */}
              <Row gutter={12}>
                <Col span={10}>
                  <Form.Item
                    label="组织名称"
                    name="name"
                    rules={[{ required: true, message: '请输入组织名称' }]}
                    style={{ marginBottom: 12 }}
                  >
                    <Input placeholder="组织名称" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    label="组织类型"
                    name="organization_type"
                    rules={[{ required: true, message: '请输入组织类型' }]}
                    style={{ marginBottom: 12 }}
                  >
                    <Input placeholder="如：门派、帮派" />
                  </Form.Item>
                </Col>
                <Col span={6}>
                  <Form.Item
                    label="势力等级"
                    name="power_level"
                    initialValue={50}
                    tooltip="0-100的数值"
                    style={{ marginBottom: 12 }}
                  >
                    <InputNumber min={0} max={100} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              </Row>

              {/* 第二行：组织目的 */}
              <Form.Item
                label="组织目的"
                name="organization_purpose"
                rules={[{ required: true, message: '请输入组织目的' }]}
                style={{ marginBottom: 12 }}
              >
                <Input placeholder="描述组织的宗旨和目标..." />
              </Form.Item>

              {/* 第三行：所在地、代表颜色 */}
              <Row gutter={12}>
                <Col span={12}>
                  <Form.Item label="所在地" name="location" style={{ marginBottom: 12 }}>
                    <Input placeholder="总部位置" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="代表颜色" name="color" style={{ marginBottom: 12 }}>
                    <Input placeholder="如：金色" />
                  </Form.Item>
                </Col>
              </Row>

              {/* 第四行：格言/口号 */}
              <Form.Item label="格言/口号" name="motto" style={{ marginBottom: 12 }}>
                <Input placeholder="组织的宗旨、格言或口号" />
              </Form.Item>

              {/* 第五行：组织背景 */}
              <Form.Item label="组织背景" name="background" style={{ marginBottom: 12 }}>
                <TextArea rows={2} placeholder="描述组织的背景故事..." />
              </Form.Item>
            </>
          )}

          <Form.Item style={{ marginBottom: 0, marginTop: 16 }}>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button onClick={() => {
                setIsCreateModalOpen(false);
                createForm.resetFields();
              }}>
                取消
              </Button>
              <Button type="primary" htmlType="submit">
                创建
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 导入对话框 */}
      <Modal
        title="导入角色/组织"
        open={isImportModalOpen}
        onCancel={() => setIsImportModalOpen(false)}
        footer={null}
        width={500}
        centered
      >
        <div style={{ textAlign: 'center', padding: '40px 20px' }}>
          <DownloadOutlined style={{ fontSize: 48, color: '#1890ff', marginBottom: 16 }} />
          <p style={{ fontSize: 16, marginBottom: 24 }}>
            选择之前导出的角色/组织JSON文件进行导入
          </p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            style={{ display: 'none' }}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) {
                handleFileSelect(file);
                e.target.value = ''; // 清空input，允许重复选择同一文件
              }
            }}
          />
          <Button
            type="primary"
            size="large"
            icon={<ImportOutlined />}
            onClick={() => fileInputRef.current?.click()}
          >
            选择文件
          </Button>
          <Divider />
          <div style={{ textAlign: 'left', fontSize: 12, color: '#666' }}>
            <p style={{ marginBottom: 8 }}><strong>说明：</strong></p>
            <ul style={{ marginLeft: 20 }}>
              <li>支持导入.json格式的角色/组织文件</li>
              <li>重复名称的角色/组织将被跳过</li>
              <li>职业信息如不存在将被忽略</li>
            </ul>
          </div>
        </div>
      </Modal>

      {/* 角色/组织详情弹窗 */}
      <Modal
        title={detailCharacter?.is_organization ? '组织详情' : '角色详情'}
        open={detailModalOpen}
        onCancel={() => setDetailModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalOpen(false)}>
            关闭
          </Button>,
          <Button key="edit" type="primary" onClick={() => {
            setDetailModalOpen(false);
            if (detailCharacter) {
              handleEditCharacter(detailCharacter);
            }
          }}>
            编辑
          </Button>
        ]}
        width={700}
      >
        {detailCharacter && (
          <div>
            {/* 基本信息 */}
            <Divider orientation="left">基本信息</Divider>
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Typography.Text type="secondary">名称：</Typography.Text>
                <Typography.Text strong style={{ marginLeft: 8 }}>{detailCharacter.name}</Typography.Text>
              </Col>
              {!detailCharacter.is_organization && (
                <>
                  <Col span={12}>
                    <Typography.Text type="secondary">年龄：</Typography.Text>
                    <Typography.Text style={{ marginLeft: 8 }}>{detailCharacter.age || '未设置'}</Typography.Text>
                  </Col>
                  <Col span={12}>
                    <Typography.Text type="secondary">性别：</Typography.Text>
                    <Typography.Text style={{ marginLeft: 8 }}>{detailCharacter.gender || '未设置'}</Typography.Text>
                  </Col>
                  <Col span={12}>
                    <Typography.Text type="secondary">角色类型：</Typography.Text>
                    <Tag style={{ marginLeft: 8 }} color={
                      detailCharacter.role_type === 'protagonist' ? 'blue' :
                      detailCharacter.role_type === 'supporting' ? 'green' :
                      detailCharacter.role_type === 'antagonist' ? 'red' : 'default'
                    }>
                      {detailCharacter.role_type === 'protagonist' ? '主角' :
                       detailCharacter.role_type === 'supporting' ? '配角' :
                       detailCharacter.role_type === 'antagonist' ? '反派' : '其他'}
                    </Tag>
                  </Col>
                </>
              )}
              {detailCharacter.is_organization && (
                <>
                  <Col span={12}>
                    <Typography.Text type="secondary">类型：</Typography.Text>
                    <Tag style={{ marginLeft: 8 }} color="cyan">{detailCharacter.organization_type || '未设置'}</Tag>
                  </Col>
                  <Col span={12}>
                    <Typography.Text type="secondary">势力等级：</Typography.Text>
                    <Tag style={{ marginLeft: 8 }} color={
                      (detailCharacter.power_level ?? 0) >= 70 ? 'red' :
                      (detailCharacter.power_level ?? 0) >= 50 ? 'orange' : 'default'
                    }>
                      {detailCharacter.power_level ?? '未设置'}
                    </Tag>
                  </Col>
                  <Col span={12}>
                    <Typography.Text type="secondary">所在地：</Typography.Text>
                    <Typography.Text style={{ marginLeft: 8 }}>{detailCharacter.location || '未设置'}</Typography.Text>
                  </Col>
                  <Col span={12}>
                    <Typography.Text type="secondary">代表颜色：</Typography.Text>
                    <Typography.Text style={{ marginLeft: 8 }}>{detailCharacter.color || '未设置'}</Typography.Text>
                  </Col>
                </>
              )}
              <Col span={12}>
                <Typography.Text type="secondary">状态：</Typography.Text>
                <Tag style={{ marginLeft: 8 }} color={
                  detailCharacter.status === 'active' ? 'green' :
                  detailCharacter.status === 'deceased' ? 'default' :
                  detailCharacter.status === 'missing' ? 'orange' :
                  detailCharacter.status === 'retired' ? 'default' :
                  detailCharacter.status === 'destroyed' ? 'default' : 'green'
                }>
                  {detailCharacter.status === 'active' ? '活跃' :
                   detailCharacter.status === 'deceased' ? '已死亡' :
                   detailCharacter.status === 'missing' ? '已失踪' :
                   detailCharacter.status === 'retired' ? '已退场' :
                   detailCharacter.status === 'destroyed' ? '已覆灭' : '活跃'}
                </Tag>
              </Col>
            </Row>

            {/* 性格与外貌（仅角色） */}
            {!detailCharacter.is_organization && (
              <>
                <Divider orientation="left">性格与外貌</Divider>
                {detailCharacter.personality && (
                  <div style={{ marginBottom: 16 }}>
                    <Typography.Text type="secondary">性格：</Typography.Text>
                    <Typography.Paragraph style={{ marginTop: 8, whiteSpace: 'pre-wrap' }}>
                      {detailCharacter.personality}
                    </Typography.Paragraph>
                  </div>
                )}
                {detailCharacter.appearance && (
                  <div style={{ marginBottom: 16 }}>
                    <Typography.Text type="secondary">外貌：</Typography.Text>
                    <Typography.Paragraph style={{ marginTop: 8, whiteSpace: 'pre-wrap' }}>
                      {detailCharacter.appearance}
                    </Typography.Paragraph>
                  </div>
                )}
                {detailCharacter.traits && (
                  <div style={{ marginBottom: 16 }}>
                    <Typography.Text type="secondary">特质：</Typography.Text>
                    <Typography.Paragraph style={{ marginTop: 8, whiteSpace: 'pre-wrap' }}>
                      {detailCharacter.traits}
                    </Typography.Paragraph>
                  </div>
                )}
                {detailCharacter.relationships && (
                  <div style={{ marginBottom: 16 }}>
                    <Typography.Text type="secondary">人物关系：</Typography.Text>
                    <Typography.Paragraph style={{ marginTop: 8, whiteSpace: 'pre-wrap' }}>
                      {detailCharacter.relationships}
                    </Typography.Paragraph>
                  </div>
                )}
              </>
            )}

            {/* 心理状态（仅角色） */}
            {!detailCharacter.is_organization && detailCharacter.current_state && (
              <>
                <Divider orientation="left">心理状态</Divider>
                <Row gutter={[16, 16]}>
                  <Col span={12}>
                    <Typography.Text type="secondary">当前状态：</Typography.Text>
                    <Typography.Text style={{ marginLeft: 8 }}>{detailCharacter.current_state}</Typography.Text>
                  </Col>
                  {detailCharacter.state_updated_chapter && (
                    <Col span={12}>
                      <Typography.Text type="secondary">更新章节：</Typography.Text>
                      <Typography.Text style={{ marginLeft: 8 }}>第{detailCharacter.state_updated_chapter}章</Typography.Text>
                    </Col>
                  )}
                </Row>
              </>
            )}

            {/* 状态变更信息 */}
            {detailCharacter.status && detailCharacter.status !== 'active' && detailCharacter.status_changed_chapter && (
              <>
                <Divider orientation="left">状态变更</Divider>
                <Row gutter={[16, 16]}>
                  <Col span={12}>
                    <Typography.Text type="secondary">变更状态：</Typography.Text>
                    <Tag style={{ marginLeft: 8 }} color={
                      detailCharacter.status === 'deceased' ? 'default' :
                      detailCharacter.status === 'missing' ? 'orange' :
                      detailCharacter.status === 'retired' ? 'default' :
                      detailCharacter.status === 'destroyed' ? 'default' : 'green'
                    }>
                      {detailCharacter.status === 'deceased' ? '已死亡' :
                       detailCharacter.status === 'missing' ? '已失踪' :
                       detailCharacter.status === 'retired' ? '已退场' :
                       detailCharacter.status === 'destroyed' ? '已覆灭' : '活跃'}
                    </Tag>
                  </Col>
                  <Col span={12}>
                    <Typography.Text type="secondary">变更章节：</Typography.Text>
                    <Typography.Text style={{ marginLeft: 8 }}>第{detailCharacter.status_changed_chapter}章</Typography.Text>
                  </Col>
                </Row>
              </>
            )}

            {/* 组织特有字段 */}
            {detailCharacter.is_organization && (
              <>
                <Divider orientation="left">组织信息</Divider>
                {detailCharacter.motto && (
                  <div style={{ marginBottom: 16 }}>
                    <Typography.Text type="secondary">格言：</Typography.Text>
                    <Typography.Paragraph style={{ marginTop: 8, whiteSpace: 'pre-wrap' }}>
                      {detailCharacter.motto}
                    </Typography.Paragraph>
                  </div>
                )}
                {detailCharacter.organization_purpose && (
                  <div style={{ marginBottom: 16 }}>
                    <Typography.Text type="secondary">目的：</Typography.Text>
                    <Typography.Paragraph style={{ marginTop: 8, whiteSpace: 'pre-wrap' }}>
                      {detailCharacter.organization_purpose}
                    </Typography.Paragraph>
                  </div>
                )}
                {detailCharacter.organization_members && (
                  <div style={{ marginBottom: 16 }}>
                    <Typography.Text type="secondary">成员：</Typography.Text>
                    <Typography.Paragraph style={{ marginTop: 8, whiteSpace: 'pre-wrap' }}>
                      {typeof detailCharacter.organization_members === 'string'
                        ? detailCharacter.organization_members
                        : JSON.stringify(detailCharacter.organization_members)}
                    </Typography.Paragraph>
                  </div>
                )}
              </>
            )}

            {/* 背景故事 */}
            {detailCharacter.background && (
              <>
                <Divider orientation="left">背景故事</Divider>
                <Typography.Paragraph style={{ whiteSpace: 'pre-wrap' }}>
                  {detailCharacter.background}
                </Typography.Paragraph>
              </>
            )}

            {/* 职业信息（仅角色） */}
            {!detailCharacter.is_organization && detailCharacter.main_career_id && (
              <>
                <Divider orientation="left">职业信息</Divider>
                <Row gutter={[16, 16]}>
                  <Col span={12}>
                    <Typography.Text type="secondary">主职业：</Typography.Text>
                    <Typography.Text style={{ marginLeft: 8 }}>
                      {mainCareers.find(c => c.id === detailCharacter.main_career_id)?.name || '未知职业'}
                    </Typography.Text>
                  </Col>
                  <Col span={12}>
                    <Typography.Text type="secondary">阶段：</Typography.Text>
                    <Typography.Text style={{ marginLeft: 8 }}>
                      第{detailCharacter.main_career_stage || 1}阶段
                    </Typography.Text>
                  </Col>
                </Row>
                {detailCharacter.sub_careers && detailCharacter.sub_careers.length > 0 && (
                  <div style={{ marginTop: 16 }}>
                    <Typography.Text type="secondary">副职业：</Typography.Text>
                    <div style={{ marginTop: 8 }}>
                      {detailCharacter.sub_careers.map((sc, idx) => {
                        const career = subCareers.find(c => c.id === sc.career_id);
                        return (
                          <Tag key={idx} color="purple" style={{ marginBottom: 4 }}>
                            {career?.name || '未知职业'} - 第{sc.stage || 1}阶段
                          </Tag>
                        );
                      })}
                    </div>
                  </div>
                )}
              </>
            )}

            {/* 能力值（仅角色） */}
            {!detailCharacter.is_organization && detailCharacter.attributes && Object.keys(detailCharacter.attributes).length > 0 && attributeSchema && (
              <>
                <Divider orientation="left">能力值</Divider>
                <Row gutter={[16, 16]}>
                  {attributeSchema.display_order.map((key) => {
                    const value = detailCharacter.attributes?.[key];
                    const config = attributeSchema.attributes[key];
                    if (!value || !config) return null;

                    // 根据类型显示不同的值
                    let displayValue: string | React.ReactNode = '';
                    if (value.type === 'numeric') {
                      displayValue = `${value.value || 0}${config.unit || ''}`;
                    } else if (value.type === 'stage') {
                      displayValue = value.name || `第${value.value || 1}阶`;
                    } else if (value.type === 'combo_select') {
                      displayValue = (
                        <Space>
                          {value.elements && value.elements.length > 0 && (
                            <span>{value.elements.join(' + ')}</span>
                          )}
                          {value.quality && <Tag color="blue">{value.quality}</Tag>}
                          {value.growth_rate && value.growth_rate > 1 && (
                            <Tag color="gold">修炼速度 {value.growth_rate}x</Tag>
                          )}
                        </Space>
                      );
                    }

                    return (
                      <Col span={8} key={key}>
                        <Typography.Text type="secondary">{config.name}：</Typography.Text>
                        <span style={{ marginLeft: 8 }}>{displayValue}</span>
                      </Col>
                    );
                  })}
                </Row>
              </>
            )}
          </div>
        )}
      </Modal>

      {/* SSE进度显示 */}
      <SSELoadingOverlay
        loading={isGenerating}
        progress={progress}
        message={progressMessage}
      />
    </div>
  );
}