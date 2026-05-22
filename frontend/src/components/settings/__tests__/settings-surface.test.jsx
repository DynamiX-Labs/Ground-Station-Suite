import React from 'react';
import { describe, expect, it, vi } from 'vitest';
import { Button, Chip } from '@mui/material';
import { render, screen } from '@testing-library/react';
import {
    SettingsActionFooter,
    SettingsMetaRow,
    SettingsSection,
    SettingsSurface,
    SettingsSurfaceHeader,
} from '../shared/index.js';

describe('settings-surface shared primitives', () => {
    it('renders a header with status chip and reload action', () => {
        const onReload = vi.fn();

        render(
            <SettingsSurface>
                <SettingsSurfaceHeader
                    title="Application Settings"
                    subtitle="Edit backend configuration"
                    status={{ label: 'Saved', color: 'success' }}
                    onReload={onReload}
                    reloadLabel="Reload"
                />
            </SettingsSurface>
        );

        expect(screen.getByRole('heading', { name: 'Application Settings' })).toBeInTheDocument();
        expect(screen.getByText('Edit backend configuration')).toBeInTheDocument();
        expect(screen.getByText('Saved')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Reload' })).toBeInTheDocument();
    });

    it('renders section/meta/footer primitives with stable actions', () => {
        render(
            <SettingsSurface>
                <SettingsSection title="General">
                    <SettingsMetaRow>
                        <Chip size="small" label="Config File" />
                    </SettingsMetaRow>
                </SettingsSection>
                <SettingsActionFooter statusText="Unsaved changes">
                    <Button>Reset</Button>
                    <Button variant="contained">Save Settings</Button>
                </SettingsActionFooter>
            </SettingsSurface>
        );

        expect(screen.getByRole('heading', { name: 'General' })).toBeInTheDocument();
        expect(screen.getByText('Config File')).toBeInTheDocument();
        expect(screen.getByRole('status')).toHaveTextContent('Unsaved changes');
        expect(screen.getByRole('button', { name: 'Reset' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Save Settings' })).toBeInTheDocument();
    });
});
