import { Composition } from 'remotion';
import { LadderVideo } from './LadderVideo';
import { PerformanceVideo } from './PerformanceVideo';
import './style.css';

export const RemotionRoot: React.FC = () => {
    return (
        <>
            <Composition
                id="LadderVideo"
                component={LadderVideo}
                durationInFrames={1200}
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
        </>
    );
};
