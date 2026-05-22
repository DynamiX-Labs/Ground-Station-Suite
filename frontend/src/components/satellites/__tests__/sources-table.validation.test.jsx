import {describe, expect, it} from 'vitest';

import {toFormValues, validateSourceForm} from '../sources-table.jsx';

const t = (key) => key;

describe('sources-table form helpers', () => {
    it('normalizes legacy provider in form values', () => {
        const formValues = toFormValues({
            id: 'source-1',
            name: 'Legacy OMM',
            url: 'https://example.com/omm.json',
            format: 'omm',
            query_mode: 'url',
            provider: 'celestrak',
            adapter: 'http_omm',
            norad_ids: [25544, 43017],
        });

        expect(formValues.id).toBe('source-1');
        expect(formValues.provider).toBe('generic_http');
        expect(formValues.query_mode).toBe('url');
        expect(formValues.norad_ids).toBe('25544, 43017');
    });

    it('preserves norad text input in form values when already string', () => {
        const formValues = toFormValues({
            provider: 'space_track',
            norad_ids: '25544,43017 57172',
        });

        expect(formValues.norad_ids).toBe('25544,43017 57172');
    });

    it('normalizes legacy celestrak provider and stale space-track adapter values', () => {
        const {errors, payload} = validateSourceForm(
            {
                id: null,
                name: 'Legacy OMM',
                url: 'https://example.com/omm.json',
                format: 'omm',
                query_mode: 'url',
                group_id: 'ignored',
                norad_ids: '25544 43017',
                provider: 'celestrak',
                adapter: 'space_track_gp',
                enabled: true,
                priority: '10',
                central_body: 'earth',
                auth_type: 'none',
                username: '',
                password: '',
            },
            t
        );

        expect(errors).toEqual({});
        expect(payload.query_mode).toBe('url');
        expect(payload.group_id).toBeNull();
        expect(payload.norad_ids).toBeNull();
        expect(payload.provider).toBe('generic_http');
        expect(payload.adapter).toBe('http_omm');
    });

    it('builds normalized payload for valid basic auth source', () => {
        const {errors, payload} = validateSourceForm(
            {
                id: 'source-2',
                name: 'Space-Track GP',
                url: '',
                format: 'omm',
                query_mode: 'url',
                group_id: '',
                norad_ids: '25544, 43017 57172',
                provider: 'space_track',
                adapter: 'space_track_gp',
                enabled: true,
                priority: '5',
                central_body: 'earth',
                auth_type: 'basic',
                username: 'demo',
                password: 'secret',
            },
            t
        );

        expect(errors).toEqual({});
        expect(payload.priority).toBe(5);
        expect(payload.query_mode).toBe('url');
        expect(payload.group_id).toBeNull();
        expect(payload.norad_ids).toEqual([25544, 43017, 57172]);
        expect(payload.url).toBe('https://www.space-track.org/basicspacedata/query/class/gp');
        expect(payload.username).toBe('demo');
        expect(payload.password).toBe('secret');
    });

    it('clears credentials from payload when auth type is none', () => {
        const {errors, payload} = validateSourceForm(
            {
                id: null,
                name: 'Public Source',
                url: 'https://example.com/tle.txt',
                format: '3le',
                query_mode: 'url',
                group_id: 'ignored-group',
                norad_ids: '25544',
                provider: 'generic_http',
                adapter: 'http_3le',
                enabled: true,
                priority: '100',
                central_body: 'earth',
                auth_type: 'none',
                username: 'ignored-user',
                password: 'ignored-pass',
            },
            t
        );

        expect(errors).toEqual({});
        expect(payload.query_mode).toBe('url');
        expect(payload.group_id).toBeNull();
        expect(payload.norad_ids).toBeNull();
        expect(payload.username).toBeNull();
        expect(payload.password).toBeNull();
    });

    it('requires norad ids for space-track sources', () => {
        const {errors} = validateSourceForm(
            {
                id: null,
                name: 'Space-Track Amateur',
                url: '',
                format: 'omm',
                query_mode: 'url',
                group_id: '',
                norad_ids: '',
                provider: 'space_track',
                adapter: 'space_track_gp',
                enabled: true,
                priority: '10',
                central_body: 'earth',
                auth_type: 'basic',
                username: 'demo',
                password: 'secret',
            },
            t
        );

        expect(errors.norad_ids).toBe('orbital_sources.validation.norad_ids_required');
    });

    it('derives space-track auth type from provider', () => {
        const {errors, payload} = validateSourceForm(
            {
                id: 'source-4',
                name: 'Space-Track Direct',
                url: '',
                format: 'omm',
                query_mode: 'url',
                group_id: '',
                norad_ids: '25544',
                provider: 'space_track',
                adapter: '',
                enabled: true,
                priority: '10',
                central_body: 'earth',
                auth_type: 'none',
                username: 'demo',
                password: 'secret',
            },
            t
        );

        expect(errors).toEqual({});
        expect(payload.adapter).toBe('space_track_gp');
        expect(payload.auth_type).toBe('basic');
    });
});
