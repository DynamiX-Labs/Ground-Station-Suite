
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

import React, {useCallback, useEffect, useRef, useState} from 'react';
import {
    MapContainer,
    TileLayer,
    Marker,
    Polyline,
    Polygon,
    useMapEvents,
} from 'react-leaflet';
import { Box, Fab, Slider } from "@mui/material";
import { SatelliteAlt } from '@mui/icons-material';
import HomeIcon from '@mui/icons-material/Home';
import FullscreenIcon from '@mui/icons-material/Fullscreen';
import FilterCenterFocusIcon from '@mui/icons-material/FilterCenterFocus';
import SettingsIcon from '@mui/icons-material/Settings';
import * as satellite from 'satellite.js';
import { getTileLayerById } from "../common/tile-layers.jsx";
import {homeIcon, sunIcon, moonIcon, satelliteIcon2} from '../common/dataurl-icons.jsx';
import {
    MapTitleBar,
    MapStatusBar,
    InternationalDateLinePolyline,
    MapArrowControls,
    SimpleTruncatedHtml,
    getClassNamesBasedOnGridEditing,
    ThemedLeafletTooltip,
    humanizeAltitude,
    humanizeVelocity,
} from "../common/common.jsx";
import CoordinateGrid from "../common/mercator-grid.jsx";
import createTerminatorLine from "../common/terminator-line.jsx";
import {getSunMoonCoords} from "../common/sunmoon.jsx";
import {getSatelliteCoverageCircle} from "../common/tracking-logic.jsx";
import {useSelector} from "react-redux";

// global leaflet map object
let MapObject = null;

const SatelliteMapContainer = ({ satelliteData }) => {
    const [currentPastSatellitesPaths, setCurrentPastSatellitesPaths] = useState([]);
    const [currentFutureSatellitesPaths, setCurrentFutureSatellitesPaths] = useState([]);
    const [currentSatellitesPosition, setCurrentSatellitesPosition] = useState([]);
    const [currentSatellitesCoverage, setCurrentSatellitesCoverage] = useState([]);
    const [terminatorLine, setTerminatorLine] = useState([]);
    const [daySidePolygon, setDaySidePolygon] = useState([]);
    const [sunPos, setSunPos] = useState([0, 0]);
    const [moonPos, setMoonPos] = useState([0, 0]);
    const [mapZoomLevel, setMapZoomLevel] = useState(2);
    const [satelliteRecord, setSatelliteRecord] = useState(null);
    const [satellitePosition, setSatellitePosition] = useState({ lat: 0, lon: 0, alt: 0, vel: 0 });

    const coverageRef = useRef(null);

    // Configuration options (you can make these props if needed)
    const config = {
        tileLayerID: 'satellite',
        pastOrbitLineColor: '#ff0000',
        futureOrbitLineColor: '#00ff00',
        satelliteCoverageColor: '#ffffff',
        showTooltip: true,
        showPastOrbitPath: false,
        showFutureOrbitPath: false,
        showSatelliteCoverage: true,
        orbitProjectionDuration: 90, // minutes
    };

    const {location} = useSelector(state => state.location);

    const handleSetMapZoomLevel = useCallback((zoomLevel) => {
        setMapZoomLevel(zoomLevel);
    }, []);

    // Subscribe to map events
    function MapEventComponent({ handleSetMapZoomLevel }) {
        const mapEvents = useMapEvents({
            zoomend: () => {
                const mapZoom = mapEvents.getZoom();
                handleSetMapZoomLevel(mapZoom);
                localStorage.setItem('satellite-map-zoom-level', mapZoom);
            },
        });
        return null;
    }

    // Initialize satellite record from TLE data
    useEffect(() => {
        if (satelliteData && satelliteData.tle1 && satelliteData.tle2) {
            try {
                const satrec = satellite.twoline2satrec(satelliteData.tle1, satelliteData.tle2);
                setSatelliteRecord(satrec);
            } catch (error) {
                console.error('Error parsing TLE data:', error);
            }
        }
    }, [satelliteData]);

    // Calculate satellite position using satellite.js
    const calculateSatellitePosition = useCallback((satrec, date) => {
        if (!satrec) return null;

        try {
            const positionAndVelocity = satellite.propagate(satrec, date);
            if (!positionAndVelocity) {
                return null;
            }
            const positionEci = positionAndVelocity.position;
            const velocityEci = positionAndVelocity.velocity;

            if (!positionEci || typeof positionEci.x !== 'number') {
                return null;
            }

            const gmst = satellite.gstime(date);
            const positionGd = satellite.eciToGeodetic(positionEci, gmst);

            const longitude = satellite.degreesLong(positionGd.longitude);
            const latitude = satellite.degreesLat(positionGd.latitude);
            const altitude = positionGd.height;

            // Calculate velocity magnitude
            const velocity = velocityEci ? Math.sqrt(
                velocityEci.x * velocityEci.x +
                velocityEci.y * velocityEci.y +
                velocityEci.z * velocityEci.z
            ) : 0;

            return {
                lat: latitude,
                lon: longitude,
                alt: altitude,
                vel: velocity
            };
        } catch (error) {
            console.error('Error calculating satellite position:', error);
            return null;
        }
    }, []);

    // Generate orbit paths
    const generateOrbitPaths = useCallback((satrec, currentTime) => {
        if (!satrec) return { past: [], future: [] };

        const pastPath = [];
        const futurePath = [];
        const stepMinutes = 2; // Calculate position every 2 minutes

        // Generate past orbit (90 minutes back)
        for (let i = config.orbitProjectionDuration; i >= 0; i -= stepMinutes) {
            const time = new Date(currentTime.getTime() - i * 60 * 1000);
            const pos = calculateSatellitePosition(satrec, time);
            if (pos) {
                pastPath.push([pos.lat, pos.lon]);
            }
        }

        // Generate future orbit (90 minutes forward)
        for (let i = stepMinutes; i <= config.orbitProjectionDuration; i += stepMinutes) {
            const time = new Date(currentTime.getTime() + i * 60 * 1000);
            const pos = calculateSatellitePosition(satrec, time);
            if (pos) {
                futurePath.push([pos.lat, pos.lon]);
            }
        }

        return { past: pastPath, future: futurePath };
    }, [calculateSatellitePosition, config.orbitProjectionDuration]);

    useEffect(() => {
        const updateInterval = setInterval(() => {
            satelliteUpdate(new Date());
        }, 3000);

        // Initial update
        satelliteUpdate(new Date());

        return () => {
            clearInterval(updateInterval);
        };
    }, [satelliteRecord]);

    const satelliteUpdate = function (now) {
        if (satelliteRecord && satelliteData) {
            const position = calculateSatellitePosition(satelliteRecord, now);

            if (!position) {
                console.warn("Could not calculate satellite position");
                return;
            }

            setSatellitePosition(position);

            const satelliteName = satelliteData.name;
            const satelliteId = satelliteData.norad_id;
            const { lat: latitude, lon: longitude, alt: altitude, vel: velocity } = position;

            // Generate orbit paths
            const paths = generateOrbitPaths(satelliteRecord, now);

            // Generate current positions for the satellite
            let currentPos = [];
            let currentCoverage = [];
            let currentFuturePaths = [];
            let currentPastPaths = [];

            if (paths) {
                // Past path
                if (config.showPastOrbitPath && paths.past.length > 0) {
                    currentPastPaths.push(
                        <Polyline
                            key={`past-path-${satelliteId}`}
                            positions={paths.past}
                            pathOptions={{
                                color: config.pastOrbitLineColor,
                                weight: 2,
                                opacity: 1,
                                smoothFactor: 1,
                            }}
                        />
                    );
                }

                // Future path
                if (config.showFutureOrbitPath && paths.future.length > 0) {
                    currentFuturePaths.push(
                        <Polyline
                            key={`future-path-${satelliteId}`}
                            positions={paths.future}
                            pathOptions={{
                                color: config.futureOrbitLineColor,
                                weight: 2,
                                opacity: 0.8,
                                dashArray: "3 3",
                                smoothFactor: 1,
                            }}
                        />
                    );
                }
            }

            // Satellite marker
            if (config.showTooltip) {
                currentPos.push(
                    <Marker key={"marker-" + satelliteId} position={[latitude, longitude]} icon={satelliteIcon2}>
                        <ThemedLeafletTooltip direction="bottom" offset={[0, 10]} opacity={1} permanent>
                            {satelliteName} - {humanizeAltitude(altitude) + " km, " + humanizeVelocity(velocity) + " km/s"}
                        </ThemedLeafletTooltip>
                    </Marker>
                );
            } else {
                currentPos.push(
                    <Marker key={"marker-" + satelliteId} position={[latitude, longitude]} icon={satelliteIcon2} />
                );
            }

            // Satellite coverage
            if (config.showSatelliteCoverage) {
                const coverage = getSatelliteCoverageCircle(latitude, longitude, altitude, 360);
                currentCoverage.push(
                    <Polyline
                        ref={coverageRef}
                        noClip={true}
                        key={"coverage-" + satelliteName}
                        pathOptions={{
                            color: config.satelliteCoverageColor,
                            weight: 1,
                            fill: true,
                            fillOpacity: 0.2,
                        }}
                        positions={coverage}
                    />
                );
            }

            setCurrentPastSatellitesPaths(currentPastPaths);
            setCurrentFutureSatellitesPaths(currentFuturePaths);
            setCurrentSatellitesPosition(currentPos);
            setCurrentSatellitesCoverage(currentCoverage);
        }

        // Day/night boundary
        const terminatorLineData = createTerminatorLine().reverse();
        setTerminatorLine(terminatorLineData);

        // Day side polygon
        const dayPoly = [...terminatorLineData];
        dayPoly.push(dayPoly[dayPoly.length - 1]);
        setDaySidePolygon(dayPoly);

        // Sun and moon position
        const [sunPosition, moonPosition] = getSunMoonCoords();
        setSunPos(sunPosition);
        setMoonPos(moonPosition);
    };

    const handleWhenReady = (map) => {
        // Map is ready
        MapObject = map.target;
    };

    useEffect(() => {
        if (coverageRef.current && MapObject) {
            // Fit the map to the polygon's bounds
            MapObject.fitBounds(coverageRef.current.getBounds(), {
                padding: [1, 1],
            });
        }
    }, [satellitePosition]);

    useEffect(() => {
        const intervalId = setInterval(() => {
            if (MapObject) {
                MapObject.invalidateSize();
            }
        }, 1000);

        return () => {
            clearInterval(intervalId);
        };
    }, []);

    // Don't render if no satellite data
    if (!satelliteData) {
        return (
            <div style={{
                width: '100%',
                height: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: '#1e1e1e',
                color: '#ffffff'
            }}>
                No satellite data available
            </div>
        );
    }

    return (
        <MapContainer
            className="satellite-details-map"
            center={[0, 0]}
            zoom={mapZoomLevel}
            style={{ width: '100%', height: '100%' }}
            maxZoom={10}
            minZoom={0}
            whenReady={handleWhenReady}
            zoomSnap={0.25}
            zoomDelta={0.25}
            keyboard={false}
            bounceAtZoomLimits={false}
            closePopupOnClick={false}
            dragging={false}
            scrollWheelZoom={false}
            zoomControl={false}
        >
            <MapEventComponent handleSetMapZoomLevel={handleSetMapZoomLevel} />
            <TileLayer url={getTileLayerById(config.tileLayerID)['url']} />
            <Marker position={sunPos} icon={sunIcon} opacity={0.5} />
            <Marker position={moonPos} icon={moonIcon} opacity={0.5} />
            <Polygon
                positions={daySidePolygon}
                pathOptions={{
                    fillColor: 'black',
                    fillOpacity: 0.4,
                    color: 'white',
                    opacity: 0.5,
                    weight: 0,
                    smoothFactor: 1,
                }}
            />
            <Polyline
                positions={terminatorLine}
                pathOptions={{
                    color: 'white',
                    weight: 1,
                    opacity: 0.1,
                }}
            />

            {InternationalDateLinePolyline()}
            {location && <Marker position={[location.lat, location.lon]} icon={homeIcon} opacity={0.8} />}
            {currentPastSatellitesPaths}
            {currentFutureSatellitesPaths}
            {currentSatellitesPosition}
            {currentSatellitesCoverage}
            <MapStatusBar>
                <SimpleTruncatedHtml
                    className={"attribution"}
                    htmlString={`<a href="https://leafletjs.com" title="A JavaScript library for interactive maps" target="_blank" rel="noopener noreferrer">Leaflet</a> | ${getTileLayerById(config.tileLayerID)['attribution']}`}
                />
            </MapStatusBar>
            <CoordinateGrid
                latInterval={15}
                lngInterval={15}
                latColor="#FFFFFF"
                lngColor="#FFFFFF"
                weight={1}
                opacity={0.5}
                showLabels={false}
            />
        </MapContainer>
    );
};

export default SatelliteMapContainer;
