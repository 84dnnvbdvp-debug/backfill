import {Composition} from 'remotion';
import {BackfillDemo} from './BackfillDemo';

export const RemotionRoot = () => {
  return (
    <Composition
      id="BackfillDemo"
      component={BackfillDemo}
      durationInFrames={7650}
      fps={30}
      width={1920}
      height={1080}
    />
  );
};
