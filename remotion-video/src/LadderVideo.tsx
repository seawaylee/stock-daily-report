import React from 'react';
import { AbsoluteFill, useVideoConfig, useCurrentFrame, interpolate, spring, Sequence, staticFile } from 'remotion';
import data from '../public/ladder_data.json';

const COLOR_BG = '#FDF6E3';
const COLOR_RED = '#D32F2F';
const COLOR_GOLD = '#FFD700';
const COLOR_BLACK = '#000000';

type Stock = {
    name: string;
    theme: string;
    is_yizi: boolean;
    is_broken: boolean;
    board?: string;
};

// Map board string to number
const getBoardLevel = (boardStr?: string) => {
    if (!boardStr) return 1;
    if (boardStr === '首板') return 1;
    const match = boardStr.match(/(\d+)板/);
    return match ? parseInt(match[1]) : 1;
};

// Flatten data for a continuous stream
const allStocks: Stock[] = data.flatMap(board =>
    board.stocks.map(s => ({ ...s, board: board.board }))
);

const FONT_TITLE = '"ZCOOL KuaiLe", sans-serif';

const StreamSlide: React.FC = () => {
    const frame = useCurrentFrame();
    const { height, width } = useVideoConfig();

    // 30s sequence total (900f), minus 2s intro (60f) = 840f
    const duration = 840;

    // Split into 3 columns
    const col1 = allStocks.filter((_, i) => i % 3 === 0);
    const col2 = allStocks.filter((_, i) => i % 3 === 1);
    const col3 = allStocks.filter((_, i) => i % 3 === 2);
    const columns = [col1, col2, col3];

    return (
        <AbsoluteFill style={{
            backgroundColor: COLOR_BG,
            overflow: 'hidden'
        }}>
            {/* Grid Floor */}
            <div style={{
                position: 'absolute', inset: 0,
                backgroundImage: 'linear-gradient(#ccc 1px, transparent 1px), linear-gradient(90deg, #ccc 1px, transparent 1px)',
                backgroundSize: '100px 100px',
                opacity: 0.1,
                transform: `perspective(1000px) rotateX(65deg) translateY(${frame * 2}px)`
            }} />

            {/* Header */}
            <div style={{
                position: 'absolute',
                top: 40, left: 40,
                zIndex: 100,
                display: 'flex',
                alignItems: 'center',
                gap: 20
            }}>
                <div style={{
                    background: COLOR_RED,
                    color: 'white',
                    padding: '12px 40px',
                    borderRadius: 16,
                    fontSize: 44,
                    fontWeight: 'bold',
                    boxShadow: '0 12px 24px rgba(0,0,0,0.15)',
                    border: '2px solid white'
                }}>
                    A股连板矩阵
                </div>
                <div style={{
                    color: COLOR_RED,
                    fontSize: 28,
                    fontWeight: 'bold',
                    background: 'white',
                    padding: '8px 20px',
                    borderRadius: 30,
                    boxShadow: '0 4px 10px rgba(0,0,0,0.05)'
                }}>
                    30s 全程扫描 • 共{allStocks.length}家
                </div>
            </div>

            {/* 3-Column Stream */}
            <div style={{
                display: 'flex',
                width: '100%',
                height: '100%',
                justifyContent: 'center',
                gap: 50,
                paddingTop: 150
            }}>
                {columns.map((col, colIndex) => {
                    const isMiddle = colIndex === 1;
                    const speedMultiplier = isMiddle ? 1.2 : 1.0;

                    // We need to calculate total height based on variable card sizes
                    // Level 1: 240px, Level 3: 300px, Level 7: 400px etc.
                    const cards = col.map(s => {
                        const level = getBoardLevel(s.board);
                        const scale = 1 + (level - 1) * 0.15; // 7板 is roughly 1.9x size
                        return { stock: s, level, scale };
                    });

                    const totalHeight = cards.reduce((acc, c) => acc + (250 * c.scale + 40), 0);
                    const travel = totalHeight + 2000;

                    const y = interpolate(
                        frame,
                        [0, duration],
                        [height, -travel],
                        { extrapolateRight: 'clamp' }
                    );

                    return (
                        <div key={colIndex} style={{
                            width: '30%',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: 40,
                            transform: `translateY(${y * speedMultiplier}px)`,
                            opacity: interpolate(frame, [duration - 40, duration], [1, 0])
                        }}>
                            {cards.map((item, i) => (
                                <div key={i} style={{
                                    background: 'white',
                                    borderRadius: 24 * item.scale,
                                    padding: `${25 * item.scale}px ${20 * item.scale}px`,
                                    boxShadow: `0 ${10 * item.scale}px ${30 * item.scale}px rgba(0,0,0,0.12)`,
                                    textAlign: 'center',
                                    position: 'relative',
                                    border: `${2 * item.scale}px solid ${item.stock.is_yizi ? COLOR_RED : '#eee'}`,
                                    borderBottom: `${10 * item.scale}px solid ${item.stock.is_yizi ? COLOR_RED : '#ddd'}`,
                                    transform: `scale(${item.scale})`,
                                    transformOrigin: 'top center',
                                    zIndex: item.level // Higher board count stocks stay on top
                                }}>
                                    {/* Board Tag - VERY BIG FOR HIGH BOARDS */}
                                    <div style={{
                                        position: 'absolute', top: -20, right: -15,
                                        background: COLOR_BLACK,
                                        color: COLOR_GOLD,
                                        padding: `${8 * (1 + item.level * 0.1)}px ${20 * (1 + item.level * 0.1)}px`,
                                        borderRadius: 12,
                                        fontSize: 22 + item.level * 4,
                                        fontWeight: '900',
                                        boxShadow: '0 5px 15px rgba(0,0,0,0.3)',
                                        border: '2px solid #FFD700',
                                        zIndex: 20
                                    }}>
                                        {item.stock.board}
                                    </div>

                                    {item.stock.is_yizi && (
                                        <div style={{
                                            position: 'absolute', top: -20, left: -15,
                                            background: COLOR_RED, color: 'white',
                                            padding: '8px 20px', borderRadius: 12,
                                            fontSize: 24, fontWeight: 'bold',
                                            boxShadow: '0 5px 15px rgba(211,47,47,0.3)',
                                            zIndex: 20
                                        }}>一字</div>
                                    )}

                                    <div style={{
                                        color: '#666',
                                        fontSize: 22 + (item.level > 1 ? 4 : 0),
                                        marginBottom: 10,
                                        fontWeight: '500'
                                    }}>
                                        {item.stock.theme}
                                    </div>
                                    <div style={{
                                        color: COLOR_BLACK,
                                        fontSize: 46 + item.level * 6,
                                        fontWeight: '900',
                                        letterSpacing: 1
                                    }}>
                                        {item.stock.name}
                                    </div>
                                </div>
                            ))}
                        </div>
                    );
                })}
            </div>

            {/* Edge Fades */}
            <div style={{
                position: 'absolute', top: 0, left: 0, right: 0, height: 300,
                background: `linear-gradient(to bottom, ${COLOR_BG} 30%, transparent)`,
                zIndex: 10
            }} />
            <div style={{
                position: 'absolute', bottom: 0, left: 0, right: 0, height: 300,
                background: `linear-gradient(to top, ${COLOR_BG} 30%, transparent)`,
                zIndex: 10
            }} />
        </AbsoluteFill>
    );
};

const CrashTitle: React.FC = () => {
    const frame = useCurrentFrame();
    return (
        <AbsoluteFill style={{
            backgroundColor: COLOR_RED,
            justifyContent: 'center',
            alignItems: 'center'
        }}>
            <div style={{
                fontSize: 140,
                color: COLOR_GOLD,
                fontWeight: '900',
                textAlign: 'center',
                transform: `scale(${interpolate(frame, [0, 60], [0.9, 1.1])})`
            }}>
                <div style={{ color: 'white', fontSize: 60, marginBottom: 20 }}>01月26日</div>
                涨停天梯·连板矩阵
                <div style={{ fontSize: 45, color: 'white', marginTop: 30, opacity: 0.9 }}>
                    30s 沉浸式深度复盘
                </div>
            </div>
        </AbsoluteFill>
    );
};

export const LadderVideo: React.FC = () => {
    return (
        <AbsoluteFill>
            <Sequence from={0} durationInFrames={60}>
                <CrashTitle />
            </Sequence>
            <Sequence from={60} durationInFrames={840}>
                <StreamSlide />
            </Sequence>
        </AbsoluteFill>
    );
};
