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
import { ToastContainer, Slide } from 'react-toastify';
import { useTheme } from '@mui/material/styles';
import { useSelector } from 'react-redux';

const SHOULD_PAUSE_ON_FOCUS_LOSS = false;

export const ToastContainerWithStyles = () => {
    const theme = useTheme();
    const preferences = useSelector((state) => state.preferences.preferences);

    // Get toast position preference
    const toastPositionPreference = preferences.find(pref => pref.name === 'toast_position');
    const position = toastPositionPreference ? toastPositionPreference.value : 'top-right';
    const pauseOnFocusLoss = SHOULD_PAUSE_ON_FOCUS_LOSS;

    return (
        <>
            <style>{`
                .Toastify__toast-container {
                    z-index: 1299 !important;
                    box-sizing: border-box;
                }

                .Toastify__toast-container--top-left,
                .Toastify__toast-container--top-right {
                    top: 75px !important;
                }

                .Toastify__toast-container--top-center {
                    top: 10px !important;
                    left: 50% !important;
                    transform: translateX(-50%) !important;
                    width: auto !important;
                    min-width: 0 !important;
                    width: max-content !important;
                    max-width: 90vw !important;
                }

                .Toastify__toast-container--top-center .Toastify__toast {
                    width: auto !important;
                    min-width: 0 !important;
                    max-width: 90vw !important;
                }

                .Toastify__toast-container--bottom-center {
                    bottom: 20px !important;
                    left: 50% !important;
                    transform: translateX(-50%) !important;
                    width: auto !important;
                    min-width: 0 !important;
                    width: max-content !important;
                    max-width: 90vw !important;
                }

                .Toastify__toast-container--bottom-center .Toastify__toast {
                    width: auto !important;
                    min-width: 0 !important;
                    max-width: 90vw !important;
                }
                
                @media (max-width: 600px) {
                    .Toastify__toast-container {
                        padding: 0 12px;
                    }
                }

                .Toastify__toast-container,
                .Toastify__toast,
                .Toastify__toast-body,
                .Toastify__toast-body > div {
                    font-family: 'Roboto', sans-serif !important;
                    font-size: 13px !important;
                }

                .Toastify__toast {
                    border-radius: 8px !important;
                    box-shadow: ${theme.palette.mode === 'dark'
                        ? '0 6px 18px rgba(0, 0, 0, 0.4)'
                        : '0 6px 18px rgba(15, 23, 42, 0.18)'} !important;
                    padding: 12px !important;
                    min-height: 64px !important;
                    backdrop-filter: blur(10px);
                }

                .Toastify__toast--success {
                    background: ${theme.palette.mode === 'dark'
                        ? 'rgba(27, 94, 32, 0.9)'
                        : 'rgba(46, 125, 50, 0.95)'} !important;
                    border-left: 4px solid ${theme.palette.success.main} !important;
                    color: #ffffff !important;
                }

                .Toastify__toast--error {
                    background: ${theme.palette.mode === 'dark'
                        ? 'rgba(183, 28, 28, 0.9)'
                        : 'rgba(198, 40, 40, 0.95)'} !important;
                    border-left: 4px solid ${theme.palette.error.main} !important;
                    color: #ffffff !important;
                }

                .Toastify__toast--warning {
                    background: ${theme.palette.mode === 'dark'
                        ? 'rgba(230, 81, 0, 0.9)'
                        : 'rgba(237, 108, 2, 0.95)'} !important;
                    border-left: 4px solid ${theme.palette.warning.main} !important;
                    color: #ffffff !important;
                }

                .Toastify__toast--info {
                    background: ${theme.palette.mode === 'dark'
                        ? 'rgba(13, 71, 161, 0.9)'
                        : 'rgba(21, 101, 192, 0.95)'} !important;
                    border-left: 4px solid ${theme.palette.info.main} !important;
                    color: #ffffff !important;
                }

                .Toastify__progress-bar--success {
                    background: ${theme.palette.success.contrastText} !important;
                }

                .Toastify__progress-bar--error {
                    background: ${theme.palette.error.contrastText} !important;
                }

                .Toastify__progress-bar--warning {
                    background: ${theme.palette.warning.contrastText} !important;
                }

                .Toastify__progress-bar--info {
                    background: ${theme.palette.info.contrastText} !important;
                }

                .Toastify__progress-bar {
                    height: 3px !important;
                    opacity: 0.6 !important;
                }

                .Toastify__close-button {
                    opacity: 0.7 !important;
                    color: rgba(255, 255, 255, 0.92) !important;
                }

                .Toastify__close-button:hover {
                    opacity: 1 !important;
                }

                .Toastify__toast-body {
                    white-space: pre-line !important;
                }

                .observation-countdown-toast__countdown {
                    font-size: 18px;
                    text-align: right;
                }

                .observation-countdown-toast__line {
                    font-size: 14px;
                    white-space: normal;
                    overflow: visible;
                    text-overflow: clip;
                }

            `}</style>
            <ToastContainer
                position={position}
                autoClose={4000}
                hideProgressBar={false}
                newestOnTop={false}
                closeOnClick={false}
                rtl={false}
                pauseOnFocusLoss={pauseOnFocusLoss}
                draggable={true}
                draggablePercent={30}
                pauseOnHover={true}
                theme={theme.palette.mode}
                transition={Slide}
                toastClassName="custom-toast"
            />
        </>
    );
};
