import React from 'react';
import { AbsoluteFill, useVideoConfig, Sequence, useCurrentFrame, interpolate, spring } from 'remotion';
import data from '../public/ladder_data.json';

const COLOR_BG = '#F5E6C8';
const COLOR_RED = '#D32F2F';
const COLOR_BLACK = '#000000';
const COLOR_GOLD = '#FFD700';

// Type definitions
type Stock = {
    name: string;
    theme: string;
    is_yizi: boolean;
    is_broken: boolean;
};

type BoardData = {
    board: string;
    count: number;
    stocks: Stock[];
};

// ------------------------------------------------------------------
// Sub-components for different visual impacts
// ------------------------------------------------------------------

// 1. HERO SLIDE
const HeroSlide: React.FC<{ item: BoardData }> = ({ item }) => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    return (
        <AbsoluteFill style={{
            backgroundColor: COLOR_BG,
            justifyContent: 'center',
            alignItems: 'center',
            fontFamily: '"ZCOOL KuaiLe", sans-serif'
        }}>
            {/* Background Board Number Watermark */}
            <div style={{
                position: 'absolute',
                fontSize: 600,
                color: 'rgba(0,0,0,0.05)',
                fontWeight: 'bold',
                zIndex: 0
            }}>
                {item.board.replace('板', '')}
            </div>

            {/* Board Title */}
            <div style={{ zIndex: 1, marginBottom: 60 }}>
                <span style={{
                    fontSize: 80,
                    color: COLOR_RED,
                    border: '4px solid #D32F2F',
                    padding: '10px 30px',
                    borderRadius: 20,
                    backgroundColor: '#fff'
                }}>{item.board} 晋级</span>
            </div>

            {/* Stocks Container */}
            <div style={{
                zIndex: 1,
                display: 'flex',
                flexDirection: 'column',
                gap: 40,
                width: '100%',
                alignItems: 'center'
            }}>
                {item.stocks.map((stock, i) => {
                    const delay = i * 10;
                    const ent = spring({
                        frame: frame - delay,
                        fps,
                        config: { damping: 10, mass: 0.5, stiffness: 200 }
                    });

                    const scale = interpolate(ent, [0, 1], [3, 1]);
                    const opacity = interpolate(ent, [0, 0.5], [0, 1]);

                    return (
                        <div key={i} style={{
                            transform: `scale(${scale})`,
                            opacity,
                            textAlign: 'center'
                        }}>
                            <div style={{
                                fontSize: 160,
                                fontWeight: '900',
                                color: COLOR_BLACK,
                                textShadow: '4px 4px 0px rgba(0,0,0,0.2)'
                            }}>
                                {stock.name}
                            </div>
                            <div style={{
                                fontSize: 50,
                                fontWeight: 'bold',
                                color: 'white',
                                backgroundColor: COLOR_RED,
                                padding: '5px 20px',
                                borderRadius: 50,
                                display: 'inline-block',
                                marginTop: 10
                            }}>
                                {stock.theme}
                            </div>
                        </div>
                    );
                })}
            </div>
        </AbsoluteFill>
    );
};

// 2. GRID SLIDE
const GridSlide: React.FC<{ item: BoardData }> = ({ item }) => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    return (
        <AbsoluteFill style={{ backgroundColor: COLOR_BG, padding: 40 }}>
            {/* Header */}
            <div style={{
                fontSize: 60,
                fontWeight: 'bold',
                color: COLOR_RED,
                marginBottom: 40,
                borderBottom: `4px solid ${COLOR_RED}`
            }}>
                {item.board} <span style={{ fontSize: 40, color: '#555' }}>(共{item.count}只)</span>
            </div>

            {/* Grid */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: 30
            }}>
                {item.stocks.map((stock, i) => {
                    const delay = i * 5;
                    const pop = spring({
                        frame: frame - delay,
                        fps,
                        config: { damping: 12, stiffness: 100 }
                    });
                    const scale = interpolate(pop, [0, 1], [0, 1]);

                    return (
                        <div key={i} style={{
                            transform: `scale(${scale})`,
                            backgroundColor: 'white',
                            padding: 20,
                            borderRadius: 15,
                            boxShadow: '0 4px 10px rgba(0,0,0,0.1)',
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            borderLeft: stock.is_yizi ? `10px solid ${COLOR_RED}` : 'none'
                        }}>
                            <span style={{ fontSize: 45, fontWeight: 'bold' }}>{stock.name}</span>
                            <span style={{ fontSize: 25, color: '#666', marginTop: 5 }}>{stock.theme}</span>
                        </div>
                    );
                })}
            </div>
        </AbsoluteFill>
    );
};

// 3. MATRIX SLIDE: 3D Parallax Stream ("Cyber Flow")
const MatrixSlide: React.FC<{ item: BoardData }> = ({ item }) => {
    const frame = useCurrentFrame();
    const { height } = useVideoConfig();

    // Split stocks into 3 columns for parallax
    const col1 = item.stocks.filter((_, i) => i % 3 === 0);
    const col2 = item.stocks.filter((_, i) => i % 3 === 1);
    const col3 = item.stocks.filter((_, i) => i % 3 === 2);

    const columns = [col1, col2, col3];
    const duration = 450; // 15s sequence

    // Dynamic camera movement
    const cameraZoom = interpolate(frame, [0, duration], [1, 1.1]);

    return (
        <AbsoluteFill style={{
            backgroundColor: COLOR_BG,
            overflow: 'hidden',
            perspective: '1200px'  // Deep 3D perspective
        }}>
            {/* Background Texture */}
            <div style={{
                position: 'absolute', inset: 0,
                backgroundImage: 'radial-gradient(#ccc 1px, transparent 1px)',
                backgroundSize: '30px 30px',
                opacity: 0.2,
                transform: `rotateX(60deg) translateY(${frame}px)` // Moving floor
            }} />

            {/* Sticky Header */}
            <div style={{
                position: 'absolute',
                top: 80, left: 0, right: 0,
                display: 'flex', justifyContent: 'center',
                zIndex: 20,
                transform: `scale(${cameraZoom})`
            }}>
                <div style={{
                    background: COLOR_RED,
                    color: COLOR_GOLD,
                    padding: '20px 60px',
                    borderRadius: 80,
                    boxShadow: '0 20px 60px rgba(211,47,47,0.5)',
                    textAlign: 'center',
                    border: '4px solid white'
                }}>
                    <div style={{ fontSize: 80, fontWeight: '900', lineHeight: 1 }}>{item.board}</div>
                    <div style={{ fontSize: 30, color: 'white', marginTop: 10, letterSpacing: 4 }}>
                        狂潮 · 共{item.count}只
                    </div>
                </div>
            </div>

            {/* 3-Column Stream */}
            <div style={{
                display: 'flex',
                width: '100%',
                height: '100%',
                justifyContent: 'center',
                gap: 40,
                transform: 'rotateX(15deg) translateY(100px)', // Angled view
                transformStyle: 'preserve-3d'
            }}>
                {columns.map((col, colIndex) => {
                    // Parallax: Middle column moves faster
                    const isMiddle = colIndex === 1;
                    const speedMultiplier = isMiddle ? 1.2 : 1.0;

                    // Calculate total height to scroll
                    const contentHeight = col.length * 180; // card height + gap
                    const travel = contentHeight + 1000;

                    const y = interpolate(
                        frame,
                        [0, duration],
                        [height, -travel],
                        { extrapolateRight: 'clamp' }
                    );

                    return (
                        <div key={colIndex} style={{
                            width: '28%',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: 30,
                            transform: `translateY(${y * speedMultiplier}px) translateZ(${isMiddle ? 50 : 0}px)`,
                            opacity: interpolate(frame, [duration - 30, duration], [1, 0])
                        }}>
                            {col.map((stock, i) => (
                                <div key={i} style={{
                                    background: 'white',
                                    borderRadius: 24,
                                    padding: '25px 15px',
                                    boxShadow: '0 15px 35px rgba(0,0,0,0.1)',
                                    textAlign: 'center',
                                    position: 'relative',
                                    borderBottom: `8px solid ${stock.is_yizi ? COLOR_RED : '#ddd'}`,
                                    transform: `rotate(${Math.sin(i + frame / 50) * 2}deg)` // Subtle float
                                }}>
                                    {stock.is_yizi && (
                                        <div style={{
                                            position: 'absolute', top: -10, left: -10,
                                            background: COLOR_RED, color: 'white',
                                            padding: '4px 12px', borderRadius: 10,
                                            fontSize: 14, fontWeight: 'bold',
                                            boxShadow: '0 4px 10px rgba(0,0,0,0.2)'
                                        }}>一字板</div>
                                    )}
                                    <div style={{
                                        color: '#666',
                                        fontSize: 22,
                                        marginBottom: 5,
                                        fontFamily: 'sans-serif'
                                    }}>
                                        {stock.theme}
                                    </div>
                                    <div style={{
                                        color: '#000',
                                        fontSize: 42,
                                        fontWeight: '800',
                                    }}>
                                        {stock.name}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )
                })}
            </div>

            {/* Vignette Overlay */}
            <div style={{
                position: 'absolute', inset: 0,
                background: 'radial-gradient(circle, transparent 50%, rgba(0,0,0,0.1) 100%)',
                pointerEvents: 'none',
                zIndex: 10
            }} />
        </AbsoluteFill>
    );
};

// Intro with impact
const CrashTitle: React.FC = () => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    const drop = spring({ frame, fps, from: -1000, to: 0, config: { damping: 15 } });
    const shake = interpolate(frame, [10, 15, 20, 25], [0, -10, 10, 0], { extrapolateRight: 'clamp' })

    return (
        <AbsoluteFill style={{ backgroundColor: COLOR_RED, justifyContent: 'center', alignItems: 'center' }}>
            <div style={{
                transform: `translateY(${drop}px) rotate(${shake}deg)`,
                fontSize: 120,
                color: COLOR_GOLD,
                fontWeight: '900',
                textAlign: 'center',
                lineHeight: 1.2
            }}>
                <div style={{ color: 'white', fontSize: 60 }}>01月26日</div>
                涨停天梯
                <div style={{ fontSize: 40, color: 'white', marginTop: 20 }}>资金进攻方向</div>
            </div>
        </AbsoluteFill>
    )
}

export const LadderVideo: React.FC = () => {
    // Allocation Logic
    // Intro: 50 frames
    // High Boards (<5 stocks): 90 frames (3s)
    // Mid Boards (5-20): 120 frames (4s)
    // Mass Boards (>20): 450 frames (15s) for reading

    let accumulatedFrames = 50;

    return (
        <AbsoluteFill style={{ backgroundColor: COLOR_BG }}>
            <Sequence from={0} durationInFrames={50}>
                <CrashTitle />
            </Sequence>

            {data.map((item, index) => {
                let duration = 90;
                let Component = HeroSlide;

                if (item.count > 20) {
                    duration = 450;
                    Component = MatrixSlide;
                } else if (item.count > 4) {
                    duration = 150;
                    Component = GridSlide;
                } else {
                    duration = 90;
                    Component = HeroSlide;
                }

                const start = accumulatedFrames;
                accumulatedFrames += duration;

                return (
                    <Sequence from={start} durationInFrames={duration} key={index}>
                        <Component item={item as BoardData} />
                    </Sequence>
                );
            })}
        </AbsoluteFill>
    );
};
