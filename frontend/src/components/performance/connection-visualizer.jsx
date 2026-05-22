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

import React, { useEffect, useRef, useState } from 'react';
import { Box } from '@mui/material';

/**
 * ConnectionVisualizer draws SVG lines showing data flow between components
 * based on their connection metadata.
 */
const ConnectionVisualizer = ({ sdrData, containerRef }) => {
    const svgRef = useRef(null);
    const [connections, setConnections] = useState([]);

    useEffect(() => {
        if (!containerRef?.current) return;

        // Get the container element once
        const container = containerRef.current;

        const calculateConnections = () => {
            const newConnections = [];
            const elementPositions = new Map();

            // Get positions of all elements by their IDs
            const elements = container.querySelectorAll('[data-component-id]');

            elements.forEach((el) => {
                const componentId = el.getAttribute('data-component-id');
                const rect = el.getBoundingClientRect();
                const containerRect = container.getBoundingClientRect();

                elementPositions.set(componentId, {
                    x: rect.left - containerRect.left + rect.width / 2,
                    y: rect.top - containerRect.top,
                    width: rect.width,
                    height: rect.height,
                });
            });

            console.log('Element positions:', Array.from(elementPositions.keys()));
            console.log('SDR data:', sdrData);

            // Process broadcasters
            if (sdrData.broadcasters) {
                Object.values(sdrData.broadcasters).forEach((broadcaster) => {
                    const sourceId = broadcaster.broadcaster_id;
                    const sourcePos = elementPositions.get(sourceId);

                    if (sourcePos && broadcaster.connections) {
                        broadcaster.connections.forEach((conn) => {
                            const targetPos = elementPositions.get(conn.target_id);
                            if (targetPos) {
                                newConnections.push({
                                    from: sourcePos,
                                    to: targetPos,
                                    type: 'broadcaster_to_consumer',
                                    color: broadcaster.broadcaster_type === 'iq' ? '#4caf50' : '#2196f3',
                                });
                            }
                        });
                    }
                });
            }

            // Process FFT processor
            if (sdrData.fft_processor?.connections) {
                const sourceId = sdrData.fft_processor.fft_id;
                const sourcePos = elementPositions.get(sourceId);

                if (sourcePos) {
                    sdrData.fft_processor.connections.forEach((conn) => {
                        const targetPos = elementPositions.get(conn.source_id);
                        if (targetPos) {
                            newConnections.push({
                                from: targetPos,
                                to: sourcePos,
                                type: 'iq_to_fft',
                                color: '#4caf50',
                            });
                        }
                    });
                }
            }

            // Process demodulators
            if (sdrData.demodulators) {
                Object.values(sdrData.demodulators).forEach((demod) => {
                    const targetId = demod.demod_id;
                    const targetPos = elementPositions.get(targetId);

                    console.log('Demod:', demod.type, 'ID:', targetId, 'Found position:', !!targetPos, 'Connections:', demod.connections);

                    if (targetPos && demod.connections) {
                        demod.connections.forEach((conn) => {
                            if (conn.source_type) {
                                const sourcePos = elementPositions.get(conn.source_id);
                                console.log('  Source conn:', conn.source_id, 'Found:', !!sourcePos);
                                if (sourcePos) {
                                    newConnections.push({
                                        from: sourcePos,
                                        to: targetPos,
                                        type: 'iq_to_demod',
                                        color: '#4caf50',
                                    });
                                }
                            }
                            if (conn.target_type) {
                                const destPos = elementPositions.get(conn.target_id);
                                console.log('  Target conn:', conn.target_id, 'Found:', !!destPos);
                                if (destPos) {
                                    newConnections.push({
                                        from: targetPos,
                                        to: destPos,
                                        type: 'demod_to_audio_broadcaster',
                                        color: '#ff9800',
                                    });
                                }
                            }
                        });
                    }
                });
            }

            // Process decoders
            if (sdrData.decoders) {
                Object.values(sdrData.decoders).forEach((decoder) => {
                    const targetId = decoder.decoder_id;
                    const targetPos = elementPositions.get(targetId);

                    console.log('Decoder:', decoder.type, 'ID:', targetId, 'Found position:', !!targetPos, 'Connections:', decoder.connections);

                    if (targetPos && decoder.connections) {
                        decoder.connections.forEach((conn) => {
                            const sourcePos = elementPositions.get(conn.source_id);
                            console.log('  Decoder source conn:', conn.source_id, 'Type:', conn.source_type, 'Found:', !!sourcePos);
                            if (sourcePos) {
                                // Use green for IQ-based decoders (BPSK, GMSK, LoRa), blue for audio-based
                                const color = conn.source_type === 'iq_broadcaster' ? '#4caf50' : '#2196f3';
                                const type = conn.source_type === 'iq_broadcaster' ? 'iq_to_decoder' : 'audio_to_decoder';

                                newConnections.push({
                                    from: sourcePos,
                                    to: targetPos,
                                    type: type,
                                    color: color,
                                });
                            }
                        });
                    }
                });
            }

            console.log('Total connections to draw:', newConnections.length, newConnections);
            setConnections(newConnections);
        };

        // Calculate initially and on resize
        calculateConnections();
        const resizeObserver = new ResizeObserver(calculateConnections);
        resizeObserver.observe(container);

        return () => resizeObserver.disconnect();
    }, [sdrData, containerRef]);

    // Draw SVG paths for connections
    const drawPath = (from, to, color) => {
        const startX = from.x;
        const startY = from.y + from.height;
        const endX = to.x;
        const endY = to.y;

        // Create a curved path
        const midY = (startY + endY) / 2;

        return {
            path: `M ${startX} ${startY} C ${startX} ${midY}, ${endX} ${midY}, ${endX} ${endY}`,
            color,
        };
    };

    return (
        <Box
            sx={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                pointerEvents: 'none',
                zIndex: 10,
            }}
        >
            <svg
                ref={svgRef}
                style={{
                    width: '100%',
                    height: '100%',
                    position: 'absolute',
                    top: 0,
                    left: 0,
                }}
            >
                <defs>
                    <marker
                        id="arrowhead"
                        markerWidth="10"
                        markerHeight="10"
                        refX="9"
                        refY="3"
                        orient="auto"
                    >
                        <polygon points="0 0, 10 3, 0 6" fill="currentColor" />
                    </marker>
                </defs>
                {connections.map((conn, index) => {
                    const { path, color } = drawPath(conn.from, conn.to, conn.color);
                    return (
                        <path
                            key={index}
                            d={path}
                            stroke={color}
                            strokeWidth="2"
                            fill="none"
                            opacity="0.6"
                            markerEnd="url(#arrowhead)"
                            style={{ color }}
                        />
                    );
                })}
            </svg>
        </Box>
    );
};

export default ConnectionVisualizer;
