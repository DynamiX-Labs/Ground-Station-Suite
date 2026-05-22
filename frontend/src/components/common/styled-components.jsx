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

import { styled } from '@mui/material/styles';
import { Box, Paper, Card, IconButton } from '@mui/material';

/**
 * Reusable Card Container with consistent styling
 * Variants: default, elevated
 */
export const StyledCard = styled(Card)(({ theme, variant = 'default' }) => ({
    backgroundColor: variant === 'elevated' ? theme.palette.background.elevated : theme.palette.background.paper,
    border: `1px solid ${theme.palette.border.main}`,
    borderRadius: theme.shape.borderRadius,
}));

/**
 * Status Indicator Box
 * Status: connected, disconnected, connecting, polling
 */
export const StatusIndicator = styled(Box)(({ theme, status = 'disconnected' }) => {
    const statusColors = {
        connected: theme.palette.status.connected,
        disconnected: theme.palette.status.disconnected,
        connecting: theme.palette.status.connecting,
        polling: theme.palette.status.polling,
    };

    return {
        width: 8,
        height: 8,
        borderRadius: '50%',
        backgroundColor: statusColors[status] || theme.palette.text.disabled,
        boxShadow: `0 0 6px ${statusColors[status] || theme.palette.text.disabled}99`,
    };
});

/**
 * Popover Container with consistent styling
 */
export const PopoverContainer = styled(Box)(({ theme }) => ({
    borderRadius: 0,
    border: '1px solid',
    borderColor: theme.palette.border.main,
    padding: theme.spacing(1),
    minWidth: 250,
    backgroundColor: theme.palette.background.paper,
}));

/**
 * Themed IconButton with hover effect
 */
export const ThemedIconButton = styled(IconButton)(({ theme }) => ({
    '&:hover': {
        backgroundColor: theme.palette.overlay.light,
    },
}));

/**
 * Section Header Paper with consistent styling
 */
export const SectionHeader = styled(Paper)(({ theme }) => ({
    padding: theme.spacing(1, 2),
    backgroundColor: theme.palette.background.elevated,
    borderBottom: `1px solid ${theme.palette.border.main}`,
    fontWeight: 'bold',
}));

/**
 * Data Row Container
 */
export const DataRow = styled(Box)(({ theme }) => ({
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: theme.spacing(1),
    borderBottom: `1px solid ${theme.palette.border.main}`,
    '&:last-child': {
        borderBottom: 'none',
    },
    '&:hover': {
        backgroundColor: theme.palette.overlay.light,
    },
}));

/**
 * Overlay Box with semi-transparent background
 * Variant: light, medium, dark
 */
export const OverlayBox = styled(Box)(({ theme, variant = 'medium' }) => {
    const overlayColors = {
        light: theme.palette.overlay.light,
        medium: theme.palette.overlay.medium,
        dark: theme.palette.overlay.dark,
    };

    return {
        backgroundColor: overlayColors[variant],
        backdropFilter: 'blur(4px)',
    };
});

/**
 * Themed Container for settings/configuration panels
 */
export const SettingsContainer = styled(Box)(({ theme }) => ({
    backgroundColor: theme.palette.background.paper,
    border: `1px solid ${theme.palette.border.main}`,
    borderRadius: theme.shape.borderRadius,
    padding: theme.spacing(2),
}));

/**
 * Monospace Text Display (for frequencies, coordinates, etc.)
 */
export const MonospaceText = styled(Box)(({ theme, color = 'text.primary' }) => ({
    fontFamily: 'monospace',
    color: theme.palette[color] || color,
    letterSpacing: '0.05em',
}));

/**
 * Status Badge for alive/dead indicators
 * Status: success, error, warning, info
 */
export const StatusBadge = styled(Box)(({ theme, status = 'success' }) => {
    const statusMap = {
        success: theme.palette.success.main,
        error: theme.palette.error.main,
        warning: theme.palette.warning.main,
        info: theme.palette.info.main,
    };

    return {
        width: 8,
        height: 8,
        borderRadius: '50%',
        backgroundColor: statusMap[status],
        display: 'inline-block',
        marginRight: theme.spacing(1),
        boxShadow: `0 0 4px ${statusMap[status]}99`,
    };
});

/**
 * Gradient Background Container
 * For special visual effects that need gradient backgrounds
 */
export const GradientContainer = styled(Box)(({ theme, variant = 'primary' }) => {
    const gradients = {
        primary: `linear-gradient(135deg, ${theme.palette.primary.dark}, ${theme.palette.primary.main})`,
        success: `linear-gradient(135deg, ${theme.palette.success.dark}, ${theme.palette.success.main})`,
        error: `linear-gradient(135deg, ${theme.palette.error.dark}, ${theme.palette.error.main})`,
        info: `linear-gradient(135deg, ${theme.palette.info.dark}, ${theme.palette.info.main})`,
        background: `linear-gradient(135deg, ${theme.palette.background.default}, ${theme.palette.background.elevated})`,
    };

    return {
        background: gradients[variant],
        color: theme.palette.getContrastText(theme.palette[variant]?.main || theme.palette.background.paper),
    };
});
