/**
 * 🌸 季节装饰入口组件
 *
 * 根据日期自动选择并渲染对应季节的装饰组件：
 * - 春节 (SpringFestival): 1月15日 ~ 3月5日
 * - 春天 (SpringSeason): 3月1日 ~ 5月31日
 * - 夏天 (SummerSeason): 6月1日 ~ 8月31日 (预留)
 * - 秋天 (AutumnSeason): 9月1日 ~ 11月30日 (预留)
 * - 冬天 (WinterSeason): 12月1日 ~ 2月28日 (预留，非春节)
 *
 * 提供统一的状态管理和可拖动的控制按钮。
 * 支持管理员全局配置（装饰类型、强制启用）。
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import SpringFestival from './SpringFestival';
import SpringSeason from './SpringSeason';
import { decorationApi } from '../services/api';
// 预留其他季节装饰导入
// import SummerSeason from './SummerSeason';
// import AutumnSeason from './AutumnSeason';
// import WinterSeason from './WinterSeason';

// 季节类型定义
export type SeasonType = 'spring-festival' | 'spring' | 'summer' | 'autumn' | 'winter' | 'none';

// 季节配置
export const SEASON_CONFIG: Record<SeasonType, {
  name: string;
  iconOn: string;
  iconOff: string;
  storageKey: string;
  component: React.ComponentType<{ visible: boolean }> | null;
}> = {
  'spring-festival': {
    name: '春节',
    iconOn: '🧨',
    iconOff: '🏮',
    storageKey: 'spring-festival-visible',
    component: SpringFestival,
  },
  'spring': {
    name: '春天',
    iconOn: '🌸',
    iconOff: '🌿',
    storageKey: 'spring-visible',
    component: SpringSeason,
  },
  'summer': {
    name: '夏天',
    iconOn: '☀️',
    iconOff: '🌻',
    storageKey: 'summer-visible',
    component: null, // 预留
  },
  'autumn': {
    name: '秋天',
    iconOn: '🍂',
    iconOff: '🍁',
    storageKey: 'autumn-visible',
    component: null, // 预留
  },
  'winter': {
    name: '冬天',
    iconOn: '❄️',
    iconOff: '⛄',
    storageKey: 'winter-visible',
    component: null, // 预留
  },
  'none': {
    name: '无',
    iconOn: '✨',
    iconOff: '✨',
    storageKey: 'none-visible',
    component: null,
  },
};

/**
 * 根据日期判断当前季节
 * 注意：春节优先级最高（会覆盖冬天）
 */
export function getCurrentSeason(): SeasonType {
  const now = new Date();
  const month = now.getMonth() + 1; // 1-12
  const day = now.getDate();

  // 春节：1月15日 ~ 3月5日（优先级最高）
  if ((month === 1 && day >= 15) || month === 2 || (month === 3 && day <= 5)) {
    return 'spring-festival';
  }

  // 春天：3月1日 ~ 5月31日
  if (month >= 3 && month <= 5) {
    return 'spring';
  }

  // 夏天：6月1日 ~ 8月31日
  if (month >= 6 && month <= 8) {
    return 'summer';
  }

  // 秋天：9月1日 ~ 11月30日
  if (month >= 9 && month <= 11) {
    return 'autumn';
  }

  // 冬天：12月1日 ~ 2月28日（非春节部分）
  return 'winter';
}

// 按钮位置类型
interface BtnPosition {
  x: number;
  y: number;
  side: 'left' | 'right';
}

// 默认按钮位置：右侧贴边居中
function getDefaultBtnPosition(): BtnPosition {
  return {
    x: window.innerWidth - 22,
    y: window.innerHeight / 2,
    side: 'right',
  };
}

// 从 localStorage 读取保存的位置
function loadBtnPosition(): BtnPosition {
  try {
    const saved = localStorage.getItem('season-decor-btn-position');
    if (saved) {
      const pos = JSON.parse(saved) as BtnPosition;
      pos.y = Math.max(22, Math.min(window.innerHeight - 22, pos.y));
      pos.x = pos.side === 'left' ? 22 : window.innerWidth - 22;
      return pos;
    }
  } catch { /* ignore */ }
  return getDefaultBtnPosition();
}

export default function SeasonDecor() {
  // 当前季节
  const [currentSeason, setCurrentSeason] = useState<SeasonType>(getCurrentSeason);

  // 全局装饰配置（管理员设置）
  const [globalConfig, setGlobalConfig] = useState<{
    decoration_type: string;
    force_enabled: boolean;
  } | null>(null);

  // 装饰可见状态
  const [visible, setVisible] = useState(() => {
    const saved = localStorage.getItem('season-decor-visible');
    if (saved !== null) return saved === 'true';
    return true; // 默认显示
  });

  // 按钮拖动状态
  const [btnPos, setBtnPos] = useState<BtnPosition>(loadBtnPosition);
  const [isDragging, setIsDragging] = useState(false);
  const dragStartRef = useRef<{ startX: number; startY: number; startBtnX: number; startBtnY: number } | null>(null);
  const hasDraggedRef = useRef(false); // 用 ref 同步记录拖动状态

  // 每分钟检查季节变化
  useEffect(() => {
    const checkSeason = () => {
      const newSeason = getCurrentSeason();
      if (newSeason !== currentSeason) {
        setCurrentSeason(newSeason);
      }
    };

    // 初始检查
    checkSeason();

    // 定时检查（每分钟）
    const interval = setInterval(checkSeason, 60000);
    return () => clearInterval(interval);
  }, [currentSeason]);

  // 获取全局装饰配置（管理员设置）
  useEffect(() => {
    const loadGlobalConfig = async () => {
      try {
        const config = await decorationApi.getPublicConfig();
        setGlobalConfig(config);
      } catch {
        // 静默失败，使用现有本地设置（不影响现有功能）
        setGlobalConfig(null);
      }
    };

    loadGlobalConfig();

    // 定时刷新配置（每5分钟）
    const interval = setInterval(loadGlobalConfig, 300000);
    return () => clearInterval(interval);
  }, []);

  // 计算实际装饰类型
  const getActualDecorationType = useCallback((): SeasonType => {
    // 无全局配置时使用现有逻辑
    if (!globalConfig) return currentSeason;

    // 强制启用且不是 auto 时，使用全局设置
    if (globalConfig.force_enabled && globalConfig.decoration_type !== 'auto') {
      return globalConfig.decoration_type as SeasonType;
    }

    // auto 模式时根据日期判断
    if (globalConfig.decoration_type === 'auto') return getCurrentSeason();

    // 否则使用全局指定的类型
    return globalConfig.decoration_type as SeasonType;
  }, [globalConfig, currentSeason]);

  // 计算实际可见状态
  const getActualVisibility = useCallback(() => {
    // 强制启用时必须显示
    if (globalConfig?.force_enabled) return true;

    // 否则使用现有本地设置
    return visible;
  }, [globalConfig, visible]);

  // 自动贴边
  const snapToEdge = useCallback((x: number, y: number): BtnPosition => {
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const btnRadius = 22;
    const clampedY = Math.max(btnRadius, Math.min(vh - btnRadius, y));

    const side: 'left' | 'right' = x < vw / 2 ? 'left' : 'right';
    const snapX = side === 'left' ? btnRadius : vw - btnRadius;

    return { x: snapX, y: clampedY, side };
  }, []);

  // 点击切换（强制启用时不执行）
  const toggleVisible = useCallback(() => {
    // 强制启用时不允许切换
    if (globalConfig?.force_enabled) return;

    const next = !visible;
    setVisible(next);
    localStorage.setItem('season-decor-visible', String(next));
  }, [visible, globalConfig]);

  // 拖动开始
  const handleDragStart = useCallback((clientX: number, clientY: number) => {
    dragStartRef.current = {
      startX: clientX,
      startY: clientY,
      startBtnX: btnPos.x,
      startBtnY: btnPos.y,
    };
    setIsDragging(true);
    hasDraggedRef.current = false; // 重置拖动标记
  }, [btnPos]);

  // 使用原生事件监听器处理 touch 事件（passive: false）
  const btnRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const btn = btnRef.current;
    if (!btn) return;

    const handleMouseDown = (e: MouseEvent) => {
      e.preventDefault();
      handleDragStart(e.clientX, e.clientY);
    };

    const handleTouchStart = (e: TouchEvent) => {
      e.preventDefault(); // 现在可以调用 preventDefault
      if (e.touches.length > 0) {
        handleDragStart(e.touches[0].clientX, e.touches[0].clientY);
      }
    };

    btn.addEventListener('mousedown', handleMouseDown);
    btn.addEventListener('touchstart', handleTouchStart, { passive: false });

    return () => {
      btn.removeEventListener('mousedown', handleMouseDown);
      btn.removeEventListener('touchstart', handleTouchStart);
    };
  }, [handleDragStart]);

  // 拖动过程
  useEffect(() => {
    if (!isDragging) return;

    const handleMove = (e: MouseEvent | TouchEvent) => {
      if (!dragStartRef.current) return;

      const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX;
      const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY;

      const dx = clientX - dragStartRef.current.startX;
      const dy = clientY - dragStartRef.current.startY;

      if (Math.abs(dx) > 5 || Math.abs(dy) > 5) {
        hasDraggedRef.current = true; // 同步记录拖动状态
      }

      const newX = dragStartRef.current.startBtnX + dx;
      const newY = dragStartRef.current.startBtnY + dy;

      setBtnPos({
        x: newX,
        y: Math.max(22, Math.min(window.innerHeight - 22, newY)),
        side: newX < window.innerWidth / 2 ? 'left' : 'right',
      });
    };

    const handleEnd = () => {
      // 判断是否是点击（没有拖动）
      const wasClick = !hasDraggedRef.current;

      setIsDragging(false);
      dragStartRef.current = null;

      setBtnPos(prev => {
        const snapped = snapToEdge(prev.x, prev.y);
        localStorage.setItem('season-decor-btn-position', JSON.stringify(snapped));
        return snapped;
      });

      // 如果是点击，切换显示状态
      if (wasClick) {
        toggleVisible();
      }
    };

    window.addEventListener('mousemove', handleMove);
    window.addEventListener('mouseup', handleEnd);
    window.addEventListener('touchmove', handleMove, { passive: false });
    window.addEventListener('touchend', handleEnd);

    return () => {
      window.removeEventListener('mousemove', handleMove);
      window.removeEventListener('mouseup', handleEnd);
      window.removeEventListener('touchmove', handleMove);
      window.removeEventListener('touchend', handleEnd);
    };
  }, [isDragging, snapToEdge, toggleVisible]);

  // 窗口大小变化时重新贴边
  useEffect(() => {
    const handleResize = () => {
      setBtnPos(prev => snapToEdge(prev.side === 'left' ? 22 : window.innerWidth - 22, prev.y));
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [snapToEdge]);

  // 计算实际装饰类型和可见状态
  const actualSeason = getActualDecorationType();
  const actualVisible = getActualVisibility();
  const actualConfig = SEASON_CONFIG[actualSeason];

  // 是否强制启用（用于按钮禁用状态）
  const isForceEnabled = globalConfig?.force_enabled ?? false;

  // 按钮样式
  const btnStyle: React.CSSProperties = {
    position: 'fixed',
    left: btnPos.x - 22,
    top: btnPos.y - 22,
    transition: isDragging ? 'none' : 'left 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), top 0.1s ease',
    cursor: isForceEnabled ? 'not-allowed' : (isDragging ? 'grabbing' : 'grab'),
    touchAction: 'none',
    userSelect: 'none',
    zIndex: 10000,
    width: 44,
    height: 44,
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 22,
    border: 'none',
    outline: 'none',
    padding: 0,
    opacity: isForceEnabled ? 0.6 : 1, // 强制启用时显示禁用样式
    background: actualSeason === 'spring-festival'
      ? 'linear-gradient(135deg, #FF0000 0%, #CC0000 100%)'
      : actualSeason === 'spring'
        ? 'linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%)'
        : actualSeason === 'summer'
          ? 'linear-gradient(135deg, #FF9800 0%, #F57C00 100%)'
          : actualSeason === 'autumn'
            ? 'linear-gradient(135deg, #FF5722 0%, #E64A19 100%)'
            : actualSeason === 'winter'
              ? 'linear-gradient(135deg, #64B5F6 0%, #1976D2 100%)'
              : 'linear-gradient(135deg, #9E9E9E 0%, #616161 100%)',
    boxShadow: actualSeason === 'spring-festival'
      ? '0 4px 16px rgba(255, 0, 0, 0.4), 0 0 20px rgba(255, 215, 0, 0.3)'
      : actualSeason === 'spring'
        ? '0 4px 16px rgba(76, 175, 80, 0.4), 0 0 20px rgba(255, 182, 193, 0.3)'
        : '0 4px 16px rgba(0, 0, 0, 0.3)',
  };

  // 如果当前季节没有装饰组件实现，不显示按钮和装饰
  if (!actualConfig.component) {
    return null;
  }

  return (
    <>
      {/* 控制按钮 */}
      <button
        ref={btnRef}
        className={`season-decor-btn ${isDragging ? 'season-decor-btn-dragging' : ''}`}
        style={btnStyle}
        title={isForceEnabled
          ? `${actualConfig.name}装饰已由管理员强制启用`
          : (actualVisible ? `关闭${actualConfig.name}装饰` : `开启${actualConfig.name}装饰`)
        }
      >
        {actualVisible ? actualConfig.iconOn : actualConfig.iconOff}
      </button>

      {/* 渲染对应季节的装饰组件 */}
      {actualConfig.component && <actualConfig.component visible={actualVisible} />}
    </>
  );
}