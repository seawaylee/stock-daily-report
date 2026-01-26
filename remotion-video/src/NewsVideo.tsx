import React from 'react';
import { AbsoluteFill, useVideoConfig, Sequence, useCurrentFrame, interpolate, spring } from 'remotion';
import newsData from '../public/news_data.json';

const FONT_BODY = '"Helvetica Neue", Helvetica, Arial, sans-serif';
const FONT_SERIF = '"Noto Serif SC", serif';

export const NewsVideo: React.FC = () => {
    const { fps, width, height } = useVideoConfig();
    const frame = useCurrentFrame();

    // 1. Intro Animation (0-40 frames)
    const introOp = interpolate(frame, [0, 20, 40, 50], [0, 1, 1, 0]);
    const introScale = interpolate(frame, [0, 50], [0.8, 1.2]);

    // 2. Main Content (Starts at 40)
    const contentStart = 40;
    const scrollDuration = 560; // Total 600 - 40 (Slower scroll for 20s)

    // Calculate total height needed? Not easily known in Remotion without measure.
    // We will just scroll smoothly.
    // 10 items * ~200px = 2000px.
    const scrollY = interpolate(frame,
        [contentStart, contentStart + scrollDuration],
        [0, -1500], // Approximate scroll distance
        { extrapolateRight: 'clamp' }
    );

    const contentOp = interpolate(frame, [30, 45], [0, 1]);

    return (
        <AbsoluteFill style={{ backgroundColor: '#F9F9F9' }}>
            {/* Background Texture */}
            <div style={{
                position: 'absolute', inset: 0,
                backgroundImage: 'url("https://www.transparenttextures.com/patterns/dust.png")',
                opacity: 0.5
            }} />

            {/* INTRO OVERLAY */}
            <div style={{
                position: 'absolute', inset: 0,
                display: frame < 50 ? 'flex' : 'none',
                justifyContent: 'center', alignItems: 'center',
                zIndex: 100,
                opacity: introOp,
                transform: `scale(${introScale})`
            }}>
                <div style={{
                    background: '#D32F2F',
                    color: 'white',
                    padding: '40px 80px',
                    borderRadius: 20,
                    boxShadow: '0 10px 30px rgba(0,0,0,0.3)',
                    textAlign: 'center'
                }}>
                    <div style={{ fontSize: 80, fontWeight: 'bold', fontFamily: FONT_SERIF }}>24h 核心要闻</div>
                    <div style={{ fontSize: 30, marginTop: 10, opacity: 0.9 }}>{newsData.date} · 权威发布</div>
                </div>
            </div>

            {/* MAIN CONTENT */}
            <AbsoluteFill style={{ opacity: contentOp }}>
                {/* Fixed Header */}
                <div style={{
                    position: 'absolute', top: 0, left: 0, right: 0, height: 180,
                    background: '#D32F2F',
                    zIndex: 20,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    boxShadow: '0 5px 20px rgba(0,0,0,0.2)'
                }}>
                    <span style={{ color: 'white', fontSize: 60, fontWeight: 'bold', fontFamily: FONT_SERIF }}>
                        关键资讯 · 财经日历
                    </span>
                </div>

                {/* Scrolling List */}
                <div style={{
                    position: 'absolute',
                    top: 200, bottom: 0, left: 0, right: 0,
                    overflow: 'hidden', // Mask
                    display: 'flex', flexDirection: 'column'
                }}>
                    <div style={{
                        padding: '20px 40px',
                        transform: `translateY(${scrollY}px)`
                    }}>
                        {newsData.items.map((item, i) => (
                            <div key={i} style={{
                                background: 'white',
                                borderRadius: 12,
                                padding: '30px 35px', // Little more padding
                                marginBottom: 25,
                                boxShadow: '0 2px 10px rgba(0,0,0,0.08)',
                                borderLeft: `12px solid ${item.type === 'bull' ? '#D32F2F' : '#2E7D32'}`, // Thicker indicator
                                display: 'flex', flexDirection: 'column', gap: 15
                            }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <div style={{ display: 'flex', gap: 15, alignItems: 'center' }}>
                                        {/* IMPACTFUL TAG */}
                                        <div style={{
                                            background: item.type === 'bull' ? '#FFEBEE' : '#E8F5E9',
                                            color: item.type === 'bull' ? '#D32F2F' : '#2E7D32',
                                            padding: '8px 20px', borderRadius: 8,
                                            fontWeight: '900', fontSize: 34, // Bigger & Bolder
                                            letterSpacing: 2,
                                            border: `2px solid ${item.type === 'bull' ? '#D32F2F' : '#2E7D32'}` // High Contrast Border
                                        }}>
                                            {item.tag_full} {/* Use full tag "利多·金融" */}
                                        </div>
                                        <span style={{ color: '#999', fontSize: 24, fontWeight: '500' }}>{item.time}</span>
                                    </div>
                                </div>
                                <div style={{
                                    fontSize: 36, // Bigger Font
                                    lineHeight: 1.5,
                                    fontWeight: 'bold',
                                    color: '#222', // Darker black
                                    fontFamily: FONT_BODY
                                }}>
                                    {item.title}
                                </div>
                            </div>
                        ))}
                        {/* Spacing at bottom */}
                        <div style={{ height: 200 }} />
                    </div>
                </div>

                {/* Footer Gradient */}
                <div style={{
                    position: 'absolute', bottom: 0, left: 0, right: 0, height: 150,
                    background: 'linear-gradient(to top, #F9F9F9 20%, transparent)',
                    zIndex: 10
                }} />
            </AbsoluteFill>
        </AbsoluteFill>
    );
};
