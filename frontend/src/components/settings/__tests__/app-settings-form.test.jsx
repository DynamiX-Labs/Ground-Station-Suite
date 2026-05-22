import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

let socketValue = null;
const navigateMock = vi.fn();
const toastSuccessMock = vi.fn();
const toastErrorMock = vi.fn();

vi.mock('react-router', async () => {
    const actual = await vi.importActual('react-router');
    return {
        ...actual,
        useNavigate: () => navigateMock,
    };
});

vi.mock('../../common/socket.jsx', () => ({
    useSocket: () => ({ socket: socketValue }),
}));

vi.mock('../../../utils/toast-with-timestamp.jsx', () => ({
    toast: {
        success: (...args) => toastSuccessMock(...args),
        error: (...args) => toastErrorMock(...args),
    },
}));

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, options) => options?.defaultValue ?? key,
    }),
}));

import AppSettingsForm from '../app-settings-form.jsx';

function buildPayload({
    host = '0.0.0.0',
    port = 5000,
    hostSource = 'file',
    hostLocked = false,
    portApplyMode = 'restart_required',
} = {}) {
    return {
        config_path: '/tmp/app_config.json',
        fields: [
            {
                key: 'host',
                value_type: 'string',
                default: '0.0.0.0',
                description: 'Host interface used by the backend web server.',
                apply_mode: 'restart_required',
                minimum: null,
                maximum: null,
                choices: null,
                sensitive: false,
                cli_flag: '--host',
            },
            {
                key: 'port',
                value_type: 'integer',
                default: 5000,
                description: 'TCP port used by the backend web server.',
                apply_mode: portApplyMode,
                minimum: 1,
                maximum: 65535,
                choices: null,
                sensitive: false,
                cli_flag: '--port',
            },
        ],
        values: {
            host,
            port,
        },
        source: {
            host: hostSource,
            port: 'file',
        },
        locked: {
            host: hostLocked,
            port: false,
        },
        defined_in_file: {
            host: true,
            port: true,
        },
        overridden_by_cli: hostLocked ? ['host'] : [],
    };
}

describe('app-settings-form', () => {
    beforeEach(() => {
        socketValue = null;
        navigateMock.mockReset();
        toastSuccessMock.mockReset();
        toastErrorMock.mockReset();
    });

    it('loads and saves settings, then shows restart-required state', async () => {
        const initialPayload = buildPayload({ hostLocked: true, hostSource: 'cli' });
        const updatedPayload = {
            ...buildPayload({ host: '127.0.0.1', hostLocked: true, hostSource: 'cli' }),
            changed_keys: ['host'],
            changed_hot_keys: [],
            changed_restart_keys: ['host'],
            restart_required: true,
        };

        socketValue = {
            emit: vi.fn((event, command, data, callback) => {
                if (event === 'data_request' && command === 'get-app-config') {
                    callback({ success: true, data: initialPayload });
                    return;
                }
                if (event === 'data_submission' && command === 'update-app-config') {
                    callback({ success: true, data: updatedPayload });
                }
            }),
        };

        render(<AppSettingsForm />);

        await screen.findByLabelText('Host');
        expect(screen.getByRole('heading', { name: 'Application Settings' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Reload' })).toBeInTheDocument();
        expect(screen.getByText('2 settings')).toBeInTheDocument();
        expect(screen.getByText('CLI override active')).toBeInTheDocument();

        fireEvent.change(screen.getByLabelText('Host'), {
            target: { value: '127.0.0.1' },
        });
        expect(screen.getAllByText('Unsaved changes').length).toBeGreaterThan(0);
        fireEvent.click(screen.getByRole('button', { name: 'Save Settings' }));

        await screen.findByRole('button', { name: 'Open Maintenance' });

        const submissionCall = socketValue.emit.mock.calls.find(
            (call) => call[0] === 'data_submission' && call[1] === 'update-app-config'
        );
        expect(submissionCall).toBeTruthy();
        expect(submissionCall[2]).toEqual({ values: { host: '127.0.0.1' } });
        expect(toastSuccessMock).toHaveBeenCalled();

        fireEvent.click(screen.getByRole('button', { name: 'Open Maintenance' }));
        expect(navigateMock).toHaveBeenCalledWith('/settings/maintenance?mtab=system-control');
    });

    it('renders backend validation errors when save fails', async () => {
        const initialPayload = buildPayload();

        socketValue = {
            emit: vi.fn((event, command, data, callback) => {
                if (event === 'data_request' && command === 'get-app-config') {
                    callback({ success: true, data: initialPayload });
                    return;
                }
                if (event === 'data_submission' && command === 'update-app-config') {
                    callback({
                        success: false,
                        error: 'One or more settings are invalid',
                        data: {
                            validation_errors: {
                                port: 'Value must be <= 65535',
                            },
                        },
                    });
                }
            }),
        };

        render(<AppSettingsForm />);

        await screen.findByLabelText('Port');

        fireEvent.change(screen.getByLabelText('Port'), {
            target: { value: '99999' },
        });
        fireEvent.click(screen.getByRole('button', { name: 'Save Settings' }));

        await waitFor(() => {
            expect(screen.getByText('Value must be <= 65535')).toBeInTheDocument();
        });
        expect(toastErrorMock).toHaveBeenCalledWith('One or more settings are invalid');
    });

    it('groups fields by subsystem in section blocks', async () => {
        const initialPayload = buildPayload({ portApplyMode: 'hot' });

        socketValue = {
            emit: vi.fn((event, command, data, callback) => {
                if (event === 'data_request' && command === 'get-app-config') {
                    callback({ success: true, data: initialPayload });
                }
            }),
        };

        render(<AppSettingsForm />);

        await screen.findByLabelText('Host');
        expect(screen.getByRole('heading', { name: 'Network' })).toBeInTheDocument();
        expect(screen.getAllByText('Saved').length).toBeGreaterThan(0);
    });
});
