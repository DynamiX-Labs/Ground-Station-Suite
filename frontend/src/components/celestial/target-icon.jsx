import React from 'react';
import BodyIcon from './body-icon.jsx';
import MissionIcon from './mission-icon.jsx';
import SatelliteIcon from './satellite-icon.jsx';

const TargetIcon = ({
    targetType = 'body',
    bodyId = '',
    size = 24,
    alt = 'target icon',
    sx = {},
}) => {
    const normalizedTargetType = String(targetType || '').toLowerCase();

    if (normalizedTargetType === 'body') {
        return (
            <BodyIcon
                bodyId={bodyId}
                size={size}
                alt={alt}
                sx={sx}
            />
        );
    }

    if (normalizedTargetType === 'mission') {
        return (
            <MissionIcon
                missionKey={bodyId}
                size={size}
                alt={alt}
                sx={sx}
            />
        );
    }

    if (normalizedTargetType === 'satellite') {
        return (
            <SatelliteIcon
                satelliteId={bodyId}
                size={size}
                alt={alt}
                sx={sx}
            />
        );
    }

    return null;
};

export default React.memo(TargetIcon);
