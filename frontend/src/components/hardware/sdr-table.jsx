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


import * as React from 'react';
import Box from '@mui/material/Box';
import {DataGrid, gridClasses} from "@mui/x-data-grid";
import Stack from "@mui/material/Stack";
import {
    Alert,
    AlertTitle,
    Button,
    FormControl,
    InputAdornment,
    InputLabel,
    MenuItem,
    Select,
    ToggleButton,
    ToggleButtonGroup,
    TextField,
    Typography
} from "@mui/material";
import { alpha } from '@mui/material/styles';
import {useEffect, useMemo, useRef, useState} from "react";
import { useTranslation } from 'react-i18next';
import DialogTitle from "@mui/material/DialogTitle";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import {useSocket} from "../common/socket.jsx";
import { toast } from '../../utils/toast-with-timestamp.jsx';
import { useDispatch, useSelector } from 'react-redux';
import {
    deleteSDRs,
    fetchSDRs,
    submitOrEditSDR,
    setOpenDeleteConfirm,
    setOpenAddDialog,
    setFormValues,
    resetFormValues,
    fetchSoapySDRServers,
    setSelectedSdrDevice,
    fetchLocalSoapySDRDevices,
    startSoapySDRDiscovery,
    fetchLocalRtlSdrDevices,
} from './sdr-slice.jsx';
import Paper from "@mui/material/Paper";
import MemoryIcon from '@mui/icons-material/Memory';
import DnsIcon from '@mui/icons-material/Dns';
import {toRowSelectionModel, toSelectedIds} from '../../utils/datagrid-selection.js';
import SelectionActionBar from './selection-action-bar.jsx';

// SDR type field configurations with default values
const sdrTypeFields = {
    rtlsdrusbv3: {
        excludeFields: ['host', 'port', 'driver'],
        fields: ['name', 'frequency_min', 'frequency_max', 'serial'],
        defaults: {
            name: 'USB SDR v3',
            frequency_min: 24,
            frequency_max: 1700,
            serial: ''
        }
    },
    rtlsdrtcpv3: {
        excludeFields: ['serial', 'driver'],
        fields: ['host', 'port', 'name', 'frequency_min', 'frequency_max'],
        defaults: {
            host: '127.0.0.1',
            port: 1234,
            name: 'TCP SDR v3',
            frequency_min: 24,
            frequency_max: 1700,
            serial: ''
        }
    },
    rtlsdrusbv4: {
        excludeFields: ['host', 'port', 'driver'],
        fields: ['name', 'frequency_min', 'frequency_max', 'serial'],
        defaults: {
            name: 'USB SDR v4',
            frequency_min: 24,
            frequency_max: 1800,
            serial: ''
        }
    },
    rtlsdrtcpv4: {
        excludeFields: ['serial', 'driver'],
        fields: ['host', 'port', 'name', 'frequency_min', 'frequency_max'],
        defaults: {
            host: '127.0.0.1',
            port: 1234,
            name: 'TCP SDR v4',
            frequency_min: 24,
            frequency_max: 1800,
            serial: ''
        }
    },
    soapysdrremote: {
        excludeFields: [],
        fields: ['host', 'port', 'name', 'frequency_min', 'frequency_max', 'driver', 'serial'],
        defaults: {
            host: '',
            port: 55132,
            name: 'SoapySDR Remote',
            frequency_min: 24,
            frequency_max: 1800,
            driver: '',
            serial: ''
        }
    },
    soapysdrlocal: {
        excludeFields: ['host', 'port'],
        fields: ['name', 'frequency_min', 'frequency_max', 'driver', 'serial'],
        defaults: {
            name: 'SoapySDR USB',
            frequency_min: 24,
            frequency_max: 1800,
            driver: '',
            serial: ''
        }
    },
    uhd: {
        excludeFields: ['host', 'port', 'driver'],
        fields: ['name', 'frequency_min', 'frequency_max', 'serial'],
        defaults: {
            name: 'UHD Device',
            frequency_min: 10,
            frequency_max: 6000,
            serial: ''
        }
    }
};

const rtlUsbTypes = new Set(['rtlsdrusbv3', 'rtlsdrusbv4']);
const rtlTcpTypes = new Set(['rtlsdrtcpv3', 'rtlsdrtcpv4']);

const getRtlGroup = (type) => {
    if (rtlUsbTypes.has(type)) return 'usb';
    if (rtlTcpTypes.has(type)) return 'tcp';
    return null;
};

const getMergedRtlValue = (type) => {
    const group = getRtlGroup(type);
    return group ? `rtlsdr${group}` : type;
};

const isMergedRtlValue = (value) => value === 'rtlsdrusb' || value === 'rtlsdrtcp';


export default function SDRsPage() {
    const { socket } = useSocket();
    const dispatch = useDispatch();
    const [selected, setSelected] = useState([]);
    const [pageSize, setPageSize] = useState(10);
    const [selectedRtlDevice, setSelectedRtlDevice] = useState('');
    const [deleteConfirmText, setDeleteConfirmText] = useState('');
    const [discovering, setDiscovering] = useState(false);
    const hasInitialized = useRef(false);
    const rtlProbeRequested = useRef(false);
    const { t } = useTranslation('hardware');

    const {
        loading,
        sdrs,
        status,
        error,
        openAddDialog,
        openDeleteConfirm,
        formValues,
        soapyServers,
        selectedSdrDevice,
        localSoapyDevices,
        loadingLocalSDRs,
        localRtlDevices,
        loadingLocalRtlSDRs,
    } = useSelector((state) => state.sdrs);
    const rowSelectionModel = useMemo(() => toRowSelectionModel(selected), [selected]);
    const isEditing = Boolean(formValues.id);
    const isDialogLoading = loading || loadingLocalSDRs || loadingLocalRtlSDRs;
    const requiresDeleteConfirmationText = selected.length > 1;
    const canConfirmDelete = !requiresDeleteConfirmationText || deleteConfirmText.trim() === 'DELETE';

    useEffect(() => {
        if (!hasInitialized.current) {
            hasInitialized.current = true;
            dispatch(fetchSoapySDRServers({ socket }));
            dispatch(fetchLocalSoapySDRDevices({ socket }));
        }
    }, [dispatch, socket]);

    useEffect(() => {
        if (openAddDialog) {
            setSelectedRtlDevice('');
        } else {
            rtlProbeRequested.current = false;
        }
    }, [openAddDialog]);

    useEffect(() => {
        const isRtlUsb = rtlUsbTypes.has(formValues.type);
        if (openAddDialog && isRtlUsb && !loadingLocalRtlSDRs && !rtlProbeRequested.current) {
            rtlProbeRequested.current = true;
            dispatch(fetchLocalRtlSdrDevices({ socket }));
        }
    }, [dispatch, formValues.type, loadingLocalRtlSDRs, openAddDialog, socket]);

    const getTypeLabel = (type) => {
        if (rtlUsbTypes.has(type)) return t('sdr.rtlsdr_usb', 'RTL-SDR USB');
        if (rtlTcpTypes.has(type)) return t('sdr.rtlsdr_tcp', 'RTL-SDR TCP');

        switch (type) {
            case 'soapysdrremote':
                return t('sdr.soapysdr_remote');
            case 'soapysdrlocal':
                return t('sdr.soapysdr_usb');
            case 'uhd':
                return t('sdr.uhd');
            default:
                return type || '-';
        }
    };

    const columns = [
        {
            field: 'name', headerName: t('sdr.name'), flex: 1, minWidth: 150
        },
        {
            field: 'type',
            headerName: t('sdr.type'),
            flex: 1,
            minWidth: 100,
            renderCell: (params) => {
                if (!params.row) {
                    return "-";
                }
                return getTypeLabel(params.row.type);
            }
        },
        {
            field: 'host', headerName: t('sdr.host'), flex: 1, minWidth: 150
        },
        {
            field: 'port', headerName: t('sdr.port'), flex: 1, minWidth: 100
        },
        {
            field: 'frequency_min',
            headerName: t('sdr.frequency_range'),
            flex: 1,
            minWidth: 200,
            renderCell: (params) => {
                if (!params.row) {
                    return "-";
                }
                return `${params.row.frequency_min || 0} MHz - ${params.row.frequency_max || 0} MHz`;
            }
        },
        {
            field: 'driver', headerName: t('sdr.driver'), flex: 1, minWidth: 100
        },
        {
            field: 'serial', headerName: t('sdr.serial'), flex: 1, minWidth: 150
        },
    ];

    const handleChange = (e) => {
        const {name, value} = e.target;

        // If changing the SDR type, apply default values for that type
        if (name === 'type') {
            const newType = value;
            const typeConfig = sdrTypeFields[newType];

            if (typeConfig && typeConfig.defaults) {
                // Set excluded fields to null and apply defaults
                const nullifiedExcluded = typeConfig.excludeFields.reduce((acc, field) => {
                    acc[field] = null;
                    return acc;
                }, {});

                dispatch(setFormValues({
                    ...typeConfig.defaults,
                    ...nullifiedExcluded,
                    type: newType
                }));
            } else {
                // Just update the type if no defaults are defined
                dispatch(setFormValues({...formValues, type: newType}));
            }
        } else {
            // Normal field update
            dispatch(setFormValues({...formValues, [name]: value}));
        }

    };

    const handleSubmit = () => {
        dispatch(submitOrEditSDR({socket, formValues}))
            .unwrap()
            .then(() => {
                toast.success(t('sdr.saved_success'));
                dispatch(setOpenAddDialog(false));
            })
            .catch((err) => {
                toast.error(err);
            });
    }

    const handleDelete = () => {
        dispatch(deleteSDRs({ socket, selectedIds: selected }))
            .unwrap()
            .then(() => {
                toast.success(t('sdr.deleted_success'));
                dispatch(setOpenDeleteConfirm(false));
            })
            .catch((err) => {
                toast.error(err);
            });
    };

    // Get the field value or its default from the SDR type configuration
    const getFieldValue = (fieldName) => {
        const selectedType = formValues.type;

        // If we have a value in formValues, use it
        if (formValues[fieldName] !== undefined) {
            return formValues[fieldName];
        }

        // Otherwise check for default in the type configuration
        if (selectedType &&
            sdrTypeFields[selectedType] &&
            sdrTypeFields[selectedType].defaults &&
            sdrTypeFields[selectedType].defaults[fieldName] !== undefined) {
            return sdrTypeFields[selectedType].defaults[fieldName];
        }

        // Fallback to empty string/value
        return '';
    };

    const getValidationErrors = () => {
        const errors = {};
        const selectedType = formValues.type || '';
        const config = selectedType ? sdrTypeFields[selectedType] : null;

        if (!selectedType || !config) return errors;

        const nameValue = getFieldValue('name');
        if (!String(nameValue || '').trim()) errors.name = t('shared.required');

        if (!config.excludeFields.includes('host')) {
            const hostValue = getFieldValue('host');
            if (!String(hostValue || '').trim()) errors.host = t('shared.required');
        }

        if (!config.excludeFields.includes('port')) {
            const portValue = getFieldValue('port');
            if (portValue === '' || portValue === null || portValue === undefined) {
                errors.port = t('shared.required');
            } else if (Number(portValue) <= 0 || Number(portValue) > 65535) {
                errors.port = t('shared.port_range');
            }
        }
        if (!config.excludeFields.includes('serial')) {
            const serialValue = getFieldValue('serial');
            if (!String(serialValue || '').trim()) errors.serial = t('shared.required');
        }

        const minFreq = getFieldValue('frequency_min');
        const maxFreq = getFieldValue('frequency_max');
        if (minFreq !== '' && Number.isNaN(Number(minFreq))) errors.frequency_min = t('shared.must_be_number');
        if (maxFreq !== '' && Number.isNaN(Number(maxFreq))) errors.frequency_max = t('shared.must_be_number');
        if (minFreq !== '' && maxFreq !== '' && Number(minFreq) > Number(maxFreq)) {
            errors.frequency_min = t('shared.min_lte_max');
            errors.frequency_max = t('shared.min_lte_max');
        }

        return errors;
    };

    const validationErrors = getValidationErrors();
    const hasValidationErrors = Object.keys(validationErrors).length > 0;

    const renderFormFields = () => {
        const selectedType = formValues.type || '';
        const mergedRtlValue = getMergedRtlValue(selectedType);
        const typeSelectValue = mergedRtlValue;
        const rtlGroup = getRtlGroup(selectedType);
        const showRtlVersion = Boolean(rtlGroup) || isMergedRtlValue(typeSelectValue);
        const rtlVersion = selectedType.endsWith('v3') ? 'v3' : 'v4';

        // Define common fields that all SDR types have
        const fields = [
            <FormControl key="type-select" fullWidth size="small">
                <InputLabel id="sdr-type-label">{t('sdr.sdr_type')}</InputLabel>
                <Select
                    name="type"
                    labelId="sdr-type-label"
                    label={t('sdr.sdr_type')}
                    size="small"
                    value={typeSelectValue || ''}
                    onChange={(e) => {
                        const nextValue = e.target.value;
                        if (isMergedRtlValue(nextValue)) {
                            const mappedType = nextValue === 'rtlsdrusb' ? 'rtlsdrusbv4' : 'rtlsdrtcpv4';
                            handleChange({target: {name: "type", value: mappedType}});
                        } else {
                            handleChange({target: {name: "type", value: nextValue}});
                        }
                        dispatch(setSelectedSdrDevice('')); // Reset selected SDR when type changes
                    }}
                >
                    <MenuItem key="rtlsdrusb" value="rtlsdrusb">{t('sdr.rtlsdr_usb', 'RTL-SDR USB')}</MenuItem>
                    <MenuItem key="rtlsdrtcp" value="rtlsdrtcp">{t('sdr.rtlsdr_tcp', 'RTL-SDR TCP')}</MenuItem>
                    <MenuItem value="soapysdrremote">{t('sdr.soapysdr_remote')}</MenuItem>
                    <MenuItem value="soapysdrlocal">{t('sdr.soapysdr_usb')}</MenuItem>
                    <MenuItem value="uhd">{t('sdr.uhd')}</MenuItem>
                </Select>
            </FormControl>
        ];

        if (showRtlVersion) {
            fields.push(
                <FormControl key="rtl-version-toggle" fullWidth size="small">
                    <Typography variant="caption" sx={{ mb: 0.5, color: 'text.secondary' }}>
                        {t('sdr.rtlsdr_version', 'RTL-SDR Version')}
                    </Typography>
                    <ToggleButtonGroup
                        exclusive
                        size="small"
                        value={rtlVersion}
                        onChange={(_, value) => {
                            if (!value) return;
                            const group = rtlGroup || (typeSelectValue === 'rtlsdrtcp' ? 'tcp' : 'usb');
                            const mappedType = group === 'tcp'
                                ? (value === 'v3' ? 'rtlsdrtcpv3' : 'rtlsdrtcpv4')
                                : (value === 'v3' ? 'rtlsdrusbv3' : 'rtlsdrusbv4');
                            handleChange({target: {name: "type", value: mappedType}});
                        }}
                    >
                        <ToggleButton value="v3">v3</ToggleButton>
                        <ToggleButton value="v4">v4</ToggleButton>
                    </ToggleButtonGroup>
                </FormControl>
            );
        }

        // If a valid SDR type is selected, add the corresponding fields
        if (selectedType && sdrTypeFields[selectedType]) {
            const config = sdrTypeFields[selectedType];

            if (rtlUsbTypes.has(selectedType)) {
                if (loadingLocalRtlSDRs) {
                    fields.push(
                        <Alert
                            key="loading-rtl-devices"
                            severity="info"
                            sx={{
                                mt: 1,
                                display: 'flex',
                                alignItems: 'center',
                                '& .MuiAlert-message': {
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 1
                                }
                            }}
                        >
                            <Box
                                sx={{
                                    display: 'inline-block',
                                    width: '16px',
                                    height: '16px',
                                    border: '2px solid #e3f2fd',
                                    borderTop: '2px solid #1976d2',
                                    borderRadius: '50%',
                                    animation: 'spin 1s linear infinite',
                                    '@keyframes spin': {
                                        '0%': { transform: 'rotate(0deg)' },
                                        '100%': { transform: 'rotate(360deg)' }
                                    }
                                }}
                            />
                            <Typography variant="body2" component="span">
                                {t('sdr.probing_rtl', 'Probing for local RTL-SDR devices...')}
                            </Typography>
                        </Alert>
                    );
                } else if (localRtlDevices && localRtlDevices.length > 0) {
                    fields.push(
                        <FormControl key="rtl-device-select" fullWidth size="small">
                            <InputLabel id="rtl-device-label">{t('sdr.select_rtl_device', 'RTL-SDR Device')}</InputLabel>
                            <Select
                                labelId="rtl-device-label"
                                label={t('sdr.select_rtl_device', 'RTL-SDR Device')}
                                size="small"
                                value={selectedRtlDevice}
                                onChange={(e) => {
                                    const selectedIndex = e.target.value;
                                    setSelectedRtlDevice(selectedIndex);

                                    if (selectedIndex !== '') {
                                        const selectedDevice = localRtlDevices[selectedIndex];
                                        if (selectedDevice) {
                                            const newValues = {
                                                ...formValues,
                                                name: selectedDevice.label || 'RTL-SDR',
                                                serial: selectedDevice.serial || ''
                                            };
                                            dispatch(setFormValues(newValues));
                                        }
                                    }
                                }}
                            >
                                <MenuItem value="" disabled>{t('sdr.select_sdr')}</MenuItem>
                                {localRtlDevices.map((device, index) => (
                                    <MenuItem key={index} value={index}>
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                            <MemoryIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
                                            <Box component="span">
                                                {device.label || `RTL-SDR ${index}`}
                                                {device.serial ? ` :: ${device.serial}` : ''}
                                            </Box>
                                        </Box>
                                    </MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                    );
                    fields.push(
                        <Button
                            key="rtl-refresh-button"
                            variant="outlined"
                            size="small"
                            onClick={() => dispatch(fetchLocalRtlSdrDevices({ socket }))}
                            sx={{ alignSelf: 'flex-start' }}
                        >
                            {t('sdr.refresh_rtl_devices', 'Refresh RTL-SDR devices')}
                        </Button>
                    );
                } else {
                    fields.push(
                        <Alert key="no-rtl-devices" severity="info" sx={{ mt: 1 }}>
                            {t('sdr.no_rtl_devices', 'No local RTL-SDR devices detected. Please connect a device and refresh.')}
                        </Alert>
                    );
                }
            }

            // Add a dropdown to select local Soapy USB devices
            if (selectedType === 'soapysdrlocal') {
                if (loadingLocalSDRs) {
                    fields.push(
                        <Alert
                            key="loading-local-devices"
                            severity="info"
                            sx={{
                                mt: 1,
                                display: 'flex',
                                alignItems: 'center',
                                '& .MuiAlert-message': {
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 1
                                }
                            }}
                        >
                            <Box
                                sx={{
                                    display: 'inline-block',
                                    width: '16px',
                                    height: '16px',
                                    border: '2px solid #e3f2fd',
                                    borderTop: '2px solid #1976d2',
                                    borderRadius: '50%',
                                    animation: 'spin 1s linear infinite',
                                    '@keyframes spin': {
                                        '0%': { transform: 'rotate(0deg)' },
                                        '100%': { transform: 'rotate(360deg)' }
                                    }
                                }}
                            />
                            <Typography variant="body2" component="span">
                                {t('sdr.probing_local')}
                            </Typography>
                        </Alert>
                    );
                } else if (localSoapyDevices && localSoapyDevices.length > 0) {
                    fields.push(
                        <FormControl key="local-sdr-device-select" fullWidth size="small">
                            <InputLabel id="local-sdr-device-label">{t('sdr.local_sdr_device')}</InputLabel>
                            <Select
                                labelId="local-sdr-device-label"
                                label={t('sdr.local_sdr_device')}
                                size="small"
                                value={selectedSdrDevice}
                                onChange={(e) => {
                                    const selectedSdrIndex = e.target.value;
                                    dispatch(setSelectedSdrDevice(selectedSdrIndex));

                                    if (selectedSdrIndex !== '') {
                                        const selectedSdr = localSoapyDevices[selectedSdrIndex];

                                        if (selectedSdr) {
                                            // Prepare new form values with SDR device information
                                            const newValues = {
                                                ...formValues,
                                                name: selectedSdr.label || 'SoapySDR USB Device',
                                                driver: selectedSdr.driver || '',
                                                serial: selectedSdr.serial || ''
                                            };

                                            dispatch(setFormValues(newValues));
                                        }
                                    }
                                }}
            >
                                <MenuItem value="" disabled>{t('sdr.select_sdr')}</MenuItem>
                                {localSoapyDevices.map((sdr, index) => (
                                    <MenuItem key={index} value={index}>
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                            <MemoryIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
                                            <Box component="span">
                                                {sdr.label || sdr.driver || `SDR Device ${index}`}
                                                {sdr.serial ? ` :: ${sdr.serial}` : ''}
                                            </Box>
                                        </Box>
                                    </MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                    );
                    fields.push(
                        <Button
                            key="soapy-refresh-button"
                            variant="outlined"
                            size="small"
                            onClick={() => dispatch(fetchLocalSoapySDRDevices({ socket }))}
                            sx={{ alignSelf: 'flex-start' }}
                        >
                            {t('sdr.refresh_soapy_devices', 'Refresh SoapySDR devices')}
                        </Button>
                    );
                } else {
                    fields.push(
                        <Alert key="no-local-devices" severity="info" sx={{ mt: 1 }}>
                            {t('sdr.no_soapy_devices')}
                        </Alert>
                    );
                    fields.push(
                        <Button
                            key="soapy-refresh-button"
                            variant="outlined"
                            size="small"
                            onClick={() => dispatch(fetchLocalSoapySDRDevices({ socket }))}
                            sx={{ alignSelf: 'flex-start' }}
                        >
                            {t('sdr.refresh_soapy_devices', 'Refresh SoapySDR devices')}
                        </Button>
                    );
                }
            }

            // Host field - only show for types that don't exclude it
            if (!config.excludeFields.includes('host')) {
                if (selectedType === 'soapysdrremote' && soapyServers && Object.keys(soapyServers).length > 0) {
                    // For SoapySDRRemote, create a dropdown of available servers
                    fields.push(
                        <FormControl key="host-select" fullWidth size="small">
                            <InputLabel id="host-label">{t('sdr.soapysdr_server')}</InputLabel>
                            <Select
                                name="host"
                                labelId="host-label"
                                label={t('sdr.soapysdr_server')}
                                size="small"
                                value={formValues.host || ''}
                                onChange={(e) => {
                                    const serverIp = e.target.value;
                                    const selectedServerEntry = Object.entries(soapyServers).find(([_, server]) => server.ip === serverIp);
                                    const serverInfo = selectedServerEntry ? selectedServerEntry[1] : {};
                                    
                                    // Reset selected SDR when server changes
                                    dispatch(setSelectedSdrDevice(''));

                                    // Use a single dispatch call with all values that need to be updated
                                    dispatch(setFormValues({
                                        ...formValues,
                                        host: serverInfo.ip || '',
                                        port: serverInfo.port || 1234
                                    }));
                                }}
            >
                                {Object.entries(soapyServers).map(([key, server]) => (
                                    <MenuItem key={key} value={server.ip}>
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                            <DnsIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
                                            <Box component="span">
                                                {key}: {server.ip}:{server.port} ({server.sdrs.length} SDRs)
                                            </Box>
                                        </Box>
                                    </MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                    );

                    // If a server is selected, add a dropdown to select SDR devices from that server
                    if (formValues.host) {
                        const selectedServerEntry = Object.entries(soapyServers).find(([_, server]) => server.ip === formValues.host);
                        const selectedServerInfo = selectedServerEntry ? selectedServerEntry[1] : null;
                        
                        if (selectedServerInfo && selectedServerInfo.sdrs && selectedServerInfo.sdrs.length > 0) {
                            fields.push(
                                <FormControl key="sdr-device-select" fullWidth size="small">
                                    <InputLabel id="sdr-device-label">{t('sdr.sdr_device')}</InputLabel>
                                    <Select
                                        labelId="sdr-device-label"
                                        label={t('sdr.sdr_device')}
                                        size="small"
                                        value={selectedSdrDevice}
                                        onChange={(e) => {
                                            const selectedSdrIndex = e.target.value;
                                            dispatch(setSelectedSdrDevice(selectedSdrIndex));
                                            
                                            if (selectedSdrIndex !== '') {
                                                const selectedSdr = selectedServerInfo.sdrs[selectedSdrIndex];
                                                
                                                if (selectedSdr) {
                                                    // Prepare new form values with SDR device information
                                                    const newValues = {
                                                        ...formValues,
                                                        name: selectedSdr.label || 'SoapySDR Device',
                                                        driver: selectedSdr['remote:driver'] || selectedSdr.driver || '',
                                                        serial: selectedSdr.serial || ''
                                                    };
                                                    
                                                    dispatch(setFormValues(newValues));
                                                }
                                            }
                                        }}
                    >
                                        <MenuItem value="" disabled>{t('sdr.select_sdr')}</MenuItem>
                                        {selectedServerInfo.sdrs.map((sdr, index) => (
                                            <MenuItem key={index} value={index}>
                                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                                    <MemoryIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
                                                    <Box component="span">
                                                        {sdr.label || sdr.driver || `SDR Device ${index}`}
                                                        {sdr.serial ? ` :: ${sdr.serial}` : ''}
                                                    </Box>
                                                </Box>
                                            </MenuItem>
                                        ))}
                                    </Select>
                                </FormControl>
                            );
                        }
                    }
                } else {
                    fields.push(
                        <TextField
                            key="host"
                            name="host"
                            label={t('sdr.host')}
                            fullWidth
                            size="small"
                            onChange={handleChange}
                            value={getFieldValue('host')}
                            error={Boolean(validationErrors.host)}
                            required
                        />
                    );
                }
            }

            // Port field - only show for types that don't exclude it
            if (!config.excludeFields.includes('port')) {
                fields.push(
                    <TextField
                        key="port"
                        name="port"
                        label={t('sdr.port')}
                        fullWidth
                        size="small"
                        type="number"
                        onChange={handleChange}
                        value={getFieldValue('port')}
                        error={Boolean(validationErrors.port)}
                        required
                    />
                );
            }

            // Add the common fields that all types have
            fields.push(
                <TextField
                    key="name"
                    name="name"
                    label={t('sdr.name')}
                    fullWidth
                    size="small"
                    onChange={handleChange}
                    value={getFieldValue('name')}
                    error={Boolean(validationErrors.name)}
                    required
                />,
                <TextField
                    key="frequency_min"
                    name="frequency_min"
                    label={t('sdr.min_frequency_mhz')}
                    fullWidth
                    size="small"
                    type="number"
                    onChange={handleChange}
                    value={getFieldValue('frequency_min')}
                    error={Boolean(validationErrors.frequency_min)}
                    InputProps={{ endAdornment: <InputAdornment position="end">MHz</InputAdornment> }}
                />,
                <TextField
                    key="frequency_max"
                    name="frequency_max"
                    label={t('sdr.max_frequency_mhz')}
                    fullWidth
                    size="small"
                    type="number"
                    onChange={handleChange}
                    value={getFieldValue('frequency_max')}
                    error={Boolean(validationErrors.frequency_max)}
                    InputProps={{ endAdornment: <InputAdornment position="end">MHz</InputAdornment> }}
                />,
            );

            // Driver field - only show for types that don't exclude it
            if (!config.excludeFields.includes('driver')) {
                fields.push(
                    <TextField
                        key="driver"
                        name="driver"
                        label={t('sdr.driver')}
                        fullWidth
                        size="small"
                        onChange={handleChange}
                        value={getFieldValue('driver')}
                    />
                );
            }

            // Serial field - only show for types that don't exclude it
            if (!config.excludeFields.includes('serial')) {
                fields.push(
                    <TextField
                        key="serial"
                        name="serial"
                    label={t('sdr.serial')}
                    fullWidth
                    size="small"
                    onChange={handleChange}
                    value={getFieldValue('serial')}
                    error={Boolean(validationErrors.serial)}
                    required
                />
                );
            }


        }

        return fields;
    };
    return (
        <Paper elevation={3} sx={{padding: 2, marginTop: 0, borderRadius: 0}}>
            <Alert severity="info" sx={{mb: 2}}>
                <AlertTitle>{t('sdr.title')}</AlertTitle>
                {t('sdr.subtitle')}
            </Alert>
            {soapyServers && Object.keys(soapyServers).length > 0 ? (
                <Alert severity="success" sx={{mb: 2}}>
                    <AlertTitle>{t('sdr.discovered_servers')}</AlertTitle>
                    {Object.entries(soapyServers).map(([key, server], index) => (
                        <Box key={key} sx={{pl: 2, mt: 1}}>
                            <Typography component="div" variant="body2" color="text.secondary"
                                        sx={{fontFamily: 'monospace'}}>
                                {t('sdr.server_entry', { key, ip: server['ip'], port: server['port'], count: server['sdrs'].length })}
                            </Typography>
                        </Box>
                    ))}
                </Alert>
            ) : null}
            <Box component="form" sx={{mt: 2}}>
                <Box sx={{width: '100%'}}>
                    <DataGrid
                        loading={loading}
                        rows={sdrs
                            .filter(row => row.type !== 'sigmfplayback')
                            .map(row => ({
                                ...row,
                                host: row.host || '-',
                                port: row.port || '-',
                                serial: row.serial || '-'
                            }))}
                        columns={columns}
                        checkboxSelection
                        disableRowSelectionExcludeModel
                        onRowSelectionModelChange={(selected) => {
                            setSelected(toSelectedIds(selected));
                        }}
                        initialState={{
                            pagination: {paginationModel: {pageSize: 10}},
                            sorting: {
                                sortModel: [{field: 'name', sort: 'desc'}],
                            },
                        }}
                        rowSelectionModel={rowSelectionModel}
                        pageSize={pageSize}
                        pageSizeOptions={[5, 10, 25, {value: -1, label: t('shared.all')}]}
                        onPageSizeChange={(newPageSize) => setPageSize(newPageSize)}
                        rowsPerPageOptions={[5, 10, 25]}
                        getRowId={(row) => row.id}
                        localeText={{
                            noRowsLabel: t('sdr.no_sdrs')
                        }}
                        sx={{
                            border: 0,
                            marginTop: 2,
                            [`& .${gridClasses.cell}:focus, & .${gridClasses.cell}:focus-within`]: {
                                outline: 'none',
                            },
                            [`& .${gridClasses.columnHeader}:focus, & .${gridClasses.columnHeader}:focus-within`]:
                                {
                                    outline: 'none',
                                },
                            '& .MuiDataGrid-columnHeaders': {
                                backgroundColor: (theme) => alpha(
                                    theme.palette.primary.main,
                                    theme.palette.mode === 'dark' ? 0.18 : 0.10
                                ),
                                borderBottom: (theme) => `2px solid ${alpha(theme.palette.primary.main, 0.45)}`,
                            },
                            '& .MuiDataGrid-columnHeader': {
                                backgroundColor: 'transparent',
                            },
                            '& .MuiDataGrid-columnHeaderTitle': {
                                fontSize: '0.8125rem',
                                fontWeight: 700,
                                letterSpacing: '0.02em',
                            },
                            '& .MuiDataGrid-overlay': {
                                fontSize: '0.875rem',
                                fontStyle: 'italic',
                                color: 'text.secondary',
                            },
                        }}
                    />
                    <SelectionActionBar
                        selectedCount={selected.length}
                        onClearSelection={() => setSelected([])}
                        primaryActions={
                            <>
                                <Button
                                    variant="contained"
                                    onClick={() => {
                                        dispatch(resetFormValues());
                                        dispatch(setSelectedSdrDevice(''));
                                        dispatch(setOpenAddDialog(true));
                                    }}
                                    disabled={loading}
                                >
                                    {t('sdr.add')}
                                </Button>
                                <Button
                                    variant="contained"
                                    disabled={selected.length !== 1 || loading}
                                    onClick={() => {
                                        const selectedRow = sdrs.find(row => row.id === selected[0]);
                                        if (selectedRow) {
                                            dispatch(setFormValues(selectedRow));
                                            dispatch(setOpenAddDialog(true));
                                        }
                                    }}
                                >
                                    {t('sdr.edit')}
                                </Button>
                                <Button
                                    variant="contained"
                                    disabled={selected.length < 1 || loading}
                                    color="error"
                                    onClick={() => {
                                        setDeleteConfirmText('');
                                        dispatch(setOpenDeleteConfirm(true));
                                    }}
                                >
                                    {t('sdr.delete')}
                                </Button>
                            </>
                        }
                        secondaryActions={
                            <Button
                                variant="contained"
                                color="primary"
                                disabled={discovering || loading}
                                onClick={async () => {
                                    if (!socket) return;
                                    setDiscovering(true);
                                    try {
                                        await dispatch(startSoapySDRDiscovery({ socket })).unwrap();
                                        toast.success(t('sdr.discovery_started', 'SoapySDR discovery started'));
                                    } catch (error) {
                                        console.error('Failed to start SoapySDR discovery:', error);
                                        toast.error(t('sdr.discovery_failed', 'Failed to start SoapySDR discovery'));
                                    } finally {
                                        setDiscovering(false);
                                    }
                                }}
                            >
                                {discovering
                                    ? t('sdr.discovering_servers', 'Discovering...')
                                    : t('sdr.discover_servers', 'Discover SoapySDR Servers')}
                            </Button>
                        }
                    />
                    <Stack direction="row" spacing={2} style={{marginTop: 15}}>
                        <Dialog
                            fullWidth={true}
                            open={openAddDialog}
                            onClose={() => dispatch(setOpenAddDialog(false))}
                            PaperProps={{
                                sx: {
                                    bgcolor: 'background.paper',
                                    border: (theme) => `1px solid ${theme.palette.divider}`,
                                    borderRadius: 2,
                                }
                            }}
                        >
                            <DialogTitle
                                sx={{
                                    bgcolor: (theme) => theme.palette.mode === 'dark' ? 'grey.900' : 'grey.100',
                                    borderBottom: (theme) => `1px solid ${theme.palette.divider}`,
                                    fontSize: '1.25rem',
                                    fontWeight: 'bold',
                                    py: 2.5,
                                }}
                            >
                                {isEditing ? t('sdr.edit_dialog_title') : t('sdr.add_dialog_title')}
                            </DialogTitle>
                            <DialogContent sx={{ px: 3, py: 3 }}>
                                <Box
                                    component="fieldset"
                                    disabled={isDialogLoading}
                                    sx={{
                                        border: 0,
                                        padding: 0,
                                        margin: 0,
                                        minWidth: 0,
                                    }}
                                >
                                    <Stack spacing={2} sx={{ mt: 3 }}>
                                        {renderFormFields()}
                                    </Stack>
                                </Box>
                            </DialogContent>
                            <DialogActions
                                sx={{
                                    bgcolor: (theme) => theme.palette.mode === 'dark' ? 'grey.900' : 'grey.100',
                                    borderTop: (theme) => `1px solid ${theme.palette.divider}`,
                                    px: 3,
                                    py: 2.5,
                                    gap: 2,
                                }}
                            >
                                <Button
                                    onClick={() => dispatch(setOpenAddDialog(false))}
                                    variant="outlined"
                                    sx={{
                                        borderColor: (theme) => theme.palette.mode === 'dark' ? 'grey.700' : 'grey.400',
                                        '&:hover': {
                                            borderColor: (theme) => theme.palette.mode === 'dark' ? 'grey.600' : 'grey.500',
                                            bgcolor: (theme) => theme.palette.mode === 'dark' ? 'grey.800' : 'grey.200',
                                        },
                                    }}
                                >
                                    {t('sdr.cancel')}
                                </Button>
                                <Button
                                    color="success"
                                    variant="contained"
                                    onClick={handleSubmit}
                                    disabled={hasValidationErrors || loading}
                                >
                                    {t('sdr.submit')}
                                </Button>
                            </DialogActions>
                        </Dialog>
                        <Dialog
                            open={openDeleteConfirm}
                            onClose={() => {
                                setDeleteConfirmText('');
                                dispatch(setOpenDeleteConfirm(false));
                            }}
                            maxWidth="sm"
                            fullWidth
                            PaperProps={{
                                sx: {
                                    bgcolor: 'background.paper',
                                    borderRadius: 2,
                                }
                            }}
                        >
                            <DialogTitle
                                sx={{
                                    bgcolor: 'error.main',
                                    color: 'error.contrastText',
                                    fontSize: '1.125rem',
                                    fontWeight: 600,
                                    py: 2,
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 1.5,
                                }}
                            >
                                <Box
                                    component="span"
                                    sx={{
                                        width: 24,
                                        height: 24,
                                        borderRadius: '50%',
                                        bgcolor: 'error.contrastText',
                                        color: 'error.main',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        fontWeight: 'bold',
                                        fontSize: '1rem',
                                    }}
                                >
                                    !
                                </Box>
                                {t('sdr.confirm_deletion')}
                            </DialogTitle>
                            <DialogContent sx={{ px: 3, pt: 3, pb: 3 }}>
                                <Typography variant="body1" sx={{ mt: 2, mb: 2, color: 'text.primary' }}>
                                    {t('sdr.confirm_delete_message')}
                                </Typography>
                                <Typography variant="body2" sx={{ mb: 2, fontWeight: 600, color: 'text.secondary' }}>
                                    {selected.length === 1
                                        ? t('sdr.delete_list_single')
                                        : t('sdr.delete_list_plural', { count: selected.length })}
                                </Typography>
                                {requiresDeleteConfirmationText && (
                                    <TextField
                                        fullWidth
                                        size="small"
                                        label={t('common.type_delete_to_confirm', 'Type DELETE to confirm')}
                                        value={deleteConfirmText}
                                        onChange={(e) => setDeleteConfirmText(e.target.value)}
                                        sx={{ mb: 2 }}
                                    />
                                )}
                                <Box sx={{
                                    maxHeight: 300,
                                    overflowY: 'auto',
                                    bgcolor: (theme) => theme.palette.mode === 'dark' ? 'grey.900' : 'grey.50',
                                    borderRadius: 1,
                                    border: (theme) => `1px solid ${theme.palette.divider}`,
                                }}>
                                    {selected.map((id, index) => {
                                        const sdr = sdrs.find(s => s.id === id);
                                        if (!sdr) return null;
                                        return (
                                            <Box
                                                key={id}
                                                sx={{
                                                    p: 2,
                                                    borderBottom: index < selected.length - 1 ? (theme) => `1px solid ${theme.palette.divider}` : 'none',
                                                }}
                                            >
                                                <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1, color: 'text.primary' }}>
                                                    {sdr.name}
                                                </Typography>
                                                <Box sx={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: 1, columnGap: 2 }}>
                                                    <Typography variant="body2" sx={{ fontSize: '0.813rem', color: 'text.secondary', fontWeight: 500 }}>
                                                        {t('sdr.type')}:
                                                    </Typography>
                                                    <Typography variant="body2" sx={{ fontSize: '0.813rem', color: 'text.primary' }}>
                                                        {getTypeLabel(sdr.type)}
                                                    </Typography>

                                                    {sdr.host && sdr.host !== '-' && (
                                                        <>
                                                            <Typography variant="body2" sx={{ fontSize: '0.813rem', color: 'text.secondary', fontWeight: 500 }}>
                                                                {t('sdr.host')}:
                                                            </Typography>
                                                            <Typography variant="body2" sx={{ fontSize: '0.813rem', color: 'text.primary' }}>
                                                                {sdr.host}{sdr.port && sdr.port !== '-' ? `:${sdr.port}` : ''}
                                                            </Typography>
                                                        </>
                                                    )}

                                                    {sdr.serial && sdr.serial !== '-' && (
                                                        <>
                                                            <Typography variant="body2" sx={{ fontSize: '0.813rem', color: 'text.secondary', fontWeight: 500 }}>
                                                                {t('sdr.serial')}:
                                                            </Typography>
                                                            <Typography variant="body2" sx={{ fontSize: '0.813rem', color: 'text.primary' }}>
                                                                {sdr.serial}
                                                            </Typography>
                                                        </>
                                                    )}

                                                    <Typography variant="body2" sx={{ fontSize: '0.813rem', color: 'text.secondary', fontWeight: 500 }}>
                                                        {t('sdr.frequency_range')}:
                                                    </Typography>
                                                    <Typography variant="body2" sx={{ fontSize: '0.813rem', color: 'text.primary' }}>
                                                        {sdr.frequency_min} - {sdr.frequency_max} MHz
                                                    </Typography>
                                                </Box>
                                            </Box>
                                        );
                                    })}
                                </Box>
                            </DialogContent>
                            <DialogActions
                                sx={{
                                    bgcolor: (theme) => theme.palette.mode === 'dark' ? 'grey.900' : 'grey.50',
                                    borderTop: (theme) => `1px solid ${theme.palette.divider}`,
                                    px: 3,
                                    py: 2,
                                    gap: 1.5,
                                }}
                            >
                                <Button
                                    onClick={() => dispatch(setOpenDeleteConfirm(false))}
                                    variant="outlined"
                                    color="inherit"
                                    sx={{
                                        minWidth: 100,
                                        textTransform: 'none',
                                        fontWeight: 500,
                                    }}
                                >
                                    {t('sdr.cancel')}
                                </Button>
                                <Button
                                    variant="contained"
                                    onClick={handleDelete}
                                    color="error"
                                    disabled={!canConfirmDelete || loading}
                                    sx={{
                                        minWidth: 100,
                                        textTransform: 'none',
                                        fontWeight: 600,
                                    }}
                                >
                                    {t('sdr.delete')}
                                </Button>
                            </DialogActions>
                        </Dialog>
                    </Stack>
                </Box>
            </Box>
        </Paper>
    );
}
