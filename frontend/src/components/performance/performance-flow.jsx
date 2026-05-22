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

import React, { useEffect, useMemo, useRef, useCallback } from 'react';
import ReactFlow, {
    Background,
    Controls,
    useNodesState,
    useEdgesState,
    useReactFlow,
    Panel,
    ReactFlowProvider,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Box, Button, Typography } from '@mui/material';
import { ComponentNode } from './flow-node.jsx';
import { createFlowFromMetrics, applyDagreLayout } from './flow-layout.js';

const nodeTypes = {
    componentNode: ComponentNode,
};

const FlowContent = ({ metrics, onAutoArrangeCallback }) => {
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);
    const fitViewCalledRef = useRef(false);
    const { fitView } = useReactFlow();

    // Convert metrics to nodes and edges
    const { nodes: flowNodes, edges: flowEdges } = useMemo(() => {
        if (!metrics) return { nodes: [], edges: [] };
        return createFlowFromMetrics(metrics);
    }, [metrics]);

    // Update nodes and edges when metrics change - always use fresh layout from createFlowFromMetrics
    useEffect(() => {
        setNodes(flowNodes);
        setEdges(flowEdges);
    }, [flowNodes, flowEdges, setNodes, setEdges]);

    // Fit view after nodes are rendered (only on first load)
    useEffect(() => {
        if (nodes.length > 0 && !fitViewCalledRef.current) {
            fitViewCalledRef.current = true;
            // Wait for nodes to be fully rendered with their dimensions
            const timeoutId = setTimeout(() => {
                fitView({ padding: 0.2, duration: 0 });
            }, 200);
            return () => clearTimeout(timeoutId);
        }
    }, [nodes.length, fitView]);

    // Auto-arrange handler
    const onAutoArrange = useCallback(() => {
        const layoutedNodes = applyDagreLayout(nodes, edges);
        setNodes(layoutedNodes);

        // Fit view after layout instantly
        window.requestAnimationFrame(() => {
            fitView({ padding: 0.2, duration: 0 });
        });
    }, [nodes, edges, setNodes, fitView]);

    // Expose the auto-arrange handler to parent
    useEffect(() => {
        if (onAutoArrangeCallback) {
            onAutoArrangeCallback(onAutoArrange);
        }
    }, [onAutoArrange, onAutoArrangeCallback]);

    return (
        <Box
            sx={{
                width: '100%',
                height: '100%',
                backgroundColor: (theme) => theme.palette.background?.default || theme.palette.background.default,
                '& .react-flow__controls': {
                    backgroundColor: (theme) => theme.palette.background?.paper || theme.palette.background.paper,
                    border: (theme) => `1px solid ${theme.palette.divider}`,
                    borderRadius: 1,
                    top: '20px !important',
                    right: '20px !important',
                    bottom: 'auto !important',
                    left: 'auto !important',
                    zIndex: 10,
                    pointerEvents: 'auto',
                },
                '& .react-flow__controls-button': {
                    backgroundColor: (theme) => theme.palette.background?.paper || theme.palette.background.paper,
                    borderBottom: (theme) => `1px solid ${theme.palette.divider}`,
                    color: (theme) => theme.palette.text.primary,
                    '&:hover': {
                        backgroundColor: (theme) => theme.palette.action?.hover || 'rgba(255, 255, 255, 0.08)',
                    },
                    '&:last-child': {
                        borderBottom: 'none',
                    },
                },
                '& .react-flow__controls-button svg': {
                    fill: (theme) => theme.palette.text.primary,
                },
                '& .react-flow__attribution': {
                    backgroundColor: (theme) => theme.palette.background?.paper || theme.palette.background.paper,
                    color: (theme) => theme.palette.text.secondary,
                    border: (theme) => `1px solid ${theme.palette.divider}`,
                    borderRadius: 1,
                    padding: '4px 8px',
                    fontSize: '10px',
                },
                '& .react-flow__attribution a': {
                    color: (theme) => theme.palette.primary.main,
                    textDecoration: 'none',
                    '&:hover': {
                        textDecoration: 'underline',
                    },
                },
            }}
        >
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                nodeTypes={nodeTypes}
                fitView
                attributionPosition="bottom-left"
                nodesDraggable={false}
                nodesConnectable={false}
                elementsSelectable={false}
            >
                <Background
                    color="#888"
                    gap={16}
                    variant="dots"
                />
                <Controls />
                <Panel position="top-left" style={{ zIndex: 1 }}>
                    <Box
                        sx={{
                            backgroundColor: 'rgba(128, 128, 128, 0.15)',
                            padding: 1,
                            borderRadius: 0.75,
                            minWidth: 150,
                            pointerEvents: 'none',
                            opacity: 0.5,
                        }}
                    >
                        <Typography variant="caption" sx={{ fontWeight: 'bold', color: '#fff', display: 'block', mb: 0.5, fontSize: '0.65rem' }}>
                            Data Types
                        </Typography>
                        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.3, mb: 1 }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                                <Box sx={{ width: 18, height: 1.5, backgroundColor: '#2196f3' }} />
                                <Typography variant="caption" sx={{ color: '#fff', fontSize: '0.6rem' }}>
                                    IQ Samples
                                </Typography>
                            </Box>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                                <Box sx={{ width: 18, height: 1.5, backgroundColor: '#4caf50' }} />
                                <Typography variant="caption" sx={{ color: '#fff', fontSize: '0.6rem' }}>
                                    Audio
                                </Typography>
                            </Box>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                                <Box sx={{ width: 18, height: 1.5, backgroundColor: '#9c27b0' }} />
                                <Typography variant="caption" sx={{ color: '#fff', fontSize: '0.6rem' }}>
                                    FFT/Waterfall
                                </Typography>
                            </Box>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                                <Box sx={{ width: 18, height: 1.5, backgroundColor: '#ff9800' }} />
                                <Typography variant="caption" sx={{ color: '#fff', fontSize: '0.6rem' }}>
                                    Decoded Data
                                </Typography>
                            </Box>
                        </Box>
                        <Typography variant="caption" sx={{ fontWeight: 'bold', color: '#fff', display: 'block', mb: 0.5, fontSize: '0.65rem' }}>
                            Line Styles
                        </Typography>
                        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.3, mb: 1 }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                                <Box sx={{ width: 18, height: 0, borderTop: '1.5px dotted #fff' }} />
                                <Typography variant="caption" sx={{ color: '#fff', fontSize: '0.6rem' }}>
                                    Data Flowing
                                </Typography>
                            </Box>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                                <Box sx={{ width: 18, height: 1.5, backgroundColor: 'rgba(255, 255, 255, 0.3)' }} />
                                <Typography variant="caption" sx={{ color: '#fff', fontSize: '0.6rem' }}>
                                    No Flow / Idle
                                </Typography>
                            </Box>
                        </Box>
                        <Typography variant="caption" sx={{ fontWeight: 'bold', color: '#fff', display: 'block', mb: 0.5, fontSize: '0.65rem' }}>
                            Queue Health
                        </Typography>
                        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.3 }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                                <Box sx={{ width: 18, height: 1.5, backgroundColor: '#4caf50' }} />
                                <Typography variant="caption" sx={{ color: '#fff', fontSize: '0.6rem' }}>
                                    Healthy (&lt;50%)
                                </Typography>
                            </Box>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                                <Box sx={{ width: 18, height: 1.5, backgroundColor: '#ff9800' }} />
                                <Typography variant="caption" sx={{ color: '#fff', fontSize: '0.6rem' }}>
                                    Warning (50-80%)
                                </Typography>
                            </Box>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                                <Box sx={{ width: 18, height: 1.5, backgroundColor: '#f44336' }} />
                                <Typography variant="caption" sx={{ color: '#fff', fontSize: '0.6rem' }}>
                                    Critical (&gt;80%)
                                </Typography>
                            </Box>
                        </Box>
                    </Box>
                </Panel>
            </ReactFlow>
        </Box>
    );
};

const PerformanceFlow = ({ metrics, onAutoArrangeCallback }) => {
    return (
        <ReactFlowProvider>
            <FlowContent metrics={metrics} onAutoArrangeCallback={onAutoArrangeCallback} />
        </ReactFlowProvider>
    );
};

export default PerformanceFlow;
