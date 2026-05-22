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

import React from 'react';
import { toast as originalToast } from 'react-toastify';

const formatTimestamp = () => {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');

    // Get timezone offset in hours and minutes
    const offset = -now.getTimezoneOffset();
    const offsetHours = String(Math.floor(Math.abs(offset) / 60)).padStart(2, '0');
    const offsetMinutes = String(Math.abs(offset) % 60).padStart(2, '0');
    const offsetSign = offset >= 0 ? '+' : '-';
    const timezone = `UTC${offsetSign}${offsetHours}:${offsetMinutes}`;

    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds} ${timezone}`;
};

const wrapWithTimestamp = (message, disableTimestamp) => {
    if (disableTimestamp) {
        return message;
    }
    const timestamp = formatTimestamp();
    return (
        <div style={{ width: '100%' }}>
            <div style={{
                fontSize: '9px',
                opacity: 0.6,
                marginBottom: '4px',
                fontFamily: 'monospace'
            }}>
                {timestamp}
            </div>
            <div>{message}</div>
        </div>
    );
};

const createToastWithClickHandler = (toastFn) => (message, options = {}) => {
    const { disablePauseOnClick, disableTimestamp, onClick, ...restOptions } = options;
    const toastId = toastFn(wrapWithTimestamp(message, disableTimestamp), {
        closeOnClick: false,
        onClick: disablePauseOnClick
            ? onClick
            : () => {
                // Pause the toast by setting autoClose to false
                originalToast.update(toastId, { autoClose: false });
                if (onClick) onClick();
            },
        ...restOptions,
    });

    return toastId;
};

export const toast = {
    success: createToastWithClickHandler(originalToast.success),
    error: createToastWithClickHandler(originalToast.error),
    info: createToastWithClickHandler(originalToast.info),
    warning: createToastWithClickHandler(originalToast.warning),
    warn: createToastWithClickHandler(originalToast.warn),
    update: (toastId, message, options = {}) => {
        const { disablePauseOnClick, disableTimestamp, onClick, ...restOptions } = options;
        originalToast.update(toastId, {
            render: wrapWithTimestamp(message, disableTimestamp),
            closeOnClick: false,
            onClick: disablePauseOnClick ? onClick : undefined,
            ...restOptions,
        });
    },
};
