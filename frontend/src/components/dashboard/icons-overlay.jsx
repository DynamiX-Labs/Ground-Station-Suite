
import React from 'react';
import { Box, SvgIcon } from '@mui/material';

const OverlayIcon = ({
                         BaseIcon,
                         OverlayIcon: Overlay,
                         overlayPosition = 'top-right',
                         overlaySize = 0.5,
                         overlayColor = '#ff0000',
                         badgeBackgroundColor = 'rgb(255,255,255)',
                         badgeBorderColor = 'rgb(52,133,75)',
                         badgeBorderWidth = 1,
                         showBadge = true,
                         baseIconProps = {},
                         overlayIconProps = {},
                         ...props
                     }) => {
    // Position mapping for overlay placement
    const positionMap = {
        'top-left': { top: '5%', left: '5%' },
        'top-right': { top: '5%', right: '5%' },
        'bottom-left': { bottom: '5%', left: '5%' },
        'bottom-right': { bottom: '5%', right: '5%' },
        'center': { top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }
    };

    const badgeSize = `${overlaySize * 1.1}em`; // Badge is larger than icon for proper padding
    const iconSize = `${overlaySize * 0.9}em`; // Icon is smaller to fit nicely in badge

    const overlayStyles = {
        position: 'absolute',
        zIndex: 1,
        ...positionMap[overlayPosition]
    };

    const badgeStyles = {
        width: badgeSize,
        height: badgeSize,
        backgroundColor: badgeBackgroundColor,
        borderRadius: '50%',
        border: badgeBorderWidth > 0 ? `${badgeBorderWidth}px solid ${badgeBorderColor}` : 'none',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: iconSize,
        color: overlayColor,
        boxShadow: '0 2px 4px rgba(0,0,0,0.2)' // Subtle shadow for depth
    };

    const plainIconStyles = {
        fontSize: `${overlaySize}em`,
        color: overlayColor,
    };

    return (
        <Box
            component="span"
            sx={{
                position: 'relative',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                ...props.sx
            }}
        >
            {/* Base Icon */}
            <BaseIcon {...baseIconProps} {...props} />

            {/* Overlay Icon */}
            {Overlay && (
                <Box
                    component="span"
                    sx={overlayStyles}
                >
                    {showBadge ? (
                        <Box sx={badgeStyles}>
                            <Overlay
                                fontSize="inherit"
                                {...overlayIconProps}
                            />
                        </Box>
                    ) : (
                        <Overlay
                            sx={plainIconStyles}
                            {...overlayIconProps}
                        />
                    )}
                </Box>
            )}
        </Box>
    );
};

export default OverlayIcon;