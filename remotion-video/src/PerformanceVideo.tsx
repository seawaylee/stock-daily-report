import React from 'react';
import { AbsoluteFill, useVideoConfig, Sequence, useCurrentFrame, interpolate, spring, staticFile } from 'remotion';
import perfData from '../public/performance_data.json';

// Font: Professional Serif/Sans combination
const FONT_FAMILY_SERIF = '"Noto Serif SC", serif';
const FONT_FAMILY_SANS = '"Helvetica Neue", Helvetica, Arial, sans-serif';

// Theme Configurations: Professional, Red Intro Background, Top 10 Layout
const STYLES: Record<string, any> = {
    growth: {
        color: '#D32F2F',
        bg: '#D32F2F', // Header BG
        title: '盈利增速 TOP10',
        sub: 'GROWTH LEADER'
    },
    turnaround: {
        color: '#E65100',
        bg: '#E65100',
        title: '扭亏为盈 TOP10',
        sub: 'TURNAROUND'
    },
    loss_turn: {
        color: '#1565C0',
        bg: '#1565C0',
        title: '盈转亏 TOP10',
        sub: 'LOSS ALERT'
    },
    loss_expand: {
        color: '#2E7D32',
        bg: '#2E7D32',
        title: '亏损扩大 TOP10',
        sub: 'RISK WARNING'
    }
};

const BACKGROUND_TEXTURE = 'url("https://www.transparenttextures.com/patterns/dust.png")';

const StickyNote: React.FC<{ stock: any; index: number; theme: any }> = ({ stock, index, theme }) => {
    const { fps } = useVideoConfig();
    const frame = useCurrentFrame();

    // Slotted list animation
    const delay = index * 2;
    const progress = spring({ frame: frame - delay, fps, config: { damping: 20 } });
    const x = interpolate(progress, [0, 1], [100, 0]); // Slide in from right for variety
    const opacity = interpolate(progress, [0, 1], [0, 1]);

    return (
        <div style={{
            opacity,
            transform: `translateX(${x}px)`,
            background: 'white',
            borderRadius: '8px',
            padding: '0 30px', // Horizontal padding only, let flex handle vertical height
            boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
            borderLeft: `8px solid ${theme.color}`, // Thicker accent
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            border: '1px solid #eee',
            flex: 1, // GROW TO FILL SPACE!
            minHeight: 0 // Allow shrinking if needed
        }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
                <span style={{
                    fontFamily: FONT_FAMILY_SANS,
                    fontSize: 40, // Bigger font
                    fontWeight: 'bold',
                    color: '#222'
                }}>
                    {stock.name}
                </span>
                <span style={{
                    fontSize: 22,
                    color: '#666',
                    fontFamily: FONT_FAMILY_SANS,
                    background: '#f4f4f4',
                    padding: '4px 10px',
                    borderRadius: 4
                }}>
                    {stock.industry}
                </span>
            </div>

            <div style={{ textAlign: 'right', display: 'flex', alignItems: 'center', gap: 20 }}>
                <div style={{ fontSize: 22, color: '#888' }}>净利{stock.profit}</div>
                <div style={{
                    fontFamily: FONT_FAMILY_SANS,
                    fontSize: 50, // Huge numbers
                    fontWeight: '900',
                    color: theme.color
                }}>
                    {stock.change}
                </div>
            </div>
        </div>
    );
};

const SectionSlide: React.FC<{ section: any }> = ({ section }) => {
    const theme = STYLES[section.key] || STYLES.growth;

    // Ensure 10 items for Top 10 density
    let items = [...section.items];
    while (items.length < 10 && items.length > 0) {
        items = items.concat(items).slice(0, 10);
    }

    return (
        <AbsoluteFill style={{ backgroundColor: '#F5F5F5' }}>
            {/* Texture */}
            <div style={{
                position: 'absolute', inset: 0,
                backgroundImage: BACKGROUND_TEXTURE,
                opacity: 0.4
            }} />

            {/* Professional Fixed Header */}
            <div style={{
                height: 220,
                background: theme.bg,
                color: 'white',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                alignItems: 'center',
                boxShadow: '0 4px 10px rgba(0,0,0,0.2)',
                zIndex: 10,
                position: 'relative'
            }}>
                <div style={{
                    fontFamily: FONT_FAMILY_SERIF,
                    fontSize: 80, // Bigger Title
                    fontWeight: 'bold',
                    textShadow: '0 2px 0 rgba(0,0,0,0.2)'
                }}>{theme.title}</div>
                <div style={{
                    fontSize: 22,
                    letterSpacing: 6,
                    marginTop: 10,
                    opacity: 0.9,
                    fontFamily: FONT_FAMILY_SANS
                }}>{theme.sub}</div>
            </div>

            {/* List Content - Flex Column asking for full height */}
            <div style={{
                position: 'absolute',
                top: 220, // Start after header
                bottom: 60, // End before footer
                left: 0, right: 0,
                padding: '15px 50px',
                display: 'flex',
                flexDirection: 'column',
                gap: 15, // Gap between items
            }}>
                {items.map((stock: any, i: number) => (
                    <StickyNote key={i} index={i} stock={stock} theme={theme} />
                ))}
            </div>

            {/* Footer */}
            <div style={{
                position: 'absolute',
                bottom: 0, left: 0, right: 0,
                height: 60,
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                fontFamily: FONT_FAMILY_SANS,
                fontSize: 20,
                color: '#999',
                backgroundColor: '#fff',
                borderTop: '1px solid #eee',
                zIndex: 10
            }}>
                A股业绩速递 · 每日收盘更新
            </div>
        </AbsoluteFill>
    );
};

// Use staticFile instead of require for reliable asset resolution
const Intro: React.FC = () => {
    const frame = useCurrentFrame();
    const scale = interpolate(frame, [0, 60], [1, 1.05]);
    const introImg = staticFile('intro_bg.png');

    return (
        <AbsoluteFill>
            <div style={{
                position: 'absolute', inset: 0,
                backgroundImage: `url("${introImg}")`,
                backgroundSize: 'cover',
                backgroundPosition: 'center',
                transform: `scale(${scale})`
            }} />
        </AbsoluteFill>
    )
}

export const PerformanceVideo: React.FC = () => {
    // 20s total
    const introDuration = 60;
    const totalDuration = 600;
    const sectionDuration = Math.floor((totalDuration - introDuration) / 4);

    return (
        <AbsoluteFill>
            <Sequence from={0} durationInFrames={introDuration}>
                <Intro />
            </Sequence>
            {perfData.sections.slice(0, 4).map((section, i) => (
                <Sequence
                    key={i}
                    from={introDuration + i * sectionDuration}
                    durationInFrames={sectionDuration}
                >
                    <SectionSlide section={section} />
                </Sequence>
            ))}
        </AbsoluteFill>
    );
};
