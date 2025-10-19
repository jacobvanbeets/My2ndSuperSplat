import { EventHandle } from 'playcanvas';

import { Events } from './events';

const registerTimelineEvents = (events: Events) => {
    let frames = 180;
    let frameRate = 30;
    let smoothness = 1;

    // frames

    const setFrames = (value: number) => {
        if (value !== frames) {
            frames = value;
            events.fire('timeline.frames', frames);
        }
    };

    events.function('timeline.frames', () => {
        return frames;
    });

    events.on('timeline.setFrames', (value: number) => {
        setFrames(value);
    });

    // frame rate

    const setFrameRate = (value: number) => {
        if (value !== frameRate) {
            frameRate = value;
            events.fire('timeline.frameRate', frameRate);
        }
    };

    events.function('timeline.frameRate', () => {
        return frameRate;
    });

    events.on('timeline.setFrameRate', (value: number) => {
        setFrameRate(value);
    });

    // smoothness

    const setSmoothness = (value: number) => {
        if (value !== smoothness) {
            smoothness = value;
            events.fire('timeline.smoothness', smoothness);
        }
    };

    events.function('timeline.smoothness', () => {
        return smoothness;
    });

    events.on('timeline.setSmoothness', (value: number) => {
        setSmoothness(value);
    });

    // current frame
    let frame = 0;

    const setFrame = (value: number) => {
        if (value !== frame) {
            frame = value;
            events.fire('timeline.frame', frame);
        }
    };

    events.function('timeline.frame', () => {
        return frame;
    });

    events.on('timeline.setFrame', (value: number) => {
        setFrame(value);
    });

    // anim controls
    let animHandle: EventHandle = null;

    const play = () => {
        let time = frame;

        // handle application update tick
        animHandle = events.on('update', (dt: number) => {
            time = (time + dt * frameRate) % frames;
            setFrame(Math.floor(time));
            events.fire('timeline.time', time);
        });
    };

    const stop = () => {
        animHandle.off();
        animHandle = null;
    };

    // playing state
    let playing = false;

    const setPlaying = (value: boolean) => {
        if (value !== playing) {
            playing = value;
            events.fire('timeline.playing', playing);
            if (playing) {
                play();
            } else {
                stop();
            }
        }
    };

    events.function('timeline.playing', () => {
        return playing;
    });

    events.on('timeline.setPlaying', (value: boolean) => {
        setPlaying(value);
    });

    // keys with types

    interface TimelineKey {
        frame: number;
        types: Set<string>; // can have multiple types (camera, depth, size)
    }

    const keys: TimelineKey[] = [];

    events.function('timeline.keys', () => {
        return keys.map(k => k.frame); // maintain backward compatibility
    });

    events.function('timeline.keysWithTypes', () => {
        return keys;
    });

    events.on('timeline.addKey', (frame: number, keyType: string = 'camera') => {
        let existingKey = keys.find(k => k.frame === frame);
        if (!existingKey) {
            existingKey = { frame, types: new Set() };
            keys.push(existingKey);
            keys.sort((a, b) => a.frame - b.frame); // keep sorted
        }
        existingKey.types.add(keyType);
        events.fire('timeline.keyAdded', frame, keyType);
    });

    events.on('timeline.removeKey', (index: number, keyType?: string) => {
        if (index >= 0 && index < keys.length) {
            if (keyType) {
                // Remove specific type from key
                keys[index].types.delete(keyType);
                if (keys[index].types.size === 0) {
                    // If no types left, remove the entire key
                    keys.splice(index, 1);
                }
            } else {
                // Remove entire key
                keys.splice(index, 1);
            }
            events.fire('timeline.keyRemoved', index, keyType);
        }
    });

    events.on('timeline.setKey', (index: number, frame: number) => {
        if (index >= 0 && index < keys.length && frame !== keys[index].frame) {
            keys[index].frame = frame;
            keys.sort((a, b) => a.frame - b.frame); // keep sorted
            events.fire('timeline.keySet', index, frame);
        }
    });

    // doc

    events.function('docSerialize.timeline', () => {
        return {
            frames,
            frameRate,
            frame,
            smoothness
        };
    });

    events.function('docDeserialize.timeline', (data: any = {}) => {
        events.fire('timeline.setFrames', data.frames ?? 180);
        events.fire('timeline.setFrameRate', data.frameRate ?? 30);
        events.fire('timeline.setFrame', data.frame ?? 0);
        events.fire('timeline.setSmoothness', data.smoothness ?? 0);
    });
};

export { registerTimelineEvents };
