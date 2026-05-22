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
import {Alert, AlertTitle, Button, FormControl, InputLabel, MenuItem, Select, TextField} from "@mui/material";
import {useEffect, useMemo, useState} from "react";
import { useTranslation } from 'react-i18next';
import DialogTitle from "@mui/material/DialogTitle";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import {useSocket} from "../common/socket.jsx";
import { toast } from '../../utils/toast-with-timestamp.jsx';
import {useDispatch, useSelector} from 'react-redux';
import {
    deleteCameras,
    fetchCameras,
    submitOrEditCamera,
    setOpenDeleteConfirm,
    setOpenAddDialog,
    setFormValues,
} from './camera-slice.jsx';
import Paper from "@mui/material/Paper";
import {toRowSelectionModel, toSelectedIds} from '../../utils/datagrid-selection.js';

export default function CameraTable() {
    const {socket} = useSocket();
    const dispatch = useDispatch();
    const [selected, setSelected] = useState([]);
    const [pageSize, setPageSize] = useState(10);
    const { t } = useTranslation('hardware');
    const {
        loading,
        cameras,
        status,
        error,
        openAddDialog,
        openDeleteConfirm,
        formValues
    } = useSelector((state) => state.cameras);
    const rowSelectionModel = useMemo(() => toRowSelectionModel(selected), [selected]);

    const columns = [
        {field: 'name', headerName: t('camera.name'), flex: 1, minWidth: 150},
        {field: 'url', headerName: t('camera.url'), flex: 1, minWidth: 200},
        {field: 'type', headerName: t('camera.type'), flex: 1, minWidth: 100},
    ];

    const handleChange = (e) => {
        const {name, value} = e.target;
        dispatch(setFormValues({...formValues, [name]: value}));
    };

    const handleSubmit = () => {
        dispatch(submitOrEditCamera({socket, formValues}))
            .unwrap()
            .then(() => {
                toast.success(t('camera.saved_success'));
                setOpenAddDialog(false);
            })
            .catch((err) => {
                toast.error(err.message);
            });
    }

    const handleDelete = () => {
        dispatch(deleteCameras({socket, selectedIds: selected}))
            .unwrap()
            .then(() => {
                toast.success(t('camera.deleted_success'));
                dispatch(setOpenDeleteConfirm(false));
            })
            .catch((err) => {
                toast.error(err.message);
            });
    };

    return (
        <Paper elevation={3} sx={{padding: 2, marginTop: 0, borderRadius: 0}}>
            <Alert severity="info">
                <AlertTitle>{t('camera.title')}</AlertTitle>
                {t('camera.subtitle')}
            </Alert>
            <Box component="form" sx={{mt: 2}}>
                <Box sx={{width: '100%'}}>
                    <DataGrid
                        loading={loading}
                        rows={cameras}
                        columns={columns}
                        checkboxSelection
                        disableRowSelectionOnClick
                        onRowSelectionModelChange={(selected) => {
                            setSelected(toSelectedIds(selected));
                        }}
                        initialState={{
                            pagination: {paginationModel: {pageSize: 5}},
                            sorting: {
                                sortModel: [{field: 'name', sort: 'desc'}],
                            },
                        }}
                        rowSelectionModel={rowSelectionModel}
                        pageSize={pageSize}
                        pageSizeOptions={[5, 10, 25, {value: -1, label: 'All'}]}
                        onPageSizeChange={(newPageSize) => setPageSize(newPageSize)}
                        rowsPerPageOptions={[5, 10, 25]}
                        getRowId={(row) => row.id}
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
                        }}
                    />
                    <Stack direction="row" spacing={2} style={{marginTop: 15}}>
                        <Button variant="contained" onClick={() => dispatch(setOpenAddDialog(true))}>
                            {t('camera.add')}
                        </Button>
                        <Dialog fullWidth={true} open={openAddDialog} onClose={() => dispatch(setOpenAddDialog(false))}>
                            <DialogTitle>{t('camera.add_dialog_title')}</DialogTitle>
                            <DialogContent>
                                <Stack spacing={2}>
                                    <TextField name="name" label={t('camera.name')} fullWidth variant="filled"
                                               onChange={handleChange}
                                               value={formValues.name}/>
                                    <TextField name="url" label={t('camera.url')} fullWidth variant="filled"
                                               onChange={handleChange} value={formValues.url}/>
                                    <FormControl fullWidth variant="filled">
                                        <InputLabel id="camera-type-label">{t('camera.camera_type')}</InputLabel>
                                        <Select
                                            name="type"
                                            labelId="camera-type-label"
                                            value={formValues.type}
                                            onChange={(e) => handleChange({
                                                target: {
                                                    name: "type",
                                                    value: e.target.value
                                                }
                                            })}
                                            variant={'filled'}>
                                            <MenuItem value="webrtc">{t('camera.webrtc')}</MenuItem>
                                            <MenuItem value="hls">{t('camera.hls')}</MenuItem>
                                            <MenuItem value="mjpeg">{t('camera.mjpeg')}</MenuItem>
                                        </Select>
                                    </FormControl>
                                </Stack>
                            </DialogContent>
                            <DialogActions style={{padding: '0px 24px 20px 20px'}}>
                                <Button onClick={() => dispatch(setOpenAddDialog(false))} color="error"
                                        variant="outlined">
                                    {t('camera.cancel')}
                                </Button>
                                <Button
                                    color="success"
                                    variant="contained"
                                    onClick={handleSubmit}
                                >
                                    {t('camera.submit')}
                                </Button>
                            </DialogActions>
                        </Dialog>
                        <Button
                            variant="contained"
                            disabled={selected.length !== 1}
                            onClick={() => {
                                const selectedRow = cameras.find(row => row.id === selected[0]);
                                if (selectedRow) {
                                    dispatch(setFormValues(selectedRow));
                                    dispatch(setOpenAddDialog(true));
                                }
                            }}
                        >
                            {t('camera.edit')}
                        </Button>
                        <Button
                            variant="contained"
                            disabled={selected.length < 1}
                            color="error"
                            onClick={() => dispatch(setOpenDeleteConfirm(true))}
                        >
                            {t('camera.delete')}
                        </Button>
                        <Dialog
                            open={openDeleteConfirm}
                            onClose={() => dispatch(setOpenDeleteConfirm(false))}
                        >
                            <DialogTitle>{t('camera.confirm_deletion')}</DialogTitle>
                            <DialogContent>
                                {t('camera.confirm_delete_message')}
                            </DialogContent>
                            <DialogActions>
                                <Button onClick={() => dispatch(setOpenDeleteConfirm(false))} color="error"
                                        variant="outlined">
                                    {t('camera.cancel')}
                                </Button>
                                <Button
                                    variant="contained"
                                    onClick={handleDelete}
                                    color="error"
                                >
                                    {t('camera.delete')}
                                </Button>
                            </DialogActions>
                        </Dialog>
                    </Stack>
                </Box>
            </Box>
        </Paper>

    );
}
