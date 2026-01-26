import { Composition } from 'remotion';
import { LadderVideo } from './LadderVideo';
import { PerformanceVideo } from './PerformanceVideo';
import { NewsVideo } from './NewsVideo';
import { MarketSummaryVideo } from './MarketSummaryVideo';
import './style.css';

export const RemotionRoot: React.FC = () => {
    return (
        <>
            <Composition
                id="LadderVideo"
                component={LadderVideo}
                durationInFrames={900} // 30s
                fps={30}
                width={1080}
                height={1920}
            />

            <Composition
                id="PerformanceVideo"
                component={PerformanceVideo}
                durationInFrames={600} // 20s
                fps={30}
                width={1080}
                height={1920}
            />

            <Composition
                id="NewsVideo"
                component={NewsVideo}
                durationInFrames={600} // 20s
                fps={30}
                width={1080}
                height={1920}
            />

            <Composition
                id="MarketSummaryVideo"
                component={MarketSummaryVideo}
                durationInFrames={900} // 30s
                fps={30}
                width={1080}
                height={1920}
            />
        </>
    );
};
