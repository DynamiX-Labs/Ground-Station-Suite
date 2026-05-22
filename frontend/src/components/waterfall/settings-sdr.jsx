import React from 'react';
import {
    Accordion,
    AccordionSummary,
    AccordionDetails,
    LoadingOverlay,
} from './settings-elements.jsx';
import Typography from '@mui/material/Typography';
import {
    Box,
    FormControl,
    FormControlLabel,
    FormHelperText,
    IconButton,
    InputLabel,
    ListSubheader,
    MenuItem,
    Select,
    Switch,
    Tooltip,
} from "@mui/material";
import RefreshIcon from '@mui/icons-material/Refresh';
import { useTranslation } from 'react-i18next';

const SdrAccordion = ({
                          expanded,
                          onAccordionChange,
                          gettingSDRParameters,
                          isStreaming,
                          sdrs,
                          selectedSDRId,
                          onSDRChange,
                          onRefreshParameters,
                          gainValues,
                          localGain,
                          onGainChange,
                          sampleRateValues,
                          localSampleRate,
                          onSampleRateChange,
                          antennasList,
                          selectedAntenna,
                          onAntennaChange,
                          sdrCapabilities,
                          sdrSettings,
                          hasBiasT,
                          biasT,
                          onBiasTChange,
                          onBitpackChange,
                          onClockSourceChange,
                          onTimeSourceChange,
                          hasTunerAgc,
                          tunerAgc,
                          onTunerAgcChange,
                          hasSoapyAgc,
                          soapyAgc,
                          onSoapyAgcChange,
                          hasRtlAgc,
                          rtlAgc,
                          onRtlAgcChange,
                          onGainElementChange,
                          isRecording,
                          startStreamValidationErrors,
}) => {
    const { t } = useTranslation('waterfall');
    const selectedCapabilities = sdrCapabilities?.[selectedSDRId] || null;
    const biasTSupported = hasBiasT || selectedCapabilities?.bias_t?.supported;
    const isNoneSourceOption = (source) =>
        typeof source === 'string' && source.trim().toLowerCase() === 'none';
    const clockSourceOptions = Array.isArray(selectedCapabilities?.clock_sources)
        ? selectedCapabilities.clock_sources.filter((source) => !isNoneSourceOption(source))
        : [];
    const timeSourceOptions = Array.isArray(selectedCapabilities?.time_sources)
        ? selectedCapabilities.time_sources.filter((source) => !isNoneSourceOption(source))
        : [];
    const selectedClockSource =
        sdrSettings?.clockSource ?? selectedCapabilities?.clock_source ?? 'none';
    const selectedTimeSource =
        sdrSettings?.timeSource ?? selectedCapabilities?.time_source ?? 'none';

    const formatList = (values) => {
        if (!values || !Array.isArray(values) || values.length === 0) {
            return '—';
        }
        return values.join(', ');
    };

    const bitpackSetting = Array.isArray(selectedCapabilities?.settings)
        ? selectedCapabilities.settings.find(
            (setting) =>
                (setting?.key || '').toLowerCase() === 'bitpack' ||
                (setting?.name || '').toLowerCase().includes('bit pack')
        )
        : null;
    const hasBitpack = Boolean(bitpackSetting);

    const refLockValue = selectedCapabilities?.sensor_values?.ref_locked;
    const hasRefLockSensor =
        refLockValue !== undefined ||
        (Array.isArray(selectedCapabilities?.sensors) &&
            selectedCapabilities.sensors.includes('ref_locked'));
    const temperatureEntries = selectedCapabilities?.sensor_values
        ? Object.entries(selectedCapabilities.sensor_values).filter(([key]) =>
            key.toLowerCase().includes('temp')
        )
        : [];

    const formatHz = (value) => {
        if (value == null || Number.isNaN(value)) {
            return '—';
        }
        if (value >= 1000000) {
            return `${(value / 1000000).toFixed(value % 1000000 === 0 ? 0 : 3)} MHz`;
        }
        return `${(value / 1000).toFixed(value % 1000 === 0 ? 0 : 3)} kHz`;
    };

    const formatBandwidthRange = (values) => {
        if (!values || !Array.isArray(values) || values.length === 0) {
            return '—';
        }
        const min = Math.min(...values);
        const max = Math.max(...values);
        if (!Number.isFinite(min) || !Number.isFinite(max)) {
            return '—';
        }
        return `${formatHz(min)} – ${formatHz(max)}`;
    };

    const gainRangeEntries = selectedCapabilities?.gain_ranges?.rx
        ? Object.entries(selectedCapabilities.gain_ranges.rx)
        : [];
    const gainElementNames = Array.isArray(selectedCapabilities?.gain_elements?.rx)
        ? selectedCapabilities.gain_elements.rx
        : [];
    const filteredGainRangeEntries =
        gainElementNames.length > 0
            ? gainRangeEntries.filter(([name]) => gainElementNames.includes(name))
            : gainRangeEntries;

    const buildGainOptions = (min, max, step) => {
        if (step == null || step <= 0) {
            return [];
        }
        const options = [];
        let current = min;
        let guard = 0;
        const maxOptions = 200;
        while (current <= max && guard < maxOptions) {
            options.push(Number(current.toFixed(6)));
            current += step;
            guard += 1;
        }
        return options;
    };

    const gainRequiredError = Boolean(startStreamValidationErrors?.gain);
    const sampleRateRequiredError = Boolean(startStreamValidationErrors?.sampleRate);
    const antennaRequiredError = Boolean(startStreamValidationErrors?.antenna);

    return (
        <Accordion expanded={expanded} onChange={onAccordionChange}>
            <AccordionSummary
                sx={{
                    boxShadow: '-1px 4px 7px #00000059',
                }}
                aria-controls="panel3d-content" id="panel3d-header">
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
                    <Typography component="span">{t('sdr.title')}</Typography>
                    <Tooltip title={t('sdr.refresh_params')}>
                        <span>
                            <IconButton
                                component="span"
                                size="small"
                                aria-label={t('sdr.refresh_params')}
                                onClick={(event) => {
                                    event.preventDefault();
                                    event.stopPropagation();
                                    onRefreshParameters?.();
                                }}
                                disabled={gettingSDRParameters || selectedSDRId === 'none'}
                                sx={{ opacity: 0.7, p: 0.5, mr: 0.5 }}
                            >
                                <RefreshIcon sx={{ fontSize: '1rem' }} />
                            </IconButton>
                        </span>
                    </Tooltip>
                </Box>
            </AccordionSummary>
            <AccordionDetails sx={{
                backgroundColor: 'background.elevated',
            }}>
                <LoadingOverlay loading={gettingSDRParameters}>
                    <Box sx={{mb: 2}}>

                        <FormControl disabled={isStreaming} margin="normal"
                                     sx={{minWidth: 200, marginTop: 0, marginBottom: 1}} fullWidth
                                     variant="outlined"
                                     size="small">
                            <InputLabel htmlFor="sdr-select">{t('sdr.sdr_label')}</InputLabel>
                            <Select
                                id="sdr-select"
                                value={sdrs.length > 0 ? selectedSDRId : "none"}
                                onChange={onSDRChange}
                                size="small"
                                label={t('sdr.sdr_label')}>
                                <MenuItem value="none" disabled={isStreaming}>
                                    {t('sdr.no_sdr_selected')}
                                </MenuItem>
                                {/* Local SDRs */}
                                {sdrs.filter(sdr => sdr.type.toLowerCase().includes('local')).length > 0 && (
                                    <ListSubheader>{t('sdr.local_sdrs')}</ListSubheader>
                                )}
                                {sdrs
                                    .filter(sdr => sdr.type.toLowerCase().includes('local'))
                                    .map((sdr, index) => {
                                        return <MenuItem value={sdr.id} key={`local-${index}`}>
                                            {sdr.name} ({sdr.type})
                                        </MenuItem>;
                                    })
                                }

                                {/* Remote SDRs */}
                                {sdrs.filter(sdr => sdr.type.toLowerCase().includes('remote')).length > 0 && (
                                    <ListSubheader>{t('sdr.remote_sdrs')}</ListSubheader>
                                )}
                                {sdrs
                                    .filter(sdr => sdr.type.toLowerCase().includes('remote'))
                                    .map((sdr, index) => {
                                        return <MenuItem value={sdr.id} key={`remote-${index}`}>
                                            {sdr.name} ({sdr.type})
                                        </MenuItem>;
                                    })
                                }

                                {/* Other SDRs (neither local nor remote) */}
                                {sdrs.filter(sdr => !sdr.type.toLowerCase().includes('local') && !sdr.type.toLowerCase().includes('remote')).length > 0 && (
                                    <ListSubheader>{t('sdr.other_sdrs')}</ListSubheader>
                                )}
                                {sdrs
                                    .filter(sdr => !sdr.type.toLowerCase().includes('local') && !sdr.type.toLowerCase().includes('remote'))
                                    .map((sdr, index) => {
                                        return <MenuItem value={sdr.id} key={`other-${index}`}>
                                            {sdr.name} ({sdr.type})
                                        </MenuItem>;
                                    })
                                }
                            </Select>
                        </FormControl>

                        <FormControl disabled={gettingSDRParameters || (selectedSDRId === 'sigmf-playback' && isStreaming)}
                                     error={gainRequiredError}
                                     sx={{minWidth: 200, marginTop: 0, marginBottom: 1}}
                                     fullWidth={true}
                                     variant="outlined" size="small">
                            <InputLabel>{t('sdr.gain_db')}</InputLabel>
                            <Select
                                disabled={gettingSDRParameters || (selectedSDRId === 'sigmf-playback' && isStreaming)}
                                size={'small'}
                                label={t('sdr.gain_db')}
                                value={gainValues.length ? localGain : "none"}
                                onChange={(e) => onGainChange(e.target.value)}>
                                <MenuItem value="none" disabled={isStreaming}>
                                    {t('sdr.no_gain_selected')}
                                </MenuItem>
                                {gainValues.map(gain => (
                                    <MenuItem key={gain} value={gain}>
                                        {gain} dB
                                    </MenuItem>
                                ))}
                            </Select>
                            {gainRequiredError && (
                                <FormHelperText>
                                    {t('sdr.gain_required', { defaultValue: 'Select gain before starting stream' })}
                                </FormHelperText>
                            )}
                        </FormControl>
                        {filteredGainRangeEntries.length > 0 && (
                            <Box sx={{mb: 1, display: 'grid', gap: 1}}>
                                {filteredGainRangeEntries.map(([name, range]) => {
                                    const options = buildGainOptions(
                                        range.min,
                                        range.max,
                                        range.step
                                    );
                                    if (options.length === 0) {
                                        return null;
                                    }
                                    return (
                                        <FormControl
                                            key={`gain-${name}`}
                                            disabled={gettingSDRParameters}
                                            fullWidth
                                            variant="outlined"
                                            size="small"
                                        >
                                            <InputLabel>{`Gain ${name}`}</InputLabel>
                                            <Select
                                                size="small"
                                                label={`Gain ${name}`}
                                                value={
                                                    sdrSettings?.gains?.[name] ??
                                                    "none"
                                                }
                                                onChange={(e) => {
                                                    const nextValue =
                                                        e.target.value === "none"
                                                            ? null
                                                            : e.target.value;
                                                    onGainElementChange?.(name, nextValue);
                                                }}
                                            >
                                                <MenuItem value="none" disabled={isStreaming}>
                                                    [not configured]
                                                </MenuItem>
                                                {options.map((option) => (
                                                    <MenuItem key={`${name}-${option}`} value={option}>
                                                        {option} dB
                                                    </MenuItem>
                                                ))}
                                            </Select>
                                        </FormControl>
                                    );
                                })}
                            </Box>
                        )}
                        <FormControl disabled={gettingSDRParameters || isRecording || (selectedSDRId === 'sigmf-playback' && isStreaming)}
                                     error={sampleRateRequiredError}
                                     sx={{minWidth: 200, marginTop: 0, marginBottom: 1}}
                                     fullWidth={true}
                                     variant="outlined" size="small">
                            <InputLabel>{t('sdr.sample_rate')}</InputLabel>
                            <Select
                                disabled={gettingSDRParameters || isRecording || (selectedSDRId === 'sigmf-playback' && isStreaming)}
                                size="small"
                                value={sampleRateValues.includes(localSampleRate) ? localSampleRate : "none"}
                                onChange={(e) => onSampleRateChange(e.target.value)}
                                label={t('sdr.sample_rate')}>
                                <MenuItem value="none" disabled={isStreaming}>
                                    {t('sdr.no_rate_selected')}
                                </MenuItem>
                                {sampleRateValues.map(rate => {
                                    // Format the sample rate for display
                                    let displayValue;
                                    if (rate >= 1000000) {
                                        displayValue = `${(rate / 1000000).toFixed(rate % 1000000 === 0 ? 0 : 3)} MHz`;
                                    } else {
                                        displayValue = `${(rate / 1000).toFixed(rate % 1000 === 0 ? 0 : 3)} kHz`;
                                    }
                                    return (
                                        <MenuItem key={rate} value={rate}>
                                            {displayValue}
                                        </MenuItem>
                                    );
                                })}
                            </Select>
                            {sampleRateRequiredError && (
                                <FormHelperText>
                                    {t('sdr.sample_rate_required', { defaultValue: 'Select sample rate before starting stream' })}
                                </FormHelperText>
                            )}
                        </FormControl>
                        <FormControl disabled={gettingSDRParameters || isRecording || (selectedSDRId === 'sigmf-playback' && isStreaming)}
                                     error={antennaRequiredError}
                                     sx={{minWidth: 200, marginTop: 0, marginBottom: 1}}
                                     fullWidth={true}
                                     variant="outlined" size="small">
                            <InputLabel>{t('sdr.antenna')}</InputLabel>
                            <Select
                                disabled={gettingSDRParameters || isRecording || (selectedSDRId === 'sigmf-playback' && isStreaming)}
                                size="small"
                                value={antennasList.rx.includes(selectedAntenna) ? selectedAntenna : "none"}
                                onChange={(e) => onAntennaChange(e.target.value)}
                                label={t('sdr.antenna')}>
                                <MenuItem value="none" disabled={isStreaming}>
                                    {t('sdr.no_antenna_selected')}
                                </MenuItem>
                                {antennasList.rx && antennasList.rx.map(antenna => (
                                    <MenuItem key={antenna} value={antenna}>
                                        {antenna}
                                    </MenuItem>
                                ))}
                            </Select>
                            {antennaRequiredError && (
                                <FormHelperText>
                                    {t('sdr.antenna_required', { defaultValue: 'Select antenna before starting stream' })}
                                </FormHelperText>
                            )}
                        </FormControl>
                        {clockSourceOptions.length > 0 && (
                            <FormControl
                                disabled={
                                    gettingSDRParameters ||
                                    isRecording ||
                                    (selectedSDRId === 'sigmf-playback' && isStreaming)
                                }
                                sx={{minWidth: 200, marginTop: 0, marginBottom: 1}}
                                fullWidth={true}
                                variant="outlined"
                                size="small"
                            >
                                <InputLabel>Clock Source</InputLabel>
                                <Select
                                    size="small"
                                    label="Clock Source"
                                    value={
                                        clockSourceOptions.includes(selectedClockSource)
                                            ? selectedClockSource
                                            : 'none'
                                    }
                                    onChange={(e) => onClockSourceChange?.(e.target.value)}
                                >
                                    <MenuItem value="none" disabled={isStreaming}>
                                        [not configured]
                                    </MenuItem>
                                    {clockSourceOptions.map((source) => (
                                        <MenuItem key={source} value={source}>
                                            {source}
                                        </MenuItem>
                                    ))}
                                </Select>
                            </FormControl>
                        )}
                        {timeSourceOptions.length > 0 && (
                            <FormControl
                                disabled={
                                    gettingSDRParameters ||
                                    isRecording ||
                                    (selectedSDRId === 'sigmf-playback' && isStreaming)
                                }
                                sx={{minWidth: 200, marginTop: 0, marginBottom: 1}}
                                fullWidth={true}
                                variant="outlined"
                                size="small"
                            >
                                <InputLabel>Time Source</InputLabel>
                                <Select
                                    size="small"
                                    label="Time Source"
                                    value={
                                        timeSourceOptions.includes(selectedTimeSource)
                                            ? selectedTimeSource
                                            : 'none'
                                    }
                                    onChange={(e) => onTimeSourceChange?.(e.target.value)}
                                >
                                    <MenuItem value="none" disabled={isStreaming}>
                                        [not configured]
                                    </MenuItem>
                                    {timeSourceOptions.map((source) => (
                                        <MenuItem key={source} value={source}>
                                            {source}
                                        </MenuItem>
                                    ))}
                                </Select>
                            </FormControl>
                        )}
                    </Box>

                    <Box sx={{mb: 0, ml: 1.5}}>
                        {biasTSupported && (
                            <FormControlLabel
                                control={
                                    <Switch
                                        disabled={gettingSDRParameters}
                                        size={'small'}
                                        checked={biasT}
                                        onChange={(e) => onBiasTChange(e.target.checked)}
                                    />
                                }
                                label={t('sdr.enable_bias_t')}
                            />
                        )}
                        {hasBitpack && (
                            <FormControlLabel
                                control={
                                    <Switch
                                        disabled={gettingSDRParameters}
                                        size={'small'}
                                        checked={Boolean(
                                            sdrSettings?.bitpack ?? bitpackSetting?.value
                                        )}
                                        onChange={(e) => onBitpackChange?.(e.target.checked)}
                                    />
                                }
                                label="Bit Packing"
                            />
                        )}
                        {hasTunerAgc && (
                            <FormControlLabel
                                control={
                                    <Switch
                                        disabled={gettingSDRParameters}
                                        size={'small'}
                                        checked={tunerAgc}
                                        onChange={(e) => onTunerAgcChange(e.target.checked)}
                                    />
                                }
                                label={t('sdr.enable_tuner_agc')}
                            />
                        )}
                        {hasSoapyAgc && (
                            <FormControlLabel
                                control={
                                    <Switch
                                        disabled={gettingSDRParameters}
                                        size={'small'}
                                        checked={soapyAgc}
                                        onChange={(e) => onSoapyAgcChange(e.target.checked)}
                                    />
                                }
                                label={t('sdr.enable_agc')}
                            />
                        )}
                        {hasRtlAgc && (
                            <FormControlLabel
                                control={
                                    <Switch
                                        disabled={gettingSDRParameters}
                                        size={'small'}
                                        checked={rtlAgc}
                                        onChange={(e) => onRtlAgcChange(e.target.checked)}
                                    />
                                }
                                label={t('sdr.enable_rtl_agc')}
                            />
                        )}
                    </Box>

                    {selectedCapabilities && (
                        <Box sx={{mt: 2}}>
                            <Box
                                sx={{
                                    display: 'grid',
                                    gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                                    gap: 0.5,
                                }}
                            >
                                {hasRefLockSensor && (
                                    <Box
                                        sx={{
                                            px: 0.75,
                                            py: 0.25,
                                            borderRadius: 1,
                                            bgcolor: 'transparent',
                                        }}
                                    >
                                        <Box sx={{display: 'flex', justifyContent: 'space-between', gap: 1}}>
                                            <Typography variant="caption" color="text.secondary">
                                                Ref Clock Lock
                                            </Typography>
                                            <Box
                                                sx={{
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: 0.5,
                                                    fontFamily: 'monospace',
                                                }}
                                            >
                                                <Box
                                                    sx={{
                                                        width: 8,
                                                        height: 8,
                                                        borderRadius: '50%',
                                                        bgcolor:
                                                            refLockValue === true
                                                                ? 'success.main'
                                                                : refLockValue === false
                                                                    ? 'error.main'
                                                                    : 'text.disabled',
                                                        boxShadow:
                                                            refLockValue === true
                                                                ? '0 0 6px rgba(76, 175, 80, 0.6)'
                                                                : refLockValue === false
                                                                    ? '0 0 6px rgba(244, 67, 54, 0.6)'
                                                                    : 'none',
                                                    }}
                                                />
                                                <Typography variant="caption" sx={{fontFamily: 'monospace'}}>
                                                    {refLockValue === true
                                                        ? 'Locked'
                                                        : refLockValue === false
                                                            ? 'Unlocked'
                                                            : '—'}
                                                </Typography>
                                            </Box>
                                        </Box>
                                    </Box>
                                )}
                                {temperatureEntries.length > 0 && (
                                    <Box
                                        sx={{
                                            px: 0.75,
                                            py: 0.25,
                                            borderRadius: 1,
                                            bgcolor: 'transparent',
                                            border: '1px solid',
                                            borderColor: 'divider',
                                        }}
                                    >
                                        <Box sx={{display: 'flex', justifyContent: 'space-between', gap: 1}}>
                                            <Typography variant="caption" color="text.secondary">
                                                Temperature
                                            </Typography>
                                            <Typography
                                                variant="caption"
                                                sx={{fontFamily: 'monospace'}}
                                            >
                                                {(() => {
                                                    const [, value] = temperatureEntries[0];
                                                    const numeric = typeof value === 'number'
                                                        ? value
                                                        : parseFloat(value);
                                                    if (Number.isFinite(numeric)) {
                                                        return numeric.toFixed(1);
                                                    }
                                                    return value ?? '—';
                                                })()}
                                            </Typography>
                                        </Box>
                                    </Box>
                                )}
                            </Box>

                        </Box>
                    )}
                </LoadingOverlay>
            </AccordionDetails>
        </Accordion>
    );
};

function areSdrAccordionPropsEqual(prevProps, nextProps) {
    return (
        prevProps.expanded === nextProps.expanded &&
        prevProps.onAccordionChange === nextProps.onAccordionChange &&
        prevProps.gettingSDRParameters === nextProps.gettingSDRParameters &&
        prevProps.isStreaming === nextProps.isStreaming &&
        prevProps.sdrs === nextProps.sdrs &&
        prevProps.selectedSDRId === nextProps.selectedSDRId &&
        prevProps.onSDRChange === nextProps.onSDRChange &&
        prevProps.onRefreshParameters === nextProps.onRefreshParameters &&
        prevProps.gainValues === nextProps.gainValues &&
        prevProps.localGain === nextProps.localGain &&
        prevProps.onGainChange === nextProps.onGainChange &&
        prevProps.sampleRateValues === nextProps.sampleRateValues &&
        prevProps.localSampleRate === nextProps.localSampleRate &&
        prevProps.onSampleRateChange === nextProps.onSampleRateChange &&
        prevProps.antennasList === nextProps.antennasList &&
        prevProps.selectedAntenna === nextProps.selectedAntenna &&
        prevProps.onAntennaChange === nextProps.onAntennaChange &&
        prevProps.sdrCapabilities === nextProps.sdrCapabilities &&
        prevProps.sdrSettings === nextProps.sdrSettings &&
        prevProps.hasBiasT === nextProps.hasBiasT &&
        prevProps.biasT === nextProps.biasT &&
        prevProps.onBiasTChange === nextProps.onBiasTChange &&
        prevProps.onBitpackChange === nextProps.onBitpackChange &&
        prevProps.onClockSourceChange === nextProps.onClockSourceChange &&
        prevProps.onTimeSourceChange === nextProps.onTimeSourceChange &&
        prevProps.hasTunerAgc === nextProps.hasTunerAgc &&
        prevProps.tunerAgc === nextProps.tunerAgc &&
        prevProps.onTunerAgcChange === nextProps.onTunerAgcChange &&
        prevProps.hasSoapyAgc === nextProps.hasSoapyAgc &&
        prevProps.soapyAgc === nextProps.soapyAgc &&
        prevProps.onSoapyAgcChange === nextProps.onSoapyAgcChange &&
        prevProps.hasRtlAgc === nextProps.hasRtlAgc &&
        prevProps.rtlAgc === nextProps.rtlAgc &&
        prevProps.onRtlAgcChange === nextProps.onRtlAgcChange &&
        prevProps.onGainElementChange === nextProps.onGainElementChange &&
        prevProps.isRecording === nextProps.isRecording &&
        prevProps.startStreamValidationErrors === nextProps.startStreamValidationErrors
    );
}

export default React.memo(SdrAccordion, areSdrAccordionPropsEqual);
