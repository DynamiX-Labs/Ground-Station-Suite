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
import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Button,
    FormGroup,
    FormControlLabel,
    Checkbox,
    Typography,
    Box,
    Divider,
} from '@mui/material';
import { useDispatch, useSelector } from 'react-redux';
import { setColumnVisibility } from './scheduler-slice.jsx';

const ObservationsTableSettingsDialog = ({ open, onClose }) => {
    const dispatch = useDispatch();
    const columnVisibility = useSelector(state => state.scheduler.columnVisibility);

    const handleColumnToggle = (columnName) => {
        dispatch(setColumnVisibility({
            [columnName]: !columnVisibility[columnName]
        }));
    };

    const columns = [
        { name: 'enabled', label: 'Enabled', category: 'basic', alwaysVisible: true },
        { name: 'satellite', label: 'Satellite', category: 'basic', alwaysVisible: true },
        { name: 'peak_elevation', label: 'Peak Elevation', category: 'pass_info' },
        { name: 'pass_start', label: 'AOS', category: 'timing' },
        { name: 'task_start', label: 'Task Start', category: 'timing' },
        { name: 'task_end', label: 'Task End', category: 'timing' },
        { name: 'pass_end', label: 'LOS', category: 'timing' },
        { name: 'sdr', label: 'SDR', category: 'equipment' },
        { name: 'tasks', label: 'Tasks', category: 'configuration' },
        { name: 'status', label: 'Status', category: 'basic' },
        { name: 'actions', label: 'Actions', category: 'basic', alwaysVisible: true },
    ];

    const categories = {
        basic: 'Basic Information',
        pass_info: 'Pass Information',
        timing: 'Timing',
        equipment: 'Equipment',
        configuration: 'Configuration',
    };

    const columnsByCategory = {
        basic: columns.filter(col => col.category === 'basic'),
        pass_info: columns.filter(col => col.category === 'pass_info'),
        timing: columns.filter(col => col.category === 'timing'),
        equipment: columns.filter(col => col.category === 'equipment'),
        configuration: columns.filter(col => col.category === 'configuration'),
    };

    return (
        <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
            <DialogTitle>Observations Table Settings</DialogTitle>
            <DialogContent
                sx={{
                    bgcolor: (theme) => (
                        theme.palette.mode === 'dark'
                            ? theme.palette.background.elevated
                            : theme.palette.background.paper
                    ),
                }}
            >
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    Customize which columns are visible in the observations table.
                </Typography>

                {Object.entries(columnsByCategory).map(([category, cols]) => (
                    <Box key={category} sx={{ mb: 2 }}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                            {categories[category]}
                        </Typography>
                        <FormGroup>
                            {cols.map(column => (
                                <FormControlLabel
                                    key={column.name}
                                    control={
                                        <Checkbox
                                            checked={column.alwaysVisible || columnVisibility[column.name] !== false}
                                            onChange={() => handleColumnToggle(column.name)}
                                            disabled={column.alwaysVisible}
                                        />
                                    }
                                    label={
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                            {column.label}
                                            {column.alwaysVisible && (
                                                <Typography variant="caption" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                                                    (Always visible)
                                                </Typography>
                                            )}
                                        </Box>
                                    }
                                />
                            ))}
                        </FormGroup>
                        <Divider sx={{ mt: 1 }} />
                    </Box>
                ))}
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose} variant="contained">
                    Close
                </Button>
            </DialogActions>
        </Dialog>
    );
};

export default ObservationsTableSettingsDialog;
