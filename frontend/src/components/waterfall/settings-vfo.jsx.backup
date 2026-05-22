    import React from 'react';
import {
    Accordion,
    AccordionSummary,
    AccordionDetails,
} from './settings-elements.jsx';
import Typography from '@mui/material/Typography';
import {
    Box,
    FormControlLabel,
    Slider,
    Switch,
    Tab,
    Tabs,
    Stack,
    ToggleButtonGroup,
    ToggleButton,
    Alert,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    Dialog,
    DialogTitle,
    DialogContent,
    IconButton,
    Link,
    Chip,
    Button,
    Tooltip,
} from "@mui/material";
import VolumeDown from '@mui/icons-material/VolumeDown';
import VolumeUp from '@mui/icons-material/VolumeUp';
import VolumeUpIcon from '@mui/icons-material/VolumeUp';
import VolumeOffIcon from '@mui/icons-material/VolumeOff';
import VolumeMuteIcon from '@mui/icons-material/VolumeMute';
import LockIcon from '@mui/icons-material/Lock';
import LockOpenIcon from '@mui/icons-material/LockOpen';
import CloseIcon from '@mui/icons-material/Close';
import SettingsIcon from '@mui/icons-material/Settings';
// import TranscribeIcon from '@mui/icons-material/Transcribe';
import LCDFrequencyDisplay from "../common/lcd-frequency-display.jsx";
import RotaryEncoder from "./rotator-encoder.jsx";
import {SquelchIcon, SquelchIconCentered} from "../common/dataurl-icons.jsx";
import { useTranslation } from 'react-i18next';
import { useSelector } from 'react-redux';
import TransmittersTable from '../satellites/transmitters-table.jsx';
import { isLockedBandwidth, getDecoderConfig, getDecoderParameters, normalizeTransmitterMode } from './vfo-config.js';
import DecoderParamsDialog from './decoder-params-dialog.jsx';
import { useAudio } from '../dashboard/audio-provider.jsx';

const BANDWIDTHS = {
    "500": "500 Hz",
    "1000": "1 kHz",
    "2100": "2.1 kHz",
    "2400": "2.4 kHz",
    "2500": "2.5 kHz",
    "2700": "2.7 kHz",
    "3000": "3 kHz",
    "3300": "3.3 kHz",
    "5000": "5 kHz",
    "6000": "6 kHz",
    "8000": "8 kHz",
    "10000": "10 kHz",
    "12500": "12.5 kHz",
    "15000": "15 kHz",
    "20000": "20 kHz",
    "25000": "25 kHz",
    "30000": "30 kHz",
    "50000": "50 kHz",
    "100000": "100 kHz",
    "150000": "150 kHz",
    "200000": "200 kHz",
    "250000": "250 kHz",
    "500000": "500 kHz"
};

const VfoAccordion = ({
                          expanded,
                          onAccordionChange,
                          selectedVFOTab,
                          onVFOTabChange,
                          vfoColors,
                          vfoMarkers,
                          vfoActive,
                          onVFOActiveChange,
                          onVFOPropertyChange,
                          selectedVFO,
                          onVFOListenChange,
                          onTranscriptionToggle,
                          geminiConfigured,
                          deepgramConfigured,
                      }) => {
    const { t } = useTranslation('waterfall');
    const squelchSliderRef = React.useRef(null);
    const volumeSliderRef = React.useRef(null);
    const [transmittersDialogOpen, setTransmittersDialogOpen] = React.useState(false);
    const [decoderParamsDialogOpen, setDecoderParamsDialogOpen] = React.useState(false);
    const [decoderParamsVfoIndex, setDecoderParamsVfoIndex] = React.useState(null);
    const [transcriptionParamsDialogOpen, setTranscriptionParamsDialogOpen] = React.useState(false);
    const [transcriptionParamsVfoIndex, setTranscriptionParamsVfoIndex] = React.useState(null);

    // Get audio controls for VFO muting, buffer monitoring, audio level, and RF power
    const { setVfoMute, getAudioBufferLength, getVfoAudioLevel, getVfoRfPower } = useAudio();

    // Track mute state for each VFO (0-3, but UI uses 1-4)
    const [vfoMuted, setVfoMuted] = React.useState({
        1: false,
        2: false,
        3: false,
        4: false
    });

    // Track audio buffer length per VFO
    const [vfoBufferLengths, setVfoBufferLengths] = React.useState({
        1: 0,
        2: 0,
        3: 0,
        4: 0
    });

    // Track audio levels per VFO
    const [vfoAudioLevels, setVfoAudioLevels] = React.useState({
        1: 0,
        2: 0,
        3: 0,
        4: 0
    });

    // Track RF power per VFO (in dB)
    const [vfoRfPower, setVfoRfPower] = React.useState({
        1: null,
        2: null,
        3: null,
        4: null
    });

    // Update buffer lengths, audio levels, and RF power every 500ms
    React.useEffect(() => {
        const interval = setInterval(() => {
            const newBufferLengths = {};
            const newAudioLevels = {};
            const newRfPower = {};
            for (let i = 1; i <= 4; i++) {
                newBufferLengths[i] = getAudioBufferLength(i);
                newAudioLevels[i] = getVfoAudioLevel(i);
                newRfPower[i] = getVfoRfPower(i);
            }
            setVfoBufferLengths(newBufferLengths);
            setVfoAudioLevels(newAudioLevels);
            setVfoRfPower(newRfPower);
        }, 500);
        return () => clearInterval(interval);
    }, [getAudioBufferLength, getVfoAudioLevel, getVfoRfPower]);

    // Handle VFO mute toggle
    const handleVfoMuteToggle = (vfoIndex) => {
        console.log('Mute button clicked for VFO', vfoIndex, 'Current state:', vfoMuted[vfoIndex]);
        const newMutedState = !vfoMuted[vfoIndex];
        console.log('Setting VFO', vfoIndex, 'to muted:', newMutedState);
        setVfoMuted(prev => ({
            ...prev,
            [vfoIndex]: newMutedState
        }));
        // Call audio provider to mute/unmute
        // Backend sends vfo_number as 1-4, which matches our vfoIndex
        console.log('Calling setVfoMute with VFO number:', vfoIndex, 'muted:', newMutedState);
        if (setVfoMute) {
            setVfoMute(vfoIndex, newMutedState);
        } else {
            console.error('setVfoMute is not available from audio context');
        }
    };

    // Get doppler-corrected transmitters from Redux state (includes alive field)
    const transmitters = useSelector(state => state.targetSatTrack.rigData.transmitters || []);

    // Get target satellite data
    const satelliteDetails = useSelector(state => state.targetSatTrack.satelliteData?.details || null);
    const satelliteTransmitters = useSelector(state => state.targetSatTrack.satelliteData?.transmitters || []);
    const targetSatelliteName = satelliteDetails?.name || '';

    // Get streaming VFOs from Redux state (array of currently streaming VFO numbers)
    const streamingVFOs = useSelector(state => state.vfo.streamingVFOs);

    // Get muted VFOs from Redux state
    const vfoMutedRedux = useSelector(state => state.vfo.vfoMuted || {});

    // Get active decoders from Redux state
    const activeDecoders = useSelector(state => state.decoders.active || {});
    const currentSessionId = useSelector(state => state.decoders.currentSessionId);

    // Get decoder info for a specific VFO (works for both data decoders and transcription)
    const getVFODecoderInfo = (vfoIndex) => {
        if (!currentSessionId || !vfoIndex) return null;
        const decoderKey = `${currentSessionId}_vfo${vfoIndex}`;
        return activeDecoders[decoderKey] || null;
    };

    // Format decoder parameters into short notation
    const formatDecoderParamsSummary = (vfoIndex) => {
        const vfo = vfoMarkers[vfoIndex];
        if (!vfo || !vfo.decoder || vfo.decoder === 'none') return '';

        const decoder = vfo.decoder;
        const params = vfo.parameters || {};

        // Helper to get framing shorthand
        const getFramingShort = (framing) => {
            const framingMap = {
                'ax25': 'AX25',
                'raw': 'RAW',
                'ccsds': 'CCSDS',
                'custom': 'CUST',
            };
            return framingMap[framing] || framing.toUpperCase();
        };

        if (decoder === 'lora') {
            const sf = params.lora_sf ?? 7;
            const bw = params.lora_bw ?? 125000;
            const cr = params.lora_cr ?? 1;
            const bwKhz = bw / 1000;
            return `SF${sf} BW${bwKhz}kHz CR4/${cr + 4}`;
        }

        // Helper to format baudrate compactly (e.g., 1k2bd, 9k6bd)
        const formatBaudrate = (baudrate) => {
            if (baudrate >= 1000) {
                const k = Math.floor(baudrate / 1000);
                const remainder = (baudrate % 1000) / 100;
                if (remainder === 0) {
                    return `${k}kbd`;
                }
                return `${k}k${remainder}bd`;
            }
            return `${baudrate}bd`;
        };

        if (decoder === 'fsk') {
            const baudrate = params.fsk_baudrate ?? 9600;
            const deviation = params.fsk_deviation ?? 5000;
            const framing = params.fsk_framing ?? 'ax25';
            const devKhz = deviation >= 1000 ? `${(deviation / 1000).toFixed(1)}k` : `${deviation}`;
            return `${formatBaudrate(baudrate)} ±${devKhz} ${getFramingShort(framing)}`;
        }

        if (decoder === 'gmsk') {
            const baudrate = params.gmsk_baudrate ?? 9600;
            const deviation = params.gmsk_deviation ?? 5000;
            const framing = params.gmsk_framing ?? 'ax25';
            const devKhz = deviation >= 1000 ? `${(deviation / 1000).toFixed(1)}k` : `${deviation}`;
            return `${formatBaudrate(baudrate)} ±${devKhz} ${getFramingShort(framing)}`;
        }

        if (decoder === 'gfsk') {
            const baudrate = params.gfsk_baudrate ?? 9600;
            const deviation = params.gfsk_deviation ?? 5000;
            const framing = params.gfsk_framing ?? 'ax25';
            const devKhz = deviation >= 1000 ? `${(deviation / 1000).toFixed(1)}k` : `${deviation}`;
            return `${formatBaudrate(baudrate)} ±${devKhz} ${getFramingShort(framing)}`;
        }

        if (decoder === 'bpsk') {
            const baudrate = params.bpsk_baudrate ?? 9600;
            const framing = params.bpsk_framing ?? 'ax25';
            const differential = params.bpsk_differential ?? false;
            return `${formatBaudrate(baudrate)} ${getFramingShort(framing)}${differential ? ' DIFF' : ''}`;
        }

        if (decoder === 'afsk') {
            const baudrate = params.afsk_baudrate ?? 1200;
            const af_carrier = params.afsk_af_carrier ?? 1700;
            const deviation = params.afsk_deviation ?? 500;
            const framing = params.afsk_framing ?? 'ax25';
            const carrierKhz = af_carrier >= 1000 ? `${(af_carrier / 1000).toFixed(1)}k` : `${af_carrier}`;
            return `${formatBaudrate(baudrate)} ${carrierKhz}Hz ±${deviation} ${getFramingShort(framing)}`;
        }

        // Default for decoders without parameters
        return 'Configure...';
    };

    // Combine details and transmitters for the TransmittersTable component
    const targetSatelliteData = satelliteDetails ? {
        ...satelliteDetails,
        transmitters: satelliteTransmitters
    } : null;

    React.useEffect(() => {
        const handleWheel = (e, vfoIndex, property, min, max, current) => {
            // Check if VFO is active before processing wheel event
            if (!vfoActive[vfoIndex]) {
                return;
            }
            e.preventDefault();
            const delta = e.deltaY > 0 ? -1 : 1;
            const newValue = Math.max(min, Math.min(max, current + delta));
            onVFOPropertyChange(vfoIndex, { [property]: newValue });
        };

        const squelchElements = document.querySelectorAll('[data-slider="squelch"]');
        const volumeElements = document.querySelectorAll('[data-slider="volume"]');

        squelchElements.forEach((el) => {
            const vfoIndex = parseInt(el.getAttribute('data-vfo-index'));
            const listener = (e) => handleWheel(e, vfoIndex, 'squelch', -150, 0, vfoMarkers[vfoIndex]?.squelch || -150);
            el.addEventListener('wheel', listener, { passive: false });
            el._wheelListener = listener;
        });

        volumeElements.forEach((el) => {
            const vfoIndex = parseInt(el.getAttribute('data-vfo-index'));
            const listener = (e) => handleWheel(e, vfoIndex, 'volume', 0, 100, vfoMarkers[vfoIndex]?.volume || 50);
            el.addEventListener('wheel', listener, { passive: false });
            el._wheelListener = listener;
        });

        return () => {
            squelchElements.forEach((el) => {
                if (el._wheelListener) {
                    el.removeEventListener('wheel', el._wheelListener);
                }
            });
            volumeElements.forEach((el) => {
                if (el._wheelListener) {
                    el.removeEventListener('wheel', el._wheelListener);
                }
            });
        };
    }, [vfoMarkers, vfoActive, onVFOPropertyChange]);

    return (
        <Accordion expanded={expanded} onChange={onAccordionChange}>
            <AccordionSummary
                sx={{
                    boxShadow: '-1px 4px 7px #00000059',
                }}
                aria-controls="vfo-content" id="vfo-header">
                <Typography component="span">{t('vfo.title')}</Typography>
            </AccordionSummary>
            <AccordionDetails sx={{
                backgroundColor: 'background.elevated',
            }}>
                <Tabs
                    value={selectedVFOTab}
                    onChange={(event, newValue) => onVFOTabChange(newValue)}
                    sx={{
                        minHeight: '32px',
                        '& .MuiTab-root': {
                            minHeight: '32px',
                            padding: '6px 12px'
                        },
                        '& .MuiTabs-indicator': {
                            backgroundColor: '#ffffffcc',
                        }
                    }}
                >
                    {[0, 1, 2, 3].map((index) => (
                        <Tab
                            key={index}
                            label={
                                <Box sx={{ position: 'relative', width: '100%', height: '100%' }}>
                                    {index + 1}
                                    {vfoMarkers[index + 1]?.lockedTransmitterId && vfoMarkers[index + 1]?.lockedTransmitterId !== 'none' && (
                                        <LockIcon
                                            sx={{
                                                position: 'absolute',
                                                top: -4,
                                                right: -8,
                                                fontSize: '0.75rem',
                                                pointerEvents: 'none',
                                            }}
                                        />
                                    )}
                                    {/* Audio icon with three states:
                                        1. Gray VolumeMute (no waves): No audio data reached browser
                                        2. Green VolumeMute (with slash): Audio reached, muted from UI
                                        3. Green VolumeUp (with waves): Audio reached and playing
                                    */}
                                    {!streamingVFOs.includes(index + 1) && (
                                        <VolumeMuteIcon
                                            sx={{
                                                position: 'absolute',
                                                bottom: -2,
                                                right: -6,
                                                fontSize: '0.75rem',
                                                pointerEvents: 'none',
                                                color: '#888888', // Gray for no audio
                                            }}
                                        />
                                    )}
                                    {streamingVFOs.includes(index + 1) && vfoMutedRedux[index + 1] && (
                                        <VolumeMuteIcon
                                            sx={{
                                                position: 'absolute',
                                                bottom: -2,
                                                right: -6,
                                                fontSize: '0.75rem',
                                                pointerEvents: 'none',
                                                color: '#00ff00', // Green for muted but streaming
                                            }}
                                        />
                                    )}
                                    {streamingVFOs.includes(index + 1) && !vfoMutedRedux[index + 1] && (
                                        <VolumeUpIcon
                                            sx={{
                                                position: 'absolute',
                                                bottom: -2,
                                                right: -6,
                                                fontSize: '0.75rem',
                                                pointerEvents: 'none',
                                                color: '#00ff00', // Green for playing
                                            }}
                                        />
                                    )}
                                    {/* Active VFO indicator (small status dot) */}
                                    {vfoActive[index + 1] && (
                                        <Box
                                            aria-label={`VFO ${index + 1} active`}
                                            sx={{
                                                position: 'absolute',
                                                top: -4,
                                                left: -8,
                                                width: 8,
                                                height: 8,
                                                borderRadius: '50%',
                                                bgcolor: 'success.main',
                                                boxShadow: 1,
                                            }}
                                        />
                                    )}
                                </Box>
                            }
                            sx={{
                                minWidth: '25%',
                                backgroundColor: `${vfoColors[index]}40`, // 40 = ~25% opacity in hex
                                '&.Mui-selected': {
                                    fontWeight: 'bold',
                                    borderBottom: 'none',
                                    color: 'text.primary',
                                },
                            }}
                        />
                    ))}

                </Tabs>
                {[1, 2, 3, 4].map((vfoIndex) => (
                    <Box key={vfoIndex} hidden={(selectedVFOTab + 1) !== vfoIndex}>
                        <Box sx={{ display: 'flex', gap: 1, flexDirection: 'column' }}>
                            <Box sx={{ display: 'flex', gap: 0.5, mt: 1 }}>
                                <Tooltip title={vfoActive[vfoIndex] ? "Deactivate VFO" : "Activate VFO"} arrow>
                                    <ToggleButton
                                        value="active"
                                        selected={vfoActive[vfoIndex]}
                                        onChange={() => onVFOActiveChange(vfoIndex, !vfoActive[vfoIndex])}
                                        sx={{
                                            flex: 1,
                                            height: '32px',
                                            fontSize: '0.8rem',
                                            border: '1px solid',
                                            borderColor: 'rgba(255, 255, 255, 0.23)',
                                            borderRadius: '4px',
                                            color: 'text.secondary',
                                            textTransform: 'none',
                                            backgroundColor: 'rgba(255, 255, 255, 0.05)',
                                            transition: 'all 0.2s ease-in-out',
                                            '&.Mui-selected': {
                                                backgroundColor: 'success.main',
                                                color: 'success.contrastText',
                                                borderColor: 'success.main',
                                                fontWeight: 600,
                                                boxShadow: '0 0 8px rgba(76, 175, 80, 0.4)',
                                                '&:hover': {
                                                    backgroundColor: 'success.dark',
                                                    boxShadow: '0 0 12px rgba(76, 175, 80, 0.6)',
                                                }
                                            },
                                            '&:hover': {
                                                backgroundColor: 'rgba(255, 255, 255, 0.1)',
                                                borderColor: 'rgba(255, 255, 255, 0.4)',
                                            }
                                        }}
                                    >
                                        {vfoActive[vfoIndex] ? t('vfo.active') : t('vfo.activate', 'Activate')}
                                    </ToggleButton>
                                </Tooltip>
                                <Tooltip title={vfoMuted[vfoIndex] ? "Unmute VFO audio" : "Mute VFO audio"} arrow>
                                    <span>
                                        <ToggleButton
                                            value="listen"
                                            selected={!vfoMuted[vfoIndex]}
                                            disabled={!vfoActive[vfoIndex]}
                                            onChange={() => handleVfoMuteToggle(vfoIndex)}
                                            sx={{
                                                flex: 1,
                                                height: '32px',
                                                fontSize: '0.8rem',
                                                border: '1px solid',
                                                borderColor: vfoMuted[vfoIndex] ? 'rgba(255, 152, 0, 0.5)' : 'rgba(255, 255, 255, 0.23)',
                                                borderRadius: '4px',
                                                color: 'text.secondary',
                                                textTransform: 'none',
                                                backgroundColor: vfoMuted[vfoIndex] ? 'rgba(255, 152, 0, 0.1)' : 'rgba(255, 255, 255, 0.05)',
                                                transition: 'all 0.2s ease-in-out',
                                                '&.Mui-selected': {
                                                    backgroundColor: 'primary.main',
                                                    color: 'primary.contrastText',
                                                    borderColor: 'primary.main',
                                                    fontWeight: 600,
                                                    boxShadow: '0 0 8px rgba(33, 150, 243, 0.4)',
                                                    '&:hover': {
                                                        backgroundColor: 'primary.dark',
                                                        boxShadow: '0 0 12px rgba(33, 150, 243, 0.6)',
                                                    }
                                                },
                                                '&:hover': {
                                                    backgroundColor: vfoMuted[vfoIndex] ? 'rgba(255, 152, 0, 0.2)' : 'rgba(255, 255, 255, 0.1)',
                                                    borderColor: vfoMuted[vfoIndex] ? 'rgba(255, 152, 0, 0.7)' : 'rgba(255, 255, 255, 0.4)',
                                                },
                                                '&.Mui-disabled': {
                                                    backgroundColor: 'rgba(255, 255, 255, 0.02)',
                                                    borderColor: 'rgba(255, 255, 255, 0.08)',
                                                    color: 'rgba(255, 255, 255, 0.3)',
                                                    opacity: 0.5,
                                                }
                                            }}
                                        >
                                            {!vfoMuted[vfoIndex] ? t('vfo.mute', 'Mute') : t('vfo.muted', 'Muted')}
                                        </ToggleButton>
                                    </span>
                                </Tooltip>
                            </Box>

                            {/* Frequency Display */}
                            <Box sx={{
                                mt: 2,
                                mb: 0,
                                width: '100%',
                                typography: 'body1',
                                fontWeight: 'medium',
                                alignItems: 'center'
                            }}>
                                <Box
                                    sx={{
                                        width: '100%',
                                        fontFamily: "Monospace",
                                        color: '#2196f3',
                                        alignItems: 'center',
                                        textAlign: 'center',
                                        justifyContent: 'center'
                                    }}>
                                    <LCDFrequencyDisplay
                                        frequency={vfoMarkers[vfoIndex]?.frequency || 0}
                                        size={"large"}/>
                                </Box>
                            </Box>

                            {/* RF Power Display (S-Meter) */}
                            <Box sx={{ mt: 1, mb: 1, opacity: vfoActive[vfoIndex] ? 1 : 0.4 }}>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                                    <Typography variant="caption" color="text.secondary">
                                        RF Power
                                    </Typography>
                                    <Typography variant="caption" sx={{
                                        fontFamily: 'monospace',
                                        color: vfoActive[vfoIndex] && vfoRfPower[vfoIndex] !== null ? (() => {
                                            const powerDb = vfoRfPower[vfoIndex];
                                            if (powerDb > -40) return '#4caf50'; // Green (excellent signal, -40dB to 0dB)
                                            if (powerDb > -60) return '#8bc34a'; // Light green (good signal, -60dB to -40dB)
                                            if (powerDb > -80) return '#4caf50'; // Green (weak signal, -80dB to -60dB)
                                            return '#f44336'; // Red (noise floor, below -80dB)
                                        })() : 'text.disabled'
                                    }}>
                                        {vfoActive[vfoIndex] && vfoRfPower[vfoIndex] !== null ? vfoRfPower[vfoIndex].toFixed(1) : '—'} dBFS
                                    </Typography>
                                </Box>
                                <Box sx={{ position: 'relative', height: 8 }}>
                                    {/* Background track */}
                                    <Box sx={{
                                        position: 'absolute',
                                        width: '100%',
                                        height: '100%',
                                        backgroundColor: 'rgba(128, 128, 128, 0.2)',
                                        borderRadius: 1,
                                    }} />
                                    {/* Power bar (filled portion) - scale from -100dB to 0dB */}
                                    {vfoActive[vfoIndex] && vfoRfPower[vfoIndex] !== null && (
                                        <Box sx={{
                                            position: 'absolute',
                                            left: 0,
                                            width: `${Math.min(100, Math.max(0, ((100 + vfoRfPower[vfoIndex]) / 100) * 100))}%`,
                                            height: '100%',
                                            background: (() => {
                                                const powerDb = vfoRfPower[vfoIndex];
                                                if (powerDb > -40) return '#4caf50'; // Green (excellent signal)
                                                if (powerDb > -60) return '#8bc34a'; // Light green (good signal)
                                                if (powerDb > -80) return '#4caf50'; // Green (weak signal)
                                                return '#f44336'; // Red (noise floor)
                                            })(),
                                            borderRadius: 1,
                                            transition: 'width 0.2s ease-out',
                                        }} />
                                    )}
                                </Box>
                            </Box>

                            {/* VU Meter Display */}
                            <Box sx={{ mt: 1, mb: 1, opacity: vfoActive[vfoIndex] ? 1 : 0.4 }}>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                                    <Typography variant="caption" color="text.secondary">
                                        Audio Level
                                    </Typography>
                                    <Typography variant="caption" sx={{
                                        fontFamily: 'monospace',
                                        color: vfoActive[vfoIndex] ? (() => {
                                            const levelDb = 20 * Math.log10(vfoAudioLevels[vfoIndex] + 0.00001);
                                            if (levelDb > -6) return '#f44336'; // Red (too loud/clipping, -6dB to 0dB)
                                            if (levelDb > -20) return '#ff9800'; // Orange (getting loud, -20dB to -6dB)
                                            if (levelDb > -60) return '#4caf50'; // Green (good level, -60dB to -20dB)
                                            return '#9e9e9e'; // Gray (too quiet, below -60dB)
                                        })() : 'text.disabled'
                                    }}>
                                        {vfoActive[vfoIndex] ? (20 * Math.log10(vfoAudioLevels[vfoIndex] + 0.00001)).toFixed(1) : '—'} dB
                                    </Typography>
                                </Box>
                                <Box sx={{ position: 'relative', height: 8 }}>
                                    {/* Background track */}
                                    <Box sx={{
                                        position: 'absolute',
                                        width: '100%',
                                        height: '100%',
                                        backgroundColor: 'rgba(128, 128, 128, 0.2)',
                                        borderRadius: 1,
                                    }} />
                                    {/* Green zone (-60dB to -20dB) - good level */}
                                    {vfoActive[vfoIndex] && (
                                        <Box sx={{
                                            position: 'absolute',
                                            left: `${((60 - 60) / 60) * 100}%`,  /* 0% from left (-60dB) */
                                            width: `${((60 - 20) / 60) * 100}%`,  /* 66.7% wide (to -20dB) */
                                            height: '100%',
                                            backgroundColor: 'rgba(76, 175, 80, 0.3)',
                                            borderRadius: 1,
                                        }} />
                                    )}
                                    {/* Orange zone (-20dB to -6dB) - getting loud */}
                                    {vfoActive[vfoIndex] && (
                                        <Box sx={{
                                            position: 'absolute',
                                            left: `${((60 - 20) / 60) * 100}%`,  /* 66.7% from left (-20dB) */
                                            width: `${((20 - 6) / 60) * 100}%`,  /* 23.3% wide (to -6dB) */
                                            height: '100%',
                                            backgroundColor: 'rgba(255, 152, 0, 0.3)',
                                            borderRadius: 1,
                                        }} />
                                    )}
                                    {/* Red zone (-6dB to 0dB) - too loud/clipping */}
                                    {vfoActive[vfoIndex] && (
                                        <Box sx={{
                                            position: 'absolute',
                                            left: `${((60 - 6) / 60) * 100}%`,   /* 90% from left (-6dB) */
                                            width: `${((6 - 0) / 60) * 100}%`,   /* 10% wide (to 0dB) */
                                            height: '100%',
                                            backgroundColor: 'rgba(244, 67, 54, 0.3)',
                                            borderRadius: 1,
                                        }} />
                                    )}
                                    {/* Level bar (filled portion) */}
                                    {vfoActive[vfoIndex] && (
                                        <Box sx={{
                                            position: 'absolute',
                                            left: 0,
                                            width: `${Math.min(100, Math.max(0, ((60 + (20 * Math.log10(vfoAudioLevels[vfoIndex] + 0.00001))) / 60) * 100))}%`,
                                            height: '100%',
                                            background: (() => {
                                                const levelDb = 20 * Math.log10(vfoAudioLevels[vfoIndex] + 0.00001);
                                                if (levelDb > -6) return 'linear-gradient(to right, #4caf50, #ff9800, #f44336)'; // Above -6dB: red zone
                                                if (levelDb > -20) return 'linear-gradient(to right, #4caf50 80%, #ff9800)'; // -20dB to -6dB: orange zone
                                                if (levelDb > -60) return '#4caf50'; // -60dB to -20dB: green zone
                                                return '#9e9e9e'; // Below -60dB: gray (too quiet)
                                            })(),
                                            borderRadius: 1,
                                            transition: 'width 0.1s ease-out',
                                        }} />
                                    )}
                                </Box>
                            </Box>

                            {/* Audio Buffer Display */}
                            <Box sx={{ mt: 1, mb: 1, opacity: vfoActive[vfoIndex] ? 1 : 0.4 }}>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                                    <Typography variant="caption" color="text.secondary">
                                        Audio Buffer
                                    </Typography>
                                    <Typography variant="caption" sx={{
                                        fontFamily: 'monospace',
                                        color: vfoActive[vfoIndex] ? (() => {
                                            const bufferMs = vfoBufferLengths[vfoIndex] * 1000;
                                            if (bufferMs >= 100 && bufferMs <= 1000) return '#4caf50'; // Green
                                            if (bufferMs < 100 || bufferMs > 1000) return '#ff9800'; // Orange
                                            return '#f44336'; // Red
                                        })() : 'text.disabled'
                                    }}>
                                        {vfoActive[vfoIndex] ? (vfoBufferLengths[vfoIndex] * 1000).toFixed(0) : '—'} ms
                                    </Typography>
                                </Box>
                                <Box sx={{ position: 'relative', height: 6 }}>
                                    {/* Background track */}
                                    <Box sx={{
                                        position: 'absolute',
                                        width: '100%',
                                        height: '100%',
                                        backgroundColor: 'rgba(128, 128, 128, 0.2)',
                                        borderRadius: 1,
                                    }} />
                                    {/* Green zone (100-1000ms) */}
                                    {vfoActive[vfoIndex] && (
                                        <Box sx={{
                                            position: 'absolute',
                                            left: `${(100 / 3000) * 100}%`,
                                            width: `${((1000 - 100) / 3000) * 100}%`,
                                            height: '100%',
                                            backgroundColor: 'rgba(76, 175, 80, 0.3)',
                                            borderRadius: 1,
                                        }} />
                                    )}
                                    {/* Indicator dot */}
                                    {vfoActive[vfoIndex] && (
                                        <Box sx={{
                                            position: 'absolute',
                                            left: `${Math.min((vfoBufferLengths[vfoIndex] * 1000 / 3000) * 100, 100)}%`,
                                            top: '50%',
                                            width: 8,
                                            height: 8,
                                            backgroundColor: (() => {
                                                const bufferMs = vfoBufferLengths[vfoIndex] * 1000;
                                                if (bufferMs >= 100 && bufferMs <= 1000) return '#4caf50';
                                                if (bufferMs < 100 || bufferMs > 1000) return '#ff9800';
                                                return '#f44336';
                                            })(),
                                            borderRadius: '50%',
                                            transform: 'translate(-50%, -50%)',
                                            border: '1px solid',
                                            borderColor: 'background.paper',
                                            boxShadow: '0 1px 2px rgba(0,0,0,0.3)',
                                        }} />
                                    )}
                                </Box>
                            </Box>

                            {/* Volume and Squelch Sliders */}
                            <Stack
                                spacing={0}
                                direction="row"
                                alignItems="center"
                                sx={{mt: 2}}
                                data-slider="squelch"
                                data-vfo-index={vfoIndex}
                            >
                                <Tooltip title="Auto Squelch (Noise Floor + 5dB)" arrow>
                                    <span>
                                        <IconButton
                                            onClick={() => {
                                                const currentPower = vfoRfPower[vfoIndex];
                                                if (currentPower !== null) {
                                                    // Set squelch to current noise floor + 5 dB
                                                    const autoSquelch = Math.round(currentPower + 5);
                                                    onVFOPropertyChange(vfoIndex, {squelch: Math.max(-150, Math.min(0, autoSquelch))});
                                                }
                                            }}
                                            disabled={!vfoActive[vfoIndex] || vfoRfPower[vfoIndex] === null}
                                            sx={{
                                                color: 'text.secondary',
                                                backgroundColor: 'rgba(33, 150, 243, 0.08)',
                                                '&:hover': {
                                                    backgroundColor: 'rgba(33, 150, 243, 0.15)',
                                                },
                                                '&:disabled': {
                                                    backgroundColor: 'transparent',
                                                },
                                            }}
                                        >
                                            <SquelchIconCentered size={24}/>
                                        </IconButton>
                                    </span>
                                </Tooltip>
                                <Slider
                                    value={vfoMarkers[vfoIndex]?.squelch || -150}
                                    min={-150}
                                    max={0}
                                    onChange={(e, val) => onVFOPropertyChange(vfoIndex, {squelch: val})}
                                    disabled={!vfoActive[vfoIndex]}
                                    sx={{ ml: '5px' }}
                                />
                                <Box sx={{minWidth: 50, fontSize: '0.875rem', textAlign: 'right'}}>{vfoMarkers[vfoIndex]?.squelch || -150} dB</Box>
                            </Stack>

                            <Stack
                                spacing={0}
                                direction="row"
                                alignItems="center"
                                sx={{mt: 2}}
                                data-slider="volume"
                                data-vfo-index={vfoIndex}
                            >
                                <Tooltip title={vfoMuted[vfoIndex] ? "Unmute VFO" : "Mute VFO"} arrow>
                                    <span>
                                        <IconButton
                                            onClick={() => handleVfoMuteToggle(vfoIndex)}
                                            disabled={!vfoActive[vfoIndex]}
                                            sx={{
                                                color: vfoMuted[vfoIndex] ? 'error.main' : 'text.secondary',
                                                backgroundColor: vfoMuted[vfoIndex] ? 'rgba(244, 67, 54, 0.08)' : 'rgba(33, 150, 243, 0.08)',
                                                '&:hover': {
                                                    backgroundColor: vfoMuted[vfoIndex] ? 'rgba(244, 67, 54, 0.15)' : 'rgba(33, 150, 243, 0.15)',
                                                },
                                                '&:disabled': {
                                                    backgroundColor: 'transparent',
                                                },
                                            }}
                                        >
                                            {vfoMuted[vfoIndex] ? <VolumeOffIcon /> : <VolumeDown />}
                                        </IconButton>
                                    </span>
                                </Tooltip>
                                <Slider
                                    value={vfoMarkers[vfoIndex]?.volume || 50}
                                    onChange={(e, val) => onVFOPropertyChange(vfoIndex, {volume: val})}
                                    disabled={!vfoActive[vfoIndex]}
                                    sx={{ ml: '5px' }}
                                />
                                <Box sx={{minWidth: 50, fontSize: '0.875rem', textAlign: 'right'}}>{vfoMarkers[vfoIndex]?.volume || 50}%</Box>
                            </Stack>

                            {/* Decoder/Transcription Status Display - Two lines */}
                            {(() => {
                                const decoderInfo = getVFODecoderInfo(vfoIndex);
                                const vfo = vfoMarkers[vfoIndex];

                                // Determine what to display
                                let line1Text = '—';
                                let line2Text = '';
                                let borderColor = 'divider';
                                let textColor = 'text.disabled';

                                // Check if this is a transcription decoder
                                if (decoderInfo && decoderInfo.decoder_type === 'transcription') {
                                    const info = decoderInfo.info || {};
                                    const status = decoderInfo.status || 'unknown';

                                    // Line 1: TRANSCRIBING status and language info
                                    const statusParts = [];
                                    statusParts.push(status.toUpperCase());

                                    // Show language flow: source -> target
                                    if (info.language) {
                                        const langDisplay = info.language.toUpperCase();
                                        const translateDisplay = info.translate_to ? info.translate_to.toUpperCase() : null;
                                        if (translateDisplay && translateDisplay !== 'NONE') {
                                            statusParts.push(`${langDisplay} → ${translateDisplay}`);
                                        } else {
                                            statusParts.push(langDisplay);
                                        }
                                    }

                                    line1Text = statusParts.join(' • ');

                                    // Line 2: Transcription metrics
                                    const metricParts = [];

                                    // Transcription request stats
                                    if (info.transcriptions_sent !== undefined && info.transcriptions_received !== undefined) {
                                        const successRate = info.transcriptions_sent > 0
                                            ? Math.round((info.transcriptions_received / info.transcriptions_sent) * 100)
                                            : 0;
                                        metricParts.push(`SENT:${info.transcriptions_sent} RCV:${info.transcriptions_received} (${successRate}%)`);
                                    }

                                    // Show errors if any
                                    if (info.errors !== undefined && info.errors > 0) {
                                        metricParts.push(`ERR:${info.errors}`);
                                    }

                                    line2Text = metricParts.length > 0 ? metricParts.join(' • ') : '—';

                                    borderColor = status === 'transcribing' ? 'success.dark' : 'warning.dark';
                                    textColor = 'text.secondary';
                                } else if (vfo && vfo.transcriptionEnabled) {
                                    // Transcription enabled but not active
                                    line1Text = 'TRANSCRIPTION - Not Active';
                                    line2Text = '';
                                    borderColor = 'warning.dark';
                                    textColor = 'warning.main';
                                } else if (vfo && vfo.decoder && vfo.decoder !== 'none') {
                                    // Data decoder (existing logic)
                                    if (decoderInfo) {
                                        const info = decoderInfo.info || {};
                                        const status = decoderInfo.status || 'unknown';

                                        // Line 1: STATUS, MODE, FRAMING
                                        const statusParts = [];
                                        statusParts.push(status.toUpperCase());
                                        if (info.transmitter_mode !== undefined && info.transmitter_mode !== null) {
                                            statusParts.push(info.transmitter_mode);
                                        }
                                        if (info.framing !== undefined && info.framing !== null) {
                                            statusParts.push(info.framing.toUpperCase());
                                        }
                                        line1Text = statusParts.join(' • ');

                                        // Line 2: baudrate and existing metrics (packets, signal power) or progress or morse-specific
                                        const metricParts = [];

                                        // Add baudrate at the start of line 2
                                        if (info.baudrate !== undefined && info.baudrate !== null) {
                                            metricParts.push(`${info.baudrate}bd`);
                                        }

                                        // Show progress for SSTV if available
                                        if (decoderInfo.progress !== undefined && decoderInfo.progress !== null) {
                                            metricParts.push(`Progress: ${decoderInfo.progress}%`);
                                        }

                                        // Show WPM and character count for Morse
                                        if (info.wpm !== undefined && info.wpm !== null) {
                                            metricParts.push(`${info.wpm} WPM`);
                                        }
                                        if (info.character_count !== undefined && info.character_count !== null && info.character_count > 0) {
                                            metricParts.push(`CHAR:${info.character_count}`);
                                        }

                                        if (info.packets_decoded !== undefined && info.packets_decoded !== null) {
                                            metricParts.push(`PKT:${info.packets_decoded}`);
                                        }
                                        if (info.signal_power_dbfs !== undefined && info.signal_power_dbfs !== null) {
                                            metricParts.push(`${info.signal_power_dbfs.toFixed(1)}dB`);
                                        }
                                        line2Text = metricParts.length > 0 ? metricParts.join(' • ') : '—';

                                        borderColor = (status === 'decoding' || status === 'transcribing') ? 'success.dark' : 'warning.dark';
                                        textColor = 'text.secondary';
                                    } else {
                                        // Decoder selected but not running
                                        line1Text = `${vfo.decoder.toUpperCase()} - Not Active`;
                                        line2Text = '';
                                        borderColor = 'warning.dark';
                                        textColor = 'warning.main';
                                    }
                                } else {
                                    // No decoder or transcription selected
                                    line1Text = '- no decoder -';
                                    line2Text = '';
                                    borderColor = 'divider';
                                    textColor = 'text.disabled';
                                }

                                return (
                                    <Box sx={{
                                        mt: 1,
                                        px: 1,
                                        py: 0.5,
                                        backgroundColor: 'rgba(0, 0, 0, 0.2)',
                                        borderRadius: 0.5,
                                        border: '1px solid',
                                        borderColor: borderColor,
                                        minHeight: '42px', // Ensure consistent height for two lines
                                        display: 'flex',
                                        flexDirection: 'column',
                                        alignItems: 'center',
                                        justifyContent: 'center'
                                    }}>
                                        <Typography
                                            variant="caption"
                                            sx={{
                                                fontSize: '0.7rem',
                                                fontFamily: 'monospace',
                                                color: textColor,
                                                display: 'block',
                                                textAlign: 'center'
                                            }}
                                        >
                                            {line1Text}
                                        </Typography>
                                        {line2Text && (
                                            <Typography
                                                variant="caption"
                                                sx={{
                                                    fontSize: '0.7rem',
                                                    fontFamily: 'monospace',
                                                    color: textColor,
                                                    display: 'block',
                                                    textAlign: 'center',
                                                    minHeight: '0.7rem' // Reserve space even when empty
                                                }}
                                            >
                                                {line2Text || '\u00A0'}
                                            </Typography>
                                        )}
                                    </Box>
                                );
                            })()}

                            {/* Lock to Transmitter Dropdown */}
                            <Box sx={{ mt: 2 }}>
                                <FormControl fullWidth size="small" disabled={!vfoActive[vfoIndex]}
                                             variant="filled">
                                    <InputLabel id={`vfo-${vfoIndex}-lock-transmitter-label`}>
                                        {vfoMarkers[vfoIndex]?.lockedTransmitterId && vfoMarkers[vfoIndex]?.lockedTransmitterId !== 'none' ? (
                                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                                <LockIcon fontSize="small" />
                                                {t('vfo.lock_to_transmitter', 'Lock to Transmitter')}
                                            </Box>
                                        ) : (
                                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                                <LockOpenIcon fontSize="small" />
                                                {t('vfo.lock_to_transmitter', 'Lock to Transmitter')}
                                            </Box>
                                        )}
                                    </InputLabel>
                                    <Select
                                        variant={'filled'}
                                        labelId={`vfo-${vfoIndex}-lock-transmitter-label`}
                                        value={(() => {
                                            const currentValue = vfoMarkers[vfoIndex]?.lockedTransmitterId;
                                            if (!currentValue || currentValue === 'none') return 'none';
                                            // Check if the current value exists in the transmitters list
                                            const exists = transmitters.some(tx => tx.id === currentValue);
                                            return exists ? currentValue : 'none';
                                        })()}
                                        label={t('vfo.lock_to_transmitter', 'Lock to Transmitter')}
                                        onChange={(e) => {
                                            const transmitterId = e.target.value === 'none' ? 'none' : e.target.value;

                                            if (transmitterId !== 'none') {
                                                // Locking to a transmitter - set frequency and lock, but don't change mode
                                                const transmitter = transmitters.find(tx => tx.id === transmitterId);
                                                if (transmitter) {
                                                    onVFOPropertyChange(vfoIndex, {
                                                        lockedTransmitterId: transmitterId,
                                                        frequency: transmitter.downlink_observed_freq,
                                                        frequencyOffset: 0
                                                    });
                                                }
                                            } else {
                                                // Unlocking - just clear the lock and reset offset
                                                onVFOPropertyChange(vfoIndex, {
                                                    lockedTransmitterId: 'none',
                                                    frequencyOffset: 0
                                                });
                                            }
                                        }}
                                        sx={{ fontSize: '0.875rem' }}
                                    >
                                        <MenuItem value="none" sx={{ fontSize: '0.875rem' }}>
                                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                                <LockOpenIcon fontSize="small" />
                                                {t('vfo.none', 'None')}
                                            </Box>
                                        </MenuItem>
                                        {transmitters.map((tx) => (
                                            <MenuItem key={tx.id} value={tx.id} sx={{ fontSize: '0.875rem' }}>
                                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                                                    <Box
                                                        sx={{
                                                            width: 8,
                                                            height: 8,
                                                            borderRadius: '50%',
                                                            backgroundColor: tx.alive ? 'success.main' : 'error.main',
                                                            boxShadow: (theme) => tx.alive
                                                                ? `0 0 6px ${theme.palette.success.main}99`
                                                                : `0 0 6px ${theme.palette.error.main}99`,
                                                            flexShrink: 0,
                                                        }}
                                                    />
                                                    <Box sx={{ flex: 1 }}>
                                                        <Box sx={{ fontWeight: 600 }}>{tx.description}</Box>
                                                        <Box sx={{ fontSize: '0.75rem', color: 'text.secondary' }}>
                                                            {(tx.downlink_observed_freq / 1e6).toFixed(6)} MHz ({tx.mode})
                                                        </Box>
                                                    </Box>
                                                </Box>
                                            </MenuItem>
                                        ))}
                                    </Select>
                                </FormControl>
                            </Box>

                            {/* Discreet link to edit transmitters */}
                            {targetSatelliteData && (
                                <Box sx={{ mt: 0.5, textAlign: 'center' }}>
                                    <Link
                                        component="button"
                                        variant="caption"
                                        onClick={() => setTransmittersDialogOpen(true)}
                                        sx={{
                                            fontSize: '0.7rem',
                                            color: 'text.disabled',
                                            textDecoration: 'none',
                                            '&:hover': {
                                                color: 'text.secondary',
                                                textDecoration: 'underline',
                                            },
                                            cursor: 'pointer',
                                        }}
                                    >
                                        Edit {targetSatelliteName} transmitters here
                                    </Link>
                                </Box>
                            )}
                        </Box>

                        {vfoMarkers[vfoIndex]?.lockedTransmitterId && vfoMarkers[vfoIndex]?.lockedTransmitterId !== 'none' && (
                            <Alert
                                severity="info"
                                icon={<LockIcon fontSize="small" />}
                                sx={{
                                    mt: 1,
                                    mb: 1,
                                    py: 0.5,
                                    fontSize: '0.875rem',
                                    '& .MuiAlert-icon': {
                                        fontSize: '1rem'
                                    }
                                }}
                            >
                                {t('vfo.locked_to_transmitter_info', 'Tracking doppler-corrected frequency')}
                            </Alert>
                        )}

                        <RotaryEncoder vfoNumber={vfoIndex} />

                        <Box sx={{ mt: 1 }}>
                            <Typography variant="body2" sx={{ mb: 1, color: 'text.secondary' }}>
                                {t('vfo.step_size')}
                            </Typography>
                            <ToggleButtonGroup
                                value={vfoMarkers[vfoIndex]?.stepSize || 1000}
                                exclusive
                                disabled={!vfoActive[vfoIndex]}
                                onChange={(event, newValue) => {
                                    if (newValue !== null) {
                                        onVFOPropertyChange(vfoIndex, { stepSize: newValue });
                                    }
                                }}
                                sx={{
                                    display: 'flex',
                                    flexWrap: 'wrap',
                                    gap: 0.5,
                                    '& .MuiToggleButton-root': {
                                        width: '60px',
                                        height: '28px',
                                        minWidth: '70px',
                                        maxWidth: '60px',
                                        padding: '4px 6px',
                                        fontSize: '0.8rem',
                                        border: '1px solid',
                                        borderColor: 'rgba(255, 255, 255, 0.23)',
                                        borderRadius: '4px',
                                        color: 'text.secondary',
                                        textAlign: 'center',
                                        textTransform: 'none',
                                        backgroundColor: 'rgba(255, 255, 255, 0.05)',
                                        transition: 'all 0.2s ease-in-out',
                                        '&.Mui-selected': {
                                            backgroundColor: 'primary.main',
                                            color: 'primary.contrastText',
                                            borderColor: 'primary.main',
                                            fontWeight: 600,
                                            boxShadow: '0 0 8px rgba(33, 150, 243, 0.4)',
                                            '&:hover': {
                                                backgroundColor: 'primary.dark',
                                                boxShadow: '0 0 12px rgba(33, 150, 243, 0.6)',
                                            }
                                        },
                                        '&:hover': {
                                            backgroundColor: 'rgba(255, 255, 255, 0.1)',
                                            borderColor: 'rgba(255, 255, 255, 0.4)',
                                        },
                                        '&.Mui-disabled': {
                                            backgroundColor: 'rgba(255, 255, 255, 0.02)',
                                            borderColor: 'rgba(255, 255, 255, 0.08)',
                                            color: 'rgba(255, 255, 255, 0.3)',
                                            opacity: 0.5,
                                        }
                                    }
                                }}
                            >
                                <ToggleButton value={50}>50 Hz</ToggleButton>
                                <ToggleButton value={100}>100 Hz</ToggleButton>
                                <ToggleButton value={250}>250 Hz</ToggleButton>
                                <ToggleButton value={500}>500 Hz</ToggleButton>
                                <ToggleButton value={1000}>1 kHz</ToggleButton>
                                <ToggleButton value={2500}>2.5 kHz</ToggleButton>
                                <ToggleButton value={5000}>5 kHz</ToggleButton>
                                <ToggleButton value={10000}>10 kHz</ToggleButton>
                                <ToggleButton value={12500}>12.5 kHz</ToggleButton>
                                <ToggleButton value={20000}>20 kHz</ToggleButton>
                                <ToggleButton value={25000}>25 kHz</ToggleButton>
                            </ToggleButtonGroup>
                        </Box>

                        <Box sx={{ mt: 2 }}>
                            <Typography variant="body2" sx={{ mb: 0.5, color: 'text.secondary', fontWeight: 600 }}>
                                {t('vfo.audio_demodulation', 'Audio Demodulation')}
                            </Typography>
                            <Typography variant="caption" sx={{ mb: 1, display: 'block', color: 'text.disabled', fontSize: '0.7rem' }}>
                                {t('vfo.audio_demodulation_help', 'How to extract audio from the RF signal')}
                            </Typography>
                            <ToggleButtonGroup
                                value={vfoMarkers[vfoIndex]?.mode || 'none'}
                                exclusive
                                disabled={!vfoActive[vfoIndex]}
                                onChange={(event, newValue) => {
                                    if (newValue !== null) {
                                        // When selecting an audio demod mode, clear decoder
                                        // (mode and decoder are mutually exclusive)
                                        onVFOPropertyChange(vfoIndex, { mode: newValue, decoder: 'none' });
                                    }
                                }}
                                sx={{
                                    display: 'flex',
                                    flexWrap: 'wrap',
                                    gap: 0.5,
                                    '& .MuiToggleButton-root': {
                                        height: '28px',
                                        minWidth: '50px',
                                        padding: '4px 8px',
                                        fontSize: '0.75rem',
                                        border: '1px solid',
                                        borderColor: 'rgba(255, 255, 255, 0.23)',
                                        borderRadius: '4px',
                                        color: 'text.secondary',
                                        textAlign: 'center',
                                        textTransform: 'none',
                                        backgroundColor: 'rgba(255, 255, 255, 0.05)',
                                        transition: 'all 0.2s ease-in-out',
                                        '&.Mui-selected': {
                                            backgroundColor: 'primary.main',
                                            color: 'primary.contrastText',
                                            borderColor: 'primary.main',
                                            fontWeight: 600,
                                            boxShadow: '0 0 8px rgba(33, 150, 243, 0.4)',
                                            '&:hover': {
                                                backgroundColor: 'primary.dark',
                                                boxShadow: '0 0 12px rgba(33, 150, 243, 0.6)',
                                            }
                                        },
                                        '&:hover': {
                                            backgroundColor: 'rgba(255, 255, 255, 0.1)',
                                            borderColor: 'rgba(255, 255, 255, 0.4)',
                                        },
                                        '&.Mui-disabled': {
                                            backgroundColor: 'rgba(255, 255, 255, 0.02)',
                                            borderColor: 'rgba(255, 255, 255, 0.08)',
                                            color: 'rgba(255, 255, 255, 0.3)',
                                            opacity: 0.5,
                                        }
                                    }
                                }}
                            >
                                <ToggleButton value="none">{t('vfo.modes.none')}</ToggleButton>
                                <ToggleButton value="AM">{t('vfo.modes.am')}</ToggleButton>
                                <ToggleButton value="FM">{t('vfo.modes.fm')}</ToggleButton>
                                <ToggleButton value="FM_STEREO">{t('vfo.modes.fm_stereo', 'FM Stereo')}</ToggleButton>
                                <ToggleButton value="LSB">{t('vfo.modes.lsb')}</ToggleButton>
                                <ToggleButton value="USB">{t('vfo.modes.usb')}</ToggleButton>
                                <ToggleButton value="CW">{t('vfo.modes.cw')}</ToggleButton>
                            </ToggleButtonGroup>
                        </Box>

                        <Box sx={{ mt: 2 }}>
                            <Typography variant="body2" sx={{ mb: 0.5, color: 'text.secondary', fontWeight: 600 }}>
                                {t('vfo.transcription_mode', 'Transcription')}
                            </Typography>
                            <Typography variant="caption" sx={{ mb: 1, display: 'block', color: 'text.disabled', fontSize: '0.7rem' }}>
                                {t('vfo.transcription_help', 'Transcribe audio using AI')}
                            </Typography>
                            <ToggleButtonGroup
                                value={vfoMarkers[vfoIndex]?.transcriptionEnabled ? (vfoMarkers[vfoIndex]?.transcriptionProvider || 'gemini') : 'none'}
                                exclusive
                                disabled={!vfoActive[vfoIndex] || (!geminiConfigured && !deepgramConfigured)}
                                onChange={(event, newValue) => {
                                    if (newValue !== null) {
                                        const currentEnabled = vfoMarkers[vfoIndex]?.transcriptionEnabled;
                                        const currentProvider = vfoMarkers[vfoIndex]?.transcriptionProvider || 'gemini';
                                        const currentValue = currentEnabled ? currentProvider : 'none';

                                        // If clicking same button, do nothing
                                        if (newValue === currentValue) {
                                            return;
                                        }

                                        const newEnabled = newValue !== 'none';
                                        const newProvider = newValue !== 'none' ? newValue : currentProvider;

                                        onTranscriptionToggle && onTranscriptionToggle(vfoIndex, newEnabled, newProvider);
                                    }
                                }}
                                sx={{
                                    display: 'flex',
                                    flexWrap: 'wrap',
                                    gap: 0.5,
                                    '& .MuiToggleButton-root': {
                                        height: '28px',
                                        minWidth: '50px',
                                        padding: '4px 8px',
                                        fontSize: '0.75rem',
                                        border: '1px solid',
                                        borderColor: 'rgba(255, 255, 255, 0.23)',
                                        borderRadius: '4px',
                                        color: 'text.secondary',
                                        textAlign: 'center',
                                        textTransform: 'none',
                                        backgroundColor: 'rgba(255, 255, 255, 0.05)',
                                        transition: 'all 0.2s ease-in-out',
                                        '&.Mui-selected': {
                                            backgroundColor: 'primary.main',
                                            color: 'primary.contrastText',
                                            borderColor: 'primary.main',
                                            fontWeight: 600,
                                            boxShadow: '0 0 8px rgba(33, 150, 243, 0.4)',
                                            '&:hover': {
                                                backgroundColor: 'primary.dark',
                                                boxShadow: '0 0 12px rgba(33, 150, 243, 0.6)',
                                            }
                                        },
                                        '&:hover': {
                                            backgroundColor: 'rgba(255, 255, 255, 0.1)',
                                            borderColor: 'rgba(255, 255, 255, 0.4)',
                                        },
                                        '&.Mui-disabled': {
                                            backgroundColor: 'rgba(255, 255, 255, 0.02)',
                                            borderColor: 'rgba(255, 255, 255, 0.08)',
                                            color: 'rgba(255, 255, 255, 0.3)',
                                            opacity: 0.5,
                                        }
                                    }
                                }}
                            >
                                <ToggleButton value="none">{t('vfo.transcription_modes.none', 'None')}</ToggleButton>
                                <ToggleButton value="gemini" disabled={!geminiConfigured}>
                                    {t('vfo.transcription_modes.gemini', 'Gemini AI')}
                                </ToggleButton>
                                <ToggleButton value="deepgram" disabled={!deepgramConfigured}>
                                    {t('vfo.transcription_modes.deepgram', 'Deepgram')}
                                </ToggleButton>
                            </ToggleButtonGroup>

                            {/* API Key notification */}
                            {!geminiConfigured && !deepgramConfigured && (
                                <Typography variant="caption" sx={{
                                    mt: 0.5,
                                    display: 'block',
                                    color: 'text.disabled',
                                    fontSize: '0.7rem',
                                    fontStyle: 'italic'
                                }}>
                                    {t('vfo.api_key_required', 'API key required in Settings')}
                                </Typography>
                            )}
                            {!geminiConfigured && deepgramConfigured && (
                                <Typography variant="caption" sx={{
                                    mt: 0.5,
                                    display: 'block',
                                    color: 'text.disabled',
                                    fontSize: '0.7rem',
                                    fontStyle: 'italic'
                                }}>
                                    {t('vfo.gemini_key_required', 'Gemini API key required for Gemini')}
                                </Typography>
                            )}
                            {geminiConfigured && !deepgramConfigured && (
                                <Typography variant="caption" sx={{
                                    mt: 0.5,
                                    display: 'block',
                                    color: 'text.disabled',
                                    fontSize: '0.7rem',
                                    fontStyle: 'italic'
                                }}>
                                    {t('vfo.deepgram_key_required', 'Deepgram API key required for Deepgram')}
                                </Typography>
                            )}

                            {/* Transcription Parameters Button */}
                            <Box sx={{ mt: 1.5, width: '100%' }}>
                                <Link
                                    component="button"
                                    variant="body2"
                                    disabled={!vfoActive[vfoIndex] || !vfoMarkers[vfoIndex]?.transcriptionEnabled || !geminiConfigured}
                                    onClick={() => {
                                        setTranscriptionParamsVfoIndex(vfoIndex);
                                        setTranscriptionParamsDialogOpen(true);
                                    }}
                                    sx={{
                                        width: '100%',
                                        fontSize: '0.8rem',
                                        color: 'text.primary',
                                        textDecoration: 'none',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'space-between',
                                        gap: 0.75,
                                        py: 0.75,
                                        px: 1.5,
                                        borderRadius: 1,
                                        backgroundColor: 'rgba(255, 255, 255, 0.05)',
                                        border: '1px solid rgba(255, 255, 255, 0.1)',
                                        transition: 'all 0.2s ease',
                                        '&:hover:not(.Mui-disabled)': {
                                            backgroundColor: 'rgba(255, 255, 255, 0.08)',
                                            borderColor: 'rgba(255, 255, 255, 0.2)',
                                        },
                                        '&.Mui-disabled': {
                                            backgroundColor: 'rgba(255, 255, 255, 0.02)',
                                            borderColor: 'rgba(255, 255, 255, 0.05)',
                                            color: 'rgba(255, 255, 255, 0.3)',
                                            opacity: 0.5,
                                            cursor: 'not-allowed',
                                        },
                                        cursor: 'pointer',
                                    }}
                                >
                                    <SettingsIcon sx={{ fontSize: '1rem', color: 'text.secondary', flexShrink: 0 }} />
                                    <Box component="span" sx={{ fontFamily: 'monospace', color: 'text.secondary', flex: 1, textAlign: 'center' }}>
                                        {(() => {
                                            const vfo = vfoMarkers[vfoIndex];
                                            if (!vfo?.transcriptionEnabled) {
                                                return '- no transcription -';
                                            }

                                            const sourceLang = vfo.transcriptionLanguage || 'auto';
                                            const translateTo = vfo.transcriptionTranslateTo || 'none';

                                            // Language code to flag emoji mapping
                                            const flagMap = {
                                                'auto': '🌐',
                                                'en': '🇬🇧',
                                                'el': '🇬🇷',
                                                'es': '🇪🇸',
                                                'fr': '🇫🇷',
                                                'de': '🇩🇪',
                                                'it': '🇮🇹',
                                                'pt': '🇵🇹',
                                                'pt-BR': '🇧🇷',
                                                'ru': '🇷🇺',
                                                'uk': '🇺🇦',
                                                'ja': '🇯🇵',
                                                'zh': '🇨🇳',
                                                'ar': '🇸🇦',
                                                'tl': '🇵🇭',
                                                'tr': '🇹🇷',
                                            };

                                            // Language code to short name mapping
                                            const langMap = {
                                                'auto': 'Auto',
                                                'en': 'EN',
                                                'el': 'EL',
                                                'es': 'ES',
                                                'fr': 'FR',
                                                'de': 'DE',
                                                'it': 'IT',
                                                'pt': 'PT',
                                                'pt-BR': 'PT-BR',
                                                'ru': 'RU',
                                                'uk': 'UK',
                                                'ja': 'JA',
                                                'zh': 'ZH',
                                                'ar': 'AR',
                                                'tl': 'TL',
                                                'tr': 'TR',
                                            };

                                            const sourceFlag = flagMap[sourceLang] || '🏳️';
                                            const sourceDisplay = langMap[sourceLang] || sourceLang.toUpperCase();

                                            const translateFlag = translateTo === 'none' ? '⭕' : (flagMap[translateTo] || '🏳️');
                                            const translateDisplay = translateTo === 'none' ? 'No Trans' : langMap[translateTo] || translateTo.toUpperCase();

                                            return `${sourceFlag} ${sourceDisplay} → ${translateFlag} ${translateDisplay}`;
                                        })()}
                                    </Box>
                                </Link>
                            </Box>
                        </Box>

                        <Box sx={{ mt: 2 }}>
                            <Typography variant="body2" sx={{ mb: 0.5, color: 'text.secondary', fontWeight: 600 }}>
                                {t('vfo.data_decoders', 'Data Decoders')}
                            </Typography>
                            <Typography variant="caption" sx={{ mb: 1, display: 'block', color: 'text.disabled', fontSize: '0.7rem' }}>
                                {t('vfo.data_decoders_help', 'An internal FM or SSB demodulator will be spun up as needed to decode some modes')}
                            </Typography>
                            <ToggleButtonGroup
                                value={vfoMarkers[vfoIndex]?.decoder || 'none'}
                                exclusive
                                disabled={!vfoActive[vfoIndex]}
                                onChange={(event, newValue) => {
                                    if (newValue !== null) {
                                        // When selecting a decoder (not none), set audio demod to NONE
                                        // Backend will start appropriate internal demodulator as needed
                                        // Also disable transcription when a decoder is selected
                                        if (newValue !== 'none') {
                                            // Disable transcription when selecting a decoder
                                            if (vfoMarkers[vfoIndex]?.transcriptionEnabled) {
                                                onTranscriptionToggle && onTranscriptionToggle(vfoIndex, false);
                                            }
                                            const updates = { decoder: newValue, mode: 'none' };

                                            // Set bandwidth based on decoder type (using vfo-config.js defaults)
                                            if (newValue === 'sstv') {
                                                updates.bandwidth = 3300; // 3.3 kHz for SSTV (audio content ~1200-2300 Hz)
                                            } else if (newValue === 'apt') {
                                                updates.bandwidth = 40000; // 40 kHz for APT (NOAA APT signal bandwidth)
                                            } else if (newValue === 'lora') {
                                                updates.bandwidth = 500000; // 500 kHz for LoRa (auto-detects 125/250/500 kHz signals)
                                            } else if (newValue === 'morse') {
                                                updates.bandwidth = 2500; // 2.5 kHz for Morse decoder (narrowband)
                                            } else if (newValue === 'gmsk' || newValue === 'gfsk' || newValue === 'bpsk') {
                                                // Get locked transmitter for GMSK/GFSK/BPSK bandwidth calculation
                                                // TODO maybe we should remove this logic and let the user adjust the
                                                // bandwidth themselves?  It's not clear that this is a good idea.
                                                const currentVFO = vfoMarkers[vfoIndex];
                                                const lockedTransmitter = currentVFO?.lockedTransmitterId
                                                    ? transmitters.find(tx => tx.id === currentVFO.lockedTransmitterId)
                                                    : null;

                                                if (lockedTransmitter && lockedTransmitter.baud) {
                                                    // Calculate bandwidth: 3x baud rate (GMSK/BPSK + Doppler margin)
                                                    updates.bandwidth = lockedTransmitter.baud * 3;
                                                    updates.transmitterBaud = lockedTransmitter.baud;
                                                } else {
                                                    // Use default from vfo-config.js
                                                    updates.bandwidth = 30000; // 30 kHz default
                                                }
                                            } else if (newValue === 'afsk') {
                                                updates.bandwidth = 3300; // 3.3 kHz for AFSK
                                            } else if (newValue === 'weather') {
                                                // Get locked transmitter for weather satellite bandwidth calculation
                                                const currentVFO = vfoMarkers[vfoIndex];
                                                const lockedTransmitter = currentVFO?.lockedTransmitterId
                                                    ? transmitters.find(tx => tx.id === currentVFO.lockedTransmitterId)
                                                    : null;

                                                if (lockedTransmitter) {
                                                    // Use calculateBandwidth from vfo-config.js
                                                    const decoderConfig = getDecoderConfig('weather');
                                                    if (decoderConfig && decoderConfig.calculateBandwidth) {
                                                        updates.bandwidth = decoderConfig.calculateBandwidth(lockedTransmitter);
                                                    } else {
                                                        updates.bandwidth = 40000; // Fallback to default (APT)
                                                    }
                                                } else {
                                                    updates.bandwidth = 40000; // Default to APT bandwidth (40 kHz)
                                                }
                                            }

                                            onVFOPropertyChange(vfoIndex, updates);
                                        } else {
                                            onVFOPropertyChange(vfoIndex, { decoder: newValue });
                                        }
                                    }
                                }}
                                sx={{
                                    display: 'flex',
                                    flexWrap: 'wrap',
                                    gap: 0.5,
                                    '& .MuiToggleButton-root': {
                                        height: '28px',
                                        minWidth: '50px',
                                        padding: '4px 8px',
                                        fontSize: '0.75rem',
                                        border: '1px solid',
                                        borderColor: 'rgba(255, 255, 255, 0.23)',
                                        borderRadius: '4px',
                                        color: 'text.secondary',
                                        textAlign: 'center',
                                        textTransform: 'none',
                                        backgroundColor: 'rgba(255, 255, 255, 0.05)',
                                        transition: 'all 0.2s ease-in-out',
                                        '&.Mui-selected': {
                                            backgroundColor: 'primary.main',
                                            color: 'primary.contrastText',
                                            borderColor: 'primary.main',
                                            fontWeight: 600,
                                            boxShadow: '0 0 8px rgba(33, 150, 243, 0.4)',
                                            '&:hover': {
                                                backgroundColor: 'primary.dark',
                                                boxShadow: '0 0 12px rgba(33, 150, 243, 0.6)',
                                            }
                                        },
                                        '&:hover': {
                                            backgroundColor: 'rgba(255, 255, 255, 0.1)',
                                            borderColor: 'rgba(255, 255, 255, 0.4)',
                                        },
                                        '&.Mui-disabled': {
                                            backgroundColor: 'rgba(255, 255, 255, 0.02)',
                                            borderColor: 'rgba(255, 255, 255, 0.08)',
                                            color: 'rgba(255, 255, 255, 0.3)',
                                            opacity: 0.5,
                                        }
                                    }
                                }}
                            >
                                <ToggleButton value="none">{t('vfo.decoders_modes.none', 'None')}</ToggleButton>
                                <ToggleButton value="sstv">{t('vfo.decoders_modes.sstv', 'SSTV')}</ToggleButton>
                                <ToggleButton value="morse">{t('vfo.decoders_modes.morse', 'Morse')}</ToggleButton>
                                <ToggleButton value="lora">{t('vfo.decoders_modes.lora', 'LoRa')}</ToggleButton>
                                <ToggleButton value="fsk">{t('vfo.decoders_modes.fsk', 'FSK')}</ToggleButton>
                                <ToggleButton value="gmsk">{t('vfo.decoders_modes.gmsk', 'GMSK')}</ToggleButton>
                                <ToggleButton value="gfsk">{t('vfo.decoders_modes.gfsk', 'GFSK')}</ToggleButton>
                                <ToggleButton value="bpsk">{t('vfo.decoders_modes.bpsk', 'BPSK')}</ToggleButton>
                                <ToggleButton value="afsk">{t('vfo.decoders_modes.afsk', 'AFSK')}</ToggleButton>
                                <ToggleButton value="weather">{t('vfo.decoders_modes.weather', 'Weather')}</ToggleButton>
                            </ToggleButtonGroup>

                            {/* Decoder Parameters Link - Click to open dialog */}
                            <Box sx={{ mt: 1.5, width: '100%' }}>
                                <Link
                                    component="button"
                                    variant="body2"
                                    disabled={!vfoActive[vfoIndex] || !vfoMarkers[vfoIndex]?.decoder || vfoMarkers[vfoIndex].decoder === 'none'}
                                    onClick={() => {
                                        setDecoderParamsVfoIndex(vfoIndex);
                                        setDecoderParamsDialogOpen(true);
                                    }}
                                    sx={{
                                        width: '100%',
                                        fontSize: '0.8rem',
                                        color: 'text.primary',
                                        textDecoration: 'none',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        gap: 0.75,
                                        py: 0.75,
                                        px: 1.5,
                                        borderRadius: 1,
                                        backgroundColor: vfoMarkers[vfoIndex]?.parametersEnabled ? 'rgba(33, 150, 243, 0.08)' : 'rgba(255, 255, 255, 0.05)',
                                        border: vfoMarkers[vfoIndex]?.parametersEnabled ? '1px solid rgba(33, 150, 243, 0.3)' : '1px solid rgba(255, 255, 255, 0.1)',
                                        transition: 'all 0.2s ease',
                                        '&:hover:not(.Mui-disabled)': {
                                            backgroundColor: vfoMarkers[vfoIndex]?.parametersEnabled ? 'rgba(33, 150, 243, 0.12)' : 'rgba(255, 255, 255, 0.08)',
                                            borderColor: vfoMarkers[vfoIndex]?.parametersEnabled ? 'rgba(33, 150, 243, 0.4)' : 'rgba(255, 255, 255, 0.2)',
                                        },
                                        '&.Mui-disabled': {
                                            backgroundColor: 'rgba(255, 255, 255, 0.02)',
                                            borderColor: 'rgba(255, 255, 255, 0.05)',
                                            color: 'rgba(255, 255, 255, 0.3)',
                                            opacity: 0.5,
                                            cursor: 'not-allowed',
                                        },
                                        cursor: 'pointer',
                                    }}
                                >
                                    <SettingsIcon sx={{ fontSize: '1rem', color: vfoMarkers[vfoIndex]?.parametersEnabled ? 'primary.main' : 'text.secondary' }} />
                                    <Box
                                        component="span"
                                        sx={{
                                            fontFamily: 'monospace',
                                            color: 'text.secondary',
                                            flex: 1,
                                            textDecoration: vfoMarkers[vfoIndex]?.decoder && vfoMarkers[vfoIndex].decoder !== 'none' && !vfoMarkers[vfoIndex]?.parametersEnabled ? 'line-through' : 'none',
                                        }}
                                    >
                                        {vfoMarkers[vfoIndex]?.decoder === 'none' || !vfoMarkers[vfoIndex]?.decoder
                                            ? '- no decoder -'
                                            : (formatDecoderParamsSummary(vfoIndex) || 'Decoder Parameters')}
                                    </Box>
                                </Link>
                            </Box>
                        </Box>

                        <Box sx={{ mt: 2 }}>
                            <Typography variant="body2" sx={{ mb: 1, color: 'text.secondary' }}>
                                {t('vfo.bandwidth')}
                            </Typography>
                            <ToggleButtonGroup
                                value={BANDWIDTHS.hasOwnProperty(vfoMarkers[vfoIndex]?.bandwidth) ? vfoMarkers[vfoIndex]?.bandwidth.toString() : 'custom'}
                                exclusive
                                disabled={
                                    !vfoActive[vfoIndex] ||
                                    isLockedBandwidth(
                                        vfoMarkers[vfoIndex]?.mode,
                                        vfoMarkers[vfoIndex]?.decoder
                                    )
                                }
                                onChange={(event, newValue) => {
                                    if (newValue !== null) {
                                        if (newValue === 'custom') {
                                            // Keep current value or set a default
                                            return;
                                        } else {
                                            onVFOPropertyChange(vfoIndex, { bandwidth: parseInt(newValue) });
                                        }
                                    }
                                }}
                                sx={{
                                    display: 'flex',
                                    flexWrap: 'wrap',
                                    gap: 0.5,
                                    '& .MuiToggleButton-root': {
                                        width: '75px',
                                        height: '28px',
                                        minWidth: '75px',
                                        maxWidth: '75px',
                                        padding: '4px 6px',
                                        fontSize: '0.8rem',
                                        border: '1px solid',
                                        borderColor: 'rgba(255, 255, 255, 0.23)',
                                        borderRadius: '4px',
                                        color: 'text.secondary',
                                        textAlign: 'center',
                                        textTransform: 'none',
                                        backgroundColor: 'rgba(255, 255, 255, 0.05)',
                                        transition: 'all 0.2s ease-in-out',
                                        '&.Mui-selected': {
                                            backgroundColor: 'primary.main',
                                            color: 'primary.contrastText',
                                            borderColor: 'primary.main',
                                            fontWeight: 600,
                                            boxShadow: '0 0 8px rgba(33, 150, 243, 0.4)',
                                            '&:hover': {
                                                backgroundColor: 'primary.dark',
                                                boxShadow: '0 0 12px rgba(33, 150, 243, 0.6)',
                                            }
                                        },
                                        '&:hover': {
                                            backgroundColor: 'rgba(255, 255, 255, 0.1)',
                                            borderColor: 'rgba(255, 255, 255, 0.4)',
                                        },
                                        '&.Mui-disabled': {
                                            backgroundColor: 'rgba(255, 255, 255, 0.02)',
                                            borderColor: 'rgba(255, 255, 255, 0.08)',
                                            color: 'rgba(255, 255, 255, 0.3)',
                                            opacity: 0.5,
                                        }
                                    }
                                }}
                            >
                                <ToggleButton value="custom">{t('vfo.custom')}</ToggleButton>
                                {Object.entries(BANDWIDTHS).map(([value, label]) => (
                                    <ToggleButton key={value} value={value}>
                                        {label}
                                    </ToggleButton>
                                ))}
                            </ToggleButtonGroup>
                        </Box>

                    </Box>
                ))}
            </AccordionDetails>

            {/* Transmitters Dialog */}
            <Dialog
                open={transmittersDialogOpen}
                onClose={() => setTransmittersDialogOpen(false)}
                maxWidth="xl"
                fullWidth
                PaperProps={{
                    sx: {
                        backgroundColor: 'background.elevated',
                    }
                }}
            >
                <DialogTitle sx={{ backgroundColor: 'background.elevated', color: 'text.primary' }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Typography variant="h6">
                            {targetSatelliteName} - Transmitters
                        </Typography>
                        <IconButton onClick={() => setTransmittersDialogOpen(false)} size="small">
                            <CloseIcon />
                        </IconButton>
                    </Box>
                </DialogTitle>
                <DialogContent dividers sx={{ p: 3, backgroundColor: 'background.elevated' }}>
                    {targetSatelliteData && (
                        <TransmittersTable satelliteData={targetSatelliteData} inDialog={true} />
                    )}
                </DialogContent>
            </Dialog>

            {/* Decoder Parameters Dialog */}
            <DecoderParamsDialog
                open={decoderParamsDialogOpen}
                onClose={() => setDecoderParamsDialogOpen(false)}
                vfoIndex={decoderParamsVfoIndex}
                vfoMarkers={vfoMarkers}
                vfoActive={vfoActive}
                onVFOPropertyChange={onVFOPropertyChange}
            />

            {/* Transcription Parameters Dialog */}
            <Dialog
                open={transcriptionParamsDialogOpen}
                onClose={() => setTranscriptionParamsDialogOpen(false)}
                maxWidth="sm"
                fullWidth
                PaperProps={{
                    sx: {
                        backgroundColor: 'background.elevated',
                    }
                }}
            >
                <DialogTitle sx={{ backgroundColor: 'background.elevated', color: 'text.primary' }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Typography variant="h6">
                            VFO {transcriptionParamsVfoIndex} - Transcription Parameters
                        </Typography>
                        <IconButton onClick={() => setTranscriptionParamsDialogOpen(false)} size="small">
                            <CloseIcon />
                        </IconButton>
                    </Box>
                </DialogTitle>
                <DialogContent dividers sx={{ p: 3, backgroundColor: 'background.elevated' }}>
                    {transcriptionParamsVfoIndex && vfoMarkers[transcriptionParamsVfoIndex] && (
                        <Box>
                            {!geminiConfigured && (
                                <Alert severity="warning" sx={{ mb: 2 }}>
                                    {t('vfo.configure_gemini', 'Configure Gemini API in Settings to enable transcription')}
                                </Alert>
                            )}

                            <Box sx={{ mb: 2.5 }}>
                                <FormControl fullWidth size="small" variant="filled">
                                    <InputLabel>{t('vfo.source_language', 'Source Language')}</InputLabel>
                                    <Select
                                        value={vfoMarkers[transcriptionParamsVfoIndex]?.transcriptionLanguage || 'auto'}
                                        label={t('vfo.source_language', 'Source Language')}
                                        onChange={(e) => onVFOPropertyChange(transcriptionParamsVfoIndex, { transcriptionLanguage: e.target.value })}
                                        disabled={!vfoMarkers[transcriptionParamsVfoIndex]?.transcriptionEnabled || !geminiConfigured}
                                        sx={{ fontSize: '0.875rem' }}
                                    >
                                        <MenuItem value="auto" sx={{ fontSize: '0.875rem' }}>🌐 {t('vfo.languages.auto', 'Auto-detect')}</MenuItem>
                                        <MenuItem value="en" sx={{ fontSize: '0.875rem' }}>🇬🇧 {t('vfo.languages.en', 'English')}</MenuItem>
                                        <MenuItem value="el" sx={{ fontSize: '0.875rem' }}>🇬🇷 {t('vfo.languages.el', 'Greek')}</MenuItem>
                                        <MenuItem value="es" sx={{ fontSize: '0.875rem' }}>🇪🇸 {t('vfo.languages.es', 'Spanish')}</MenuItem>
                                        <MenuItem value="fr" sx={{ fontSize: '0.875rem' }}>🇫🇷 {t('vfo.languages.fr', 'French')}</MenuItem>
                                        <MenuItem value="de" sx={{ fontSize: '0.875rem' }}>🇩🇪 {t('vfo.languages.de', 'German')}</MenuItem>
                                        <MenuItem value="it" sx={{ fontSize: '0.875rem' }}>🇮🇹 {t('vfo.languages.it', 'Italian')}</MenuItem>
                                        <MenuItem value="pt" sx={{ fontSize: '0.875rem' }}>🇵🇹 {t('vfo.languages.pt', 'Portuguese')}</MenuItem>
                                        <MenuItem value="pt-BR" sx={{ fontSize: '0.875rem' }}>🇧🇷 {t('vfo.languages.pt-BR', 'Portuguese (Brazil)')}</MenuItem>
                                        <MenuItem value="ru" sx={{ fontSize: '0.875rem' }}>🇷🇺 {t('vfo.languages.ru', 'Russian')}</MenuItem>
                                        <MenuItem value="uk" sx={{ fontSize: '0.875rem' }}>🇺🇦 {t('vfo.languages.uk', 'Ukrainian')}</MenuItem>
                                        <MenuItem value="ja" sx={{ fontSize: '0.875rem' }}>🇯🇵 {t('vfo.languages.ja', 'Japanese')}</MenuItem>
                                        <MenuItem value="zh" sx={{ fontSize: '0.875rem' }}>🇨🇳 {t('vfo.languages.zh', 'Chinese')}</MenuItem>
                                        <MenuItem value="ar" sx={{ fontSize: '0.875rem' }}>🇸🇦 {t('vfo.languages.ar', 'Arabic')}</MenuItem>
                                        <MenuItem value="tl" sx={{ fontSize: '0.875rem' }}>🇵🇭 {t('vfo.languages.tl', 'Filipino')}</MenuItem>
                                        <MenuItem value="tr" sx={{ fontSize: '0.875rem' }}>🇹🇷 {t('vfo.languages.tr', 'Turkish')}</MenuItem>
                                        <MenuItem value="sk" sx={{ fontSize: '0.875rem' }}>🇸🇰 {t('vfo.languages.sk', 'Slovak')}</MenuItem>
                                        <MenuItem value="hr" sx={{ fontSize: '0.875rem' }}>🇭🇷 {t('vfo.languages.hr', 'Croatian')}</MenuItem>
                                    </Select>
                                </FormControl>
                            </Box>

                            {/* Translation */}
                            <Box sx={{ mb: 2.5 }}>
                                <FormControl fullWidth size="small" variant="filled">
                                    <InputLabel>{t('vfo.translate_to', 'Translate To')}</InputLabel>
                                    <Select
                                        value={vfoMarkers[transcriptionParamsVfoIndex]?.transcriptionTranslateTo || 'none'}
                                        label={t('vfo.translate_to', 'Translate To')}
                                        onChange={(e) => onVFOPropertyChange(transcriptionParamsVfoIndex, { transcriptionTranslateTo: e.target.value })}
                                        disabled={!vfoMarkers[transcriptionParamsVfoIndex]?.transcriptionEnabled}
                                        sx={{ fontSize: '0.875rem' }}
                                    >
                                        <MenuItem value="none" sx={{ fontSize: '0.875rem' }}>⭕ {t('vfo.languages.none', 'No Translation')}</MenuItem>
                                        <MenuItem value="en" sx={{ fontSize: '0.875rem' }}>🇬🇧 {t('vfo.languages.en', 'English')}</MenuItem>
                                        <MenuItem value="el" sx={{ fontSize: '0.875rem' }}>🇬🇷 {t('vfo.languages.el', 'Greek')}</MenuItem>
                                        <MenuItem value="es" sx={{ fontSize: '0.875rem' }}>🇪🇸 {t('vfo.languages.es', 'Spanish')}</MenuItem>
                                        <MenuItem value="fr" sx={{ fontSize: '0.875rem' }}>🇫🇷 {t('vfo.languages.fr', 'French')}</MenuItem>
                                        <MenuItem value="de" sx={{ fontSize: '0.875rem' }}>🇩🇪 {t('vfo.languages.de', 'German')}</MenuItem>
                                        <MenuItem value="it" sx={{ fontSize: '0.875rem' }}>🇮🇹 {t('vfo.languages.it', 'Italian')}</MenuItem>
                                        <MenuItem value="pt" sx={{ fontSize: '0.875rem' }}>🇵🇹 {t('vfo.languages.pt', 'Portuguese')}</MenuItem>
                                        <MenuItem value="pt-BR" sx={{ fontSize: '0.875rem' }}>🇧🇷 {t('vfo.languages.pt-BR', 'Portuguese (Brazil)')}</MenuItem>
                                        <MenuItem value="ru" sx={{ fontSize: '0.875rem' }}>🇷🇺 {t('vfo.languages.ru', 'Russian')}</MenuItem>
                                        <MenuItem value="uk" sx={{ fontSize: '0.875rem' }}>🇺🇦 {t('vfo.languages.uk', 'Ukrainian')}</MenuItem>
                                        <MenuItem value="ja" sx={{ fontSize: '0.875rem' }}>🇯🇵 {t('vfo.languages.ja', 'Japanese')}</MenuItem>
                                        <MenuItem value="zh" sx={{ fontSize: '0.875rem' }}>🇨🇳 {t('vfo.languages.zh', 'Chinese')}</MenuItem>
                                        <MenuItem value="ar" sx={{ fontSize: '0.875rem' }}>🇸🇦 {t('vfo.languages.ar', 'Arabic')}</MenuItem>
                                        <MenuItem value="tl" sx={{ fontSize: '0.875rem' }}>🇵🇭 {t('vfo.languages.tl', 'Filipino')}</MenuItem>
                                        <MenuItem value="tr" sx={{ fontSize: '0.875rem' }}>🇹🇷 {t('vfo.languages.tr', 'Turkish')}</MenuItem>
                                        <MenuItem value="sk" sx={{ fontSize: '0.875rem' }}>🇸🇰 {t('vfo.languages.sk', 'Slovak')}</MenuItem>
                                        <MenuItem value="hr" sx={{ fontSize: '0.875rem' }}>🇭🇷 {t('vfo.languages.hr', 'Croatian')}</MenuItem>
                                    </Select>
                                </FormControl>
                            </Box>

                            {/* Deepgram translation info */}
                            {vfoMarkers[transcriptionParamsVfoIndex]?.transcriptionProvider === 'deepgram' &&
                             vfoMarkers[transcriptionParamsVfoIndex]?.transcriptionTranslateTo &&
                             vfoMarkers[transcriptionParamsVfoIndex]?.transcriptionTranslateTo !== 'none' && (
                                <Alert severity="info" sx={{ mb: 2, fontSize: '0.75rem' }}>
                                    {t('vfo.deepgram_translation_info', 'Deepgram transcribes audio. Translation uses Google Translate API (configured in Settings).')}
                                </Alert>
                            )}

                            {/* Transcription Stats Display */}
                            {(() => {
                                const decoderInfo = getVFODecoderInfo(transcriptionParamsVfoIndex);
                                // Check if this is a transcription decoder
                                if (!decoderInfo || decoderInfo.decoder_type !== 'transcription') return null;

                                const info = decoderInfo.info || {};
                                const isConnected = decoderInfo.status === 'transcribing';
                                const successRate = info.transcriptions_sent > 0
                                    ? Math.round((info.transcriptions_received / info.transcriptions_sent) * 100)
                                    : 0;

                                return (
                                    <Box sx={{
                                        mt: 2,
                                        px: 2,
                                        py: 1.5,
                                        backgroundColor: 'rgba(0, 0, 0, 0.2)',
                                        borderRadius: 1,
                                        border: '1px solid',
                                        borderColor: isConnected ? 'success.dark' : 'error.dark',
                                    }}>
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                                            <Box
                                                sx={{
                                                    width: 10,
                                                    height: 10,
                                                    borderRadius: '50%',
                                                    backgroundColor: isConnected ? 'success.main' : 'error.main',
                                                    boxShadow: (theme) => isConnected
                                                        ? `0 0 8px ${theme.palette.success.main}99`
                                                        : `0 0 8px ${theme.palette.error.main}99`,
                                                }}
                                            />
                                            <Typography variant="body2" sx={{
                                                fontFamily: 'monospace',
                                                color: 'text.primary',
                                                fontWeight: 600
                                            }}>
                                                {isConnected ? 'Transcribing' : 'Disconnected'}
                                                {info.provider && ` (${info.provider.charAt(0).toUpperCase() + info.provider.slice(1)})`}
                                            </Typography>
                                        </Box>
                                        <Typography variant="body2" sx={{
                                            fontFamily: 'monospace',
                                            color: 'text.secondary',
                                            display: 'block'
                                        }}>
                                            Sent: {info.transcriptions_sent || 0} • Received: {info.transcriptions_received || 0} • Success Rate: {successRate}%
                                        </Typography>
                                        {info.errors > 0 && (
                                            <Typography variant="body2" sx={{
                                                fontFamily: 'monospace',
                                                color: 'error.main',
                                                display: 'block',
                                                mt: 0.5
                                            }}>
                                                Errors: {info.errors}
                                            </Typography>
                                        )}
                                    </Box>
                                );
                            })()}

                            <Box sx={{
                                mt: 2,
                                display: 'flex',
                                justifyContent: 'center',
                                alignItems: 'center',
                                fontSize: '0.875rem',
                                color: 'text.secondary',
                                gap: 0.5
                            }}>
                                ✨ Powered by Gemini
                            </Box>
                        </Box>
                    )}
                </DialogContent>
            </Dialog>
        </Accordion>
    );
};

export default VfoAccordion;