import { describe, expect, it } from 'vitest';
import reducer, { clearGnssOutputsForDecoder, decoderOutputReceived, decoderStatusChanged } from '../decoders-slice.jsx';

describe('decoders slice status lifecycle', () => {
    it('keeps starting status as active decoder state', () => {
        let state = reducer(undefined, { type: '@@INIT' });

        state = reducer(state, decoderStatusChanged({
            session_id: 'session-1',
            decoder_id: 'decoder-1',
            decoder_type: 'gnss',
            vfo: 2,
            status: 'starting',
            timestamp: 1234,
            info: {
                phase: 'initializing',
            },
        }));

        expect(state.active['session-1_vfo2']).toBeDefined();
        expect(state.active['session-1_vfo2'].status).toBe('starting');
        expect(state.active['session-1_vfo2'].info?.phase).toBe('initializing');
    });

    it('clears only matching GNSS outputs on decoder restart', () => {
        let state = reducer(undefined, { type: '@@INIT' });

        state = reducer(state, decoderOutputReceived({
            timestamp: 1,
            session_id: 'session-1',
            vfo: 2,
            decoder_type: 'gnss',
            output: { event: 'nmea_gga' },
        }));
        state = reducer(state, decoderOutputReceived({
            timestamp: 2,
            session_id: 'session-1',
            vfo: 3,
            decoder_type: 'gnss',
            output: { event: 'nmea_gga' },
        }));
        state = reducer(state, decoderOutputReceived({
            timestamp: 3,
            session_id: 'session-1',
            vfo: 2,
            decoder_type: 'morse',
            output: { text: 'CQ' },
        }));

        state = reducer(state, clearGnssOutputsForDecoder({
            session_id: 'session-1',
            vfo: 2,
        }));

        expect(state.outputs).toHaveLength(2);
        expect(state.outputs.some((out) => out.decoder_type === 'gnss' && out.vfo === 2)).toBe(false);
        expect(state.outputs.some((out) => out.decoder_type === 'gnss' && out.vfo === 3)).toBe(true);
        expect(state.outputs.some((out) => out.decoder_type === 'morse')).toBe(true);
    });
});
