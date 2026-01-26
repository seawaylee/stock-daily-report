import React from 'react';
import { AbsoluteFill, useVideoConfig, useCurrentFrame, interpolate, spring, Easing, Sequence } from 'remotion';
import data from '../public/summary_data.json';

const COLOR_BG = '#0F1115';
const COLOR_CARD = '#1C1F26';
const COLOR_RED = '#FF4444';
const COLOR_GREEN = '#00CC88';
const COLOR_GOLD = '#FFD700';
const COLOR_TEXT = '#FFFFFF';
const COLOR_SUBTEXT = '#888888';

const Card: React.FC<{ title: string; children: React.ReactNode; delay: number }> = ({ title, children, delay }) => {
    const frame = useCurrentFrame();
    const opacity = interpolate(frame, [delay, delay + 20], [0, 1]);
    const translateY = interpolate(frame, [delay, delay + 20], [20, 0], { extrapolateRight: 'clamp' });

    return (
        <div style={{
            background: COLOR_CARD,
            borderRadius: 16,
            padding: 24,
            marginBottom: 24,
            opacity,
            transform: `translateY(${translateY}px)`,
            border: '1px solid #333',
            boxShadow: '0 4px 20px rgba(0,0,0,0.3)'
        }}>
            <div style={{
                color: COLOR_SUBTEXT,
                fontSize: 24,
                marginBottom: 16,
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: 2
            }}>
                {title}
            </div>
            {children}
        </div>
    );
};

export const MarketSummaryVideo: React.FC = () => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    // Animations
    const titleSlide = spring({ frame, fps, config: { damping: 15 } });

    return (
        <AbsoluteFill style={{ backgroundColor: COLOR_BG, padding: 40, fontFamily: 'system-ui, sans-serif' }}>

            {/* Background Texture */}
            <div style={{
                position: 'absolute', inset: 0,
                backgroundImage: 'radial-gradient(#333 1px, transparent 1px)',
                backgroundSize: '40px 40px',
                opacity: 0.1
            }} />

            {/* Header */}
            <div style={{
                marginBottom: 40,
                transform: `translateX(${interpolate(titleSlide, [0, 1], [-50, 0])}px)`,
                opacity: titleSlide,
                borderBottom: `2px solid ${COLOR_RED}`,
                paddingBottom: 20,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-end'
            }}>
                <div>
                    <div style={{ color: COLOR_RED, fontSize: 32, fontWeight: 'bold', letterSpacing: 4 }}>MARKET DAILY</div>
                    <div style={{ color: COLOR_TEXT, fontSize: 80, fontWeight: 900, lineHeight: 1 }}>{data.date}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                    <div style={{ color: COLOR_SUBTEXT, fontSize: 24 }}>MARKET MODE</div>
                    <div style={{
                        color: COLOR_GOLD,
                        fontSize: 48,
                        fontWeight: 'bold',
                        textShadow: `0 0 20px ${COLOR_GOLD}40`
                    }}>
                        {data.market_mode}
                    </div>
                </div>
            </div>

            {/* Main Grid Layout */}
            <div style={{ display: 'flex', gap: 40, height: '100%' }}>

                {/* Left Column: Narrative */}
                <div style={{ flex: 1.2 }}>
                    <Card title="Core Narrative" delay={15}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                            {data.summary_bullets.map((bullet, i) => (
                                <div key={i} style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    fontSize: 36,
                                    color: COLOR_TEXT,
                                    fontWeight: 500,
                                    lineHeight: 1.4
                                }}>
                                    <div style={{
                                        width: 12, height: 12,
                                        background: COLOR_RED,
                                        borderRadius: '50%',
                                        marginRight: 20,
                                        boxShadow: `0 0 10px ${COLOR_RED}`
                                    }} />
                                    {bullet}
                                </div>
                            ))}
                        </div>
                    </Card>

                    <Card title="Strategy Focus" delay={30}>
                        <div style={{
                            fontSize: 42,
                            fontWeight: 'bold',
                            color: COLOR_TEXT,
                            background: 'linear-gradient(90deg, #333, transparent)',
                            padding: 20,
                            borderLeft: `8px solid ${COLOR_GOLD}`
                        }}>
                            {data.strategy}
                        </div>
                    </Card>
                </div>

                {/* Right Column: Data */}
                <div style={{ flex: 0.8 }}>
                    <Card title="Sector Heatmap" delay={45}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 15 }}>
                            {data.hot_sectors.map((sector, i) => (
                                <div key={i} style={{
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                    padding: '15px 20px',
                                    background: 'rgba(255,255,255,0.03)',
                                    borderRadius: 8
                                }}>
                                    <span style={{ fontSize: 32, color: COLOR_TEXT, fontWeight: 600 }}>
                                        {sector.name}
                                    </span>
                                    <span style={{
                                        fontSize: 32,
                                        fontWeight: 'bold',
                                        color: sector.type === 'up' ? COLOR_RED : COLOR_GREEN
                                    }}>
                                        {sector.change}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </Card>

                    {/* Sentiment Meter Mockup */}
                    <Card title="Sentiment Score" delay={60}>
                        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 10 }}>
                            <div style={{ fontSize: 80, fontWeight: 900, color: COLOR_TEXT, lineHeight: 0.8 }}>
                                {data.sentiment_score}
                            </div>
                            <div style={{ fontSize: 24, color: COLOR_SUBTEXT, marginBottom: 10 }}>/ 100</div>
                        </div>
                        <div style={{
                            height: 10,
                            background: '#333',
                            borderRadius: 5,
                            marginTop: 20,
                            overflow: 'hidden'
                        }}>
                            <div style={{
                                width: `${data.sentiment_score}%`,
                                height: '100%',
                                background: `linear-gradient(90deg, ${COLOR_GREEN}, ${COLOR_RED})`
                            }} />
                        </div>
                        <div style={{ marginTop: 10, color: COLOR_SUBTEXT, fontSize: 20 }}>Fear / Panic Zone</div>
                    </Card>
                </div>
            </div>

            {/* Footer Ticker */}
            <div style={{
                position: 'absolute', bottom: 40, left: 40, right: 40,
                borderTop: '1px solid #333', paddingTop: 20,
                display: 'flex', justifyContent: 'center', gap: 40,
                color: COLOR_SUBTEXT, fontSize: 20,
                opacity: 0.6
            }}>
                <span>STOCK DAILY REPORT • POWERED BY AGENTIC AI</span>
                <span>•</span>
                <span>DATA SOURCE: EASTMONEY</span>
            </div>

        </AbsoluteFill>
    );
};

