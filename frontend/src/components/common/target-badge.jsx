import * as React from 'react';
import { Box, Typography } from '@mui/material';

const baseSx = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 0.45,
    px: 0.7,
    py: 0.2,
    borderRadius: 999,
    border: '1px solid',
    borderColor: 'divider',
    backgroundColor: 'background.paper',
    minHeight: 22,
    userSelect: 'none',
};

function TargetBadge({
    targetNumber,
    tracking = false,
    clickable = false,
    onClick,
    sx = {},
}) {
    const numericTarget = Number(targetNumber);
    const suffix = Number.isFinite(numericTarget) ? numericTarget : '?';
    const label = `T${suffix}`;

    return (
        <Box
            component={clickable ? 'button' : 'span'}
            type={clickable ? 'button' : undefined}
            onClick={clickable ? onClick : undefined}
            sx={{
                ...baseSx,
                color: 'text.secondary',
                borderColor: 'divider',
                backgroundColor: 'background.paper',
                cursor: clickable ? 'pointer' : 'default',
                font: 'inherit',
                margin: 0,
                appearance: 'none',
                ...(clickable
                    ? {
                        '&:hover': { borderColor: 'primary.main', color: 'primary.main' },
                        '&:focus-visible': {
                            outline: '2px solid',
                            outlineColor: 'primary.main',
                            outlineOffset: 1,
                        },
                    }
                    : {}),
                ...sx,
            }}
        >
            <Box
                sx={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    bgcolor: tracking ? 'success.light' : 'text.disabled',
                    flexShrink: 0,
                }}
            />
            <Typography
                component="span"
                sx={{
                    fontWeight: 800,
                    fontSize: '0.73rem',
                    lineHeight: 1,
                    letterSpacing: '0.02em',
                }}
            >
                {label}
            </Typography>
        </Box>
    );
}

export default React.memo(TargetBadge);
