/**
 * @license
 * Copyright (c) 2025 Efstratios Goudelis
 * Modifications and extensions Copyright (C) 2026 DynamiX-Labs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program. If not, see <https://www.gnu.org/licenses/>.
 *
 */


import Stack from "@mui/material/Stack";
import {ThemeSwitcher} from "@toolpad/core/DashboardLayout";
import Typography from "@mui/material/Typography";
import PropTypes from "prop-types";
import * as React from "react";
import {Outlet, useNavigate, useLocation} from "react-router";
import {
    AppBar,
    Avatar,
    Backdrop,
    Box,
    Button,
    CssBaseline,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogContentText,
    DialogActions,
    Divider,
    Drawer,
    IconButton,
    List,
    ListItem,
    ListItemButton,
    ListItemIcon,
    ListItemText,
    MenuItem,
    MenuList,
    Toolbar,
    useTheme,
    styled
} from "@mui/material";
import {Account, AccountPopoverFooter, AccountPreview, SignOutButton} from "@toolpad/core";
import {stringAvatar} from "../common/common.jsx";
import Grid from "@mui/material/Grid";
import BorderColorIcon from '@mui/icons-material/BorderColor';
import {useCallback, useEffect, useRef, useState} from "react";
import {setGridEditable as setOverviewGridEditable} from '../overview/overview-slice.jsx';
import {setGridEditable as setTargetGridEditable} from '../target/target-slice.jsx';
import {setGridEditable as setWaterfallGridEditable} from '../waterfall/waterfall-slice.jsx';
import CheckIcon from '@mui/icons-material/Check';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import {useSocket} from "../common/socket.jsx";
import {useDispatch, useSelector} from "react-redux";
import { useTranslation } from 'react-i18next';
import { setIsEditing, setShowLocationSetupDialog } from "./dashboard-slice.jsx";
import { addStreamingVFO, removeStreamingVFO } from "../waterfall/vfo-marker/vfo-slice.jsx";
import WakeLockStatus from "./wake-lock-icon.jsx";
import ConnectionStatus from "./connection-popover.jsx";
import Tooltip from "@mui/material/Tooltip";
import { AudioProvider, useAudio } from "./audio-provider.jsx";
import HardwareSettingsPopover from "./hardware-popover.jsx";
import LocationWarningPopover from "./location-popover.jsx";
import ConnectionOverlay from "./reconnecting-overlay.jsx";
import SatelliteInfoPopover from "./target-popover.jsx";
import VersionInfo from "./version-info.jsx";
import VersionUpdateOverlay from "./version-update-overlay.jsx";
import UpdateIndicator from "./update-indicator.jsx";
import PerformanceMetricsDialog from "../performance/performance-metrics-dialog.jsx";
import BackgroundTasksPopover from "../tasks/tasks-popover.jsx";
import MenuIcon from '@mui/icons-material/Menu';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import {getNavigation} from "../../config/navigation.jsx";
import { useUserTimeSettings } from '../../hooks/useUserTimeSettings.jsx';
import { formatTime } from '../../utils/date-time.js';

// Drawer widths
const drawerWidthExpanded = 240;
const drawerWidthCollapsed = 56;

// Styled components
const openedMixin = (theme) => ({
    width: drawerWidthExpanded,
    transition: theme.transitions.create('width', {
        easing: theme.transitions.easing.sharp,
        duration: theme.transitions.duration.enteringScreen,
    }),
    overflowX: 'hidden',
});

const closedMixin = (theme) => ({
    transition: theme.transitions.create('width', {
        easing: theme.transitions.easing.sharp,
        duration: theme.transitions.duration.leavingScreen,
    }),
    overflowX: 'hidden',
    width: drawerWidthCollapsed,
});

const CustomDrawer = styled(Drawer, { shouldForwardProp: (prop) => prop !== 'open' })(
    ({ theme, open }) => ({
        width: open ? drawerWidthExpanded : drawerWidthCollapsed,
        flexShrink: 0,
        whiteSpace: 'nowrap',
        boxSizing: 'border-box',
        ...(open && {
            ...openedMixin(theme),
            '& .MuiDrawer-paper': openedMixin(theme),
        }),
        ...(!open && {
            ...closedMixin(theme),
            '& .MuiDrawer-paper': closedMixin(theme),
        }),
    }),
);

const CustomAppBar = styled(AppBar, {
    shouldForwardProp: (prop) => prop !== 'open',
})(({ theme, open }) => ({
    zIndex: theme.zIndex.drawer + 1,
    ...(theme.palette.mode === 'dark' ? {
        backgroundColor: `${theme.palette.background.appBar || theme.palette.surface.appBar} !important`,
        backgroundImage: 'none',
        '&.MuiAppBar-colorPrimary': {
            backgroundColor: `${theme.palette.background.appBar || theme.palette.surface.appBar} !important`,
        },
    } : {}),
}));

function DashboardEditor() {
    const theme = useTheme();
    const dispatch = useDispatch();
    const { t } = useTranslation('dashboard');
    const {isEditing} = useSelector(state => state.dashboard);

    const handleEditClick = () => {
        // Use Redux actions directly for production-safe behavior.
        // The previous approach relied on mutable callbacks exported from page modules, which can
        // become brittle under optimized/code-split production bundles.
        dispatch(setIsEditing(true));
        dispatch(setOverviewGridEditable(true));
        dispatch(setTargetGridEditable(true));
        dispatch(setWaterfallGridEditable(true));
    };

    const handleSaveClick = () => {
        dispatch(setIsEditing(false));
        dispatch(setOverviewGridEditable(false));
        dispatch(setTargetGridEditable(false));
        dispatch(setWaterfallGridEditable(false));
    };

    const handleCancelClick = () => {
        dispatch(setIsEditing(false));
        dispatch(setOverviewGridEditable(false));
        dispatch(setTargetGridEditable(false));
        dispatch(setWaterfallGridEditable(false));
    };

    return (
        <>
            {isEditing ? (
                <Stack direction="row" spacing={2}>
                    <Tooltip title={t('layout.done_editing')}>
                        <IconButton size="small" onClick={handleSaveClick} sx={{
                            width: 40,
                        }}>
                            <CheckIcon color="success"/>
                        </IconButton>
                    </Tooltip>
                </Stack>
            ) : (
                <Tooltip title={t('layout.edit_layout')}>
                        <IconButton size="small" onClick={handleEditClick} sx={{
                            width: 40,
                        }}>
                            <BorderColorIcon sx={{
                            color: theme.palette.primary.main
                        }}/>
                    </IconButton>
                </Tooltip>
            )}
        </>
    );
}

function ToolbarActions() {
    return (
        <Stack direction="row" sx={{padding: "6px 0px 0px 0px"}}>
            <ConnectionStatus />
            <LocationWarningPopover />
            <SatelliteInfoPopover />
            <HardwareSettingsPopover />
            <BackgroundTasksPopover />
            <WakeLockStatus />
            <DashboardEditor />
            <TimeDisplay />
            <ThemeSwitcher />
        </Stack>
    );
}

const MemoToolbarActions = React.memo(ToolbarActions);

function ActiveObservationIndicator() {
    const observations = useSelector((state) => state.scheduler?.observations || []);
    const { timezone, locale } = useUserTimeSettings();
    const [nowMs, setNowMs] = React.useState(() => Date.now());

    const runningObservations = React.useMemo(
        () => observations.filter((obs) => obs.status === 'running' && obs.enabled),
        [observations]
    );

    React.useEffect(() => {
        const interval = setInterval(() => setNowMs(Date.now()), 1000);
        return () => clearInterval(interval);
    }, []);

    if (!runningObservations.length) {
        return null;
    }

    const primaryObservation = runningObservations[0];
    const endTimeIso = primaryObservation.task_end || primaryObservation.pass?.event_end;
    const startTimeIso = primaryObservation.task_start || primaryObservation.pass?.event_start;
    const formattedEndTime = endTimeIso
        ? formatTime(endTimeIso, {
            timezone,
            locale,
            options: { hour: '2-digit', minute: '2-digit', hour12: false },
        })
        : null;
    const formattedStartTime = startTimeIso
        ? formatTime(startTimeIso, {
            timezone,
            locale,
            options: { hour: '2-digit', minute: '2-digit', hour12: false },
        })
        : null;
    const peakAltitude = primaryObservation.pass?.peak_altitude;

    const getRemainingText = (observation) => {
        const endIso = observation.task_end || observation.pass?.event_end;
        if (!endIso) {
            return 'ending time unavailable';
        }
        const endTime = new Date(endIso);
        const remainingMs = endTime.getTime() - nowMs;
        if (remainingMs <= 0) {
            return 'ending soon';
        }
        const hours = Math.floor(remainingMs / 3600000);
        const minutes = Math.floor((remainingMs % 3600000) / 60000);
        const seconds = Math.floor((remainingMs % 60000) / 1000);
        if (hours > 0) return `${hours}h ${minutes}m ${seconds}s left`;
        if (minutes > 0) return `${minutes}m ${seconds}s left`;
        return `${seconds}s left`;
    };

    return (
        <Box
            sx={{
                display: 'none',
                '@media (min-width:1400px)': {
                    display: 'flex',
                },
                alignItems: 'center',
                gap: 0.75,
                px: 1.25,
                py: 0.4,
                mx: 1,
                borderRadius: 1,
                border: '1px solid',
                borderColor: 'success.light',
                backgroundColor: (theme) =>
                    theme.palette.mode === 'dark'
                        ? 'rgba(76, 175, 80, 0.18)'
                        : 'rgba(76, 175, 80, 0.12)',
                minWidth: 0,
                maxWidth: 760,
                flexShrink: 1,
                overflow: 'hidden',
            }}
            aria-label="Active observation indicator"
        >
            <FiberManualRecordIcon
                sx={{
                    fontSize: 10,
                    color: 'success.main',
                    animation: 'observationPulse 1.6s ease-in-out infinite',
                    '@keyframes observationPulse': {
                        '0%, 100%': { opacity: 1 },
                        '50%': { opacity: 0.45 },
                    },
                }}
            />
            <Typography
                variant="caption"
                sx={{
                    fontWeight: 600,
                    color: 'success.main',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                }}
            >
                {runningObservations.length > 1
                    ? `Observing ${runningObservations.length}: ${primaryObservation.satellite?.name || 'Unknown'} +${runningObservations.length - 1}`
                    : `Observing: ${primaryObservation.satellite?.name || 'Unknown'}`}
            </Typography>
            {primaryObservation.satellite?.norad_id && (
                <Typography
                    variant="caption"
                    sx={{
                        color: 'text.secondary',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                    }}
                >
                    ({primaryObservation.satellite.norad_id})
                </Typography>
            )}
            {(formattedEndTime || runningObservations.length > 0) && (
                <Typography
                    variant="caption"
                    sx={{
                        color: 'text.secondary',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                    }}
                >
                    • {formattedEndTime ? `ends ${formattedEndTime}` : ''}{formattedEndTime ? ' • ' : ''}{getRemainingText(primaryObservation)}
                </Typography>
            )}
            {formattedStartTime && runningObservations.length === 1 && (
                <Typography
                    variant="caption"
                    sx={{
                        color: 'text.secondary',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                    }}
                >
                    • started {formattedStartTime}
                </Typography>
            )}
            {typeof peakAltitude === 'number' && (
                <Typography
                    variant="caption"
                    sx={{
                        color: 'text.secondary',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                    }}
                >
                    • peak {peakAltitude.toFixed(0)}°
                </Typography>
            )}
        </Box>
    );
}

function UpcomingObservationIndicator() {
    const observations = useSelector((state) => state.scheduler?.observations || []);
    const { timezone, locale } = useUserTimeSettings();
    const [nowMs, setNowMs] = React.useState(() => Date.now());

    React.useEffect(() => {
        const interval = setInterval(() => setNowMs(Date.now()), 1000);
        return () => clearInterval(interval);
    }, []);

    const { runningCount, nextObservation, timeUntilStartMs } = React.useMemo(() => {
        const now = new Date(nowMs);
        const running = observations.filter((obs) => obs.status === 'running' && obs.enabled);
        const upcoming = observations
            .filter((obs) => {
                if (!obs.enabled || obs.status !== 'scheduled') return false;
                const start = obs.task_start || obs.pass?.event_start;
                return !!start;
            })
            .map((obs) => ({
                ...obs,
                startTime: new Date(obs.task_start || obs.pass?.event_start),
            }))
            .filter((obs) => obs.startTime > now)
            .sort((a, b) => a.startTime - b.startTime)[0];

        const timeUntil = upcoming ? upcoming.startTime - now : null;
        return { runningCount: running.length, nextObservation: upcoming, timeUntilStartMs: timeUntil };
    }, [observations, nowMs]);

    if (runningCount > 0 || !nextObservation || !timeUntilStartMs || timeUntilStartMs > 60000 || timeUntilStartMs <= 0) {
        return null;
    }

    const startTimeIso = nextObservation.task_start || nextObservation.pass?.event_start;
    const formattedStartTime = startTimeIso
        ? formatTime(startTimeIso, {
            timezone,
            locale,
            options: { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false },
        })
        : null;
    const peakAltitude = nextObservation.pass?.peak_altitude;
    const totalSeconds = Math.ceil(timeUntilStartMs / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    const countdownText = `${minutes}:${String(seconds).padStart(2, '0')}`;

    return (
        <Box
            sx={{
                display: 'none',
                '@media (min-width:1400px)': {
                    display: 'flex',
                },
                alignItems: 'center',
                gap: 0.75,
                px: 1.25,
                py: 0.4,
                mx: 1,
                borderRadius: 1,
                border: '1px solid',
                borderColor: 'info.light',
                backgroundColor: (theme) =>
                    theme.palette.mode === 'dark'
                        ? 'rgba(33, 150, 243, 0.20)'
                        : 'rgba(33, 150, 243, 0.12)',
                minWidth: 0,
                maxWidth: 760,
                flexShrink: 1,
                overflow: 'hidden',
            }}
            aria-label="Upcoming observation indicator"
        >
            <AccessTimeIcon
                sx={{
                    fontSize: 12,
                    color: 'info.main',
                    animation: 'upcomingObservationPulse 1.2s ease-in-out infinite',
                    '@keyframes upcomingObservationPulse': {
                        '0%, 100%': { opacity: 1 },
                        '50%': { opacity: 0.5 },
                    },
                }}
            />
            <Typography
                variant="caption"
                sx={{
                    fontWeight: 700,
                    color: 'info.main',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                }}
            >
                Starting Soon: {nextObservation.satellite?.name || 'Unknown'}
            </Typography>
            {nextObservation.satellite?.norad_id && (
                <Typography
                    variant="caption"
                    sx={{
                        color: 'text.secondary',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                    }}
                >
                    ({nextObservation.satellite.norad_id})
                </Typography>
            )}
            <Typography
                variant="caption"
                sx={{
                    color: 'info.main',
                    fontWeight: 700,
                    whiteSpace: 'nowrap',
                }}
            >
                • T-{countdownText}
            </Typography>
            {formattedStartTime && (
                <Typography
                    variant="caption"
                    sx={{
                        color: 'text.secondary',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                    }}
                >
                    • starts {formattedStartTime}
                </Typography>
            )}
            {typeof peakAltitude === 'number' && (
                <Typography
                    variant="caption"
                    sx={{
                        color: 'text.secondary',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                    }}
                >
                    • peak {peakAltitude.toFixed(0)}°
                </Typography>
            )}
        </Box>
    );
}

function SidebarFooter({ mini }) {
    return (
        <Typography variant="caption" sx={{ m: 1, whiteSpace: 'nowrap', overflow: 'hidden' }}>
            {mini ? '© MUI' : `© ${new Date().getFullYear()} Made with love by MUI`}
        </Typography>
    );
}

SidebarFooter.propTypes = {
    mini: PropTypes.bool.isRequired,
};

function CustomAppTitle() {
    return (
        <Grid container direction="row">
            <Grid row={1} column={1} sx={{display: 'flex', alignItems: 'center'}}>
                <Stack direction="row" alignItems="center" spacing={2}>
                    <Box display={{xs: "none", sm: "block"}}>
                        <Box display="flex" alignItems="center" gap={1}>
                            <img src="/dynamix_labs_logo.png" alt="DynamiX-Labs" width="30" height="30" />
                            <Typography variant="h6">DynamiX-Labs</Typography>
                            {/* Hide version indicator on phones and small tablets; show from ~768px and up */}
                            <Box sx={{
                                display: 'none',
                                '@media (min-width:768px)': {
                                    display: 'block',
                                },
                            }}>
                                <Stack direction="row" spacing={1} alignItems="center">
                                    <VersionInfo minimal={true}/>
                                    <UpdateIndicator />
                                </Stack>
                            </Box>
                        </Box>
                    </Box>
                    <Box display={{xs: "block", sm: "none"}}>
                        <Typography variant="h6"></Typography>
                    </Box>
                </Stack>
            <Grid/>
            <Grid spacing={3} row={1} column={1}>
                <Grid container direction="row" spacing={4}>
                    <Grid>
                    </Grid>
                </Grid>
            </Grid>
            </Grid>
        </Grid>
    );
}

function AccountSidebarPreview(props) {
    const { handleClick, open, mini } = props;
    return (
        <Stack direction="column" p={0}>
            <Divider />
            <AccountPreview
                variant={mini ? 'condensed' : 'expanded'}
                handleClick={handleClick}
                open={open}
            />
        </Stack>
    );
}

AccountSidebarPreview.propTypes = {
    /**
     * The handler used when the preview is expanded
     */
    handleClick: PropTypes.func,
    mini: PropTypes.bool.isRequired,
    /**
     * The state of the Account popover
     * @default false
     */
    open: PropTypes.bool,
};

const accounts = [
    {
        id: 1,
        name: 'Efstratios Goudelis',
        email: 'sgoudelis@nerv.home',
        image: null,
        projects: [
            {
                id: 3,
                title: 'Project X',
            },
        ],
    }
];

function TimeDisplay() {
    const [isUTC, setIsUTC] = React.useState(false); // Toggle between UTC and Local Time
    const [currentTime, setCurrentTime] = React.useState(new Date());
    const { timezone, locale } = useUserTimeSettings();

    // Update the time every second
    React.useEffect(() => {
        const interval = setInterval(() => setCurrentTime(new Date()), 1000);
        return () => clearInterval(interval); // Cleanup on unmount
    }, []);

    // Format time based on whether it's UTC or local
    const formattedTime = isUTC
        ? formatTime(currentTime, {
            timezone: 'UTC',
            locale,
            options: { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false },
        })
        : formatTime(currentTime, {
            timezone,
            locale,
            options: { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false },
        });

    const timeZoneAbbr = isUTC
        ? 'UTC'
        : new Intl.DateTimeFormat(locale, { timeZone: timezone, timeZoneName: 'short' })
            .formatToParts(currentTime)
            .find((part) => part.type === 'timeZoneName')?.value || timezone;

    return (
        <Box
            onClick={() => setIsUTC(!isUTC)} // Toggle between UTC and Local Time on click
            sx={{
                cursor: "pointer",
                p: 0,
                paddingTop: 0.75,
                paddingBottom: 0,
                borderRadius: "4px",
                textAlign: "center",
                maxWidth: "100px",
                display: "flex",
                flexDirection: "column",
                alignItems: "center"
            }}
        >
            <Typography variant="body2" sx={{fontSize: "0.65rem", fontWeight: "bold", fontFamily: "monospace"}}>
                {formattedTime}
            </Typography>
            <Typography variant="caption" sx={{fontSize: "0.65rem", fontFamily: "monospace", color: "text.secondary"}}>
                {isUTC ? "UTC" : timeZoneAbbr}
            </Typography>
        </Box>
    );
}

function SidebarFooterAccountPopover() {
    return (
        <Stack direction="column" sx={{
            pl: '0px',
            pr: '0px',
        }}>
            <Typography variant="body2" mx={2} mt={1}>
                Accounts
            </Typography>
            <MenuList>
                {accounts.map((account) => (
                    <MenuItem
                        key={account.id}
                        component="button"
                        sx={{
                            justifyContent: 'flex-start',
                            width: '100%',
                            columnGap: 2,
                        }}
                    >
                        <ListItemIcon>
                            <Avatar {...stringAvatar('My Name')} />
                        </ListItemIcon>
                        <ListItemText
                            sx={{
                                display: 'flex',
                                flexDirection: 'column',
                                alignItems: 'flex-start',
                                width: '100%',
                            }}
                            primary={account.name}
                            secondary={account.email}
                        />
                    </MenuItem>
                ))}
            </MenuList>
            <Divider />
            <AccountPopoverFooter>
                <SignOutButton />
            </AccountPopoverFooter>
        </Stack>
    );
}

function SidebarFooterAccount({ mini }) {
    const PreviewComponent = React.useMemo(() => createPreviewComponent(mini), [mini]);
    return (
        <Account
            slots={{
                preview: PreviewComponent,
                popoverContent: SidebarFooterAccountPopover,
            }}
            slotProps={{
                popover: {
                    transformOrigin: { horizontal: 'left', vertical: 'bottom' },
                    anchorOrigin: { horizontal: 'right', vertical: 'bottom' },
                    disableAutoFocus: true,
                    slotProps: {
                        paper: {
                            elevation: 0,
                            sx: {
                                overflow: 'visible',
                                // filter: (theme) => `drop-shadow(0px 2px 8px ${theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.10)' : 'rgba(0,0,0,0.32)'})`,
                                mt: 1,
                                '&::before': {
                                    content: '""',
                                    display: 'block',
                                    position: 'absolute',
                                    bottom: 10,
                                    left: 0,
                                    width: 10,
                                    height: 10,
                                    bgcolor: 'background.paper',
                                    transform: 'translate(-50%, -50%) rotate(45deg)',
                                    zIndex: 0,
                                },
                            },
                        },
                    },
                },
            }}
        />
    );
}

SidebarFooterAccount.propTypes = {
    mini: PropTypes.bool.isRequired,
};

const createPreviewComponent = (mini) => {
    function PreviewComponent(props) {
        return <AccountSidebarPreview {...props} mini={mini} />;
    }
    return PreviewComponent;
};

export default function Layout() {
    const theme = useTheme();
    const dispatch = useDispatch();
    const navigate = useNavigate();
    const location = useLocation();
    const { socket } = useSocket();
    const { t } = useTranslation();
    const [open, setOpen] = React.useState(false);
    const [mobileOpen, setMobileOpen] = React.useState(false);
    const preferences = useSelector((state) => state.preferences?.preferences || []);
    const celestialEnabledPreference = preferences.find((pref) => pref.name === 'celestial_enabled');
    const showCelestial = String(celestialEnabledPreference?.value ?? 'false').toLowerCase() === 'true';
    const [navigation, setNavigation] = React.useState(getNavigation({ showCelestial }));
    const { timezone, locale } = useUserTimeSettings();

    const {
        connecting,
        connected,
        disconnected,
        reConnectAttempt,
        connectionError,
        initialDataLoading,
        showLocationSetupDialog,
    } = useSelector((state) => state.dashboard);
    const {
        hasVersionChanged,
        data
    } = useSelector((state) => state.version);

    // Use the audio context
    const { initializeAudio, playAudioSamples, getAudioState } = useAudio();
    const streamingTimeoutsRef = useRef({}); // Track per-VFO timeouts
    const streamingVFOsRef = useRef([]); // Track which VFOs are streaming (ref to avoid useEffect re-runs)
    const streamingVFOs = useSelector((state) => state.vfo.streamingVFOs); // Get Redux state for syncing
    const isStreaming = useSelector((state) => state.waterfall.isStreaming); // Get streaming state to filter audio

    // Sync ref with Redux state
    useEffect(() => {
        streamingVFOsRef.current = streamingVFOs;
    }, [streamingVFOs]);

    // Update navigation when language changes or state changes
    React.useEffect(() => {
        setNavigation(getNavigation({ showCelestial }));
    }, [t, showCelestial]);

    useEffect(() => {
        console.info('Initializing audio...');

        // Check if audio is enabled before trying to play
        const audioState = getAudioState();
        if (!audioState.enabled) {
            initializeAudio()
                .then(() => {
                    console.info('Audio initialized successfully');
                })
                .catch((error) => {
                    console.error('Error initializing audio', error);
                });
        }
    }, []);

    useEffect(() => {
        if (socket) {
            socket.on("audio-data", (data) => {
                // Extract VFO number from audio data
                const vfoNumber = data.vfo?.vfo_number;

                if (vfoNumber !== undefined) {
                    // Clear previous timeout for this VFO
                    if (streamingTimeoutsRef.current[vfoNumber]) {
                        clearTimeout(streamingTimeoutsRef.current[vfoNumber]);
                    }

                    // Only dispatch if VFO is not already marked as streaming
                    // This prevents flooding Redux store with redundant actions
                    // Use ref instead of state to avoid triggering useEffect re-runs
                    if (!streamingVFOsRef.current.includes(vfoNumber)) {
                        dispatch(addStreamingVFO(vfoNumber));
                    }

                    // Set timeout to remove this VFO from streaming after 500ms of no audio
                    streamingTimeoutsRef.current[vfoNumber] = setTimeout(() => {
                        delete streamingTimeoutsRef.current[vfoNumber];
                        dispatch(removeStreamingVFO(vfoNumber));
                    }, 500);
                }

                // Only play audio if streaming (prevents delayed audio after stop)
                if (isStreaming) {
                    playAudioSamples(data);
                }
            });
        }

        return () => {
            if (socket) {
                socket.off("audio-data");
            }
            // Clear all VFO timeouts on cleanup
            Object.values(streamingTimeoutsRef.current).forEach(timeout => {
                clearTimeout(timeout);
            });
            streamingTimeoutsRef.current = {};
        };
    }, [socket, playAudioSamples, dispatch, isStreaming]);

    const handleDrawerToggle = () => {
        // On mobile, toggle the temporary drawer
        if (window.innerWidth < 600) {
            setMobileOpen(!mobileOpen);
        } else {
            // On desktop, toggle between collapsed/expanded
            setOpen(!open);
        }
    };

    const handleMobileDrawerClose = () => {
        setMobileOpen(false);
    };

    const handleNavigation = (segment) => {
        navigate(`/${segment}`);
        // Close mobile drawer after navigation
        if (window.innerWidth < 600) {
            setMobileOpen(false);
        }
    };

    const isActiveRoute = (segment) => {
        const currentPath = location.pathname.slice(1); // Remove leading slash
        if (segment === '' && currentPath === '') return true;
        if (
            segment === 'settings/preferences' &&
            (
                currentPath.startsWith('settings/backend')
                || currentPath.startsWith('settings/settings')
                || currentPath.startsWith('settings/preferences')
                || currentPath.startsWith('settings/integrations')
                || currentPath.startsWith('settings/location')
            )
        ) {
            return true;
        }
        if (segment && currentPath.startsWith(segment)) return true;
        return false;
    };

    // Get scheduler state for dynamic tooltip
    const schedulerObservations = useSelector((state) => state.scheduler?.observations || []);

    /**
     * Get comprehensive scheduler observation information
     * Returns details about running observation and next upcoming observation
     */
    const getSchedulerObservationInfo = () => {
        const now = new Date();

        // Find running observations
        const runningObservations = schedulerObservations.filter(
            obs => obs.status === 'running' && obs.enabled
        );

        // Find next enabled scheduled observation
        const nextObservation = schedulerObservations
            .filter(obs => obs.status === 'scheduled' && obs.enabled && (obs.task_start || obs.pass?.event_start))
            .map(obs => ({
                ...obs,
                startTime: new Date(obs.task_start || obs.pass.event_start),
            }))
            .filter(obs => obs.startTime > now)
            .sort((a, b) => a.startTime - b.startTime)[0];

        return { runningObservations, nextObservation };
    };

    const { runningObservations, nextObservation } = getSchedulerObservationInfo();

    // Helper function to format time remaining/until
    const formatTimeUntil = (targetDate) => {
        const now = new Date();
        const ms = targetDate - now;
        const hours = Math.floor(ms / 3600000);
        const minutes = Math.floor((ms % 3600000) / 60000);

        if (hours > 24) {
            const days = Math.floor(hours / 24);
            return `${days}d ${hours % 24}h`;
        } else if (hours > 0) {
            return `${hours}h ${minutes}m`;
        } else {
            return `${minutes}m`;
        }
    };

    // Helper function to get tooltip text
    const getTooltipText = (item, drawerExpanded) => {
        if (!drawerExpanded) {
            // For scheduler, show comprehensive dynamic tooltip
            if (item.segment === 'scheduler') {
                const parts = [];

                // Show running observations (up to 3 lines)
                if (runningObservations.length > 0) {
                    const primary = runningObservations[0];
                    const satelliteName = primary.satellite?.name || 'Unknown';
                    const endTime = primary.task_end || primary.pass?.event_end;
                    const endLabel = endTime
                        ? formatTime(endTime, {
                            timezone,
                            locale,
                            options: { hour: '2-digit', minute: '2-digit', hour12: false },
                        })
                        : 'N/A';
                    const remainingTime = endTime ? formatTimeUntil(new Date(endTime)) : 'N/A';
                    const extras = runningObservations.length > 1 ? ` +${runningObservations.length - 1}` : '';
                    parts.push(`⚫ Active: ${satelliteName}${extras} (${remainingTime} left, ends ${endLabel})`);
                }

                // Show next observation
                if (nextObservation) {
                    const satelliteName = nextObservation.satellite?.name || 'Unknown';
                    const nextStart = nextObservation.task_start || nextObservation.pass?.event_start;
                    const correctedStartTime = nextStart
                        ? formatTime(nextStart, {
                            timezone,
                            locale,
                            options: { hour: '2-digit', minute: '2-digit', hour12: false },
                          })
                        : 'N/A';
                    const timeUntil = nextStart
                        ? formatTimeUntil(new Date(nextStart))
                        : 'N/A';
                    const prefix = runningObservations.length > 0 ? '\n⏱ Next: ' : '⏱ Next: ';
                    parts.push(`${prefix}${satelliteName} (in ${timeUntil}, starts ${correctedStartTime})`);
                }

                // If we have info to show, return it; otherwise fall back to title
                if (parts.length > 0) {
                    return parts.join('');
                }
            }
            return item.title;
        }
        return '';
    };

    // Drawer content component
    const drawerContent = (isExpanded) => (
        <>
            <Toolbar />
            <Box component="nav" role="navigation" aria-label="Main navigation" sx={{ overflow: 'auto', mt: 1 }}>
                <List>
                    {navigation.map((item, index) => {
                        if (item.kind === 'header') {
                            return isExpanded ? (
                                <ListItem key={index} sx={{ pt: 2, pb: 1 }}>
                                    <Typography
                                        variant="caption"
                                        sx={{
                                            fontWeight: 'bold',
                                            color: 'text.secondary',
                                            pl: 2
                                        }}
                                    >
                                        {item.title}
                                    </Typography>
                                </ListItem>
                            ) : null;
                        }

                        if (item.kind === 'divider') {
                            return <Divider key={index} sx={{ my: 1 }} />;
                        }

                        const isActive = isActiveRoute(item.segment);

                        return (
                            <ListItem key={index} disablePadding sx={{ display: 'block' }}>
                                <Tooltip
                                    title={getTooltipText(item, isExpanded)}
                                    placement="right"
                                    disableFocusListener
                                    disableTouchListener
                                >
                                    <ListItemButton
                                        onClick={() => handleNavigation(item.segment)}
                                        selected={isActive}
                                        sx={{
                                            minHeight: 40,
                                            justifyContent: isExpanded ? 'flex-start' : 'center',
                                            px: isExpanded ? 2 : 0,
                                            py: 0.75,
                                            display: 'flex',
                                            alignItems: 'center',
                                        }}
                                    >
                                        <ListItemIcon
                                            sx={{
                                                minWidth: 0,
                                                mr: isExpanded ? 2 : 0,
                                                display: 'flex',
                                                justifyContent: 'center',
                                                alignItems: 'center',
                                            }}
                                        >
                                            {item.icon}
                                        </ListItemIcon>
                                        {isExpanded && (
                                            <ListItemText
                                                primary={item.title}
                                                sx={{
                                                    '& .MuiTypography-root': {
                                                        fontSize: '0.875rem'
                                                    }
                                                }}
                                            />
                                        )}
                                    </ListItemButton>
                                </Tooltip>
                            </ListItem>
                        );
                    })}
                </List>
            </Box>
        </>
    );

    return (
        <Box sx={{ display: 'flex', minHeight: '100vh', overflow: 'hidden' }}>
            <CssBaseline />
            <CustomAppBar position="fixed" open={open}>
                <Toolbar>
                    <IconButton
                        color="inherit"
                        aria-label="toggle drawer"
                        onClick={handleDrawerToggle}
                        edge="start"
                        sx={{ mr: 2 }}
                    >
                        {open ? <ChevronLeftIcon /> : <MenuIcon />}
                    </IconButton>
                    <Box sx={{ flexGrow: 1 }}>
                        <CustomAppTitle />
                    </Box>
                    <Box
                        sx={{
                            position: 'absolute',
                            left: '50%',
                            transform: 'translateX(-50%)',
                            pointerEvents: 'none',
                        }}
                    >
                        <ActiveObservationIndicator />
                        <UpcomingObservationIndicator />
                    </Box>
                    <MemoToolbarActions />
                </Toolbar>
            </CustomAppBar>

            {/* Mobile drawer - temporary */}
            <Drawer
                variant="temporary"
                open={mobileOpen}
                onClose={handleMobileDrawerClose}
                ModalProps={{
                    keepMounted: true, // Better open performance on mobile
                }}
                PaperProps={{
                    role: 'navigation',
                    'aria-label': 'Mobile navigation',
                }}
                sx={{
                    display: { xs: 'block', sm: 'none' },
                    '& .MuiDrawer-paper': {
                        width: drawerWidthExpanded,
                        boxSizing: 'border-box',
                    },
                }}
            >
                {drawerContent(true)}
            </Drawer>

            {/* Desktop drawer - permanent */}
            <CustomDrawer
                variant="permanent"
                open={open}
                PaperProps={{
                    role: 'navigation',
                    'aria-label': 'Desktop navigation',
                }}
                ModalProps={{
                    disableEnforceFocus: true,
                    disableAutoFocus: true,
                }}
                sx={{
                    display: { xs: 'none', sm: 'block' },
                    flexShrink: 0,
                }}
            >
                {drawerContent(open)}
            </CustomDrawer>

            <Box
                component="main"
                sx={{
                    flexGrow: 1,
                    mt: '52px',
                    minWidth: 0,
                }}
            >
                {connected && !initialDataLoading ? <Outlet /> : <ConnectionOverlay />}
                {hasVersionChanged && <VersionUpdateOverlay />}
                <PerformanceMetricsDialog />
            </Box>

            {/* Location Setup Dialog */}
            <Dialog
                open={showLocationSetupDialog}
                onClose={() => dispatch(setShowLocationSetupDialog(false))}
                aria-labelledby="location-setup-dialog-title"
                maxWidth="sm"
                fullWidth
                PaperProps={{
                    sx: {
                        borderRadius: 2,
                        boxShadow: 24,
                    }
                }}
            >
                <DialogTitle
                    id="location-setup-dialog-title"
                    sx={{
                        pb: 1,
                        fontSize: '1.5rem',
                        fontWeight: 600,
                        color: 'warning.main',
                    }}
                >
                    {t('dashboard.location_not_set_title', 'Ground Station Location Required')}
                </DialogTitle>
                <DialogContent sx={{ pt: 2 }}>
                    <DialogContentText sx={{ fontSize: '1rem', lineHeight: 1.6, color: 'text.primary' }}>
                        {t('dashboard.location_not_set_message', 'Your ground station location has not been configured yet. Location information is required for:')}
                    </DialogContentText>
                    <Box component="ul" sx={{ mt: 2, mb: 2, pl: 3, '& li': { mb: 1, color: 'text.primary' } }}>
                        <li>{t('dashboard.location_required_tracking', 'Real-time satellite tracking and visualization')}</li>
                        <li>{t('dashboard.location_required_passes', 'Calculating satellite pass predictions')}</li>
                        <li>{t('dashboard.location_required_scheduling', 'Automated observation scheduling')}</li>
                    </Box>
                    <DialogContentText sx={{ fontSize: '0.95rem', color: 'text.secondary' }}>
                        {t('dashboard.location_prompt', 'Please configure your location to enable full functionality.')}
                    </DialogContentText>
                </DialogContent>
                <DialogActions sx={{ px: 3, pb: 3, pt: 1 }}>
                    <Button
                        onClick={() => dispatch(setShowLocationSetupDialog(false))}
                        sx={{ mr: 1 }}
                    >
                        {t('dashboard.location_dialog_later', 'Remind Me Later')}
                    </Button>
                    <Button
                        onClick={() => {
                            dispatch(setShowLocationSetupDialog(false));
                            navigate('/settings/location');
                        }}
                        variant="contained"
                        size="large"
                        autoFocus
                        sx={{
                            px: 3,
                            fontWeight: 600,
                        }}
                    >
                        {t('dashboard.location_dialog_go_to_settings', 'Set Location Now')}
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
}
