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

import React from "react";
import { Box, Tooltip } from "@mui/material";
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import KeyboardDoubleArrowUpIcon from '@mui/icons-material/KeyboardDoubleArrowUp';
import KeyboardDoubleArrowDownIcon from '@mui/icons-material/KeyboardDoubleArrowDown';
import HorizontalRuleIcon from '@mui/icons-material/HorizontalRule';

/**
 * Reusable component to display satellite elevation with trend indicator
 * @param {number} elevation - Current elevation in degrees
 * @param {string} trend - Trend: 'rising_slow', 'rising_fast', 'falling_slow', 'falling_fast', 'peak', 'stable'
 * @param {number} timeToMaxEl - Time to maximum elevation in seconds (optional)
 * @param {number} elRate - Rate of elevation change in degrees per update (optional)
 * @param {boolean} showNegative - Whether to show negative elevations (default: false, for tables. Set true for info card)
 */
const ElevationDisplay = React.memo(function ElevationDisplay({
    elevation,
    trend,
    timeToMaxEl,
    elRate,
    showNegative = false
}) {
    // Handle null/undefined elevation
    if (elevation === null || elevation === undefined) {
        return <span>-</span>;
    }

    // Below horizon - hide unless showNegative is true
    if (elevation < 0 && !showNegative) {
        return <span>-</span>;
    }

    // Determine color based on elevation value
    let color;
    if (elevation < 0) {
        // Below horizon - show in gray
        color = 'text.secondary';
    } else if (elevation < 10) {
        color = 'error.main';
    } else if (elevation >= 10 && elevation < 45) {
        color = 'warning.main';
    } else {
        color = 'success.main';
    }

    // Determine trend icon and color
    let TrendIcon = null;
    let trendColor = 'text.secondary';

    if (trend === 'rising_fast') {
        TrendIcon = KeyboardDoubleArrowUpIcon;
        trendColor = 'info.main';
    } else if (trend === 'rising_slow') {
        TrendIcon = ArrowUpwardIcon;
        trendColor = 'info.main';
    } else if (trend === 'falling_fast') {
        TrendIcon = KeyboardDoubleArrowDownIcon;
        trendColor = 'error.main';
    } else if (trend === 'falling_slow') {
        TrendIcon = ArrowDownwardIcon;
        trendColor = 'error.main';
    } else if (trend === 'peak') {
        TrendIcon = HorizontalRuleIcon;
        trendColor = 'warning.main';
    }

    // Format time to max elevation
    const formatTimeToMax = (seconds) => {
        if (!seconds) return '';
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        if (mins > 0) {
            return `${mins}m ${secs}s`;
        }
        return `${secs}s`;
    };

    // Build tooltip content
    const tooltipContent = [];
    if (trend && trend !== 'stable') {
        const trendLabel = {
            rising_fast: 'rising (fast)',
            rising_slow: 'rising (slow)',
            falling_fast: 'falling (fast)',
            falling_slow: 'falling (slow)',
            peak: 'peak',
        }[trend] || trend;
        tooltipContent.push(`Trend: ${trendLabel}`);
    }
    if (elRate !== null && elRate !== undefined) {
        tooltipContent.push(`Rate: ${elRate.toFixed(2)}°/update`);
    }
    if (timeToMaxEl) {
        tooltipContent.push(`Time to peak: ${formatTimeToMax(timeToMaxEl)}`);
    }

    const hasTooltip = tooltipContent.length > 0;

    const content = (
        <Box
            component="span"
            sx={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                color,
                fontWeight: 'bold'
            }}
        >
            {elevation.toFixed(1)}°
            {TrendIcon && (
                <TrendIcon
                    sx={{
                        fontSize: '0.9rem',
                        color: trendColor,
                        verticalAlign: 'middle'
                    }}
                />
            )}
        </Box>
    );

    if (hasTooltip) {
        return (
            <Tooltip
                title={tooltipContent.join(' • ')}
                arrow
                enterDelay={500}
            >
                {content}
            </Tooltip>
        );
    }

    return content;
});

export default ElevationDisplay;
