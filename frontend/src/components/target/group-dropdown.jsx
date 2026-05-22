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

import * as React from "react";
import {
    FormControl,
    InputLabel,
    ListSubheader,
    MenuItem,
    Select,
} from "@mui/material";
import {useSocket} from "../common/socket.jsx";
import {useDispatch, useSelector} from "react-redux";
import {
    fetchSatellitesByGroupId,
    setSatGroupId,
    setSatelliteId,
    setSatelliteGroupSelectOpen,
    setGroupOfSats,
} from './target-slice.jsx';
import { useTranslation } from 'react-i18next';

const SATELLITE_NUMBER_LIMIT = 150;

const GroupDropdown = React.memo(function GroupDropdown() {
    const { socket } = useSocket();
    const dispatch = useDispatch();
    const { t } = useTranslation('target');
    const {
        satGroups,
        groupId,
        trackingState,
    } = useSelector((state) => state.targetSatTrack);

    const handleGroupChange = (e) => {
        const newGroupId = e.target.value;
        if (!newGroupId || newGroupId === 'none') {
            return;
        }
        dispatch(setSatGroupId(newGroupId));
        dispatch(fetchSatellitesByGroupId({ socket, groupId: newGroupId }));
        dispatch(setSatelliteId(''));
        dispatch(setGroupOfSats([]));
    };

    const handleSelectOpenEvent = (event) => {
        dispatch(setSatelliteGroupSelectOpen(true));
    };

    const handleSelectCloseEvent = (event) => {
        dispatch(setSatelliteGroupSelectOpen(false));
    };

    return (
        <FormControl
            disabled={trackingState['rotator_state'] === "tracking" || trackingState['rig_state'] === "tracking"}
            sx={{ minWidth: 200, margin: 0 }}
            fullWidth
            size="small"
        >
            <InputLabel id="grouped-select-label">{t('group_dropdown.label')}</InputLabel>
            <Select
                onClose={handleSelectCloseEvent}
                onOpen={handleSelectOpenEvent}
                onChange={handleGroupChange}
                value={satGroups.length > 0 ? groupId : ""}
                id="grouped-select"
                labelId="grouped-select-label"
                label={t('group_dropdown.label')}
                size="small"
            >
                <ListSubheader>{t('group_dropdown.user_groups')}</ListSubheader>
                {satGroups.filter(group => group.type === "user").length === 0 ? (
                    <MenuItem disabled value="">
                        {t('group_dropdown.none_created')}
                    </MenuItem>
                ) : (
                    satGroups.map((group, index) => {
                        if (group.type === "user") {
                            return (
                                <MenuItem
                                    disabled={group.satellite_ids.length > SATELLITE_NUMBER_LIMIT}
                                    value={group.id}
                                    key={index}
                                >
                                    {group.name} ({group.satellite_ids.length})
                                </MenuItem>
                            );
                        }
                    })
                )}
                <ListSubheader>{t('group_dropdown.tle_groups')}</ListSubheader>
                {satGroups.map((group, index) => {
                    if (group.type === "system") {
                        return (
                            <MenuItem
                                disabled={group.satellite_ids.length > SATELLITE_NUMBER_LIMIT}
                                value={group.id}
                                key={index}
                            >
                                {group.name} ({group.satellite_ids.length})
                            </MenuItem>
                        );
                    }
                })}
            </Select>
        </FormControl>
    );
});

export default GroupDropdown;
