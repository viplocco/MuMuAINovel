import { App } from 'antd';
import { useEffect } from 'react';
import { setMessageInstance } from '../utils/antdStatic';

/**
 * 用于初始化 antd 静态方法的组件
 * 必须放在 App 组件内部
 */
export default function AntdStaticProvider() {
  const { message } = App.useApp();

  useEffect(() => {
    setMessageInstance(message);
  }, [message]);

  return null;
}