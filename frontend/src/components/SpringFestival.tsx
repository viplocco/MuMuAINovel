/**
 * 🧧 春节喜庆装饰组件
 *
 * 包含以下元素：
 * - 🏮 悬挂灯笼（左右各两个）
 * - 🎆 烟花效果（canvas-confetti）
 * - 🌸 飘落装饰物（梅花、福字等）
 * - 🧧 新春祝福横幅
 *
 * 由 SeasonDecor 组件统一管理 visible 状态和控制按钮。
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import confetti from 'canvas-confetti';
import './SpringFestival.css';

interface SpringFestivalProps {
  visible: boolean;
}

// 飘落装饰物配置
const FALLING_ITEMS = ['🌸', '✨', '🧧', '💮', '🎐', '❄️', '🏮'];
const SPRING_COUPLETS = [
  '马年大吉',
  '恭喜发财',
  '红包拿来',
  '万事如意',
  '阖家欢乐',
  '新春快乐',
  '福星高照',
];

interface FallingItem {
  id: number;
  emoji: string;
  left: number;
  delay: number;
  duration: number;
  size: number;
}

export default function SpringFestival({ visible }: SpringFestivalProps) {
  const [showBanner, setShowBanner] = useState(true);
  const [bannerText] = useState(() => {
    return SPRING_COUPLETS[Math.floor(Math.random() * SPRING_COUPLETS.length)];
  });

  // 灯笼文字：从 SPRING_COUPLETS 中取四字词，定时轮换
  const [lanternChars, setLanternChars] = useState<string[]>(() => {
    const text = SPRING_COUPLETS[Math.floor(Math.random() * SPRING_COUPLETS.length)];
    return text.split('');
  });
  const [lanternFading, setLanternFading] = useState(false);
  const lanternIndexRef = useRef(Math.floor(Math.random() * SPRING_COUPLETS.length));

  const [fallingItems, setFallingItems] = useState<FallingItem[]>([]);
  const fireworksIntervalRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const fallingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const lanternIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const idCounterRef = useRef(0);

  // 生成飘落物
  const createFallingItem = useCallback((): FallingItem => {
    idCounterRef.current += 1;
    return {
      id: idCounterRef.current,
      emoji: FALLING_ITEMS[Math.floor(Math.random() * FALLING_ITEMS.length)],
      left: Math.random() * 100,
      delay: 0,
      duration: 6 + Math.random() * 8,
      size: 12 + Math.random() * 16,
    };
  }, []);

  // 烟花效果
  const launchFirework = useCallback(() => {
    if (!visible) return;

    const colors = ['#FF0000', '#FFD700', '#FF6347', '#FF4500', '#FFA500', '#DC143C'];

    confetti({
      particleCount: 30 + Math.floor(Math.random() * 30),
      spread: 60 + Math.random() * 40,
      origin: {
        x: 0.1 + Math.random() * 0.8,
        y: 0.2 + Math.random() * 0.4,
      },
      colors: colors.slice(0, 3 + Math.floor(Math.random() * 3)),
      shapes: ['circle', 'square'],
      gravity: 0.8,
      scalar: 0.8 + Math.random() * 0.4,
      drift: (Math.random() - 0.5) * 0.5,
      ticks: 200,
      disableForReducedMotion: true,
    });
  }, [visible]);

  // 初始烟花欢迎效果
  const launchWelcomeFireworks = useCallback(() => {
    const positions = [
      { x: 0.2, y: 0.3 },
      { x: 0.5, y: 0.2 },
      { x: 0.8, y: 0.3 },
    ];

    positions.forEach((pos, i) => {
      setTimeout(() => {
        confetti({
          particleCount: 60,
          spread: 80,
          origin: pos,
          colors: ['#FF0000', '#FFD700', '#FF6347', '#FF4500', '#DC143C', '#FFA500'],
          shapes: ['circle', 'square'],
          gravity: 0.7,
          scalar: 1,
          ticks: 250,
          disableForReducedMotion: true,
        });
      }, i * 400);
    });
  }, []);

  // 管理飘落物和烟花
  useEffect(() => {
    if (!visible) {
      setFallingItems([]);
      if (fireworksIntervalRef.current) {
        clearTimeout(fireworksIntervalRef.current);
        fireworksIntervalRef.current = null;
      }
      if (fallingIntervalRef.current) {
        clearInterval(fallingIntervalRef.current);
        fallingIntervalRef.current = null;
      }
      if (lanternIntervalRef.current) {
        clearInterval(lanternIntervalRef.current);
        lanternIntervalRef.current = null;
      }
      return;
    }

    // 初始生成一批飘落物
    const initialItems: FallingItem[] = [];
    for (let i = 0; i < 12; i++) {
      const item = createFallingItem();
      item.delay = Math.random() * 8;
      initialItems.push(item);
    }
    setFallingItems(initialItems);

    // 初始欢迎烟花
    setTimeout(launchWelcomeFireworks, 1000);

    // 定期添加新飘落物
    fallingIntervalRef.current = setInterval(() => {
      setFallingItems(prev => {
        const kept = prev.slice(-15);
        return [...kept, createFallingItem()];
      });
    }, 3000);

    // 定期发射烟花（每20-40秒一次）
    const scheduleFirework = () => {
      const delay = 20000 + Math.random() * 20000;
      fireworksIntervalRef.current = setTimeout(() => {
        launchFirework();
        scheduleFirework();
      }, delay);
    };
    scheduleFirework();

    // 灯笼文字定时轮换（每10秒）
    lanternIntervalRef.current = setInterval(() => {
      setLanternFading(true);
      setTimeout(() => {
        lanternIndexRef.current = (lanternIndexRef.current + 1) % SPRING_COUPLETS.length;
        const newText = SPRING_COUPLETS[lanternIndexRef.current];
        setLanternChars(newText.split(''));
        setLanternFading(false);
      }, 500);
    }, 10000);

    return () => {
      if (fireworksIntervalRef.current) {
        clearTimeout(fireworksIntervalRef.current);
        fireworksIntervalRef.current = null;
      }
      if (fallingIntervalRef.current) {
        clearInterval(fallingIntervalRef.current);
        fallingIntervalRef.current = null;
      }
      if (lanternIntervalRef.current) {
        clearInterval(lanternIntervalRef.current);
        lanternIntervalRef.current = null;
      }
    };
  }, [visible, createFallingItem, launchFirework, launchWelcomeFireworks]);

  // 横幅自动隐藏
  useEffect(() => {
    if (visible && showBanner) {
      const timer = setTimeout(() => setShowBanner(false), 8000);
      return () => clearTimeout(timer);
    }
  }, [visible, showBanner]);

  // 鼠标点击页面时发射小烟花
  const handlePageClick = useCallback((e: MouseEvent) => {
    if (!visible) return;
    const target = e.target as HTMLElement;
    if (target.closest('.season-decor-btn') || target.closest('.sf-banner')) return;

    const x = e.clientX / window.innerWidth;
    const y = e.clientY / window.innerHeight;

    confetti({
      particleCount: 15 + Math.floor(Math.random() * 15),
      spread: 40 + Math.random() * 30,
      origin: { x, y },
      colors: ['#FF0000', '#FFD700', '#FF6347', '#FF4500'],
      shapes: ['circle'],
      gravity: 1.2,
      scalar: 0.6 + Math.random() * 0.3,
      ticks: 120,
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

  // 点击灯笼：爆发烟花 + 立即切换祝福语
  const handleLanternClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();

    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const x = (rect.left + rect.width / 2) / window.innerWidth;
    const y = (rect.top + rect.height / 2) / window.innerHeight;

    confetti({
      particleCount: 50,
      spread: 70,
      origin: { x, y },
      colors: ['#FF0000', '#FFD700', '#FF6347', '#FF4500', '#DC143C'],
      shapes: ['circle', 'square'],
      gravity: 0.8,
      scalar: 0.9,
      ticks: 200,
      disableForReducedMotion: true,
    });

    setLanternFading(true);
    setTimeout(() => {
      lanternIndexRef.current = (lanternIndexRef.current + 1) % SPRING_COUPLETS.length;
      const newText = SPRING_COUPLETS[lanternIndexRef.current];
      setLanternChars(newText.split(''));
      setLanternFading(false);
    }, 400);
  }, []);

  // 当 visible 变为 true 时重置横幅
  useEffect(() => {
    if (visible) {
      setShowBanner(true);
    }
  }, [visible]);

  if (!visible) return null;

  return (
    <>
      {/* 新春祝福横幅 */}
      {showBanner && (
        <div className="sf-banner" onClick={() => setShowBanner(false)}>
          <div className="sf-banner-content">
            <span className="sf-banner-icon">🧧</span>
            <span className="sf-banner-text">
              {bannerText}
            </span>
            <span className="sf-banner-icon">🧧</span>
          </div>
        </div>
      )}

      {/* 灯笼 - 左侧（往中间靠拢），可点击 */}
      <div className="sf-lantern-group sf-lantern-left sf-lantern-clickable" onClick={handleLanternClick}>
        <div className="sf-lantern sf-lantern-1">
          <div className="sf-lantern-line"></div>
          <div className="sf-lantern-body">
            <div className="sf-lantern-top"></div>
            <div className="sf-lantern-middle">
              <span className={`sf-lantern-char ${lanternFading ? 'sf-char-fade-out' : 'sf-char-fade-in'}`}>
                {lanternChars[0] || '福'}
              </span>
            </div>
            <div className="sf-lantern-bottom"></div>
            <div className="sf-lantern-tassel"></div>
          </div>
        </div>
        <div className="sf-lantern sf-lantern-2">
          <div className="sf-lantern-line"></div>
          <div className="sf-lantern-body">
            <div className="sf-lantern-top"></div>
            <div className="sf-lantern-middle">
              <span className={`sf-lantern-char ${lanternFading ? 'sf-char-fade-out' : 'sf-char-fade-in'}`}>
                {lanternChars[1] || '春'}
              </span>
            </div>
            <div className="sf-lantern-bottom"></div>
            <div className="sf-lantern-tassel"></div>
          </div>
        </div>
      </div>

      {/* 灯笼 - 右侧（往中间靠拢），可点击 */}
      <div className="sf-lantern-group sf-lantern-right sf-lantern-clickable" onClick={handleLanternClick}>
        <div className="sf-lantern sf-lantern-3">
          <div className="sf-lantern-line"></div>
          <div className="sf-lantern-body">
            <div className="sf-lantern-top"></div>
            <div className="sf-lantern-middle">
              <span className={`sf-lantern-char ${lanternFading ? 'sf-char-fade-out' : 'sf-char-fade-in'}`}>
                {lanternChars[2] || '喜'}
              </span>
            </div>
            <div className="sf-lantern-bottom"></div>
            <div className="sf-lantern-tassel"></div>
          </div>
        </div>
        <div className="sf-lantern sf-lantern-4">
          <div className="sf-lantern-line"></div>
          <div className="sf-lantern-body">
            <div className="sf-lantern-top"></div>
            <div className="sf-lantern-middle">
              <span className={`sf-lantern-char ${lanternFading ? 'sf-char-fade-out' : 'sf-char-fade-in'}`}>
                {lanternChars[3] || '乐'}
              </span>
            </div>
            <div className="sf-lantern-bottom"></div>
            <div className="sf-lantern-tassel"></div>
          </div>
        </div>
      </div>

      {/* 飘落装饰物 */}
      <div className="sf-falling-container">
        {fallingItems.map(item => (
          <span
            key={item.id}
            className="sf-falling-item"
            style={{
              left: `${item.left}%`,
              animationDelay: `${item.delay}s`,
              animationDuration: `${item.duration}s`,
              fontSize: `${item.size}px`,
            }}
          >
            {item.emoji}
          </span>
        ))}
      </div>

      {/* 顶部红色装饰条 */}
      <div className="sf-top-border"></div>
    </>
  );
}