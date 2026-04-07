/**
 * 🌸 春天装饰组件
 *
 * 包含以下元素：
 * - 🌿 侧边垂柳装饰（随风轻摆）
 * - 🌸 飘落花瓣（樱花、桃花、柳叶）
 * - 🍃 顶部绿色装饰条
 * - 📜 春天诗句横幅
 * - 💨 风速变化效果（飘落物速度/角度变化）
 * - 🌺 点击交互（花朵绽放效果）
 *
 * 由 SeasonDecor 组件统一管理 visible 状态和控制按钮。
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import confetti from 'canvas-confetti';
import './SpringSeason.css';

interface SpringSeasonProps {
  visible: boolean;
}

// 春天诗句/祝福语
const SPRING_VERSES = [
  '春风十里',
  '花开富贵',
  '万物复苏',
  '春意盎然',
  '桃红柳绿',
  '春暖花开',
  '生机勃勃',
  '花团锦簇',
];

// 飘落物类型
type FallingType = 'willow-leaf' | 'sakura' | 'peach-petal';

interface FallingItem {
  id: number;
  type: FallingType;
  left: number;
  delay: number;
  duration: number;
  size: number;
  drift: number; // 水平漂移（模拟风吹）
}

// 风速状态
interface WindState {
  strength: number; // 0-1，风速强度
  direction: number; // -1 左风 / 1 右风
}

export default function SpringSeason({ visible }: SpringSeasonProps) {
  const [showBanner, setShowBanner] = useState(true);
  const [bannerText] = useState(() => {
    return SPRING_VERSES[Math.floor(Math.random() * SPRING_VERSES.length)];
  });

  const [fallingItems, setFallingItems] = useState<FallingItem[]>([]);
  const [wind, setWind] = useState<WindState>({ strength: 0.3, direction: 1 });
  const fallingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const windIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const idCounterRef = useRef(0);

  // 生成飘落物
  const createFallingItem = useCallback((currentWind: WindState): FallingItem => {
    idCounterRef.current += 1;

    // 根据类型概率分布
    const types: FallingType[] = ['willow-leaf', 'sakura', 'peach-petal'];
    const type = types[Math.floor(Math.random() * types.length)];

    // 根据风速调整飘落参数
    const baseDuration = type === 'willow-leaf' ? 8 : 6;
    const windAdjustedDuration = baseDuration * (1 + currentWind.strength * 0.5);

    return {
      id: idCounterRef.current,
      type,
      left: Math.random() * 100,
      delay: 0,
      duration: windAdjustedDuration + Math.random() * 4,
      size: type === 'willow-leaf' ? 16 + Math.random() * 12 : 14 + Math.random() * 10,
      drift: currentWind.direction * (currentWind.strength * 80 + Math.random() * 30),
    };
  }, []);

  // 风速变化
  const updateWind = useCallback(() => {
    // 风速在 0.2 到 0.8 之间变化，方向随机
    const newStrength = 0.2 + Math.random() * 0.6;
    const newDirection = Math.random() > 0.5 ? 1 : -1;
    setWind({ strength: newStrength, direction: newDirection });
  }, []);

  // 花朵绽放效果（点击交互）
  const launchBlossom = useCallback((x: number, y: number) => {
    // 粉色、绿色花瓣绽放
    const colors = ['#FFB7C5', '#FF69B4', '#90EE90', '#FFC0CB', '#98FB98', '#FFDAB9'];

    confetti({
      particleCount: 40 + Math.floor(Math.random() * 20),
      spread: 55,
      origin: { x, y },
      colors: colors,
      shapes: ['circle'],
      gravity: 0.6,
      scalar: 0.7 + Math.random() * 0.3,
      drift: (Math.random() - 0.5) * 0.8,
      ticks: 180,
      disableForReducedMotion: true,
    });
  }, []);

  // 管理飘落物和风速
  useEffect(() => {
    if (!visible) {
      setFallingItems([]);
      if (fallingIntervalRef.current) {
        clearInterval(fallingIntervalRef.current);
        fallingIntervalRef.current = null;
      }
      if (windIntervalRef.current) {
        clearInterval(windIntervalRef.current);
        windIntervalRef.current = null;
      }
      return;
    }

    // 初始生成一批飘落物
    const initialItems: FallingItem[] = [];
    for (let i = 0; i < 15; i++) {
      const item = createFallingItem(wind);
      item.delay = Math.random() * 6;
      initialItems.push(item);
    }
    setFallingItems(initialItems);

    // 定期添加新飘落物（每2秒）
    fallingIntervalRef.current = setInterval(() => {
      setFallingItems(prev => {
        const kept = prev.slice(-20);
        return [...kept, createFallingItem(wind)];
      });
    }, 2000);

    // 定期更新风速（每5-10秒）
    const scheduleWindChange = () => {
      const delay = 5000 + Math.random() * 5000;
      windIntervalRef.current = setInterval(() => {
        updateWind();
      }, delay);
    };
    scheduleWindChange();

    // 初始欢迎花朵绽放
    setTimeout(() => {
      launchBlossom(0.3, 0.3);
      setTimeout(() => launchBlossom(0.7, 0.25), 300);
    }, 800);

    return () => {
      if (fallingIntervalRef.current) {
        clearInterval(fallingIntervalRef.current);
        fallingIntervalRef.current = null;
      }
      if (windIntervalRef.current) {
        clearInterval(windIntervalRef.current);
        windIntervalRef.current = null;
      }
    };
  }, [visible, wind, createFallingItem, updateWind, launchBlossom]);

  // 横幅自动隐藏
  useEffect(() => {
    if (visible && showBanner) {
      const timer = setTimeout(() => setShowBanner(false), 8000);
      return () => clearTimeout(timer);
    }
  }, [visible, showBanner]);

  // 当 visible 变为 true 时重置横幅
  useEffect(() => {
    if (visible) {
      setShowBanner(true);
    }
  }, [visible]);

  // 鼠标点击页面时发射花瓣
  const handlePageClick = useCallback((e: MouseEvent) => {
    if (!visible) return;
    const target = e.target as HTMLElement;
    if (target.closest('.season-decor-btn') || target.closest('.ss-banner') || target.closest('.ss-willow')) return;

    const x = e.clientX / window.innerWidth;
    const y = e.clientY / window.innerHeight;

    confetti({
      particleCount: 12 + Math.floor(Math.random() * 10),
      spread: 35,
      origin: { x, y },
      colors: ['#FFB7C5', '#FF69B4', '#90EE90', '#FFC0CB'],
      shapes: ['circle'],
      gravity: 0.8,
      scalar: 0.5 + Math.random() * 0.3,
      ticks: 100,
      disableForReducedMotion: true,
    });
  }, [visible]);

  // 绑定全局鼠标点击事件
  useEffect(() => {
    if (!visible) return;

    window.addEventListener('click', handlePageClick);

    return () => {
      window.removeEventListener('click', handlePageClick);
    };
  }, [visible, handlePageClick]);

  // 点击垂柳：花朵绽放效果
  const handleWillowClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();

    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const x = (rect.left + rect.width / 2) / window.innerWidth;
    const y = (rect.top + rect.height / 2) / window.innerHeight;

    // 多次绽放
    launchBlossom(x, y);
    setTimeout(() => launchBlossom(x + 0.05, y - 0.02), 150);
    setTimeout(() => launchBlossom(x - 0.05, y + 0.02), 300);
  }, [launchBlossom]);

  // 渲染飘落物
  const renderFallingItem = (item: FallingItem) => {
    switch (item.type) {
      case 'willow-leaf':
        return (
          <svg
            viewBox="0 0 20 40"
            className="ss-willow-leaf-svg"
            style={{
              width: item.size,
              height: item.size * 2,
            }}
          >
            <path
              d="M10 0 Q 15 10 12 20 Q 10 30 10 40 Q 8 30 8 20 Q 5 10 10 0"
              fill="url(#willowGradient)"
            />
            <defs>
              <linearGradient id="willowGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#90EE90" />
                <stop offset="100%" stopColor="#228B22" />
              </linearGradient>
            </defs>
          </svg>
        );
      case 'sakura':
        return <span className="ss-sakura-emoji">🌸</span>;
      case 'peach-petal':
        return (
          <svg
            viewBox="0 0 20 20"
            className="ss-peach-petal-svg"
            style={{
              width: item.size,
              height: item.size,
            }}
          >
            <ellipse
              cx="10"
              cy="10"
              rx="8"
              ry="10"
              fill="url(#peachGradient)"
              opacity="0.85"
            />
            <defs>
              <linearGradient id="peachGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#FFB7C5" />
                <stop offset="100%" stopColor="#FF69B4" />
              </linearGradient>
            </defs>
          </svg>
        );
    }
  };

  if (!visible) return null;

  return (
    <>
      {/* 春天诗句横幅 */}
      {showBanner && (
        <div className="ss-banner" onClick={() => setShowBanner(false)}>
          <div className="ss-banner-content">
            <span className="ss-banner-icon">🌸</span>
            <span className="ss-banner-text">
              {bannerText}
            </span>
            <span className="ss-banner-icon">🌸</span>
          </div>
        </div>
      )}

      {/* 垂柳 - 左侧 */}
      <div className="ss-willow-group ss-willow-left" onClick={handleWillowClick}>
        {/* 柳枝1 - 向左弯曲 */}
        <svg className="ss-willow-tree ss-willow-1" viewBox="0 0 80 200">
          <g className="ss-willow-branch-group">
            {/* 枝干：从顶部向左下弯曲 */}
            <path className="ss-willow-branch-path" d="M40 0 Q32 50 24 100 Q16 150 8 190" />
            {/* 柳叶：起始点精确贴合枝干 */}
            <path className="ss-willow-leaf ss-leaf-left" d="M32 50 Q10 55 -8 65" style={{ animationDelay: '0.1s' }} />
            <path className="ss-willow-leaf ss-leaf-left" d="M28 70 Q8 75 -12 85" style={{ animationDelay: '0.2s' }} />
            <path className="ss-willow-leaf ss-leaf-left" d="M24 90 Q4 95 -18 105" style={{ animationDelay: '0.3s' }} />
            <path className="ss-willow-leaf ss-leaf-left" d="M20 110 Q0 115 -20 125" style={{ animationDelay: '0.4s' }} />
            <path className="ss-willow-leaf ss-leaf-left" d="M16 130 Q-4 135 -22 145" style={{ animationDelay: '0.5s' }} />
            <path className="ss-willow-leaf ss-leaf-left" d="M12 150 Q-6 155 -24 165" style={{ animationDelay: '0.6s' }} />
            <path className="ss-willow-leaf ss-leaf-left" d="M10 165 Q-8 170 -26 180" style={{ animationDelay: '0.7s' }} />
            {/* 右侧柳叶 */}
            <path className="ss-willow-leaf ss-leaf-right" d="M32 50 Q55 55 68 65" style={{ animationDelay: '0.15s' }} />
            <path className="ss-willow-leaf ss-leaf-right" d="M28 70 Q52 75 66 88" style={{ animationDelay: '0.25s' }} />
            <path className="ss-willow-leaf ss-leaf-right" d="M24 90 Q48 95 64 108" style={{ animationDelay: '0.35s' }} />
            <path className="ss-willow-leaf ss-leaf-right" d="M20 110 Q44 115 60 128" style={{ animationDelay: '0.45s' }} />
            <path className="ss-willow-leaf ss-leaf-right" d="M16 130 Q38 135 54 148" style={{ animationDelay: '0.55s' }} />
          </g>
        </svg>
        {/* 柳枝2 - 较短 */}
        <svg className="ss-willow-tree ss-willow-2" viewBox="0 0 70 160">
          <g className="ss-willow-branch-group">
            <path className="ss-willow-branch-path" d="M35 0 Q42 40 50 80 Q58 120 62 150" strokeWidth="1.5" />
            {/* 柳叶 */}
            <path className="ss-willow-leaf ss-leaf-right" d="M42 40 Q65 45 78 55" style={{ animationDelay: '0.2s' }} />
            <path className="ss-willow-leaf ss-leaf-right" d="M46 60 Q70 65 82 75" style={{ animationDelay: '0.3s' }} />
            <path className="ss-willow-leaf ss-leaf-right" d="M50 80 Q74 85 86 95" style={{ animationDelay: '0.4s' }} />
            <path className="ss-willow-leaf ss-leaf-right" d="M54 100 Q78 105 88 115" style={{ animationDelay: '0.5s' }} />
            <path className="ss-willow-leaf ss-leaf-right" d="M58 120 Q80 125 90 135" style={{ animationDelay: '0.6s' }} />
            {/* 左侧柳叶 */}
            <path className="ss-willow-leaf ss-leaf-left" d="M42 40 Q22 45 5 55" style={{ animationDelay: '0.25s' }} />
            <path className="ss-willow-leaf ss-leaf-left" d="M46 60 Q26 65 8 78" style={{ animationDelay: '0.35s' }} />
            <path className="ss-willow-leaf ss-leaf-left" d="M50 80 Q30 85 12 98" style={{ animationDelay: '0.45s' }} />
            <path className="ss-willow-leaf ss-leaf-left" d="M54 100 Q34 105 16 118" style={{ animationDelay: '0.55s' }} />
          </g>
        </svg>
      </div>

      {/* 垂柳 - 右侧 */}
      <div className="ss-willow-group ss-willow-right" onClick={handleWillowClick}>
        {/* 柳枝3 - 向右弯曲 */}
        <svg className="ss-willow-tree ss-willow-3" viewBox="0 0 80 200">
          <g className="ss-willow-branch-group">
            <path className="ss-willow-branch-path" d="M40 0 Q48 50 56 100 Q64 150 72 190" />
            {/* 柳叶 */}
            <path className="ss-willow-leaf ss-leaf-right" d="M48 50 Q72 55 88 65" style={{ animationDelay: '0.15s' }} />
            <path className="ss-willow-leaf ss-leaf-right" d="M52 70 Q76 75 92 85" style={{ animationDelay: '0.25s' }} />
            <path className="ss-willow-leaf ss-leaf-right" d="M56 90 Q80 95 96 105" style={{ animationDelay: '0.35s' }} />
            <path className="ss-willow-leaf ss-leaf-right" d="M60 110 Q84 115 100 125" style={{ animationDelay: '0.45s' }} />
            <path className="ss-willow-leaf ss-leaf-right" d="M64 130 Q88 135 104 145" style={{ animationDelay: '0.55s' }} />
            <path className="ss-willow-leaf ss-leaf-right" d="M68 150 Q90 155 106 165" style={{ animationDelay: '0.65s' }} />
            <path className="ss-willow-leaf ss-leaf-right" d="M70 165 Q92 170 108 180" style={{ animationDelay: '0.75s' }} />
            {/* 左侧柳叶 */}
            <path className="ss-willow-leaf ss-leaf-left" d="M48 50 Q25 55 8 65" style={{ animationDelay: '0.1s' }} />
            <path className="ss-willow-leaf ss-leaf-left" d="M52 70 Q28 75 10 88" style={{ animationDelay: '0.2s' }} />
            <path className="ss-willow-leaf ss-leaf-left" d="M56 90 Q32 95 14 108" style={{ animationDelay: '0.3s' }} />
            <path className="ss-willow-leaf ss-leaf-left" d="M60 110 Q36 115 18 128" style={{ animationDelay: '0.4s' }} />
            <path className="ss-willow-leaf ss-leaf-left" d="M64 130 Q40 135 22 148" style={{ animationDelay: '0.5s' }} />
          </g>
        </svg>
        {/* 柳枝4 - 较短 */}
        <svg className="ss-willow-tree ss-willow-4" viewBox="0 0 70 160">
          <g className="ss-willow-branch-group">
            <path className="ss-willow-branch-path" d="M35 0 Q28 40 20 80 Q12 120 8 150" strokeWidth="1.5" />
            {/* 柳叶 */}
            <path className="ss-willow-leaf ss-leaf-left" d="M28 40 Q8 45 -6 55" style={{ animationDelay: '0.2s' }} />
            <path className="ss-willow-leaf ss-leaf-left" d="M24 60 Q4 65 -10 78" style={{ animationDelay: '0.3s' }} />
            <path className="ss-willow-leaf ss-leaf-left" d="M20 80 Q0 85 -14 98" style={{ animationDelay: '0.4s' }} />
            <path className="ss-willow-leaf ss-leaf-left" d="M16 100 Q-4 105 -18 118" style={{ animationDelay: '0.5s' }} />
            <path className="ss-willow-leaf ss-leaf-left" d="M12 120 Q-6 125 -20 135" style={{ animationDelay: '0.6s' }} />
            {/* 右侧柳叶 */}
            <path className="ss-willow-leaf ss-leaf-right" d="M28 40 Q50 45 62 55" style={{ animationDelay: '0.25s' }} />
            <path className="ss-willow-leaf ss-leaf-right" d="M24 60 Q46 65 58 78" style={{ animationDelay: '0.35s' }} />
            <path className="ss-willow-leaf ss-leaf-right" d="M20 80 Q42 85 54 98" style={{ animationDelay: '0.45s' }} />
            <path className="ss-willow-leaf ss-leaf-right" d="M16 100 Q38 105 50 118" style={{ animationDelay: '0.55s' }} />
          </g>
        </svg>
      </div>

      {/* 飘落装饰物 */}
      <div className="ss-falling-container">
        {fallingItems.map(item => (
          <span
            key={item.id}
            className="ss-falling-item"
            style={{
              left: `${item.left}%`,
              animationDelay: `${item.delay}s`,
              animationDuration: `${item.duration}s`,
              fontSize: `${item.size}px`,
              // 根据风速调整漂移方向
              '--drift-x': `${item.drift}px`,
            } as React.CSSProperties}
          >
            {renderFallingItem(item)}
          </span>
        ))}
      </div>

      {/* 顶部绿色装饰条 */}
      <div className="ss-top-border" />

      {/* 风吹效果指示器（视觉提示，可选） */}
      {wind.strength > 0.5 && (
        <div className="ss-wind-indicator" style={{ transform: `translateX(${wind.direction * 30}px)` }}>
          <span className="ss-wind-arrow">🍃</span>
        </div>
      )}
    </>
  );
}