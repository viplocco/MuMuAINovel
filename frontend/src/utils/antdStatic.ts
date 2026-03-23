import type { MessageInstance } from 'antd/es/message/interface';

let messageInstance: MessageInstance | null = null;

export const setMessageInstance = (instance: MessageInstance) => {
  messageInstance = instance;
};

export const getMessageInstance = (): MessageInstance => {
  if (!messageInstance) {
    console.warn('Message instance not initialized. Make sure App component is mounted.');
    // Return a fallback that uses console
    return {
      success: (content) => { console.log('[Success]', content); return content; },
      error: (content) => { console.error('[Error]', content); return content; },
      info: (content) => { console.info('[Info]', content); return content; },
      warning: (content) => { console.warn('[Warning]', content); return content; },
      warn: (content) => { console.warn('[Warn]', content); return content; },
      loading: (content) => { console.log('[Loading]', content); return content; },
      destroy: () => {},
    } as unknown as MessageInstance;
  }
  return messageInstance;
};