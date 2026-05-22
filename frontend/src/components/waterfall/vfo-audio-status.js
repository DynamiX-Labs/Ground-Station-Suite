/**
 * Shared VFO audio status resolver for tab and overlay icon consistency.
 */

export const VFO_AUDIO_STATUS = Object.freeze({
    NO_AUDIO: 'no-audio',
    MUTED: 'muted',
    SQUELCHED: 'squelched',
    PLAYING: 'playing',
});

/**
 * Resolve the UI audio state for a VFO.
 *
 * @param {Object} params
 * @param {boolean} params.isStreaming - Whether audio packets are arriving.
 * @param {boolean} params.isMuted - Whether user muted the VFO.
 * @param {boolean|null|undefined} params.isSquelchOpen - Squelch gate open state, if available.
 * @returns {'no-audio'|'muted'|'squelched'|'playing'}
 */
export const resolveVfoAudioStatus = ({ isStreaming, isMuted, isSquelchOpen }) => {
    if (!isStreaming) {
        return VFO_AUDIO_STATUS.NO_AUDIO;
    }
    if (isMuted) {
        return VFO_AUDIO_STATUS.MUTED;
    }
    if (isSquelchOpen === false) {
        return VFO_AUDIO_STATUS.SQUELCHED;
    }
    return VFO_AUDIO_STATUS.PLAYING;
};
