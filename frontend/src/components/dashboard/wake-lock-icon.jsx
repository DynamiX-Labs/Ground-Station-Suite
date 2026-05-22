import React from 'react';
import { Tooltip, IconButton } from '@mui/material';
import { useWakeLockContext } from './wake-lock-provider.jsx';
import LockIcon from '@mui/icons-material/Lock';
import LockOpenIcon from '@mui/icons-material/LockOpen';
import WarningIcon from '@mui/icons-material/Warning';
import ScreenLockPortraitIcon from '@mui/icons-material/ScreenLockPortrait';
import StayPrimaryPortraitIcon from '@mui/icons-material/StayPrimaryPortrait';

const WakeLockStatus = ({ size = 'medium' }) => {
    const {
        isSupported,
        isActive,
        activeRequests,
        hasManualRequest,
        forceRelease,
        requestManualWakeLock,
    } = useWakeLockContext();

    const handleClick = async () => {
        if (isActive) {
            // Release all wake locks
            forceRelease();
        } else {
            // Manually acquire wake lock
            await requestManualWakeLock();
        }
    };

    const getTooltipText = () => {
        if (!isSupported) {
            return 'Wake lock not supported on this device';
        }

        if (hasManualRequest && activeRequests > 0) {
            return `Manual + ${activeRequests} component wake lock${activeRequests !== 1 ? 's' : ''} active. Click to release all.`;
        } else if (hasManualRequest) {
            return 'Manual wake lock active. Click to release.';
        } else if (activeRequests > 0) {
            return `${activeRequests} component wake lock${activeRequests !== 1 ? 's' : ''} active. Click to release all.`;
        } else {
            return 'Screen can sleep. Click to manually activate wake lock.';
        }
    };

    const getIcon = () => {
        if (!isSupported) {
            return <WarningIcon color="warning" />;
        }
        return isActive ? <ScreenLockPortraitIcon color="primary" /> : <StayPrimaryPortraitIcon color="action" />;
    };

    return (
        <Tooltip title={getTooltipText()}>
            <IconButton
                onClick={isSupported ? handleClick : undefined}
                size={size}
                disabled={!isSupported}
            >
                {getIcon()}
            </IconButton>
        </Tooltip>
    );
};

export default WakeLockStatus;