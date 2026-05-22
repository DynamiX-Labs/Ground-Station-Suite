import React, { useEffect, useMemo, useState } from 'react';
import {
    Box,
    Button,
    Dialog,
    DialogContent,
    DialogTitle,
    FormControlLabel,
    Paper,
    Stack,
    Switch,
    Typography,
} from '@mui/material';
import { useDispatch } from 'react-redux';
import { useTranslation } from 'react-i18next';
import {
    DEFAULT_SOLAR_SYSTEM_DISPLAY_OPTIONS,
    setSolarSystemDisplayOption,
} from './celestial-display-slice.jsx';

const DIALOG_PAPER_SX = {
    bgcolor: 'background.paper',
    border: (theme) => `1px solid ${theme.palette.divider}`,
    borderRadius: 2,
};

const DIALOG_TITLE_SX = {
    bgcolor: (theme) => (theme.palette.mode === 'dark' ? 'grey.900' : 'grey.100'),
    borderBottom: (theme) => `1px solid ${theme.palette.divider}`,
    fontSize: '1.125rem',
    fontWeight: 'bold',
    py: 2.2,
};

const DIALOG_CONTENT_SX = {
    p: 0,
    height: '72vh',
    maxHeight: '72vh',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
};

const SETTING_KEYS = Object.keys(DEFAULT_SOLAR_SYSTEM_DISPLAY_OPTIONS);

const SECTION_DEFS = [
    {
        title: 'Scene Elements',
        subtitle: 'Primary solar system layers and labels.',
        options: [
            { key: 'showGrid', label: 'Show grid' },
            { key: 'showPlanets', label: 'Show planets' },
            { key: 'showPlanetLabels', label: 'Show planet labels' },
            { key: 'showPlanetOrbits', label: 'Show planet orbits' },
        ],
    },
    {
        title: 'Tracked Targets',
        subtitle: 'Tracked objects and their orbit/label overlays.',
        options: [
            { key: 'showTrackedObjects', label: 'Show tracked objects' },
            { key: 'showTrackedOrbits', label: 'Show tracked orbits' },
            { key: 'showTrackedLabels', label: 'Show tracked labels' },
        ],
    },
    {
        title: 'Guides and Metadata',
        subtitle: 'Contextual markers, labels, and scene metadata.',
        options: [
            { key: 'showAsteroidZones', label: 'Show asteroid zones' },
            { key: 'showZoneLabels', label: 'Show asteroid zone labels' },
            { key: 'showResonanceMarkers', label: 'Show resonance markers' },
            { key: 'showTimestamp', label: 'Show epoch label' },
            { key: 'showScaleIndicator', label: 'Show scale label' },
            { key: 'showGestureHint', label: 'Show gesture hint' },
        ],
    },
];

const buildSettings = (initialOptions) => {
    const settings = {};
    SETTING_KEYS.forEach((key) => {
        settings[key] = Boolean(initialOptions?.[key] ?? DEFAULT_SOLAR_SYSTEM_DISPLAY_OPTIONS[key]);
    });
    return settings;
};

const settingsEqual = (left, right) => SETTING_KEYS.every((key) => left[key] === right[key]);

const SectionBlock = ({ title, subtitle, children }) => (
    <Paper
        variant="outlined"
        sx={{
            borderColor: 'divider',
            borderRadius: 1.5,
            p: 1.5,
            bgcolor: 'background.paper',
        }}
    >
        <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
            {title}
        </Typography>
        {subtitle ? (
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.4, mb: 1.25 }}>
                {subtitle}
            </Typography>
        ) : null}
        <Stack spacing={1.1}>{children}</Stack>
    </Paper>
);

const ToggleRow = ({ label, checked, onChange }) => (
    <FormControlLabel
        control={<Switch size="small" checked={checked} onChange={(event) => onChange(event.target.checked)} />}
        label={label}
        sx={{ ml: 0.2 }}
    />
);

function SolarSystemLayoutOptionsDialog({ open, initialOptions, onClose }) {
    const dispatch = useDispatch();
    const { t } = useTranslation('common');

    const initialSettings = useMemo(() => buildSettings(initialOptions), [initialOptions]);
    const [draftSettings, setDraftSettings] = useState(initialSettings);

    useEffect(() => {
        if (open) {
            setDraftSettings(initialSettings);
        }
    }, [open, initialSettings]);

    const isDirty = !settingsEqual(draftSettings, initialSettings);

    const handleCancel = () => {
        setDraftSettings(initialSettings);
        onClose?.();
    };

    const handleApply = () => {
        // Commit only changed keys to keep Redux updates focused and predictable.
        SETTING_KEYS.forEach((key) => {
            if (draftSettings[key] !== initialSettings[key]) {
                dispatch(
                    setSolarSystemDisplayOption({
                        key,
                        value: draftSettings[key],
                    }),
                );
            }
        });
        onClose?.();
    };

    return (
        <Dialog
            open={open}
            onClose={handleCancel}
            fullWidth
            maxWidth="sm"
            PaperProps={{ sx: DIALOG_PAPER_SX }}
        >
            <DialogTitle sx={DIALOG_TITLE_SX}>
                {t('map_settings.solar_system_layout_options_title', { defaultValue: 'Solar System Layout Options' })}
            </DialogTitle>
            <DialogContent sx={DIALOG_CONTENT_SX}>
                <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
                    <Box sx={{ flex: 1, minHeight: 0, overflowY: 'auto', px: 2, pt: 2, pb: 1.5 }}>
                        <Stack spacing={1.5}>
                            {SECTION_DEFS.map((section) => (
                                <SectionBlock key={section.title} title={section.title} subtitle={section.subtitle}>
                                    {section.options.map((option) => (
                                        <ToggleRow
                                            key={option.key}
                                            label={option.label}
                                            checked={Boolean(draftSettings[option.key])}
                                            onChange={(value) => {
                                                setDraftSettings((current) => ({
                                                    ...current,
                                                    [option.key]: value,
                                                }));
                                            }}
                                        />
                                    ))}
                                </SectionBlock>
                            ))}
                        </Stack>
                    </Box>

                    <Box
                        sx={{
                            flexShrink: 0,
                            px: 2,
                            py: 1.5,
                            bgcolor: 'background.paper',
                            borderTop: '1px solid',
                            borderColor: 'divider',
                        }}
                    >
                        <Stack
                            direction={{ xs: 'column', sm: 'row' }}
                            spacing={1}
                            alignItems={{ xs: 'stretch', sm: 'center' }}
                            justifyContent="space-between"
                        >
                            <Button
                                variant="text"
                                onClick={() => {
                                    setDraftSettings({ ...DEFAULT_SOLAR_SYSTEM_DISPLAY_OPTIONS });
                                }}
                            >
                                {t('map_settings.reset_defaults', { defaultValue: 'Reset Defaults' })}
                            </Button>

                            <Stack direction="row" spacing={1} alignItems="center" justifyContent="flex-end">
                                <Button variant="outlined" onClick={handleCancel}>
                                    {t('close', { defaultValue: 'Close' })}
                                </Button>
                                <Button variant="contained" onClick={handleApply} disabled={!isDirty}>
                                    {t('map_settings.apply', { defaultValue: 'Apply' })}
                                </Button>
                            </Stack>
                        </Stack>
                    </Box>
                </Box>
            </DialogContent>
        </Dialog>
    );
}

export default SolarSystemLayoutOptionsDialog;
